"""Behavioral checks for the Lab 04 simulation engine."""

from pathlib import Path
import sys

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulation import SimParams, generate_groups, interpret_example, run_tests, simulate


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
