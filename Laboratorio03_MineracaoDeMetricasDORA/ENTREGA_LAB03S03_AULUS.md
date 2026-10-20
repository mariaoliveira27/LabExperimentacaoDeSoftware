# Entrega de Áulus — Lab03S03

Execução em **20/10/2026**, horário de São Paulo. Branch local:
`feat/lab03-s03-aulus-evidencias`, partindo de
`d9ccb5fe2036378a1f3c6edaf430b11c773a5bca`.

**A sprint permanece incompleta.** Foram implementadas, testadas e executadas
as rotinas de responsabilidade de Áulus, mas não há população final de 300
aprovados, referência comum real ou três avaliações humanas independentes.
Nenhum resultado oficial DORA, kappa humano ou consenso foi inventado.

## Estado inicial e atribuições

A inspeção inicial cobriu Git, Issues remotas, CI, pipeline, cliente e coletores,
métricas, scripts da amostra-ouro, testes e metodologia. A única alteração
preexistente era a remoção de `AMOSTRA_OURO.md`: ela permanece removida e não
foi incluída em nenhum commit desta entrega. A introdução e as hipóteses,
os dois CSVs preexistentes de Vinicius e o dataset legado foram preservados;
seus SHA-256 estão em [execucoes.json](data/execucao_s03/execucoes.json).
Os rótulos dos colegas não foram usados para preencher decisões de Áulus.

As [Issues reais e o CI inicial](data/execucao_s03/github.json) foram consultados
pela API autenticada. A busca por `Lab03S03` retornou zero Issues. Por isso, os
commits usam os números existentes, sem criar ou atribuir cartões fictícios:

| Issue | Responsável e estado remoto consultado | Situação nesta entrega |
|---|---|---|
| #51 — Cache e retomada | Áulus; fechada | Cobertura auditável e correção de bloqueios transitórios de arquivos; testes e retomada real. |
| #61 — Sorteio reproduzível | Áulus; fechada | Auditoria do bundle final e reprodução/verificação da referência implementadas. Sorteio real bloqueado pelos dados. |
| #62 — Rotulagem independente | Grupo; aberta | Fluxo de formulário vazio e instruções prontos. Avaliação pessoal de Áulus e avaliações dos colegas pendentes. |
| #70 — Fleiss e consenso | Áulus; fechada | Avaliação pré-consenso, divergências e formulário de consenso vazio implementados. Cálculo humano real bloqueado. |
| #63 — Metodologia da amostra-ouro | Áulus; fechada | Metodologia atualizada com auditoria, cegamento, desempate e limites de concordância. |
| #59 — Relatório final compartilhado | Grupo; aberta | Scripts RQ01–RQ04, execução e evidências da parte de Áulus registrados; resultados empíricos pendentes. |

Nenhuma nova Issue foi encerrada. O fechamento anterior de uma Issue de script
não comprova que a coleta, a rotulagem ou o experimento foram concluídos.

## Implementação entregue

- `coletor_runs.py`: preserva o coletor existente e acrescenta relatório de
  consultas, filtros, páginas, intervalos completos e falhas. Subdivide consultas
  no teto de 1.000 resultados, inclusive quando esse total é truncado, e reutiliza
  as páginas completas no SQLite. `enumeration_complete` refere-se aos registros
  retornados pela API; `historico_anual_completo` permanece falso.
- `verificar_cobertura_runs.py`: diagnóstico reproduzível de toda a janela, com
  metadados públicos atuais, requisições auditadas e preservação de falhas.
- `coleta_amostra_real.py`: auditoria final compartilhada sem rede nem escrita,
  índice dos primeiros 100 aprovados em ordem de aprovação, e retentativa limitada
  de trocas atômicas sob bloqueios transitórios do Windows. Erros persistentes
  continuam interrompendo a coleta com checkpoints preservados.
- `gerar_amostra_rotulagem.py`, `executar_amostra_ouro.py` e `rotulagem.py`:
  exigem bundle/manifesto verificáveis, reproduzem a seleção 60 × 5 e recusam
  referências já preenchidas. Nenhum julgamento humano é atribuído automaticamente.
- `metricas/concordancia.py`: valida três avaliações das mesmas unidades,
  rejeita avaliadores repetidos e o mesmo arquivo físico, calcula Fleiss antes
  da reunião e prepara divergências e as 420 decisões vazias de consenso.
- `analisar_rqs.py`: audita o dataset final antes de calcular RQ01–RQ04; produz
  medianas, Q1, Q3, IQR, denominadores, ausências e censura identificados. Inclui
  as duas variantes de Lead Time e os proxies de CI e releases do CFR. Reutiliza
  as métricas e a heurística existentes. Compara commits somente com páginas
  originais completas e verificadas. As quatro figuras SVG e as tabelas têm
  identificação das RQs e manifesto com hashes.
- `pipeline.py`: remove Lead Time derivado por fórmula do modo real, registra a
  dependência da #65 e deixa seus valores e classificação ausentes. Métricas
  ausentes também não geram uma classificação geral artificial. A integração
  paginada atribuída a Maria não foi implementada nem declarada concluída.

## Coleta real executada e evidências

Os comandos foram executados na pasta deste laboratório, com o ambiente
`.venv` instalado. Autenticação foi lida pelo `gh`, sem gravar credenciais.
A configuração preserva **01/10/2023 a 30/09/2024 UTC**, estrelas ≥1.000,
cinco releases estáveis e 50 runs válidos de `push` no default branch.

```powershell
.venv/Scripts/python.exe coleta_amostra_real.py --config config.yaml --saida data/coleta_s03 --alvo 300 --limite-candidatos 100 --usar-gh-auth
```

Resultado: código **2**, coleta `insuficiente`. O limite de 100 é de candidatos,
não de aprovados, e está declarado na busca. A busca informou 58.506 candidatos
na consulta raiz, retornou 100 para o piloto e sinalizou a limitação. Ela não
comprova que os demais projetos tenham sido qualificados.

| Etapa | Restantes | Descartados nesta etapa |
|---|---:|---:|
| Candidatos processados | 100 | 0 |
| Evidência atual de GitHub Actions | 91 | 9 |
| Pelo menos cinco releases na janela | 41 | 50 |
| Pelo menos 50 runs válidos comprovados | **0** | 41 |

Os motivos relacionados a runs e Actions indicam **evidência histórica
insuficiente**, sem afirmar ausência histórica de execução. A API não devolveu
evidência que sustentasse aprovações nesses 100 candidatos. O CSV antigo e a
fonte parcial do Zenodo não foram usados para completar o piloto S03.

Evidências versionadas: [estado](data/coleta_s03/estado.json),
[configuração](data/coleta_s03/config_coleta.json), [busca](data/coleta_s03/busca.json),
[funil](data/coleta_s03/funil_selecao.csv), [descartes](data/coleta_s03/descartes.csv),
[requisições](data/coleta_s03/requisicoes.jsonl),
[resumos extraídos das qualificações](data/coleta_s03/evidencias_qualificacoes.json)
e [índice dos primeiros 100 aprovados](data/coleta_s03/primeiros_100_aprovados.json).
Este último informa `n_comprovados=0` e `completo=false`; não contém candidatos
apresentados como aprovações.

Os 100 snapshots originais ficam em `data/coleta_s03/qualificacoes/`, e o SQLite
em `data/coleta_s03/cache/`, fora do Git. Para preservar as respostas extensas
sem adicionar centenas de megabytes ao histórico, foi mantido localmente o ZIP
`.cache/coleta_s03_snapshots_compacto.zip`, com **50.843.205 bytes** e SHA-256
`018b93198c39aa22d8734062287d8055f7f2737349f30760da2856a9a33f369c`.
O [manifesto do arquivo](data/coleta_s03/arquivo_snapshots.json) e o estado
registram os hashes individuais. Em outro checkout, transfira o ZIP/cache ou
refaça a coleta em outro diretório; os resumos não substituem os originais
necessários para auditar ou retomar esses checkpoints. O arquivo local pode ser
extraído com `python -m zipfile -e .cache/coleta_s03_snapshots_compacto.zip data/coleta_s03`
depois de conferir seu hash.

O mesmo comando de coleta foi repetido para verificar a retomada: os 100
snapshots foram revalidados e as oito consultas da busca vieram do cache, sem
repetir a qualificação. O log completo tem **589 respostas HTTP e oito leituras
de cache**, totalizando 597 registros. Não houve aprovação nova na retomada.

```powershell
.venv/Scripts/python.exe verificar_cobertura_runs.py --repositorio microsoft/vscode --saida data/cobertura_s03/microsoft_vscode.json --usar-gh-auth
```

Resultado: código **0**, enumeração mensal concluída em **12 intervalos** e
zero runs retidos. O [JSON original do diagnóstico](data/cobertura_s03/microsoft_vscode.json)
preserva metadados, cada consulta e seu total. Esse projeto foi usado como
diagnóstico, sem aprovação de amostra. A consulta não certifica que o histórico
anual foi preservado e não autoriza DORA anual com valores zero.

## Amostra-ouro, rotulagem e análises executadas

```powershell
.venv/Scripts/python.exe -X utf8 executar_amostra_ouro.py --config config.yaml --coleta data/coleta_s03 --saida data/amostra_ouro --rotulos rotulos_aulus.csv
.venv/Scripts/python.exe -X utf8 analisar_rqs.py --config config.yaml --coleta data/coleta_s03 --saida data/analises_rqs
```

Ambos terminaram com código **2**, informando que faltam
`repositorios_aprovados.csv`, `releases.json` e `proveniencia.json` finais e os
≥300 aprovados. Não criaram `rotulos_aulus.csv`, seleção substituta ou diretório
de resultados oficiais. O bloqueio é de dados, anterior ao preenchimento humano.
Gerar um CSV com 300 identificadores inventados, ou somente um cabeçalho, não
entregaria o formulário real solicitado.

Assim que o grupo fornecer o bundle final, os mesmos comandos produzirão a
referência e o formulário com julgamentos vazios. O roteiro de preenchimento e
de validação posterior está em [ROTULAGEM_AULUS.md](ROTULAGEM_AULUS.md).
Não é possível validar como completo um arquivo humano que ainda não foi
preenchido. Os três kappas e as decisões de consenso continuam sem execução
humana real. O comando `avaliar` ficará disponível antes da reunião; `calcular`
exigirá o consenso documentado, sem converter maioria inicial em decisão.

Em um bundle final válido, RQ01 poderá usar releases reais. Para RQ02 e CFR(b),
o contrato das comparações está em `analisar_rqs.py --help`. Sem essas entradas,
as métricas correspondentes ficam ausentes. CFR(CI) e recuperação anuais
requerem fontes anuais preservadas e auditadas; hashes e marcadores de cobertura
não dispensam a verificação da fonte original pelo grupo. Os resultados e a
discussão das quatro RQs estão explicitamente pendentes no artigo.

## Testes e CI

**286 testes relevantes passaram**; **455 testes da suíte completa passaram**.
Cobertura de `metricas`: **98,42%**, acima do mínimo de 80% do CI.
Os comandos exatos e suas saídas estão em
[execucoes.json](data/execucao_s03/execucoes.json),
[testes relevantes](data/execucao_s03/testes_relevantes.txt) e
[suíte completa](data/execucao_s03/testes_suite_completa.txt).
As versões efetivamente usadas estão em [ambiente.json](data/execucao_s03/ambiente.json).

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest --cov=metricas --cov-report=term-missing --cov-report=json:.cache/coverage_s03_final.json --cov-fail-under=80 -q --tb=short --basetemp .cache/pytest_s03_final -p no:cacheprovider
```

O `--basetemp` local evita o diretório TEMP externo bloqueado pelo ambiente;
`-p no:cacheprovider` evita o cache preexistente sem permissão. Uma falha
transitória de `Path.replace` durante checkpoints motivou a correção e dois
testes específicos; as rodadas finais passaram. Os testes usam fixtures
temporárias, inclusive para verificar tabelas/gráficos, sem publicá-las como
observações empíricas. Também cobrem intervalos cheios e subdivididos, páginas
faltantes, retomada, hash adulterado, categoria/ID inválidos, avaliador repetido,
ausências, discordâncias e episódios censurados.

O [CI da revisão inicial](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/actions/runs/38668538784)
terminou com sucesso no SHA de partida. O workflow na raiz foi conferido e usa
a suíte completa com cobertura mínima de 80%. Os commits desta branch são
locais e **não foram publicados**; não existe ainda um CI remoto desses commits.

## Pendências para declarar a Lab03S03 completa

**Código e dados do grupo:**

1. Qualificar e preservar evidências de ≥300 aprovados reais, incluindo os
   primeiros 100 aprovados. A busca particionada de Maria (#64) já existe e foi
   reutilizada; sua Issue continua aberta. Ampliar candidatos isoladamente não
   recupera runs antigos removidos nem certifica cobertura histórica.
2. Obter uma fonte auditável de runs de `push` no default branch para toda a
   janela exigida. Os registros atuais da API e o arquivo parcial 2024 não
   comprovam essa preservação. Não alterar a janela do estudo silenciosamente.
3. Disponibilizar as comparações completas e paginadas com predecessoras,
   SHAs e `commit.author.date`: #65 (Maria), #55/#54 (Vinícius). Os scripts de
   análise estão prontos para consumi-las, sem assumir a implementação alheia.
4. Executar e revisar as análises reais e integrar as tabelas/figuras ao artigo.
   A integração de CFR(b) e o benchmarking humano (#67/#68, Vinícius) continuam
   atribuídos a ele; esta entrega reaproveita a heurística, sem encerrar essas Issues.
5. Maria e Vinícius precisam avaliar a nova referência comum independentemente.
   Depois dos três arquivos completos, o grupo deverá executar Fleiss e registrar
   a reunião, divergências e todas as decisões de consenso.

**Rotulagem pessoal de Áulus:**

Após existir a referência real 60 × 5, preencher pessoalmente
`rotulos_aulus.csv`, sem consultar os rótulos dos colegas ou previsões; validar
sem `--rascunho` e preservar a versão independente antes da reunião. A Issue
#62 permanece aberta e não será concluída por geração de formulário ou por
testes automatizados.
