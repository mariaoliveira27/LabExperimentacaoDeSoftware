import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildPlan } from '../scripts/lib/plan.mjs';
import { executionRows, parseRawFileName, rowFromLhr } from '../scripts/lib/metrics.mjs';
import { findRawFile, moveToInvalid, readLhrFile, writeLhrFile } from '../scripts/lib/rawfiles.mjs';
import { parseCsv, tukeyOutliers } from '../scripts/lib/validation.mjs';

const services = [
  { id: 'a', url: 'https://a.example/' },
  { id: 'b-c', url: 'https://b.example/' },
];

test('buildPlan com blocos: bloco 1 tem as réplicas 1..R/B de cada célula, bloco 2 as seguintes', () => {
  const plan = buildPlan(services, 10, 99, 2);
  assert.equal(plan.length, 2 * 2 * 10);
  const b1 = plan.filter((t) => t.block === 1);
  const b2 = plan.filter((t) => t.block === 2);
  assert.equal(b1.length, 20);
  assert.ok(b1.every((t) => t.run <= 5) && b2.every((t) => t.run > 5));
  assert.ok(Math.max(...b1.map((t) => t.order)) < Math.min(...b2.map((t) => t.order)));
  assert.deepEqual(buildPlan(services, 10, 99, 2), plan);
  assert.throws(() => buildPlan(services, 10, 99, 3), /múltiplo/);
});

test('buildPlan com 1 bloco é igual ao plano da Sprint 1 (mesma seed, mesma ordem)', () => {
  const keys = (p) => p.map((t) => `${t.serviceId}_${t.formFactor}_${t.run}`);
  assert.deepEqual(keys(buildPlan(services, 3, 41872753)), keys(buildPlan(services, 3, 41872753, 1)));
});

test('arquivos brutos .json.gz: grava, lê, acha e move para invalid/', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lab05-'));
  const key = { serviceId: 'a', formFactor: 'mobile', run: 3 };
  assert.equal(findRawFile(dir, key), null);
  await writeLhrFile(join(dir, 'a_mobile_3.json.gz'), JSON.stringify({ x: 1 }));
  const found = findRawFile(dir, key);
  assert.ok(found.endsWith('a_mobile_3.json.gz'));
  assert.deepEqual(await readLhrFile(found), { x: 1 });
  const moved = await moveToInvalid(found, '20261125T1200');
  assert.ok(moved.endsWith(join('invalid', 'a_mobile_3.20261125T1200.json.gz')));
  assert.equal(findRawFile(dir, key), null);
  assert.deepEqual(await readdir(join(dir, 'invalid')), ['a_mobile_3.20261125T1200.json.gz']);
  assert.deepEqual(parseRawFileName('a_mobile_3.json.gz'), { service: 'a', formFactor: 'mobile', run: 3 });
});

test('rowFromLhr rejeita métrica nula sem runtimeError (NO_FCP dentro das auditorias)', () => {
  const lhr = {
    requestedUrl: 'https://a.example/', fetchTime: '2026-11-25T14:00:00.000Z', configSettings: { formFactor: 'mobile' },
    categories: { performance: { score: null }, accessibility: { score: 0.9 } },
    audits: {
      'largest-contentful-paint': { numericValue: undefined }, 'first-contentful-paint': {},
      'total-blocking-time': {}, 'cumulative-layout-shift': { numericValue: 0 }, 'speed-index': {},
    },
  };
  const r = rowFromLhr(lhr, { service: 'a', formFactor: 'mobile', run: 1 });
  assert.equal(r.ok, false);
  assert.equal(r.failure.reasonCode, 'MISSING_VALUES');
});

test('parseCsv lê campos com aspas, vírgulas e aspas duplicadas', () => {
  const rows = parseCsv('a,b\n1,"x, ""y"""\n2,\n');
  assert.deepEqual(rows, [{ a: '1', b: 'x, "y"' }, { a: '2', b: '' }]);
});

test('tukeyOutliers marca só valores fora de Q1 - 1,5 IQR e Q3 + 1,5 IQR da célula', () => {
  const vals = [10, 11, 12, 13, 14, 15, 16, 17, 18, 100];
  const rows = vals.map((v, i) => ({ service: 'a', formFactor: 'mobile', run: i + 1, LCP: v }));
  rows.push({ service: 'b', formFactor: 'mobile', run: 1, LCP: 100 });
  const out = tukeyOutliers(rows, ['LCP']);
  assert.equal(out.length, 1);
  assert.equal(out[0].run, 10);
  assert.equal(out[0].side, 'high');
});

test('executionRows deriva finishedAtUtc de startedAtUtc + durationMs nas sessões antigas', () => {
  const meta = { sessions: [{ sessionId: 's', phase: 'pilot', executions: [
    { order: 1, serviceId: 'a', formFactor: 'mobile', run: 1, status: 'ok', startedAtUtc: '2026-11-17T18:00:00.000Z', durationMs: 1500 },
  ] }, { sessionId: 't', phase: 'full', executions: [] }] };
  const rows = executionRows(meta, 'pilot');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].finishedAtUtc, '2026-11-17T18:00:01.500Z');
});
