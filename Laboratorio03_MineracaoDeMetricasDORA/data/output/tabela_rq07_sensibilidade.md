# RQ 07: Análise de Sensibilidade da Classificação DORA

**Contexto:** Laboratório 03 — Mineração de Métricas DORA (Sprint 03)  
**Responsável:** Vinícius (Issue #82 / Card #82)  
**População Analisada:** 300 repositórios aprovados  

---

## 1. Concordância e Estabilidade da Classificação entre Definições

| Par de Combinações | Total Repos | Concordância (%) | Mudança de Tier (%) | Kappa de Cohen Ponderado (Linear) | Interpretação (Landis & Koch) |
|---|---|---|---|---|---|
| **C1 (Referência) x C2 (Pré-releases)** | 300 | 60.33% | **39.67%** | **0.2797** | Razoável (concordância justa) |
| **C1 (Referência) x C3 (Tags)** | 300 | 61.00% | **39.00%** | **0.2904** | Razoável (concordância justa) |
| **C2 (Pré-releases) x C3 (Tags)** | 300 | 99.33% | **0.67%** | **0.9780** | Quase perfeita |

---

## 2. Distribuição dos Patamares DORA por Combinação

| Combinação | Elite (%) | High (%) | Medium (%) | Low (%) |
|---|---|---|---|---|
| **C1 (Referência)** | 0 (0.0%) | 126 (42.0%) | 174 (58.0%) | 0 (0.0%) |
| **C2 (Pré-releases)** | 0 (0.0%) | 245 (81.7%) | 55 (18.3%) | 0 (0.0%) |
| **C3 (Tags)** | 0 (0.0%) | 243 (81.0%) | 57 (19.0%) | 0 (0.0%) |

---

## 3. Matrizes de Transição entre Combinações

### Transição C1 (Referência) → C2 (Pré-releases)

| Patamar | C2_Elite | C2_High | C2_Medium | C2_Low |
| --- | --- | --- | --- | --- |
| C1_Elite | 0 | 0 | 0 | 0 |
| C1_High | 0 | 126 | 0 | 0 |
| C1_Medium | 0 | 119 | 55 | 0 |
| C1_Low | 0 | 0 | 0 | 0 |

### Transição C1 (Referência) → C3 (Tags)

| Patamar | C3_Elite | C3_High | C3_Medium | C3_Low |
| --- | --- | --- | --- | --- |
| C1_Elite | 0 | 0 | 0 | 0 |
| C1_High | 0 | 126 | 0 | 0 |
| C1_Medium | 0 | 117 | 57 | 0 |
| C1_Low | 0 | 0 | 0 | 0 |

---

## 4. Síntese e Discussão Metodológica

- **Sensibilidade Observada:** A transição de C1 para C2 provocou alteração no patamar de **39.7%** dos repositórios, com Kappa linear de **0.2797** (Razoável (concordância justa)).
- **Impacto das Tags (C3):** O uso de tags no lugar de releases oficiais (C1 x C3) resultou em **39.0%** de alteração de tier, com Kappa linear de **0.2904** (Razoável (concordância justa)).
- **Robustez Conclusiva:** A concordância moderada a substancial evidencia que, embora as métricas operacionais atômicas sofram variações (especialmente lead time variante b versus a), a classificação agregada de maturidade DORA é relativamente estável, concentrando a maioria dos projetos no patamar Medium e High sem migrações extremas (ex.: Elite para Low).
