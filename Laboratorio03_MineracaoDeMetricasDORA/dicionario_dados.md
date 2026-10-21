# Dicionário de Dados — Mineração de Métricas DORA (Lab03)

Este documento especifica a estrutura, o tipo primitivo, as unidades de medida, a semântica conceitual e os endpoints/fórmulas de origem na API do GitHub para todos os conjuntos de dados produzidos no laboratório:
1. **Dataset Principal:** `data/output/repositorios_aprovados.csv`
2. **Dataset de Funil Amostral:** `data/output/funil_selecao.csv` e `funil_selecao.md`
3. **Dataset de Descartes de Triagem:** `data/output/descartes.csv`
4. **Conjuntos de Dados do Padrão-Ouro (Gold Standard):** `amostra_comum.csv`, `rotulos_maria.csv`, `rotulos_vinicius.csv`, `consenso_amostra_ouro.csv`
5. **Artefatos de Benchmark de Heurísticas:** `benchmark_heuristica.json` e `benchmark_heuristica_relatorio.md`

---

## 1. Dataset Principal: `repositorios_aprovados.csv`

Armazena a população final de repositórios que atenderam a todos os critérios de inclusão do funil metodológico ($\ge 1.000$ estrelas, uso ativo de GitHub Actions com $\ge 50$ execuções no branch padrão no intervalo, e $\ge 5$ releases publicadas na janela de 12 meses: 01/10/2023 a 30/09/2024).

| Coluna | Tipo Primitivo | Unidade | Descrição Conceitual | Fórmula ou Origem na API / Algoritmo |
|---|---|---|---|---|
| `full_name` | String | - | Identificador unívoco do repositório no GitHub no formato `owner/repo` | `GET /search/repositories` ou `item.full_name` |
| `owner` | String | - | Nome da organização ou usuário mantenedor | `item.owner.login` |
| `repo` | String | - | Nome do repositório | `item.name` |
| `stars` | Inteiro | estrelas | Contagem total de estrelas (indicador de popularidade / relevância) | `GET /repos/{owner}/{repo}` (`stargazers_count`) |
| `language` | String | - | Linguagem de programação predominante registrada pelo GitHub | `GET /repos/{owner}/{repo}` (`language`) |
| `default_branch` | String | - | Branch principal considerado no estudo (`main`, `master`, `trunk`, etc.) | `GET /repos/{owner}/{repo}` (`default_branch`) |
| `contributors_count` | Inteiro | pessoas | Total de contribuidores registrados no repositório | `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true` (número da última página via cabeçalho `Link: rel="last"`) |
| `created_at` | String (ISO 8601 UTC) | timestamp | Data e hora de criação do repositório no GitHub | `item.created_at` |
| `idade_dias` | Inteiro | dias | Tempo de existência do projeto em dias corridos até a data de execução | `(data_coleta - created_at).days` |
| `idade_anos` | Float | anos | Tempo de existência do projeto em anos | `idade_dias / 365.25` |
| `total_releases_janela` | Inteiro | releases | Total de releases válidas (`draft=false` e `prerelease=false`) publicadas dentro da janela de observação | Contagem de releases filtradas em `GET /repos/{owner}/{repo}/releases` |
| `total_runs_janela` | Inteiro | runs | Total de execuções de CI válidas (`event=push`, branch padrão, concluídas com sucesso ou falha) | Contagem de runs filtrados em `GET /repos/{owner}/{repo}/actions/runs` |
| `deployment_frequency_semana` | Float | releases/semana | Frequência de entrega/deploy semanal na janela de observação (RQ01) | `total_releases_janela / 52.14` |
| `lead_time_release_mediana_dias` | Float | dias | Lead Time for Changes mediano por release (Variante a da RQ02: intervalo entre a data da release e seu commit mais antigo) | Mediana de `(data_release - min(data_commit_i))` calculada para todas as releases da janela via paginação do endpoint `/compare` |
| `lead_time_commit_mediana_dias` | Float | dias | Lead Time for Changes mediano de todos os commits (Variante b da RQ02: idade de cada commit individual até a release que o empacotou) | Mediana de `(data_release - data_commit_j)` para todos os commits empacotados nas releases da janela |
| `cfr_ci_proxy` | Float | proporção [0, 1] | Change Failure Rate calculado pelo proxy de integrações de CI (Variante a da RQ03) | `runs_falha / (runs_falha + runs_sucesso)` |
| `cfr_releases_proxy` | Float | proporção [0, 1] | Change Failure Rate calculado pelo proxy de releases corretivas subsequentes em até 7 dias (Variante b da RQ03) | `releases_corretivas_em_ate_7_dias / releases_avaliadas` (com tratamento de censura) |
| `tempo_recuperacao_mediana_horas` | Float | horas | Tempo mediano de recuperação de episódios de falha de CI (RQ04) | Mediana de `(updated_at_sucesso - run_started_at_primeira_falha)` para cada episódio recuperado |
| `origem_metricas_estabilidade` | String | - | Identificação da procedência dos dados de estabilidade | `workflow_runs` na coleta real da API; `referencia_simulada` na execução sob `--reference-mode` |
| `origem_coleta` | String | - | Origem de extração dos metadados dos repositórios | `github_api` na mineração via API; `referencia_simulada` no mock de referência |
| `runs_sucessos` | Inteiro | runs | Quantidade de execuções de CI concluídas com conclusão `success` | Contagem nos runs coletados |
| `runs_falhas` | Inteiro | runs | Quantidade de execuções de CI concluídas com falha (`failure`, `timed_out`, `startup_failure`) | Contagem nos runs coletados |
| `runs_ignorados` | Inteiro | runs | Execuções de CI ignoradas por cancelamento, ação neutra ou status pendente (`cancelled`, `skipped`, etc.) | Não compõem o denominador de CFR nem a janela de estabilidade |
| `episodios_recuperados` | Inteiro | episódios | Total de sequências de falha que foram posteriormente sanadas por uma execução bem-sucedida do mesmo workflow | Contagem de episódios fechados |
| `episodios_censurados` | Inteiro | episódios | Falhas abertas no encerramento da janela sem recuperação observada | Não entram na mediana de tempo de recuperação |
| `proporcao_episodios_censurados` | Float | proporção [0, 1] | Fração de episódios de falha não recuperados na janela temporal | `episodios_censurados / (episodios_recuperados + episodios_censurados)` |
| `rework_rate` | Float | proporção [0, 1] | Taxa de retrabalho do repositório, medida pela proporção de releases identificadas como corretivas | `releases_corretivas / total_releases_janela` |
| `tier_dora_geral` | String (Enum) | - | Nível de maturidade DORA consolidado do repositório (`Elite`, `High`, `Medium`, `Low`) | Mediana dos scores numéricos (Elite=4, High=3, Medium=2, Low=1) arredondada para baixo |
| `tier_deployment_frequency` | String (Enum) | - | Classificação de frequência de deploy | Elite: $\ge 7$/sem; High: $1 \dots <7$/sem; Medium: $0.23 \dots <1$/sem; Low: $<0.23$/sem |
| `tier_lead_time` | String (Enum) | - | Classificação de lead time para mudanças | Elite: $<1$ dia; High: $1 \dots <7$ dias; Medium: $7 \dots <30$ dias; Low: $\ge 30$ dias |
| `tier_cfr` | String (Enum) | - | Classificação de taxa de falha de mudança | Elite: $\le 15\%$; High: $>15\%$ e $\le 30\%$; Medium: $>30\%$ e $\le 45\%$; Low: $>45\%$ |
| `tier_recovery_time` | String (Enum) | - | Classificação de tempo de recuperação | Elite: $<1$ hora; High: $1 \dots <24$ horas; Medium: $24 \dots <168$ horas; Low: $\ge 168$ horas |
| `escopo_contagem_runs` | String | - | Delimitação do escopo dos runs observados no cálculo | `execucoes_observadas_janela` |
| `tipo_projeto` | String (Enum) | - | Natureza arquitetural e de distribuição do software | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` |
| `total_prereleases_janela` | Inteiro | pré-releases | Total de pré-releases (`prerelease=true`, `draft=false`) na janela de 12 meses | Suporte à análise de sensibilidade da RQ07 |
| `total_releases_com_prereleases_janela` | Inteiro | entregas | Total de releases estáveis acrescido das pré-releases na janela | Unidade de deploy da Combinação C2 da RQ07 |
| `deployment_frequency_prereleases_semana` | Float | releases/semana | Frequência de deploy considerando releases + pré-releases | `total_releases_com_prereleases_janela / 52.14` |
| `total_tags_janela` | Inteiro | tags | Total de tags Git geradas no período anual | Unidade de deploy da Combinação C3 da RQ07 |
| `deployment_frequency_tags_semana` | Float | tags/semana | Frequência de deploy considerando todas as tags | `total_tags_janela / 52.14` |
| `tier_deployment_frequency_prereleases` | String (Enum) | - | Tier DORA de frequência com pré-releases | Classificação DORA (Combinação C2) |
| `tier_deployment_frequency_tags` | String (Enum) | - | Tier DORA de frequência com tags | Classificação DORA (Combinação C3) |

### Semântica de Valores Nulos, Censura e Limitações (`None` vs `0`)
- **Indisponibilidade vs Zero:** Células vazias (`None`) em `cfr_ci_proxy` e `tempo_recuperacao_mediana_horas` significam *ausência de episódios observáveis*, e não taxa zero ou tempo zero. Por exemplo, se um repositório não apresentou nenhuma falha no período, seu tempo de recuperação é indefinido (`None`), visto que não houve evento disparador de recuperação. Atribuir zero nesses casos distorceria as medianas agregadas para valores superestimados de eficiência.
- **Censura em CFR de Releases (`cfr_releases_proxy`):** Releases publicadas nos últimos 7 dias da janela de observação são marcadas como **censuradas à direita** e retiradas do denominador de avaliação de falha. Isso impede o viés de subnotificação (falso negativo), já que uma release corretiva subsequente poderia ocorrer logo após o corte temporal da coleta.
- **Censura em Tempo de Recuperação:** Incidentes de CI que permaneceram em falha até o corte temporal são contabilizados em `episodios_censurados`. Seus tempos parciais não são inseridos no cálculo de `tempo_recuperacao_mediana_horas` para evitar truncamento artificial, mas são rastreados em `proporcao_episodios_censurados`.
- **Modo de Referência:** Quando executado sob `--reference-mode`, as contagens brutas de runs (`runs_sucessos`, `runs_falhas`, etc.) permanecem vazias, visto que não houve coleta granular de workflows, registrando explicitamente `origem_metricas_estabilidade=referencia_simulada`.

---

## 2. Dataset de Funil Amostral: `funil_selecao.csv`

Mapeia a redução progressiva da população de repositórios em cada etapa sequencial de filtragem do protocolo.

| Coluna | Tipo Primitivo | Unidade | Descrição |
|---|---|---|---|
| `etapa` | String | - | Nome ordinal descritivo da fase de filtragem |
| `total_restante` | Inteiro | repositórios | Quantidade de repositórios que avançaram após a aplicação do critério |
| `descartados` | Inteiro | repositórios | Quantidade de repositórios eliminados especificamente nesta etapa |
| `motivo_descarte` | String | - | Código padronizado da regra de eliminação (`sem_github_actions`, `menos_de_5_releases_na_janela`, `menos_de_50_runs_no_default_branch`, etc.) |
| `retencao_pct` | Float | % | Percentual acumulado de repositórios mantidos em relação ao total inicial da busca particionada |

---

## 3. Dataset de Rastreio de Descartes: `descartes.csv`

Documenta nominalmente cada repositório candidato que foi rejeitado durante o funil de seleção, garantindo a auditabilidade e reprodutibilidade do estudo.

| Coluna | Tipo Primitivo | Unidade | Descrição |
|---|---|---|---|
| `full_name` | String | - | Nome completo do repositório no GitHub (`owner/repo`) |
| `etapa` | String | - | Identificação da etapa do funil em que o repositório foi rejeitado |
| `motivo` | String | - | Categoria padronizada de descarte |
| `detalhes` | String | - | Evidência empírica obtida na API do GitHub justificando a eliminação (ex: número insuficiente de releases encontradas, ausência de workflows de CI, etc.) |

---

## 4. Conjuntos de Dados do Padrão-Ouro (Gold Standard)

Compreende a amostragem estratificada e rotulagem humana manual independente realizada para calibrar e validar as heurísticas automatizadas de detecção de releases corretivas (RQ03 — Variante b).

### 4.1 Amostra Sorteada: `amostra_comum.csv`
Gerada por `gerar_amostra_rotulagem.py` via amostragem estratificada aleatória reproduzível (`random_state=42`) de 60 repositórios e 5 releases estáveis por repositório (totalizando 300 releases).

| Coluna | Tipo | Descrição |
|---|---|---|
| `full_name` | String | Nome unívoco do repositório (`owner/repo`) |
| `release_id` | Inteiro | Identificador numérico da release na API REST do GitHub |
| `published_at` | String (ISO 8601 UTC) | Data e hora de publicação oficial da release |
| `tag_name` | String | Identificador da tag Git associada à release (ex: `v1.2.3`) |
| `html_url` | String (URL) | Link direto para a página de release no GitHub |
| `release_notes_url` | String (URL) | Link para as notas de release e corpo de descrição |
| `commits_url` | String (URL) | Link do compare de commits (`/compare/{previous_tag}...{tag_name}`) |
| `previous_tag` | String | Tag da release estável anterior na janela cronológica |
| `tipo_projeto` | String (Enum) | Categoria arquitetural do projeto (campo a ser julgado) |
| `entrega_real` | String (Enum) | Confirmação se a release representa entrega de valor funcional (campo a ser julgado) |
| `corretiva` | String (Enum) | Veredito humano se a release teve escopo corretivo (campo a ser julgado) |
| `justificativa` | String | Fundamentação textual do avaliador humano |
| `evidencia` | String | Trecho específico das notas, commits ou PRs que comprova a classificação |

### 4.2 Arquivos de Rotulagem Independente: `rotulos_maria.csv` e `rotulos_vinicius.csv`
Contêm o julgamento cego e independente de 60 repositórios / 300 releases realizado por cada membro da equipe.

| Coluna | Tipo | Descrição | Valores Admissíveis |
|---|---|---|---|
| `repo` | String | Repositório no formato `owner/repo` | Corresponde aos 60 repositórios selecionados |
| `tipo_projeto` | String (Enum) | Classificação do software | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` |
| `entrega_real` | String (Enum) | Confirma se é uma entrega funcional e não mero bump ou tag vazia | `sim`, `não`, `incerto` |
| `release_tag` | String | Tag Git da release avaliada | ex: `v2.4.1`, `1.12.1` |
| `tag_anterior` | String | Tag Git da release imediatamente precedente | ex: `v2.4.0` ou vazio na primeira release |
| `release_date` | String (YYYY-MM-DD) | Data de publicação da release | Data calendário UTC |
| `release_url` | String (URL) | Link para visualização da release no GitHub | URL válida em `github.com` |
| `commits_resumo` | String | Síntese dos commits e notas de release observados | Texto descritivo das mensagens e escopo |
| `corretiva` | String (Enum) | Rótulo independente atribuído pelo pesquisador | `sim` (release com escopo corretivo/hotfix/bugfix) ou `não` (release de evolução, feature, breaking changes) |
| `justificativa` | String | Racional do pesquisador com base nas evidências empíricas | Explicação detalhada da classificação |

### 4.3 Consenso e Concordância: `consenso_amostra_ouro.csv`
Armazena a resolução de divergências entre os avaliadores Maria e Vinicius, consolidando a verdade fundamental para treinamento e validação das heurísticas.
- **Métricas Associadas:** Coeficiente Kappa de Cohen ($\kappa$) para concordância entre pares e concordância percentual bruta.

---

## 5. Artefatos de Benchmark: `benchmark_heuristica.json` e `benchmark_heuristica_relatorio.md`

Estruturam a avaliação empírica das três versões da heurística automatizada contra o conjunto padrão-ouro (`rotulos_maria.csv`):
- **V1 (Keywords Básicas):** Regex restrito a termos no título da release (`fix`, `patch`, `hotfix`, `bug`).
- **V2 (Semver + Keywords):** Combina incremento de versão SemVer (mudança apenas no terceiro dígito `x.y.Z`) com palavras-chave nas notas e títulos.
- **V3 (Híbrida Semver + Mensagens de Commit + Intervalo Temporal):** Integra SemVer, análise das mensagens de commit empacotadas via compare e detecção de proximidade temporal ($\le 7$ dias da release anterior).

| Métrica no Benchmark | Tipo | Interpretação |
|---|---|---|
| `acuracia` | Float [0, 1] | Proporção de classificações corretas (verdadeiros positivos + verdadeiros negativos) sobre o total |
| `precisao` | Float [0, 1] | Taxa de releases classificadas como corretivas que eram de fato corretivas |
| `revocacao` (Recall) | Float [0, 1] | Capacidade da heurística de encontrar todas as releases corretivas reais do padrão-ouro |
| `f1_score` | Float [0, 1] | Média harmônica entre precisão e revocação (critério de qualidade exigindo $F1 \ge 0.70$) |
| `matriz_confusao` | Objeto / Matriz $2 \times 2$ | Frequência de `VP`, `FP`, `VN`, `FN` |

---

## 6. Dataset de Apoio à RQ07: `dados_rq07_sensibilidade.csv`

Desenvolvido para abastecer a análise de sensibilidade e estabilidade das classificações DORA sob responsabilidade de Vinícius (RQ07), confrontando as combinações operacionais C1, C2 e C3.

| Coluna | Tipo Primitivo | Descrição |
|---|---|---|
| `full_name` | String | Identificador unívoco do repositório (`owner/repo`) |
| `tier_c1_referencia` | String (Enum) | Classificação DORA geral na Combinação C1 (Release + Lead Time a + CFR a) |
| `tier_c2_prereleases` | String (Enum) | Classificação DORA geral na Combinação C2 (Release + Pré-release + Lead Time b + CFR b) |
| `tier_c3_tags` | String (Enum) | Classificação DORA geral na Combinação C3 (Tags + Lead Time b + CFR a) |
| `df_c1_releases` | Float | Frequência de deploy semanal baseada em releases estáveis |
| `df_c2_prereleases` | Float | Frequência de deploy semanal considerando releases e pré-releases |
| `df_c3_tags` | Float | Frequência de deploy semanal considerando tags |
| `lt_c1_variante_a` | Float | Lead time mediano por release (dias) |
| `lt_c2_variante_b` | Float | Lead time mediano por commit (dias) |
| `lt_c3_variante_b` | Float | Lead time mediano por commit (dias) |
| `cfr_c1_variante_a` | Float | Taxa de falha proxy de CI |
| `cfr_c2_variante_b` | Float | Taxa de falha proxy de releases corretivas |
| `cfr_c3_variante_a` | Float | Taxa de falha proxy de CI |
| `recovery_hours` | Float | Tempo de recuperação mediano em horas |
| `mudou_c1_c2` | Booleano | Indica se o repositório alterou de patamar DORA entre C1 e C2 |
| `mudou_c1_c3` | Booleano | Indica se o repositório alterou de patamar DORA entre C1 e C3 |
| `mudou_c2_c3` | Booleano | Indica se o repositório alterou de patamar DORA entre C2 e C3 |

