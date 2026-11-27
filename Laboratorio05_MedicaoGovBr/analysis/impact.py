#!/usr/bin/env python3
"""Impact estimate for docs/impacto.md: extra waiting time per month, in hours.

    .venv/Scripts/python analysis/impact.py

Inputs:
  data/processed/full.csv   LCP of every valid run (ms)
  data/usage.json           public usage numbers, with source, link and access date

For each service with useInConversion = true:

  monthly_events = value / periodMonths          (assumes an even spread over the period)
  extra_s        = max(0, LCP - reference) / 1000
  hours_month    = extra_s * monthly_events / 3600

LCP is taken at the 25th percentile (low), median and 75th percentile (high) of the runs of the
service in that form factor (linear interpolation, same as analysis/analyze.py). References:
  ref_a  the service's own desktop median LCP (applied to the mobile LCP)
  ref_b  2.5 s, the "good LCP" threshold from web.dev (applied to mobile and to desktop LCP)

Sensitivity to the share of accesses that come from a phone (analysis/output/impact_sensitivity.csv):

  ref_a  hours = share * hours_mobile                         (desktop is the reference, so its extra time is 0)
  ref_b  hours = share * hours_mobile + (1 - share) * hours_desktop

The central result of impact.csv is the scenario in which every access is mobile (share = 1). The usage
numbers do not say how many accesses come from phones, so shares of 0, 0.5 and 1 are shown instead of one guess.

Writes analysis/output/impact.csv and analysis/output/impact_sensitivity.csv and prints the tables.
Does not touch raw data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "processed" / "full.csv"
USAGE = ROOT / "data" / "usage.json"
OUT = ROOT / "analysis" / "output" / "impact.csv"
OUT_SENS = ROOT / "analysis" / "output" / "impact_sensitivity.csv"

MOBILE_SHARES = (0.0, 0.5, 1.0)

SCENARIOS = {"low": 0.25, "median": 0.50, "high": 0.75}


def lcp_quantiles(runs: pd.DataFrame, service: str, form_factor: str) -> dict[str, float]:
    values = runs[(runs.service == service) & (runs.formFactor == form_factor)]["LCP"].to_numpy(float)
    if len(values) == 0:
        raise ValueError(f"no runs for {service} {form_factor}")
    return {name: float(np.quantile(values, q)) for name, q in SCENARIOS.items()}


def sensitivity(table: pd.DataFrame) -> pd.DataFrame:
    """Hours per month for each share of mobile accesses, per service and in total."""
    rows = []
    services = [s for s in table.service.unique() if s != "TOTAL"]
    for service in services:
        t = table[table.service == service].set_index(["reference", "formFactor"])
        for reference in ("ref_a_desktop_median", "ref_b_2500ms"):
            mobile = t.loc[(reference, "mobile")]
            desktop = t.loc[(reference, "desktop")] if (reference, "desktop") in t.index else None
            for share in MOBILE_SHARES:
                row = dict(service=service, reference=reference, mobile_share=share)
                for name in SCENARIOS:
                    desk = 0.0 if desktop is None else float(desktop[f"hours_{name}"])
                    row[f"hours_{name}"] = share * float(mobile[f"hours_{name}"]) + (1 - share) * desk
                rows.append(row)
    out = pd.DataFrame(rows)
    totals = (out.groupby(["reference", "mobile_share"], sort=False)[[f"hours_{n}" for n in SCENARIOS]]
              .sum().reset_index().assign(service="TOTAL"))
    return pd.concat([out, totals], ignore_index=True)


def main() -> None:
    runs = pd.read_csv(RUNS)
    usage = json.loads(USAGE.read_text(encoding="utf-8"))
    threshold = float(usage["lcpGoodThresholdMs"])
    rows = []
    for entry in usage["services"]:
        if not entry["useInConversion"]:
            continue
        monthly = entry["value"] / entry["periodMonths"]
        mobile = lcp_quantiles(runs, entry["service"], "mobile")
        desktop = lcp_quantiles(runs, entry["service"], "desktop")
        cases = [
            ("ref_a_desktop_median", "mobile", mobile, desktop["median"]),
            ("ref_b_2500ms", "mobile", mobile, threshold),
            ("ref_b_2500ms", "desktop", desktop, threshold),
        ]
        for reference, form_factor, lcp, ref_ms in cases:
            row = dict(service=entry["service"], unit=entry["unit"], period=entry["period"],
                       monthly_events=monthly, reference=reference, formFactor=form_factor, reference_ms=ref_ms)
            for name in SCENARIOS:
                extra_s = max(0.0, lcp[name] - ref_ms) / 1000
                row[f"lcp_{name}_ms"] = lcp[name]
                row[f"extra_{name}_s"] = extra_s
                row[f"hours_{name}"] = extra_s * monthly / 3600
            rows.append(row)
    table = pd.DataFrame(rows)
    totals = (table.groupby(["reference", "formFactor"], sort=False)[[f"hours_{n}" for n in SCENARIOS]]
              .sum().reset_index().assign(service="TOTAL"))
    table = pd.concat([table, totals], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, float_format="%.6g")
    cols = ["service", "reference", "formFactor", "monthly_events", "reference_ms",
            "lcp_low_ms", "lcp_median_ms", "lcp_high_ms", "hours_low", "hours_median", "hours_high"]
    print(table[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print(f"\nWritten {OUT.relative_to(ROOT)}")
    sens = sensitivity(table.drop(columns=[]))
    sens.to_csv(OUT_SENS, index=False, float_format="%.6g")
    print(sens.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print(f"\nWritten {OUT_SENS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
