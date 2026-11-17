#!/usr/bin/env node
// Runs Lighthouse against each service, N times per form factor (mobile and desktop),
// sequentially and in a seeded random order, with a pause of at least 10 s between runs.
//
//   node scripts/run-lighthouse.mjs --phase pilot --runs 3
//   node scripts/run-lighthouse.mjs --phase full --runs 10 --seed 12345
//
// Options:
//   --phase <name>      output folder under data/raw/ (default: pilot)
//   --runs <N>          executions per service and form factor (default: 3)
//   --services <ids>    comma-separated ids from data/urls.json
//                       (default: services with "pilot": true for --phase pilot, all otherwise)
//   --seed <int>        seed for the execution order (default: random, always logged)
//   --pause <seconds>   pause between executions, minimum 10 (default: 10)
//   --force             overwrite raw files that already exist
//   --dry-run           print the planned order and exit without running Lighthouse
//
// Outputs:
//   data/raw/<phase>/<service>_<formFactor>_<n>.json   raw Lighthouse result (LHR)
//   data/run-metadata.json                             one entry per session (appended)
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

const require = createRequire(import.meta.url);
const LIGHTHOUSE_VERSION = require('lighthouse/package.json').version;
const CHROME_LAUNCHER_VERSION = require('chrome-launcher/package.json').version;

const CATEGORIES = ['performance', 'accessibility'];
const ROBOTS_MAX_AGE_DAYS = 7;
const MAX_CONSECUTIVE_ERRORS = 3;
const CHROME_FLAGS = ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-extensions'];

// Settings passed as Lighthouse flags for every run. Everything else is Lighthouse's default
// (mobile) or desktop preset. disableFullPageScreenshot only skips a screenshot captured after
// the page load; it does not change metrics, and it keeps each raw JSON much smaller.
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
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function parseOptions() {
  const phase = args.phase;
  if (!/^[a-z0-9-]+$/.test(phase)) fail('--phase must match [a-z0-9-]+');
  const runs = Number(args.runs);
  if (!Number.isInteger(runs) || runs < 1) fail('--runs must be a positive integer');
  const pauseMs = Number(args.pause) * 1000;
  if (!Number.isFinite(pauseMs) || pauseMs < MIN_PAUSE_MS) fail(`--pause must be at least ${MIN_PAUSE_MS / 1000} seconds (ethics rule)`);
  const seed = args.seed === undefined ? newSeed() : Number(args.seed);
  if (!Number.isInteger(seed) || seed < 0 || seed > 2 ** 32 - 1) fail('--seed must be an integer in [0, 2^32-1]');
  return { phase, runs, pauseMs, seed, force: args.force, dryRun: args['dry-run'] };
}

async function selectServices(phase) {
  const all = await loadServices();
  if (args.services) {
    const ids = args.services.split(',').map((s) => s.trim());
    const unknown = ids.filter((id) => !all.some((s) => s.id === id));
    if (unknown.length) fail(`unknown service id(s): ${unknown.join(', ')}`);
    return all.filter((s) => ids.includes(s.id));
  }
  return phase === 'pilot' ? all.filter((s) => s.pilot) : all;
}

/** Ethics gate: every URL must have been checked against robots.txt recently and be allowed. */
async function robotsGate(services) {
  if (!existsSync(ROBOTS_JSON)) fail('data/robots-check.json not found; run `npm run robots` first');
  const robots = await readJson(ROBOTS_JSON);
  const ageDays = (Date.now() - new Date(robots.generatedAt).getTime()) / 86_400_000;
  if (!(ageDays <= ROBOTS_MAX_AGE_DAYS)) {
    fail(`robots check is ${ageDays.toFixed(1)} days old (max ${ROBOTS_MAX_AGE_DAYS}); run \`npm run robots\` again`);
  }
  const crawlDelays = {};
  for (const s of services) {
    const r = robots.results.find((x) => x.id === s.id && x.url === s.url);
    if (!r) fail(`${s.id} (${s.url}) is not in the robots check; run \`npm run robots\` again`);
    if (!r.allowed) fail(`${s.id} is not allowed by robots.txt (${r.reason}); replace it in data/urls.json`);
    crawlDelays[s.id] = r.crawlDelay ?? 0;
  }
  return { generatedAt: robots.generatedAt, crawlDelays };
}

function machineInfo() {
  const cpus = os.cpus();
  return {
    os: { type: os.type(), release: os.release(), version: os.version(), platform: os.platform(), arch: os.arch() },
    cpu: { model: cpus[0]?.model?.trim() ?? 'unknown', logicalCores: cpus.length, speedMHz: cpus[0]?.speed ?? null },
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

/** Keeps only the settings that define the measurement conditions. */
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
    if (!result) throw new Error('Lighthouse returned no result');
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
        // On Windows the temporary profile folder is sometimes still locked; not a measurement problem.
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
  if (!services.length) fail('no services selected');
  const robots = await robotsGate(services);
  const plan = buildPlan(services, opts.runs, opts.seed);
  const rawDir = join(DATA_DIR, 'raw', opts.phase);
  const outFileOf = (t) => join(rawDir, `${t.serviceId}_${t.formFactor}_${t.run}.json`);

  console.log(`Phase "${opts.phase}": ${services.length} service(s) x ${FORM_FACTORS.length} form factors x ${opts.runs} run(s) = ${plan.length} executions`);
  console.log(`Seed ${opts.seed}; pause ${opts.pauseMs / 1000}s; Lighthouse ${LIGHTHOUSE_VERSION}`);
  for (const t of plan) console.log(`  ${String(t.order).padStart(3)}. ${t.serviceId} ${t.formFactor} #${t.run}`);
  if (opts.dryRun) return;

  const existing = plan.map(outFileOf).filter((f) => existsSync(f));
  if (existing.length && !opts.force) {
    fail(`${existing.length} raw file(s) already exist in ${relative(ROOT, rawDir)}; use --force to overwrite`);
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
    plannedOrder: plan.map((t) => `${t.serviceId}_${t.formFactor}_${t.run}`),
    executions: [],
  };
  meta.sessions.push(session);
  const save = () => writeJson(RUN_METADATA_FILE, meta);
  await save();

  let consecutiveErrors = 0;
  let executedAny = false;
  const blockedServices = new Map(); // serviceId -> reason
  for (const task of plan) {
    const label = `[${task.order}/${plan.length}] ${task.serviceId} ${task.formFactor} #${task.run}`;

    // A service that answered with a block/challenge page is not measured again in this
    // session: repeating the request would only add traffic the site has asked us not to send.
    if (blockedServices.has(task.serviceId)) {
      session.executions.push({
        order: task.order, serviceId: task.serviceId, url: task.url, formFactor: task.formFactor, run: task.run,
        status: 'skipped-blocked', blockReason: blockedServices.get(task.serviceId),
      });
      await save();
      console.log(`${localIsoTimestamp()} ${label} skipped (service blocked earlier in this session)`);
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
      blocked: () => `${record.blockReason}; remaining runs of ${task.serviceId} will be skipped`,
      error: () => record.error,
    }[record.status]();
    console.log(`${localIsoTimestamp()} ${label} ${record.status} in ${(record.durationMs / 1000).toFixed(1)}s — ${detail}`);

    // Script-level errors (not page errors) usually mean a broken setup; stop instead of
    // sending more traffic that cannot produce data.
    consecutiveErrors = record.status === 'error' ? consecutiveErrors + 1 : 0;
    if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      session.status = 'aborted';
      session.abortReason = `${MAX_CONSECUTIVE_ERRORS} consecutive script errors; last: ${record.error}`;
      break;
    }
  }
  if (blockedServices.size) {
    session.blockedServices = Object.fromEntries(blockedServices);
    console.log(`Blocked services (replace them in data/urls.json): ${[...blockedServices.keys()].join(', ')}`);
  }

  if (session.status === 'running') session.status = 'finished';
  session.finishedAt = localIsoTimestamp();
  await save();
  const counts = session.executions.reduce((acc, e) => ({ ...acc, [e.status]: (acc[e.status] ?? 0) + 1 }), {});
  if (session.status === 'aborted') {
    console.error(`ABORTED: ${session.abortReason}`);
    process.exitCode = 1;
  }
  console.log(`Session ${session.status}. ${JSON.stringify(counts)}. Metadata in data/run-metadata.json`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
