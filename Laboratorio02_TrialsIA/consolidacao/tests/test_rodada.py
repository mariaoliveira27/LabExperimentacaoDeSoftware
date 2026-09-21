"""Rodadas integradas com exercício DEMO e dados inteiramente temporários."""

import contextlib
import csv
import hashlib
import io
import json
import math
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from Laboratorio02_TrialsIA.consolidacao import artefatos, terminal
from Laboratorio02_TrialsIA.cronometro.src import cronometro


CORRETA = "def saudar(nome):\n    return 'Oi, ' + nome\nprint(saudar(input()))\n"
INCORRETA = "def saudar(nome):\n    if nome:\n        return 'Outra resposta'\nprint(saudar(input()))\n"


class RodadaIntegradaTests(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.pasta = Path(temporario.name)
        self.solucao = self.pasta / "saudacao_demo.py"
        self.solucao.write_bytes(CORRETA.encode("utf-8"))
        self.casos = self.pasta / "casos_demo.json"
        self.casos.write_text(json.dumps({"demo_saudacao": [
            {"entrada": "Ana\n", "saida_esperada": "Oi, Ana", "finalidade": "Nome demonstrativo"},
            {"entrada": "Bia\n", "saida_esperada": "Oi, Bia", "finalidade": "Outro nome demonstrativo"},
        ]}), encoding="utf-8")
        self.enunciado = self.pasta / "enunciado_demo.md"
        self.enunciado.write_text("Cumprimente o nome recebido com 'Oi, '.", encoding="utf-8")
        self.saida = self.pasta / "resultados_demo"
        self.csv = self.pasta / "registro_demo.csv"

    def executar(self, **opcoes):
        argumentos = {
            "integrante": "DEMO", "kata": "DEMO_SAUDACAO", "tratamento": "manual",
            "arquivo_solucao": self.solucao, "trial_id": "DEMO_integracao_01",
            "diretorio_saida": self.saida, "caminho_csv": self.csv,
            "arquivo_testes": self.casos, "automatico": True,
        }
        argumentos.update(opcoes)
        with contextlib.redirect_stdout(io.StringIO()):
            return cronometro.coordenar_rodada(**argumentos)

    @staticmethod
    def ler_json(caminho):
        return json.loads(Path(caminho).read_text(encoding="utf-8"))

    def registros(self):
        with self.csv.open(encoding="utf-8", newline="") as fluxo:
            return list(csv.DictReader(fluxo))

    def arquivos_atuais(self):
        return {str(arquivo.relative_to(self.pasta)): arquivo.read_bytes()
                for arquivo in self.pasta.rglob("*") if arquivo.is_file()}

    def test_sucesso_conecta_tempo_testes_metricas_copia_e_csv(self):
        resultado = self.executar()
        self.assertEqual(resultado["status"], "SUCESSO")
        self.assertGreaterEqual(resultado["tempo_decorrido_min"], 0)
        itens = resultado["artefatos"]
        copia = Path(itens["copia_solucao"])
        digest = hashlib.sha256(CORRETA.encode("utf-8")).hexdigest()
        self.assertEqual(copia.read_bytes(), CORRETA.encode("utf-8"))
        self.assertIn(resultado["trial_id"], copia.name)
        documentos = [self.ler_json(itens[chave]) for chave in ("testes_json", "metricas_json", "manifesto")]
        documentos.append(self.ler_json(copia.parent / "inicio_rodada.json"))
        self.assertEqual({d["trial_id"] for d in documentos}, {resultado["trial_id"]})
        testes, metricas, manifesto, _ = documentos
        self.assertEqual({testes["sha256_solucao"], metricas["sha256_solucao"], itens["sha256_copia"]}, {digest})
        self.assertEqual(Path(testes["arquivo_executado"]).read_bytes(), copia.read_bytes())
        self.assertEqual(Path(metricas["arquivo"]), copia)
        self.assertEqual(Path(testes["arquivo_solucao"]), copia)
        self.assertTrue(testes["resultado"]["passou_todos"])
        self.assertEqual((metricas["loc"], metricas["quantidade_funcoes"], metricas["complexidade_media"]), (3, 1, 1))
        self.assertEqual(manifesto["tempo_decorrido_min"], resultado["tempo_decorrido_min"])
        self.assertEqual(Path(itens["casos_testes"]).read_bytes(), self.casos.read_bytes())
        linha, = self.registros()
        self.assertEqual(linha["Trial_ID"], resultado["trial_id"])
        self.assertEqual(Path(linha["Copia_Solucao"]), copia)
        self.assertEqual(linha["Status"], "SUCESSO")
        self.assertEqual(float(linha["Tempo_Decorrido_Min"]), resultado["tempo_decorrido_min"])

    def test_edicao_durante_testes_exige_reavaliacao_da_versao_final(self):
        avaliar = cronometro.avaliar_copia
        versoes = []

        def avaliar_e_editar(copia, *args, **kwargs):
            versoes.append(copia.read_bytes())
            resultado = avaliar(copia, *args, **kwargs)
            if len(versoes) == 1:
                self.solucao.write_bytes(INCORRETA.encode("utf-8"))
            return resultado

        with patch.object(cronometro, "avaliar_copia", side_effect=avaliar_e_editar):
            resultado = self.executar()
        self.assertEqual(versoes, [CORRETA.encode("utf-8"), INCORRETA.encode("utf-8")])
        self.assertEqual(resultado["status"], "TESTES_REPROVADOS")
        itens = resultado["artefatos"]
        self.assertEqual(Path(itens["copia_solucao"]).read_bytes(), INCORRETA.encode("utf-8"))
        self.assertFalse(self.ler_json(itens["testes_json"])["resultado"]["passou_todos"])
        metricas = self.ler_json(itens["metricas_json"])
        self.assertEqual((metricas["loc"], metricas["complexidade_media"]), (4, 2))

    def test_finalizador_legado_nao_reutiliza_aprovacao_de_arquivo_mutavel(self):
        with contextlib.redirect_stdout(io.StringIO()):
            aprovacao_antiga = artefatos.avaliar_copia(self.solucao, "demo_saudacao", self.casos)
            self.solucao.write_text(INCORRETA, encoding="utf-8")
            resultado = cronometro.finalizar_rodada(
                "SUCESSO", "DEMO", "DEMO_SAUDACAO", "manual", self.solucao,
                "DEMO_legado", 1000, 1001, aprovacao_antiga,
                diretorio_saida=self.saida, caminho_csv=self.csv, arquivo_testes=self.casos,
            )
        self.assertEqual(resultado["status"], "TESTES_REPROVADOS")
        self.assertFalse(resultado["passou_todos"])
        self.assertEqual(Path(resultado["artefatos"]["copia_solucao"]).read_text(encoding="utf-8"), INCORRETA)

    def test_trial_id_duplicado_nao_altera_qualquer_arquivo_ou_csv(self):
        self.executar()
        antes = self.arquivos_atuais()
        for destino in (self.saida, self.pasta / "outro_destino"):
            with self.subTest(destino=destino):
                with self.assertRaises(FileExistsError):
                    self.executar(diretorio_saida=destino)
                self.assertEqual(self.arquivos_atuais(), antes)

    def test_diretorio_de_trial_existente_e_preservado_mesmo_sem_csv(self):
        pasta_trial = self.saida / "DEMO_integracao_01"
        pasta_trial.mkdir(parents=True)
        (pasta_trial / "resultado_existente.json").write_text('{"preservar": true}', encoding="utf-8")
        antes = self.arquivos_atuais()
        with self.assertRaises(FileExistsError):
            self.executar()
        self.assertEqual(self.arquivos_atuais(), antes)

    def test_reprovacao_tem_resultados_observados_e_metricas_validas(self):
        self.solucao.write_text(INCORRETA, encoding="utf-8")
        resultado = self.executar()
        self.assertEqual(resultado["status"], "TESTES_REPROVADOS")
        self.assertEqual(resultado["taxa_sucesso_testes"], 0)
        self.assertFalse(resultado["passou_todos"])
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["erros"], [])

    def test_falha_de_analise_preserva_erro_e_metricas_nulas(self):
        self.solucao.write_text("def saudacao(:\n", encoding="utf-8")
        resultado = self.executar()
        self.assertEqual(resultado["status"], "ERRO")
        self.assertEqual(resultado["status_encerramento"], "TESTES_REPROVADOS")
        metricas = self.ler_json(resultado["artefatos"]["metricas_json"])
        self.assertEqual(metricas["status_analise"], "erro_sintaxe")
        self.assertEqual(metricas["erro"]["tipo"], "SyntaxError")
        for campo in ("loc", "sloc", "quantidade_funcoes", "complexidade_media", "funcoes"):
            self.assertIsNone(metricas[campo])

    def test_avaliador_indisponivel_nao_inventa_reprovacao_ou_zero(self):
        with patch.object(artefatos, "avaliar_solucao", return_value=None):
            resultado = self.executar()
        self.assertEqual(resultado["status"], "ERRO")
        self.assertIsNone(resultado["passou_todos"])
        self.assertIsNone(resultado["taxa_sucesso_testes"])
        testes = self.ler_json(resultado["artefatos"]["testes_json"])
        self.assertEqual(testes["status_execucao"], "erro")
        self.assertIsNone(testes["resultado"])
        linha, = self.registros()
        self.assertEqual(linha["Passou_Testes"], "")
        self.assertEqual(linha["Taxa_Sucesso_Testes"], "")

    def test_interrupcoes_de_terminal_preservam_tempo_real(self):
        for erro in (EOFError, KeyboardInterrupt):
            with self.subTest(erro=erro.__name__):
                with patch("builtins.input", return_value=""), patch.object(cronometro, "ler_ate", side_effect=erro):
                    resultado = self.executar(automatico=False, trial_id=f"DEMO_{erro.__name__}")
                self.assertEqual(resultado["status"], "INTERRUPCAO")
                self.assertFalse(resultado["dado_censurado"])
                self.assertLess(resultado["tempo_final_considerado"], 35)
                self.assertIn(erro.__name__, resultado["motivo_interrupcao"])
                self.assertTrue(Path(resultado["artefatos"]["copia_solucao"]).is_file())

    def test_limite_aguardando_entrada_nao_vira_interrupcao_ou_sucesso(self):
        with patch("builtins.input", return_value=""), patch.object(cronometro, "ler_ate", side_effect=TimeoutError("prazo encerrado")):
            resultado = self.executar(automatico=False, timebox_minutos=0.01)
        self.assertEqual(resultado["status"], "LIMITE_ATINGIDO")
        self.assertTrue(resultado["dado_censurado"])
        self.assertEqual(resultado["tempo_final_considerado"], 0.01)
        # A avaliação posterior preserva dados úteis, sem atribuir sucesso à rodada.
        self.assertTrue(resultado["passou_todos"])

    def test_interromper_congela_codigo_e_tempo_antes_da_justificativa(self):
        def justificar(*args):
            self.solucao.write_bytes(INCORRETA.encode("utf-8"))
            time.sleep(0.05)
            raise TimeoutError("Prazo acabou durante a justificativa")

        with patch("builtins.input", return_value=""), patch.object(
            cronometro, "ler_ate", side_effect=["3", TimeoutError("sem motivo")]
        ):
            resultado = self.executar(automatico=False)
        self.assertEqual(resultado["status"], "INTERRUPCAO")
        self.assertFalse(resultado["dado_censurado"])
        with patch("builtins.input", return_value=""), patch.object(
            cronometro, "ler_ate", side_effect=lambda mensagem, prazo: "3" if "[1]" in mensagem else justificar()
        ):
            resultado = self.executar(automatico=False, trial_id="DEMO_justificativa")
        self.assertEqual(resultado["status"], "INTERRUPCAO")
        self.assertLess(resultado["tempo_decorrido_min"] * 60, 0.05)
        self.assertEqual(Path(resultado["artefatos"]["copia_solucao"]).read_bytes(), CORRETA.encode("utf-8"))
        self.assertTrue(resultado["passou_todos"])

    def test_solucao_que_apaga_copia_registra_erro_e_restaura_fonte(self):
        fonte = b"from pathlib import Path\nPath(__file__).unlink()\nprint('Oi, ' + input())\n"
        self.solucao.write_bytes(fonte)
        resultado = self.executar()
        self.assertEqual(resultado["status"], "ERRO")
        self.assertEqual(Path(resultado["artefatos"]["copia_solucao"]).read_bytes(), fonte)
        self.assertIsNone(self.ler_json(resultado["artefatos"]["testes_json"])["resultado"])
        self.assertEqual(len(self.registros()), 1)

    def test_solucao_removida_antes_da_parada_preserva_relatorios_de_erro(self):
        def remover(*args):
            self.solucao.unlink()
            raise EOFError()

        with patch("builtins.input", return_value=""), patch.object(cronometro, "ler_ate", side_effect=remover):
            resultado = self.executar(automatico=False)
        self.assertEqual(resultado["status"], "ERRO")
        self.assertEqual(resultado["status_encerramento"], "INTERRUPCAO")
        self.assertIsNone(resultado["artefatos"]["copia_solucao"])
        self.assertIsNone(resultado["taxa_sucesso_testes"])
        metricas = self.ler_json(resultado["artefatos"]["metricas_json"])
        self.assertIsNone(metricas["loc"])
        self.assertIsNone(metricas["complexidade_media"])

    def test_base_utf8_com_bom_e_aceita_em_toda_integracao(self):
        self.casos.write_bytes(b"\xef\xbb\xbf" + self.casos.read_bytes())
        resultado = self.executar()
        self.assertEqual(resultado["status"], "SUCESSO")

    def test_simulacao_legada_exige_destinos_separados(self):
        with self.assertRaises(ValueError):
            self.executar(simulacao={"tipo": "sucesso"}, caminho_csv=cronometro.ARQUIVO_LOG_PADRAO)
        self.assertFalse(self.saida.exists())

    def test_coletor_indisponivel_registra_erro_sem_perder_aceitacao(self):
        with patch("Laboratorio02_TrialsIA.metricas_estruturais.src.coletar_metricas.analisar_arquivo",
                   side_effect=ImportError("dependência indisponível")):
            resultado = self.executar()
        self.assertEqual(resultado["status"], "ERRO")
        self.assertEqual(resultado["status_encerramento"], "SUCESSO")
        self.assertTrue(resultado["passou_todos"])
        self.assertIsNone(self.ler_json(resultado["artefatos"]["metricas_json"])["loc"])

    def test_timeboxes_invalidos_nao_iniciam_rodada(self):
        antes = self.arquivos_atuais()
        for limite in (0, -1, 35.001, math.inf, -math.inf, math.nan):
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    self.executar(timebox_minutos=limite)
                self.assertEqual(self.arquivos_atuais(), antes)

    def test_gemini_exige_tratamento_ia_e_enunciado(self):
        for tratamento, enunciado in (("manual", self.enunciado), ("ia", None)):
            with self.subTest(tratamento=tratamento, enunciado=enunciado):
                with self.assertRaises(ValueError):
                    self.executar(gemini=True, tratamento=tratamento, enunciado=enunciado)
        self.assertFalse(self.saida.exists())

    def simular_worker(self, resposta):
        executar_real = subprocess.run
        chamadas = []

        def executar(comando, **opcoes):
            if "Laboratorio02_TrialsIA.consolidacao.gerar_ia" in comando:
                chamadas.append((comando, opcoes))
                return resposta(comando, opcoes)
            return executar_real(comando, **opcoes)

        return patch.object(cronometro.subprocess, "run", side_effect=executar), chamadas

    def test_gemini_gera_em_worker_limitado_e_avalia_arquivo_resultante(self):
        self.solucao.write_text("# aguardando geração\n", encoding="utf-8")

        def responder(comando, opcoes):
            Path(comando[-1]).write_text(CORRETA, encoding="utf-8")
            return subprocess.CompletedProcess(comando, 0, stdout="", stderr="")

        worker, chamadas = self.simular_worker(responder)
        with worker:
            resultado = self.executar(gemini=True, tratamento="ia", enunciado=self.enunciado)
        self.assertEqual(resultado["status"], "SUCESSO")
        comando, opcoes = chamadas[0]
        self.assertEqual(len(chamadas), 1)
        self.assertGreater(opcoes["timeout"], 0)
        self.assertLessEqual(opcoes["timeout"], 35 * 60)
        self.assertEqual(comando[1], "-m")
        self.assertEqual(Path(comando[-2]), self.enunciado)
        self.assertNotEqual(Path(comando[-1]), self.solucao)
        self.assertEqual(Path(comando[-1]).suffix, ".py")
        self.assertEqual(self.solucao.read_text(encoding="utf-8"), CORRETA)
        self.assertEqual(Path(resultado["artefatos"]["copia_solucao"]).read_text(encoding="utf-8"), CORRETA)

    def test_gemini_com_falha_registra_erro_sem_alterar_solucao_original(self):
        def responder(comando, opcoes):
            return subprocess.CompletedProcess(comando, 1, stdout="", stderr="falha demonstrativa")

        worker, _ = self.simular_worker(responder)
        with worker:
            resultado = self.executar(gemini=True, tratamento="ia", enunciado=self.enunciado)
        self.assertEqual(resultado["status"], "ERRO")
        self.assertIn("falha demonstrativa", resultado["erros"][0]["mensagem"])
        self.assertEqual(self.solucao.read_text(encoding="utf-8"), CORRETA)

    def test_gemini_com_timeout_nao_publica_resultado_parcial_ou_tardio(self):
        def responder(comando, opcoes):
            Path(comando[-1]).write_text(INCORRETA, encoding="utf-8")
            raise subprocess.TimeoutExpired(comando, opcoes["timeout"])

        worker, chamadas = self.simular_worker(responder)
        with worker:
            resultado = self.executar(gemini=True, tratamento="ia", enunciado=self.enunciado, timebox_minutos=0.01)
        self.assertEqual(resultado["status"], "LIMITE_ATINGIDO")
        self.assertEqual(resultado["tempo_final_considerado"], 0.01)
        self.assertLessEqual(chamadas[0][1]["timeout"], 0.6)
        self.assertEqual(self.solucao.read_text(encoding="utf-8"), CORRETA)
        self.assertEqual(Path(resultado["artefatos"]["copia_solucao"]).read_text(encoding="utf-8"), CORRETA)


class TerminalComPrazoTests(unittest.TestCase):
    def test_entrada_bloqueada_respeita_deadline_finito(self):
        liberar = threading.Event()
        terminou = threading.Event()

        def entrada_bloqueada(_):
            try:
                liberar.wait(2)
                return "resposta tardia"
            finally:
                terminou.set()

        inicio = time.monotonic()
        try:
            with patch("builtins.input", side_effect=entrada_bloqueada):
                with self.assertRaises(TimeoutError):
                    terminal.ler_ate("Demo: ", inicio + 0.05)
            self.assertLess(time.monotonic() - inicio, 1)
        finally:
            liberar.set()
            terminou.wait(2)

    def test_entrada_ou_interrupcao_e_repassada(self):
        with patch("builtins.input", return_value="3"):
            self.assertEqual(terminal.ler_ate("Demo: ", time.monotonic() + 2), "3")
        for erro in (EOFError, KeyboardInterrupt):
            with self.subTest(erro=erro.__name__):
                with patch("builtins.input", side_effect=erro):
                    with self.assertRaises(erro):
                        terminal.ler_ate("Demo: ", time.monotonic() + 2)


if __name__ == "__main__":
    unittest.main()
