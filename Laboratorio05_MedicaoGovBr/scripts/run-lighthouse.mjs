#!/usr/bin/env node
// Roda o Lighthouse em cada serviço, N vezes por form factor (mobile e desktop), em sequência,
// em ordem aleatória com seed e com pausa de pelo menos 10 s entre execuções.
//
//   node scripts/run-lighthouse.mjs --phase pilot --runs 3
//   node scripts/run-lighthouse.mjs --phase full --runs 10 --seed 12345
//
// Opções:
//   --phase <nome>      pasta de saída dentro de data/raw/ (padrão: pilot)
//   --runs <N>          execuções por serviço e por form factor (padrão: 3)
//   --services <ids>    ids de data/urls.json separados por vírgula
//                       (padrão: serviços com "pilot": true na fase pilot; todos nas outras)
//   --seed <inteiro>    seed da ordem de execução (padrão: sorteada, sempre gravada)
//   --pause <segundos>  pausa entre execuções, mínimo 10 (padrão: 10)
//   --force             sobrescreve arquivos brutos que já existem
//   --dry-run           mostra a ordem planejada e sai sem rodar o Lighthouse
//
// Saídas:
//   data/raw/<fase>/<servico>_<formFactor>_<n>.json   resultado bruto do Lighthouse (LHR)
//   data/run-metadata.json                            uma entrada por sessão (acrescentada ao fim)
import { parseArgs } from 'node:util';
import { existsSync } from 'node:fs';
import { writeFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join, relative } from 'node:path';
import os from 'node:os';
import lighthouse, { desktopConfig } from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import {
  DATA_DIR, MIN_PAUSE_MS, ROBOTS_JSON, ROOT, RUN_METADATA_FILE,
  loadServices, localIsoTimestamp, readJson, sleep, writeJson,
} from './lib/common.mjs';
import { newSeed } from './lib/random.mjs';
import { FORM_FACTORS, buildPlan } from './lib/plan.mjs';
import { pageValidity } from './lib/metrics.mjs';
import { hostConditions } from './lib/environment.mjs';

const require = createRequire(import.meta.url);
const LIGHTHOUSE_VERSION = require('lighthouse/package.json').version;
const CHROME_LAUNCHER_VERSION = require('chrome-launcher/package.json').version;

const CATEGORIES = ['performance', 'accessibility'];
const ROBOTS_MAX_AGE_DAYS = 7;
const MAX_CONSECUTIVE_ERRORS = 3;
const CHROME_FLAGS = ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-extensions'];

// Configurações passadas como flags do Lighthouse em toda execução. O resto é o padrão do
// Lighthouse (mobile) ou o preset desktop. disableFullPageScreenshot só pula uma captura de tela
// feita depois do carregamento; não muda as métricas e deixa cada JSON bruto bem menor.
const LIGHTHOUSE_FLAGS = {
  output: 'json',
  logLevel: 'error',
  onlyCategories: CATEGORIES,
  disableFullPageScreenshot: true,
};

const { values: args } = parseArgs({
  options: {
    phase: { type: 'string', default: 'pilot' },
    runs: { type: 'string', default: '3' },
    services: { type: 'string' },
    seed: { type: 'string' },
    pause: { type: 'string', default: '10' },
    force: { type: 'boolean', default: false },
    'dry-run': { type: 'boolean', default: false },
  },
});

function fail(message) {
  console.error(`ERRO: ${message}`);
  process.exit(1);
}

function parseOptions() {
  const phase = args.phase;
  if (!/^[a-z0-9-]+$/.test(phase)) fail('--phase precisa seguir o padrão [a-z0-9-]+');
  const runs = Number(args.runs);
  if (!Number.isInteger(runs) || runs < 1) fail('--runs precisa ser um inteiro positivo');
  const pauseMs = Number(args.pause) * 1000;
  if (!Number.isFinite(pauseMs) || pauseMs < MIN_PAUSE_MS) fail(`--pause precisa ser de pelo menos ${MIN_PAUSE_MS / 1000} segundos (regra de ética)`);
  const seed = args.seed === undefined ? newSeed() : Number(args.seed);
  if (!Number.isInteger(seed) || seed < 0 || seed > 2 ** 32 - 1) fail('--seed precisa ser um inteiro em [0, 2^32-1]');
  return { phase, runs, pauseMs, seed, force: args.force, dryRun: args['dry-run'] };
}

async function selectServices(phase) {
  const all = await loadServices();
  if (args.services) {
    const ids = args.services.split(',').map((s) => s.trim());
    const unknown = ids.filter((id) => !all.some((s) => s.id === id));
    if (unknown.length) fail(`id(s) de serviço desconhecido(s): ${unknown.join(', ')}`);
    return all.filter((s) => ids.includes(s.id));
  }
  return phase === 'pilot' ? all.filter((s) => s.pilot) : all;
}

/** Trava de ética: toda URL precisa ter sido verificada no robots.txt há pouco tempo e estar liberada. */
async function robotsGate(services) {
  if (!existsSync(ROBOTS_JSON)) fail('data/robots-check.json não encontrado; rode antes `npm run robots`');
  const robots = await readJson(ROBOTS_JSON);
  const ageDays = (Date.now() - new Date(robots.generatedAt).getTime()) / 86_400_000;
  if (!(ageDays <= ROBOTS_MAX_AGE_DAYS)) {
    fail(`a verificação do robots.txt tem ${ageDays.toFixed(1)} dias (máximo ${ROBOTS_MAX_AGE_DAYS}); rode \`npm run robots\` de novo`);
  }
  const crawlDelays = {};
  for (const s of services) {
    const r = robots.results.find((x) => x.id === s.id && x.url === s.url);
    if (!r) fail(`${s.id} (${s.url}) não está na verificação do robots.txt; rode \`npm run robots\` de novo`);
    if (!r.allowed) fail(`${s.id} não é liberado pelo robots.txt (${r.reason}); troque o serviço em data/urls.json`);
    crawlDelays[s.id] = r.crawlDelay ?? 0;
  }
  return { generatedAt: robots.generatedAt, crawlDelays };
}

function machineInfo() {
  const cpus = os.cpus();
  return {
    os: { type: os.type(), release: os.release(), version: os.version(), platform: os.platform(), arch: os.arch() },
    cpu: { model: cpus[0]?.model?.trim() ?? 'desconhecido', logicalCores: cpus.length, speedMHz: cpus[0]?.speed ?? null },
    ramGB: Math.round((os.totalmem() / 1024 ** 3) * 10) / 10,
    node: process.version,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

async function browserVersion(port) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(5_000) });
    const info = await res.json();
    return { browser: info.Browser, protocolVersion: info['Protocol-Version'], userAgent: info['User-Agent'] };
  } catch {
    return null;
  }
}

/** Guarda só as configurações que definem as condições da medição. */
function pickSettings(cs) {
  const keys = ['formFactor', 'throttlingMethod', 'throttling', 'screenEmulation', 'emulatedUserAgent',
    'onlyCategories', 'maxWaitForFcp', 'maxWaitForLoad', 'disableStorageReset', 'clearStorageTypes',
    'disableFullPageScreenshot', 'locale', 'channel'];
  return Object.fromEntries(keys.map((k) => [k, cs?.[k]]));
}

async function runOnce(task, outFile) {
  const startedAt = new Date();
  const record = {
    order: task.order, serviceId: task.serviceId, url: task.url, formFactor: task.formFactor, run: task.run,
    startedAt: localIsoTimestamp(startedAt), startedAtUtc: startedAt.toISOString(),
    finishedAt: null, durationMs: null, status: 'error', file: null,
    chrome: null, lighthouseVersion: null, finalDisplayedUrl: null, mainDocumentUrl: null,
    mainDocumentStatus: null, runtimeError: null, blockReason: null, runWarnings: [], benchmarkIndex: null,
    performanceScore: null, accessibilityScore: null, error: null,
  };
  let chrome;
  let lhr;
  try {
    chrome = await chromeLauncher.launch({ chromeFlags: CHROME_FLAGS, logLevel: 'error' });
    record.chrome = await browserVersion(chrome.port);
    const config = task.formFactor === 'desktop' ? desktopConfig : undefined;
    const result = await lighthouse(task.url, { ...LIGHTHOUSE_FLAGS, port: chrome.port }, config);
    if (!result) throw new Error('o Lighthouse não devolveu resultado');
    lhr = result.lhr;
    await mkdir(join(outFile, '..'), { recursive: true });
    await writeFile(outFile, result.report, 'utf8');
    record.file = relative(ROOT, outFile).replaceAll('\\', '/');
    record.lighthouseVersion = lhr.lighthouseVersion;
    record.finalDisplayedUrl = lhr.finalDisplayedUrl;
    record.mainDocumentUrl = lhr.mainDocumentUrl ?? null;
    record.runWarnings = lhr.runWarnings ?? [];
    record.benchmarkIndex = lhr.environment?.benchmarkIndex ?? null;
    record.performanceScore = lhr.categories.performance?.score ?? null;
    record.accessibilityScore = lhr.categories.accessibility?.score ?? null;
    const validity = pageValidity(lhr);
    record.mainDocumentStatus = validity.mainDocumentStatus;
    if (lhr.runtimeError) {
      record.runtimeError = { code: lhr.runtimeError.code, message: lhr.runtimeError.message };
      record.status = 'runtime-error';
    } else if (!validity.valid) {
      record.blockReason = validity.reason;
      record.status = 'blocked';
    } else {
      record.status = 'ok';
    }
  } catch (err) {
    record.error = `${err.name}: ${err.message}`;
  } finally {
    if (chrome) {
      try {
        await chrome.kill();
      } catch {
        // No Windows a pasta temporária do perfil às vezes continua travada; não afeta a medição.
      }
    }
    const finishedAt = new Date();
    record.finishedAt = localIsoTimestamp(finishedAt);
    record.durationMs = finishedAt - startedAt;
  }
  return { record, settings: lhr ? pickSettings(lhr.configSettings) : null };
}

async function loadMetadata() {
  if (!existsSync(RUN_METADATA_FILE)) return { sessions: [] };
  const meta = await readJson(RUN_METADATA_FILE);
  meta.sessions ??= [];
  return meta;
}

async function main() {
  const opts = parseOptions();
  const services = await selectServices(opts.phase);
  if (!services.length) fail('nenhum serviço selecionado');
  const robots = await robotsGate(services);
  const plan = buildPlan(services, opts.runs, opts.seed);
  const rawDir = join(DATA_DIR, 'raw', opts.phase);
  const outFileOf = (t) => join(rawDir, `${t.serviceId}_${t.formFactor}_${t.run}.json`);

  console.log(`Fase "${opts.phase}": ${services.length} serviço(s) x ${FORM_FACTORS.length} form factors x ${opts.runs} execução(ões) = ${plan.length} execuções`);
  console.log(`Seed ${opts.seed}; pausa ${opts.pauseMs / 1000}s; Lighthouse ${LIGHTHOUSE_VERSION}`);
  for (const t of plan) console.log(`  ${String(t.order).padStart(3)}. ${t.serviceId} ${t.formFactor} #${t.run}`);
  if (opts.dryRun) return;

  const existing = plan.map(outFileOf).filter((f) => existsSync(f));
  if (existing.length && !opts.force) {
    fail(`${existing.length} arquivo(s) bruto(s) já existe(m) em ${relative(ROOT, rawDir)}; use --force para sobrescrever`);
  }

  const meta = await loadMetadata();
  const session = {
    sessionId: `${opts.phase}-${localIsoTimestamp().replace(/[:]/g, '')}`,
    phase: opts.phase,
    status: 'running',
    startedAt: localIsoTimestamp(),
    finishedAt: null,
    seed: opts.seed,
    runsPerFormFactor: opts.runs,
    pauseBetweenRunsMs: opts.pauseMs,
    services: services.map((s) => ({ id: s.id, url: s.url })),
    robotsCheckGeneratedAt: robots.generatedAt,
    tools: { lighthouse: LIGHTHOUSE_VERSION, chromeLauncher: CHROME_LAUNCHER_VERSION, chromeFlags: CHROME_FLAGS, chrome: null },
    lighthouseFlags: LIGHTHOUSE_FLAGS,
    configByFormFactor: {},
    machine: machineInfo(),
    // Plano de energia e adaptador da rota padrão, lidos uma vez no início da sessão.
    hostConditions: await hostConditions(),
    plannedOrder: plan.map((t) => `${t.serviceId}_${t.formFactor}_${t.run}`),
    executions: [],
  };
  meta.sessions.push(session);
  const save = () => writeJson(RUN_METADATA_FILE, meta);
  await save();

  let consecutiveErrors = 0;
  let executedAny = false;
  const blockedServices = new Map(); // serviceId -> motivo
  for (const task of plan) {
    const label = `[${task.order}/${plan.length}] ${task.serviceId} ${task.formFactor} #${task.run}`;

    // Um serviço que respondeu com página de bloqueio ou desafio não é medido de novo nesta
    // sessão: repetir a requisição só aumentaria um tráfego que o site pediu para não receber.
    if (blockedServices.has(task.serviceId)) {
      session.executions.push({
        order: task.order, serviceId: task.serviceId, url: task.url, formFactor: task.formFactor, run: task.run,
        status: 'skipped-blocked', blockReason: blockedServices.get(task.serviceId),
      });
      await save();
      console.log(`${localIsoTimestamp()} ${label} pulada (serviço bloqueado antes nesta sessão)`);
      continue;
    }

    if (executedAny) await sleep(Math.max(opts.pauseMs, (robots.crawlDelays[task.serviceId] ?? 0) * 1000));
    executedAny = true;

    console.log(`${localIsoTimestamp()} ${label} ...`);
    const { record, settings } = await runOnce(task, outFileOf(task));
    session.executions.push(record);
    if (settings && !session.configByFormFactor[task.formFactor]) session.configByFormFactor[task.formFactor] = settings;
    if (record.chrome && !session.tools.chrome) session.tools.chrome = record.chrome.browser;
    if (record.status === 'blocked') blockedServices.set(task.serviceId, record.blockReason);
    await save();

    const score = (v) => (v === null ? '—' : Math.round(v * 100));
    const detail = {
      ok: () => `perf ${score(record.performanceScore)} a11y ${score(record.accessibilityScore)}`,
      'runtime-error': () => `${record.runtimeError.code}: ${record.runtimeError.message}`,
      blocked: () => `${record.blockReason}; as próximas execuções de ${task.serviceId} serão puladas`,
      error: () => record.error,
    }[record.status]();
    console.log(`${localIsoTimestamp()} ${label} ${record.status} em ${(record.durationMs / 1000).toFixed(1)}s — ${detail}`);

    // Erros do script (e não da página) costumam indicar ambiente quebrado; a sessão para em vez
    // de mandar mais tráfego que não vai gerar dados.
    consecutiveErrors = record.status === 'error' ? consecutiveErrors + 1 : 0;
    if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      session.status = 'aborted';
      session.abortReason = `${MAX_CONSECUTIVE_ERRORS} erros seguidos do script; último: ${record.error}`;
      break;
    }
  }
  if (blockedServices.size) {
    session.blockedServices = Object.fromEntries(blockedServices);
    console.log(`Serviços bloqueados (troque-os em data/urls.json): ${[...blockedServices.keys()].join(', ')}`);
  }

  if (session.status === 'running') session.status = 'finished';
  session.finishedAt = localIsoTimestamp();
  await save();
  const counts = session.executions.reduce((acc, e) => ({ ...acc, [e.status]: (acc[e.status] ?? 0) + 1 }), {});
  if (session.status === 'aborted') {
    console.error(`INTERROMPIDA: ${session.abortReason}`);
    process.exitCode = 1;
  }
  console.log(`Sessão ${session.status}. ${JSON.stringify(counts)}. Metadados em data/run-metadata.json`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
