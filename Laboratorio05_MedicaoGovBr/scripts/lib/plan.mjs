// Monta o plano de execução aleatorizado do run-lighthouse.mjs.
import { mulberry32, shuffle } from './random.mjs';

export const FORM_FACTORS = ['mobile', 'desktop'];

/**
 * Divide as `runs` réplicas de cada (serviço, form factor) em `blocks` blocos de horário iguais e
 * embaralha cada bloco com o mesmo gerador com seed, um bloco depois do outro. O número da réplica
 * é atribuído depois do embaralhamento, então `run` é a ordem cronológica dentro de um serviço e
 * form factor: no bloco 1 ficam as réplicas 1..R/B, no bloco 2 as réplicas R/B+1..2R/B, e assim por
 * diante. Com blocks = 1 o plano é o mesmo da Sprint 1 (um único embaralhamento).
 */
export function buildPlan(services, runs, seed, blocks = 1) {
  if (!Number.isInteger(blocks) || blocks < 1 || runs % blocks !== 0) {
    throw new Error(`runs (${runs}) precisa ser múltiplo de blocks (${blocks})`);
  }
  const perBlock = runs / blocks;
  const rng = mulberry32(seed);
  const seen = new Map();
  const plan = [];
  for (let block = 1; block <= blocks; block++) {
    const slots = [];
    for (const s of services) {
      for (const formFactor of FORM_FACTORS) {
        for (let i = 0; i < perBlock; i++) slots.push({ serviceId: s.id, url: s.url, formFactor });
      }
    }
    for (const t of shuffle(slots, rng)) {
      const key = `${t.serviceId}|${t.formFactor}`;
      const run = (seen.get(key) ?? 0) + 1;
      seen.set(key, run);
      plan.push({ order: plan.length + 1, block, ...t, run });
    }
  }
  return plan;
}
