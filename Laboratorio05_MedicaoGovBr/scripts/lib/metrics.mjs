// Converte os resultados brutos do Lighthouse (LHR) em linhas para exportar em CSV.
//
// Unidades no CSV:
//   performanceScore, accessibilityScore  0-100 (score da categoria no Lighthouse x 100)
//   LCP, FCP, TBT, SpeedIndex             milissegundos
//   CLS                                   sem unidade
//   timestamp                             fetchTime do LHR (ISO 8601, UTC)

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

// Hosts que servem páginas de CAPTCHA/desafio anti-bot. Usados só como evidência de apoio: uma
// página real também pode carregar scripts do SDK do WAF (ex.: *.edge.sdk.awswaf.com), então a
// decisão se baseia no status HTTP do documento principal.
const CHALLENGE_HOST_PATTERNS = [/\.captcha\.awswaf\.com$/i, /\.token\.awswaf\.com$/i, /^challenges\.cloudflare\.com$/i];

// Textos de páginas de desafio anti-bot, comparados com o texto do elemento LCP. Numa página de
// desafio, o maior texto é a mensagem do desafio. Só o texto do AWS WAF foi visto neste estudo
// (piloto, Portal da Transparência: "Complete the security check before continuing..."); os
// outros são textos comuns desse tipo de página. Todos são frases de várias palavras, para que o
// texto normal de uma página (ex.: um banner de cookies) não case com eles.
const CHALLENGE_TEXT_PATTERNS = [
  /complete the security check/i,
  /\b(confirm|verify) (that )?you are (a )?human\b/i,
  /\bchecking (if the site connection is secure|your browser)\b/i,
  /\bjust a moment\.\.\./i,
  /verifica[cç][aã]o de seguran[cç]a/i,
  /\b(confirme|verifique) (que|se) voc[eê] [eé] (um )?humano\b/i,
];

const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
};

function challengeHostsOf(items) {
  return [...new Set(items.map((r) => hostOf(r.url)).filter((h) => h && CHALLENGE_HOST_PATTERNS.some((p) => p.test(h))))];
}

/**
 * Confere se a execução mediu a página do serviço, e não uma página de bloqueio ou de desafio.
 * Regra 1: o documento principal precisa voltar com HTTP 200. Desafios anti-bot costumam vir com
 * um status 2xx diferente de 200 (o AWS WAF usa 202), que o Lighthouse não trata como erro; assim
 * uma execução "bem-sucedida" pode descrever a página errada.
 * Regra 2: o elemento LCP não pode ser uma mensagem de desafio. Pega desafios servidos com HTTP 200.
 * @returns {{valid: boolean, mainDocumentStatus: number|null, code?: string, reason?: string}}
 */
export function pageValidity(lhr) {
  const items = lhr.audits?.['network-requests']?.details?.items ?? [];
  const mainUrl = lhr.mainDocumentUrl ?? lhr.finalDisplayedUrl;
  const main = items.find((r) => r.url === mainUrl) ?? items.find((r) => r.resourceType === 'Document');
  const mainDocumentStatus = main?.statusCode ?? null;
  const challengeHosts = challengeHostsOf(items);
  const extra = challengeHosts.length ? `; recursos de desafio carregados de ${challengeHosts.join(', ')}` : '';
  if (mainDocumentStatus !== null && mainDocumentStatus !== 200) {
    return { valid: false, mainDocumentStatus, code: 'BLOCKED_OR_NOT_200', reason: `documento principal devolveu HTTP ${mainDocumentStatus}${extra}` };
  }
  const label = (lcpElement(lhr).lcpNodeLabel ?? '').replace(/\s+/g, ' ');
  const pattern = CHALLENGE_TEXT_PATTERNS.find((p) => p.test(label));
  if (pattern) {
    return {
      valid: false, mainDocumentStatus, code: 'CHALLENGE_PAGE',
      reason: `texto do elemento LCP é uma mensagem de desafio anti-bot (${pattern}): "${label.slice(0, 80)}"${extra}`,
    };
  }
  return { valid: true, mainDocumentStatus };
}

// Limiar do próprio Lighthouse (core/gather/driver/environment.js, SLOW_CPU_BENCHMARK_INDEX_THRESHOLD).
// O Lighthouse só mostra o aviso de CPU lenta na CLI, então execuções pela API Node nunca o recebem.
export const SLOW_CPU_BENCHMARK_INDEX = 1000;
// Uma execução válida cujo DOM tem menos elementos do que esta fração do maior DOM visto no mesmo
// serviço e form factor é marcada. No piloto, o número de elementos variou menos de 0,1% dentro de
// uma célula, enquanto a página de CAPTCHA tinha 44 elementos contra 1318 a 1800 da página real.
export const DOM_DROP_RATIO = 0.5;

export const FLAG_COLUMNS = ['service', 'formFactor', 'run', 'timestamp', 'flag', 'detail'];

/** Valores de cada execução usados por reviewFlags(). */
export function runFacts(lhr, { service, formFactor, run }) {
  const items = lhr.audits?.['network-requests']?.details?.items ?? [];
  return {
    service, formFactor, run, timestamp: lhr.fetchTime,
    benchmarkIndex: lhr.environment?.benchmarkIndex ?? null,
    domElements: lhr.audits?.['dom-size-insight']?.numericValue ?? lhr.audits?.['dom-size']?.numericValue ?? null,
    requestedHost: hostOf(lhr.requestedUrl),
    finalHost: hostOf(lhr.finalDisplayedUrl),
    challengeHosts: challengeHostsOf(items),
  };
}

/** Quantil com interpolação linear (igual ao tipo 7 do R e ao padrão do numpy). */
export function quantile(values, q) {
  const v = values.filter((x) => typeof x === 'number').sort((a, b) => a - b);
  if (!v.length) return null;
  const pos = (v.length - 1) * q;
  const lo = Math.floor(pos);
  return v[lo] + (v[Math.min(lo + 1, v.length - 1)] - v[lo]) * (pos - lo);
}

/**
 * Marca execuções válidas para revisão manual. As marcações não tiram linhas do CSV: a análise é
 * feita com e sem as execuções marcadas (análise de sensibilidade, docs/proposta.md seção 7.6).
 * @param {ReturnType<typeof runFacts>[]} facts execuções válidas de uma fase
 */
export function reviewFlags(facts) {
  const flags = [];
  const add = (f, flag, detail) => flags.push({ service: f.service, formFactor: f.formFactor, run: f.run, timestamp: f.timestamp, flag, detail });

  // Cerca inferior de Tukey sobre o benchmarkIndex de todas as execuções válidas da fase (um bloco de horário).
  const bi = facts.map((f) => f.benchmarkIndex);
  const q1 = quantile(bi, 0.25);
  const q3 = quantile(bi, 0.75);
  const fence = q1 === null ? null : q1 - 1.5 * (q3 - q1);

  const maxDom = new Map();
  for (const f of facts) {
    const key = `${f.service}|${f.formFactor}`;
    if (typeof f.domElements === 'number') maxDom.set(key, Math.max(maxDom.get(key) ?? 0, f.domElements));
  }

  for (const f of facts) {
    if (typeof f.benchmarkIndex === 'number') {
      if (f.benchmarkIndex <= SLOW_CPU_BENCHMARK_INDEX) {
        add(f, 'SLOW_HOST_CPU', `benchmarkIndex ${f.benchmarkIndex} <= ${SLOW_CPU_BENCHMARK_INDEX} (limiar de CPU lenta do Lighthouse)`);
      } else if (fence !== null && f.benchmarkIndex < fence) {
        add(f, 'BENCHMARK_LOW_OUTLIER', `benchmarkIndex ${f.benchmarkIndex} < cerca inferior de Tukey ${fence.toFixed(1)} (Q1 ${q1.toFixed(1)}, Q3 ${q3.toFixed(1)})`);
      }
    }
    const max = maxDom.get(`${f.service}|${f.formFactor}`);
    if (typeof f.domElements === 'number' && max && f.domElements < DOM_DROP_RATIO * max) {
      add(f, 'DOM_SIZE_DROP', `${f.domElements} elementos DOM < ${DOM_DROP_RATIO * 100}% da maior execução desta célula (${max})`);
    }
    if (f.requestedHost && f.finalHost && f.requestedHost !== f.finalHost) {
      add(f, 'FINAL_HOST_CHANGED', `pedido ${f.requestedHost}, final ${f.finalHost}`);
    }
    if (f.challengeHosts.length) {
      add(f, 'CHALLENGE_RESOURCES', `carregou ${f.challengeHosts.join(', ')}`);
    }
  }
  return flags;
}

export const LCP_ELEMENT_COLUMNS = ['service', 'formFactor', 'run', 'lcpSelector', 'lcpNodeLabel'];

/**
 * Elemento que o Lighthouse usou como Largest Contentful Paint. Registrado porque o piloto mostrou
 * que em algumas páginas o elemento LCP é um modal de consentimento de cookies, e não o conteúdo principal.
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

/** Lê "<servico>_<formFactor>_<n>.json" ou ".json.gz". Ids de serviço nunca têm "_". */
export function parseRawFileName(name) {
  const m = /^([a-z0-9-]+)_(mobile|desktop)_(\d+)\.json(?:\.gz)?$/.exec(name);
  return m ? { service: m[1], formFactor: m[2], run: Number(m[3]) } : null;
}

/**
 * @returns {{ok: true, row: object} | {ok: false, failure: object}}
 */
export function rowFromLhr(lhr, { service, formFactor, run }) {
  const actualFormFactor = lhr.configSettings?.formFactor;
  if (actualFormFactor !== formFactor) {
    throw new Error(`${service}_${formFactor}_${run}: o nome do arquivo diz ${formFactor}, mas o LHR diz ${actualFormFactor}`);
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
    return { ok: false, failure: { ...base, reasonCode: 'MISSING_VALUES', reason: `valor(es) nulo(s): ${missing.join(', ')}` } };
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

/** Mediana por (serviço, form factor), mais o mínimo e o máximo do performance score. */
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

export const EXECUTION_COLUMNS = [
  'sessionId', 'sessionLabel', 'block', 'order', 'service', 'formFactor', 'run', 'status',
  'startedAtUtc', 'finishedAtUtc', 'durationMs', 'benchmarkIndex', 'file',
];

/**
 * Uma linha por tentativa registrada em run-metadata.json para a fase, na ordem em que aconteceram.
 * Sessões antigas (piloto) não têm finishedAtUtc nem rótulo; finishedAtUtc é então derivado de
 * startedAtUtc + durationMs.
 */
export function executionRows(meta, phase) {
  const rows = [];
  for (const s of meta.sessions ?? []) {
    if (s.phase !== phase) continue;
    for (const e of s.executions ?? []) {
      const finished = e.finishedAtUtc
        ?? (e.startedAtUtc && typeof e.durationMs === 'number' ? new Date(new Date(e.startedAtUtc).getTime() + e.durationMs).toISOString() : null);
      rows.push({
        sessionId: s.sessionId, sessionLabel: e.sessionLabel ?? s.sessionLabel ?? '', block: e.block ?? s.block ?? '',
        order: e.order, service: e.serviceId, formFactor: e.formFactor, run: e.run, status: e.status,
        startedAtUtc: e.startedAtUtc ?? '', finishedAtUtc: finished ?? '', durationMs: e.durationMs ?? '',
        benchmarkIndex: e.benchmarkIndex ?? '', file: e.file ?? '',
      });
    }
  }
  return rows;
}
