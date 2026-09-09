"""Verifica o comparador do executor, sem executar soluções ou rodadas."""

import importlib.util
import unittest
from pathlib import Path


CAMINHO_EXECUTOR = Path(__file__).resolve().parents[1] / "executor.py"
SPEC = importlib.util.spec_from_file_location("executor_katas", CAMINHO_EXECUTOR)
executor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(executor)


class ComparacaoExecutorTests(unittest.TestCase):
    def test_texto_mantem_normalizacao_existente(self):
        caso = {"saida_esperada": "SIM NAO", "tipo_comparacao": "texto"}
        self.assertTrue(executor.comparar_saidas("  SIM  \nNAO\n", caso))
        self.assertFalse(executor.comparar_saidas("Resultado: SIM NAO", caso))

    def test_float_sem_tolerancia_mantem_padroes_existentes(self):
        caso = {"saida_esperada": "0.5", "tipo_comparacao": "float"}
        self.assertTrue(executor.comparar_saidas("0.50009", caso))
        self.assertFalse(executor.comparar_saidas("0.50011", caso))
        caso["saida_esperada"] = "1000000000"
        self.assertTrue(executor.comparar_saidas("1000000000.5", caso))

    def test_tolerancia_explicita_aplica_limite_absoluto(self):
        caso = {"saida_esperada": "0", "tipo_comparacao": "float",
                "tolerancia_absoluta": 1e-9}
        self.assertTrue(executor.comparar_saidas("1e-9\n", caso))
        self.assertFalse(executor.comparar_saidas("1.000001e-9", caso))
        caso["saida_esperada"] = "0.5"
        self.assertFalse(executor.comparar_saidas("0.50000001", caso))

    def test_tolerancia_explicita_desativa_tolerancia_relativa(self):
        caso = {"saida_esperada": "1000000000", "tipo_comparacao": "float",
                "tolerancia_absoluta": 1e-9}
        self.assertFalse(executor.comparar_saidas("1000000000.5", caso))

    def test_float_rejeita_nao_finitos_e_texto_adicional(self):
        for adicionais in ({}, {"tolerancia_absoluta": 1e-9}):
            caso = {"saida_esperada": "0.5", "tipo_comparacao": "float", **adicionais}
            for saida in ("NaN", "inf", "-inf", "0,5", "valor: 0.5", "0.5\n0.5", ""):
                with self.subTest(saida=saida, adicionais=adicionais):
                    self.assertFalse(executor.comparar_saidas(saida, caso))
            for nao_finito in ("NaN", "inf", "-inf"):
                with self.subTest(referencia=nao_finito, adicionais=adicionais):
                    caso["saida_esperada"] = nao_finito
                    self.assertFalse(executor.comparar_saidas(nao_finito, caso))

    def test_tolerancia_explicita_invalida_reprova_comparacao(self):
        for tolerancia in (-1, float("nan"), float("inf"), "invalida", None):
            with self.subTest(tolerancia=tolerancia):
                caso = {"saida_esperada": "0.5", "tipo_comparacao": "float",
                        "tolerancia_absoluta": tolerancia}
                self.assertFalse(executor.comparar_saidas("0.5", caso))


if __name__ == "__main__":
    unittest.main()
