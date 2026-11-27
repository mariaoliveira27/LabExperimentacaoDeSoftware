#!/usr/bin/env python3
"""Independent check of the main numbers in analysis/results.md.

    python analysis/check_results.py            # needs only numpy and pandas

It recomputes, straight from data/processed/full.csv and without scipy or the code of analyze.py,
the numbers that docs/conclusoes.md quotes:

  RQ1  Kruskal-Wallis H (tie-corrected), p and epsilon squared, per form factor and metric
  RQ2  Spearman rho between performance and accessibility score, on the per-service medians
  RQ3  mobile vs desktop LCP and performance score, per service medians

and repeats everything without the two services whose LCP element is a cookie banner
(Portal gov.br and Valores a Receber). It is a cross-check of analyze.py, not a replacement:
the Dunn post-hoc, the bootstrap intervals and the Wilcoxon p-values are not recomputed here.
Compare the output with analysis/results.md (sections 5 to 7).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BANNER_SERVICES = ["govbr", "svr-bcb"]


def gamma_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x); the chi-square survival is Q(df/2, H/2)."""
    if x <= 0:
        return 1.0
    log_gamma = math.lgamma(a)
    if x < a + 1:
        ap, total, term = a, 1.0 / a, 1.0 / a
        for _ in range(1000):
            ap += 1
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return 1 - total * math.exp(-x + a * math.log(x) - log_gamma)
    b = x + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = d if abs(d) > 1e-300 else 1e-300
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - log_gamma) * h


def kruskal(frame: pd.DataFrame, column: str) -> tuple[float, float, float]:
    ranks = frame[column].rank(method="average")
    n = len(frame)
    stat = sum(ranks[group.index].sum() ** 2 / len(group) for _, group in frame.groupby("service"))
    stat = 12 / (n * (n + 1)) * stat - 3 * (n + 1)
    ties = frame[column].value_counts()
    stat /= 1 - ((ties**3 - ties).sum()) / (n**3 - n)
    k = frame.service.nunique()
    return stat, gamma_q((k - 1) / 2, stat / 2), stat / (n - 1)


def report(frame: pd.DataFrame, label: str) -> None:
    print(f"== {label} ({frame.service.nunique()} serviços, {len(frame)} execuções)")
    for form_factor in ("mobile", "desktop"):
        part = frame[frame.formFactor == form_factor]
        for column in ("performanceScore", "LCP"):
            h, p, eps = kruskal(part, column)
            print(f"RQ1 Kruskal-Wallis {form_factor:7s} {column:16s} H={h:5.1f}  p={p:.1e}  eps2={eps:.2f}")
    med = frame.groupby(["service", "formFactor"])[["performanceScore", "accessibilityScore", "LCP_s"]].median().unstack()
    for form_factor in ("mobile", "desktop"):
        perf = med[("performanceScore", form_factor)].rank()
        a11y = med[("accessibilityScore", form_factor)].rank()
        print(f"RQ2 Spearman (medianas) {form_factor:7s} rho={perf.corr(a11y):.2f}  n={len(med)}")
    lcp_m, lcp_d = med[("LCP_s", "mobile")], med[("LCP_s", "desktop")]
    perf_diff = med[("performanceScore", "mobile")] - med[("performanceScore", "desktop")]
    print(f"RQ3 LCP mobile > desktop em {int((lcp_m > lcp_d).sum())} de {len(med)}; "
          f"mediana mobile {lcp_m.median():.2f} s, desktop {lcp_d.median():.2f} s, "
          f"mediana das diferenças {(lcp_m - lcp_d).median():.2f} s, mediana das razões {(lcp_m / lcp_d).median():.2f}")
    print(f"RQ3 score mobile < desktop em {int((perf_diff < 0).sum())} de {len(med)}; "
          f"mediana das diferenças {perf_diff.median():.1f} pontos\n")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "processed" / "full.csv"
    runs = pd.read_csv(path)
    runs["LCP_s"] = runs["LCP"] / 1000
    report(runs, "todas as execuções")
    report(runs[~runs.service.isin(BANNER_SERVICES)], "sem Portal gov.br e Valores a Receber (LCP é banner de cookies)")


if __name__ == "__main__":
    main()
