// Shared helpers for the Lab05 scripts: paths, service list loading and small utilities.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const DATA_DIR = join(ROOT, 'data');
export const DOCS_DIR = join(ROOT, 'docs');
export const URLS_FILE = join(DATA_DIR, 'urls.json');
export const ROBOTS_JSON = join(DATA_DIR, 'robots-check.json');
export const RUN_METADATA_FILE = join(DATA_DIR, 'run-metadata.json');

/** Minimum pause between two Lighthouse executions, required by the study's ethics rules. */
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

/** Loads data/urls.json and validates ids and URLs. */
export async function loadServices() {
  const file = await readJson(URLS_FILE);
  const seen = new Set();
  for (const s of file.services) {
    if (!/^[a-z0-9-]+$/.test(s.id)) throw new Error(`Invalid service id "${s.id}" (use [a-z0-9-])`);
    if (seen.has(s.id)) throw new Error(`Duplicated service id "${s.id}"`);
    seen.add(s.id);
    const u = new URL(s.url);
    if (u.protocol !== 'https:') throw new Error(`Service "${s.id}" must use https`);
  }
  return file.services;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Local time with UTC offset, e.g. 2026-11-17T15:40:12-03:00 (keeps time-of-day readable). */
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
