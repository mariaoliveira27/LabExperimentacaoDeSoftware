# Sprint 01 — workflows, cache e estabilidade

Esta entrega usa o `GitHubClient` compartilhado por todos os coletores, sem PyGithub.
As funções de métricas são puras e não consultam a rede. Cache/retomada corresponde à
Issue #51, CFR(a) à #52 e recuperação à #53. A associação da coleta de workflows a uma
Issue depende da identificação do cartão correspondente, sem reutilizar um número arbitrário.

## Executar

Execute os comandos dentro de `Laboratorio03_MineracaoDeMetricasDORA`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python pipeline.py --config config.yaml
```

Configure `GITHUB_TOKEN` no ambiente antes da coleta autenticada. O token fica no cabeçalho
HTTP e não é persistido no cache. Repositórios públicos também podem ser consultados sem
token, sujeitos à cota da API. A validação TLS fica ativada por padrão. As chamadas são
sequenciais; não há trabalhadores concorrentes disputando a cota.

Em `config.yaml`, `window.start_date` e `window.end_date` definem limites inclusivos com
fuso horário. Use UTC e precisão de segundos, por exemplo:

```yaml
window:
  start_date: "2023-10-01T00:00:00Z"
  end_date: "2024-09-30T23:59:59Z"
  weeks: 52.14
```

`weeks` continua sendo a configuração preexistente da frequência de releases; mantenha-a
coerente com a janela se alterar sua duração. Para uma execução demonstrativa sem rede:

```powershell
python pipeline.py --config config.yaml --reference-mode
```

Esse modo precisa ser solicitado explicitamente. Suas linhas contêm
`origem_metricas_estabilidade=referencia_simulada`; na execução normal, o valor é
`workflow_runs`. Não misture as duas origens em uma análise.

## Coletar somente workflows e usar as interfaces

O exemplo abaixo pode ser executado em um script Python dentro da pasta do laboratório.
Substitua `OWNER/REPO` pelo repositório escolhido:

```python
from dataclasses import asdict
from api_client import GitHubClient
from coletor_runs import ColetorRuns
from pipeline import carregar_config
from metricas.calculo_metricas import (
    parse_datetime, calcular_cfr_ci, calcular_tempo_recuperacao,
)

cfg = carregar_config("config.yaml")
client = GitHubClient(cache_db_path=cfg["storage"]["cache_db"])
owner, repo = "OWNER/REPO".split("/")
status, metadata, _ = client.request(f"/repos/{owner}/{repo}")
if status != 200 or not metadata.get("default_branch"):
    raise RuntimeError("Não foi possível consultar o default_branch")
runs = ColetorRuns(client).coletar_runs_janela(
    owner, repo, metadata["default_branch"],
    parse_datetime(cfg["window"]["start_date"]),
    parse_datetime(cfg["window"]["end_date"]),
)
print(asdict(calcular_cfr_ci(runs)))
print(asdict(calcular_tempo_recuperacao(runs, window_end=parse_datetime(cfg["window"]["end_date"]))))
```

Outros coletores devem receber a mesma instância de `GitHubClient` e usar
`request(endpoint, params)`, que mantém o retorno `(status, json, headers)`, ou
`paginate(endpoint, params)` para listas paginadas. Validação específica que falhe deve
chamar `invalidate_cache(endpoint, params)` e sinalizar erro; não converter erro em lista
vazia nem persistir um resultado agregado parcial como completo.

## Completude, cache e retomada

A janela é dividida inicialmente por meses de calendário. Um intervalo com
`total_count >= 1000` é dividido em dois, repetidamente, até cada consulta ficar abaixo do
limite documentado pela [API de workflow runs](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository).
As páginas são verificadas e os IDs deduplicados. O resultado preserva `id`, `workflow_id`,
`name`, `head_branch`, `event`, `conclusion`, `created_at`, `run_started_at` e `updated_at`.
Somente o default branch, `event=push` e `created_at` dentro da janela entram na coleta.
Conclusões ignoradas permanecem no resultado para permitir sua contagem nas métricas.

```text
data/
  cache/
    github_cache.db    # respostas e estados por URL + parâmetros
  output/
    repositorios_aprovados.csv
    funil_selecao.csv
    funil_selecao.md
    descartes.csv
```

O caminho é configurado por `storage.cache_db`, relativo ao diretório de execução.
Cada página e cada intervalo possuem sua própria chave, incluindo `created`, `page`,
`branch` e `event`. A tabela SQLite `api_cache` distingue `pending` de `complete`.
Somente HTTP 200 com JSON objeto/lista validado pode ser `complete`; JSON inválido e
`incomplete_results=true` não são reutilizados. A gravação ocorre em transação antes
de esperar por rate limit. Falhas de gravação são propagadas.

Após Ctrl+C, erro temporário ou esgotamento de tentativas, repita **o mesmo comando com a
mesma configuração e cache**. O coletor reconstrói os intervalos deterministicamente,
reutiliza as respostas completas e consulta apenas páginas pendentes. Estados pendentes
não equivalem a zero runs. Os resultados anteriores são preservados no cache; uma coleta
incompleta interrompe a execução antes de exportar um novo CSV completo.

Se o `total_count` mudar entre páginas ou os IDs retornados forem inconsistentes, o intervalo
afetado é invalidado e será reconsultado na retomada. Os demais intervalos válidos permanecem
no cache; uma contagem antiga não prende a retomada em um erro permanente.

HTTP 429 é tratado pelo status, mesmo sem mensagem de rate limit. `Retry-After` aceita
segundos ou data HTTP; `X-RateLimit-Remaining` e `X-RateLimit-Reset` determinam a espera até
o reset. Falhas de conexão e 5xx usam backoff exponencial com número limitado de tentativas,
configurado em `api.max_retries` e `api.backoff_base_seconds`.

Os caches antigos são migrados adicionando `state`; suas entradas ficam pendentes para
revalidação, pois a versão anterior aceitava conteúdo inválido. Não há expiração automática:
um cache representa uma coleta reproduzível. Para atualizar conclusões de runs ainda em
andamento, permissões ou metadados, use uma coleta nova.

Para iniciar uma coleta independente, mude `storage.cache_db`, por exemplo para
`data/cache/coleta-nova/github_cache.db`, e escolha outro `storage.output_dir` e caminhos
de saída. Para limpar somente o cache padrão, encerre a coleta e execute:

```powershell
Remove-Item -LiteralPath .\data\cache\github_cache.db
```

## Interpretar as métricas

`calcular_cfr_ci(runs)` retorna `ResultadoCFR` com `cfr`, `falhas`, `sucessos` e `ignorados`.
`success` conta como sucesso; `failure`, `timed_out` e `startup_failure` contam como falha.
Toda outra conclusão é ignorada. A fórmula é `falhas / (falhas + sucessos)`.
Sem runs válidos, `cfr=None`; com sucessos e nenhuma falha, `cfr=0.0`.

`calcular_tempo_recuperacao(runs)` retorna `ResultadoRecuperacao` com `mediana_horas`,
`tempos_horas`, `recuperados`, `censurados` e `proporcao_censurada`. Os runs são agrupados
por workflow e ordenados por `run_started_at`, com ID numérico como desempate.
Somente uma falha após um sucesso observado abre um episódio. Falhas consecutivas não
abrem episódios adicionais; conclusões ignoradas não abrem nem encerram episódios.
Falhas anteriores ao primeiro sucesso observado não entram nas contagens de episódios.

O sucesso seguinte encerra o episódio: `updated_at do sucesso - run_started_at da primeira
falha`, em horas. Um episódio aberto no fim da janela é censurado: ele entra na proporção
`censurados / (recuperados + censurados)`, mas não recebe uma duração inventada nem entra
na mediana. Sem episódios recuperados, a mediana é `None`; sem episódio algum, a proporção
também é `None`. IDs e datas necessários às medições são validados; dados inconsistentes
geram erro, sem substituir timestamps ausentes por `created_at`.

O argumento opcional `window_end` fixa o corte de observação; o pipeline sempre o informa.
Sucessos que só terminam após esse corte não encerram episódios, mesmo se o run tiver sido
criado dentro da janela. Sem o argumento, a função considera todos os runs fornecidos.

Os retornos antigos em tuplas foram substituídos por objetos com atributos; os consumidores
do repositório foram atualizados. Use `dataclasses.asdict` para obter um dicionário.
No CSV, valores indisponíveis são campos vazios. `total_runs_janela` continua contando
apenas sucessos + falhas para o critério de inclusão; `runs_ignorados` é informado à parte.
As contagens e a proporção de censura também são exportadas.

## Testar sem rede

```powershell
python -m pytest -q
python -m pytest --cov=metricas --cov-report=term-missing --cov-fail-under=80
python -m pytest tests/test_pipeline.py -k exporta_metricas_reais -v
```

`tests/conftest.py` bloqueia chamadas HTTP reais. Os testes usam mocks de transporte e
SQLite temporário, sem token real. A fixture `tests/fixtures/workflow_runs.json` reproduz
dois sucessos e uma falha, com recuperação de 10:00 a 11:12: CFR = `1/3` e recuperação =
`1,2 h`. O teste de integração verifica esses valores no CSV, variando estrelas e
contribuidores, e repete a execução com a rede indisponível para verificar a retomada.

## Limitações e responsabilidades preservadas

Validação realizada em 07/10/2026, Python 3.12: baseline de 19 testes passando antes das
alterações; suíte final de **124 testes passando**, com **97,22% de cobertura em `metricas`**.
O exemplo de três runs retornou CFR `0.3333333333333333` e recuperação `1.2` hora. A inspeção
de 34 arquivos versionados/novos não encontrou padrões de tokens nem o token do ambiente;
o banco existente permaneceu vazio e nenhum workflow de CI foi alterado.

- Se um único segundo atingir 1.000 resultados, a divisão temporal não consegue garantir
  completude. O coletor sinaliza erro; não publica silenciosamente apenas os primeiros mil.
- Paginação não é um snapshot transacional do GitHub. Prefira janelas encerradas; alterações
  nos runs durante a coleta podem causar inconsistências que exigem nova coleta/cache.
- O pipeline continua usando a lista de candidatos existente. A busca de candidatos, lead
  time, CFR(b), rework e classificação preexistentes não foram reimplementados. Lead time,
  CFR(b) e rework ainda têm valores simulados, e a classificação herda essas limitações.
- A CI fica como pendência de **Marias**: mover o workflow para `.github/workflows` na raiz
  do repositório e corrigir os caminhos `Laboraorio03...`. Nenhum YAML de CI foi alterado.
