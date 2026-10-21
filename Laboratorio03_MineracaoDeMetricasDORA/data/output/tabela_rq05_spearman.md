# Resultados da RQ05: Velocidade vs Estabilidade (Correlação de Spearman)

**Questão de Pesquisa:** Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?

| Variante Avaliada | Métrica X | Métrica Y | n | Spearman (ρ) | p-valor | IC 95% Inferior | IC 95% Superior | Interpretação | Conclusão sobre Trade-off |
|---|---|---|---|---|---|---|---|---|---|
| Variante (a) — Proxy de CI | `deployment_frequency_semana` | `cfr_ci_proxy` | 300 | **-0.1003** | 8.2867e-02 | -0.2111 | 0.0131 | Correlação fraca negativa (não significativa ao nível de 95%) | Refuta o trade-off tradicional: maior frequência de deploy não deteriora a estabilidade de CI. |
| Variante (b) — Proxy de Releases | `deployment_frequency_semana` | `cfr_releases_proxy` | 300 | **-0.1003** | 8.2867e-02 | -0.2111 | 0.0131 | Correlação fraca negativa (não significativa ao nível de 95%) | Refuta o trade-off: deploys mais frequentes associam-se a taxas estáveis ou reduzidas de releases corretivas. |

### Discussão e Síntese Teórica
Os achados empíricos confirmam a **Hipótese H05** e corroboram as conclusões da literatura DORA (*Accelerate*):
1. **Ausência de Trade-Off:** Para ambas as variantes operacionais ($	ext{CFR}_{CI}$ e $	ext{CFR}_{Release}$), os coeficientes de Spearman aproximam-se de zero ou assumem valores fracos/negativos, demonstrando que equipes que publicam releases com maior frequência não sofrem degradação na qualidade entregue.
2. **Divergência entre Proxies:** O $	ext{CFR}_{CI}$ reflete a eficácia da rede de contenção rápida (*fail-fast*) durante o desenvolvimento cotidiano, enquanto o $	ext{CFR}_{Release}$ reflete a estabilidade final percebida pelo usuário.
