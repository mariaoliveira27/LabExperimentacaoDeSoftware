# Amostra para rotulagem independente — Lab03S02

Os identificadores foram conferidos no GitHub: [sorteio #61](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/61), [concordância #70](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/70), [rotulagem #62](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/62) e [metodologia #63](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/63). As tarefas 01–03 da divisão não são os números das Issues.

## Estado da entrega

A implementação da coleta real, do preparo integrado, do sorteio, da preparação/validação de Áulus e da concordância está disponível. A tentativa anterior de sorteio foi interrompida com código 2: o arquivo legado `data/output/repositorios_aprovados.csv` tem somente **100 repositórios**, sem proveniência registrada. O piloto anterior da nova coleta em `data/coleta_final/estado.json` registra **100 candidatos consultados e zero aprovados comprovados**, sem extrapolar esse resultado para toda a população.

O ZIP histórico foi baixado integralmente, com **952.289.386 bytes**, MD5 `df0e00311cdfa611e784c373d20bacd5` conferido contra a publicação e SHA-256 registrado `285e9ad9ed0ecee07ebbf2cf3e0ccbc3f8075b5bcba2fbb48183886b7f9506c6`. A recuperação terminou e seu manifesto, `data/historico_2024/proveniencia_historico.json`, registra:

| Registro da recuperação | Quantidade comprovada |
|---|---:|
| Repositórios com metadados preservados | 19.849 |
| Repositórios com pelo menos 1.000 estrelas no snapshot da fonte | 32 |
| Repositórios identificados sem arquivo de runs | 2 (histórico desconhecido, não zero runs) |
| Repositórios com pelo menos 50 runs válidos observados nos filtros | 15 |
| Runs originais exportados desses repositórios | 6.708 |

O intervalo efetivamente observado é de 01/01/2024 a 30/09/2024 UTC, dentro da janela original do estudo. Os 15 repositórios ainda precisam de verificação dos metadados atuais e de pelo menos cinco releases reais; **não são 15 aprovações finais nem comprovam uma população de 300**. A qualificação e a ampliação da população continuam em curso. Não existem atualmente a referência comum verificável de 300 releases ou três avaliações humanas completas vinculadas a ela. Portanto, `rotulos_aulus.csv` será criado somente quando existir essa referência: a Issue #62 permanece **pendente de julgamento humano de Áulus**. Não foi criado um CSV com releases inventadas para aparentar a conclusão da tarefa.

O gerador anterior tinha projetos, releases, mensagens resumidas e classificações fixas no código. Foi substituído. Os dois arquivos antigos chamados `rotulos_vinicius.csv` foram preservados; eles e os relatórios antigos de benchmarking não comprovam uma avaliação humana independente nem devem servir de referência para este fluxo.

## Contrato de entrada da coleta final

O novo coletor [`coleta_amostra_real.py`](coleta_amostra_real.py) busca candidatos reais no GitHub e coleta metadados e releases pela API própria. Os runs podem vir da API ou de uma exportação pública original verificada; o CSV e as qualificações preservam a origem em `origem_metricas_estabilidade` e a cobertura em `escopo_contagem_runs`. A coleta concluída deve fornecer estes três artefatos, preservando também seus registros de requisições/paginação e respostas originais. `seed_data.py` e `--reference-mode` não preparam essa entrada. A coleta ampliada corresponde ao trabalho de coleta do grupo, incluindo a [Issue #64](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/64).

1. `data/coleta_final/repositorios_aprovados.csv`, com pelo menos 300 `full_name` únicos e aprovados por coleta real. Cada linha exige `origem_coleta=github_api`, `stars >= 1000`, `total_releases_janela >= 5` e `total_runs_janela >= 50`. Os runs devem satisfazer o filtro do protocolo (Actions/default branch/push, sucesso ou falha). Outras colunas podem ser preservadas. Uma origem `referencia_simulada` é rejeitada.
2. `data/coleta_final/releases.json`: objeto que mapeia cada `full_name` aprovado para a lista de releases originais da API REST `/repos/{owner}/{repo}/releases`, com paginação concluída. Campos exigidos nas releases estáveis da janela: `id` inteiro positivo, `tag_name`, `published_at` ISO 8601 com fuso, `html_url` direto do GitHub, `draft` e `prerelease` booleanos. Preserve `body` e `name` para consulta das notas. Releases fora da janela, drafts e pré-releases não são sorteadas. A quantidade válida deve corresponder ao CSV; nenhum repositório insuficiente é substituído silenciosamente depois do sorteio.
3. `data/coleta_final/proveniencia.json`, **emitido pela coleta real concluída**, com os seguintes campos:

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

## Coleta, retomada e disponibilidade histórica

A busca de candidatos consulta páginas atuais do GitHub, sem reutilizar seu cache SQLite: uma página antiga não pode ser combinada com outra recém-obtida. Mudanças de contagem ou duplicatas entre páginas/fatias descartam a rodada inteira, com no máximo três rodadas desde a raiz. As rodadas rejeitadas são registradas no relatório da busca concluída e nos logs; HTTP e campos obrigatórios inválidos continuam sendo erros. Se a instabilidade persistir, a execução termina com código 2 e preserva as qualificações anteriores. Repita o mesmo comando para retomar; não é necessário apagar o cache de metadados, releases ou runs, nem usar `--reavaliar` para esse erro.

A lista da API pode mudar entre rodadas, pois estrelas, visibilidade e índice de busca são mutáveis. A reprodução do sorteio depende dos mesmos arquivos finais aprovados, releases e manifesto, congelados e identificados por hashes e versões. Uma nova busca pode produzir outros candidatos. `--limite-candidatos 5000` é um orçamento de busca, não uma declaração de 5.000 aprovados ou de universo exaurido.

Quando a listagem de releases retorna HTTP 422 com `Only the first 10000 results are available.`, o projeto fica com qualificação inconclusiva (`evidencia_releases_incompleta`). O prefixo obtido não é tratado como listagem completa nem como comprovação de menos de cinco releases. O coletor registra a ocorrência em `pendencias_tecnicas.csv`, no snapshot e em `estado.json` (`n_pendencias_tecnicas`), e continua os demais candidatos. As páginas completas do cache permanecem disponíveis. Outras falhas HTTP e de schema continuam interrompendo a execução.

Essas pendências também aparecem em `descartes.csv` e no total de não aprovados daquela etapa do funil: representam exclusão operacional por evidência incompleta, sem reprovar o critério substantivo de cinco releases. A retomada comum preserva a pendência já registrada. Uma nova tentativa do candidato exige `--reavaliar`, que preserva as qualificações anteriores e repete os filtros; essa flag, sozinha, não remove o limite da API e deve ser usada depois de resolver a obtenção dos dados.

O caso observado em 15/10/2026 foi `vercel/ai`, com rejeição da página 101 apesar de o cabeçalho indicar mais páginas. A [API de releases](https://docs.github.com/en/rest/releases/releases#list-releases) oferece paginação, mas não um filtro de datas ou garantia de ordenação por `published_at`. Por isso, encontrar uma release antiga não permite encerrar a listagem e declarar toda a janela recuperada. Pendências exigem outra obtenção completa e verificável da origem; não serão aprovadas pelo prefixo. A limitação de cobertura deve ser considerada como possível viés de seleção em projetos com muitas releases.

Na auditoria da execução de 15/10/2026, os 1.231 candidatos concluídos se dividiram em 167 com evidência de Actions insuficiente, 541 com menos de cinco releases elegíveis e 523 com releases suficientes, mas zero runs disponíveis na API da janela. Isso explica as zero aprovações até aquele checkpoint; não prova ausência histórica de CI. Nenhum dos 15 projetos com runs no arquivo histórico havia sido processado. Só três deles estavam entre os 5.000 candidatos dessa rodada, ainda aguardando: `GoogleContainerTools/distroless`, `PHPMailer/PHPMailer` e `h2o/h2o`. Portanto, ampliar essa busca não garante resolver a falta de registros para 300 aprovações reais; fontes históricas adicionais continuam necessárias para comprovar os demais.

Uma verificação auxiliar pela API real, concluída às 19:01 UTC de 15/10/2026, examinou esses três projetos sem alterar o checkpoint principal. Foram encontradas, respectivamente, **0, 1 e 0 releases estáveis elegíveis** na janela original, com paginação completa. Embora tenham 238, 93 e 52 runs históricos válidos, nenhum dos três satisfaz o mínimo de cinco releases. As respostas, os hashes e os snapshots locais estão preservados em `.cache/auditoria_3_historicos_20261015/rodada_20261015T190104_612266Z/`, com resumo em `resumo.json` e cache SQLite separado. Essa auditoria de cobertura não constitui amostra-ouro, julgamento humano ou resultado de desempenho. A fonte recuperada, aplicada à lista atual de 5.000 candidatos, não fornece aprovados; repetir a coleta com a mesma fonte não resolve, por si só, a população mínima. Será necessário obter fontes históricas adicionais verificáveis ou uma revisão da janela autorizada pelo professor antes de alterar o protocolo.

Execute na pasta `Laboratorio03_MineracaoDeMetricasDORA`, após `pip install -r requirements.txt`. A autenticação usa `GITHUB_TOKEN`; alternativamente, `--usar-gh-auth` utiliza a autenticação existente do GitHub CLI, sem gravar o token nos artefatos:

Os candidatos vêm da API de busca, com particionamento para tratar o limite por consulta. O coletor preserva o progresso e as respostas da API. Uma interrupção ou amostra insuficiente mantém os artefatos parciais (`estado.json`, descartes, funil e cache) para auditoria e retomada; esses registros não são uma população final de 300 aprovados. Execute novamente o mesmo comando para continuar a coleta. Não complete as linhas com dados de demonstração.

A janela definida em `config.yaml` permanece de 01/10/2023 a 30/09/2024 UTC. A partir de 01/10/2026, a retenção do GitHub também abrange metadados de workflow runs, com limite de 90 dias nos repositórios públicos; aumentar a retenção não restaura registros removidos. [GitHub Changelog](https://github.blog/changelog/2026-10-01-actions-retention-now-covers-checks-runs-and-statuses/), [documentação de retenção](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization).

Isso pode limitar uma coleta retrospectiva de 2023–2024. Consultas piloto sem runs disponíveis não comprovam ausência histórica de Actions nos projetos nem autorizam extrapolar para todos os candidatos. Quando os dados da janela não estiverem mais disponíveis, será necessário localizar exportações históricas reais com origem verificável. A janela não será alterada automaticamente e a ausência de dados não será substituída por contagens inventadas. A geração da amostra e das planilhas continuará bloqueada até satisfazer os filtros com dados reais.

Para comprovar o filtro de inclusão, pelo menos 50 runs distintos efetivamente observados na janela, disparados por `push` no default branch e concluídos com sucesso ou falha, constituem um limite inferior verificável. O arquivo histórico pode cobrir apenas parte da janela e ainda comprovar esse mínimo; isso **não comprova o total anual** nem permite apresentar CFR e recuperação anuais como resultados completos. Não se contam jobs ou linhas de logs como runs. Os identificadores, o evento, o branch, a conclusão e as datas precisam estar preservados.

Uma consulta de runs com `total_count=0` ou menos de 50 registros será registrada como `evidencia_runs_historicos_insuficiente`. Se houver registros suficientes, mas menos de 50 com conclusões válidas, o motivo será `evidencia_runs_validos_insuficiente`. A ausência de workflows atuais sem evidência histórica utilizável será registrada como `evidencia_actions_historicos_insuficiente`. Esses motivos descrevem falta de comprovação; não provam que o projeto não usava Actions ou que teve menos de 50 execuções históricas. Fontes de pesquisa com arquivos históricos foram identificadas, mas sua existência não equivale a um conjunto de 300 aprovados validado. A recuperação precisa preservar o arquivo original, verificar seu checksum publicado e conferir os registros antes de utilizá-los no funil.

Uma das fontes identificadas é [`cicd_env_results.zip`, Zenodo 20414642](https://zenodo.org/records/20414642), com MD5 publicado `df0e00311cdfa611e784c373d20bacd5`. Baixe ou retome o original com:

```powershell
python baixar_historico.py --saida .cache/arquivos_historicos/2024/cicd_env_results.zip
```

O downloader só disponibiliza o ZIP final após conferir tamanho e MD5. Em caso de interrupção, retorna código 2, preserva os bytes em `.zip.part` e registra o progresso em `.zip.download.json`; repetir o mesmo comando retoma de onde parou. O registro de download diferencia checksum integral pendente de `download_verificado`. SHA-256 também é registrado após a verificação completa. Um download parcial não é evidência pronta. Depois de completar e verificar o ZIP, execute o adaptador:

```powershell
python recuperar_historico.py --arquivo .cache/arquivos_historicos/2024/cicd_env_results.zip --config config.yaml --saida data/historico_2024
```

Esse comando cria um diretório novo com `metadata_repositorios.json`, `runs_historicos.json` e `proveniencia_historico.json`. Os runs são preservados com seus dados originais e filtrados por data, evento, branch, conclusão e mínimo observado; a procedência declara a cobertura como limite inferior, sem afirmar resultados anuais completos. Esses artefatos são entradas históricas para verificar os candidatos e **não substituem** a amostra final aprovada com todos os filtros, as releases reais e a procedência exigida pelo sorteio. Como `data/historico_2024/` já foi produzido nesta execução, preserve-o; use outro diretório para uma recuperação nova, pois o adaptador recusa sobrescritas.

Os metadados e o branch do arquivo são snapshots da fonte; o coletor verifica a identidade GitHub e os metadados atuais, preservando os nomes e IDs originais e selecionando runs do default branch usado no protocolo. As estrelas do snapshot e o total bruto de runs do dataset, isoladamente, não aprovam um repositório.

Depois de validar o conjunto histórico, execute:

```powershell
python coleta_amostra_real.py --config config.yaml --saida data/coleta_final --alvo 300 --limite-candidatos 5000 --usar-gh-auth --historico-zenodo data/historico_2024 --reavaliar
```

`--historico-zenodo` vincula o arquivo original verificado, seus hashes e os runs exportados à coleta. Para retomar o piloto anterior com essa nova fonte, `--reavaliar` preserva as qualificações anteriores e repete a verificação; ele não converte descartes em aprovados automaticamente. A etapa ainda exige metadados atuais, pelo menos cinco releases reais e 50 runs válidos observados na janela por repositório. Se não houver 300 aprovados, a saída continua parcial e não pode alimentar o sorteio.

## Coleta com workers e múltiplas credenciais

`--workers` controla a concorrência dentro de **um único processo**, com valores de 1 a 8 e padrão 1. Mantenha somente uma execução usando cada diretório `--saida`: antes de iniciar o comando paralelo, encerre e aguarde o fechamento da execução anterior. Um bloqueio do sistema operacional impede outro processo sobre a mesma saída. Cada worker usa sua própria sessão HTTP, o cache é compartilhado e um único escritor persiste estado, snapshots e relatórios, na ordem dos candidatos. Para continuar com quatro workers e autenticação pelo GitHub CLI, compartilhando uma única cota de conta:

```powershell
python coleta_amostra_real.py --config config.yaml --saida data/coleta_final --alvo 300 --limite-candidatos 5000 --usar-gh-auth --historico-zenodo data/historico_2024 --workers 4
```

Sem `--token-env`, permanece o comportamento de `GITHUB_TOKEN` ou `--usar-gh-auth`, inclusive quando uma única credencial atende a vários workers. Para fornecer múltiplas credenciais de contas distintas, prepare variáveis de ambiente no processo e passe seus **nomes** usando `--token-env` repetível. A quantidade de variáveis deve ser menor ou igual ao número de workers. A opção é incompatível com `--usar-gh-auth`:

```powershell
python coleta_amostra_real.py --config config.yaml --saida data/coleta_final --alvo 300 --limite-candidatos 5000 --historico-zenodo data/historico_2024 --workers 4 --token-env GITHUB_TOKEN_A --token-env GITHUB_TOKEN_B
```

O comando não recebe valores literais de token. As credenciais múltiplas são verificadas na API `/user`, sem cache. Valores repetidos ou credenciais associadas ao mesmo identificador de conta são rejeitados; use somente um token por conta. Os segredos permanecem em memória, sem gravação em argumentos, logs, snapshots ou arquivos de configuração da coleta. Os exemplos pressupõem que as variáveis já estejam configuradas no ambiente; seus valores não devem ser incluídos no comando mostrado ou no repositório.

A retomada com outro número de workers mantém os critérios e as qualificações preservadas. `--reavaliar` é necessário quando se deseja repetir os filtros de candidatos anteriores, como ao incorporar uma nova fonte histórica; ele não é necessário apenas para mudar a concorrência. O cache e os registros existentes devem permanecer no diretório da coleta.

O processo limita o início das requisições a até 10 GET/s e compartilha as pausas por limites secundários. A cota primária é acompanhada por conta e por tipo de recurso da API. Ao receber `Ctrl+C`, a parada é cooperativa: o programa aguarda as requisições em voo, com timeout HTTP de 30 segundos, encerra os workers e preserva o checkpoint. Requisições já iniciadas podem acrescentar respostas ao cache após o alvo ser atingido; isso não incorpora candidatos extras à população final, e os hashes finais são calculados após encerrar os workers.

O número de workers aumenta a concorrência das requisições, sujeito às cotas e aos limites da API. A janela de 01/10/2023 a 30/09/2024 UTC, a necessidade de dados reais e as pendências de cobertura histórica permanecem. Os três projetos auditados continuam sem cinco releases elegíveis; executar em paralelo não altera esse resultado nem comprova a população mínima de 300 aprovados. A amostra e a rotulagem seguem bloqueadas enquanto faltarem as entradas finais verificadas.

## Sorteio e artefatos

Execute a partir de `Laboratorio03_MineracaoDeMetricasDORA`, em ambiente Python com `pip install -r requirements.txt`, **somente depois de a coleta indicar `status=completa` e preservar pelo menos 300 aprovados nos arquivos finais**:

```powershell
python executar_amostra_ouro.py --config config.yaml --coleta data/coleta_final --saida data/amostra_ouro --rotulos rotulos_aulus.csv
```

Esse comando valida o conjunto de coleta concluído, gera a referência comum e prepara `rotulos_aulus.csv` com julgamentos vazios, verificando-o como rascunho. Ele termina indicando o dado necessário quando faltarem os 300 aprovados ou a procedência, sem produzir uma amostra substituta. Arquivos existentes são preservados. Para executar apenas o sorteio, sem preparar a cópia de Áulus:

```powershell
python gerar_amostra_rotulagem.py --config config.yaml --repos data/coleta_final/repositorios_aprovados.csv --releases data/coleta_final/releases.json --proveniencia data/coleta_final/proveniencia.json --saida data/amostra_ouro
```

O script ordena a população por `full_name` e aplica `pandas.DataFrame.sample(n=60, random_state=42)`, sem reposição. Em cada repositório, ordena todas as releases estáveis válidas por instante UTC de publicação e ID, e aplica separadamente `sample(n=5, random_state=42)`. A mesma semente é reiniciada para cada sorteio. A entrada reordenada gera a mesma seleção. Não há seleção por rótulo, heurística ou conveniência.

São gerados, em um diretório novo:

- `amostra_comum.csv`: 60 repositórios × 5 releases, IDs reais, datas, tags, links de release/notas e commits; todos os julgamentos começam vazios.
- `evidencias_releases.json`: corpo original e metadados das releases selecionadas, sem rótulos ou saída de heurística.
- `selecao.json`: semente, algoritmo, janela, versões Python/pandas, tamanho da população, seleção completa por IDs/tags e hashes de entradas e saídas. Preserve os arquivos de entrada e as versões registradas para repetir o sorteio.

`previous_tag` é a tag da release estável imediatamente anterior **na população da janela**, mesmo que não tenha sido sorteada. O link de commits usa `compare/{previous_tag}...{tag}`. Na primeira release válida, não há predecessor nessa janela: `previous_tag` fica vazio e o link aponta para `commits/{tag}`. Nesse caso, o avaliador deve consultar a história anterior para determinar o intervalo; o link não comprova sozinho quais commits pertencem à release. As tags nos links são codificadas para URL.

O script recusa um diretório de seleção já existente. As planilhas e relatórios também usam criação exclusiva para preservar decisões e saídas anteriores.

## Preparação e preenchimento de Áulus

O preparo integrado já cria `rotulos_aulus.csv`. Se foi executado apenas o sorteio ou uma interrupção ocorreu depois da seleção e antes da criação da cópia, execute o primeiro comando abaixo **somente se o arquivo de Áulus ainda não existir**. O gerador recusa sobrescritas:

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
