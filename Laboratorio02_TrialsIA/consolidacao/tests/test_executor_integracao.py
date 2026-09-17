"""Prazo da rodada e falhas reais do executor, usando um exercício demonstrativo."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


EXECUTOR = Path(__file__).resolve().parents[2] / "casos_de_teste" / "executor.py"
SPEC = importlib.util.spec_from_file_location("executor_integracao", EXECUTOR)
executor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(executor)


class ExecutorIntegracaoTests(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.pasta = Path(self.temporario.name)
        self.solucao = self.pasta / "saudacao_demo.py"
        self.solucao.write_text("print('Oi, ' + input())\n", encoding="utf-8")
        self.casos = [
            {"entrada": "Ana\n", "saida_esperada": "Oi, Ana", "finalidade": "Nome curto"},
            {"entrada": "Bia\n", "saida_esperada": "Oi, Bia", "finalidade": "Outro nome"},
        ]
        self.bateria = self.pasta / "saudacao_demo.json"
        self.bateria.write_text(
            json.dumps({"demo_saudacao": self.casos}), encoding="utf-8",
        )

    def avaliar(self, **opcoes):
        with contextlib.redirect_stdout(io.StringIO()):
            return executor.avaliar_solucao(
                str(self.solucao), "demo_saudacao", str(self.bateria), **opcoes,
            )

    def executar_caso(self, **opcoes):
        caso = self.casos[0]
        return executor.executar_casos_de_teste(
            [sys.executable, str(self.solucao)], caso["entrada"], caso, **opcoes,
        )

    def test_chamada_antiga_aprova_bateria_real(self):
        resultado = self.avaliar()
        self.assertTrue(resultado["passou_todos"])
        self.assertEqual(resultado["aprovados"], 2)
        self.assertEqual(resultado["reprovados"], 0)

    def test_bateria_real_com_deadline_preserva_resultados(self):
        resultado = self.avaliar(deadline=time.monotonic() + 10)
        self.assertTrue(resultado["passou_todos"])
        self.assertEqual(len(resultado["detalhes"]), 2)

    def test_saida_incorreta_permanece_reprovacao(self):
        self.solucao.write_text("print('outra resposta')\n", encoding="utf-8")
        resultado = self.avaliar()
        self.assertFalse(resultado["passou_todos"])
        self.assertEqual(resultado["reprovados"], 2)
        self.assertEqual(resultado["detalhes"][0]["resultado"], "SAIDA_INCORRETA")

    def test_erro_da_solucao_permanece_erro_execucao(self):
        for codigo in ("raise RuntimeError('falha demo')\n", "def quebrada(:\n"):
            with self.subTest(codigo=codigo):
                self.solucao.write_text(codigo, encoding="utf-8")
                self.assertEqual(self.executar_caso(), "ERRO_EXECUCAO")

    def test_timeout_real_individual_mantem_status(self):
        self.solucao.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
        self.assertEqual(self.executar_caso(timeout=0.05), "TIMEOUT")

    def test_deadline_real_interrompe_subprocesso(self):
        self.solucao.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
        inicio = time.monotonic()
        with self.assertRaises(TimeoutError):
            self.avaliar(deadline=inicio + 0.2)
        self.assertLess(time.monotonic() - inicio, 4)

    def test_deadline_vencido_nao_inicia_testes(self):
        with patch.object(executor.subprocess, "run") as executar:
            with self.assertRaises(TimeoutError):
                self.avaliar(deadline=time.monotonic() - 1)
        executar.assert_not_called()

    def test_bateria_compartilha_orcamento_e_nao_inventa_resultados(self):
        relogio = [92.0]
        limites = []

        def executar(comando, **opcoes):
            limites.append(opcoes["timeout"])
            if len(limites) == 1:
                relogio[0] = 96.0
                return subprocess.CompletedProcess(comando, 0, "Oi, Ana", "")
            relogio[0] = 100.0
            raise subprocess.TimeoutExpired(comando, opcoes["timeout"])

        with patch.object(executor.time, "monotonic", side_effect=lambda: relogio[0]):
            with patch.object(executor.subprocess, "run", side_effect=executar):
                with self.assertRaises(TimeoutError):
                    self.avaliar(deadline=100.0)
        self.assertEqual(limites, [5, 4])

    def test_processo_concluido_apos_deadline_nao_aprova(self):
        with patch.object(executor.time, "monotonic", side_effect=[90.0, 101.0]):
            with patch.object(executor.subprocess, "run", return_value=(
                subprocess.CompletedProcess(["python"], 0, "Oi, Ana", "")
            )):
                with self.assertRaises(TimeoutError):
                    self.executar_caso(deadline=100.0)

    def test_timeout_individual_com_orcamento_global_disponivel(self):
        with patch.object(executor.time, "monotonic", return_value=90.0):
            with patch.object(executor.subprocess, "run", side_effect=(
                subprocess.TimeoutExpired(["python"], 5)
            )) as executar:
                self.assertEqual(self.executar_caso(deadline=100.0), "TIMEOUT")
        self.assertEqual(executar.call_args.kwargs["timeout"], 5)

    def test_erro_de_infraestrutura_nao_vira_erro_de_sintaxe(self):
        for erro in (FileNotFoundError("Python indisponível"), PermissionError("Acesso negado")):
            with self.subTest(erro=type(erro).__name__):
                with patch.object(executor.subprocess, "run", side_effect=erro):
                    with self.assertRaises(type(erro)):
                        self.avaliar()

    def test_interrupcao_nao_vira_reprovacao(self):
        with patch.object(executor.subprocess, "run", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.avaliar()

    def test_configuracao_de_teste_invalida_propaga_erro(self):
        with patch.object(executor.subprocess, "run", return_value=(
            subprocess.CompletedProcess(["python"], 0, "Oi, Ana", "")
        )):
            with self.assertRaises(KeyError):
                executor.executar_casos_de_teste(["python"], "", {})

    def test_prazos_invalidos_sao_rejeitados_antes_de_executar(self):
        with patch.object(executor.subprocess, "run") as executar:
            for deadline in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(deadline=deadline):
                    with self.assertRaises(ValueError):
                        self.avaliar(deadline=deadline)
            for timeout in (0, -1, float("nan"), float("inf")):
                with self.subTest(timeout=timeout):
                    with self.assertRaises(ValueError):
                        self.executar_caso(timeout=timeout)
        executar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
