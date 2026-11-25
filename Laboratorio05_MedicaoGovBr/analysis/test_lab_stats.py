"""Testes unitários de lab_stats. Rodar com: python -m unittest discover -s analysis"""
import math
import unittest

from lab_stats import cliffs_delta, cliffs_magnitude, epsilon_squared, holm, paired_rank_biserial


class HolmTest(unittest.TestCase):
    def test_sequencial_e_monotono(self):
        # p ordenados: 0,01; 0,02; 0,04 -> 0,03; 0,04; 0,04 (monótono), devolvidos na ordem de entrada.
        self.assertEqual([round(v, 6) for v in holm([0.04, 0.01, 0.02])], [0.04, 0.03, 0.04])

    def test_limita_em_um_e_mantem_nan(self):
        out = holm([0.6, float("nan"), 0.5])
        self.assertEqual(out[0], 1.0)
        self.assertTrue(math.isnan(out[1]))
        self.assertEqual(out[2], 1.0)


class TamanhoDeEfeitoTest(unittest.TestCase):
    def test_epsilon_quadrado_igual_a_h_sobre_n_menos_1(self):
        self.assertAlmostEqual(epsilon_squared(9.0, 31), 9.0 / 30)
        self.assertTrue(math.isnan(epsilon_squared(1.0, 1)))

    def test_delta_de_cliff(self):
        self.assertEqual(cliffs_delta([3, 4], [1, 2]), 1.0)
        self.assertEqual(cliffs_delta([1, 2], [3, 4]), -1.0)
        self.assertEqual(cliffs_delta([1, 2], [1, 2]), 0.0)
        # pares: (1,1)=, (1,3)<, (5,1)>, (5,3)> -> (2 - 1) / 4
        self.assertEqual(cliffs_delta([1, 5], [1, 3]), 0.25)

    def test_limiares_do_delta_de_cliff(self):
        self.assertEqual(cliffs_magnitude(0.1), "negligible")
        self.assertEqual(cliffs_magnitude(-0.2), "small")
        self.assertEqual(cliffs_magnitude(0.4), "medium")
        self.assertEqual(cliffs_magnitude(0.474), "large")

    def test_rank_biserial_pareada(self):
        self.assertEqual(paired_rank_biserial([1, 2, 3]), 1.0)
        self.assertEqual(paired_rank_biserial([-1, -2, 0]), -1.0)
        # postos de |d|: 1 -> 1, 2 -> 2, 3 -> 3; positivos 1 + 3 = 4, negativo 2 -> (4 - 2) / 6
        self.assertAlmostEqual(paired_rank_biserial([1, -2, 3]), 2 / 6)
        self.assertTrue(math.isnan(paired_rank_biserial([0, 0])))


if __name__ == "__main__":
    unittest.main()


class BootstrapTest(unittest.TestCase):
    def test_reprodutivel_e_contem_a_media(self):
        import numpy as np
        from lab_stats import bootstrap_ci
        x = np.arange(50, dtype=float)
        a = bootstrap_ci(lambda i: x[i].mean(), len(x), np.random.default_rng(1), reps=2000)
        b = bootstrap_ci(lambda i: x[i].mean(), len(x), np.random.default_rng(1), reps=2000)
        self.assertEqual(a, b)
        self.assertLess(a[0], 24.5)
        self.assertGreater(a[1], 24.5)

    def test_cluster_reamostra_grupos_inteiros(self):
        import numpy as np
        from lab_stats import bootstrap_ci
        groups = np.repeat([0, 1, 2], 4)
        sizes = []
        bootstrap_ci(lambda i: sizes.append(len(i)) or 0.0, 12, np.random.default_rng(3), reps=50, groups=groups)
        self.assertTrue(all(s == 12 for s in sizes))
