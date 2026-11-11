"""Behavioral checks for the Lab 04 simulation engine."""

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
from scipy import stats

try:
    import pytest
except ImportError:
    class _Approx:
        def __init__(self, expected, rel=1e-5, abs=1e-8):
            self.expected = expected
            self.rel = rel
            self.abs = abs

        def __eq__(self, actual):
            return bool(np.isclose(actual, self.expected, rtol=self.rel, atol=self.abs))

        def __repr__(self):
            return f"approx({self.expected})"

    class _PytestMock:
        approx = _Approx

    pytest = _PytestMock()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulation import (
    DEFAULT_DELTAS,
    SimParams,
    power_curve,
    type_i_error,
    generate_groups,
    interpret_example,
    run_tests,
    simulate,
    simulate_q1,
    simulate_q2,
    simulate_q3,
)


def test_generate_groups_sizes_and_default_seed() -> None:
    params = SimParams(n_a=17, n_b=23)

    first_a, first_b = generate_groups(params)
    second_a, second_b = generate_groups(params)

    assert first_a.shape == (17,)
    assert first_b.shape == (23,)
    np.testing.assert_array_equal(first_a, second_a)
    np.testing.assert_array_equal(first_b, second_b)


def test_simulate_same_seed_produces_identical_results() -> None:
    params = SimParams(n_a=12, n_b=15, delta=0.5)

    first = simulate(params, n_sims=100, rng=np.random.default_rng(42))
    second = simulate(params, n_sims=100, rng=np.random.default_rng(42))

    for key in ("p_values_welch", "p_values_mw", "stat_welch", "stat_mw"):
        np.testing.assert_array_equal(first[key], second[key])
    assert first["reject_rate_welch"] == second["reject_rate_welch"]
    assert first["reject_rate_mw"] == second["reject_rate_mw"]


def test_normal_null_rejection_rates_are_near_alpha() -> None:
    params = SimParams(dist="normal", n_a=30, n_b=30, delta=0.0)

    result = simulate(params, n_sims=10_000)

    assert 0.04 <= result["reject_rate_welch"] <= 0.06
    assert 0.04 <= result["reject_rate_mw"] <= 0.06
    for key in ("p_values_welch", "p_values_mw", "stat_welch", "stat_mw"):
        assert result[key].shape == (10_000,)


def test_run_tests_statistics_and_return_keys() -> None:
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([2.0, 3.0, 4.0, 6.0, 8.0])

    result = run_tests(a, b, alpha=0.10, delta=0.5)

    assert {"welch", "mann_whitney", "alpha", "delta"} <= result.keys()
    assert {"statistic", "p_value", "rejected", "df"} <= result["welch"].keys()
    assert {"statistic", "p_value", "rejected", "u", "z_score"} <= result[
        "mann_whitney"
    ].keys()
    welch = stats.ttest_ind(a, b, equal_var=False)
    mann_whitney = stats.mannwhitneyu(a, b, alternative="two-sided")
    assert result["welch"]["statistic"] == pytest.approx(welch.statistic)
    assert result["welch"]["p_value"] == pytest.approx(welch.pvalue)
    var_a, var_b = np.var(a, ddof=1) / len(a), np.var(b, ddof=1) / len(b)
    expected_df = (var_a + var_b) ** 2 / (
        var_a**2 / (len(a) - 1) + var_b**2 / (len(b) - 1)
    )
    assert result["welch"]["df"] == pytest.approx(expected_df)
    assert result["mann_whitney"]["u"] == pytest.approx(mann_whitney.statistic)
    assert result["mann_whitney"]["statistic"] == pytest.approx(mann_whitney.statistic)
    assert result["mann_whitney"]["p_value"] == pytest.approx(mann_whitney.pvalue)
    assert result["alpha"] == 0.10
    assert result["delta"] == 0.5
    for test in (result["welch"], result["mann_whitney"]):
        assert isinstance(test["rejected"], bool)
        assert test["rejected"] == (test["p_value"] < 0.10)


def test_mann_whitney_z_corrects_variance_for_ties() -> None:
    a = np.array([1.0, 2.0, 2.0, 4.0])
    b = np.array([2.0, 3.0, 4.0, 4.0, 5.0])
    result = run_tests(a, b)["mann_whitney"]

    n_a, n_b = len(a), len(b)
    n = n_a + n_b
    _, counts = np.unique(np.concatenate((a, b)), return_counts=True)
    tie_term = np.sum(counts**3 - counts)
    variance = n_a * n_b / 12 * (n + 1 - tie_term / (n * (n - 1)))
    expected_z = (result["u"] - n_a * n_b / 2) / np.sqrt(variance)
    assert result["z_score"] == pytest.approx(expected_z)


def test_interpretation_uses_known_truth_and_selected_alpha() -> None:
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([11.0, 12.0, 13.0, 14.0, 15.0])
    unknown = interpret_example(run_tests(a, b))
    null = interpret_example(run_tests(a, b, alpha=0.10, delta=0.0))
    effect = interpret_example(run_tests(a, b, alpha=0.10, delta=1.0))

    assert "alfa = 0.1" in null
    assert "falso positivo" in null.lower()
    assert "corret" in effect.lower()
    assert "desconhecid" in unknown.lower()


def test_simulate_q1_type1_error_rate() -> None:
    res = simulate_q1(n_sims=500, alpha=0.05, seed=42)
    assert "rate_welch" in res
    assert "rate_mw" in res
    assert 0.01 <= res["rate_welch"] <= 0.08
    assert 0.02 <= res["rate_mw"] <= 0.08


def test_simulate_q2_power_curve_monotonicity() -> None:
    deltas = [0.0, 0.4, 0.8, 1.2]
    res = simulate_q2(effects=deltas, n_sims=200, alpha=0.05, seed=42)
    pw = res["power_welch"]
    pmw = res["power_mw"]
    assert len(pw) == len(deltas)
    assert len(pmw) == len(deltas)
    # Power should increase with effect size
    assert pw[-1] > pw[0]
    assert pmw[-1] > pmw[0]
    assert pmw[-1] >= 0.80


def test_simulate_q3_violations_structure() -> None:
    res = simulate_q3(n_sims=100, alpha=0.05, seed=42)
    assert "scenarios" in res
    sc = res["scenarios"]
    for k in ("assimetria_extrema", "amostra_pequena", "outliers"):
        assert k in sc
        assert "type1_welch" in sc[k]
        assert "type1_mw" in sc[k]


# Issue #95: Type I error and Monte Carlo uncertainty.


def test_type_i_error_forces_null_and_reports_uncertainty() -> None:
    params = SimParams(dist="normal", delta=1.5)
    n_sims = 2_000

    result = type_i_error(params, n_sims=n_sims)
    expected = simulate(replace(params, delta=0.0), n_sims=n_sims)

    assert params.delta == 1.5
    for test, rate_key in (
        ("welch", "reject_rate_welch"),
        ("mann_whitney", "reject_rate_mw"),
    ):
        summary = result[test]
        rate = summary["rejection_rate"]
        expected_se = np.sqrt(rate * (1 - rate) / n_sims)
        assert rate == expected[rate_key]
        assert 0.04 <= rate <= 0.06
        assert summary["mc_se"] == pytest.approx(expected_se)
        assert summary["ci_low"] == pytest.approx(
            max(0.0, rate - 1.96 * expected_se)
        )
        assert summary["ci_high"] == pytest.approx(
            min(1.0, rate + 1.96 * expected_se)
        )
        assert 0.0 <= summary["ci_low"] <= rate
        assert rate <= summary["ci_high"] <= 1.0


def test_type_i_error_reproduces_seed_and_respects_alpha() -> None:
    params = SimParams(dist="normal")
    first = type_i_error(
        params, n_sims=2_000, rng=np.random.default_rng(42)
    )
    second = type_i_error(
        params, n_sims=2_000, rng=np.random.default_rng(42)
    )
    strict = type_i_error(
        params, n_sims=2_000, alpha=0.01, rng=np.random.default_rng(42)
    )
    expected = simulate(
        params, n_sims=2_000, alpha=0.01, rng=np.random.default_rng(42)
    )

    assert first == second
    for test, rate_key in (
        ("welch", "reject_rate_welch"),
        ("mann_whitney", "reject_rate_mw"),
    ):
        assert strict[test]["rejection_rate"] == expected[rate_key]
        assert strict[test]["rejection_rate"] < first[test]["rejection_rate"]


# Issue #96: Power curves with configurable effects and significance levels.


def test_power_curve_zero_effect_matches_type_i_error_exactly() -> None:
    params = SimParams(dist="normal", delta=0.8)
    null = type_i_error(
        params, n_sims=2_000, rng=np.random.default_rng(42)
    )
    points = power_curve(
        params, n_sims=2_000, rng=np.random.default_rng(42)
    )

    assert tuple(point["delta"] for point in points) == DEFAULT_DELTAS
    for test in ("welch", "mann_whitney"):
        assert points[0][test] == null[test]
        assert 0.04 <= points[0][test]["rejection_rate"] <= 0.06


def test_power_curve_increases_with_monte_carlo_tolerance() -> None:
    points = power_curve(SimParams(dist="normal"), n_sims=2_000)

    for test in ("welch", "mann_whitney"):
        rates = [point[test]["rejection_rate"] for point in points]
        assert rates[-1] > rates[0] + 0.70
        for previous, current in zip(points, points[1:]):
            tolerance = 3 * np.sqrt(
                previous[test]["mc_se"] ** 2 + current[test]["mc_se"] ** 2
            )
            assert (
                current[test]["rejection_rate"]
                >= previous[test]["rejection_rate"] - tolerance
            )


def test_power_curve_accepts_custom_deltas_and_alpha() -> None:
    deltas = [0.0, 0.3, 1.0]
    params = SimParams(dist="normal")
    usual = power_curve(params, deltas=deltas, n_sims=200, alpha=0.05)
    strict = power_curve(params, deltas=deltas, n_sims=200, alpha=0.01)

    assert [point["delta"] for point in usual] == deltas
    assert [point["delta"] for point in strict] == deltas
    for usual_point, strict_point in zip(usual, strict):
        for test in ("welch", "mann_whitney"):
            assert (
                strict_point[test]["rejection_rate"]
                <= usual_point[test]["rejection_rate"]
            )


def test_simulate_q2_rejects_invalid_alpha_with_empty_effects() -> None:
    for alpha in (-0.1, 0.0, 1.0, 1.1, float("nan")):
        with np.testing.assert_raises(ValueError):
            simulate_q2(effects=[], n_sims=10, alpha=alpha)


if __name__ == "__main__":
    tests = [
        test_generate_groups_sizes_and_default_seed,
        test_simulate_same_seed_produces_identical_results,
        test_normal_null_rejection_rates_are_near_alpha,
        test_run_tests_statistics_and_return_keys,
        test_mann_whitney_z_corrects_variance_for_ties,
        test_interpretation_uses_known_truth_and_selected_alpha,
        test_simulate_q1_type1_error_rate,
        test_simulate_q2_power_curve_monotonicity,
        test_simulate_q3_violations_structure,
        test_type_i_error_forces_null_and_reports_uncertainty,
        test_type_i_error_reproduces_seed_and_respects_alpha,
        test_power_curve_zero_effect_matches_type_i_error_exactly,
        test_power_curve_increases_with_monte_carlo_tolerance,
        test_power_curve_accepts_custom_deltas_and_alpha,
        test_simulate_q2_rejects_invalid_alpha_with_empty_effects,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            raise
    print(f"\nAll {passed} tests passed successfully!")

