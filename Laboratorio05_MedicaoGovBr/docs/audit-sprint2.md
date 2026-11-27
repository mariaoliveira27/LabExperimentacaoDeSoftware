# Sprint 2 audit

Done on 26/11/2026, at the start of Sprint 3, before the impact and conclusions documents were written. Scope: the full collection of 25/11/2026 (200 valid runs, 205 attempts), the validation, the analysis in `analysis/` and the documents that describe them.

## What was checked and how

| Check | Result |
|---|---|
| `node scripts/validate-data.mjs --phase full` | 200 of 200 expected runs present; 0 errors, 0 warnings; 105 values outside the Tukey fences (60 runs), flagged, not removed; smallest pause between attempts 10.001 s, median 10.011 s. `docs/data-validation.md` regenerated. |
| Independent recomputation of the main numbers (`analysis/check_results.py`, numpy and pandas only) | Matches `analysis/results.md`: Kruskal–Wallis H 95.4, 91.9, 90.3, 84.3 and ε² 0.96, 0.93, 0.91, 0.85 (RQ1); Spearman on the per-service medians 0.41 (mobile) and 0.48 (desktop) (RQ2); LCP higher on mobile in 10 of 10 services, median 13.65 s against 3.61 s, median difference 9.39 s, median of per-service ratios 4.76, median score difference −19.2 points (RQ3). |
| `npm test` | 20 of 20 pass. |
| `analysis/run_all.py`, `analyze.py` and the Python unit tests | **Not rerun** in this environment: scipy, statsmodels and scikit-posthocs could not be installed (no access to the package index). The Dunn post-hoc, the bootstrap intervals and the Wilcoxon p-values were not recomputed. TODO: rerun `.venv/Scripts/python analysis/run_all.py` on the group's machine and compare with the committed tables. |
| Failed attempts | 5 invalid attempts of 205, all Consumidor.gov.br (`MISSING_VALUES`, `NO_FCP`), all redone. No blocks. |
| Pause rule and seed | Seed 3118576651 in `data/raw/full/plan.json`; both sessions use the same plan. |

## Findings and actions

| # | Finding | Action |
|---|---|---|
| F1 | At the start of this audit `docs/` held only `proposta.md` and `robots-check.md`. `README.md`, `results.md` and `proposta.md` link to nine documents that were not on disk: `audit-sprint1.md`, `url-changes.md`, `data-validation.md`, `ameacas-validade.md`, `sprint2-entrega.md`, `audit-sprint2.md`, `impacto.md`, `categorias-pesquisa.md` and `conclusoes.md`. | `data-validation.md` regenerated with the validation script. The other eight written in Sprint 3 from the data and from `proposta.md` and `results.md`. |
| F2 | In `data/failed-runs.csv`, the `file` column of the three afternoon retries (Consumidor.gov.br desktop runs 2, 8 and 9) pointed to the valid redo, not to the invalid file. | Fixed: the three rows now point to the `-t1` files in `data/raw/full/invalid/`. All 5 paths in the file exist. Validation still passes. |
| F3 | `proposta.md` named Chrome 157 (the pilot version); the full collection ran on Chrome 158.0.8127.37. | Fixed (see Sprint 1 audit, F1). |
| F4 | The null-metric check was added to the script after the morning session. The two morning runs with null metrics were found only when the afternoon session resumed (`invalid-found-on-resume`), moved to `invalid/` and redone. | No data affected: the 200 valid runs pass every check. Documented in `ameacas-validade.md`. |
| F5 | The ratio of mobile to desktop LCP appears twice: 4.8× is the median of the 10 per-service ratios, and 3.8× is the ratio of the two medians (13.65 / 3.61). | Checked: `results.md` §7.1 and `README.md` label the 4.8× correctly. `conclusoes.md` states both. |
| F6 | The sensitivity analysis without the two services whose LCP element is a cookie banner (Portal gov.br and Valores a Receber) was never reported. | Recomputed with `analysis/check_results.py`: the conclusions do not change (Kruskal–Wallis p < 0.001, ε² 0.83 to 0.97; ρ 0.37 and 0.39 with n = 8, still inconclusive; LCP higher on mobile in 8 of 8). TODO: produce the official tables with `analyze.py --exclude-services govbr,svr-bcb`. |
| F7 | `proposta.md` §1.3 lists 72 million queries for Valores a Receber; the impact estimate uses 73 million from the Banco Central. | See the Sprint 1 audit, F2. |
| F8 | The central impact result applies the mobile LCP to every access, and that assumption was not listed. | `analysis/impact.py` now also writes `impact_sensitivity.csv` (0%, 50% and 100% mobile), and `impacto.md` states the assumption. |

## Still open

- Provider and city of the measuring machine are not recorded (connection type and power plan are, per session).
- No evening block: the collection covers one morning and one afternoon of one day.
- Exclusion and sensitivity criteria (`proposta.md` §7.6) are not yet confirmed with the group and the professor.
- Official tables for the cookie-banner sensitivity run (F6) and a rerun of `run_all.py` (above).
- The INSS page on gov.br was not opened in this audit; the 123.4 million site accesses were checked in republications of the INSS text.
