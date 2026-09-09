"""Testes do coletor com exemplos próprios, sem soluções dos exercícios oficiais.

As expectativas são explícitas: cada função começa em 1 e cada ``if`` simples
acrescenta 1. Classes e funções que apenas contêm outras definições não somam
novamente a complexidade dessas definições. Os testes não calculam o valor
esperado chamando o próprio Radon.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


COMPONENTE = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPT = COMPONENTE / "src" / "coletar_metricas.py"
sys.path.insert(0, str(SCRIPT.parent))

from coletar_metricas import analisar_arquivo, gravar_resultado  # noqa: E402


CAMPOS_RESULTADO = {
    "schema_version",
    "trial_id",
    "arquivo",
    "status_analise",
    "erro",
    "quantidade_funcoes",
    "complexidade_media",
    "loc",
    "sloc",
    "funcoes",
}
CAMPOS_METRICAS = (
    "quantidade_funcoes", "complexidade_media", "loc", "sloc", "funcoes"
)


class TestAnalisarArquivo(unittest.TestCase):
    def analisar_fixture(self, nome):
        arquivo = FIXTURES / nome
        resultado = analisar_arquivo(arquivo, "DEMO-unittest-Áulus")
        self.assertEqual(set(resultado), CAMPOS_RESULTADO)
        self.assertEqual(resultado["schema_version"], 1)
        self.assertEqual(resultado["trial_id"], "DEMO-unittest-Áulus")
        self.assertEqual(resultado["arquivo"], str(arquivo))
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertIsNone(resultado["erro"])
        for funcao in resultado["funcoes"]:
            self.assertEqual(set(funcao), {"nome", "linha", "complexidade"})
            self.assertIsInstance(funcao["linha"], int)
            self.assertIsInstance(funcao["complexidade"], int)
        return resultado

    def verificar_erro(self, resultado, status, tipo):
        self.assertEqual(set(resultado), CAMPOS_RESULTADO)
        self.assertEqual(resultado["status_analise"], status)
        self.assertEqual(set(resultado["erro"]), {"tipo", "mensagem"})
        self.assertEqual(resultado["erro"]["tipo"], tipo)
        self.assertTrue(resultado["erro"]["mensagem"])
        for campo in CAMPOS_METRICAS:
            with self.subTest(campo=campo):
                self.assertIsNone(resultado[campo])

    def test_funcao_sem_decisoes_tem_complexidade_um(self):
        resultado = self.analisar_fixture("sem_decisoes.py")
        self.assertEqual(resultado["quantidade_funcoes"], 1)
        self.assertEqual(resultado["complexidade_media"], 1)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "saudacao", "linha": 1, "complexidade": 1}
        ])

    def test_funcao_com_if_tem_complexidade_dois(self):
        resultado = self.analisar_fixture("if_simples.py")
        self.assertEqual(resultado["quantidade_funcoes"], 1)
        self.assertEqual(resultado["complexidade_media"], 2)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "rotulo", "linha": 1, "complexidade": 2}
        ])

    def test_duas_funcoes_com_complexidades_um_e_tres_tem_media_dois(self):
        resultado = self.analisar_fixture("media_dois.py")
        self.assertEqual(resultado["quantidade_funcoes"], 2)
        self.assertEqual(resultado["complexidade_media"], 2)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "constante", "linha": 1, "complexidade": 1},
            {"nome": "categoria", "linha": 5, "complexidade": 3},
        ])

    def test_metodos_nao_incluem_valor_agregado_da_classe(self):
        resultado = self.analisar_fixture("classes.py")
        self.assertEqual(resultado["quantidade_funcoes"], 2)
        self.assertEqual(resultado["complexidade_media"], 1.5)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "Painel.titulo", "linha": 2, "complexidade": 1},
            {"nome": "Painel.estado", "linha": 5, "complexidade": 2},
        ])

    def test_funcao_aninhada_e_contada_uma_vez_sem_somar_na_externa(self):
        resultado = self.analisar_fixture("aninhadas.py")
        self.assertEqual(resultado["quantidade_funcoes"], 2)
        self.assertEqual(resultado["complexidade_media"], 1.5)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "externa", "linha": 1, "complexidade": 1},
            {"nome": "externa.interna", "linha": 2, "complexidade": 2},
        ])

    def test_classes_locais_escopos_profundos_e_async(self):
        resultado = self.analisar_fixture("escopos_profundos.py")
        self.assertEqual(resultado["quantidade_funcoes"], 7)
        self.assertAlmostEqual(resultado["complexidade_media"], 10 / 7)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "Caixa.simples", "linha": 2, "complexidade": 1},
            {"nome": "Caixa.decidir", "linha": 5, "complexidade": 2},
            {"nome": "Caixa.Interna.acao", "linha": 11, "complexidade": 2},
            {"nome": "criar", "linha": 17, "complexidade": 1},
            {"nome": "criar.Local.metodo", "linha": 19, "complexidade": 1},
            {"nome": "criar.Local.metodo.profunda", "linha": 20,
             "complexidade": 1},
            {"nome": "criar.Local.metodo.profunda.folha", "linha": 21,
             "complexidade": 2},
        ])

    def test_arquivo_sem_funcoes_preserva_loc_sloc_e_media_nula(self):
        resultado = self.analisar_fixture("sem_funcoes.py")
        self.assertEqual(resultado["quantidade_funcoes"], 0)
        self.assertIsNone(resultado["complexidade_media"])
        self.assertEqual(resultado["funcoes"], [])
        self.assertEqual(resultado["loc"], 3)
        self.assertEqual(resultado["sloc"], 1)

    def test_loc_inclui_comentarios_docstring_e_linhas_vazias(self):
        resultado = self.analisar_fixture("comentarios_linhas_vazias.py")
        self.assertEqual(resultado["loc"], 9)
        self.assertEqual(resultado["sloc"], 2)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "exemplo", "linha": 3, "complexidade": 1}
        ])

    def test_arquivo_vazio(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "vazio.py"
            arquivo.write_text("", encoding="utf-8")
            resultado = analisar_arquivo(arquivo, "DEMO-vazio")
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["quantidade_funcoes"], 0)
        self.assertIsNone(resultado["complexidade_media"])
        self.assertEqual(resultado["funcoes"], [])
        self.assertEqual((resultado["loc"], resultado["sloc"]), (0, 0))

    def test_sintaxe_invalida_deixa_metricas_indisponiveis(self):
        arquivo = FIXTURES / "erro_sintaxe.txt"
        resultado = analisar_arquivo(arquivo, "DEMO-sintaxe")
        self.verificar_erro(resultado, "erro_sintaxe", "SyntaxError")
        self.assertEqual(resultado["trial_id"], "DEMO-sintaxe")
        self.assertEqual(resultado["arquivo"], str(arquivo))

    def test_arquivo_inexistente(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "nao_existe.py"
            resultado = analisar_arquivo(arquivo, "DEMO-inexistente")
        self.verificar_erro(resultado, "erro_leitura", "FileNotFoundError")

    def test_sem_permissao_de_leitura(self):
        with patch.object(Path, "read_text", side_effect=PermissionError(
            "Leitura negada para demonstração"
        )):
            resultado = analisar_arquivo(FIXTURES / "sem_decisoes.py", "DEMO-leitura")
        self.verificar_erro(resultado, "erro_leitura", "PermissionError")
        self.assertIn("Leitura negada", resultado["erro"]["mensagem"])

    def test_utf8_invalido_nao_vira_metrica_zero(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "encoding_invalido.py"
            arquivo.write_bytes(b"# \xff\n")
            resultado = analisar_arquivo(arquivo, "DEMO-encoding")
        self.verificar_erro(resultado, "erro_leitura", "UnicodeDecodeError")

    def test_utf8_com_bom_e_nome_acentuado(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "acentuação.py"
            arquivo.write_text("def ação():\n    return 'olá'\n", encoding="utf-8-sig")
            resultado = analisar_arquivo(str(arquivo), "DEMO-Áulus")
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["arquivo"], str(arquivo))
        self.assertEqual(resultado["funcoes"], [
            {"nome": "ação", "linha": 1, "complexidade": 1}
        ])

    def test_validacao_nao_herda_future_annotations_do_coletor(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "anotacao_valida.py"
            arquivo.write_text(
                "def f(x: (y := 1)):\n    return x\n", encoding="utf-8"
            )
            resultado = analisar_arquivo(arquivo, "DEMO-anotacao-valida")
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["funcoes"], [
            {"nome": "f", "linha": 1, "complexidade": 1}
        ])

    def test_validacao_respeita_future_annotations_da_solucao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "anotacao_invalida.py"
            arquivo.write_text(
                "from __future__ import annotations\n"
                "def f(x: (y := 1)):\n    return x\n", encoding="utf-8"
            )
            resultado = analisar_arquivo(arquivo, "DEMO-anotacao-invalida")
        self.verificar_erro(resultado, "erro_sintaxe", "SyntaxError")

    def test_return_fora_de_funcao_e_erro_de_sintaxe(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "return_fora_de_funcao.py"
            arquivo.write_text("return 1\n", encoding="utf-8")
            resultado = analisar_arquivo(arquivo, "DEMO-contexto-invalido")
        self.verificar_erro(resultado, "erro_sintaxe", "SyntaxError")

    def test_falha_da_analise_radon_deixa_metricas_indisponiveis(self):
        with patch("coletar_metricas.analyze", side_effect=ValueError(
            "Falha simulada no processamento de métricas brutas"
        )):
            resultado = analisar_arquivo(FIXTURES / "sem_decisoes.py", "DEMO-radon")
        self.verificar_erro(resultado, "erro_analise", "ValueError")

    def test_solucao_nao_e_importada_nem_executada(self):
        with tempfile.TemporaryDirectory() as pasta:
            marcador = Path(pasta) / "NAO_DEVE_EXISTIR.txt"
            arquivo = Path(pasta) / "efeito_colateral.py"
            arquivo.write_text(
                "from pathlib import Path\n"
                f"Path({str(marcador)!r}).write_text('executado', encoding='utf-8')\n"
                "raise RuntimeError('O coletor executou a solução!')\n"
                "\n"
                "def exemplo():\n"
                "    return 1\n",
                encoding="utf-8",
            )
            resultado = analisar_arquivo(arquivo, "DEMO-sem-execucao")
            self.assertFalse(marcador.exists())
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["quantidade_funcoes"], 1)

    def test_analisa_somente_arquivo_indicado_sem_importar_dependencias(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "principal.py"
            arquivo.write_text(
                "import dependencia\nimport modulo_que_nao_existe_demo\n\n"
                "def principal():\n    return 1\n",
                encoding="utf-8",
            )
            (Path(pasta) / "dependencia.py").write_text(
                "raise RuntimeError('Não importar')\n\n"
                "def auxiliar():\n    return 2\n",
                encoding="utf-8",
            )
            resultado = analisar_arquivo(arquivo, "DEMO-arquivo-unico")
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["quantidade_funcoes"], 1)
        self.assertEqual(resultado["funcoes"], [
            {"nome": "principal", "linha": 4, "complexidade": 1}
        ])


class TestGravarResultado(unittest.TestCase):
    def setUp(self):
        self.resultado = analisar_arquivo(FIXTURES / "media_dois.py", "DEMO-Áulus-001")

    def test_json_utf8_legivel_e_trial_id_preservado(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "resultado.json"
            gravar_resultado(self.resultado, saida)
            reaberto = json.loads(saida.read_text(encoding="utf-8"))
        self.assertEqual(reaberto, self.resultado)
        self.assertEqual(reaberto["trial_id"], "DEMO-Áulus-001")
        self.assertEqual(reaberto["schema_version"], 1)

    def test_falha_gravacao_em_pasta_inexistente(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "pasta_inexistente" / "resultado.json"
            with self.assertRaises(OSError):
                gravar_resultado(self.resultado, saida)

    def test_nao_sobrescreve_resultado_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "resultado.json"
            original = b'{"trial_id": "DEMO-original", "preservar": true}\n'
            saida.write_bytes(original)
            with self.assertRaises(FileExistsError):
                gravar_resultado(self.resultado, saida)
            self.assertEqual(saida.read_bytes(), original)

    def test_saida_igual_entrada_nao_modifica_solucao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "solucao.py"
            original = b"def exemplo():\n    return 1\n"
            arquivo.write_bytes(original)
            resultado = analisar_arquivo(arquivo, "DEMO-mesmo-arquivo")
            with self.assertRaises(FileExistsError):
                gravar_resultado(resultado, arquivo)
            self.assertEqual(arquivo.read_bytes(), original)


class TestCLI(unittest.TestCase):
    def executar(self, *argumentos):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, argumentos)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )

    def test_cli_sucesso_e_json_lido_por_outro_programa(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "metricas.json"
            processo = self.executar(
                "--arquivo", FIXTURES / "media_dois.py",
                "--trial-id", "DEMO-integracao-001", "--saida", saida,
            )
            self.assertEqual(processo.returncode, 0, processo.stderr)
            resultado = json.loads(saida.read_text(encoding="utf-8"))
        self.assertEqual(resultado["trial_id"], "DEMO-integracao-001")
        self.assertEqual(resultado["status_analise"], "ok")
        self.assertEqual(resultado["quantidade_funcoes"], 2)
        self.assertEqual(resultado["complexidade_media"], 2)

    def test_cli_sintaxe_invalida_grava_json_de_erro_e_retorna_um(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "erro.json"
            processo = self.executar(
                "--arquivo", FIXTURES / "erro_sintaxe.txt",
                "--trial-id", "DEMO-cli-sintaxe", "--saida", saida,
            )
            self.assertEqual(processo.returncode, 1, processo.stderr)
            self.assertTrue(processo.stderr.strip())
            resultado = json.loads(saida.read_text(encoding="utf-8"))
        self.assertEqual(resultado["trial_id"], "DEMO-cli-sintaxe")
        self.assertEqual(resultado["status_analise"], "erro_sintaxe")
        self.assertEqual(resultado["erro"]["tipo"], "SyntaxError")
        for campo in CAMPOS_METRICAS:
            self.assertIsNone(resultado[campo])

    def test_cli_arquivo_inexistente_grava_json_de_erro(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "erro.json"
            processo = self.executar(
                "--arquivo", Path(pasta) / "inexistente.py",
                "--trial-id", "DEMO-cli-ausente", "--saida", saida,
            )
            self.assertEqual(processo.returncode, 1, processo.stderr)
            self.assertTrue(processo.stderr.strip())
            resultado = json.loads(saida.read_text(encoding="utf-8"))
        self.assertEqual(resultado["status_analise"], "erro_leitura")
        self.assertEqual(resultado["erro"]["tipo"], "FileNotFoundError")

    def test_cli_falha_gravacao_informa_stderr_e_retorna_dois(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "inexistente" / "metricas.json"
            processo = self.executar(
                "--arquivo", FIXTURES / "sem_decisoes.py",
                "--trial-id", "DEMO-cli-gravacao", "--saida", saida,
            )
            self.assertEqual(processo.returncode, 2)
            self.assertTrue(processo.stderr.strip())
            self.assertFalse(saida.exists())

    def test_cli_resultado_existente_e_preservado(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "metricas.json"
            original = b'{"trial_id": "DEMO-anterior"}\n'
            saida.write_bytes(original)
            processo = self.executar(
                "--arquivo", FIXTURES / "sem_decisoes.py",
                "--trial-id", "DEMO-nao-sobrescrever", "--saida", saida,
            )
            self.assertEqual(processo.returncode, 2)
            self.assertTrue(processo.stderr.strip())
            self.assertEqual(saida.read_bytes(), original)

    def test_cli_erro_de_analise_e_gravacao_prioriza_falha_de_gravacao(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = Path(pasta) / "inexistente" / "erro.json"
            processo = self.executar(
                "--arquivo", FIXTURES / "erro_sintaxe.txt",
                "--trial-id", "DEMO-duas-falhas", "--saida", saida,
            )
        self.assertEqual(processo.returncode, 2)
        self.assertTrue(processo.stderr.strip())

    def test_cli_argumentos_obrigatorios(self):
        processo = self.executar()
        self.assertEqual(processo.returncode, 2)
        self.assertTrue(processo.stderr.strip())


if __name__ == "__main__":
    unittest.main()
