"""Effect sizes and corrections used in docs/proposta.md, section 7.

Kept free of I/O so they can be unit-tested (analysis/test_lab_stats.py).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy.stats import rankdata


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm (1979) step-down adjusted p-values. NaN entries are ignored and stay NaN."""
    p = np.asarray(pvalues, dtype=float)
    adjusted = np.full(p.shape, np.nan)
    idx = np.flatnonzero(~np.isnan(p))
    m = idx.size
    if m == 0:
        return adjusted.tolist()
    order = idx[np.argsort(p[idx], kind="stable")]
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adjusted[i] = running
    return adjusted.tolist()


def epsilon_squared(h: float, n: int) -> float:
    """Kruskal-Wallis effect size: H / ((n^2 - 1) / (n + 1)) (Tomczak & Tomczak, 2014)."""
    if n < 2 or h is None or math.isnan(h):
        return float("nan")
    return h / ((n**2 - 1) / (n + 1))


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """Cliff's delta: P(X > Y) - P(X < Y) over all pairs (Cliff, 1993)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or y.size == 0:
        return float("nan")
    diff = x[:, None] - y[None, :]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / diff.size)


def cliffs_magnitude(delta: float) -> str:
    """Thresholds of Romano et al. (2006)."""
    if delta is None or math.isnan(delta):
        return "n/a"
    d = abs(delta)
    if d < 0.147:
        return "negligible"
    if d < 0.33:
        return "small"
    if d < 0.474:
        return "medium"
    return "large"


def paired_rank_biserial(differences: Sequence[float]) -> float:
    """Matched-pairs rank-biserial correlation, simple difference formula (Kerby, 2014).

    r = (sum of ranks of positive differences - sum of ranks of negative differences) / total
    rank sum. Zero differences are dropped, as in the Wilcoxon signed-rank test; tied absolute
    differences get average ranks.
    """
    d = np.asarray(differences, dtype=float)
    d = d[d != 0]
    if d.size == 0:
        return float("nan")
    ranks = rankdata(np.abs(d))
    total = ranks.sum()
    return float((ranks[d > 0].sum() - ranks[d < 0].sum()) / total)
