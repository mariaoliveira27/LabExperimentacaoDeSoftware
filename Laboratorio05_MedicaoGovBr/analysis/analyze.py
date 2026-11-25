#!/usr/bin/env python3
"""Análise estatística das medições do Lighthouse (docs/proposta.md, seção 7; analysis/results.md).

Lê data/processed/<fase>.csv e os arquivos que o acompanham (_flags, _failures, _lcp_elements,
_executions, _outliers) e grava tabelas CSV, um resumo em markdown e os gráficos.

    python analysis/analyze.py                       # fase full, as duas variantes, com gráficos
    python analysis/analyze.py --phases pilot --out <pasta> --no-figures   # piloto: só confere o script

Variantes (sempre as duas, cada uma em <out>/<variante>/):
    todas          todas as execuções válidas (menos as de --exclude-flags)
    sem-outliers   tira, de cada métrica, os valores fora da cerca de Tukey da célula
                   (data/processed/<fase>_outliers.csv, gerado por scripts/validate-data.mjs)

Outras análises de sensibilidade (rodar de novo com as opções):
    --exclude-flags SLOW_HOST_CPU      padrão; execuções no limiar de CPU lenta do Lighthouse ou abaixo
    --exclude-flags all                tira todas as execuções listadas em <fase>_flags.csv
    --exclude-services govbr,svr-bcb   ex.: serviços cujo elemento LCP é um banner de cookies

Bootstrap com seed fixa (--seed), então a saída é a mesma a cada execução.
Os nomes das tabelas e das colunas ficam em inglês porque são identificadores lidos por código.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import warnings
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy import stats

from lab_stats import (bootstrap_ci, cliffs_delta, cliffs_magnitude, epsilon_squared, holm,
                       paired_rank_biserial)

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
URLS_FILE = ROOT / "data" / "urls.json"

FORM_FACTORS = ["mobile", "desktop"]
METRICS = ["performanceScore", "accessibilityScore", "LCP", "FCP", "TBT", "CLS", "SpeedIndex"]
# Para cada métrica usada na ordenação dos serviços: valor maior é pior?
HIGHER_IS_WORSE = {"performanceScore": False, "accessibilityScore": False, "LCP": True}
KEY = ["block", "service", "formFactor", "run"]
VARIANTS = ["todas", "sem-outliers"]
BOOT_REPS = 10_000


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phases", default="full", help="fases separadas por vírgula (padrão: full)")
    ap.add_argument("--out", help="pasta das tabelas (padrão: analysis/output)")
    ap.add_argument("--figures", help="pasta dos gráficos (padrão: analysis/figures)")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--exclude-flags", default="SLOW_HOST_CPU",
                    help="códigos de <fase>_flags.csv a excluir, separados por vírgula, 'all' ou 'none'")
    ap.add_argument("--exclude-services", default="", help="ids de serviço a deixar de fora, separados por vírgula")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=20261125, help="seed do bootstrap")
    return ap.parse_args()


def quiet(fn, *a, **kw):
    """Roda um teste do SciPy sem os avisos; quem chama confere se o resultado é NaN."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*a, **kw)


# ---------------------------------------------------------------- leitura

def read_csv(phase: str, suffix: str, required: bool) -> pd.DataFrame:
    path = PROCESSED / f"{phase}{suffix}.csv"
    if not path.exists():
        if required:
            sys.exit(f"{path.relative_to(ROOT)} não encontrado; rode antes `node scripts/extract-metrics.mjs --phase {phase}`")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.insert(0, "phase", phase)
    return df


def load(phases: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for name, suffix, required in [("runs", "", True), ("flags", "_flags", False), ("failures", "_failures", False),
                                   ("lcp", "_lcp_elements", False), ("executions", "_executions", False),
                                   ("outliers", "_outliers", False)]:
        frames = [f for f in (read_csv(p, suffix, required) for p in phases) if not f.empty]
        out[name] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Bloco de horário de cada execução: o --session-label da tentativa 'ok' que gerou o arquivo.
    # Sem rótulo (piloto), o bloco é a própria fase.
    ex = out["executions"]
    label = pd.Series(dtype=object)
    if not ex.empty and "sessionLabel" in ex:
        ok = ex[ex["status"] == "ok"].drop_duplicates(["phase", "service", "formFactor", "run"], keep="last")
        label = ok.set_index(["phase", "service", "formFactor", "run"])["sessionLabel"]
    for name in ["runs", "flags", "lcp", "outliers"]:
        df = out[name]
        if df.empty:
            continue
        idx = pd.MultiIndex.from_frame(df[["phase", "service", "formFactor", "run"]])
        lab = label.reindex(idx).to_numpy() if not label.empty else np.full(len(df), np.nan)
        df.insert(1, "block", [l if isinstance(l, str) and l else p for l, p in zip(lab, df["phase"])])
    return out


def select_runs(data: dict, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica as exclusões e devolve (execuções mantidas, execuções excluídas com o motivo)."""
    runs = data["runs"].copy()
    listed = {s["id"] for s in json.loads(URLS_FILE.read_text(encoding="utf-8"))["services"]}
    reasons = pd.Series("", index=runs.index)

    def mark(mask: pd.Series, reason: str) -> None:
        reasons.loc[mask & (reasons == "")] = reason

    mark(~runs["service"].isin(listed), "serviço fora de data/urls.json (trocado)")
    excluded_services = {s for s in args.exclude_services.split(",") if s}
    mark(runs["service"].isin(excluded_services), "--exclude-services")

    flags = data["flags"]
    codes = args.exclude_flags.strip()
    if codes != "none" and not flags.empty:
        selected = flags if codes == "all" else flags[flags["flag"].isin(codes.split(","))]
        per_run = selected.groupby(KEY)["flag"].agg(lambda s: "+".join(sorted(set(s)))).rename("flags")
        joined = runs.join(per_run, on=KEY)
        has_flag = joined["flags"].notna()
        reasons.loc[has_flag & (reasons == "")] = "marcação: " + joined.loc[has_flag & (reasons == ""), "flags"]

    excluded = runs[reasons != ""].assign(reason=reasons[reasons != ""])[KEY + ["reason"]]
    return runs[reasons == ""].reset_index(drop=True), excluded


def apply_variant(runs: pd.DataFrame, outliers: pd.DataFrame, variant: str) -> pd.DataFrame:
    """Na variante sem-outliers, o valor marcado vira NaN só na métrica em que foi marcado."""
    if variant == "todas" or outliers.empty:
        return runs.copy()
    out = runs.copy()
    for m in METRICS:
        o = outliers[outliers["metric"] == m][KEY].assign(_o=True)
        hit = out[KEY].merge(o, on=KEY, how="left")["_o"].fillna(False).to_numpy(bool)
        out.loc[hit, m] = np.nan
    return out


# ---------------------------------------------------------------- estatística descritiva

def describe(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (svc, ff), g in runs.groupby(["service", "formFactor"]):
        for m in METRICS:
            v = g[m].dropna().astype(float)
            rec = dict(service=svc, formFactor=ff, metric=m, n=len(v), median=v.median(),
                       q1=v.quantile(0.25), q3=v.quantile(0.75), mean=v.mean(), sd=v.std(ddof=1),
                       min=v.min(), max=v.max(), shapiro_W=math.nan, shapiro_p=math.nan, note="")
            rec["iqr"] = rec["q3"] - rec["q1"]
            if len(v) < 3:
                rec["note"] = "n < 3: sem Shapiro-Wilk"
            elif v.max() == v.min():
                rec["note"] = "constante"
            else:
                w, p = quiet(stats.shapiro, v)
                rec.update(shapiro_W=w, shapiro_p=p)
            rows.append(rec)
    cols = ["service", "formFactor", "metric", "n", "median", "q1", "q3", "iqr", "mean", "sd", "min", "max",
            "shapiro_W", "shapiro_p", "note"]
    return pd.DataFrame(rows, columns=cols)


def normality_summary(desc: pd.DataFrame, alpha: float) -> pd.DataFrame:
    def agg(g: pd.DataFrame) -> pd.Series:
        tested = g["shapiro_p"].notna()
        return pd.Series(dict(groups=len(g), tested=int(tested.sum()),
                              rejected_normality=int((g.loc[tested, "shapiro_p"] < alpha).sum()),
                              constant=int((g["note"] == "constante").sum())))
    return desc.groupby("metric", sort=False)[["shapiro_p", "note"]].apply(agg).reset_index()


def invalid_runs(failures: pd.DataFrame) -> pd.DataFrame:
    if failures.empty:
        return pd.DataFrame(columns=["phase", "service", "formFactor", "reasonCode", "count"])
    return failures.groupby(["phase", "service", "formFactor", "reasonCode"]).size().rename("count").reset_index()


def lcp_summary(lcp: pd.DataFrame, kept: pd.DataFrame) -> pd.DataFrame:
    if lcp.empty:
        return pd.DataFrame(columns=["service", "formFactor", "lcpNodeLabel", "runs", "share"])
    lcp = lcp.merge(kept[KEY], on=KEY)
    counts = lcp.groupby(["service", "formFactor", "lcpNodeLabel"], dropna=False).size().rename("runs").reset_index()
    counts["share"] = counts["runs"] / counts.groupby(["service", "formFactor"])["runs"].transform("sum")
    return counts.sort_values(["service", "formFactor", "runs"], ascending=[True, True, False])


def block_medians(runs: pd.DataFrame) -> pd.DataFrame:
    t = (runs.groupby(["service", "formFactor", "block"])
         .agg(n=("run", "size"), performanceScore=("performanceScore", "median"), LCP=("LCP", "median"))
         .reset_index())
    return t


def block_effect(runs: pd.DataFrame) -> pd.DataFrame:
    """Mann-Whitney entre os dois blocos de horário, por serviço x form factor (só descritivo/diagnóstico)."""
    blocks = sorted(runs["block"].unique())
    rows = []
    if len(blocks) != 2:
        return pd.DataFrame(rows)
    a_lab, b_lab = blocks
    for (svc, ff), g in runs.groupby(["service", "formFactor"]):
        for m in ["performanceScore", "LCP"]:
            a = g.loc[g["block"] == a_lab, m].dropna().to_numpy(float)
            b = g.loc[g["block"] == b_lab, m].dropna().to_numpy(float)
            rec = dict(service=svc, formFactor=ff, metric=m, block_a=a_lab, block_b=b_lab, n_a=len(a), n_b=len(b),
                       median_a=np.median(a) if len(a) else math.nan, median_b=np.median(b) if len(b) else math.nan,
                       cliffs_delta=cliffs_delta(a, b), mw_p=math.nan)
            if len(a) and len(b) and np.ptp(np.concatenate([a, b])) > 0:
                rec["mw_p"] = quiet(stats.mannwhitneyu, a, b, alternative="two-sided").pvalue
            rows.append(rec)
    t = pd.DataFrame(rows)
    t["mw_p_holm"] = holm(t["mw_p"].tolist())
    return t


def first_run_vs_rest(runs: pd.DataFrame) -> pd.DataFrame:
    """Verificação de cache de CDN frio: primeira réplica de cada bloco contra as seguintes."""
    first = runs.groupby(["service", "formFactor", "block"])["run"].transform("min")
    r = runs.assign(position=np.where(runs["run"] == first, "first", "later"))
    t = r.groupby(["service", "formFactor", "position"]).agg(
        n=("run", "size"), performanceScore=("performanceScore", "median"), LCP=("LCP", "median"))
    return t.unstack("position").pipe(lambda d: d.set_axis([f"{a}_{b}" for a, b in d.columns], axis=1)).reset_index()


# ---------------------------------------------------------------- RQ1

def rq1(runs: pd.DataFrame, alpha: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tests, dunn_rows, worst_rows = [], [], []
    for ff in FORM_FACTORS:
        for m in ["performanceScore", "LCP"]:
            d = runs.loc[runs["formFactor"] == ff, ["service", m]].dropna()
            groups = {s: g[m].astype(float).to_numpy() for s, g in d.groupby("service")}
            n = int(sum(len(v) for v in groups.values()))
            rec = dict(formFactor=ff, metric=m, k=len(groups), n=n, H=math.nan, df=len(groups) - 1, p=math.nan,
                       epsilon2=math.nan, note="")
            tests.append(rec)
            if len(groups) < 2:
                rec["note"] = "menos de 2 serviços"
                continue
            try:
                h, p = quiet(stats.kruskal, *groups.values())
            except ValueError as err:  # ex.: todos os valores iguais
                rec["note"] = str(err)
                continue
            rec.update(H=h, p=p, epsilon2=epsilon_squared(h, n))

            dunn = sp.posthoc_dunn(d, val_col=m, group_col="service", p_adjust="holm")
            medians = d.groupby("service")[m].median()
            services = sorted(groups)
            for i, a in enumerate(services):
                for b in services[i + 1:]:
                    dunn_rows.append(dict(formFactor=ff, metric=m, service_a=a, service_b=b,
                                          median_a=medians[a], median_b=medians[b],
                                          cliffs_delta=cliffs_delta(groups[a], groups[b]), p_holm=dunn.loc[a, b]))
            worse = (lambda x, y: x > y) if HIGHER_IS_WORSE[m] else (lambda x, y: x < y)
            ranked = medians.sort_values(ascending=not HIGHER_IS_WORSE[m])  # o pior primeiro
            for rank, (s, med) in enumerate(ranked.items(), start=1):
                sig_worse = sum(1 for o in services if o != s and dunn.loc[s, o] < alpha and worse(med, medians[o]))
                worst_rows.append(dict(formFactor=ff, metric=m, rank_worst_first=rank, service=s, median=med,
                                       iqr=d.loc[d["service"] == s, m].quantile(0.75) - d.loc[d["service"] == s, m].quantile(0.25),
                                       significantly_worse_than=sig_worse, others=len(services) - 1,
                                       worse_than_majority=sig_worse > (len(services) - 1) / 2))
    t = pd.DataFrame(tests)
    t["p_holm"] = holm(t["p"].tolist())
    return t, pd.DataFrame(dunn_rows), pd.DataFrame(worst_rows)


# ---------------------------------------------------------------- medianas por serviço

def service_medians(runs: pd.DataFrame) -> pd.DataFrame:
    return (runs.groupby(["service", "formFactor"])
            .agg(n=("run", "size"), performanceScore=("performanceScore", "median"),
                 accessibilityScore=("accessibilityScore", "median"), LCP=("LCP", "median"))
            .reset_index())


# ---------------------------------------------------------------- RQ2

def spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return math.nan
    return float(quiet(stats.spearmanr, x, y).statistic)


def rq2(runs: pd.DataFrame, med: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for ff in FORM_FACTORS:
        for unit in ["service-median", "run"]:
            if unit == "service-median":
                d = med[med["formFactor"] == ff].dropna(subset=["performanceScore", "accessibilityScore"])
                groups = None
            else:
                d = runs[runs["formFactor"] == ff].dropna(subset=["performanceScore", "accessibilityScore"])
                groups = d["service"].to_numpy()
            x = d["performanceScore"].to_numpy(float)
            y = d["accessibilityScore"].to_numpy(float)
            rec = dict(formFactor=ff, unit=unit, n=len(d), n_services=d["service"].nunique(),
                       spearman_rho=spearman_rho(x, y), spearman_p=math.nan, ci_low=math.nan, ci_high=math.nan,
                       ci_method="", boot_dropped=0, kendall_tau_b=math.nan, kendall_p=math.nan, note="")
            rows.append(rec)
            if math.isnan(rec["spearman_rho"]):
                rec["note"] = "menos de 3 pontos ou variável constante"
                continue
            rec["spearman_p"] = float(quiet(stats.spearmanr, x, y).pvalue)
            tau = quiet(stats.kendalltau, x, y)  # tau-b (empates no accessibility score)
            rec.update(kendall_tau_b=tau.statistic, kendall_p=tau.pvalue)
            lo, hi, dropped = bootstrap_ci(lambda i: spearman_rho(x[i], y[i]), len(x), rng, BOOT_REPS, groups=groups)
            rec.update(ci_low=lo, ci_high=hi, boot_dropped=dropped,
                       ci_method="bootstrap percentil 95%, " + ("reamostrando serviços" if groups is None
                                                                else "por cluster (serviço inteiro)"))
    t = pd.DataFrame(rows)
    t["spearman_p_holm"] = np.nan
    for unit in ["service-median", "run"]:
        mask = t["unit"] == unit
        t.loc[mask, "spearman_p_holm"] = holm(t.loc[mask, "spearman_p"].tolist())
    return t


# ---------------------------------------------------------------- RQ3

def rq3_services(med: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Teste principal: pares = medianas por serviço (n = 10)."""
    wide = med.pivot(index="service", columns="formFactor", values=["performanceScore", "LCP"])
    wide.columns = [f"{m}_{ff}" for m, ff in wide.columns]
    pairs = wide.dropna().reset_index()
    rows = []
    for m in ["LCP", "performanceScore"]:  # o LCP é a medida principal
        mob, desk = pairs[f"{m}_mobile"].to_numpy(float), pairs[f"{m}_desktop"].to_numpy(float)
        diff = mob - desk
        rec = dict(metric=m, n_pairs=len(pairs), median_mobile=np.median(mob) if len(mob) else math.nan,
                   median_desktop=np.median(desk) if len(desk) else math.nan,
                   median_difference=np.median(diff) if len(diff) else math.nan,
                   median_ratio=np.median(mob / desk) if m == "LCP" and len(diff) else math.nan,
                   wilcoxon_W=math.nan, wilcoxon_p=math.nan, cliffs_delta=cliffs_delta(mob, desk),
                   paired_rank_biserial=paired_rank_biserial(diff), sign_test_p=math.nan, note="")
        rec["cliffs_magnitude"] = cliffs_magnitude(rec["cliffs_delta"])
        nonzero = int(np.sum(diff != 0))
        if nonzero == 0:
            rec["note"] = "sem pares ou todas as diferenças são zero"
        else:
            w = quiet(stats.wilcoxon, mob, desk)
            rec.update(wilcoxon_W=w.statistic, wilcoxon_p=w.pvalue)
            rec["sign_test_p"] = stats.binomtest(int(np.sum(diff > 0)), nonzero, 0.5).pvalue
        rows.append(rec)
    t = pd.DataFrame(rows)
    t["wilcoxon_p_holm"] = holm(t["wilcoxon_p"].tolist())
    return t, pairs


def rq3_per_service(runs: pd.DataFrame) -> pd.DataFrame:
    """Por serviço: pares = execuções mobile e desktop com o mesmo número de réplica (run).

    run k de mobile e run k de desktop são a k-ésima medição daquela célula e caem no mesmo bloco
    de horário, então o pareamento controla o horário de forma aproximada; não são simultâneas.
    """
    rows = []
    for m in ["LCP", "performanceScore"]:
        for svc, g in runs.groupby("service"):
            w = g.pivot_table(index=["block", "run"], columns="formFactor", values=m, aggfunc="first").dropna()
            if not set(FORM_FACTORS) <= set(w.columns):
                continue
            mob, desk = w["mobile"].to_numpy(float), w["desktop"].to_numpy(float)
            diff = mob - desk
            rec = dict(metric=m, service=svc, n_pairs=len(w), median_mobile=np.median(mob), median_desktop=np.median(desk),
                       median_difference=np.median(diff), wilcoxon_W=math.nan, wilcoxon_p=math.nan,
                       cliffs_delta=cliffs_delta(g.loc[g["formFactor"] == "mobile", m].dropna(),
                                                 g.loc[g["formFactor"] == "desktop", m].dropna()),
                       paired_rank_biserial=paired_rank_biserial(diff))
            rec["cliffs_magnitude"] = cliffs_magnitude(rec["cliffs_delta"])
            if np.any(diff != 0):
                res = quiet(stats.wilcoxon, mob, desk)
                rec.update(wilcoxon_W=res.statistic, wilcoxon_p=res.pvalue)
            rows.append(rec)
    t = pd.DataFrame(rows)
    t["wilcoxon_p_holm"] = np.nan
    for m in t["metric"].unique():
        mask = t["metric"] == m
        t.loc[mask, "wilcoxon_p_holm"] = holm(t.loc[mask, "wilcoxon_p"].tolist())
    return t


# ---------------------------------------------------------------- gráficos

COLORS = {"mobile": "#257de0", "desktop": "#f47230"}  # slots 1 e 2 da paleta validada (skill dataviz)
INK, INK2, GRID, AXIS = "#191919", "#666666", "#e7e7e7", "#c2c2c2"


def style_axes(ax) -> None:
    ax.set_facecolor("white")
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def place_labels(fig, ax, xs, ys, texts) -> None:
    """Rótulos diretos sem sobreposição: posição gulosa entre candidatas, conferida pela caixa do texto."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    candidates = [(5, 4, "left"), (-5, 4, "right"), (5, -11, "left"), (-5, -11, "right"),
                  (5, 14, "left"), (5, -21, "left"), (-5, 14, "right"), (-5, -21, "right")]
    taken = []
    for x, y in zip(xs, ys):  # caixa de cada ponto, para o texto não cobrir pontos
        px, py = ax.transData.transform((x, y))
        taken.append((px - 4, py - 4, px + 4, py + 4))
    order = np.argsort(xs)
    for i in order:
        for dx, dy, ha in candidates:
            t = ax.annotate(texts[i], (xs[i], ys[i]), xytext=(dx, dy), textcoords="offset points",
                            fontsize=7.5, color=INK2, ha=ha)
            bb = t.get_window_extent(renderer)
            box = (bb.x0, bb.y0, bb.x1, bb.y1)
            overlap = any(not (box[2] < o[0] or box[0] > o[2] or box[3] < o[1] or box[1] > o[3]) for o in taken)
            if not overlap or (dx, dy, ha) == candidates[-1]:
                taken.append(box)
                break
            t.remove()


def figures(runs: pd.DataFrame, med: pd.DataFrame, names: dict[str, str], outdir: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150, "savefig.dpi": 150})
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    label = lambda s: names.get(s, s)

    # 1. Boxplot do LCP por serviço e form factor
    order = (med[med["formFactor"] == "mobile"].sort_values("LCP")["service"].tolist())
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    pos = np.arange(len(order))
    for j, ff in enumerate(FORM_FACTORS):
        data = [runs.loc[(runs["service"] == s) & (runs["formFactor"] == ff), "LCP"].dropna().to_numpy() / 1000 for s in order]
        offset = 0.2 if ff == "mobile" else -0.2
        ax.boxplot(data, positions=pos + offset, widths=0.34, orientation="horizontal", patch_artist=True, showfliers=True,
                   boxprops=dict(facecolor=COLORS[ff], edgecolor=COLORS[ff], alpha=0.35, linewidth=1),
                   medianprops=dict(color=COLORS[ff], linewidth=2), whiskerprops=dict(color=COLORS[ff], linewidth=1),
                   capprops=dict(color=COLORS[ff], linewidth=1),
                   flierprops=dict(marker="o", markersize=4, markerfacecolor=COLORS[ff], markeredgecolor="white", alpha=0.9))
    ax.set_yticks(pos, [label(s) for s in order])
    ax.set_xlabel("LCP (s)")
    ax.set_title("LCP por serviço e form factor (cada caixa: execuções válidas)", loc="left", color=INK, fontsize=11)
    style_axes(ax)
    ax.legend(handles=[Patch(facecolor=COLORS[f], alpha=0.6, label=f) for f in ["mobile", "desktop"]],
              frameon=False, loc="lower right", bbox_to_anchor=(1, 1), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / "lcp_boxplot.png")
    plt.close(fig)
    written.append("lcp_boxplot.png")

    # 2. Performance x acessibilidade (medianas por serviço), um painel por form factor
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    for ax, ff in zip(axes, FORM_FACTORS):
        d = med[med["formFactor"] == ff]
        ax.scatter(d["performanceScore"], d["accessibilityScore"], s=42, color=COLORS[ff], edgecolor="white", linewidth=1.5, zorder=3)
        # Serviços no mesmo ponto ou quase (mesma linha, até 4 pontos de score de distância) recebem
        # um rótulo só, em ordem de x; os valores exatos ficam na tabela de results.md. Cada rótulo
        # testa algumas posições em volta do grupo e fica na primeira que não encosta em outro
        # rótulo nem em outro ponto.
        clusters: list[list[tuple[float, float, str]]] = []
        for _, r in d.sort_values(["accessibilityScore", "performanceScore"]).iterrows():
            p = (float(r["performanceScore"]), float(r["accessibilityScore"]), label(r["service"]))
            last = clusters[-1][-1] if clusters else None
            if last and abs(p[1] - last[1]) <= 1.5 and p[0] - last[0] <= 4:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        place_labels(fig, ax, np.array([np.mean([p[0] for p in c]) for c in clusters]),
                     np.array([np.mean([p[1] for p in c]) for c in clusters]),
                     [", ".join(p[2] for p in c) for c in clusters])
        ax.set_title(ff, loc="left", color=INK, fontsize=10)
        ax.set_xlabel("Performance score (mediana, 0–100)")
        ax.set_xlim(-3, 103)
        style_axes(ax)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
    axes[0].set_ylabel("Accessibility score (mediana, 0–100)")
    fig.suptitle("Desempenho × acessibilidade por serviço", x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(outdir / "perf_vs_a11y.png")
    plt.close(fig)
    written.append("perf_vs_a11y.png")

    # 3. Mobile x desktop pareado (mediana do LCP por serviço)
    w = med.pivot(index="service", columns="formFactor", values="LCP").dropna() / 1000
    w = w.sort_values("mobile")
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    y = np.arange(len(w))
    ax.hlines(y, w["desktop"], w["mobile"], color=AXIS, linewidth=2, zorder=1)
    for ff in ["desktop", "mobile"]:
        ax.scatter(w[ff], y, s=48, color=COLORS[ff], edgecolor="white", linewidth=1.5, zorder=3, label=ff)
    for yi, (svc, r) in zip(y, w.iterrows()):
        ax.annotate(f"{r['mobile'] / r['desktop']:.1f}×", (r["mobile"], yi), xytext=(7, -3), textcoords="offset points", fontsize=8, color=INK2)
    ax.set_yticks(y, [label(s) for s in w.index])
    ax.set_xlabel("LCP mediano (s); à direita, razão mobile/desktop")
    ax.set_title("LCP mediano por serviço: desktop × mobile", loc="left", color=INK, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / "mobile_vs_desktop.png")
    plt.close(fig)
    written.append("mobile_vs_desktop.png")

    # 4. Boxplot do performance score (apêndice)
    order = med[med["formFactor"] == "mobile"].sort_values("performanceScore", ascending=False)["service"].tolist()
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    pos = np.arange(len(order))
    for ff in FORM_FACTORS:
        data = [runs.loc[(runs["service"] == s) & (runs["formFactor"] == ff), "performanceScore"].dropna().to_numpy() for s in order]
        offset = 0.2 if ff == "mobile" else -0.2
        ax.boxplot(data, positions=pos + offset, widths=0.34, orientation="horizontal", patch_artist=True,
                   boxprops=dict(facecolor=COLORS[ff], edgecolor=COLORS[ff], alpha=0.35, linewidth=1),
                   medianprops=dict(color=COLORS[ff], linewidth=2), whiskerprops=dict(color=COLORS[ff], linewidth=1),
                   capprops=dict(color=COLORS[ff], linewidth=1),
                   flierprops=dict(marker="o", markersize=4, markerfacecolor=COLORS[ff], markeredgecolor="white"))
    ax.set_yticks(pos, [label(s) for s in order])
    ax.set_xlabel("Performance score (0–100)")
    ax.set_xlim(-3, 103)
    ax.set_title("Performance score por serviço e form factor", loc="left", color=INK, fontsize=11)
    style_axes(ax)
    ax.legend(handles=[Patch(facecolor=COLORS[f], alpha=0.6, label=f) for f in ["mobile", "desktop"]],
              frameon=False, loc="lower right", bbox_to_anchor=(1, 1), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / "performance_boxplot.png")
    plt.close(fig)
    written.append("performance_boxplot.png")
    return written


# ---------------------------------------------------------------- principal

def run_variant(data: dict, runs_base: pd.DataFrame, variant: str, args, out: Path) -> dict:
    rng = np.random.default_rng(args.seed)
    runs = apply_variant(runs_base, data["outliers"], variant)
    med = service_medians(runs)
    desc = describe(runs)
    rq1_tests, rq1_dunn, rq1_worst = rq1(runs, args.alpha)
    rq3_tests, rq3_pairs = rq3_services(med)
    tables = {
        "descriptives": desc,
        "normality_summary": normality_summary(desc, args.alpha),
        "service_medians": med,
        "block_medians": block_medians(runs),
        "block_effect": block_effect(runs),
        "first_run_vs_rest": first_run_vs_rest(runs),
        "lcp_elements": lcp_summary(data["lcp"], runs),
        "rq1_kruskal": rq1_tests,
        "rq1_dunn": rq1_dunn,
        "rq1_worst": rq1_worst,
        "rq2_correlation": rq2(runs, med, rng),
        "rq3_pairs": rq3_pairs,
        "rq3_wilcoxon": rq3_tests,
        "rq3_per_service": rq3_per_service(runs),
    }
    vdir = out / variant
    vdir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(vdir / f"{name}.csv", index=False, float_format="%.6g")
    tables["_values_removed"] = int(sum(runs_base[m].notna().sum() - runs[m].notna().sum() for m in METRICS))
    return tables


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    phases = [p for p in args.phases.split(",") if p]
    out = Path(args.out) if args.out else ROOT / "analysis" / "output"
    figdir = Path(args.figures) if args.figures else ROOT / "analysis" / "figures"
    out.mkdir(parents=True, exist_ok=True)

    data = load(phases)
    runs, excluded = select_runs(data, args)
    excluded.to_csv(out / "excluded_runs.csv", index=False)
    invalid_runs(data["failures"]).to_csv(out / "invalid_runs.csv", index=False)
    # Nome curto para os gráficos: o nome de data/urls.json sem o texto entre parênteses.
    names = {s["id"]: s["name"].split(" (")[0] for s in json.loads(URLS_FILE.read_text(encoding="utf-8"))["services"]}

    results = {v: run_variant(data, runs, v, args, out) for v in VARIANTS}

    written = []
    if not args.no_figures:
        written = figures(runs, results["todas"]["service_medians"], names, figdir)

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phases": phases, "alpha": args.alpha, "bootstrapSeed": args.seed, "bootstrapReps": BOOT_REPS,
        "excludeFlags": args.exclude_flags, "excludeServices": args.exclude_services,
        "runsRead": len(data["runs"]), "runsKept": len(runs), "runsExcluded": len(excluded),
        "valuesRemovedAsOutliers": results["sem-outliers"]["_values_removed"],
        "figures": written,
        "versions": {"python": platform.python_version(),
                     **{p: version(p) for p in ["numpy", "pandas", "scipy", "scikit-posthocs", "matplotlib"]}},
    }
    (out / "analysis-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if "pilot" in phases:
        print("AVISO: dados do piloto (3 execuções por célula, poucos serviços). Os testes só conferem que o "
              "script funciona; não são resultados.\n")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(f"Execuções lidas {len(data['runs'])}, mantidas {len(runs)}, excluídas {len(excluded)}; "
          f"valores marcados como outlier (variante sem-outliers): {meta['valuesRemovedAsOutliers']}")
    for v in VARIANTS:
        print(f"\n######## variante {v}")
        for name in ["rq1_kruskal", "rq1_worst", "rq2_correlation", "rq3_wilcoxon"]:
            print(f"\n== {name}\n{results[v][name].to_string(index=False, float_format=lambda x: f'{x:.4g}')}")
    print(f"\nTabelas em {out}; gráficos em {figdir if written else '(desligados)'}")


if __name__ == "__main__":
    main()
