"""Tamanhos de efeito e correções usados em docs/proposta.md, seção 7.

Sem leitura ou escrita de arquivos, para poderem ser testados isoladamente (analysis/test_lab_stats.py).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy.stats import rankdata


def holm(pvalues: Sequence[float]) -> list[float]:
    """p-valores ajustados pelo procedimento sequencial de Holm (1979). NaN é ignorado e continua NaN."""
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
    """Tamanho de efeito do Kruskal-Wallis: H / ((n^2 - 1) / (n + 1)) (Tomczak e Tomczak, 2014)."""
    if n < 2 or h is None or math.isnan(h):
        return float("nan")
    return h / ((n**2 - 1) / (n + 1))


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """Delta de Cliff: P(X > Y) - P(X < Y) sobre todos os pares (Cliff, 1993)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or y.size == 0:
        return float("nan")
    diff = x[:, None] - y[None, :]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / diff.size)


def cliffs_magnitude(delta: float) -> str:
    """Limiares de Romano et al. (2006). Os rótulos ficam em inglês porque são valores de coluna."""
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
    """Correlação rank-biserial para dados pareados, pela fórmula da diferença simples (Kerby, 2014).

    r = (soma dos postos das diferenças positivas - soma dos postos das negativas) / soma total dos
    postos. Diferenças zero são descartadas, como no teste de Wilcoxon; diferenças absolutas
    empatadas recebem o posto médio.
    """
    d = np.asarray(differences, dtype=float)
    d = d[d != 0]
    if d.size == 0:
        return float("nan")
    ranks = rankdata(np.abs(d))
    total = ranks.sum()
    return float((ranks[d > 0].sum() - ranks[d < 0].sum()) / total)
