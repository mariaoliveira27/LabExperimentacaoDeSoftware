"""Verifica somente os dados de aceitação, sem executar soluções oficiais."""

import json
import math
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


ARQUIVO_CASOS = Path(__file__).resolve().parents[1] / "casos_de_teste_katas.json"


class CasosAceitacaoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.todos = json.loads(ARQUIVO_CASOS.read_text(encoding="utf-8"))
        cls.k05 = cls.todos["kata05"]
        cls.k06 = cls.todos["kata06"]

    def test_base_central_e_quantidade_por_grupo(self):
        self.assertEqual(set(self.todos), {f"kata{i:02d}" for i in range(1, 7)})
        self.assertEqual(
            {chave: len(casos) for chave, casos in self.todos.items()},
            {"kata01": 10, "kata02": 10, "kata03": 10, "kata04": 10,
             "kata05": 11, "kata06": 10},
        )

    def test_esquema_e_identificadores_unicos(self):
        obrigatorios = {"id", "finalidade", "entrada", "saida_esperada", "tipo_comparacao"}
        identificadores = set()
        for prefixo, casos in (("K05", self.k05), ("K06", self.k06)):
            self.assertIsInstance(casos, list)
            for caso in casos:
                with self.subTest(caso=caso.get("id")):
                    campos = obrigatorios | (
                        {"tolerancia_absoluta"} if prefixo == "K06" else set()
                    )
                    self.assertEqual(set(caso), campos)
                    self.assertRegex(caso["id"], rf"^{prefixo}-\d{{2}}$")
                    self.assertNotIn(caso["id"], identificadores)
                    identificadores.add(caso["id"])
                    self.assertIsInstance(caso["finalidade"], str)
                    self.assertTrue(caso["finalidade"].strip())
                    self.assertIsInstance(caso["entrada"], str)
                    self.assertTrue(caso["entrada"].endswith("\n"))
                    self.assertIsInstance(caso["saida_esperada"], str)

    def test_k05_contrato_e_primeira_ocorrencia(self):
        for caso in self.k05:
            with self.subTest(caso=caso["id"]):
                linhas = caso["entrada"].splitlines()
                self.assertEqual(len(linhas), 3)
                n = int(linhas[0])
                vetor = [int(valor) for valor in linhas[1].split()]
                alvo = int(linhas[2])
                self.assertGreaterEqual(n, 0)
                self.assertLessEqual(n, 200)
                self.assertEqual(len(vetor), n)
                if n == 0:
                    self.assertEqual(linhas[1], "")
                referencia = vetor.index(alvo) if alvo in vetor else -1
                self.assertEqual(caso["tipo_comparacao"], "texto")
                self.assertIsInstance(caso["saida_esperada"], str)
                self.assertEqual(caso["saida_esperada"], str(referencia))

    def test_k05_cobertura_dos_limites_e_cenarios(self):
        self.assertGreaterEqual(len(self.k05), 10)
        cenarios = set()
        for caso in self.k05:
            linhas = caso["entrada"].splitlines()
            vetor = [int(valor) for valor in linhas[1].split()]
            alvo = int(linhas[2])
            posicao = int(caso["saida_esperada"])
            if not vetor:
                cenarios.add("vazio")
            if len(vetor) == 1:
                cenarios.add("unitario_presente" if posicao == 0 else "unitario_ausente")
            if len(vetor) > 1:
                if posicao == -1:
                    cenarios.add("ausente")
                elif posicao == 0:
                    cenarios.add("inicio")
                elif posicao == len(vetor) - 1:
                    cenarios.add("fim")
                else:
                    cenarios.add("meio")
            if any(valor < 0 for valor in vetor) and 0 in vetor:
                cenarios.add("negativos_e_zero")
            if vetor.count(alvo) > 1:
                cenarios.add("repetidos")
            if len(vetor) == 200 and posicao == 199:
                cenarios.add("limite_200")
            if alvo == 0 and posicao >= 0:
                cenarios.add("encontra_zero")
        self.assertEqual(cenarios, {
            "vazio", "unitario_presente", "unitario_ausente", "inicio", "meio",
            "fim", "ausente", "negativos_e_zero", "repetidos", "limite_200",
            "encontra_zero",
        })

    def test_k06_entradas_e_tolerancia(self):
        self.assertEqual(
            sorted(int(caso["entrada"]) for caso in self.k06),
            [1, 2, 3, 4, 5, 6, 8, 10, 15, 20],
        )
        for caso in self.k06:
            with self.subTest(caso=caso["id"]):
                self.assertRegex(caso["entrada"], r"\A(?:[1-9]|1[0-9]|20)\n\Z")
                self.assertEqual(caso["tipo_comparacao"], "float")
                self.assertIsInstance(caso["saida_esperada"], str)
                self.assertTrue(math.isfinite(float(caso["saida_esperada"])))
                self.assertEqual(caso["tolerancia_absoluta"], 1e-9)

    def test_k06_referencias_independentes_por_soma_parcial(self):
        for caso in self.k06:
            with self.subTest(caso=caso["id"]):
                n = int(caso["entrada"])
                # Oráculo aritmético dos dados; não é solução recursiva do exercício.
                soma = Fraction(0)
                for k in range(n):
                    soma += Fraction((-1) ** k, math.factorial(2 * k))
                with localcontext() as contexto:
                    contexto.prec = 80
                    referencia = Decimal(soma.numerator) / Decimal(soma.denominator)
                    armazenado = Decimal(str(caso["saida_esperada"]))
                    self.assertLess(abs(armazenado - referencia), Decimal("1e-16"))


if __name__ == "__main__":
    unittest.main()
