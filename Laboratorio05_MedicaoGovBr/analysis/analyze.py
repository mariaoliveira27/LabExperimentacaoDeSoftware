#!/usr/bin/env python3
"""Statistical analysis of the Lighthouse measurements (docs/proposta.md, section 7).

Reads data/processed/<phase>.csv and its companion files (_flags, _failures, _lcp_elements) for
one or more phases and writes CSV tables to --out. Each phase is one collection session, so in
Sprint 2 each time block is one phase (e.g. full-b1, full-b2, full-b3).

    python analysis/analyze.py --phases full-b1,full-b2,full-b3
    python analysis/analyze.py --phases pilot --out <dir>     # pilot: checks the script only

Main analysis vs sensitivity analyses (re-run with options):
    --exclude-flags SLOW_HOST_CPU      default; runs at or below Lighthouse's slow-CPU threshold
    --exclude-flags all                drop every run listed in <phase>_flags.csv
    --exclude-services govbr,svr-bcb   e.g. services whose LCP element is a cookie banner
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

from lab_stats import cliffs_delta, cliffs_magnitude, epsilon_squared, holm, paired_rank_biserial

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
URLS_FILE = ROOT / "data" / "urls.json"

FORM_FACTORS = ["mobile", "desktop"]
METRICS = ["performanceScore", "accessibilityScore", "LCP", "FCP", "TBT", "CLS", "SpeedIndex"]
# For each metric used to rank services: is a higher value worse?
HIGHER_IS_WORSE = {"performanceScore": False, "accessibilityScore": False, "LCP": True}
KEY = ["block", "service", "formFactor", "run"]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phases", required=True, help="comma-separated phases; each is one block")
    ap.add_argument("--out", help="output folder (default data/analysis/<phases joined by +>)")
    ap.add_argument("--exclude-flags", default="SLOW_HOST_CPU",
                    help="flag codes from <phase>_flags.csv to exclude, comma-separated, 'all' or 'none'")
    ap.add_argument("--exclude-services", default="", help="comma-separated service ids to leave out")
    ap.add_argument("--alpha", type=float, default=0.05)
    return ap.parse_args()


def read_csv(phase: str, suffix: str, required: bool) -> pd.DataFrame:
    path = PROCESSED / f"{phase}{suffix}.csv"
    if not path.exists():
        if required:
            sys.exit(f"{path.relative_to(ROOT)} not found; run `node scripts/extract-metrics.mjs --phase {phase}` first")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.insert(0, "block", phase)
    return df


def load(phases: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for name, suffix, required in [("runs", "", True), ("flags", "_flags", False),
                                   ("failures", "_failures", False), ("lcp", "_lcp_elements", False)]:
        frames = [read_csv(p, suffix, required) for p in phases]
        frames = [f for f in frames if not f.empty]
        out[name] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return out


def select_runs(data: dict, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applies the exclusions and returns (kept runs, excluded runs with reason)."""
    runs = data["runs"].copy()
    listed = {s["id"] for s in json.loads(URLS_FILE.read_text(encoding="utf-8"))["services"]}
    reasons = pd.Series("", index=runs.index)

    def mark(mask: pd.Series, reason: str) -> None:
        reasons.loc[mask & (reasons == "")] = reason

    mark(~runs["service"].isin(listed), "service not in data/urls.json (replaced)")
    excluded_services = {s for s in args.exclude_services.split(",") if s}
    mark(runs["service"].isin(excluded_services), "--exclude-services")

    flags = data["flags"]
    codes = args.exclude_flags.strip()
    if codes != "none" and not flags.empty:
        selected = flags if codes == "all" else flags[flags["flag"].isin(codes.split(","))]
        per_run = selected.groupby(KEY)["flag"].agg(lambda s: "+".join(sorted(set(s)))).rename("flags")
        joined = runs.join(per_run, on=KEY)
        has_flag = joined["flags"].notna()
        reasons.loc[has_flag & (reasons == "")] = "flag: " + joined.loc[has_flag & (reasons == ""), "flags"]

    excluded = runs[reasons != ""].assign(reason=reasons[reasons != ""])[KEY + ["reason"]]
    return runs[reasons == ""].reset_index(drop=True), excluded


def quiet(fn, *a, **kw):
    """Runs a SciPy test with its warnings silenced; the caller checks for NaN."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*a, **kw)


# ---------------------------------------------------------------- descriptive statistics (7.1)

def describe(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (svc, ff), g in runs.groupby(["service", "formFactor"]):
        for m in METRICS:
            v = g[m].astype(float)
            rec = dict(service=svc, formFactor=ff, metric=m, n=len(v), median=v.median(),
                       q1=v.quantile(0.25), q3=v.quantile(0.75), min=v.min(), max=v.max(),
                       shapiro_W=math.nan, shapiro_p=math.nan, note="")
            rec["iqr"] = rec["q3"] - rec["q1"]
            if len(v) < 3:
                rec["note"] = "n < 3: no Shapiro-Wilk"
            elif v.max() == v.min():
                rec["note"] = "constant"
            else:
                w, p = quiet(stats.shapiro, v)
                rec.update(shapiro_W=w, shapiro_p=p)
            rows.append(rec)
    cols = ["service", "formFactor", "metric", "n", "median", "q1", "q3", "iqr", "min", "max", "shapiro_W", "shapiro_p", "note"]
    return pd.DataFrame(rows, columns=cols)


def invalid_runs(failures: pd.DataFrame) -> pd.DataFrame:
    if failures.empty:
        return pd.DataFrame(columns=["block", "service", "formFactor", "reasonCode", "count"])
    return failures.groupby(["block", "service", "formFactor", "reasonCode"]).size().rename("count").reset_index()


def lcp_summary(lcp: pd.DataFrame, kept: pd.DataFrame) -> pd.DataFrame:
    if lcp.empty:
        return pd.DataFrame(columns=["service", "formFactor", "lcpNodeLabel", "runs", "share"])
    lcp = lcp.merge(kept[KEY], on=KEY)
    counts = lcp.groupby(["service", "formFactor", "lcpNodeLabel"], dropna=False).size().rename("runs").reset_index()
    counts["share"] = counts["runs"] / counts.groupby(["service", "formFactor"])["runs"].transform("sum")
    return counts.sort_values(["service", "formFactor", "runs"], ascending=[True, True, False])


def block_medians(runs: pd.DataFrame) -> pd.DataFrame:
    return (runs.groupby(["service", "formFactor", "block"])
            .agg(n=("run", "size"), performanceScore=("performanceScore", "median"), LCP=("LCP", "median"))
            .reset_index())


def first_run_vs_rest(runs: pd.DataFrame) -> pd.DataFrame:
    """Cold-CDN check (section 8.2): run 1 of each block against the later runs."""
    r = runs.assign(position=np.where(runs["run"] == 1, "run1", "later"))
    t = r.groupby(["service", "formFactor", "position"]).agg(
        n=("run", "size"), performanceScore=("performanceScore", "median"), LCP=("LCP", "median"))
    return t.unstack("position").pipe(lambda d: d.set_axis([f"{a}_{b}" for a, b in d.columns], axis=1)).reset_index()


# ---------------------------------------------------------------- RQ1 (7.2)

def rq1(runs: pd.DataFrame, alpha: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tests, dunn_rows, worst_rows = [], [], []
    for ff in FORM_FACTORS:
        d = runs[runs["formFactor"] == ff]
        for m in ["performanceScore", "LCP"]:
            groups = {s: g[m].astype(float).to_numpy() for s, g in d.groupby("service")}
            n = int(sum(len(v) for v in groups.values()))
            rec = dict(formFactor=ff, metric=m, k=len(groups), n=n, H=math.nan, p=math.nan, epsilon2=math.nan, note="")
            tests.append(rec)
            if len(groups) < 2:
                rec["note"] = "fewer than 2 services"
                continue
            try:
                h, p = quiet(stats.kruskal, *groups.values())
            except ValueError as err:  # e.g. all values identical
                rec["note"] = str(err)
                continue
            rec.update(H=h, p=p, epsilon2=epsilon_squared(h, n))

            dunn = sp.posthoc_dunn(d, val_col=m, group_col="service", p_adjust="holm")
            medians = d.groupby("service")[m].median()
            services = sorted(groups)
            for i, a in enumerate(services):
                for b in services[i + 1:]:
                    dunn_rows.append(dict(formFactor=ff, metric=m, service_a=a, service_b=b,
                                          median_a=medians[a], median_b=medians[b], p_holm=dunn.loc[a, b]))
            worse = (lambda x, y: x > y) if HIGHER_IS_WORSE[m] else (lambda x, y: x < y)
            ranked = medians.sort_values(ascending=not HIGHER_IS_WORSE[m])  # worst first
            for rank, (s, med) in enumerate(ranked.items(), start=1):
                sig_worse = sum(1 for o in services if o != s and dunn.loc[s, o] < alpha and worse(med, medians[o]))
                worst_rows.append(dict(formFactor=ff, metric=m, rank_worst_first=rank, service=s, median=med,
                                       significantly_worse_than=sig_worse, others=len(services) - 1,
                                       worse_than_majority=sig_worse > (len(services) - 1) / 2))
    t = pd.DataFrame(tests)
    t["p_holm"] = holm(t["p"].tolist())
    return t, pd.DataFrame(dunn_rows), pd.DataFrame(worst_rows)


# ---------------------------------------------------------------- per-service medians (RQ2, RQ3)

def service_medians(runs: pd.DataFrame) -> pd.DataFrame:
    return (runs.groupby(["service", "formFactor"])
            .agg(n=("run", "size"), performanceScore=("performanceScore", "median"),
                 accessibilityScore=("accessibilityScore", "median"), LCP=("LCP", "median"))
            .reset_index())


def rq2(med: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ff in FORM_FACTORS:
        d = med[med["formFactor"] == ff]
        rec = dict(formFactor=ff, n_services=len(d), spearman_rho=math.nan, spearman_p=math.nan,
                   kendall_tau_b=math.nan, kendall_p=math.nan, note="")
        rows.append(rec)
        if len(d) < 3:
            rec["note"] = "fewer than 3 services"
            continue
        x, y = d["performanceScore"], d["accessibilityScore"]
        if x.nunique() < 2 or y.nunique() < 2:
            rec["note"] = "a variable is constant across services"
            continue
        rho, p = quiet(stats.spearmanr, x, y)
        tau, p_tau = quiet(stats.kendalltau, x, y)  # tau-b (ties in the accessibility score)
        rec.update(spearman_rho=rho, spearman_p=p, kendall_tau_b=tau, kendall_p=p_tau)
    t = pd.DataFrame(rows)
    t["spearman_p_holm"] = holm(t["spearman_p"].tolist())
    t["kendall_p_holm"] = holm(t["kendall_p"].tolist())
    return t


def rq3(med: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = med.pivot(index="service", columns="formFactor", values=["performanceScore", "LCP"])
    wide.columns = [f"{m}_{ff}" for m, ff in wide.columns]
    pairs = wide.dropna().reset_index()
    rows = []
    for m in ["LCP", "performanceScore"]:  # LCP is the main measure (section 7.4)
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
            rec["note"] = "no pairs or all differences are zero"
        else:
            w, p = quiet(stats.wilcoxon, mob, desk)
            rec.update(wilcoxon_W=w, wilcoxon_p=p)
            rec["sign_test_p"] = stats.binomtest(int(np.sum(diff > 0)), nonzero, 0.5).pvalue
        rows.append(rec)
    t = pd.DataFrame(rows)
    t["wilcoxon_p_holm"] = holm(t["wilcoxon_p"].tolist())
    return t, pairs


# ---------------------------------------------------------------- main

def main() -> None:
    args = parse_args()
    phases = [p for p in args.phases.split(",") if p]
    out = Path(args.out) if args.out else ROOT / "data" / "analysis" / "+".join(phases)
    out.mkdir(parents=True, exist_ok=True)

    data = load(phases)
    runs, excluded = select_runs(data, args)
    med = service_medians(runs)
    rq1_tests, rq1_dunn, rq1_worst = rq1(runs, args.alpha)
    rq3_tests, rq3_pairs = rq3(med)

    tables = {
        "descriptives": describe(runs),
        "invalid_runs": invalid_runs(data["failures"]),
        "excluded_runs": excluded,
        "lcp_elements": lcp_summary(data["lcp"], runs),
        "block_medians": block_medians(runs),
        "first_run_vs_rest": first_run_vs_rest(runs),
        "service_medians": med,
        "rq1_kruskal": rq1_tests,
        "rq1_dunn": rq1_dunn,
        "rq1_worst": rq1_worst,
        "rq2_correlation": rq2(med),
        "rq3_pairs": rq3_pairs,
        "rq3_wilcoxon": rq3_tests,
    }
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False, float_format="%.6g")

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phases": phases, "alpha": args.alpha,
        "excludeFlags": args.exclude_flags, "excludeServices": args.exclude_services,
        "runsRead": len(data["runs"]), "runsKept": len(runs), "runsExcluded": len(excluded),
        "versions": {"python": platform.python_version(),
                     **{p: version(p) for p in ["numpy", "pandas", "scipy", "scikit-posthocs"]}},
    }
    (out / "analysis-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if "pilot" in phases:
        print("NOTE: pilot data (3 runs per cell, few services). The tests only check that the script runs; "
              "they are not results.\n")
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print(f"Runs read {len(data['runs'])}, kept {len(runs)}, excluded {len(excluded)}")
    for name in ["excluded_runs", "service_medians", "rq1_kruskal", "rq1_worst", "rq2_correlation", "rq3_wilcoxon"]:
        print(f"\n== {name}\n{tables[name].to_string(index=False, float_format=lambda v: f'{v:.4g}')}")
    print(f"\nWrote {len(tables)} tables and analysis-metadata.json to {out}")


if __name__ == "__main__":
    main()
