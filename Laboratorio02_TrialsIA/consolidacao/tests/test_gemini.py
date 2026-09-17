"""Integração Gemini com respostas simuladas; não usa API nem katas oficiais."""

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[2] / "casos_de_teste" / "katas_Gemini.py"
SPEC = importlib.util.spec_from_file_location("gemini_testado", SCRIPT)
gemini = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gemini)


class ErroAPIExemplo(Exception):
    pass


class TestGerarSolucao(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.saida = Path(self.temporario.name) / "DEMO" / "solucao.py"
        self.cliente = Mock()
        self.chat = self.cliente.chats.create.return_value
        self.chat.send_message.return_value = types.SimpleNamespace(
            text="```python\nprint('demonstração')\n```"
        )
        inicializar = patch.object(
            gemini, "_inicializar_cliente", return_value=(self.cliente, ErroAPIExemplo)
        )
        inicializar.start()
        self.addCleanup(inicializar.stop)

    def test_gera_um_arquivo_e_informa_modelo(self):
        resultado = gemini.gerar_solucao("Exiba uma saudação demonstrativa.", self.saida, modelo="modelo-demo")
        self.assertEqual(self.saida.read_text(encoding="utf-8"), "print('demonstração')")
        self.assertEqual(resultado, {
            "caminho_saida": str(self.saida), "modelo": "modelo-demo", "tentativas": 1
        })
        self.cliente.chats.create.assert_called_once_with(model="modelo-demo")
        self.assertIn("Exiba uma saudação demonstrativa.", self.chat.send_message.call_args.args[0])

    def test_modelo_ambiente_pode_ser_sobrescrito(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "modelo-ambiente"}):
            resultado = gemini.gerar_solucao("Exemplo demonstrativo.", str(self.saida))
        self.assertEqual(resultado["modelo"], "modelo-ambiente")

    def test_reaproveita_extracao_sem_markdown(self):
        self.chat.send_message.return_value.text = "print('texto direto')\n"
        gemini.gerar_solucao("Exemplo demonstrativo.", self.saida)
        self.assertEqual(self.saida.read_text(encoding="utf-8"), "print('texto direto')\n")

    def test_reaproveita_extracao_generica(self):
        self.assertEqual(gemini.extrair_codigo("```\nprint(42)\n```"), "print(42)")

    @patch.object(gemini.time, "sleep")
    def test_api_error_repete_e_registra_tentativas(self, dormir):
        self.chat.send_message.side_effect = [
            ErroAPIExemplo("indisponível"), types.SimpleNamespace(text="print(42)")
        ]
        resultado = gemini.gerar_solucao("Exemplo demonstrativo.", self.saida)
        self.assertEqual(resultado["tentativas"], 2)
        dormir.assert_called_once_with(5)

    @patch.object(gemini.time, "sleep")
    def test_falha_final_preserva_arquivo_existente(self, dormir):
        self.saida.parent.mkdir()
        self.saida.write_text("print('original')", encoding="utf-8")
        self.chat.send_message.side_effect = ErroAPIExemplo("indisponível")
        with self.assertRaises(ErroAPIExemplo):
            gemini.gerar_solucao("Exemplo demonstrativo.", self.saida)
        self.assertEqual(self.chat.send_message.call_count, 3)
        self.assertEqual(dormir.call_count, 2)
        self.assertEqual(self.saida.read_text(encoding="utf-8"), "print('original')")

    def test_resposta_vazia_nao_cria_solucao(self):
        for resposta in (None, "", "   ", "```python\n\n```"):
            with self.subTest(resposta=resposta):
                self.chat.send_message.return_value.text = resposta
                with self.assertRaises(RuntimeError):
                    gemini.gerar_solucao("Exemplo demonstrativo.", self.saida)
                self.assertFalse(self.saida.exists())

    def test_interrupcao_e_propagada_sem_criar_solucao(self):
        self.chat.send_message.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            gemini.gerar_solucao("Exemplo demonstrativo.", self.saida)
        self.assertFalse(self.saida.exists())

    def test_enunciado_vazio_falha_antes_de_inicializar_cliente(self):
        with self.assertRaises(ValueError):
            gemini.gerar_solucao("   ", self.saida)
        gemini._inicializar_cliente.assert_not_called()

    def test_comando_em_lote_reutiliza_interface(self):
        entrada = Path(self.temporario.name) / "enunciados"
        entrada.mkdir()
        (entrada / "kata99_demo.md").write_text("Exemplo demonstrativo.", encoding="utf-8")
        (entrada / "README.md").write_text("Ignorar.", encoding="utf-8")
        with patch.object(gemini, "KATAS_DIR", str(entrada)):
            with patch.object(gemini, "SOLUCOES_DIR", str(self.saida.parent)):
                with patch.object(gemini, "gerar_solucao") as gerar:
                    gemini.processar_katas()
        gerar.assert_called_once_with(
            "Exemplo demonstrativo.", str(self.saida.parent / "kata99_gemini_ia.py")
        )


class TestConfiguracaoGemini(unittest.TestCase):
    def test_import_nao_requer_chave_ou_sdk(self):
        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, {"google": None}):
            modulo = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(modulo)
        self.assertTrue(callable(modulo.gerar_solucao))

    def test_erro_claro_sem_chave(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY ou GOOGLE_API_KEY"):
                gemini._inicializar_cliente()

    def test_erro_claro_sem_dependencia(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "chave-ficticia"}, clear=True):
            with patch.dict(sys.modules, {"google": None}):
                with self.assertRaisesRegex(RuntimeError, "Instale google-genai"):
                    gemini._inicializar_cliente()

    def test_duas_variaveis_de_chave_com_prioridade_gemini(self):
        genai = types.ModuleType("google.genai")
        genai.Client = Mock()
        google = types.ModuleType("google")
        google.genai = genai
        errors = types.ModuleType("google.genai.errors")
        errors.APIError = ErroAPIExemplo
        modulos = {"google": google, "google.genai": genai, "google.genai.errors": errors}
        for ambiente, chave in (
            ({"GOOGLE_API_KEY": "google-ficticia"}, "google-ficticia"),
            ({"GOOGLE_API_KEY": "google-ficticia", "GEMINI_API_KEY": "gemini-ficticia"}, "gemini-ficticia"),
        ):
            with self.subTest(ambiente=ambiente):
                with patch.dict(os.environ, ambiente, clear=True), patch.dict(sys.modules, modulos):
                    cliente, erro_api = gemini._inicializar_cliente()
                genai.Client.assert_called_with(api_key=chave)
                self.assertIs(cliente, genai.Client.return_value)
                self.assertIs(erro_api, ErroAPIExemplo)


if __name__ == "__main__":
    unittest.main()
