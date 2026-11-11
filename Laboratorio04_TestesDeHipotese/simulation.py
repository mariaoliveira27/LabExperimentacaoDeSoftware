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
    type_i_error(params, n_sims=10_000, alpha=0.05, rng=None): force delta=0
        and return each test's rejection_rate, mc_se, ci_low and ci_high.
    power_curve(params, deltas=DEFAULT_DELTAS, n_sims=10_000, alpha=0.05,
        rng=None): return points with delta and summaries for both tests.
    Scenario(name, description, params): immutable scenario configuration.
    build_scenarios(base_params): return the seven reference/stress scenarios.
    run_scenarios(scenarios, deltas=DEFAULT_DELTAS, n_sims=10_000,
        alpha=0.05, rng=None): return tidy records, including delta=0 for Q1.
    run_all(n_sims=10_000, alpha=0.05, rng=None): dashboard entrypoint
        returning one record per (scenario, test, delta), with scenario,
        test, delta,
        n_a, n_b, alpha, n_sims, rejection_rate, ci_low and ci_high. Rates and
        interval bounds are proportions, not percentages. Filter delta=0 for
        G3; use all rows for G4. This does not modify or launch the dashboard.
    to_dataframe(records): convert tidy records using the existing pandas
        dependency, preserving the same columns for an empty record list.

Random functions create a generator seeded with 42 when no generator is given.
Scenario streams are spawned from a shared root and keyed by scenario name,
so reordering or adding scenarios leaves existing results unchanged when the
root starts in the same state. Delta is a log-location shift for lognormal
data and a mean shift in original units for normal/contaminated normal data;
it is not standardized when sigma differs from 1. For contaminated normal,
sigma is the base component scale; delta is not standardized by the mixture
standard deviation, even when sigma=1. Confidence intervals are 95% normal
approximations to Monte Carlo uncertainty, clipped to [0, 1].
No real sample is loaded or calibrated automatically: run_all retains the
repository's illustrative lognormal baseline (median=10, sigma=1, n=30).
Legacy simulate_q1/q2/q3 interfaces and their original scenarios are retained.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    import pandas as pd


# Q1 (#95): Monte Carlo interval configuration.
NORMAL_95_CRITICAL_VALUE: float = 1.96

# Q2 (#96): effects retain the Sprint 1 distribution-specific units.
DEFAULT_DELTAS: tuple[float, ...] = (0.0, 0.2, 0.5, 0.8, 1.2, 1.5)

# Q3 (#97): contamination and dashboard record schema.
OUTLIER_PROPORTION: float = 0.10
OUTLIER_SCALE_FACTOR: float = 10.0
RECORD_COLUMNS: tuple[str, ...] = (
    "scenario", "test", "delta", "n_a", "n_b", "alpha", "n_sims",
    "rejection_rate", "ci_low", "ci_high",
)


@dataclass(frozen=True)
class SimParams:
    """Describe the two synthetic distributions and their sample sizes.

    For lognormal groups, median_a is the median of A, sigma is the standard
    deviation on the log scale, and mu_b = log(median_a) + delta. For normal
    groups, median_a is the mean of A, sigma is the standard deviation, and
    mean_b = median_a + delta. Contaminated normal groups share these means,
    with OUTLIER_PROPORTION drawn at OUTLIER_SCALE_FACTOR times sigma, their
    base component scale rather than the mixture's standard deviation.
    Both groups share the same scale/mixture. A zero delta makes their
    distributions equal. Delta is not standardized when sigma != 1, nor by
    the contaminated mixture's standard deviation even when sigma=1.
    """

    dist: Literal["lognormal", "normal", "contaminated_normal"] = "lognormal"
    median_a: float = 10.0
    sigma: float = 1.0
    n_a: int = 30
    n_b: int = 30
    delta: float = 0.0

    def __post_init__(self) -> None:
        if self.dist not in ("lognormal", "normal", "contaminated_normal"):
            raise ValueError(
                "dist must be 'lognormal', 'normal' or 'contaminated_normal'"
            )
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
    if params.dist == "contaminated_normal":
        return (
            _draw_contaminated_normal(
                rng, params.median_a, params.sigma, size_a
            ),
            _draw_contaminated_normal(
                rng, params.median_a + params.delta, params.sigma, size_b
            ),
        )
    return (
        rng.normal(params.median_a, params.sigma, size_a),
        rng.normal(params.median_a + params.delta, params.sigma, size_b),
    )


# Q3 (#97): a symmetric mixture changes tails without shifting the null mean.
def _draw_contaminated_normal(
    rng: np.random.Generator,
    mean: float,
    sigma: float,
    size: int | tuple[int, int],
) -> np.ndarray:
    """Draw 90% N(mean, sigma) and 10% N(mean, 10*sigma)."""
    contaminated = rng.random(size) < OUTLIER_PROPORTION
    scales = np.where(contaminated, sigma * OUTLIER_SCALE_FACTOR, sigma)
    return rng.normal(mean, scales)


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


# Q1 (#95): empirical Type I error and Monte Carlo uncertainty.
def _rate_summary(rate: float, n_sims: int) -> dict[str, float]:
    """Summarize a rejection proportion using a 95% normal interval."""
    mc_se = float(np.sqrt(rate * (1 - rate) / n_sims))
    margin = NORMAL_95_CRITICAL_VALUE * mc_se
    return {
        "rejection_rate": rate,
        "mc_se": mc_se,
        "ci_low": max(0.0, rate - margin),
        "ci_high": min(1.0, rate + margin),
    }


def _simulation_summary(
    result: dict[str, Any], n_sims: int
) -> dict[str, dict[str, float]]:
    return {
        "welch": _rate_summary(result["reject_rate_welch"], n_sims),
        "mann_whitney": _rate_summary(result["reject_rate_mw"], n_sims),
    }


def type_i_error(
    params: SimParams,
    n_sims: int = 10_000,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> dict[str, dict[str, float]]:
    """Force delta=0 and estimate each test's Type I error and MC uncertainty.

    Return rejection_rate, mc_se, ci_low and ci_high per test. The interval
    is rate +/- 1.96*sqrt(rate*(1-rate)/n_sims), clipped to [0, 1]. Delta's
    log-scale/mean-shift units do not affect the identical-distribution null.
    """
    result = simulate(replace(params, delta=0.0), n_sims, alpha, rng)
    return _simulation_summary(result, n_sims)


# Q2 (#96): power at configurable effects, including Q1 at delta=0.
def _validate_deltas(deltas: Sequence[float]) -> tuple[float, ...]:
    effects = tuple(float(delta) for delta in deltas)
    if not effects or not all(np.isfinite(delta) for delta in effects):
        raise ValueError("deltas must contain finite effects")
    if len(set(effects)) != len(effects):
        raise ValueError("deltas must be unique")
    return effects


def power_curve(
    params: SimParams,
    deltas: Sequence[float] = DEFAULT_DELTAS,
    n_sims: int = 10_000,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> list[dict[str, Any]]:
    """Return delta and both tests' rate/MC summaries for each effect.

    Delta shifts log location for lognormal data and the mean in original
    units for normal/contaminated normal data. It is not standardized when
    sigma != 1; for contaminated normal it is never standardized by the
    mixture's standard deviation. With the same initial generator state, a
    first delta=0 exactly reproduces type_i_error. Subsequent points use
    fresh datasets.
    """
    effects = _validate_deltas(deltas)
    generator = rng if rng is not None else np.random.default_rng(42)
    points = []
    for delta in effects:
        if delta == 0:
            summaries = type_i_error(params, n_sims, alpha, generator)
        else:
            result = simulate(
                replace(params, delta=delta), n_sims, alpha, generator
            )
            summaries = _simulation_summary(result, n_sims)
        points.append({"delta": delta, **summaries})
    return points


# Q3 (#97): assumption scenarios, stable child streams and tidy results.
@dataclass(frozen=True)
class Scenario:
    """Name, describe and configure one simulation scenario."""

    name: str
    description: str
    params: SimParams


def build_scenarios(base_params: SimParams) -> list[Scenario]:
    """Build seven scenarios around the repository's illustrative baseline.

    Normal reference and small-n scenarios share sigma=1 and differ only
    in sample size. Outliers use the same reference location/base scale.
    Real-data-like parameters are supplied, not fitted by this function.
    """
    base = replace(base_params, n_a=30, n_b=30, delta=0.0)
    normal = replace(base, dist="normal", sigma=1.0)
    return [
        Scenario(
            "baseline_normal", "Normal reference, n=30, sigma=1.", normal
        ),
        Scenario(
            "real_data_like", "Supplied illustrative baseline, n=30.", base
        ),
        Scenario(
            "skewed_sigma_1_5", "Severe lognormal skewness, sigma=1.5.",
            replace(base, dist="lognormal", sigma=1.5),
        ),
        Scenario(
            "skewed_sigma_2_0", "Severe lognormal skewness, sigma=2.0.",
            replace(base, dist="lognormal", sigma=2.0),
        ),
        Scenario(
            "outliers", "Normal mixture: 10% at 10 times the base scale.",
            replace(normal, dist="contaminated_normal"),
        ),
        Scenario(
            "small_n_10", "Normal reference with only n=10 per group.",
            replace(normal, n_a=10, n_b=10),
        ),
        Scenario(
            "small_n_15", "Normal reference with only n=15 per group.",
            replace(normal, n_a=15, n_b=15),
        ),
    ]


def _scenario_generator(
    root_entropy: np.ndarray, name: str
) -> np.random.Generator:
    """Spawn a child keyed by name, independent of list position or length."""
    digest = sha256(name.encode("utf-8")).digest()
    name_key = tuple(int(word) for word in np.frombuffer(digest, dtype="<u4"))
    sequence = np.random.SeedSequence(root_entropy, spawn_key=name_key)
    return np.random.default_rng(sequence.spawn(1)[0])


def run_scenarios(
    scenarios: Sequence[Scenario],
    deltas: Sequence[float] = DEFAULT_DELTAS,
    n_sims: int = 10_000,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> list[dict[str, Any]]:
    """Run Q1/Q2 per scenario and return one row per scenario/test/delta.

    Prepend delta=0 if omitted, so Q1 is always present without duplicate
    null simulations. Name-keyed SeedSequence children keep existing
    scenarios unchanged when others are added or reordered, given the same
    initial root state. Scenario names must be unique. Delta retains the
    distribution-specific units documented in power_curve.
    """
    _validate_alpha(alpha)
    if isinstance(n_sims, bool) or not isinstance(n_sims, int) or n_sims < 1:
        raise ValueError("n_sims must be a positive integer")
    effects = _validate_deltas(deltas)
    if 0.0 not in effects:
        effects = (0.0, *effects)
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("scenario names must be unique")
    generator = rng if rng is not None else np.random.default_rng(42)
    root_entropy = generator.integers(0, 2**32, size=4, dtype=np.uint32)
    records = []
    for scenario in scenarios:
        points = power_curve(
            scenario.params, effects, n_sims, alpha,
            _scenario_generator(root_entropy, scenario.name),
        )
        for point in points:
            for test in ("welch", "mann_whitney"):
                summary = point[test]
                records.append({
                    "scenario": scenario.name,
                    "test": test,
                    "delta": point["delta"],
                    "n_a": scenario.params.n_a,
                    "n_b": scenario.params.n_b,
                    "alpha": alpha,
                    "n_sims": n_sims,
                    "rejection_rate": summary["rejection_rate"],
                    "ci_low": summary["ci_low"],
                    "ci_high": summary["ci_high"],
                })
    return records


def run_all(
    n_sims: int = 10_000,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> list[dict[str, Any]]:
    """Return tidy G3/G4 records for all seven scenarios and default effects.

    Keep this dashboard-facing signature stable. The real-data-like base is
    the repository placeholder, not a fitted empirical model. See the module
    docstring for record keys and the distribution-specific units of delta.
    """
    return run_scenarios(
        build_scenarios(SimParams()), n_sims=n_sims, alpha=alpha, rng=rng
    )


def to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert records to the dashboard schema using existing pandas."""
    import pandas as pd

    return pd.DataFrame.from_records(records, columns=RECORD_COLUMNS)


# Legacy dashboard-facing helpers: preserve their signatures and results.
def simulate_q1(
    params: SimParams | None = None,
    n_sims: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute Q1: simulate 10,000 datasets under H0 and measure Type I error rate.

    Returns the rejection proportion and 95% binomial confidence margin.
    Expected result is approximately 5% for calibrated tests.
    """
    p = params if params is not None else SimParams(delta=0.0)
    if p.delta != 0.0:
        p = replace(p, delta=0.0)

    rng = np.random.default_rng(seed)
    sim_res = simulate(p, n_sims=n_sims, alpha=alpha, rng=rng)

    rate_w = sim_res["reject_rate_welch"]
    rate_mw = sim_res["reject_rate_mw"]

    se_w = 1.96 * np.sqrt(rate_w * (1 - rate_w) / n_sims)
    se_mw = 1.96 * np.sqrt(rate_mw * (1 - rate_mw) / n_sims)

    return {
        "question": "Q1: Erro Tipo I sob H0 verdadeira",
        "n_sims": n_sims,
        "alpha": alpha,
        "params": p,
        "rate_welch": rate_w,
        "rate_mw": rate_mw,
        "margin_welch": se_w,
        "margin_mw": se_mw,
        "welch_close_to_alpha": bool(abs(rate_w - alpha) <= 0.015),
        "mw_close_to_alpha": bool(abs(rate_mw - alpha) <= 0.015),
    }


def simulate_q2(
    effects: list[float] | None = None,
    base_params: SimParams | None = None,
    n_sims: int = 2_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute Q2: simulate power curves for increasing effect sizes."""
    _validate_alpha(alpha)
    deltas = effects if effects is not None else [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5]
    base = base_params if base_params is not None else SimParams()

    rng = np.random.default_rng(seed)
    power_welch = []
    power_mw = []

    for d in deltas:
        p = replace(base, delta=d)
        res = simulate(p, n_sims=n_sims, alpha=alpha, rng=rng)
        power_welch.append(float(res["reject_rate_welch"]))
        power_mw.append(float(res["reject_rate_mw"]))

    return {
        "question": "Q2: Curvas de Poder com efeitos crescentes",
        "n_sims_per_point": n_sims,
        "alpha": alpha,
        "deltas": deltas,
        "power_welch": power_welch,
        "power_mw": power_mw,
    }


def simulate_q3(
    n_sims: int = 2_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute Q3: evaluate behavior when parametric assumptions are violated.

    Violations tested:
    1. Extreme skewness (lognormal with sigma=1.6)
    2. Outlier contamination (10% extreme multipliers)
    3. Small sample size (N=12)
    """
    _validate_alpha(alpha)
    rng = np.random.default_rng(seed)
    deltas = [0.0, 0.5, 1.0]

    scenarios = {
        "assimetria_extrema": {
            "nome": "Assimetria Extrema (σ=1.6)",
            "fn": lambda r, d: (
                r.lognormal(mean=np.log(10), sigma=1.6, size=(n_sims, 30)),
                r.lognormal(mean=np.log(10) + d, sigma=1.6, size=(n_sims, 30)),
            ),
        },
        "amostra_pequena": {
            "nome": "Amostra Pequena (N=12)",
            "fn": lambda r, d: (
                r.lognormal(mean=np.log(10), sigma=1.0, size=(n_sims, 12)),
                r.lognormal(mean=np.log(10) + d, sigma=1.0, size=(n_sims, 12)),
            ),
        },
        "outliers": {
            "nome": "Contaminação por Outliers (10%)",
            "fn": lambda r, d: _draw_with_outliers(r, n_sims, 30, d),
        },
    }

    results = {}
    for key, sc in scenarios.items():
        welch_rates = []
        mw_rates = []
        for d in deltas:
            a, b = sc["fn"](rng, d)
            w = stats.ttest_ind(a, b, axis=1, equal_var=False)
            mw = stats.mannwhitneyu(a, b, axis=1, alternative="two-sided")
            welch_rates.append(float(np.mean(w.pvalue < alpha)))
            mw_rates.append(float(np.mean(mw.pvalue < alpha)))

        results[key] = {
            "nome": sc["nome"],
            "deltas": deltas,
            "welch_rates": welch_rates,
            "mw_rates": mw_rates,
            "type1_welch": welch_rates[0],
            "type1_mw": mw_rates[0],
        }

    return {
        "question": "Q3: Violação de Pressupostos Paramétricos",
        "n_sims": n_sims,
        "alpha": alpha,
        "scenarios": results,
    }


def _draw_with_outliers(
    rng: np.random.Generator,
    n_sims: int,
    n: int,
    delta: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw lognormal samples with 10% outlier contamination."""
    a = rng.lognormal(mean=np.log(10), sigma=1.0, size=(n_sims, n))
    b = rng.lognormal(mean=np.log(10) + delta, sigma=1.0, size=(n_sims, n))
    mask_a = rng.random(size=(n_sims, n)) < 0.10
    mask_b = rng.random(size=(n_sims, n)) < 0.10
    a[mask_a] *= 8.0
    b[mask_b] *= 8.0
    return a, b


# Q3 (#97): plain-text summaries for all scenarios and both alpha levels.
def _print_summary(records: list[dict[str, Any]]) -> None:
    """Print Type I error with MC uncertainty, then power at every delta."""
    if not records:
        return
    print(f"\nalpha={records[0]['alpha']:.2f}; n_sims={records[0]['n_sims']}")
    print("Q1: Type I error (delta=0); MC SE and 95% normal interval")
    print(f"{'scenario':<20} {'test':<13} {'rate':>7} {'MC SE':>7}  95% CI")
    for row in records:
        if row["delta"] == 0:
            rate = row["rejection_rate"]
            mc_se = np.sqrt(rate * (1 - rate) / row["n_sims"])
            print(
                f"{row['scenario']:<20} {row['test']:<13} {rate:7.2%} "
                f"{mc_se:7.2%}  [{row['ci_low']:.2%}, {row['ci_high']:.2%}]"
            )
    print("Q2/Q3: rejection rates by delta (delta=0 is Type I error)")
    deltas = tuple(dict.fromkeys(row["delta"] for row in records))
    groups = tuple(dict.fromkeys(
        (row["scenario"], row["test"]) for row in records
    ))
    rates = {
        (row["scenario"], row["test"], row["delta"]): row["rejection_rate"]
        for row in records
    }
    columns = " ".join(f"{delta:>7.1f}" for delta in deltas)
    print(f"{'scenario':<20} {'test':<13} {columns}")
    for scenario, test in groups:
        values = " ".join(
            f"{rates[scenario, test, delta]:7.2%}" for delta in deltas
        )
        print(f"{scenario:<20} {test:<13} {values}")


if __name__ == "__main__":
    print("LAB 04: Q1, Q2 and Q3 Monte Carlo simulations")
    print("Illustrative baseline: lognormal, median=10, sigma=1, n=30.")
    print("Delta: log shift for lognormal; mean shift for normal mixtures.")
    print("Delta is not standardized when sigma != 1.")
    print("For contaminated normal, delta is not standardized by mixture SD.")
    print("Small normal samples isolate sample size; normality is preserved.")
    for significance in (0.05, 0.01):
        _print_summary(run_all(alpha=significance))

