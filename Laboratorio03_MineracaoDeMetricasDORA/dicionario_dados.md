# Dicionário de Dados — Mineração de Métricas DORA (Lab03)

Este documento especifica cada coluna dos arquivos de dados gerados pelo pipeline de mineração (`repositorios_aprovados.csv`, `funil_selecao.csv`, `descartes.csv`), incluindo seu tipo primitivo, unidade de medida, descrição conceitual e fórmula ou endpoint de origem na API do GitHub.

---

## 1. Dataset Principal: `repositorios_aprovados.csv`

| Coluna | Tipo | Unidade | Descrição Conceitual | Fórmula ou Origem na API |
|---|---|---|---|---|
| `full_name` | String | - | Identificador único do repositório no GitHub (`owner/repo`) | `GET /search/repositories` ou `item.full_name` |
| `owner` | String | - | Nome da organização ou usuário mantenedor | `item.owner.login` |
| `repo` | String | - | Nome do repositório | `item.name` |
| `stars` | Inteiro | estrelas | Contagem de estrelas (popularidade) | `GET /repos/{owner}/{repo}` (`stargazers_count`) |
| `language` | String | - | Linguagem primária predominante do projeto | `GET /repos/{owner}/{repo}` (`language`) |
| `default_branch` | String | - | Branch principal considerado no estudo (`main`, `master`, `trunk`) | `GET /repos/{owner}/{repo}` (`default_branch`) |
| `contributors_count` | Inteiro | pessoas | Total de contribuidores registrados no repositório | `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true` (número da última página via cabeçalho `Link: rel="last"`) |
| `created_at` | String (ISO 8601) | data/hora | Data e hora de criação do repositório | `item.created_at` |
| `idade_dias` | Inteiro | dias | Tempo de existência do projeto em dias | `(data_atual - created_at).days` |
| `idade_anos` | Float | anos | Tempo de existência do projeto em anos | `idade_dias / 365.25` |
| `total_releases_janela` | Inteiro | releases | Total de releases válidas (`draft=false`, `prerelease=false`) na janela | Contagem de releases filtradas em `GET /repos/{owner}/{repo}/releases` |
| `total_runs_janela` | Inteiro | runs | Total de execuções de CI válidas no default branch (`event=push`) | Contagem de runs filtrados em `GET /repos/{owner}/{repo}/actions/runs` |
| `deployment_frequency_semana` | Float | releases/semana | Frequência de deploy semanal na janela de observação (RQ01) | `total_releases_janela / 52.14` |
| `lead_time_release_mediana_dias` | Float | dias | Lead time for changes mediano por release (Variante a da RQ02) | Mediana de `(data_release - data_commit_mais_antigo_da_release)` |
| `lead_time_commit_mediana_dias` | Float | dias | Lead time for changes mediano de todos os commits (Variante b da RQ02) | Mediana de `(data_release - data_commit)` para todos os commits |
| `cfr_ci_proxy` | Float | proporção [0, 1] | Change failure rate calculado pelo proxy de CI (Variante a da RQ03) | `runs_falha / (runs_falha + runs_sucesso)` |
| `cfr_releases_proxy` | Float | proporção [0, 1] | Change failure rate calculado pelo proxy de releases corretivas em até 7 dias (Variante b da RQ03) | `releases_corretivas_em_ate_7_dias / releases_avaliadas` (excluindo censura dos últimos 7 dias) |
| `tempo_recuperacao_mediana_horas` | Float | horas | Tempo de recuperação mediano dos episódios de falha (RQ04) | Mediana de `(fim_sucesso_updated_at - inicio_primeira_falha_run_started_at)` |
| `tier_dora_geral` | String (Enum) | - | Categoria DORA consolidada do repositório (`Elite`, `High`, `Medium`, `Low`) | Mediana dos 4 scores DORA (4, 3, 2, 1) arredondada para baixo |
| `tier_deployment_frequency` | String (Enum) | - | Classificação de frequência de deploy | Elite: ≥ 7/sem; High: 1..6.99/sem; Medium: 0.23..0.99/sem; Low: < 0.23/sem |
| `tier_lead_time` | String (Enum) | - | Classificação de lead time | Elite: < 1 dia; High: 1..< 7 dias; Medium: 7..< 30 dias; Low: ≥ 30 dias |
| `tier_cfr` | String (Enum) | - | Classificação de taxa de falha | Elite: ≤ 15%; High: > 15% e ≤ 30%; Medium: > 30% e ≤ 45%; Low: > 45% |
| `tier_recovery_time` | String (Enum) | - | Classificação de tempo de recuperação | Elite: < 1 hora; High: 1..< 24 horas; Medium: 24..< 168 horas; Low: ≥ 168 horas |

---

## 2. Dataset de Funil: `funil_selecao.csv`

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `etapa` | String | - | Descrição ordinal da etapa no funil de seleção |
| `total_restante` | Inteiro | repositórios | Número de repositórios que continuam na amostra após a etapa |
| `descartados` | Inteiro | repositórios | Número de repositórios descartados especificamente nesta etapa |
| `motivo_descarte` | String | - | Identificador padronizado da razão de descarte (`sem_github_actions`, `menos_de_5_releases_na_janela`, etc.) |
| `retencao_pct` | Float | % | Proporção percentual de repositórios retidos em relação à busca inicial |

---

## 3. Dataset de Rastreio de Descartes: `descartes.csv`

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `full_name` | String | - | Nome completo do repositório descartado (`owner/repo`) |
| `etapa` | String | - | Nome da etapa do funil na qual o descarte ocorreu |
| `motivo` | String | - | Motivo padronizado do descarte |
| `detalhes` | String | - | Justificativa com evidência empírica coletada na API |
