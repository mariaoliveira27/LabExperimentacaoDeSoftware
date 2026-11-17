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

// Hosts that serve bot-protection CAPTCHA/challenge pages. Only used as supporting evidence:
// a real page may also load WAF SDK scripts (e.g. *.edge.sdk.awswaf.com), so the decision is
// based on the main document's HTTP status.
const CHALLENGE_HOST_PATTERNS = [/\.captcha\.awswaf\.com$/i, /\.token\.awswaf\.com$/i, /^challenges\.cloudflare\.com$/i];

/**
 * Checks that the run measured the target page and not a block or challenge page.
 * Bot-protection challenges are often served with a non-200 2xx status (AWS WAF uses 202), which
 * Lighthouse does not treat as an error, so a "successful" run can describe the wrong page.
 * @returns {{valid: boolean, mainDocumentStatus: number|null, code?: string, reason?: string}}
 */
export function pageValidity(lhr) {
  const items = lhr.audits?.['network-requests']?.details?.items ?? [];
  const mainUrl = lhr.mainDocumentUrl ?? lhr.finalDisplayedUrl;
  const main = items.find((r) => r.url === mainUrl) ?? items.find((r) => r.resourceType === 'Document');
  const mainDocumentStatus = main?.statusCode ?? null;
  const challengeHosts = [...new Set(items.map((r) => {
    try {
      return new URL(r.url).host;
    } catch {
      return null;
    }
  }).filter((h) => h && CHALLENGE_HOST_PATTERNS.some((p) => p.test(h))))];
  if (mainDocumentStatus !== null && mainDocumentStatus !== 200) {
    const extra = challengeHosts.length ? `; challenge resources from ${challengeHosts.join(', ')}` : '';
    return { valid: false, mainDocumentStatus, code: 'BLOCKED_OR_NOT_200', reason: `main document returned HTTP ${mainDocumentStatus}${extra}` };
  }
  return { valid: true, mainDocumentStatus };
}

export const LCP_ELEMENT_COLUMNS = ['service', 'formFactor', 'run', 'lcpSelector', 'lcpNodeLabel'];

/**
 * Element Lighthouse used as the Largest Contentful Paint. Recorded because the pilot showed that
 * on some pages the LCP element is a cookie-consent modal, not the main content.
 */
export function lcpElement(lhr) {
  const findNode = (v) => {
    if (!v || typeof v !== 'object') return null;
    if (v.type === 'node' && (v.selector || v.nodeLabel)) return v;
    for (const child of Object.values(v)) {
      const found = findNode(child);
      if (found) return found;
    }
    return null;
  };
  const node = findNode(lhr.audits?.['lcp-breakdown-insight']?.details)
    ?? findNode(lhr.audits?.['largest-contentful-paint-element']?.details);
  return { lcpSelector: node?.selector ?? null, lcpNodeLabel: node?.nodeLabel ?? null };
}

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
  const validity = pageValidity(lhr);
  if (!validity.valid) {
    return { ok: false, failure: { ...base, reasonCode: validity.code, reason: validity.reason } };
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
