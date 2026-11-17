# Lab05 — Outside-in measurement of gov.br digital services

Laboratório de Experimentação de Software (PUC Minas). We measure the **public entry pages** of
ten Brazilian government digital services with [Lighthouse](https://github.com/GoogleChrome/lighthouse),
the way an ordinary visitor would load them. This is **not** a load test: executions are
sequential, one URL at a time, with at least 10 s between executions.

Research questions (details, hypotheses and analysis plan in [docs/proposta.md](docs/proposta.md), in Portuguese):

- **RQ1** — Do performance score and LCP differ across the selected services? Which are the worst?
- **RQ2** — Do services with worse performance also have worse accessibility (Lighthouse accessibility score)?
- **RQ3** — How much worse is mobile performance than desktop?

## Ethics rules (enforced by the scripts)

| Rule | How it is enforced |
|---|---|
| Read `robots.txt` before measuring | `scripts/robots-check.mjs` writes `docs/robots-check.md` and `data/robots-check.json`. `run-lighthouse.mjs` refuses any URL that is not marked allowed there, and refuses to run if the check is older than 7 days. |
| Sequential, no parallelism | One Chrome instance and one Lighthouse run at a time. |
| At least 10 s between executions | `--pause` defaults to 10 s and values below 10 s are rejected. A `Crawl-delay` in `robots.txt` is honored if it is longer. |
| Public pages only | `data/urls.json` lists only public entry pages. No login, no form submission, no personal data. |

## Requirements

- Node.js **22.19 or newer** (required by Lighthouse 13). Tested with Node 24.18.0.
- Google Chrome installed (found automatically by `chrome-launcher`; set `CHROME_PATH` to override).
- Pinned dependencies: `lighthouse@13.6.0`, `chrome-launcher@1.2.3`, `robots-parser@3.0.1`.

## Install

```bash
cd Laboratorio05_MedicaoGovBr
npm ci
```

## Run the pilot

```bash
npm run robots          # 1. check robots.txt for every URL in data/urls.json
npm run pilot           # 2. 3 pilot services x 2 form factors x 3 runs = 18 executions (~10 min)
npm run extract:pilot   # 3. build data/processed/pilot*.csv from the raw JSON files
npm test                # unit tests for the plan builder and the metric extractor
```

`npm run pilot` is `node scripts/run-lighthouse.mjs --phase pilot --runs 3`. Pilot services are
the entries with `"pilot": true` in `data/urls.json`.

### Runner options

```bash
node scripts/run-lighthouse.mjs --phase <name> --runs <N> [--services id1,id2] [--seed <int>] [--pause <s>] [--force] [--dry-run]
```

| Option | Default | Meaning |
|---|---|---|
| `--phase` | `pilot` | Output folder `data/raw/<phase>/`. For `pilot`, only services with `"pilot": true` are used; for any other phase, all services. |
| `--runs` | `3` | Executions per service **and** per form factor. |
| `--services` | — | Comma-separated subset of ids from `data/urls.json`. |
| `--seed` | random | Seed of the execution order. Always written to the metadata, so the order can be reproduced. |
| `--pause` | `10` | Seconds between executions (minimum 10). |
| `--force` | off | Overwrite raw files that already exist. |
| `--dry-run` | off | Print the planned order and exit. |

A run is marked `blocked` when its main document is not HTTP 200 (e.g. a bot-protection CAPTCHA served with HTTP 202) or when the text of its LCP element is a bot-challenge message (catches challenges served with HTTP 200). The remaining runs of that service in the session are skipped and logged as `skipped-blocked`.

How one session works:

1. The list of executions (service × form factor × run) is shuffled with a seeded PRNG
   (mulberry32 + Fisher–Yates). `run` is the chronological replicate number within a service and
   form factor (run 1 is the first measurement of that combination in the session).
2. Each execution launches a **fresh headless Chrome with a temporary profile** (cold browser
   cache, i.e. a first visit), runs Lighthouse with only the `performance` and `accessibility`
   categories, saves the raw result, and closes Chrome.
3. Mobile uses Lighthouse's default preset; desktop uses Lighthouse's `desktop-config`. Both use
   simulated throttling (`throttlingMethod: simulate`).
4. If three executions in a row fail with a script error (not a page error), the session stops.
5. Every run is checked for validity: if the main document is not HTTP 200, or the LCP element
   is a challenge message, the run measured a block or challenge page, not the service (see
   "Pilot status" below).

## Where the data is

```
data/
├── urls.json                 # services, URLs, pilot flag, and the list of replaced candidates
├── robots-check.json         # robots.txt verdict per URL (read by the runner as a gate)
├── robots/<host>.txt         # raw copy of each robots.txt as downloaded
├── run-metadata.json         # one entry per session (see below)
├── raw/<phase>/<service>_<formFactor>_<n>.json   # raw Lighthouse result (LHR), one per execution
└── processed/
    ├── <phase>.csv           # one row per successful execution
    ├── <phase>_failures.csv  # runtimeError, block/CAPTCHA page (main document not HTTP 200) or missing values
    ├── <phase>_summary.csv   # medians per service and form factor
    ├── <phase>_lcp_elements.csv  # element Lighthouse used as LCP in each valid run
    └── <phase>_flags.csv     # valid runs to review (see below); they stay in <phase>.csv
docs/
├── robots-check.md           # robots.txt evidence (generated)
└── proposta.md               # study proposal (Portuguese)
analysis/
├── analyze.py                # statistical analysis (RQ1-RQ3)
├── lab_stats.py              # effect sizes and Holm correction
└── requirements.txt          # pinned Python dependencies
```

Review flags in `<phase>_flags.csv`:

| Flag | Meaning |
|---|---|
| `SLOW_HOST_CPU` | `benchmarkIndex` ≤ 1000, Lighthouse's own slow-CPU threshold. Lighthouse only warns about it in the CLI, never through the Node API, so the extractor applies it. |
| `BENCHMARK_LOW_OUTLIER` | `benchmarkIndex` below Tukey's lower fence (Q1 − 1.5 × IQR) of the phase's valid runs. |
| `DOM_SIZE_DROP` | Fewer than half the DOM elements of the largest run of the same service and form factor. |
| `FINAL_HOST_CHANGED` | The final URL's host differs from the requested one. |
| `CHALLENGE_RESOURCES` | The page loaded resources from known CAPTCHA hosts. |

`data/run-metadata.json` holds, per session: phase, seed, planned order, Lighthouse and
chrome-launcher versions, Chrome version, Chrome flags, the Lighthouse settings used per form
factor (throttling, screen emulation, user agent, timeouts), OS, CPU, RAM, Node version,
time zone, the active power plan and the network adapter of the default route (media type, link
speed, physical or virtual; no IP, MAC, SSID or provider is read), and for every execution its
start/end time, duration, status, final URL, `runtimeError`, `runWarnings` and Lighthouse's
`benchmarkIndex` for the host.

### CSV columns (`data/processed/<phase>.csv`)

| Column | Unit | Source in the LHR |
|---|---|---|
| `service` | id | file name |
| `url` | — | `requestedUrl` |
| `formFactor` | `mobile` / `desktop` | `configSettings.formFactor` |
| `run` | integer | file name |
| `performanceScore` | 0–100 | `categories.performance.score` × 100 |
| `accessibilityScore` | 0–100 | `categories.accessibility.score` × 100 |
| `LCP` | ms | `audits["largest-contentful-paint"].numericValue` |
| `FCP` | ms | `audits["first-contentful-paint"].numericValue` |
| `TBT` | ms | `audits["total-blocking-time"].numericValue` |
| `CLS` | unitless | `audits["cumulative-layout-shift"].numericValue` |
| `SpeedIndex` | ms | `audits["speed-index"].numericValue` |
| `timestamp` | ISO 8601, UTC | `fetchTime` |

## Statistical analysis

Python 3.12 with the pinned packages in `analysis/requirements.txt`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r analysis/requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m unittest discover -s analysis
.venv/Scripts/python analysis/analyze.py --phases full-b1,full-b2,full-b3
```

Each phase is read as one time block. Tables go to `data/analysis/<phases>/` (or `--out`):
descriptives, invalid and excluded runs, LCP elements, block medians, run 1 vs later runs,
Kruskal–Wallis + ε² + Dunn (RQ1), Spearman + Kendall τ-b (RQ2), paired Wilcoxon + Cliff's δ +
paired rank-biserial + sign test (RQ3), and `analysis-metadata.json` with options and versions.
Services no longer in `data/urls.json` are left out.

The main analysis excludes runs flagged `SLOW_HOST_CPU`. Sensitivity analyses are reruns:
`--exclude-flags all` drops every flagged run, and `--exclude-services govbr,svr-bcb` drops
services (e.g. those whose LCP element is a cookie banner).

On the pilot data the script runs, but with 3 runs per cell its tests are not results.

## Replacing a service

1. Edit `data/urls.json`: change the entry and add the old one to `replaced` with the date and reason.
2. Run `npm run robots` again. The runner will not start until the new URL is checked and allowed.

## Pilot status (2026-11-17)

24 executions in two sessions (seeds 41872753 and 484856555), no script errors, minimum gap
between executions 10.00 s. Pilot services: `govbr`, `meuinss`, `svr-bcb`.

- Portal da Transparência was in the first session but served an AWS WAF CAPTCHA (HTTP 202) to
  4 of 6 runs. It was replaced by Valores a Receber (`svr-bcb`); its raw files are kept in
  `data/raw/pilot/` as evidence and the extractor lists them in `pilot_failures.csv`.
- Pilot medians and what the pilot showed are in [docs/proposta.md](docs/proposta.md), section 9.

## Notes from setting up

- Some hosts answer non-browser user agents differently (e.g. `portaldatransparencia.gov.br`
  returned HTTP 405 for `robots.txt` to a custom user agent and 200 to a browser user agent). The
  robots check therefore retries non-2xx answers with the user agent Lighthouse sends.
- `cav.receita.fazenda.gov.br` sends an incomplete TLS chain. Browsers fetch the missing
  intermediate via AIA; Node does not. The robots check does the same as a browser and only
  accepts the intermediate if it verifies against a root in Node's trust store.
