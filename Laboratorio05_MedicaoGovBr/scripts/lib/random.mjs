// Gerador pseudoaleatório com seed, para que a ordem das execuções possa ser reproduzida a partir
// da seed gravada.
import { randomInt } from 'node:crypto';

/** mulberry32: gerador de 32 bits pequeno e rápido. Devolve uma função que gera números em [0, 1). */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Embaralhamento de Fisher-Yates guiado por `rng`. Devolve um novo array; a entrada não é alterada. */
export function shuffle(items, rng) {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** Nova seed aleatória de 32 bits, usada quando nenhuma é passada na linha de comando. */
export function newSeed() {
  return randomInt(0, 2 ** 32 - 1);
}
