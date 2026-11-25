// Leitura e nomes dos arquivos brutos do Lighthouse (LHR). A fase pilot grava .json; a fase full
// grava .json.gz (gzip nível 9) para o repositório não passar de ~120 MB com 200 execuções.
import { existsSync } from 'node:fs';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import { gunzipSync, gzipSync, constants } from 'node:zlib';
import { basename, dirname, join } from 'node:path';

export const RAW_NAME_RE = /^([a-z0-9-]+)_(mobile|desktop)_(\d+)\.json(\.gz)?$/;

/** Nome base, sem extensão, de uma execução. */
export const rawBaseName = ({ serviceId, service, formFactor, run }) => `${serviceId ?? service}_${formFactor}_${run}`;

/** Caminho do arquivo bruto que já existe para a execução (.json ou .json.gz), ou null. */
export function findRawFile(dir, key) {
  const base = join(dir, rawBaseName(key));
  for (const ext of ['.json.gz', '.json']) if (existsSync(base + ext)) return base + ext;
  return null;
}

export async function readLhrFile(path) {
  const buf = await readFile(path);
  return JSON.parse((path.endsWith('.gz') ? gunzipSync(buf) : buf).toString('utf8'));
}

export async function writeLhrFile(path, json) {
  await mkdir(dirname(path), { recursive: true });
  const data = path.endsWith('.gz') ? gzipSync(Buffer.from(json, 'utf8'), { level: constants.Z_BEST_COMPRESSION }) : json;
  await writeFile(path, data);
}

/**
 * Tira de cena um arquivo bruto inválido antes de refazer a execução, sem apagá-lo: ele vai para
 * <dir>/invalid/<nome>.<carimbo>.<ext> e continua como evidência.
 */
export async function moveToInvalid(path, stamp) {
  const dir = join(dirname(path), 'invalid');
  await mkdir(dir, { recursive: true });
  const name = basename(path);
  const m = /^(.*?)(\.json(\.gz)?)$/.exec(name);
  const target = join(dir, `${m[1]}.${stamp}${m[2]}`);
  await rename(path, target);
  return target;
}
