#!/usr/bin/env node
// Lê data/raw/<fase>/*.json (resultados brutos do Lighthouse) e grava:
//   data/processed/<fase>.csv           uma linha por execução válida (colunas em CSV_COLUMNS)
//   data/processed/<fase>_failures.csv  execuções com runtimeError do Lighthouse, página de bloqueio
//                                       ou desafio, ou valores ausentes
//   data/processed/<fase>_summary.csv   medianas por serviço e form factor
//   data/processed/<fase>_lcp_elements.csv  elemento usado como LCP em cada execução válida
//   data/processed/<fase>_flags.csv     execuções válidas para revisar (CPU do host lenta ou fora da
//                                       faixa, DOM muito menor que o maior da célula, host final
//                                       diferente, recursos de desafio carregados); elas continuam
//                                       em <fase>.csv
//   data/processed/<fase>_executions.csv registro de cada tentativa em data/run-metadata.json
//                                       (sessão, rótulo de horário, bloco, horários em UTC com ms,
//                                       status), usado pela validação e pela análise
//
//   node scripts/extract-metrics.mjs --phase pilot
import { parseArgs } from 'node:util';
import { readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { DATA_DIR, ROOT, RUN_METADATA_FILE, readJson, writeText } from './lib/common.mjs';
import { readLhrFile } from './lib/rawfiles.mjs';
import {
  CSV_COLUMNS, EXECUTION_COLUMNS, FAILURE_COLUMNS, FLAG_COLUMNS, LCP_ELEMENT_COLUMNS, SUMMARY_COLUMNS,
  executionRows, lcpElement, parseRawFileName, reviewFlags, rowFromLhr, runFacts, summarize, toCsv,
} from './lib/metrics.mjs';

const { values: args } = parseArgs({ options: { phase: { type: 'string', default: 'pilot' } } });

async function main() {
  const phase = args.phase;
  if (!/^[a-z0-9-]+$/.test(phase)) throw new Error('--phase precisa seguir o padrão [a-z0-9-]+');
  const rawDir = join(DATA_DIR, 'raw', phase);
  if (!existsSync(rawDir)) throw new Error(`${relative(ROOT, rawDir)} não existe; rode antes o script do Lighthouse`);

  const files = (await readdir(rawDir)).filter((f) => /\.json(\.gz)?$/.test(f) && f !== 'plan.json');
  const rows = [];
  const failures = [];
  const skipped = [];
  const lcpElements = [];
  const facts = [];
  for (const file of files) {
    const key = parseRawFileName(file);
    if (!key) {
      skipped.push(file);
      continue;
    }
    const lhr = await readLhrFile(join(rawDir, file));
    const result = rowFromLhr(lhr, key);
    if (result.ok) {
      rows.push(result.row);
      lcpElements.push({ ...key, ...lcpElement(lhr) });
      facts.push(runFacts(lhr, key));
    } else {
      failures.push(result.failure);
    }
  }
  const byKey = (a, b) => a.service.localeCompare(b.service) || a.formFactor.localeCompare(b.formFactor) || a.run - b.run;
  rows.sort(byKey);
  failures.sort(byKey);
  lcpElements.sort(byKey);
  const summary = summarize(rows).sort(byKey);
  const flags = reviewFlags(facts).sort(byKey);

  const outDir = join(DATA_DIR, 'processed');
  await writeText(join(outDir, `${phase}.csv`), toCsv(rows, CSV_COLUMNS));
  await writeText(join(outDir, `${phase}_failures.csv`), toCsv(failures, FAILURE_COLUMNS));
  await writeText(join(outDir, `${phase}_summary.csv`), toCsv(summary, SUMMARY_COLUMNS));
  await writeText(join(outDir, `${phase}_lcp_elements.csv`), toCsv(lcpElements, LCP_ELEMENT_COLUMNS));
  await writeText(join(outDir, `${phase}_flags.csv`), toCsv(flags, FLAG_COLUMNS));
  const meta = existsSync(RUN_METADATA_FILE) ? await readJson(RUN_METADATA_FILE) : { sessions: [] };
  const executions = executionRows(meta, phase);
  await writeText(join(outDir, `${phase}_executions.csv`), toCsv(executions, EXECUTION_COLUMNS));

  console.log(`${files.length} arquivo(s) bruto(s): ${rows.length} válido(s), ${failures.length} inválido(s), ${skipped.length} ignorado(s) (nome fora do padrão)`);
  for (const f of skipped) console.log(`  ignorado: ${f}`);
  for (const f of failures) console.log(`  inválido: ${f.service} ${f.formFactor} #${f.run} — ${f.reasonCode}: ${f.reason}`);
  console.log(`${flags.length} marcação(ões) para revisão em execuções válidas`);
  for (const f of flags) console.log(`  revisar: ${f.service} ${f.formFactor} #${f.run} — ${f.flag}: ${f.detail}`);
  console.table(summary.map((s) => ({
    serviço: s.service, formFactor: s.formFactor, n: s.n,
    perf: s.performanceScore_median, 'perf mín-máx': `${s.performanceScore_min}-${s.performanceScore_max}`,
    a11y: s.accessibilityScore_median, 'LCP ms': s.LCP_median, 'TBT ms': s.TBT_median, CLS: s.CLS_median,
  })));
  console.log(`Gravados data/processed/${phase}.csv, ${phase}_failures.csv, ${phase}_summary.csv, ${phase}_lcp_elements.csv, ${phase}_flags.csv e ${phase}_executions.csv (${executions.length} tentativas)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
