"""Unit tests for lab_stats. Run: python -m unittest discover -s analysis"""
import math
import unittest

from lab_stats import cliffs_delta, cliffs_magnitude, epsilon_squared, holm, paired_rank_biserial


class HolmTest(unittest.TestCase):
    def test_step_down_and_monotone(self):
        # Sorted p: 0.01, 0.02, 0.04 -> 0.03, 0.04, 0.04 (monotone), mapped back to input order.
        self.assertEqual([round(v, 6) for v in holm([0.04, 0.01, 0.02])], [0.04, 0.03, 0.04])

    def test_caps_at_one_and_keeps_nan(self):
        out = holm([0.6, float("nan"), 0.5])
        self.assertEqual(out[0], 1.0)
        self.assertTrue(math.isnan(out[1]))
        self.assertEqual(out[2], 1.0)


class EffectSizeTest(unittest.TestCase):
    def test_epsilon_squared_equals_h_over_n_minus_1(self):
        self.assertAlmostEqual(epsilon_squared(9.0, 31), 9.0 / 30)
        self.assertTrue(math.isnan(epsilon_squared(1.0, 1)))

    def test_cliffs_delta(self):
        self.assertEqual(cliffs_delta([3, 4], [1, 2]), 1.0)
        self.assertEqual(cliffs_delta([1, 2], [3, 4]), -1.0)
        self.assertEqual(cliffs_delta([1, 2], [1, 2]), 0.0)
        # pairs: (1,1)=, (1,3)<, (5,1)>, (5,3)> -> (2 - 1) / 4
        self.assertEqual(cliffs_delta([1, 5], [1, 3]), 0.25)

    def test_cliffs_magnitude_thresholds(self):
        self.assertEqual(cliffs_magnitude(0.1), "negligible")
        self.assertEqual(cliffs_magnitude(-0.2), "small")
        self.assertEqual(cliffs_magnitude(0.4), "medium")
        self.assertEqual(cliffs_magnitude(0.474), "large")

    def test_paired_rank_biserial(self):
        self.assertEqual(paired_rank_biserial([1, 2, 3]), 1.0)
        self.assertEqual(paired_rank_biserial([-1, -2, 0]), -1.0)
        # |d| ranks: 1 -> 1, 2 -> 2, 3 -> 3; positive 1 + 3 = 4, negative 2 -> (4 - 2) / 6
        self.assertAlmostEqual(paired_rank_biserial([1, -2, 3]), 2 / 6)
        self.assertTrue(math.isnan(paired_rank_biserial([0, 0])))


if __name__ == "__main__":
    unittest.main()
