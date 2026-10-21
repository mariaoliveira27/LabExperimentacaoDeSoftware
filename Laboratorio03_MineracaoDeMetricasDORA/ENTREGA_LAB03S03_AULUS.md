# Entrega de Áulus — Lab03S03 após integrar a main

## Atualização: referência do CSV adotado e preparação humana

Por instrução de Áulus, a seleção passou a usar o CSV da main e o arquivo de
releases associado, no modo explícito `csv_main_adotado`. Foram preparados
**60 repositórios × 5 releases**, com `random_state=42`, mantendo a janela de
01/10/2023 a 30/09/2024 UTC. A [referência](data/amostra_ouro_csv_main/amostra_comum.csv),
os [registros fornecidos](data/amostra_ouro_csv_main/evidencias_releases.json),
as cópias das entradas e o [manifesto](data/amostra_ouro_csv_main/selecao.json)
permitem reproduzir a seleção e verificar sua integridade.

Essa escolha não resolve a procedência empírica: a origem gerada identificada
na auditoria permanece declarada. O manifesto mantém falsos os indicadores de
releases originais auditadas, critérios de aprovação auditados e cobertura
histórica verificada. `executar_amostra_ouro.py` conserva os requisitos da
coleta real. Nenhum ID ou registro foi fabricado para substituir evidência.

**Entregas preparadas de Áulus (#75/#62/#77):**

- `rotulos_aulus.csv`, `rotulos_maria_independente.csv` e
  `rotulos_vinicius_independente.csv`, cada um com 300 registros e todos os
  julgamentos vazios; arquivos legados dos colegas preservados.
- `data/concordancia_aulus/estado.json`, com **0/3 avaliações completas**, e
  `consenso_formulario.csv`, com **420 decisões vazias**.
- `preparar_concordancia_aulus.py`, que confere a referência e os três arquivos;
  somente com todos completos calcula Fleiss pré-consenso e gera divergências
  e o formulário para a reunião. Sem rótulos, kappa ou decisões automáticas.
- [Guia de rotulagem e reunião](ROTULAGEM_AULUS.md), com comandos de reprodução,
  validação, cálculo pré-consenso e consolidação posterior ao encontro.

**Investigação das releases originais:** o cache tem paginação completa para
222 dos 300 nomes; 164 desses têm pelo menos cinco releases estáveis na janela.
No sorteio original de 60, somente 26 têm o mínimo comprovado no cache, 16 têm
menos de cinco e 18 não têm cobertura no cache. Consultas adicionais à API
confirmaram zero releases elegíveis de `FactoryBoy/factory_boy`, uma de
`yaml/pyyaml` e HTTP 404 para `ecosystem-org/lib-tool-001`. A evidência está em
`data/execucao_amostra_aulus/`, incluindo os relatórios do cache e as respostas
em `confirmacoes_api/`. O ZIP com snapshots dos selecionados permanece local
(`originais_selecionados60.zip`, 19.895.042 bytes, SHA-256
`27869afe60409e3d97065795998d9854014f96f66f54cbd464e005739b7f9d82`), fora do Git.

**Pendências atuais de Áulus:** preencher pessoalmente seus julgamentos (#62),
respeitando a ausência de fonte real verificável; executar o cálculo após as
três avaliações completas; participar da reunião e validar seu registro (#75).
Evidências dos primeiros 100 reais e resultados empíricos continuam dependentes
da coleta auditável (#74/#76/#77). **Pendências do grupo:** comprovar a população
real e a cobertura anual, preservar comparações completas de commits, concluir
as três avaliações independentes e registrar o consenso. As Issues e a sprint
continuam abertas.

Os relatos abaixo documentam as execuções anteriores à adoção dessa referência.
Em particular, a ausência de `rotulos_aulus.csv` neles descreve o estado anterior.
**Testes desta preparação:** 154 testes relevantes e mais 13 testes novos
isolados passaram; a suíte completa passou com **552 testes** e **83,13% de
cobertura de `metricas`**. Os comandos e resultados estão em
[execucoes.json](data/execucao_amostra_aulus/execucoes.json) e no
[log completo](data/execucao_amostra_aulus/suite_completa.txt).
As contagens das execuções históricas abaixo descrevem as rodadas anteriores.

O `fetch` mais recente identificou dois commits adicionais de `origin/main`,
até `4e05345`: `17224e5` (Maria, resumo/conclusão e comentários da heurística)
e `4e05345` (Vinícius, `FloatBarrier`). Ambos alteram somente `artigo/main.tex`.
A publicação desta preparação também deverá incorporar esses commits na branch
de Áulus, preservando os oito commits locais e os formulários preparados.

## Histórico: análise do CSV e integração da main

**Atualização de 21/10/2026 — CSV adotado para análise:** por escolha expressa
de Áulus, `data/output/repositorios_aprovados.csv` da main `a892089` passou a
ser a entrada de uma análise descritiva dos 300 registros fornecidos.
Os resultados e sua interpretação estão em [RESULTADOS_CSV_MAIN.md](RESULTADOS_CSV_MAIN.md)
e os artefatos em `data/analises_csv_main/`. O arquivo original foi preservado.
A origem por seeds/fórmulas identificada na auditoria permanece declarada;
não foram produzidas comparações ou runs inexistentes para converter os
agregados em coleta real. O fluxo `analisar_rqs.py` conserva sua auditoria.
A remoção de `AMOSTRA_OURO.md`, que estava fora dos commits na execução abaixo,
foi posteriormente registrada por Áulus em `ec27244`; esse commit foi preservado.
Validação desta atualização: **82 testes relevantes e 527 testes da suíte
completa passaram**, com **83,08% de cobertura de `metricas`**. Os comandos,
códigos de saída e hashes antes/depois da entrada estão em
[execucoes.json](data/execucao_csv_main/execucoes.json).

Execução em **21/10/2026**, horário de São Paulo, na branch
`feat/lab03-s03-aulus-evidencias`. **A sprint continua incompleta.**
O código novo de Maria e Vinícius foi integrado e testado. O bundle recebido
declara 300 aprovados, mas sua procedência empírica foi rejeitada. A investigação
adicional qualificou **sete repositórios reais** com evidência histórica parcial;
isso não completa os primeiros 100 nem autoriza sorteio ou resultados anuais.

## Git, integração e preservação

O estado inicial tinha oito commits locais sobre `d9ccb5f`, terminando em
`83917e8`, e apenas a remoção não commitada de `AMOSTRA_OURO.md`.
Essa remoção foi protegida em stash antes de `fetch`/merge e restaurada
depois da integração, sem entrar nos commits. O stash de proteção foi mantido. Nenhuma alteração foi integrada na
branch `main` local ou na `origin/main`.

Os oito commits originais permanecem com seus hashes:
`5eb6463`, `b3b44c9`, `ba0aa7b`, `29ea202`, `0dea57b`, `b7988d0`,
`5a0dc78`, `83917e8`. Foi feito merge, sem rebase ou substituição de histórico.

O `fetch origin` confirmou sete commits recebidos até `a892089`:

| Commit | Autor | Conteúdo recebido |
|---|---|---|
| `8f80457` | Maria | Testes de compare, paginação, 404 e Lead Time real. |
| `dd43899` | Maria | Refatoração. |
| `874c8b9` | Maria | Refatoração e consolidação de dados. |
| `155bef1` | Maria | Integração da main. |
| `acbc338` | Maria | Análises e testes de RQ05–RQ06. |
| `dbc7151` | Vinícius | Integração CFR(b), retrabalho e análise RQ07 (#81/#82). |
| `a892089` | Vinícius | Artigo LaTeX e gráficos. |

Conflitos resolvidos: `pipeline.py` e `artigo_metodologia_dora.md`.
O merge `e881d7d` preserva Lead Time real paginado, CFR(b), retrabalho,
coleta/cache de runs, tratamento de dados ausentes e protocolo humano.
Os arquivos de dados e de avaliações recebidos foram preservados para auditoria.

A correção `654704b` impede que erro HTTP ou paginação interrompida devolvam
um prefixo como comparação completa; verifica total, SHAs, datas, mensagens,
Links e tags codificadas. `None` continua distinto de comparação comprovada
sem commits. Foram corrigidos também o import `Sequence` e a exportação de
figuras RQ07 sem depender de uma interface Tk. Os commits usam `refs`, sem
fechar Issues automaticamente.

## Atribuições atuais verificadas no GitHub

As Issues S03 agora existem; a consulta anterior de 20/10 não descreve o estado
atual. As [Issues consultadas](data/execucao_pos_main/github_issues.json)
estão abertas, sem corpo adicional às atribuições dos títulos:

| Issue | Estado desta entrega |
|---|---|
| [#74 — Runs e primeiros 100 aprovados](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/74) | Coleta, cache, retomada e evidências integradas. Sete aprovações parciais reais; faltam 93 para os primeiros 100. Histórico anual não comprovado. |
| [#75 — Sorteio, Fleiss e consenso](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/75) | Fluxo testado; execução real recusou bundle sem origem comprovada. Sem três arquivos humanos completos, nenhum kappa ou consenso foi gerado. |
| [#76 — RQ01–RQ04](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/76) | Integração e regressões corrigidas. Análises reais executadas, mas bloqueadas pela auditoria da entrada; sem resultados oficiais. |
| [#77 — Metodologia e artigo](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/77) | Protocolo e estado de RQ01–RQ04 atualizados em Markdown e LaTeX, incluindo tabelas de pendências, figuras sem validação e limites da discussão. Resultados empíricos aguardam os dados. |

As Issues anteriores #51/#61/#63/#70 preservam o histórico dos scripts.
A avaliação pessoal continua vinculada à #62. Nenhuma Issue foi fechada e a
sprint não foi declarada concluída.

## Auditoria concreta do bundle recebido

Relatório reproduzível: [auditoria_dados.json](data/execucao_pos_main/auditoria_dados.json),
com [script somente de leitura](data/execucao_pos_main/auditar_dados.py).

- `data/coleta_final/repositorios_aprovados.csv` contém 300 nomes, todos iguais
  aos primeiros 300 seeds com `status=aprovado`; as contagens de runs e releases
  também correspondem ao seed em todas as linhas.
- As **5.189 releases** reproduzem os IDs, tags e datas regulares de
  `consolidar_dataset.py`. Esse script calcula LT por `120/n_releases`, CFR por
  `stars % 17` e recuperação por fórmula, mas publica `origem=github_api`.
  Não foi executado para completar dados nesta entrega.
- Os hashes do CSV e das releases conferem, mas só comprovam integridade.
  O manifesto omite `alvo`, `evidencias`, `busca` e `requisicoes_sha256`;
  o estado não contém índice de snapshots e não há primeiros 100 comprovados
  vinculados ao bundle. A data declarada de coleta é 01/10/2024; o log local
  contém requisições de 14–15/10/2026, sem vínculo final auditável.
- Foram lidos os 4.617 snapshots locais anteriores: **zero `aprovado=true`**.
  São 2.037 com menos de cinco releases, 1.515 com runs insuficientes,
  1.057 com evidência Actions insuficiente e oito com releases incompletas.
  Não foram convertidos em aprovações. O piloto pessoal de 100 candidatos em
  `data/coleta_s03` também continua com zero aprovações comprovadas.
- A [consulta real das releases](data/execucao_pos_main/consulta_releases_github.json)
  retornou 404 para o ID gerado `psf/black/releases/1001`. Como controle,
  a release real `24.8.0` tem ID `168486939` e publicação em
  `2024-08-02T17:42:53Z`.

Não há páginas REST de compare ou manifesto de comparações no bundle; o cache
SQLite recebido tem zero entradas `/compare/`. A main resolveu a implementação
de Lead Time e CFR(b), mas não forneceu as comparações originais auditáveis
necessárias para alimentar as análises de Áulus.

## Coleta real adicional, histórico e retomada

A janela permanece **01/10/2023 a 30/09/2024 UTC**, estrelas ≥1.000,
cinco releases estáveis e pelo menos 50 runs válidos de `push` no default branch.

O [histórico foi revalidado](data/execucao_pos_main/verificacao_historico.json)
contra o ZIP original de 952.289.386 bytes, MD5
`df0e00311cdfa611e784c373d20bacd5` e SHA-256
`285e9ad9ed0ecee07ebbf2cf3e0ccbc3f8075b5bcba2fbb48183886b7f9506c6`.
Foram conferidos os hashes dos exports e sua derivação do original:
19.849 metadados e 6.708 runs válidos observados em 15 projetos.

Após essa verificação, a [qualificação pontual dos 15](data/execucao_pos_main/historico_15/qualificacao.json)
reutilizou três descartes por releases recontadas e consultou os outros 12
pela API real. Resultado: **7 aprovados, 8 descartados, nenhum erro**.

| Repositório | Estrelas atuais | Releases estáveis na janela | Runs históricos válidos observados |
|---|---:|---:|---:|
| gajus/slonik | 4.940 | 272 | 168 |
| nuclio/nuclio | 5.766 | 26 | 188 |
| badeball/cypress-cucumber-preprocessor | 1.360 | 17 | 62 |
| JuliaNLSolvers/Optim.jl | 1.206 | 8 | 220 |
| microsoft/msticpy | 2.019 | 7 | 71 |
| open-telemetry/opentelemetry-js | 3.499 | 32 | 1.644 |
| lunarphp/lunar | 3.759 | 12 | 788 |

Os **3.141 runs** desses sete comprovam mínimos observados, com
`escopo_contagem_runs=limite_inferior_arquivo_historico`.
O [índice dos primeiros 100](data/execucao_pos_main/historico_15/primeiros_100_aprovados.json)
informa `n_comprovados=7`, `completo=false`. Não são 300 aprovações nem
resultados anuais. O [manifesto dos originais](data/execucao_pos_main/historico_15/arquivo_originais.json)
preserva snapshots, hashes e instruções de extração; o ZIP histórico original
continua necessário para revalidar a derivação dos runs. O script
[qualificar_historico_15.py](data/execucao_pos_main/qualificar_historico_15.py)
preserva checkpoints e revalida seus hashes na retomada, sem sobrescrever a
coleta recebida ou produzir um bundle final artificial.
A [retomada real](data/execucao_pos_main/historico_15/verificacao_retomada.json)
confirmou os 15 snapshots com hashes idênticos e as mesmas sete aprovações:
o log permaneceu com 59 requisições, **zero consultas novas**. O ZIP dos
originais tem 3.334.254 bytes e SHA-256
`2cd2b9efb840f0fa01aa10748349c8a758384893cf704827c1b91a6dcf3b7a25`,
com CRC e hashes internos conferidos.

Também foram executados dois diagnósticos mensais reais de `psf/black`:

```powershell
.venv/Scripts/python.exe -X utf8 verificar_cobertura_runs.py --repositorio psf/black --saida data/cobertura_pos_main/psf_black.json --usar-gh-auth
.venv/Scripts/python.exe -X utf8 verificar_cobertura_runs.py --repositorio psf/black --saida data/cobertura_pos_main/psf_black_retomada.json --usar-gh-auth
```

Ambos retornaram código 0, 12 intervalos enumerados e zero runs disponíveis.
O [registro de cache](data/execucao_pos_main/verificacao_runs_cache.json)
mostra 14 respostas HTTP (incluindo dois metadados) e 12 leituras de cache na
retomada. A ausência de registros retidos não significa ausência histórica de
Actions ou duração/taxa zero. A evidência anual continua desconhecida.

**Evidência exata ainda faltante:** a fonte histórica cobre janeiro–setembro de
2024 dentro da janela, sem certificar completude anual. Outubro–dezembro de
2023 estão fora de sua cobertura. Faltam registros originais identificados e
preservação integral de todos os meses por repositório, além do restante da
população aprovada e das comparações paginadas. Nenhuma janela ou critério foi
alterado sem autorização do professor.

## Sorteio, avaliação humana e análises executadas

```powershell
.venv/Scripts/python.exe -X utf8 executar_amostra_ouro.py --config config.yaml --coleta data/coleta_final --saida data/amostra_ouro_pos_main --rotulos rotulos_aulus.csv
.venv/Scripts/python.exe -X utf8 analisar_rqs.py --config config.yaml --coleta data/coleta_final --saida data/analises_rqs_pos_main
```

Ambos retornaram **2**, após rejeitar o contrato final. Logs:
[sorteio](data/execucao_pos_main/sorteio.txt) e
[RQ01–RQ04](data/execucao_pos_main/analises_rq01_rq04.txt).
Não foram criados `rotulos_aulus.csv`, referência 60 × 5, tabelas ou figuras
oficiais de análises. A tabela de estado substitui os números sem evidência
nas seções RQ01–RQ04 do artigo. Os PNGs e dados recebidos permanecem preservados,
com sua ausência de validação explicitada.

Os arquivos de Maria e Vinícius foram auditados somente quanto à estrutura,
quantidade e hashes, sem copiar julgamentos para Áulus. Usam schema legado,
sem `full_name`, `release_id` e `evidencia`, e não são três avaliações completas
sobre referência auditada. Não se executou kappa fictício nem se presumiu
reunião. O [guia pessoal](ROTULAGEM_AULUS.md) permanece pronto para uso quando
existir a referência real; todos os julgamentos iniciarão vazios.

## Testes, commits e CI

**345 testes relevantes passaram** (37,19 s); **510 testes da suíte completa
passaram** (68,85 s). Cobertura de `metricas`: **83,08%** (830/999 linhas),
acima dos 80% exigidos pelo CI. A cobertura inclui os novos módulos da main;
não se reutilizou a porcentagem antiga de 98,42% como se fosse a atual.

Comandos, códigos e cobertura por arquivo estão no
[sumário](data/execucao_pos_main/sumario_testes.json), com
[log relevante](data/execucao_pos_main/testes_relevantes.txt),
[log completo](data/execucao_pos_main/testes_suite_completa.txt) e
[ambiente](data/execucao_pos_main/ambiente.json).
A primeira coleta de testes detectou `Sequence` ausente; a rodada seguinte
detectou dependência indevida de Tk. Ambas foram corrigidas e a rodada final
passou, sem reduzir o requisito do CI. O workflow remoto executará a suíte
com `--cov=metricas --cov-fail-under=80` na publicação desta branch.

## Pendências de Áulus e do grupo

**Áulus:** concluir evidências dos primeiros 100 aprovados quando houver
fontes suficientes (#74); executar seleção real 60 × 5 e preparar formulário
vazio (#75); preencher pessoalmente seus julgamentos (#62); após três arquivos
completos, executar Fleiss pré-consenso e preparar divergências; depois da
reunião, validar as decisões registradas pelo grupo. RQ01–RQ04 e seus resultados
no artigo aguardam o bundle auditável (#76/#77).

**Grupo:** ampliar a população real de sete para ≥300 com proveniência (#78),
obter cobertura histórica integral na janela original, preservar as comparações
REST com predecessoras/SHAs/datas, reexecutar os resultados recebidos sobre
dados válidos (#79–#83) e entregar três avaliações humanas independentes.
A reunião de consenso é uma decisão do grupo. Nenhum resultado oficial,
rótulo, kappa ou decisão humana foi inventado para encerrar essas pendências.
