#!/usr/bin/env node
// Reads data/raw/<phase>/*.json (raw Lighthouse results) and writes:
//   data/processed/<phase>.csv           one row per successful execution (columns in CSV_COLUMNS)
//   data/processed/<phase>_failures.csv  executions with a Lighthouse runtimeError, a block/challenge page
//                                        (main document not HTTP 200) or missing values
//   data/processed/<phase>_summary.csv   medians per service and form factor
//   data/processed/<phase>_lcp_elements.csv  element used as LCP in each successful execution
//
//   node scripts/extract-metrics.mjs --phase pilot
import { parseArgs } from 'node:util';
import { readdir, readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { DATA_DIR, ROOT, writeText } from './lib/common.mjs';
import {
  CSV_COLUMNS, FAILURE_COLUMNS, LCP_ELEMENT_COLUMNS, SUMMARY_COLUMNS, lcpElement, parseRawFileName, rowFromLhr, summarize, toCsv,
} from './lib/metrics.mjs';

const { values: args } = parseArgs({ options: { phase: { type: 'string', default: 'pilot' } } });

async function main() {
  const phase = args.phase;
  if (!/^[a-z0-9-]+$/.test(phase)) throw new Error('--phase must match [a-z0-9-]+');
  const rawDir = join(DATA_DIR, 'raw', phase);
  if (!existsSync(rawDir)) throw new Error(`${relative(ROOT, rawDir)} does not exist; run the Lighthouse script first`);

  const files = (await readdir(rawDir)).filter((f) => f.endsWith('.json'));
  const rows = [];
  const failures = [];
  const skipped = [];
  const lcpElements = [];
  for (const file of files) {
    const key = parseRawFileName(file);
    if (!key) {
      skipped.push(file);
      continue;
    }
    const lhr = JSON.parse(await readFile(join(rawDir, file), 'utf8'));
    const result = rowFromLhr(lhr, key);
    if (result.ok) {
      rows.push(result.row);
      lcpElements.push({ ...key, ...lcpElement(lhr) });
    } else {
      failures.push(result.failure);
    }
  }
  const byKey = (a, b) => a.service.localeCompare(b.service) || a.formFactor.localeCompare(b.formFactor) || a.run - b.run;
  rows.sort(byKey);
  failures.sort(byKey);
  lcpElements.sort(byKey);
  const summary = summarize(rows).sort(byKey);

  const outDir = join(DATA_DIR, 'processed');
  await writeText(join(outDir, `${phase}.csv`), toCsv(rows, CSV_COLUMNS));
  await writeText(join(outDir, `${phase}_failures.csv`), toCsv(failures, FAILURE_COLUMNS));
  await writeText(join(outDir, `${phase}_summary.csv`), toCsv(summary, SUMMARY_COLUMNS));
  await writeText(join(outDir, `${phase}_lcp_elements.csv`), toCsv(lcpElements, LCP_ELEMENT_COLUMNS));

  console.log(`${files.length} raw file(s): ${rows.length} ok, ${failures.length} failed, ${skipped.length} skipped (unexpected name)`);
  for (const f of skipped) console.log(`  skipped: ${f}`);
  for (const f of failures) console.log(`  failed: ${f.service} ${f.formFactor} #${f.run} — ${f.reasonCode}: ${f.reason}`);
  console.table(summary.map((s) => ({
    service: s.service, formFactor: s.formFactor, n: s.n,
    perf: s.performanceScore_median, 'perf range': `${s.performanceScore_min}-${s.performanceScore_max}`,
    a11y: s.accessibilityScore_median, 'LCP ms': s.LCP_median, 'TBT ms': s.TBT_median, CLS: s.CLS_median,
  })));
  console.log(`Wrote data/processed/${phase}.csv, ${phase}_failures.csv, ${phase}_summary.csv and ${phase}_lcp_elements.csv`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
