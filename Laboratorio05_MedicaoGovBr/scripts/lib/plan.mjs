// Monta o plano de execução aleatorizado do run-lighthouse.mjs.
import { mulberry32, shuffle } from './random.mjs';

export const FORM_FACTORS = ['mobile', 'desktop'];

/**
 * Embaralha todas as combinações (serviço, form factor) com o gerador com seed. O número da
 * réplica é atribuído depois do embaralhamento, então `run` é a ordem cronológica dentro de um
 * serviço e form factor (run 1 é a primeira vez que aquela combinação foi medida na sessão).
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
