# Sprint 1 audit

Retrospective check of the Sprint 1 deliverables against the Sprint 1 plan, done on 26/11/2026 (during Sprint 3), from the files on disk. Nothing here changes data. Items marked "fixed" were corrected during this audit.

## Checklist

| # | Planned deliverable | Found | Status |
|---|---|---|---|
| 1 | Node project with pinned Lighthouse and chrome-launcher | `package.json` pins `lighthouse` 13.6.0, `chrome-launcher` 1.2.3 and `robots-parser` 3.0.1; `engines.node` is `>=22.19`; `package-lock.json` is present | OK |
| 2 | `robots-check` script and `docs/robots-check.md` | `scripts/robots-check.mjs`, `docs/robots-check.md`, `data/robots-check.json` and 10 copies in `data/robots/`. Generated on 25/11/2026 at 11:37, before the first full session (a rerun was needed: the pilot check of 17/11 was older than the 7-day limit) | OK |
| 3 | `run-lighthouse` script: sequential, random order with seed logged, pause >= 10 s, N configurable, raw JSON per run | `scripts/run-lighthouse.mjs`: one Chrome and one run at a time, seeded shuffle (mulberry32 + Fisher–Yates), `--pause` below 10 s refused, `--runs`, one raw file per run. Refuses URLs not cleared by `robots-check` | OK |
| 4 | `data/run-metadata.json` with versions, config, OS, CPU, RAM and timestamps | 4 sessions (2 pilot, 2 full). Each has Lighthouse, chrome-launcher and Chrome versions, Chrome flags, Lighthouse config per form factor, OS, CPU, RAM, Node version, time zone, planned order and one entry per execution with start and end time | OK |
| 5 | `extract-metrics` script and CSV with the agreed columns | `scripts/extract-metrics.mjs`; `data/processed/pilot.csv` header is `service,url,formFactor,run,performanceScore,accessibilityScore,LCP,FCP,TBT,CLS,SpeedIndex,timestamp` | OK |
| 6 | `data/urls.json` with 10 services and replaced candidates | 10 services; 5 entries in `replaced` with date and reason | OK |
| 7 | Pilot: 3 URLs, 3 runs per form factor | 24 runs in 2 sessions (seeds 41872753 and 484856555): 18 for the planned 3 services plus 6 more after one service was replaced. 20 valid, 4 invalid (CAPTCHA page of the replaced service). Smallest gap between runs, recomputed from `pilot_executions.csv`: 10.002 s. Pilot medians in `proposta.md` §9.2 match `pilot_summary.csv` | OK |
| 8 | Impact evidence with number, source, link and access date | `proposta.md` §1.3: 10 services, access date 17/11/2026, "NÃO ENCONTRADO" where no verifiable number exists (Portal do Servidor) | OK, with finding F2 |
| 9 | `docs/proposta.md` with the agreed sections | §1 criteria, §2 RQs and hypotheses, §3 GQM, §4 entities and attributes, §5 seven categories, §6 collection plan, §7 analysis plan, §8 threats to validity, §9 pilot results, §10 TODO list | OK |
| 10 | `README.md` | Install, pilot, full collection, options, data layout, analysis | OK |
| 11 | Unit tests | `npm test`: 20 of 20 pass (Node 22.23.5 in this audit; Sprint 1 used Node 24.18.0) | OK |

## Findings

| # | Finding | Action |
|---|---|---|
| F1 | `proposta.md` §6.6 and §8.2 named Chrome 157.0.8103.79, the pilot version. The full collection ran on Chrome 158.0.8127.37 (`run-metadata.json`). | Fixed: both places now name 157 for the pilot and 158 for the full collection. |
| F2 | `proposta.md` §1.3 lists 72 million public queries for Valores a Receber (MGI note of 14/02/2025). `data/usage.json` uses 73 million (Banco Central presentation of 26/05/2025, slide 9). | Not an error: both sources exist. The impact estimate uses the Banco Central number; `proposta.md` now says so in the changelog. |
| F3 | 4 of the 10 `robots.txt` files carry no valid rules: Meu INSS answers 403, Carteira de Trabalho Digital 404, and e-CAC and Meu SUS Digital return an HTML page. Under RFC 9309 a 4xx means no restrictions, and a page without rules restricts nothing. | Recorded in `url-changes.md`. No action. |

## Still open from Sprint 1

The five TODO items in `proposta.md` §10 are still open and are listed in `conclusoes.md` §6.
