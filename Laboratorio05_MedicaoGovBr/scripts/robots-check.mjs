#!/usr/bin/env node
// Downloads the robots.txt of every service in data/urls.json and checks whether the
// measured path is allowed. Writes:
//   - docs/robots-check.md       human-readable evidence for the report
//   - data/robots-check.json     machine-readable result, read by run-lighthouse.mjs as a gate
//   - data/robots/<host>.txt     raw copy of each robots.txt as downloaded
//
// Interpretation follows RFC 9309 (Robots Exclusion Protocol):
//   - 2xx           -> parse the file and apply its rules
//   - 4xx           -> "unavailable": no restrictions apply (allowed)
//   - 429/5xx/net   -> "unreachable": assume complete disallow (not allowed)
// A URL is only marked allowed if it is allowed for every user agent in USER_AGENTS.
//
// Some hosts answer a non-browser User-Agent with an error (e.g. a WAF returning 405) while
// serving real rules to a browser. Treating that error as "no restrictions" would be wrong, so
// any non-2xx answer is retried once with the same desktop User-Agent Lighthouse sends.
import { join } from 'node:path';
import robotsParser from 'robots-parser';
import { desktopConfig } from 'lighthouse';
import { fetchMissingIntermediate, httpGet } from './lib/http.mjs';
import {
  DATA_DIR, DOCS_DIR, ROBOTS_JSON, URLS_FILE, loadServices, localIsoTimestamp, readJson, sleep, writeJson, writeText,
} from './lib/common.mjs';

// '*' covers generic rules; the other two are the tokens Lighthouse has been identified by.
const USER_AGENTS = ['*', 'Lighthouse', 'Chrome-Lighthouse'];
const IDENTIFYING_UA = 'Mozilla/5.0 (compatible; Lab05-robots-check; academic study, PUC Minas)';
const BROWSER_UA = desktopConfig.settings.emulatedUserAgent;
const PAUSE_BETWEEN_HOSTS_MS = 2_000;
const PAUSE_BEFORE_RETRY_MS = 3_000;
const PAUSE_BEFORE_NETWORK_RETRY_MS = 10_000;
const TIMEOUT_MS = 20_000;

const caByHost = new Map(); // host -> {ca, note} when the server's certificate chain was incomplete

async function fetchOnce(robotsUrl, userAgent) {
  const fetchedAt = localIsoTimestamp();
  const host = new URL(robotsUrl).host;
  let tlsNote = caByHost.get(host)?.note ?? null;
  try {
    let res;
    try {
      res = await httpGet(robotsUrl, { userAgent, ca: caByHost.get(host)?.ca, timeoutMs: TIMEOUT_MS });
    } catch (err) {
      if (err.code !== 'UNABLE_TO_VERIFY_LEAF_SIGNATURE' || caByHost.has(host)) throw err;
      const fix = await fetchMissingIntermediate(host);
      caByHost.set(host, fix);
      tlsNote = fix.note;
      res = await httpGet(robotsUrl, { userAgent, ca: fix.ca, timeoutMs: TIMEOUT_MS });
    }
    return { robotsUrl, userAgent, finalUrl: res.finalUrl, fetchedAt, status: res.status, body: res.body, error: null, tlsNote };
  } catch (err) {
    return { robotsUrl, userAgent, finalUrl: null, fetchedAt, status: null, body: '', error: `${err.code ?? err.name}: ${err.message}`, tlsNote };
  }
}

const isOk = (r) => r.status !== null && r.status >= 200 && r.status < 300;

/**
 * Fetches robots.txt with the identifying UA; if the answer is not 2xx, retries with the
 * browser UA; if that still has no HTTP status (network error), retries once more after a
 * longer pause. At most three requests per host.
 */
async function fetchRobots(origin) {
  const robotsUrl = `${origin}/robots.txt`;
  const attempts = [];
  const first = await fetchOnce(robotsUrl, IDENTIFYING_UA);
  attempts.push(summary(first));
  if (isOk(first)) return { ...first, attempts };
  await sleep(PAUSE_BEFORE_RETRY_MS);
  let second = await fetchOnce(robotsUrl, BROWSER_UA);
  attempts.push(summary(second));
  if (second.status === null) {
    await sleep(PAUSE_BEFORE_NETWORK_RETRY_MS);
    second = await fetchOnce(robotsUrl, BROWSER_UA);
    attempts.push(summary(second));
  }
  // Use the browser answer when it is a 2xx, or when the first attempt did not even get a status.
  const chosen = isOk(second) || first.status === null ? second : first;
  return { ...chosen, attempts };
}

function summary(r) {
  return { userAgent: r.userAgent, fetchedAt: r.fetchedAt, status: r.status, error: r.error, tlsNote: r.tlsNote };
}

function evaluate(service, robots) {
  const base = { allowedPerAgent: {}, crawlDelay: null };
  if (robots.error || robots.status === null || robots.status === 429 || robots.status >= 500) {
    return { ...base, verdict: 'unreachable', allowed: false, reason: `robots.txt unreachable (${robots.error ?? `HTTP ${robots.status}`}); RFC 9309 says assume full disallow` };
  }
  if (robots.status >= 400) {
    return { ...base, verdict: 'unavailable', allowed: true, reason: `robots.txt returned HTTP ${robots.status}; RFC 9309 says no restrictions apply` };
  }
  if (robots.status >= 300) {
    return { ...base, verdict: 'unreachable', allowed: false, reason: `robots.txt still redirecting (HTTP ${robots.status}); treated as unreachable` };
  }
  // A 2xx that is actually an HTML page (soft 404) has no valid rules; robots-parser then allows all.
  const looksLikeHtml = /^\s*<(!doctype|html)/i.test(robots.body);
  const parser = robotsParser(robots.robotsUrl, robots.body);
  const allowedPerAgent = {};
  for (const ua of USER_AGENTS) allowedPerAgent[ua] = parser.isAllowed(service.url, ua) !== false;
  const allowed = Object.values(allowedPerAgent).every(Boolean);
  const delays = USER_AGENTS.map((ua) => parser.getCrawlDelay(ua)).filter((d) => d !== undefined);
  const crawlDelay = delays.length ? Math.max(...delays) : null;
  const blocking = Object.entries(allowedPerAgent).filter(([, ok]) => !ok).map(([ua]) => ua);
  const reason = allowed
    ? (looksLikeHtml ? 'robots.txt URL returned an HTML page (no valid rules); allowed' : 'path allowed for all checked user agents')
    : `path disallowed for: ${blocking.join(', ')}`;
  return { allowedPerAgent, crawlDelay, verdict: allowed ? 'allowed' : 'disallowed', allowed, reason };
}

function uaLabel(ua) {
  return ua === IDENTIFYING_UA ? 'identifying' : 'browser (retry)';
}

function toMarkdown(results, replaced, generatedAt) {
  const lines = [
    '# robots.txt check',
    '',
    `Generated by \`scripts/robots-check.mjs\` on ${generatedAt}.`,
    '',
    `User agents checked: ${USER_AGENTS.map((u) => `\`${u}\``).join(', ')}. A URL counts as allowed only if every one of them is allowed.`,
    'Rules follow RFC 9309: a 4xx robots.txt means no restrictions; a 429, 5xx or network error means full disallow.',
    `Each robots.txt is first requested with an identifying User-Agent (\`${IDENTIFYING_UA}\`). ` +
      'If the answer is not 2xx, it is requested once more with the desktop User-Agent that Lighthouse sends, ' +
      'because some hosts block non-browser clients. The "UA" column says which answer was used.',
    'Raw copies of each robots.txt are stored in `data/robots/`. The full attempt log is in `data/robots-check.json`.',
    '',
    '| Service | URL | robots.txt | Fetched at | HTTP | UA | Allowed? | Crawl-delay | Notes |',
    '|---|---|---|---|---|---|---|---|---|',
  ];
  for (const r of results) {
    const allowed = r.allowed ? 'yes' : '**NO**';
    lines.push(
      `| ${r.name} | ${r.url} | ${r.robotsUrl} | ${r.fetchedAt} | ${r.status ?? '—'} | ${uaLabel(r.userAgent)} | ${allowed} | ${r.crawlDelay ?? '—'} | ${r.reason} |`,
    );
  }
  const blocked = results.filter((r) => !r.allowed);
  lines.push('');
  lines.push(blocked.length
    ? `**${blocked.length} URL(s) not allowed** — they must be dropped and replaced before measuring: ${blocked.map((b) => b.id).join(', ')}.`
    : 'All listed URLs are allowed.');
  lines.push('');
  if (replaced.length) {
    lines.push('## Discarded candidates', '');
    lines.push('Candidates removed from `data/urls.json`, kept here as evidence (source: the `replaced` list in that file).', '');
    lines.push('| Candidate | URL | Date | Replaced by | Reason |', '|---|---|---|---|---|');
    for (const d of replaced) lines.push(`| ${d.candidate} | ${d.url} | ${d.date} | ${d.replacedBy} | ${d.reason} |`);
    lines.push('');
  }
  return lines.join('\n');
}

async function main() {
  const services = await loadServices();
  const { replaced = [] } = await readJson(URLS_FILE);

  const cache = new Map(); // origin -> robots fetch result (each host is downloaded once)
  const results = [];
  for (const service of services) {
    const origin = new URL(service.url).origin;
    if (!cache.has(origin)) {
      if (cache.size > 0) await sleep(PAUSE_BETWEEN_HOSTS_MS);
      const robots = await fetchRobots(origin);
      cache.set(origin, robots);
      const host = new URL(origin).host;
      if (robots.status !== null) {
        await writeText(join(DATA_DIR, 'robots', `${host}.txt`),
          `# Downloaded from ${robots.robotsUrl} on ${robots.fetchedAt} (HTTP ${robots.status}, final URL ${robots.finalUrl})\n${robots.body}`);
      }
    }
    const robots = cache.get(origin);
    const verdict = evaluate(service, robots);
    if (robots.tlsNote) verdict.reason += ` (TLS: ${robots.tlsNote})`;
    const row = {
      id: service.id, name: service.name, url: service.url,
      robotsUrl: robots.robotsUrl, fetchedAt: robots.fetchedAt, status: robots.status,
      userAgent: robots.userAgent, attempts: robots.attempts,
      ...verdict,
    };
    results.push(row);
    console.log(`${row.allowed ? 'ALLOWED    ' : 'NOT ALLOWED'} ${service.id.padEnd(16)} HTTP ${row.status ?? '---'} [${uaLabel(row.userAgent)}]  ${row.reason}`);
  }

  const generatedAt = localIsoTimestamp();
  await writeJson(ROBOTS_JSON, { generatedAt, userAgents: USER_AGENTS, results });
  await writeText(join(DOCS_DIR, 'robots-check.md'), toMarkdown(results, replaced, generatedAt));
  console.log(`\nWrote ${ROBOTS_JSON} and docs/robots-check.md`);
  if (results.some((r) => !r.allowed)) process.exitCode = 2;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
