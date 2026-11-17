#!/usr/bin/env node
// Baixa o robots.txt de cada serviço de data/urls.json e confere se o caminho medido é liberado.
// Grava:
//   - docs/robots-check.md       evidência legível para o relatório
//   - data/robots-check.json     resultado para máquina, lido pelo run-lighthouse.mjs como trava
//   - data/robots/<host>.txt     cópia de cada robots.txt como foi baixado
//
// A interpretação segue a RFC 9309 (Robots Exclusion Protocol):
//   - 2xx            -> lê o arquivo e aplica as regras
//   - 4xx            -> "indisponível": sem restrições (liberado)
//   - 429/5xx/rede   -> "inacessível": assume proibição total (não liberado)
// Uma URL só é marcada como liberada se for liberada para todos os user agents de USER_AGENTS.
//
// Alguns hosts respondem com erro a um User-Agent que não é de navegador (ex.: um WAF devolvendo
// 405) e servem as regras reais para um navegador. Tratar esse erro como "sem restrições" seria
// errado, então toda resposta que não é 2xx é repetida uma vez com o mesmo User-Agent de desktop
// que o Lighthouse envia.
import { join } from 'node:path';
import robotsParser from 'robots-parser';
import { desktopConfig } from 'lighthouse';
import { fetchMissingIntermediate, httpGet } from './lib/http.mjs';
import {
  DATA_DIR, DOCS_DIR, ROBOTS_JSON, URLS_FILE, loadServices, localIsoTimestamp, readJson, sleep, writeJson, writeText,
} from './lib/common.mjs';

// '*' cobre as regras genéricas; os outros dois são os nomes pelos quais o Lighthouse se identifica.
const USER_AGENTS = ['*', 'Lighthouse', 'Chrome-Lighthouse'];
// Valor do cabeçalho User-Agent enviado aos servidores (ASCII, por isso sem acentos).
const IDENTIFYING_UA = 'Mozilla/5.0 (compatible; Lab05-robots-check; academic study, PUC Minas)';
const BROWSER_UA = desktopConfig.settings.emulatedUserAgent;
const PAUSE_BETWEEN_HOSTS_MS = 2_000;
const PAUSE_BEFORE_RETRY_MS = 3_000;
const PAUSE_BEFORE_NETWORK_RETRY_MS = 10_000;
const TIMEOUT_MS = 20_000;

const caByHost = new Map(); // host -> {ca, note} quando a cadeia de certificados do servidor veio incompleta

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
 * Baixa o robots.txt com o UA identificado; se a resposta não for 2xx, tenta de novo com o UA de
 * navegador; se ainda assim não houver status HTTP (erro de rede), tenta mais uma vez depois de
 * uma pausa maior. No máximo três requisições por host.
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
  // Usa a resposta do navegador quando ela é 2xx, ou quando a primeira tentativa nem teve status.
  const chosen = isOk(second) || first.status === null ? second : first;
  return { ...chosen, attempts };
}

function summary(r) {
  return { userAgent: r.userAgent, fetchedAt: r.fetchedAt, status: r.status, error: r.error, tlsNote: r.tlsNote };
}

function evaluate(service, robots) {
  const base = { allowedPerAgent: {}, crawlDelay: null };
  if (robots.error || robots.status === null || robots.status === 429 || robots.status >= 500) {
    return { ...base, verdict: 'unreachable', allowed: false, reason: `robots.txt inacessível (${robots.error ?? `HTTP ${robots.status}`}); pela RFC 9309, assume-se proibição total` };
  }
  if (robots.status >= 400) {
    return { ...base, verdict: 'unavailable', allowed: true, reason: `robots.txt devolveu HTTP ${robots.status}; pela RFC 9309, não há restrições` };
  }
  if (robots.status >= 300) {
    return { ...base, verdict: 'unreachable', allowed: false, reason: `robots.txt continua redirecionando (HTTP ${robots.status}); tratado como inacessível` };
  }
  // Um 2xx que na verdade é uma página HTML (soft 404) não tem regras válidas; o robots-parser então libera tudo.
  const looksLikeHtml = /^\s*<(!doctype|html)/i.test(robots.body);
  const parser = robotsParser(robots.robotsUrl, robots.body);
  const allowedPerAgent = {};
  for (const ua of USER_AGENTS) allowedPerAgent[ua] = parser.isAllowed(service.url, ua) !== false;
  const allowed = Object.values(allowedPerAgent).every(Boolean);
  const delays = USER_AGENTS.map((ua) => parser.getCrawlDelay(ua)).filter((d) => d !== undefined);
  const crawlDelay = delays.length ? Math.max(...delays) : null;
  const blocking = Object.entries(allowedPerAgent).filter(([, ok]) => !ok).map(([ua]) => ua);
  const reason = allowed
    ? (looksLikeHtml ? 'a URL do robots.txt devolveu uma página HTML (sem regras válidas); liberado' : 'caminho liberado para todos os user agents verificados')
    : `caminho proibido para: ${blocking.join(', ')}`;
  return { allowedPerAgent, crawlDelay, verdict: allowed ? 'allowed' : 'disallowed', allowed, reason };
}

function uaLabel(ua) {
  return ua === IDENTIFYING_UA ? 'identificado' : 'navegador (2ª tentativa)';
}

function toMarkdown(results, replaced, generatedAt) {
  const lines = [
    '# Verificação do robots.txt',
    '',
    `Gerado por \`scripts/robots-check.mjs\` em ${generatedAt}.`,
    '',
    `User agents verificados: ${USER_AGENTS.map((u) => `\`${u}\``).join(', ')}. Uma URL só conta como liberada se todos eles forem liberados.`,
    'As regras seguem a RFC 9309: robots.txt com 4xx significa sem restrições; 429, 5xx ou erro de rede significa proibição total.',
    `Cada robots.txt é pedido primeiro com um User-Agent que identifica o estudo (\`${IDENTIFYING_UA}\`). ` +
      'Se a resposta não for 2xx, ele é pedido mais uma vez com o User-Agent de desktop que o Lighthouse envia, ' +
      'porque alguns hosts bloqueiam clientes que não são navegadores. A coluna "UA" diz qual resposta foi usada.',
    'As cópias de cada robots.txt estão em `data/robots/`. O registro completo das tentativas está em `data/robots-check.json`.',
    '',
    '| Serviço | URL | robots.txt | Baixado em | HTTP | UA | Liberado? | Crawl-delay | Observações |',
    '|---|---|---|---|---|---|---|---|---|',
  ];
  for (const r of results) {
    const allowed = r.allowed ? 'sim' : '**NÃO**';
    lines.push(
      `| ${r.name} | ${r.url} | ${r.robotsUrl} | ${r.fetchedAt} | ${r.status ?? '—'} | ${uaLabel(r.userAgent)} | ${allowed} | ${r.crawlDelay ?? '—'} | ${r.reason} |`,
    );
  }
  const blocked = results.filter((r) => !r.allowed);
  lines.push('');
  lines.push(blocked.length
    ? `**${blocked.length} URL(s) não liberada(s)**: precisam ser descartadas e trocadas antes de medir: ${blocked.map((b) => b.id).join(', ')}.`
    : 'Todas as URLs da lista estão liberadas.');
  lines.push('');
  if (replaced.length) {
    lines.push('## Candidatas descartadas', '');
    lines.push('Candidatas retiradas de `data/urls.json`, mantidas aqui como evidência (fonte: a lista `replaced` desse arquivo).', '');
    lines.push('| Candidata | URL | Data | Trocada por | Motivo |', '|---|---|---|---|---|');
    for (const d of replaced) lines.push(`| ${d.candidate} | ${d.url} | ${d.date} | ${d.replacedBy} | ${d.reason} |`);
    lines.push('');
  }
  return lines.join('\n');
}

async function main() {
  const services = await loadServices();
  const { replaced = [] } = await readJson(URLS_FILE);

  const cache = new Map(); // origem -> resultado do download do robots.txt (cada host é baixado uma vez)
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
          `# Baixado de ${robots.robotsUrl} em ${robots.fetchedAt} (HTTP ${robots.status}, URL final ${robots.finalUrl})\n${robots.body}`);
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
    console.log(`${row.allowed ? 'LIBERADO    ' : 'NÃO LIBERADO'} ${service.id.padEnd(16)} HTTP ${row.status ?? '---'} [${uaLabel(row.userAgent)}]  ${row.reason}`);
  }

  const generatedAt = localIsoTimestamp();
  await writeJson(ROBOTS_JSON, { generatedAt, userAgents: USER_AGENTS, results });
  await writeText(join(DOCS_DIR, 'robots-check.md'), toMarkdown(results, replaced, generatedAt));
  console.log(`\nGravados ${ROBOTS_JSON} e docs/robots-check.md`);
  if (results.some((r) => !r.allowed)) process.exitCode = 2;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
