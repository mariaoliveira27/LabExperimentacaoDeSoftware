import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mulberry32, shuffle } from '../scripts/lib/random.mjs';
import { buildPlan } from '../scripts/lib/plan.mjs';
import {
  median, pageValidity, parseRawFileName, rowFromLhr, summarize, toCsv, CSV_COLUMNS,
} from '../scripts/lib/metrics.mjs';

const services = [
  { id: 'a', url: 'https://a.example/' },
  { id: 'b-c', url: 'https://b.example/' },
];

test('shuffle is deterministic for a given seed and keeps all items', () => {
  const items = [...Array(20).keys()];
  const s1 = shuffle(items, mulberry32(7));
  const s2 = shuffle(items, mulberry32(7));
  assert.deepEqual(s1, s2);
  assert.notDeepEqual(s1, items);
  assert.deepEqual([...s1].sort((x, y) => x - y), items);
});

test('buildPlan covers every service x formFactor x run once, with chronological run numbers', () => {
  const plan = buildPlan(services, 3, 123);
  assert.equal(plan.length, 2 * 2 * 3);
  assert.deepEqual(plan.map((t) => t.order), [...Array(12).keys()].map((i) => i + 1));
  const keys = plan.map((t) => `${t.serviceId}_${t.formFactor}_${t.run}`);
  assert.equal(new Set(keys).size, keys.length);
  const lastRun = new Map();
  for (const t of plan) {
    const k = `${t.serviceId}|${t.formFactor}`;
    assert.equal(t.run, (lastRun.get(k) ?? 0) + 1);
    lastRun.set(k, t.run);
  }
  assert.deepEqual(buildPlan(services, 3, 123), plan);
  assert.notDeepEqual(buildPlan(services, 3, 124), plan);
});

test('parseRawFileName accepts ids with hyphens and rejects other names', () => {
  assert.deepEqual(parseRawFileName('receita-ecac_mobile_2.json'), { service: 'receita-ecac', formFactor: 'mobile', run: 2 });
  assert.equal(parseRawFileName('notes.json'), null);
  assert.equal(parseRawFileName('x_tablet_1.json'), null);
});

function fakeLhr(overrides = {}) {
  const audit = (v) => ({ numericValue: v });
  return {
    requestedUrl: 'https://a.example/',
    fetchTime: '2026-11-17T18:00:00.000Z',
    configSettings: { formFactor: 'mobile' },
    categories: { performance: { score: 0.57 }, accessibility: { score: 0.9 } },
    audits: {
      'largest-contentful-paint': audit(4321.987),
      'first-contentful-paint': audit(1500.04),
      'total-blocking-time': audit(250),
      'cumulative-layout-shift': audit(0.123456),
      'speed-index': audit(3000.55),
    },
    ...overrides,
  };
}

test('rowFromLhr maps scores to 0-100 and metrics to rounded numbers', () => {
  const r = rowFromLhr(fakeLhr(), { service: 'a', formFactor: 'mobile', run: 1 });
  assert.equal(r.ok, true);
  assert.deepEqual(r.row, {
    service: 'a', url: 'https://a.example/', formFactor: 'mobile', run: 1, timestamp: '2026-11-17T18:00:00.000Z',
    performanceScore: 57, accessibilityScore: 90, LCP: 4322, FCP: 1500, TBT: 250, CLS: 0.1235, SpeedIndex: 3000.6,
  });
});

test('rowFromLhr reports runtime errors and null scores as failures', () => {
  const err = rowFromLhr(fakeLhr({ runtimeError: { code: 'ERRORED_DOCUMENT_REQUEST', message: 'status 403' } }),
    { service: 'a', formFactor: 'mobile', run: 1 });
  assert.equal(err.ok, false);
  assert.equal(err.failure.reasonCode, 'ERRORED_DOCUMENT_REQUEST');
  const nul = rowFromLhr(fakeLhr({ categories: { performance: { score: null }, accessibility: { score: 1 } } }),
    { service: 'a', formFactor: 'mobile', run: 1 });
  assert.equal(nul.ok, false);
  assert.equal(nul.failure.reasonCode, 'MISSING_VALUES');
});

test('pageValidity flags a bot-challenge page served with a non-200 status', () => {
  const challenge = fakeLhr({
    mainDocumentUrl: 'https://a.example/',
    audits: {
      ...fakeLhr().audits,
      'network-requests': { details: { items: [
        { url: 'https://a.example/', resourceType: 'Document', statusCode: 202 },
        { url: 'https://x.sa-east-1.captcha.awswaf.com/captcha.js', resourceType: 'Script', statusCode: 200 },
      ] } },
    },
  });
  const v = pageValidity(challenge);
  assert.equal(v.valid, false);
  assert.equal(v.mainDocumentStatus, 202);
  assert.match(v.reason, /HTTP 202.*captcha\.awswaf\.com/);
  const r = rowFromLhr(challenge, { service: 'a', formFactor: 'mobile', run: 1 });
  assert.equal(r.ok, false);
  assert.equal(r.failure.reasonCode, 'BLOCKED_OR_NOT_200');
});

test('pageValidity accepts a 200 page even if it loads a WAF SDK script', () => {
  const real = fakeLhr({
    mainDocumentUrl: 'https://a.example/',
    audits: {
      ...fakeLhr().audits,
      'network-requests': { details: { items: [
        { url: 'https://a.example/', resourceType: 'Document', statusCode: 200 },
        { url: 'https://x.edge.sdk.awswaf.com/challenge.js', resourceType: 'Script', statusCode: 200 },
      ] } },
    },
  });
  assert.deepEqual(pageValidity(real), { valid: true, mainDocumentStatus: 200 });
});

test('rowFromLhr rejects a file whose name does not match its form factor', () => {
  assert.throws(() => rowFromLhr(fakeLhr(), { service: 'a', formFactor: 'desktop', run: 1 }));
});

test('median, summarize and toCsv', () => {
  assert.equal(median([3, 1, 2]), 2);
  assert.equal(median([4, 1, 2, 3]), 2.5);
  assert.equal(median([]), null);
  const rows = [1, 2, 3].map((run) => ({
    ...rowFromLhr(fakeLhr(), { service: 'a', formFactor: 'mobile', run }).row,
    performanceScore: 50 + run,
  }));
  const [s] = summarize(rows);
  assert.equal(s.n, 3);
  assert.equal(s.performanceScore_median, 52);
  assert.equal(s.performanceScore_min, 51);
  assert.equal(s.performanceScore_max, 53);
  const csv = toCsv([{ ...rows[0], url: 'https://x/?a=1,2' }], CSV_COLUMNS);
  assert.match(csv, /^service,url,formFactor,run,performanceScore,accessibilityScore,LCP,FCP,TBT,CLS,SpeedIndex,timestamp\n/);
  assert.match(csv, /"https:\/\/x\/\?a=1,2"/);
});
