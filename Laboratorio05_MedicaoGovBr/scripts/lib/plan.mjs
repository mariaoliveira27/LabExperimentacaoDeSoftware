// Builds the randomized execution plan for run-lighthouse.mjs.
import { mulberry32, shuffle } from './random.mjs';

export const FORM_FACTORS = ['mobile', 'desktop'];

/**
 * Shuffles all (service, formFactor) slots with the seeded PRNG. Run numbers are assigned
 * after shuffling, so `run` is the chronological replicate index within a service and form
 * factor (run 1 is the first time that combination was measured in the session).
 */
export function buildPlan(services, runs, seed) {
  const slots = [];
  for (const s of services) {
    for (const formFactor of FORM_FACTORS) {
      for (let i = 0; i < runs; i++) slots.push({ serviceId: s.id, url: s.url, formFactor });
    }
  }
  const seen = new Map();
  return shuffle(slots, mulberry32(seed)).map((t, i) => {
    const key = `${t.serviceId}|${t.formFactor}`;
    const run = (seen.get(key) ?? 0) + 1;
    seen.set(key, run);
    return { order: i + 1, ...t, run };
  });
}
