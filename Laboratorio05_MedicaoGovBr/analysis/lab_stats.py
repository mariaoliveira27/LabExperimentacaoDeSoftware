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


def bootstrap_ci(stat, n: int, rng: np.random.Generator, reps: int = 10_000, level: float = 0.95,
                 groups: Sequence | None = None) -> tuple[float, float, int]:
    """Intervalo percentil por bootstrap de `stat(idx)`, em que idx são índices reamostrados com reposição.

    Com `groups`, reamostra grupos inteiros (bootstrap por cluster): sorteia grupos com reposição e
    junta todos os índices de cada grupo sorteado. Reamostras em que a estatística dá NaN (por exemplo,
    uma variável constante) são descartadas; o terceiro valor devolvido é quantas foram descartadas.
    """
    if groups is None:
        draws = (rng.integers(0, n, n) for _ in range(reps))
    else:
        g = np.asarray(groups)
        labels = np.unique(g)
        members = [np.flatnonzero(g == lab) for lab in labels]
        draws = (np.concatenate([members[i] for i in rng.integers(0, len(labels), len(labels))]) for _ in range(reps))
    values = np.array([stat(idx) for idx in draws], dtype=float)
    dropped = int(np.isnan(values).sum())
    values = values[~np.isnan(values)]
    if values.size == 0:
        return float("nan"), float("nan"), dropped
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(values, [tail, 100 - tail])
    return float(lo), float(hi), dropped
