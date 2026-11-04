"""Generate synthetic groups and compare them with two statistical tests.

Public interface:
    SimParams(dist, median_a, sigma, n_a, n_b, delta): distribution parameters.
    generate_groups(params, rng=None): return one pair of NumPy arrays.
    run_tests(a, b, alpha=0.05, *, delta=None): return ``welch`` and
        ``mann_whitney`` dictionaries with ``statistic``, ``p_value`` and
        ``rejected``; Welch also has ``df``, and Mann-Whitney has ``u`` and
        ``z_score``. The result also records ``alpha`` and the optional known
        simulation effect ``delta`` for interpretation.
    simulate(params, n_sims=10_000, alpha=0.05, rng=None): return arrays
        ``p_values_welch``, ``p_values_mw``, ``stat_welch`` and ``stat_mw``,
        plus ``reject_rate_welch`` and ``reject_rate_mw``.
    interpret_example(result): interpret one run_tests result in Portuguese.

Random functions create a generator seeded with 42 when no generator is given.
No data from the real sample is loaded or calibrated automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class SimParams:
    """Describe the two synthetic distributions and their sample sizes.

    For lognormal groups, median_a is the median of A, sigma is the standard
    deviation on the log scale, and mu_b = log(median_a) + delta. For normal
    groups, median_a is the mean of A, sigma is the standard deviation, and
    mean_b = median_a + delta. Both groups share sigma. A zero delta makes
    their distributions equal.
    """

    dist: Literal["lognormal", "normal"] = "lognormal"
    median_a: float = 10.0
    sigma: float = 1.0
    n_a: int = 30
    n_b: int = 30
    delta: float = 0.0

    def __post_init__(self) -> None:
        if self.dist not in ("lognormal", "normal"):
            raise ValueError("dist must be 'lognormal' or 'normal'")
        values = (self.median_a, self.sigma, self.delta)
        if not all(np.isfinite(value) for value in values):
            raise ValueError("distribution parameters must be finite")
        if self.dist == "lognormal" and self.median_a <= 0:
            raise ValueError("median_a must be positive for lognormal data")
        if self.sigma <= 0:
            raise ValueError("sigma must be positive")
        if any(
            isinstance(n, bool) or not isinstance(n, int) or n < 2
            for n in (self.n_a, self.n_b)
        ):
            raise ValueError("sample sizes must be integers of at least 2")


def _validate_alpha(alpha: float) -> None:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")


def _draw_groups(
    params: SimParams, rng: np.random.Generator, n_sims: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    size_a = params.n_a if n_sims is None else (n_sims, params.n_a)
    size_b = params.n_b if n_sims is None else (n_sims, params.n_b)
    if params.dist == "lognormal":
        mu_a = np.log(params.median_a)
        return (
            rng.lognormal(mu_a, params.sigma, size_a),
            rng.lognormal(mu_a + params.delta, params.sigma, size_b),
        )
    return (
        rng.normal(params.median_a, params.sigma, size_a),
        rng.normal(params.median_a + params.delta, params.sigma, size_b),
    )


def generate_groups(
    params: SimParams, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Generate one independent sample for each group."""
    generator = rng if rng is not None else np.random.default_rng(42)
    return _draw_groups(params, generator)


def _mann_whitney_z(a: np.ndarray, b: np.ndarray, u: float) -> float:
    """Standardize U with tie-adjusted variance, without continuity correction.

    SciPy's p-value can use an exact method or continuity correction, so it
    need not correspond exactly to the displayed normal-approximation z.
    """
    n_a, n_b = len(a), len(b)
    _, counts = np.unique(np.concatenate((a, b)), return_counts=True)
    total = n_a + n_b
    tie_term = np.sum(counts**3 - counts) / (total * (total - 1))
    variance = n_a * n_b / 12 * (total + 1 - tie_term)
    if variance <= 0:
        return float("nan")
    return float((u - n_a * n_b / 2) / np.sqrt(variance))


def run_tests(
    a: np.ndarray,
    b: np.ndarray,
    alpha: float = 0.05,
    *,
    delta: float | None = None,
) -> dict[str, Any]:
    """Test one pair of samples; delta records known simulation metadata."""
    _validate_alpha(alpha)
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if any(
        x.ndim != 1 or x.size < 2 or not np.isfinite(x).all() for x in (a, b)
    ):
        raise ValueError("each sample must be a finite 1D array of size >= 2")
    if delta is not None and not np.isfinite(delta):
        raise ValueError("delta must be finite when provided")
    welch = stats.ttest_ind(a, b, equal_var=False)
    mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    if not np.isfinite(welch.pvalue) or not np.isfinite(mw.pvalue):
        raise ValueError("test p-values are undefined for these samples")
    return {
        "welch": {
            "statistic": float(welch.statistic),
            "p_value": float(welch.pvalue),
            "rejected": bool(welch.pvalue < alpha),
            "df": float(welch.df),
        },
        "mann_whitney": {
            "statistic": float(mw.statistic),
            "p_value": float(mw.pvalue),
            "rejected": bool(mw.pvalue < alpha),
            "u": float(mw.statistic),
            "z_score": _mann_whitney_z(a, b, float(mw.statistic)),
        },
        "alpha": alpha,
        "delta": delta,
    }


def simulate(
    params: SimParams,
    n_sims: int = 10_000,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Simulate independent datasets and return test statistics and rates."""
    _validate_alpha(alpha)
    if isinstance(n_sims, bool) or not isinstance(n_sims, int) or n_sims < 1:
        raise ValueError("n_sims must be a positive integer")
    generator = rng if rng is not None else np.random.default_rng(42)
    a, b = _draw_groups(params, generator, n_sims)
    welch = stats.ttest_ind(a, b, axis=1, equal_var=False)
    mw = stats.mannwhitneyu(a, b, axis=1, alternative="two-sided")
    if not np.isfinite(welch.pvalue).all() or not np.isfinite(mw.pvalue).all():
        raise ValueError("some simulated test p-values are undefined")
    return {
        "p_values_welch": welch.pvalue,
        "p_values_mw": mw.pvalue,
        "stat_welch": welch.statistic,
        "stat_mw": mw.statistic,
        "reject_rate_welch": float(np.mean(welch.pvalue < alpha)),
        "reject_rate_mw": float(np.mean(mw.pvalue < alpha)),
    }


def interpret_example(result: dict[str, Any]) -> str:
    """Explain both decisions for a single simulated dataset in Portuguese."""
    alpha = result["alpha"]
    delta = result["delta"]
    sentences = []
    for label, comparison, key in (
        ("Welch", "médias", "welch"),
        ("Mann-Whitney", "postos", "mann_whitney"),
    ):
        test = result[key]
        if not np.isfinite(test["p_value"]):
            sentences.append(
                f"{label} comparou {comparison}, mas o p-valor é indefinido "
                "e não permite uma decisão."
            )
            continue
        decision = "rejeitou" if test["rejected"] else "não rejeitou"
        if delta is None:
            outcome = (
                "a correção da decisão é desconhecida, pois delta não foi "
                "informado"
            )
        elif delta == 0:
            outcome = (
                "um falso positivo" if test["rejected"]
                else "uma decisão correta sob H0"
            )
        else:
            outcome = (
                "uma rejeição correta" if test["rejected"]
                else "um efeito não detectado"
            )
        sentences.append(
            f"{label} comparou {comparison} (p = {test['p_value']:.4g}) "
            f"e {decision} H0 com alfa = {alpha:g}: {outcome}."
        )
    return " ".join(sentences)


if __name__ == "__main__":
    base_params = SimParams()
    for effect in (0.0, 0.5):
        params = replace(base_params, delta=effect)
        group_a, group_b = generate_groups(params)
        print(f"delta = {effect:g}")
        print(interpret_example(run_tests(group_a, group_b, delta=effect)))
    results = simulate(base_params)
    print(f"Welch rejection rate: {results['reject_rate_welch']:.2%}")
    print(f"Mann-Whitney rejection rate: {results['reject_rate_mw']:.2%}")
