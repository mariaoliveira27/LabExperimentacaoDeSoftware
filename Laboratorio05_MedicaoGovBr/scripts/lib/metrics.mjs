// Turns raw Lighthouse results (LHR) into flat rows for CSV export.
//
// Units in the CSV:
//   performanceScore, accessibilityScore  0-100 (Lighthouse category score x 100)
//   LCP, FCP, TBT, SpeedIndex             milliseconds
//   CLS                                   unitless
//   timestamp                             LHR fetchTime (ISO 8601, UTC)

export const CSV_COLUMNS = [
  'service', 'url', 'formFactor', 'run', 'performanceScore', 'accessibilityScore',
  'LCP', 'FCP', 'TBT', 'CLS', 'SpeedIndex', 'timestamp',
];

export const FAILURE_COLUMNS = ['service', 'url', 'formFactor', 'run', 'timestamp', 'reasonCode', 'reason'];

export const METRIC_AUDITS = {
  LCP: 'largest-contentful-paint',
  FCP: 'first-contentful-paint',
  TBT: 'total-blocking-time',
  CLS: 'cumulative-layout-shift',
  SpeedIndex: 'speed-index',
};

const DIGITS = { LCP: 1, FCP: 1, TBT: 1, SpeedIndex: 1, CLS: 4 };

const round = (v, digits) => (typeof v === 'number' && Number.isFinite(v) ? Number(v.toFixed(digits)) : null);
const toScore = (s) => (typeof s === 'number' ? Math.round(s * 100) : null);

/** Parses "<service>_<formFactor>_<n>.json". Service ids never contain "_". */
export function parseRawFileName(name) {
  const m = /^([a-z0-9-]+)_(mobile|desktop)_(\d+)\.json$/.exec(name);
  return m ? { service: m[1], formFactor: m[2], run: Number(m[3]) } : null;
}

/**
 * @returns {{ok: true, row: object} | {ok: false, failure: object}}
 */
export function rowFromLhr(lhr, { service, formFactor, run }) {
  const actualFormFactor = lhr.configSettings?.formFactor;
  if (actualFormFactor !== formFactor) {
    throw new Error(`${service}_${formFactor}_${run}: file name says ${formFactor} but LHR says ${actualFormFactor}`);
  }
  const base = { service, url: lhr.requestedUrl, formFactor, run, timestamp: lhr.fetchTime };
  if (lhr.runtimeError) {
    return { ok: false, failure: { ...base, reasonCode: lhr.runtimeError.code, reason: lhr.runtimeError.message } };
  }
  const performanceScore = toScore(lhr.categories?.performance?.score);
  const accessibilityScore = toScore(lhr.categories?.accessibility?.score);
  const metrics = Object.fromEntries(
    Object.entries(METRIC_AUDITS).map(([col, id]) => [col, round(lhr.audits?.[id]?.numericValue, DIGITS[col])]),
  );
  const missing = [
    ...(performanceScore === null ? ['performanceScore'] : []),
    ...(accessibilityScore === null ? ['accessibilityScore'] : []),
    ...Object.entries(metrics).filter(([, v]) => v === null).map(([k]) => k),
  ];
  if (missing.length) {
    return { ok: false, failure: { ...base, reasonCode: 'MISSING_VALUES', reason: `null value(s): ${missing.join(', ')}` } };
  }
  return { ok: true, row: { ...base, performanceScore, accessibilityScore, ...metrics } };
}

function csvCell(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return /[",\n\r]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

export function toCsv(rows, columns) {
  return [columns.join(','), ...rows.map((r) => columns.map((c) => csvCell(r[c])).join(','))].join('\n') + '\n';
}

export function median(values) {
  const v = values.filter((x) => typeof x === 'number').sort((a, b) => a - b);
  if (!v.length) return null;
  const mid = Math.floor(v.length / 2);
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

/** Median per (service, formFactor), plus min/max of the performance score. */
export function summarize(rows) {
  const groups = new Map();
  for (const r of rows) {
    const key = `${r.service}|${r.formFactor}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  return [...groups.values()].map((g) => {
    const col = (c) => g.map((r) => r[c]);
    return {
      service: g[0].service,
      formFactor: g[0].formFactor,
      n: g.length,
      performanceScore_median: median(col('performanceScore')),
      performanceScore_min: Math.min(...col('performanceScore')),
      performanceScore_max: Math.max(...col('performanceScore')),
      accessibilityScore_median: median(col('accessibilityScore')),
      LCP_median: median(col('LCP')),
      FCP_median: median(col('FCP')),
      TBT_median: median(col('TBT')),
      CLS_median: median(col('CLS')),
      SpeedIndex_median: median(col('SpeedIndex')),
    };
  });
}

export const SUMMARY_COLUMNS = [
  'service', 'formFactor', 'n', 'performanceScore_median', 'performanceScore_min', 'performanceScore_max',
  'accessibilityScore_median', 'LCP_median', 'FCP_median', 'TBT_median', 'CLS_median', 'SpeedIndex_median',
];
