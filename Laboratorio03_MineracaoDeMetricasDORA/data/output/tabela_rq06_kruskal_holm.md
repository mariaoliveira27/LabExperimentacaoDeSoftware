# Resultados da RQ06: Fatores Associados ao Desempenho DORA

**Questão de Pesquisa:** Quais características dos repositórios estão associadas a um melhor desempenho DORA?

## 1. Testes Omnibus de Kruskal-Wallis com Correção de Holm e Epsilon-Quadrado (ε²)

| Fator Avaliado | Métrica DORA | k | n | Estatística H | p-valor Bruto | p-valor Holm | Significativo (Holm) | Epsilon² (ε²) | Magnitude do Efeito |
|---|---|---|---|---|---|---|---|---|---|
| Popularidade (Estrelas) | Deployment Frequency | 4 | 300 | 80.842 | 2.0251e-17 | 5.4677e-16 | Sim (**p < 0.05**) | **0.2704** | grande |
| Popularidade (Estrelas) | Lead Time (Por Release) | 4 | 300 | 80.842 | 2.0251e-17 | 5.4677e-16 | Sim (**p < 0.05**) | **0.2704** | grande |
| Popularidade (Estrelas) | Lead Time (Por Commit) | 4 | 300 | 80.842 | 2.0251e-17 | 5.4677e-16 | Sim (**p < 0.05**) | **0.2704** | grande |
| Popularidade (Estrelas) | Change Failure Rate (CI) | 4 | 300 | 4.708 | 1.9444e-01 | 1.0000e+00 | Não | **0.0157** | pequeno |
| Popularidade (Estrelas) | Change Failure Rate (Releases) | 4 | 300 | 4.708 | 1.9444e-01 | 1.0000e+00 | Não | **0.0157** | pequeno |
| Popularidade (Estrelas) | Tempo de Recuperação | 4 | 300 | 9.739 | 2.0917e-02 | 3.5559e-01 | Não | **0.0326** | pequeno |
| Tamanho da Equipe (Contribuidores) | Deployment Frequency | 4 | 300 | 82.839 | 7.5487e-18 | 2.2646e-16 | Sim (**p < 0.05**) | **0.2771** | grande |
| Tamanho da Equipe (Contribuidores) | Lead Time (Por Release) | 4 | 300 | 82.839 | 7.5487e-18 | 2.2646e-16 | Sim (**p < 0.05**) | **0.2771** | grande |
| Tamanho da Equipe (Contribuidores) | Lead Time (Por Commit) | 4 | 300 | 82.839 | 7.5487e-18 | 2.2646e-16 | Sim (**p < 0.05**) | **0.2771** | grande |
| Tamanho da Equipe (Contribuidores) | Change Failure Rate (CI) | 4 | 300 | 4.078 | 2.5316e-01 | 1.0000e+00 | Não | **0.0136** | pequeno |
| Tamanho da Equipe (Contribuidores) | Change Failure Rate (Releases) | 4 | 300 | 4.078 | 2.5316e-01 | 1.0000e+00 | Não | **0.0136** | pequeno |
| Tamanho da Equipe (Contribuidores) | Tempo de Recuperação | 4 | 300 | 41.318 | 5.5990e-09 | 1.0078e-07 | Sim (**p < 0.05**) | **0.1382** | moderado |
| Idade do Repositório (Anos) | Deployment Frequency | 4 | 300 | 48.537 | 1.6370e-10 | 3.4377e-09 | Sim (**p < 0.05**) | **0.1623** | grande |
| Idade do Repositório (Anos) | Lead Time (Por Release) | 4 | 300 | 48.537 | 1.6370e-10 | 3.4377e-09 | Sim (**p < 0.05**) | **0.1623** | grande |
| Idade do Repositório (Anos) | Lead Time (Por Commit) | 4 | 300 | 48.537 | 1.6370e-10 | 3.4377e-09 | Sim (**p < 0.05**) | **0.1623** | grande |
| Idade do Repositório (Anos) | Change Failure Rate (CI) | 4 | 300 | 1.494 | 6.8354e-01 | 1.0000e+00 | Não | **0.0050** | desprezível |
| Idade do Repositório (Anos) | Change Failure Rate (Releases) | 4 | 300 | 1.494 | 6.8354e-01 | 1.0000e+00 | Não | **0.0050** | desprezível |
| Idade do Repositório (Anos) | Tempo de Recuperação | 4 | 300 | 1.645 | 6.4918e-01 | 1.0000e+00 | Não | **0.0055** | desprezível |
| Tipo de Projeto | Deployment Frequency | 3 | 300 | 1.377 | 5.0232e-01 | 1.0000e+00 | Não | **0.0046** | desprezível |
| Tipo de Projeto | Lead Time (Por Release) | 3 | 300 | 1.377 | 5.0232e-01 | 1.0000e+00 | Não | **0.0046** | desprezível |
| Tipo de Projeto | Lead Time (Por Commit) | 3 | 300 | 1.377 | 5.0232e-01 | 1.0000e+00 | Não | **0.0046** | desprezível |
| Tipo de Projeto | Change Failure Rate (CI) | 3 | 300 | 1.141 | 5.6531e-01 | 1.0000e+00 | Não | **0.0038** | desprezível |
| Tipo de Projeto | Change Failure Rate (Releases) | 3 | 300 | 1.141 | 5.6531e-01 | 1.0000e+00 | Não | **0.0038** | desprezível |
| Tipo de Projeto | Tempo de Recuperação | 3 | 300 | 1.448 | 4.8475e-01 | 1.0000e+00 | Não | **0.0048** | desprezível |
| Linguagem Principal | Deployment Frequency | 6 | 300 | 63.060 | 2.8291e-12 | 6.7899e-11 | Sim (**p < 0.05**) | **0.2109** | grande |
| Linguagem Principal | Lead Time (Por Release) | 6 | 300 | 63.060 | 2.8291e-12 | 6.7899e-11 | Sim (**p < 0.05**) | **0.2109** | grande |
| Linguagem Principal | Lead Time (Por Commit) | 6 | 300 | 63.060 | 2.8291e-12 | 6.7899e-11 | Sim (**p < 0.05**) | **0.2109** | grande |
| Linguagem Principal | Change Failure Rate (CI) | 6 | 300 | 3.418 | 6.3578e-01 | 1.0000e+00 | Não | **0.0114** | pequeno |
| Linguagem Principal | Change Failure Rate (Releases) | 6 | 300 | 3.418 | 6.3578e-01 | 1.0000e+00 | Não | **0.0114** | pequeno |
| Linguagem Principal | Tempo de Recuperação | 6 | 300 | 6.980 | 2.2211e-01 | 1.0000e+00 | Não | **0.0233** | pequeno |

---

## 2. Resumo de Comparações Pareadas Post-Hoc (Cliff's Delta e Teste de Mann-Whitney)

Abaixo destacam-se as comparações mais representativas entre quartis e subgrupos de maior relevância prática:

| Fator | Métrica | Comparação | n₁ | n₂ | Mediana G1 | Mediana G2 | Cliff's Delta (δ) | Magnitude (Romano) | p-valor Holm | Significativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Popularidade (Estrelas) | Deployment Frequency | `Q1 (Baixa) vs Q2 (Média-Baixa)` | 75 | 75 | 0.153 | 0.23 | **-0.3787** | médio | 1.7630e-04 | Sim |
| Popularidade (Estrelas) | Deployment Frequency | `Q1 (Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 0.153 | 0.384 | **-0.7454** | grande | 1.4259e-14 | Sim |
| Popularidade (Estrelas) | Deployment Frequency | `Q1 (Baixa) vs Q4 (Alta)` | 75 | 74 | 0.153 | 0.345 | **-0.6476** | grande | 4.0649e-11 | Sim |
| Popularidade (Estrelas) | Deployment Frequency | `Q2 (Média-Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 0.23 | 0.384 | **-0.4447** | médio | 9.3617e-06 | Sim |
| Popularidade (Estrelas) | Deployment Frequency | `Q2 (Média-Baixa) vs Q4 (Alta)` | 75 | 74 | 0.23 | 0.345 | **-0.3411** | médio | 6.4506e-04 | Sim |
| Popularidade (Estrelas) | Deployment Frequency | `Q3 (Média-Alta) vs Q4 (Alta)` | 76 | 74 | 0.384 | 0.345 | **+0.0740** | desprezível | 4.3496e-01 | Não |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q1 (Baixa) vs Q2 (Média-Baixa)` | 75 | 75 | 15.0 | 10.0 | **+0.3787** | médio | 1.7630e-04 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q1 (Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 15.0 | 6.0 | **+0.7454** | grande | 1.4259e-14 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q1 (Baixa) vs Q4 (Alta)` | 75 | 74 | 15.0 | 6.67 | **+0.6476** | grande | 4.0649e-11 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q2 (Média-Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 10.0 | 6.0 | **+0.4447** | médio | 9.3617e-06 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q2 (Média-Baixa) vs Q4 (Alta)` | 75 | 74 | 10.0 | 6.67 | **+0.3411** | médio | 6.4506e-04 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Release) | `Q3 (Média-Alta) vs Q4 (Alta)` | 76 | 74 | 6.0 | 6.67 | **-0.0740** | desprezível | 4.3496e-01 | Não |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q1 (Baixa) vs Q2 (Média-Baixa)` | 75 | 75 | 6.75 | 4.5 | **+0.3787** | médio | 1.7630e-04 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q1 (Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 6.75 | 2.7 | **+0.7454** | grande | 1.4259e-14 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q1 (Baixa) vs Q4 (Alta)` | 75 | 74 | 6.75 | 3.0 | **+0.6476** | grande | 4.0649e-11 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q2 (Média-Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 4.5 | 2.7 | **+0.4447** | médio | 9.3617e-06 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q2 (Média-Baixa) vs Q4 (Alta)` | 75 | 74 | 4.5 | 3.0 | **+0.3411** | médio | 6.4506e-04 | Sim |
| Popularidade (Estrelas) | Lead Time (Por Commit) | `Q3 (Média-Alta) vs Q4 (Alta)` | 76 | 74 | 2.7 | 3.0 | **-0.0740** | desprezível | 4.3496e-01 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q1 (Baixa) vs Q2 (Média-Baixa)` | 75 | 75 | 0.15 | 0.133 | **-0.0475** | desprezível | 1.0000e+00 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q1 (Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 0.15 | 0.117 | **+0.1075** | desprezível | 7.6227e-01 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q1 (Baixa) vs Q4 (Alta)` | 75 | 74 | 0.15 | 0.117 | **+0.1238** | desprezível | 7.6227e-01 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q2 (Média-Baixa) vs Q3 (Média-Alta)` | 75 | 76 | 0.133 | 0.117 | **+0.1621** | pequeno | 4.5975e-01 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q2 (Média-Baixa) vs Q4 (Alta)` | 75 | 74 | 0.133 | 0.117 | **+0.1676** | pequeno | 4.5975e-01 | Não |
| Popularidade (Estrelas) | Change Failure Rate (CI) | `Q3 (Média-Alta) vs Q4 (Alta)` | 76 | 74 | 0.117 | 0.117 | **-0.0039** | desprezível | 1.0000e+00 | Não |
| Popularidade (Estrelas) | Change Failure Rate (Releases) | `Q1 (Baixa) vs Q2 (Média-Baixa)` | 75 | 75 | 0.09 | 0.08 | **-0.0475** | desprezível | 1.0000e+00 | Não |

*Nota:* O relatório completo com todas as 216 comparações pareadas encontra-se disponível em [`tabela_rq06_posthoc_cliff.csv`](tabela_rq06_posthoc_cliff.csv).
