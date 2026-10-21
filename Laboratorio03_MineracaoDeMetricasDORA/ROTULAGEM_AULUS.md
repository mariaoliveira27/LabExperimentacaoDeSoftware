# Rotulagem independente de Áulus — Issues #62 e #75

A referência de **60 repositórios × 5 releases** foi preparada com o CSV e o
arquivo de releases da main, conforme a escolha de Áulus. Os arquivos
`rotulos_aulus.csv`, `rotulos_maria_independente.csv` e
`rotulos_vinicius_independente.csv` contêm as mesmas 300 unidades, com os cinco
campos de julgamento vazios. Os arquivos antigos dos colegas foram preservados.

O manifesto identifica `tipo_fonte=csv_main_adotado`. A auditoria encontrou
seeds e registros gerados nessa fonte. Os identificadores, datas, notas e links
fornecidos foram preservados, mas não certificam releases originais da API,
300 aprovações reais ou cobertura histórica integral. A preparação permite
trabalhar com a entrada escolhida; a validação empírica continua pendente.
Sem fonte real verificável para uma unidade, preserve o julgamento pendente.

## Arquivos e reprodução

- [Referência comum](data/amostra_ouro_csv_main/amostra_comum.csv): 300 unidades, sem julgamentos.
- [Manifesto](data/amostra_ouro_csv_main/selecao.json): semente, janela, origem, hashes e seleção.
- [Registros de releases fornecidos](data/amostra_ouro_csv_main/evidencias_releases.json): conteúdo associado aos identificadores sorteados.
- `data/amostra_ouro_csv_main/fontes_entrada/`: cópias das entradas preservadas para reprodução.
- [Formulário de Áulus](rotulos_aulus.csv): arquivo a preencher pessoalmente.
- [Estado da concordância](data/concordancia_aulus/estado.json): 0/3 avaliações completas.
- [Formulário de consenso](data/concordancia_aulus/consenso_formulario.csv): 420 decisões vazias.

Execute na pasta `Laboratorio03_MineracaoDeMetricasDORA`. Para reproduzir a
preparação, escolha saídas novas; os comandos não sobrescrevem arquivos:

```powershell
.\.venv\Scripts\python.exe -X utf8 amostra_csv_main.py --csv data/coleta_final/repositorios_aprovados.csv --releases data/coleta_final/releases.json --proveniencia data/coleta_final/proveniencia.json --config config.yaml --saida data/amostra_ouro_csv_main_reproducao --rotulos rotulos_aulus_reproducao.csv
```

A população é ordenada por `full_name`; as releases estáveis fornecidas são
ordenadas por publicação UTC e ID. Cada sorteio usa `random_state=42`, sem
reposição: 60 repositórios e cinco releases por repositório. A janela permanece
de `2023-10-01T00:00:00Z` a `2024-09-30T23:59:59Z`. A validação reproduz o
sorteio e confere hashes e conteúdo das evidências. Os indicadores de auditoria
de origem, critérios e cobertura permanecem falsos no manifesto.

O fluxo `executar_amostra_ouro.py` continua exigindo o bundle real e seus
snapshots. Ele não foi flexibilizado para aceitar a fonte fornecida.

## Preencher pessoalmente

1. Trabalhe somente no seu CSV e nas fontes do projeto. Não consulte rótulos
   dos colegas, previsões da heurística ou consenso antes de concluir e preservar
   sua avaliação independente.
2. Mantenha `full_name`, `release_id`, `published_at`, `tag_name`, `html_url`,
   `release_notes_url`, `commits_url` e `previous_tag` sem alterações. Salve em
   UTF-8, com vírgula como delimitador e aspas nos textos que contêm vírgulas.
3. Para cada repositório, consulte README, descrição e documentação. Em
   `tipo_projeto`, escolha `biblioteca/framework`, `aplicação/serviço`,
   `ferramenta CLI` ou `outro`.
4. Em `entrega_real`, escolha `sim`, `não` ou `incerto` após avaliar se as
   releases representam entregas funcionais aos usuários, incluindo consumidores
   de bibliotecas. Repita `tipo_projeto` e `entrega_real` nas cinco linhas:
   cada dimensão tem uma decisão por repositório.
5. Para cada release, confira notas e commits. Marque `corretiva=sim` quando o
   objetivo predominante for corrigir defeitos, regressões ou vulnerabilidades;
   caso contrário, marque `não`. Um incremento de patch sozinho não determina
   a classificação. Se `previous_tag` estiver vazio, investigue também o
   histórico anterior da tag para delimitar as mudanças.
6. Preencha `justificativa` e `evidencia` em cada linha com o motivo e links,
   SHAs ou trechos identificáveis. Os registros fornecidos podem apontar para
   releases inexistentes ou diferentes das reais. Sem evidência suficiente,
   mantenha a unidade pendente e registre o problema; não invente um julgamento.

Valide o rascunho durante o preenchimento:

```powershell
.\.venv\Scripts\python.exe -X utf8 rotulagem.py validar --amostra data/amostra_ouro_csv_main/amostra_comum.csv --rotulos rotulos_aulus.csv --rascunho
```

Depois de concluir pessoalmente todos os campos humanos, valide sem
`--rascunho` e preserve o arquivo anterior à reunião:

```powershell
.\.venv\Scripts\python.exe -X utf8 rotulagem.py validar --amostra data/amostra_ouro_csv_main/amostra_comum.csv --rotulos rotulos_aulus.csv
Get-FileHash rotulos_aulus.csv -Algorithm SHA256
```

Maria e Vinícius preencherão, separadamente, suas novas cópias
`rotulos_maria_independente.csv` e `rotulos_vinicius_independente.csv`.
O validador comprova estrutura, categorias e correspondência com a referência.
A independência humana precisa ser respeitada e declarada pelos avaliadores.
A Issue #62 permanece aberta.

## Concordância pré-consenso

A preparação atual gerou `data/concordancia_aulus/estado.json`, com **0/3
avaliações completas**, e `consenso_formulario.csv`, com 420 decisões vazias.
Não há kappa ou relatório de divergências enquanto faltarem os três arquivos
humanos completos. Para verificar novamente, use um novo diretório:

```powershell
.\.venv\Scripts\python.exe -X utf8 preparar_concordancia_aulus.py --amostra data/amostra_ouro_csv_main/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria_independente.csv --vinicius rotulos_vinicius_independente.csv --saida data/concordancia_aulus_verificacao
```

Após as três avaliações completas, execute com uma saída ainda inexistente:

```powershell
.\.venv\Scripts\python.exe -X utf8 preparar_concordancia_aulus.py --amostra data/amostra_ouro_csv_main/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria_independente.csv --vinicius rotulos_vinicius_independente.csv --saida data/concordancia_aulus_preconsenso
```

Somente com três arquivos completos o comando produz `kappas_pre_consenso.json`,
`divergencias.csv` e `consenso.csv`. Fleiss usa os votos independentes
**anteriores à reunião**: 60 unidades de `tipo_projeto`, 60 de `entrega_real`
e 300 de `corretiva`. Distribuições com kappa indefinido têm o motivo registrado.
O resultado mantém os limites de origem da referência; calcular concordância
não comprova a origem das releases. O mesmo arquivo físico não pode representar
dois avaliadores.

## Reunião e decisões

O `consenso.csv` mantém vazias as 420 decisões, inclusive unanimidades. Na
reunião, confiram fontes e divergências e preencham `rotulo_consenso`,
`justificativa`, `evidencia`, `responsaveis` (`aulus;maria;vinicius`),
`data_reuniao` (`YYYY-MM-DD`) e `protocolo`. Apliquem maioria simples após a
discussão; empates 1-1-1 exigem decisão conjunta registrada em `desempate`.
Casos não resolvidos permanecem pendentes. Preservem os arquivos independentes.

Depois de o grupo registrar as 420 decisões, valide a consolidação:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m metricas.concordancia calcular --amostra data/amostra_ouro_csv_main/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria_independente.csv --vinicius rotulos_vinicius_independente.csv --consenso data/concordancia_aulus_preconsenso/consenso.csv --saida data/concordancia_aulus_preconsenso/concordancia_final.json
```

Nenhum rótulo, kappa, decisão, responsável ou data de reunião foi preenchido
automaticamente. A Issue #75 depende das três avaliações humanas e do consenso.
