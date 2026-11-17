import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parsePowercfg } from '../scripts/lib/environment.mjs';

test('parsePowercfg reads GUID and name from English and Portuguese output', () => {
  assert.deepEqual(
    parsePowercfg('Power Scheme GUID: 381B4222-F694-41F0-9685-FF5BB260DF2E  (Balanced)\r\n'),
    { guid: '381b4222-f694-41f0-9685-ff5bb260df2e', name: 'Balanced' },
  );
  assert.deepEqual(
    parsePowercfg('GUID do Esquema de Energia: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (Alto desempenho)'),
    { guid: '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c', name: 'Alto desempenho' },
  );
  assert.equal(parsePowercfg('unexpected output'), null);
});
