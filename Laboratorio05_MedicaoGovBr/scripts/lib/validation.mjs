// Funções puras usadas por scripts/validate-data.mjs (testadas em tests/lib.test.mjs).
import { quantile } from './metrics.mjs';

export const OUTLIER_COLUMNS = ['service', 'formFactor', 'run', 'metric', 'value', 'q1', 'q3', 'lowerFence', 'upperFence', 'side'];
export const TUKEY_K = 1.5;

/** CSV simples (o extrator só põe aspas em campos com vírgula, aspas ou quebra de linha). */
export function parseCsv(text) {
  const rows = [];
  let field = '';
  let row = [];
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; } else if (c === '"') quoted = false; else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const [header, ...body] = rows.filter((r) => r.length > 1 || r[0] !== '');
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
}

/** Linhas fora da cerca de Tukey, por serviço x form factor x métrica. */
export function tukeyOutliers(rows, metrics, k = TUKEY_K) {
  const out = [];
  const groups = new Map();
  for (const r of rows) {
    const key = `${r.service}|${r.formFactor}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  for (const g of groups.values()) {
    for (const m of metrics) {
      const vals = g.map((r) => Number(r[m]));
      const q1 = quantile(vals, 0.25);
      const q3 = quantile(vals, 0.75);
      const lo = q1 - k * (q3 - q1);
      const hi = q3 + k * (q3 - q1);
      for (const r of g) {
        const v = Number(r[m]);
        if (v < lo || v > hi) {
          out.push({ service: r.service, formFactor: r.formFactor, run: Number(r.run), metric: m, value: v,
            q1, q3, lowerFence: Number(lo.toFixed(4)), upperFence: Number(hi.toFixed(4)), side: v < lo ? 'low' : 'high' });
        }
      }
    }
  }
  return out;
}
