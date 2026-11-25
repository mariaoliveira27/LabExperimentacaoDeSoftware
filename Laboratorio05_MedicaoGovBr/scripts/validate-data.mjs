#!/usr/bin/env node
// Valida os dados processados de uma fase e grava docs/data-validation.md.
//
//   node scripts/validate-data.mjs --phase full
//
// Lê data/raw/<fase>/plan.json, data/processed/<fase>.csv, <fase>_failures.csv, <fase>_executions.csv,
// <fase>_flags.csv e data/failed-runs.csv (rode antes `node scripts/extract-metrics.mjs --phase <fase>`).
//
// Verificações (erro = o dado não pode ser usado como está; aviso = registrar e seguir):
//   1. toda execução do plano tem uma linha válida em <fase>.csv                       (erro)
//   2. nenhuma métrica vazia, NaN ou infinita                                          (erro)
//   3. faixas: scores inteiros em 0-100 (score do Lighthouse 0-1 x 100); LCP, FCP e
//      Speed Index > 0 ms; TBT >= 0 ms e CLS >= 0 (zero é valor legítimo nos dois)     (erro)
//      LCP >= FCP (o maior elemento não pode pintar antes do primeiro)                  (aviso)
//   4. sem linhas repetidas por (serviço, form factor, run); sem dois brutos para a
//      mesma execução; URL igual à de data/urls.json                                   (erro)
//   5. horários: pausa >= 10 s entre o fim de uma tentativa e o início da seguinte na
//      mesma sessão (UTC com ms); sessões sem sobreposição (nada em paralelo); fetchTime
//      do LHR dentro da janela da tentativa que gerou o arquivo                        (erro)
//   6. outliers: cerca de Tukey (Q1 - 1,5 IQR, Q3 + 1,5 IQR) por serviço x form factor
//      x métrica. Só marca; nada é apagado. Saída em data/processed/<fase>_outliers.csv (aviso)
import { parseArgs } from 'node:util';
import { existsSync } from 'node:fs';
import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { DATA_DIR, DOCS_DIR, FAILED_RUNS_FILE, MIN_PAUSE_MS, loadServices, localIsoTimestamp, readJson, writeText } from './lib/common.mjs';
import { FORM_FACTORS } from './lib/plan.mjs';
import { RAW_NAME_RE } from './lib/rawfiles.mjs';
import { quantile, toCsv } from './lib/metrics.mjs';
import { OUTLIER_COLUMNS, TUKEY_K, parseCsv, tukeyOutliers } from './lib/validation.mjs';

const { values: args } = parseArgs({ options: { phase: { type: 'string', default: 'full' } } });

const SCORE_COLS = ['performanceScore', 'accessibilityScore'];
const POSITIVE_COLS = ['LCP', 'FCP', 'SpeedIndex'];
const NON_NEGATIVE_COLS = ['TBT', 'CLS'];
const METRIC_COLS = [...SCORE_COLS, ...POSITIVE_COLS, ...NON_NEGATIVE_COLS];

async function readCsv(path) {
  return existsSync(path) ? parseCsv(await readFile(path, 'utf8')) : null;
}

const fmt = (n, d = 1) => (Number.isFinite(n) ? n.toFixed(d).replace('.', ',') : '—');

async function main() {
  const phase = args.phase;
  const errors = [];
  const warnings = [];
  const P = (name) => join(DATA_DIR, 'processed', `${phase}${name}.csv`);
  const rawDir = join(DATA_DIR, 'raw', phase);
  const planFile = join(rawDir, 'plan.json');
  if (!existsSync(planFile)) throw new Error(`${planFile} não existe`);
  const planDoc = await readJson(planFile);
  const rows = await readCsv(P(''));
  if (!rows) throw new Error(`data/processed/${phase}.csv não existe; rode antes o extrator`);
  const failures = (await readCsv(P('_failures'))) ?? [];
  const executions = (await readCsv(P('_executions'))) ?? [];
  const flags = (await readCsv(P('_flags'))) ?? [];
  const failedRuns = ((await readCsv(FAILED_RUNS_FILE)) ?? []).filter((r) => r.phase === phase);
  const services = await loadServices();
  const urlOf = Object.fromEntries(services.map((s) => [s.id, s.url]));
  const keyOf = (r) => `${r.service}_${r.formFactor}_${r.run}`;

  // 1. completude
  const expected = planDoc.plan.map((p) => p.key);
  const rowKeys = new Map();
  for (const r of rows) rowKeys.set(keyOf(r), (rowKeys.get(keyOf(r)) ?? 0) + 1);
  const failureByKey = new Map(failures.map((f) => [keyOf(f), f]));
  const missing = expected.filter((k) => !rowKeys.has(k));
  for (const k of missing) {
    const f = failureByKey.get(k);
    errors.push(`execução sem linha válida: ${k}${f ? ` (bruto inválido: ${f.reasonCode})` : ' (sem arquivo bruto)'}`);
  }
  const unexpected = [...rowKeys.keys()].filter((k) => !expected.includes(k));
  for (const k of unexpected) errors.push(`linha fora do plano: ${k}`);

  // 2 e 3. valores e faixas
  for (const r of rows) {
    for (const c of METRIC_COLS) {
      const v = r[c] === '' ? NaN : Number(r[c]);
      if (!Number.isFinite(v)) { errors.push(`${keyOf(r)}: ${c} vazio ou NaN ("${r[c]}")`); continue; }
      if (SCORE_COLS.includes(c) && !(Number.isInteger(v) && v >= 0 && v <= 100)) errors.push(`${keyOf(r)}: ${c} = ${v} fora de 0-100`);
      if (POSITIVE_COLS.includes(c) && !(v > 0)) errors.push(`${keyOf(r)}: ${c} = ${v} não é > 0`);
      if (NON_NEGATIVE_COLS.includes(c) && !(v >= 0)) errors.push(`${keyOf(r)}: ${c} = ${v} é negativo`);
    }
    if (Number(r.LCP) < Number(r.FCP)) warnings.push(`${keyOf(r)}: LCP (${r.LCP}) < FCP (${r.FCP})`);
    if (r.url !== urlOf[r.service]) errors.push(`${keyOf(r)}: URL ${r.url} difere de data/urls.json (${urlOf[r.service]})`);
    if (Number.isNaN(Date.parse(r.timestamp))) errors.push(`${keyOf(r)}: timestamp inválido "${r.timestamp}"`);
  }

  // 4. duplicatas
  for (const [k, n] of rowKeys) if (n > 1) errors.push(`linha repetida ${n}x: ${k}`);
  const rawNames = (await readdir(rawDir)).filter((f) => RAW_NAME_RE.test(f));
  const rawCount = new Map();
  for (const f of rawNames) {
    const m = RAW_NAME_RE.exec(f);
    const k = `${m[1]}_${m[2]}_${m[3]}`;
    rawCount.set(k, (rawCount.get(k) ?? 0) + 1);
  }
  for (const [k, n] of rawCount) if (n > 1) errors.push(`${n} arquivos brutos para ${k} (.json e .json.gz)`);

  // 5. horários
  const ran = executions.filter((e) => e.startedAtUtc && e.finishedAtUtc);
  const bySession = new Map();
  for (const e of ran) {
    if (!bySession.has(e.sessionId)) bySession.set(e.sessionId, []);
    bySession.get(e.sessionId).push(e);
  }
  const gaps = [];
  const sessionWindows = [];
  for (const [sid, list] of bySession) {
    list.sort((a, b) => Date.parse(a.startedAtUtc) - Date.parse(b.startedAtUtc));
    for (let i = 1; i < list.length; i++) {
      const gap = Date.parse(list[i].startedAtUtc) - Date.parse(list[i - 1].finishedAtUtc);
      gaps.push(gap);
      if (gap < MIN_PAUSE_MS) errors.push(`${sid}: pausa de ${gap} ms antes de ${list[i].service}_${list[i].formFactor}_${list[i].run} (mínimo ${MIN_PAUSE_MS})`);
    }
    sessionWindows.push({ sid, label: list[0].sessionLabel, start: Date.parse(list[0].startedAtUtc), end: Date.parse(list.at(-1).finishedAtUtc), n: list.length });
  }
  sessionWindows.sort((a, b) => a.start - b.start);
  for (let i = 1; i < sessionWindows.length; i++) {
    if (sessionWindows[i].start < sessionWindows[i - 1].end) errors.push(`sessões sobrepostas: ${sessionWindows[i - 1].sid} e ${sessionWindows[i].sid}`);
  }
  // a tentativa que gerou cada linha válida é a última 'ok' com aquele arquivo
  const okByKey = new Map();
  for (const e of ran) if (e.status === 'ok') okByKey.set(keyOf(e), e);
  for (const r of rows) {
    const e = okByKey.get(keyOf(r));
    if (!e) { errors.push(`${keyOf(r)}: nenhuma tentativa 'ok' em run-metadata.json`); continue; }
    const t = Date.parse(r.timestamp);
    if (t < Date.parse(e.startedAtUtc) || t > Date.parse(e.finishedAtUtc)) errors.push(`${keyOf(r)}: fetchTime ${r.timestamp} fora da janela da tentativa (${e.startedAtUtc} a ${e.finishedAtUtc})`);
  }

  // 6. outliers
  const outliers = tukeyOutliers(rows, METRIC_COLS);
  outliers.sort((a, b) => a.service.localeCompare(b.service) || a.formFactor.localeCompare(b.formFactor) || a.metric.localeCompare(b.metric) || a.run - b.run);
  await writeText(P('_outliers'), toCsv(outliers, OUTLIER_COLUMNS));

  // ---- relatório
  const labelOfKey = new Map([...okByKey].map(([k, e]) => [k, e.sessionLabel || '—']));
  const labels = [...new Set([...labelOfKey.values()])].sort();
  const L = [];
  L.push('# Validação dos dados da coleta completa', '');
  L.push(`Gerado por \`scripts/validate-data.mjs --phase ${phase}\` em ${localIsoTimestamp()}. Não edite à mão: rode o script de novo.`, '');
  L.push(`Plano: \`data/raw/${phase}/plan.json\`, seed ${planDoc.seed}, ${planDoc.runs} execuções por serviço e form factor em ${planDoc.blocks} blocos, ${expected.length} execuções esperadas.`, '');
  L.push('## Resumo', '');
  L.push('| Item | Valor |', '|---|---|');
  L.push(`| Execuções esperadas | ${expected.length} |`);
  L.push(`| Linhas válidas em \`${phase}.csv\` | ${rows.length} |`);
  L.push(`| Execuções sem linha válida | ${missing.length} |`);
  L.push(`| Tentativas registradas em \`run-metadata.json\` | ${executions.length} (${Object.entries(executions.reduce((a, e) => ({ ...a, [e.status]: (a[e.status] ?? 0) + 1 }), {})).map(([k, v]) => `${k}: ${v}`).join(', ')}) |`);
  L.push(`| Linhas em \`data/failed-runs.csv\` desta fase | ${failedRuns.length} |`);
  L.push(`| Brutos inválidos ainda na pasta (\`${phase}_failures.csv\`) | ${failures.length} |`);
  L.push(`| Erros | **${errors.length}** |`);
  L.push(`| Avisos | ${warnings.length} |`);
  L.push(`| Valores fora da cerca de Tukey (marcados, não removidos) | ${outliers.length} em ${new Set(outliers.map((o) => `${o.service}_${o.formFactor}_${o.run}`)).size} execuções |`);
  L.push(`| Pausa entre tentativas (mín. / mediana) | ${fmt(Math.min(...gaps) / 1000, 3)} s / ${fmt(quantile(gaps, 0.5) / 1000, 3)} s |`);
  L.push('');
  L.push('## Sessões', '');
  L.push('| Sessão | Rótulo | Início (UTC) | Fim (UTC) | Tentativas com horário |', '|---|---|---|---|---|');
  for (const w of sessionWindows) L.push(`| ${w.sid} | ${w.label || '—'} | ${new Date(w.start).toISOString()} | ${new Date(w.end).toISOString()} | ${w.n} |`);
  L.push('');
  L.push('## Execuções válidas por serviço × form factor × horário', '');
  L.push(`| Serviço | Form factor | ${labels.join(' | ')} | Total | Esperado |`, `|---|---|${labels.map(() => '---|').join('')}---|---|`);
  for (const s of services) {
    for (const ff of FORM_FACTORS) {
      const keys = expected.filter((k) => k.startsWith(`${s.id}_${ff}_`));
      const valid = keys.filter((k) => rowKeys.has(k));
      const per = labels.map((lab) => valid.filter((k) => labelOfKey.get(k) === lab).length);
      L.push(`| ${s.id} | ${ff} | ${per.join(' | ')} | ${valid.length} | ${keys.length} |`);
    }
  }
  L.push('');
  L.push('## Erros', '');
  L.push(errors.length ? errors.map((e) => `- ${e}`).join('\n') : 'Nenhum.');
  L.push('', '## Avisos', '');
  L.push(warnings.length ? warnings.map((e) => `- ${e}`).join('\n') : 'Nenhum.');
  L.push('', '## Tentativas que falharam (`data/failed-runs.csv`)', '');
  if (failedRuns.length) {
    L.push('| Sessão | Rótulo | Execução | Status | Código | Motivo |', '|---|---|---|---|---|---|');
    for (const f of failedRuns) L.push(`| ${f.sessionId} | ${f.sessionLabel} | ${keyOf(f)} | ${f.status} | ${f.reasonCode} | ${f.reason.replaceAll('|', '/').slice(0, 160)} |`);
  } else L.push('Nenhuma.');
  L.push('', '## Marcações de revisão (`' + phase + '_flags.csv`)', '');
  if (flags.length) {
    const byFlag = flags.reduce((a, f) => ({ ...a, [f.flag]: [...(a[f.flag] ?? []), keyOf(f)] }), {});
    for (const [flag, keys] of Object.entries(byFlag)) L.push(`- \`${flag}\`: ${keys.length} (${keys.join(', ')})`);
  } else L.push('Nenhuma.');
  L.push('', '## Outliers (regra de Tukey)', '');
  L.push(`Regra: dentro de cada serviço × form factor, um valor é outlier se fica abaixo de Q1 − ${TUKEY_K} × IQR ou acima de Q3 + ${TUKEY_K} × IQR (quantis com interpolação linear). As execuções **não são removidas**: a análise roda com todas as execuções e de novo sem as marcadas (ver \`analysis/results.md\`). Lista completa em \`data/processed/${phase}_outliers.csv\`.`, '');
  if (outliers.length) {
    const byCell = new Map();
    for (const o of outliers) {
      const k = `${o.service}|${o.formFactor}|${o.metric}`;
      if (!byCell.has(k)) byCell.set(k, []);
      byCell.get(k).push(o);
    }
    L.push('| Serviço | Form factor | Métrica | Runs (valor) | Cercas |', '|---|---|---|---|---|');
    for (const list of byCell.values()) {
      const o = list[0];
      L.push(`| ${o.service} | ${o.formFactor} | ${o.metric} | ${list.map((x) => `${x.run} (${x.value})`).join(', ')} | ${o.lowerFence} a ${o.upperFence} |`);
    }
  } else L.push('Nenhum.');
  L.push('');
  await writeText(join(DOCS_DIR, 'data-validation.md'), L.join('\n'));

  console.log(`${rows.length}/${expected.length} execuções válidas; ${errors.length} erro(s), ${warnings.length} aviso(s), ${outliers.length} valor(es) fora da cerca de Tukey`);
  for (const e of errors.slice(0, 20)) console.log(`  ERRO ${e}`);
  if (errors.length > 20) console.log(`  ... e mais ${errors.length - 20}`);
  console.log('Gravados docs/data-validation.md e data/processed/' + phase + '_outliers.csv');
  if (errors.length) process.exitCode = 1;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
