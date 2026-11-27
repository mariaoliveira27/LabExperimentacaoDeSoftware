# Sprint 2: o que foi entregue

Texto para o card do GitHub Projects. Coleta de 25/11/2026; auditoria em [`audit-sprint2.md`](audit-sprint2.md).

## Entregue

- **Auditoria da Sprint 1** ([`audit-sprint1.md`](audit-sprint1.md)) e lista final de URLs, com as trocas e o motivo ([`url-changes.md`](url-changes.md)). Nenhum serviço foi trocado na coleta completa.
- **Coleta completa:** 10 serviços × 2 form factors × 10 execuções = 200 execuções válidas, em 205 tentativas. Duas sessões (manhã e tarde), uma execução por vez, pausa mínima de 10 s (menor pausa: 10,001 s), ordem aleatória com seed 3118576651, `robots.txt` verificado antes. Nenhum bloqueio.
- **Falhas registradas:** 5 tentativas inválidas, todas do Consumidor.gov.br (`NO_FCP`, métricas nulas), em `data/failed-runs.csv`; todas refeitas.
- **Validação dos dados:** 0 erros, 0 avisos ([`data-validation.md`](data-validation.md)). 105 valores fora da cerca de Tukey, marcados e não removidos.
- **Dados versionados:** bruto em `data/raw/full/*.json.gz` (23 MB), CSV em `data/processed/`, metadados em `data/run-metadata.json`.
- **Análise** ([`analysis/results.md`](../analysis/results.md)): estatística descritiva, Kruskal–Wallis com ε² e Dunn (Holm), Spearman com bootstrap, Wilcoxon pareado com rank-biserial e δ de Cliff, com e sem outliers; 4 gráficos.
- **Ameaças à validade** ([`ameacas-validade.md`](ameacas-validade.md)): os 4 tipos, com mitigação e limitação.

## Resultados

- **RQ1:** o desempenho varia muito entre os serviços (p < 0,001; ε² de 0,85 a 0,96). Pior LCP mobile: Meu SUS Digital, 33,9 s. Pior score mobile: Valores a Receber, 1.
- **RQ2:** inconclusivo (ρ = 0,41 mobile e 0,48 desktop; p Holm = 0,33; IC 95% inclui o zero).
- **RQ3:** o LCP mobile é maior nos 10 serviços: 13,7 s contra 3,6 s; mediana das diferenças 9,4 s; p Holm = 0,004.

## Pendente

- Provedor de internet e cidade da máquina de medição.
- Bloco da noite (seria uma nova fase).
- Confirmar os critérios de exclusão com o grupo e o professor.
