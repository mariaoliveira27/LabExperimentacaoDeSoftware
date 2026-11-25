#!/usr/bin/env node
// Roda o Lighthouse em cada serviço, N vezes por form factor (mobile e desktop), em sequência,
// em ordem aleatória com seed e com pausa de pelo menos 10 s entre execuções.
//
//   node scripts/run-lighthouse.mjs --phase pilot --runs 3
//   node scripts/run-lighthouse.mjs --phase full --block 1 --session-label morning
//   node scripts/run-lighthouse.mjs --phase full --block 2 --session-label afternoon
//
// Opções:
//   --phase <nome>          pasta de saída dentro de data/raw/ (padrão: pilot)
//   --runs <N>              execuções por serviço e por form factor (padrão: 10 na fase full, 3 nas outras)
//   --blocks <B>            blocos de horário em que as N réplicas são divididas (padrão: 2 na fase full, 1 nas outras)
//   --block <k>             roda só as execuções do bloco k (padrão: todas as que faltam)
//   --session-label <rótulo> morning, afternoon ou night; obrigatório na fase full
//   --services <ids>        ids de data/urls.json separados por vírgula
//                           (padrão: serviços com "pilot": true na fase pilot; todos nas outras)
//   --seed <inteiro>        seed da ordem de execução (padrão: a de data/raw/<fase>/plan.json, ou sorteada)
//   --pause <segundos>      pausa entre execuções, mínimo 10 (padrão: 10)
//   --gzip / --no-gzip      grava o bruto como .json.gz (padrão: ligado fora da fase pilot)
//   --force                 refaz também as execuções que já têm JSON válido
//   --dry-run               mostra o plano, o que falta e a estimativa de tempo, e sai
//
// A sessão pode ser interrompida (Ctrl+C) e retomada com o mesmo comando: execuções com JSON válido
// são puladas; um JSON inválido (bloqueio, runtimeError) vai para data/raw/<fase>/invalid/ e a
// execução é refeita.
//
// Saídas:
//   data/raw/<fase>/<servico>_<formFactor>_<n>.json[.gz]  resultado bruto do Lighthouse (LHR)
//   data/raw/<fase>/plan.json                             seed, blocos e plano completo da fase
//   data/run-metadata.json                                uma entrada por sessão (acrescentada ao fim)
//   data/failed-runs.csv                                  uma linha por execução que falhou ou foi pulada
import { parseArgs } from 'node:util';
import { existsSync, unlinkSync, writeFileSync } from 'node:fs';
import { appendFile, readFile, writeFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join, relative } from 'node:path';
import os from 'node:os';
import lighthouse, { desktopConfig } from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import {
  DATA_DIR, FAILED_RUNS_FILE, MIN_PAUSE_MS, ROBOTS_JSON, ROOT, RUN_METADATA_FILE,
  loadServices, localIsoTimestamp, readJson, sleep, writeJson,
} from './lib/common.mjs';
import { newSeed } from './lib/random.mjs';
import { FORM_FACTORS, buildPlan } from './lib/plan.mjs';
import { pageValidity, rowFromLhr, toCsv } from './lib/metrics.mjs';
import { hostConditions } from './lib/environment.mjs';
import { findRawFile, moveToInvalid, rawBaseName, readLhrFile, writeLhrFile } from './lib/rawfiles.mjs';

const require = createRequire(import.meta.url);
const LIGHTHOUSE_VERSION = require('lighthouse/package.json').version;
const CHROME_LAUNCHER_VERSION = require('chrome-launcher/package.json').version;

const CATEGORIES = ['performance', 'accessibility'];
const ROBOTS_MAX_AGE_DAYS = 7;
const MAX_CONSECUTIVE_ERRORS = 3;
const CHROME_FLAGS = ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-extensions'];
const SESSION_LABELS = { morning: [6, 12], afternoon: [12, 18], night: [18, 24] };
const LOCK_FILE = join(DATA_DIR, 'raw', '.lighthouse.lock');
// Duração usada na estimativa quando ainda não há execuções anteriores em run-metadata.json.
const DEFAULT_RUN_MS = 20_000;

export const FAILED_RUN_COLUMNS = [
  'loggedAt', 'phase', 'sessionId', 'sessionLabel', 'block', 'order', 'service', 'formFactor', 'run',
  'status', 'reasonCode', 'reason', 'file',
];

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
    runs: { type: 'string' },
    blocks: { type: 'string' },
    block: { type: 'string' },
    'session-label': { type: 'string' },
    services: { type: 'string' },
    seed: { type: 'string' },
    pause: { type: 'string', default: '10' },
    gzip: { type: 'boolean' },
    'no-gzip': { type: 'boolean', default: false },
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
  const isFull = phase === 'full';
  const runs = Number(args.runs ?? (isFull ? 10 : 3));
  if (!Number.isInteger(runs) || runs < 1) fail('--runs precisa ser um inteiro positivo');
  const blocks = Number(args.blocks ?? (isFull ? 2 : 1));
  if (!Number.isInteger(blocks) || blocks < 1 || runs % blocks !== 0) fail(`--blocks precisa dividir --runs (${runs})`);
  const block = args.block === undefined ? null : Number(args.block);
  if (block !== null && !(Number.isInteger(block) && block >= 1 && block <= blocks)) fail(`--block precisa estar entre 1 e ${blocks}`);
  const pauseMs = Number(args.pause) * 1000;
  if (!Number.isFinite(pauseMs) || pauseMs < MIN_PAUSE_MS) fail(`--pause precisa ser de pelo menos ${MIN_PAUSE_MS / 1000} segundos (regra de ética)`);
  const seed = args.seed === undefined ? null : Number(args.seed);
  if (seed !== null && !(Number.isInteger(seed) && seed >= 0 && seed <= 2 ** 32 - 1)) fail('--seed precisa ser um inteiro em [0, 2^32-1]');
  const sessionLabel = args['session-label'] ?? null;
  if (sessionLabel !== null && !(sessionLabel in SESSION_LABELS)) fail(`--session-label precisa ser um de: ${Object.keys(SESSION_LABELS).join(', ')}`);
  if (isFull && sessionLabel === null && !args['dry-run']) fail('--session-label é obrigatório na fase full (morning, afternoon ou night)');
  const gzip = args['no-gzip'] ? false : (args.gzip ?? phase !== 'pilot');
  return { phase, runs, blocks, block, pauseMs, seed, sessionLabel, gzip, force: args.force, dryRun: args['dry-run'] };
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

/**
 * O plano de uma fase é fixado na primeira sessão e guardado em data/raw/<fase>/plan.json, para que
 * as sessões seguintes (outro bloco ou uma retomada) usem a mesma seed e a mesma ordem.
 */
async function loadOrCreatePlan(rawDir, opts, services) {
  const planFile = join(rawDir, 'plan.json');
  const serviceList = services.map((s) => ({ id: s.id, url: s.url }));
  if (existsSync(planFile)) {
    const saved = await readJson(planFile);
    const mismatch = [];
    if (opts.seed !== null && opts.seed !== saved.seed) mismatch.push(`seed ${opts.seed} ≠ ${saved.seed}`);
    if (opts.runs !== saved.runs) mismatch.push(`runs ${opts.runs} ≠ ${saved.runs}`);
    if (opts.blocks !== saved.blocks) mismatch.push(`blocks ${opts.blocks} ≠ ${saved.blocks}`);
    if (JSON.stringify(serviceList) !== JSON.stringify(saved.services)) mismatch.push('lista de serviços ou URLs mudou');
    if (mismatch.length) fail(`${relative(ROOT, planFile)} não confere com as opções (${mismatch.join('; ')}). Use outra --phase ou apague o plano de propósito.`);
    return { seed: saved.seed, plan: buildPlan(services, saved.runs, saved.seed, saved.blocks), planFile, created: false };
  }
  const seed = opts.seed ?? newSeed();
  const plan = buildPlan(services, opts.runs, seed, opts.blocks);
  const content = {
    phase: opts.phase, seed, runs: opts.runs, blocks: opts.blocks, createdAt: localIsoTimestamp(), services: serviceList,
    plan: plan.map((t) => ({ order: t.order, block: t.block, key: rawBaseName(t) })),
  };
  if (!opts.dryRun) await writeJson(planFile, content);
  return { seed, plan, planFile, created: true };
}

/**
 * Uma execução tem JSON válido quando o LHR existe, não tem runtimeError, mediu a página certa e tem
 * todas as métricas (a mesma regra do extrator: rowFromLhr).
 */
async function rawStatus(file, task) {
  try {
    const lhr = await readLhrFile(file);
    const r = rowFromLhr(lhr, { service: task.serviceId, formFactor: task.formFactor, run: task.run });
    return r.ok ? { valid: true } : { valid: false, reason: `${r.failure.reasonCode}: ${r.failure.reason}` };
  } catch (err) {
    return { valid: false, reason: `JSON ilegível (${err.message})` };
  }
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

async function runOnce(task, outFile, sessionLabel) {
  const startedAt = new Date();
  const record = {
    order: task.order, block: task.block, sessionLabel, serviceId: task.serviceId, url: task.url,
    formFactor: task.formFactor, run: task.run,
    startedAt: localIsoTimestamp(startedAt), startedAtUtc: startedAt.toISOString(),
    finishedAt: null, finishedAtUtc: null, durationMs: null, status: 'error', file: null,
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
    await writeLhrFile(outFile, result.report);
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
      record.blockCode = validity.code;
      record.status = 'blocked';
    } else {
      // Métrica nula sem runtimeError (ex.: NO_FCP dentro das auditorias): a página foi medida, mas
      // o resultado não serve. Conta como falha e a execução é refeita.
      const row = rowFromLhr(lhr, { service: task.serviceId, formFactor: task.formFactor, run: task.run });
      if (row.ok) {
        record.status = 'ok';
      } else {
        record.status = 'missing-values';
        record.missingValues = row.failure.reason;
        record.auditErrors = [...new Set(Object.values(lhr.audits).map((a) => a.errorMessage).filter(Boolean))];
      }
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
    record.finishedAtUtc = finishedAt.toISOString();
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

/** Mediana da duração das execuções 'ok' já registradas, usada na estimativa de tempo. */
function typicalRunMs(meta) {
  const d = meta.sessions.flatMap((s) => s.executions).filter((e) => e.status === 'ok' && e.durationMs).map((e) => e.durationMs).sort((a, b) => a - b);
  return d.length ? d[Math.floor(d.length / 2)] : DEFAULT_RUN_MS;
}

const fmtDuration = (ms) => {
  const min = Math.round(ms / 60_000);
  return min >= 60 ? `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min` : `${min} min`;
};

async function appendFailedRun(row) {
  const header = !existsSync(FAILED_RUNS_FILE);
  const csv = toCsv([row], FAILED_RUN_COLUMNS);
  await mkdir(DATA_DIR, { recursive: true });
  await appendFile(FAILED_RUNS_FILE, header ? csv : csv.slice(csv.indexOf('\n') + 1), 'utf8');
}

/** Impede duas sessões ao mesmo tempo (regra de ética: sem paralelismo). */
async function acquireLock(sessionId) {
  if (existsSync(LOCK_FILE)) {
    const lock = JSON.parse(await readFile(LOCK_FILE, 'utf8'));
    let alive = false;
    try {
      process.kill(lock.pid, 0);
      alive = true;
    } catch {
      // processo não existe mais: a trava ficou de uma sessão interrompida
    }
    if (alive) fail(`outra sessão está rodando (pid ${lock.pid}, ${lock.sessionId}); medições em paralelo não são permitidas`);
    console.log(`Trava antiga de ${lock.sessionId} (pid ${lock.pid}, processo encerrado) foi substituída.`);
  }
  await mkdir(join(DATA_DIR, 'raw'), { recursive: true });
  await writeFile(LOCK_FILE, JSON.stringify({ pid: process.pid, sessionId, startedAt: localIsoTimestamp() }) + '\n', 'utf8');
  process.on('exit', () => {
    try {
      if (existsSync(LOCK_FILE)) unlinkSync(LOCK_FILE);
    } catch {
      // nada a fazer
    }
  });
}

/** Ctrl+C: marca a sessão como interrompida (gravação síncrona) e sai; a trava é liberada no 'exit'. */
function onInterrupt(meta, session) {
  for (const sig of ['SIGINT', 'SIGTERM', 'SIGBREAK']) {
    process.on(sig, () => {
      session.status = 'interrupted';
      session.finishedAt = localIsoTimestamp();
      writeFileSync(RUN_METADATA_FILE, JSON.stringify(meta, null, 2) + '\n', 'utf8');
      console.log(`\nInterrompida (${sig}). Rode o mesmo comando para retomar; as execuções com JSON válido serão puladas.`);
      process.exit(130);
    });
  }
}

async function main() {
  const opts = parseOptions();
  const services = await selectServices(opts.phase);
  if (!services.length) fail('nenhum serviço selecionado');
  const robots = await robotsGate(services);
  const rawDir = join(DATA_DIR, 'raw', opts.phase);
  const { seed, plan, planFile, created } = await loadOrCreatePlan(rawDir, opts, services);
  const outFileOf = (t) => join(rawDir, `${rawBaseName(t)}.json${opts.gzip ? '.gz' : ''}`);

  // O que falta: execuções do(s) bloco(s) escolhido(s) sem JSON válido (ou todas, com --force).
  const selected = plan.filter((t) => opts.block === null || t.block === opts.block);
  const todo = [];
  const toMove = [];
  for (const t of selected) {
    const existing = findRawFile(rawDir, t);
    if (!existing) {
      todo.push(t);
      continue;
    }
    const st = opts.force ? { valid: false, reason: '--force' } : await rawStatus(existing, t);
    if (!st.valid) {
      todo.push(t);
      toMove.push({ task: t, file: existing, reason: st.reason });
    }
  }

  const meta = await loadMetadata();
  const perRunMs = typicalRunMs(meta);
  const estimateMs = todo.length * perRunMs + Math.max(0, todo.length - 1) * opts.pauseMs;
  console.log(`Fase "${opts.phase}": ${services.length} serviço(s) x ${FORM_FACTORS.length} form factors x ${opts.runs} execução(ões) em ${opts.blocks} bloco(s) = ${plan.length} execuções`);
  console.log(`Seed ${seed} (${created ? 'nova' : `de ${relative(ROOT, planFile)}`}); pausa ${opts.pauseMs / 1000}s; Lighthouse ${LIGHTHOUSE_VERSION}; bruto em ${opts.gzip ? '.json.gz' : '.json'}`);
  console.log(`${opts.block === null ? 'Todos os blocos' : `Bloco ${opts.block}`}: ${selected.length} execuções no plano, ${selected.length - todo.length} já com JSON válido, ${todo.length} a rodar (${toMove.length} com JSON inválido a refazer)`);
  console.log(`Estimativa: ${todo.length} x (${(perRunMs / 1000).toFixed(1)} s por execução, mediana já registrada) + pausas de ${opts.pauseMs / 1000} s = ~${fmtDuration(estimateMs)}`);
  if (opts.dryRun) {
    for (const t of todo) console.log(`  ${String(t.order).padStart(3)}. [b${t.block}] ${t.serviceId} ${t.formFactor} #${t.run}`);
    return;
  }
  if (!todo.length) {
    console.log('Nada a fazer.');
    return;
  }
  if (opts.sessionLabel) {
    const [from, to] = SESSION_LABELS[opts.sessionLabel];
    const h = new Date().getHours();
    if (h < from || h >= to) console.warn(`AVISO: --session-label ${opts.sessionLabel} (${from}h-${to}h), mas agora são ${h}h`);
  }

  const sessionId = `${opts.phase}-${localIsoTimestamp().replace(/[:]/g, '')}`;
  await acquireLock(sessionId);

  const session = {
    sessionId,
    phase: opts.phase,
    sessionLabel: opts.sessionLabel,
    block: opts.block,
    status: 'running',
    startedAt: localIsoTimestamp(),
    finishedAt: null,
    seed,
    runsPerFormFactor: opts.runs,
    blocks: opts.blocks,
    pauseBetweenRunsMs: opts.pauseMs,
    estimatedDurationMs: estimateMs,
    services: services.map((s) => ({ id: s.id, url: s.url })),
    robotsCheckGeneratedAt: robots.generatedAt,
    tools: { lighthouse: LIGHTHOUSE_VERSION, chromeLauncher: CHROME_LAUNCHER_VERSION, chromeFlags: CHROME_FLAGS, chrome: null },
    lighthouseFlags: LIGHTHOUSE_FLAGS,
    configByFormFactor: {},
    machine: machineInfo(),
    // Plano de energia e adaptador da rota padrão, lidos uma vez no início da sessão.
    hostConditions: await hostConditions(),
    plannedOrder: todo.map((t) => rawBaseName(t)),
    movedInvalidFiles: [],
    executions: [],
  };
  meta.sessions.push(session);
  onInterrupt(meta, session);
  const save = () => writeJson(RUN_METADATA_FILE, meta);
  const stamp = session.startedAt.replace(/[:+]/g, '').slice(0, 15);
  for (const m of toMove) {
    const target = await moveToInvalid(m.file, stamp);
    session.movedInvalidFiles.push({ key: rawBaseName(m.task), from: relative(ROOT, m.file).replaceAll('\\', '/'), to: relative(ROOT, target).replaceAll('\\', '/'), reason: m.reason });
    // O JSON inválido pode ter vindo de uma sessão anterior que não o registrou (versão antiga do
    // script); registrar aqui garante que nenhuma falha some em silêncio.
    if (m.reason !== '--force') {
      // Sessão que gerou o arquivo: a última tentativa registrada para essa execução nesta fase.
      const origin = meta.sessions.filter((s) => s.phase === opts.phase && s !== session)
        .flatMap((s) => s.executions.map((e) => ({ s, e })))
        .filter(({ e }) => e.serviceId === m.task.serviceId && e.formFactor === m.task.formFactor && e.run === m.task.run).at(-1);
      await appendFailedRun({
        loggedAt: localIsoTimestamp(), phase: opts.phase, sessionId: origin?.s.sessionId ?? sessionId,
        sessionLabel: origin?.e.sessionLabel ?? origin?.s.sessionLabel ?? '', block: m.task.block,
        order: m.task.order, service: m.task.serviceId, formFactor: m.task.formFactor, run: m.task.run,
        status: 'invalid-found-on-resume', reasonCode: m.reason.split(':')[0], reason: m.reason,
        file: relative(ROOT, target).replaceAll('\\', '/'),
      });
    }
  }
  await save();

  const logFailure = (task, status, reasonCode, reason, file = null) => appendFailedRun({
    loggedAt: localIsoTimestamp(), phase: opts.phase, sessionId, sessionLabel: opts.sessionLabel ?? '', block: task.block,
    order: task.order, service: task.serviceId, formFactor: task.formFactor, run: task.run, status, reasonCode, reason, file,
  });

  let consecutiveErrors = 0;
  let executedAny = false;
  let done = 0;
  const sessionStart = Date.now();
  const blockedServices = new Map(); // serviceId -> motivo
  // Fila: execuções com falha da página ou do script (não bloqueio) voltam uma vez para o fim da fila.
  const queue = todo.map((t) => ({ ...t, attempt: 1 }));
  const MAX_ATTEMPTS = 2;
  for (let qi = 0; qi < queue.length; qi++) {
    const task = queue[qi];
    done++;
    const label = `[${done}/${queue.length}] (#${task.order} b${task.block}${task.attempt > 1 ? ` tentativa ${task.attempt}` : ''}) ${task.serviceId} ${task.formFactor} #${task.run}`;

    // Um serviço que respondeu com página de bloqueio ou desafio não é medido de novo nesta
    // sessão: repetir a requisição só aumentaria um tráfego que o site pediu para não receber.
    if (blockedServices.has(task.serviceId)) {
      session.executions.push({
        order: task.order, block: task.block, sessionLabel: opts.sessionLabel, serviceId: task.serviceId, url: task.url,
        formFactor: task.formFactor, run: task.run, status: 'skipped-blocked', blockReason: blockedServices.get(task.serviceId),
      });
      await logFailure(task, 'skipped-blocked', 'SERVICE_BLOCKED_EARLIER', blockedServices.get(task.serviceId));
      await save();
      console.log(`${localIsoTimestamp()} ${label} pulada (serviço bloqueado antes nesta sessão)`);
      continue;
    }

    if (executedAny) await sleep(Math.max(opts.pauseMs, (robots.crawlDelays[task.serviceId] ?? 0) * 1000));
    executedAny = true;

    if (task.attempt > 1) {
      const previous = findRawFile(rawDir, task);
      if (previous) {
        const target = await moveToInvalid(previous, `${stamp}-t${task.attempt - 1}`);
        session.movedInvalidFiles.push({ key: rawBaseName(task), from: relative(ROOT, previous).replaceAll('\\', '/'), to: relative(ROOT, target).replaceAll('\\', '/'), reason: 'refeita na mesma sessão' });
      }
    }
    console.log(`${localIsoTimestamp()} ${label} ...`);
    const { record, settings } = await runOnce(task, outFileOf(task), opts.sessionLabel);
    record.attempt = task.attempt;
    session.executions.push(record);
    if (settings && !session.configByFormFactor[task.formFactor]) session.configByFormFactor[task.formFactor] = settings;
    if (record.chrome && !session.tools.chrome) session.tools.chrome = record.chrome.browser;
    if (record.status === 'blocked') blockedServices.set(task.serviceId, record.blockReason);
    if (record.status !== 'ok') {
      const [code, reason] = {
        'runtime-error': () => [record.runtimeError.code, record.runtimeError.message],
        blocked: () => [record.blockCode, record.blockReason],
        'missing-values': () => ['MISSING_VALUES', `${record.missingValues}; ${record.auditErrors.join(' / ')}`],
        error: () => [/timed? ?out|timeout/i.test(record.error) ? 'TIMEOUT' : 'SCRIPT_ERROR', record.error],
      }[record.status]();
      await logFailure(task, record.status, code, reason, record.file);
      if (record.status !== 'blocked' && task.attempt < MAX_ATTEMPTS) queue.push({ ...task, attempt: task.attempt + 1 });
    }
    await save();

    const score = (v) => (v === null ? '—' : Math.round(v * 100));
    const detail = {
      ok: () => `perf ${score(record.performanceScore)} a11y ${score(record.accessibilityScore)}`,
      'runtime-error': () => `${record.runtimeError.code}: ${record.runtimeError.message}`,
      blocked: () => `${record.blockReason}; as próximas execuções de ${task.serviceId} serão puladas`,
      'missing-values': () => `${record.missingValues} (${record.auditErrors.join(' / ').slice(0, 120)}); vai ser refeita no fim da fila`,
      error: () => record.error,
    }[record.status]();
    const elapsed = Date.now() - sessionStart;
    const eta = (elapsed / done) * (queue.length - done);
    console.log(`${localIsoTimestamp()} ${label} ${record.status} em ${(record.durationMs / 1000).toFixed(1)}s — ${detail} | restam ~${fmtDuration(eta)}`);

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
  console.log(`Sessão ${session.status} em ${fmtDuration(Date.now() - sessionStart)}. ${JSON.stringify(counts)}. Metadados em data/run-metadata.json; falhas em data/failed-runs.csv`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
