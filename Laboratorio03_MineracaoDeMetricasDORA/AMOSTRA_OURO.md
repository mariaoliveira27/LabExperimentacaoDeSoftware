# Amostra para rotulagem independente — Lab03S02

Os identificadores foram conferidos no GitHub: [sorteio #61](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/61), [concordância #70](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/70), [rotulagem #62](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/62) e [metodologia #63](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/63). As tarefas 01–03 da divisão não são os números das Issues.

## Estado da entrega

A implementação do sorteio, da preparação/validação de Áulus e da concordância está disponível. A execução real do sorteio foi interrompida com código 2: `data/output/repositorios_aprovados.csv` tem somente **100 repositórios**, sem proveniência registrada. Não existem atualmente a referência comum verificável de 300 releases ou três avaliações humanas completas vinculadas a ela. Portanto, `rotulos_aulus.csv` será criado somente quando existir essa referência: a Issue #62 permanece **pendente de julgamento humano de Áulus**. Não foi criado um CSV com releases inventadas para aparentar a conclusão da tarefa.

O gerador anterior tinha projetos, releases, mensagens resumidas e classificações fixas no código. Foi substituído. Os dois arquivos antigos chamados `rotulos_vinicius.csv` foram preservados; eles e os relatórios antigos de benchmarking não comprovam uma avaliação humana independente nem devem servir de referência para este fluxo.

## Contrato de entrada da coleta final

A coleta real deve fornecer estes três artefatos, preservando também seus registros de requisições/paginação e respostas originais. O pipeline atual da Sprint 01 **não produz este contrato** e utiliza candidatos de `seed_data.py`; aumentar `target_approved_repos` ou executar `--reference-mode` não prepara a entrada necessária. A coleta ampliada corresponde ao trabalho de coleta do grupo, incluindo a [Issue #64](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/64).

1. CSV da amostra final, com pelo menos 300 `full_name` únicos e aprovados por coleta real. Cada linha exige `origem_coleta=github_api`, `stars >= 1000`, `total_releases_janela >= 5` e `total_runs_janela >= 50`. Os runs devem satisfazer o filtro do protocolo (Actions/default branch/push, sucesso ou falha). Outras colunas podem ser preservadas. Uma origem `referencia_simulada` é rejeitada.
2. `data/coleta/releases.json`: objeto que mapeia cada `full_name` aprovado para a lista de releases originais da API REST `/repos/{owner}/{repo}/releases`, com paginação concluída. Campos exigidos nas releases estáveis da janela: `id` inteiro positivo, `tag_name`, `published_at` ISO 8601 com fuso, `html_url` direto do GitHub, `draft` e `prerelease` booleanos. Preserve `body` e `name` para consulta das notas. Releases fora da janela, drafts e pré-releases não são sorteadas. A quantidade válida deve corresponder ao CSV; nenhum repositório insuficiente é substituído silenciosamente depois do sorteio.
3. `data/coleta/proveniencia.json`, **emitido pela coleta real**, com os seguintes campos:

| Campo | Valor ou regra |
|---|---|
| `schema_version` | `1` |
| `origem` | `github_api` |
| `modo_referencia` | `false` booleano |
| `fonte_candidatos` | `github_search_api` |
| `coletado_em` | Momento verdadeiro da coleta, ISO 8601 com fuso |
| `janela.inicio` / `janela.fim` | Mesmos instantes de `window.start_date` / `window.end_date` de `config.yaml` |
| `criterios.min_stars` | Inteiro >= 1000 |
| `criterios.min_releases` | Inteiro >= 5 |
| `criterios.min_workflow_runs` | Inteiro >= 50 |
| `repositorios_sha256` | SHA-256 dos bytes do CSV final aprovado |
| `releases_sha256` | SHA-256 dos bytes de `releases.json` |

Não acrescente esses campos aos dados antigos apenas para passar a validação. O manifesto registra a origem declarada e verifica a integridade dos arquivos; hashes, isoladamente, não provam que uma requisição à API ocorreu. A auditabilidade empírica depende da preservação dos registros e respostas reais da coleta.

## Sorteio e artefatos

Execute os comandos a partir de `Laboratorio03_MineracaoDeMetricasDORA`, em ambiente Python com `pip install -r requirements.txt`:

```powershell
python gerar_amostra_rotulagem.py --config config.yaml --repos data/output/repositorios_aprovados.csv --releases data/coleta/releases.json --proveniencia data/coleta/proveniencia.json --saida data/amostra_ouro
```

O script ordena a população por `full_name` e aplica `pandas.DataFrame.sample(n=60, random_state=42)`, sem reposição. Em cada repositório, ordena todas as releases estáveis válidas por instante UTC de publicação e ID, e aplica separadamente `sample(n=5, random_state=42)`. A mesma semente é reiniciada para cada sorteio. A entrada reordenada gera a mesma seleção. Não há seleção por rótulo, heurística ou conveniência.

São gerados, em um diretório novo:

- `amostra_comum.csv`: 60 repositórios × 5 releases, IDs reais, datas, tags, links de release/notas e commits; todos os julgamentos começam vazios.
- `evidencias_releases.json`: corpo original e metadados das releases selecionadas, sem rótulos ou saída de heurística.
- `selecao.json`: semente, algoritmo, janela, versões Python/pandas, tamanho da população, seleção completa por IDs/tags e hashes de entradas e saídas. Preserve os arquivos de entrada e as versões registradas para repetir o sorteio.

`previous_tag` é a tag da release estável imediatamente anterior **na população da janela**, mesmo que não tenha sido sorteada. O link de commits usa `compare/{previous_tag}...{tag}`. Na primeira release válida, não há predecessor nessa janela: `previous_tag` fica vazio e o link aponta para `commits/{tag}`. Nesse caso, o avaliador deve consultar a história anterior para determinar o intervalo; o link não comprova sozinho quais commits pertencem à release. As tags nos links são codificadas para URL.

O script recusa um diretório de seleção já existente. As planilhas e relatórios também usam criação exclusiva para preservar decisões e saídas anteriores.

## Preparação e preenchimento de Áulus

```powershell
python rotulagem.py gerar --amostra data/amostra_ouro/amostra_comum.csv --saida rotulos_aulus.csv
python rotulagem.py validar --amostra data/amostra_ouro/amostra_comum.csv --rotulos rotulos_aulus.csv --rascunho
```

Leia as release notes e os commits sem consultar os julgamentos de Maria/Vinícius ou a heurística. Mantenha os oito campos de referência intactos. Preencha `tipo_projeto`, `entrega_real`, `corretiva`, `justificativa` e `evidencia` (links/referências consultadas). Não basta inferir uma correção apenas pela numeração da tag.

| Dimensão | Categorias permitidas | Unidade |
|---|---|---|
| `tipo_projeto` | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` | Uma decisão por repositório, repetida nas cinco linhas |
| `entrega_real` | `sim`, `não`, `incerto` | Uma decisão por repositório, repetida nas cinco linhas |
| `corretiva` | `sim`, `não` | Uma decisão para cada release |

Após preencher todas as linhas, valide sem `--rascunho`:

```powershell
python rotulagem.py validar --amostra data/amostra_ouro/amostra_comum.csv --rotulos rotulos_aulus.csv
```

O modo rascunho valida a estrutura e os valores já preenchidos, mas não declara a avaliação concluída. A validação completa exige os julgamentos, as justificativas/evidências, exatamente as mesmas unidades da referência e consistência das duas decisões por repositório.

## Divergências, reunião e cálculo final

Maria e Vinícius precisam entregar arquivos independentes completos sobre a **mesma referência**. Use uma nova cópia para Vinícius, como `rotulos_vinicius_independente.csv`, preservando os arquivos antigos. A preparação aceita três caminhos distintos; não converte o arquivo antigo nem trata preenchimento automático como avaliação humana.

```powershell
python -m metricas.concordancia preparar --amostra data/amostra_ouro/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria.csv --vinicius rotulos_vinicius_independente.csv --divergencias data/amostra_ouro/divergencias.csv --consenso data/amostra_ouro/consenso.csv
```

Depois das três avaliações completas, o comando gera divergências com votos e evidências e um formulário de **420 decisões**: 60 de tipo de projeto, 60 de entrega real e 300 de release corretiva. `release_id` fica vazio nas decisões por repositório. Todos os campos de decisão começam vazios, inclusive em unidades unânimes.

Na reunião, o grupo deve discutir as evidências, registrar a decisão confirmada (`rotulo_consenso`), a justificativa, a evidência, os responsáveis, a data e o protocolo usado. Após discussão, pode adotar a maioria simples; um empate 1–1–1 requer resolução explícita do grupo e preenchimento de `desempate`. Casos não resolvidos permanecem vazios e impedem o resultado final. Use `responsaveis=aulus;maria;vinicius` e `data_reuniao` no formato `YYYY-MM-DD`. Nenhuma reunião ou decisão é presumida pelo programa.

```powershell
python -m metricas.concordancia calcular --amostra data/amostra_ouro/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria.csv --vinicius rotulos_vinicius_independente.csv --consenso data/amostra_ouro/consenso.csv --saida data/amostra_ouro/concordancia.json
```

A emissão do relatório final exige os três arquivos completos e as 420 decisões documentadas. Os três kappas são calculados sobre **os votos independentes anteriores ao consenso**, usando `aggregate_raters` e `fleiss_kappa(method="fleiss")` do [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html). O JSON informa `n`, categorias, categorias observadas, kappa e hashes dos arquivos usados. Quando só há uma categoria observada, o kappa é indefinido (`null`), pois a concordância esperada ao acaso é 1; não é reportado como concordância perfeita. O fluxo não calcula F1 nem apresenta os benchmarks antigos como validação humana. Uma avaliação futura da heurística deve usar o consenso humano validado e conteúdo real das releases/commits.

## Testes

As fixtures são dados artificiais explicitamente restritos aos testes. Não geram a amostra-ouro real nem representam julgamentos dos integrantes.

```powershell
python -m pytest tests/test_amostra_ouro.py tests/test_rotulagem.py tests/test_concordancia.py
python -m pytest --cov=metricas --cov-report=term-missing --cov-fail-under=80
```

Se o ambiente restringir o diretório temporário ou `.pytest_cache`, crie um diretório local e use:

```powershell
New-Item -ItemType Directory -Path .cache -Force | Out-Null
python -m pytest -p no:cacheprovider --basetemp .cache/testes-local --cov=metricas --cov-report=term-missing --cov-fail-under=80
```

Isso executa a suíte completa do laboratório. A pasta `.cache` é ignorada pelo Git; use um novo subdiretório em cada execução se houver restrições de permissões.
