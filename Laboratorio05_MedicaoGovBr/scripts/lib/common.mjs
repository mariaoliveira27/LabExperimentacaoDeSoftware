// Funções compartilhadas pelos scripts do Lab05: caminhos, leitura da lista de serviços e utilitários.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const DATA_DIR = join(ROOT, 'data');
export const DOCS_DIR = join(ROOT, 'docs');
export const URLS_FILE = join(DATA_DIR, 'urls.json');
export const ROBOTS_JSON = join(DATA_DIR, 'robots-check.json');
export const RUN_METADATA_FILE = join(DATA_DIR, 'run-metadata.json');
export const FAILED_RUNS_FILE = join(DATA_DIR, 'failed-runs.csv');

/** Pausa mínima entre duas execuções do Lighthouse, exigida pelas regras de ética do estudo. */
export const MIN_PAUSE_MS = 10_000;

export async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

export async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

export async function writeText(path, text) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, text, 'utf8');
}

/** Lê data/urls.json e valida ids e URLs. */
export async function loadServices() {
  const file = await readJson(URLS_FILE);
  const seen = new Set();
  for (const s of file.services) {
    if (!/^[a-z0-9-]+$/.test(s.id)) throw new Error(`Id de serviço inválido "${s.id}" (use [a-z0-9-])`);
    if (seen.has(s.id)) throw new Error(`Id de serviço repetido "${s.id}"`);
    seen.add(s.id);
    const u = new URL(s.url);
    if (u.protocol !== 'https:') throw new Error(`O serviço "${s.id}" precisa usar https`);
  }
  return file.services;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Hora local com deslocamento UTC, ex.: 2026-11-17T15:40:12-03:00 (mantém o horário do dia legível). */
export function localIsoTimestamp(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  const offsetMin = -date.getTimezoneOffset();
  const sign = offsetMin >= 0 ? '+' : '-';
  const abs = Math.abs(offsetMin);
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}
