# Lab05 — Medição externa de serviços digitais do gov.br

Laboratório de Experimentação de Software (PUC Minas). Medimos as **páginas públicas de entrada**
de dez serviços digitais do governo com o [Lighthouse](https://github.com/GoogleChrome/lighthouse),
do jeito que um visitante comum as carregaria. **Não** é um teste de carga: as execuções são
sequenciais, uma URL por vez, com pelo menos 10 s entre elas.

Perguntas de pesquisa (detalhes, hipóteses e plano de análise em [docs/proposta.md](docs/proposta.md)):

- **RQ1** — O performance score e o LCP variam entre os serviços escolhidos? Quais são os piores?
- **RQ2** — Os serviços com pior desempenho também têm pior acessibilidade (accessibility score do Lighthouse)?
- **RQ3** — Quanto o desempenho no mobile é pior que no desktop?

## Regras de ética (garantidas pelos scripts)

| Regra | Como é garantida |
|---|---|
| Ler o `robots.txt` antes de medir | `scripts/robots-check.mjs` grava `docs/robots-check.md` e `data/robots-check.json`. O `run-lighthouse.mjs` recusa qualquer URL que não esteja marcada como liberada ali, e recusa rodar se a verificação tiver mais de 7 dias. |
| Sequencial, sem paralelismo | Um Chrome e uma execução do Lighthouse por vez. |
| Pelo menos 10 s entre execuções | `--pause` vale 10 s por padrão e valores abaixo de 10 s são recusados. Um `Crawl-delay` maior no `robots.txt` é respeitado. |
| Só páginas públicas | `data/urls.json` lista só páginas públicas de entrada. Sem login, sem envio de formulário, sem dados pessoais. |

## Requisitos

- Node.js **22.19 ou mais novo** (exigido pelo Lighthouse 13). Testado com Node 24.18.0.
- Google Chrome instalado (o `chrome-launcher` o encontra sozinho; defina `CHROME_PATH` para usar outro).
- Dependências com versão fixa: `lighthouse@13.6.0`, `chrome-launcher@1.2.3`, `robots-parser@3.0.1`.

## Instalação

```bash
cd Laboratorio05_MedicaoGovBr
npm ci
```

## Rodar o piloto

```bash
npm run robots          # 1. verifica o robots.txt de cada URL de data/urls.json
npm run pilot           # 2. 3 serviços do piloto x 2 form factors x 3 execuções = 18 execuções (~10 min)
npm run extract:pilot   # 3. gera data/processed/pilot*.csv a partir dos JSONs brutos
npm test                # testes unitários do plano de execução e da extração de métricas
```

`npm run pilot` é `node scripts/run-lighthouse.mjs --phase pilot --runs 3`. Os serviços do piloto
são os que têm `"pilot": true` em `data/urls.json`.

## Coleta completa (Sprint 2)

10 serviços × 2 form factors × 10 execuções = **200 execuções**, divididas em 2 blocos de horário
de 5 réplicas por célula (100 execuções por bloco). O plano (seed, blocos, ordem) é criado na
primeira sessão e guardado em `data/raw/full/plan.json`; as sessões seguintes reutilizam o mesmo plano.

```bash
npm run robots                                   # a verificação vale por 7 dias
node scripts/run-lighthouse.mjs --phase full --dry-run          # o que falta e a estimativa de tempo
npm run full:morning      # = --phase full --block 1 --session-label morning   (~40 min)
npm run full:afternoon    # = --phase full --block 2 --session-label afternoon (~40 min)
```

Estimativa: cerca de 24 s por execução (mediana de 13–14 s do Lighthouse mais 10 s de pausa),
cerca de 40 min por bloco e 1 h 20 min no total.

**Retomar.** A sessão pode ser interrompida (Ctrl+C) e retomada com o mesmo comando. Execuções com
JSON válido são puladas; um JSON inválido (bloqueio, `runtimeError`, métrica nula) é movido para
`data/raw/full/invalid/` e a execução é refeita. Para fazer tudo o que falta em qualquer bloco,
de uma vez, com o rótulo do horário atual:

```bash
node scripts/run-lighthouse.mjs --phase full --session-label afternoon   # ou morning / night
```

Uma trava (`data/raw/.lighthouse.lock`) impede duas sessões ao mesmo tempo. Cada execução que
falha (erro do Lighthouse, bloqueio, métrica nula, erro do script ou timeout) vira uma linha em
`data/failed-runs.csv` com o motivo, e é repetida uma vez no fim da fila da mesma sessão, exceto bloqueio.

### Opções do script de medição

```bash
node scripts/run-lighthouse.mjs --phase <nome> [--runs <N>] [--blocks <B>] [--block <k>] [--session-label morning|afternoon|night]
                                [--services id1,id2] [--seed <inteiro>] [--pause <s>] [--gzip|--no-gzip] [--force] [--dry-run]
```

| Opção | Padrão | Significado |
|---|---|---|
| `--phase` | `pilot` | Pasta de saída `data/raw/<fase>/`. Na fase `pilot`, só os serviços com `"pilot": true`; em qualquer outra fase, todos. |
| `--runs` | `10` na fase `full`, `3` nas outras | Execuções por serviço **e** por form factor. |
| `--blocks` | `2` na fase `full`, `1` nas outras | Blocos de horário em que as réplicas são divididas. |
| `--block` | todos | Roda só as execuções que faltam do bloco k. |
| `--session-label` | — (obrigatório na fase `full`) | Horário da sessão, gravado na sessão e em cada execução; a análise usa esse rótulo como bloco. |
| `--services` | — | Subconjunto de ids de `data/urls.json`, separados por vírgula. |
| `--seed` | a de `plan.json`, ou sorteada | Seed da ordem de execução. Sempre gravada, para a ordem poder ser reproduzida. |
| `--pause` | `10` | Segundos entre execuções (mínimo 10). |
| `--gzip` | ligado fora da fase `pilot` | Grava o bruto como `.json.gz` (gzip nível 9). |
| `--force` | desligada | Refaz também as execuções que já têm JSON válido. |
| `--dry-run` | desligada | Mostra o que falta, a estimativa de tempo e sai. |

## Validação, análise e gráficos

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r analysis/requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python analysis/run_all.py      # extração + validação + análise + gráficos, um comando
```

`analysis/run_all.py` roda, em ordem:

1. `node scripts/extract-metrics.mjs --phase full` → `data/processed/full*.csv`
2. `node scripts/validate-data.mjs --phase full` → `docs/data-validation.md` e `data/processed/full_outliers.csv`
3. `analysis/analyze.py` → tabelas em `analysis/output/todas/` e `analysis/output/sem-outliers/`, e
   gráficos em `analysis/figures/`

O bootstrap usa seed fixa (`--seed 20261125`), então rodar de novo dá os mesmos números. A leitura
dos resultados está em [`analysis/results.md`](analysis/results.md). Para refazer só os gráficos:
`.venv/Scripts/python analysis/analyze.py` (as tabelas são regravadas juntas).

A validação confere: todas as 200 execuções do plano presentes, nenhuma métrica vazia ou NaN,
scores entre 0 e 100, tempos > 0 (TBT e CLS ≥ 0), nenhuma linha repetida, pausa ≥ 10 s entre
tentativas (com milissegundos), sessões sem sobreposição, e `fetchTime` dentro da janela de cada
tentativa. Outliers (cerca de Tukey, 1,5 × IQR, por serviço × form factor × métrica) são
marcados, não apagados; a análise sai com todas as execuções e sem os valores marcados.

Uma execução é marcada como `blocked` quando o documento principal não volta com HTTP 200 (por exemplo, um CAPTCHA anti-bot servido com HTTP 202) ou quando o texto do elemento LCP é uma mensagem de desafio anti-bot (pega desafios servidos com HTTP 200). As execuções restantes daquele serviço na sessão são puladas e registradas como `skipped-blocked`.

Como funciona uma sessão:

1. A lista de execuções (serviço × form factor × réplica) é embaralhada com um gerador
   pseudoaleatório com seed (mulberry32 + Fisher–Yates). `run` é o número da réplica dentro do
   serviço e form factor. No piloto é a ordem cronológica na sessão. Na fase `full`, o número vem
   do plano: o bloco 1 tem as réplicas 1–5 e o bloco 2 as réplicas 6–10, e uma réplica refeita
   mantém o número.
2. Cada execução abre um **Chrome headless novo com perfil temporário** (cache do navegador
   vazio, ou seja, primeira visita), roda o Lighthouse só com as categorias `performance` e
   `accessibility`, grava o resultado bruto e fecha o Chrome.
3. O mobile usa o preset padrão do Lighthouse; o desktop usa o `desktop-config` do Lighthouse. Os
   dois usam throttling simulado (`throttlingMethod: simulate`).
4. Se três execuções seguidas falharem por erro do script (e não da página), a sessão para.
5. Toda execução passa por uma verificação de validade: se o documento principal não for HTTP 200,
   ou se o elemento LCP for uma mensagem de desafio, a execução mediu uma página de bloqueio ou de
   desafio, e não o serviço (ver "Situação do piloto" abaixo).

## Onde ficam os dados

```
data/
├── urls.json                 # serviços, URLs, flag de piloto e lista de candidatas trocadas
├── robots-check.json         # veredito do robots.txt por URL (lido pelo script de medição como trava)
├── robots/<host>.txt         # cópia de cada robots.txt como foi baixado
├── run-metadata.json         # uma entrada por sessão (ver abaixo)
├── failed-runs.csv           # uma linha por tentativa que falhou ou foi pulada, com o motivo (Sprint 2)
├── raw/pilot/<servico>_<formFactor>_<n>.json      # bruto do piloto (LHR)
├── raw/full/<servico>_<formFactor>_<n>.json.gz    # bruto da coleta completa, gzip nível 9
├── raw/full/plan.json        # seed, blocos e ordem planejada da fase full
├── raw/full/invalid/         # brutos inválidos tirados de cena antes de refazer a execução
└── processed/
    ├── <fase>.csv            # uma linha por execução válida
    ├── <fase>_failures.csv   # runtimeError, página de bloqueio ou desafio, ou valores ausentes
    ├── <fase>_summary.csv    # medianas por serviço e form factor
    ├── <fase>_lcp_elements.csv  # elemento que o Lighthouse usou como LCP em cada execução válida
    ├── <fase>_flags.csv      # execuções válidas para revisar (ver abaixo); continuam em <fase>.csv
    ├── <fase>_executions.csv # cada tentativa: sessão, rótulo de horário, bloco, horários UTC com ms, status
    └── full_outliers.csv     # valores fora da cerca de Tukey (gerado pela validação)
docs/
├── proposta.md               # proposta do estudo (com changelog da Sprint 2)
├── robots-check.md           # evidência do robots.txt (gerada)
├── audit-sprint1.md          # auditoria da Sprint 1
├── url-changes.md            # lista final de URLs e trocas
├── data-validation.md        # validação dos dados (gerada)
├── ameacas-validade.md       # ameaças à validade
└── sprint2-entrega.md        # o que foi entregue na Sprint 2 (para o card do GitHub Projects)
analysis/
├── run_all.py                # extração + validação + análise, um comando
├── analyze.py                # análise estatística (RQ1-RQ3) e gráficos
├── lab_stats.py              # tamanhos de efeito, Holm e bootstrap
├── test_lab_stats.py         # testes de lab_stats
├── requirements.txt          # dependências Python com versão fixa
├── results.md                # resultados e leitura
├── output/                   # tabelas CSV (todas/ e sem-outliers/) e analysis-metadata.json
└── figures/                  # gráficos PNG
```

O bruto da coleta completa fica comprimido em `data/raw/full/*.json.gz` (cerca de 120 KB por
execução, em vez de ~600 KB). Para ler um arquivo: `node -e "console.log(require('zlib').gunzipSync(require('fs').readFileSync('<arquivo>')).toString())"`
ou qualquer `gunzip`. O extrator e o validador leem `.json` e `.json.gz`.

Marcações de revisão em `<fase>_flags.csv`:

| Marcação | Significado |
|---|---|
| `SLOW_HOST_CPU` | `benchmarkIndex` ≤ 1000, o limiar de CPU lenta do próprio Lighthouse. O Lighthouse só avisa sobre isso na CLI, nunca pela API Node, então o extrator aplica o limiar. |
| `BENCHMARK_LOW_OUTLIER` | `benchmarkIndex` abaixo da cerca inferior de Tukey (Q1 − 1,5 × IQR) das execuções válidas da fase. |
| `DOM_SIZE_DROP` | Menos da metade dos elementos DOM da maior execução do mesmo serviço e form factor. |
| `FINAL_HOST_CHANGED` | O host da URL final é diferente do host pedido. |
| `CHALLENGE_RESOURCES` | A página carregou recursos de hosts conhecidos de CAPTCHA. |

O `data/run-metadata.json` guarda, por sessão: fase, seed, ordem planejada, versões do Lighthouse
e do chrome-launcher, versão e flags do Chrome, as configurações do Lighthouse usadas em cada form
factor (throttling, emulação de tela, user agent, tempos limite), sistema operacional, CPU, RAM,
versão do Node, fuso horário, o plano de energia ativo e o adaptador de rede da rota padrão (tipo,
velocidade do link, físico ou virtual; não se lê IP, MAC, nome da rede nem provedor), e, para
cada execução, horário de início e fim, duração, status, URL final, `runtimeError`, `runWarnings`
e o `benchmarkIndex` que o Lighthouse mediu na máquina.

### Colunas do CSV (`data/processed/<fase>.csv`)

Os nomes das colunas são os definidos no enunciado.

| Coluna | Unidade | Origem no LHR |
|---|---|---|
| `service` | id | nome do arquivo |
| `url` | — | `requestedUrl` |
| `formFactor` | `mobile` / `desktop` | `configSettings.formFactor` |
| `run` | inteiro | nome do arquivo |
| `performanceScore` | 0–100 | `categories.performance.score` × 100 |
| `accessibilityScore` | 0–100 | `categories.accessibility.score` × 100 |
| `LCP` | ms | `audits["largest-contentful-paint"].numericValue` |
| `FCP` | ms | `audits["first-contentful-paint"].numericValue` |
| `TBT` | ms | `audits["total-blocking-time"].numericValue` |
| `CLS` | sem unidade | `audits["cumulative-layout-shift"].numericValue` |
| `SpeedIndex` | ms | `audits["speed-index"].numericValue` |
| `timestamp` | ISO 8601, UTC | `fetchTime` |

## Análise estatística

Python 3.12 com os pacotes de versão fixa em `analysis/requirements.txt` (instalação na seção
"Validação, análise e gráficos"). Testes: `.venv/Scripts/python -m unittest discover -s analysis`.

O bloco de cada execução é o `--session-label` da sessão que a gerou (sem rótulo, como no piloto,
o bloco é a fase). As tabelas vão para `analysis/output/<variante>/` (ou `--out`): estatística
descritiva com Shapiro–Wilk, medianas e efeito por bloco, réplica 1 contra as seguintes, elementos
LCP, Kruskal–Wallis + ε² + Dunn/Holm (RQ1), Spearman com IC por bootstrap nas medianas por serviço e
em todas as execuções + τ-b de Kendall (RQ2), Wilcoxon pareado + delta de Cliff + rank-biserial
pareada + teste do sinal, entre serviços e dentro de cada serviço (RQ3), e `analysis-metadata.json`
com as opções e as versões. Serviços que não estão mais em `data/urls.json` ficam de fora. Os nomes
das tabelas e das colunas ficam em inglês porque são identificadores lidos por código.

A análise principal exclui as execuções marcadas com `SLOW_HOST_CPU`. As análises de sensibilidade
são novas execuções do script: `--exclude-flags all` tira todas as execuções marcadas, e
`--exclude-services govbr,svr-bcb` tira serviços (por exemplo, aqueles cujo elemento LCP é um
banner de cookies).

Com os dados do piloto o script roda, mas com 3 execuções por célula os testes não são resultados.
Os resultados da coleta completa estão em [`analysis/results.md`](analysis/results.md).

## Trocar um serviço

1. Edite `data/urls.json`: troque a entrada e acrescente a antiga em `replaced`, com a data e o motivo.
2. Rode `npm run robots` de novo. O script de medição não começa enquanto a nova URL não for verificada e liberada.

## Situação da coleta completa (25/11/2026)

| Item | Valor |
|---|---|
| Sessões | `morning` 11:38–12:14 (100 tentativas) e `afternoon` 15:01–15:39 (105 tentativas), Chrome 158.0.8127.37, Lighthouse 13.6.0 |
| Execuções | **200 de 200 válidas** (10 por serviço × form factor, 5 em cada bloco; o Consumidor.gov.br tem 6 à tarde e 4 de manhã) |
| Falhas | 5 tentativas inválidas, todas do Consumidor.gov.br (`MISSING_VALUES`: `NO_FCP`, a página não pintou nada); registradas em `data/failed-runs.csv` e refeitas |
| Bloqueios | Nenhum |
| Validação | 0 erros, 0 avisos; menor pausa entre tentativas 10,001 s ([`docs/data-validation.md`](docs/data-validation.md)) |
| Marcações | 2 `BENCHMARK_LOW_OUTLIER` (mantidas); 105 valores fora da cerca de Tukey em 60 execuções (marcados, não removidos) |
| Bruto | `data/raw/full/`: 200 `.json.gz` + `plan.json`, 23 MB; 5 inválidos em `data/raw/full/invalid/` |

Resumo dos resultados (detalhes em [`analysis/results.md`](analysis/results.md)):

- **RQ1**: o desempenho varia muito entre os serviços (Kruskal–Wallis com p < 0,001 e ε² de 0,85 a
  0,98). O pior no LCP é o Meu SUS Digital (33,9 s no mobile); o pior no performance score mobile é
  o Valores a Receber (mediana 1).
- **RQ2**: inconclusivo; ρ = 0,41 (mobile) e 0,48 (desktop), com p Holm = 0,33 e IC 95% incluindo o zero.
- **RQ3**: o LCP mobile é maior em todos os 10 serviços: mediana de 13,7 s contra 3,6 s (4,8×),
  p Holm = 0,004.

## Situação do piloto (17/11/2026)

24 execuções em duas sessões (seeds 41872753 e 484856555), nenhum erro de script, menor intervalo
entre execuções de 10,00 s. Serviços do piloto: `govbr`, `meuinss`, `svr-bcb`.

- O Portal da Transparência estava na primeira sessão, mas serviu um CAPTCHA do AWS WAF (HTTP 202)
  em 4 de 6 execuções. Foi trocado pelo Valores a Receber (`svr-bcb`); os arquivos brutos dele
  ficaram em `data/raw/pilot/` como evidência e o extrator os lista em `pilot_failures.csv`.
- As medianas do piloto e o que ele mostrou estão em [docs/proposta.md](docs/proposta.md), seção 9.
- Os textos de `data/run-metadata.json` gravados durante o piloto (por exemplo `blockReason`)
  ficaram em inglês, porque são o registro do que o script escreveu naquele momento.

## Observações da preparação

- Alguns hosts respondem de forma diferente a user agents que não são de navegador (ex.: o
  `portaldatransparencia.gov.br` devolveu HTTP 405 para o `robots.txt` a um user agent próprio e
  200 a um user agent de navegador). Por isso a verificação do robots.txt repete as respostas que
  não são 2xx com o user agent que o Lighthouse envia.
- O `cav.receita.fazenda.gov.br` envia uma cadeia TLS incompleta. Navegadores buscam o certificado
  intermediário que falta via AIA; o Node não. A verificação do robots.txt faz o mesmo que o
  navegador e só aceita o intermediário se ele for verificado contra uma raiz do repositório de
  confiança do Node.
