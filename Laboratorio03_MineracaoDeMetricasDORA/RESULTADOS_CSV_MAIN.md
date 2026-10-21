# RQ01–RQ04 — análise do CSV adotado da main

Em 21/10/2026, por escolha expressa de Áulus, foi adotado como entrada analítica
`data/output/repositorios_aprovados.csv`, recebido de `origin/main` no commit
`a8920892d70e7118477888535783c0cbb0a1b3e5`. São **300 repositórios únicos**,
com métricas previamente calculadas. O CSV foi preservado sem alterações.

Esta análise descreve os valores fornecidos nesse arquivo. A
[auditoria anterior](data/execucao_pos_main/auditoria_dados.json) identificou
correspondência com seeds e fórmulas de `consolidar_dataset.py`; essa origem
continua registrada. A adoção do CSV não fornece respostas originais de
commits/runs, não comprova a cobertura anual nem modifica o número de
aprovações independentes demonstradas pela coleta histórica.

## Reprodução e artefatos

Na pasta do laboratório, com as dependências instaladas:

```powershell
.venv/Scripts/python.exe -X utf8 analisar_csv_main.py --csv data/output/repositorios_aprovados.csv --config config.yaml --commit-origem a8920892d70e7118477888535783c0cbb0a1b3e5 --saida data/analises_csv_main
```

Use um diretório novo para outra execução. As saídas preservam a origem dos
valores, hashes e a diferença entre análise de agregados fornecidos e
reprocessamento de eventos originais. O script `analisar_rqs.py` mantém seu
contrato de coleta final auditada.

## Estatísticas descritivas

A unidade principal é o repositório. Cada métrica possui 300 valores e zero
ausências no CSV. Os quartis usam interpolação linear tipo 7; IQR = Q3 − Q1.
São estatísticas das métricas agregadas já publicadas, sem reconstruir
commits, releases ou episódios individuais.

| RQ | Métrica fornecida | Unidade | Mediana | Q1 | Q3 | IQR |
|---|---|---|---:|---:|---:|---:|
| RQ01 | Frequência de releases | releases/semana | 0,269 | 0,153 | 0,460 | 0,307 |
| RQ02 | Lead Time (a), por release | dias | 8,57 | 5,00 | 15,00 | 10,00 |
| RQ02 | Lead Time (b), por commit | dias | 3,86 | 2,25 | 6,75 | 4,50 |
| RQ03 | CFR de CI | proporção | 0,133 | 0,067 | 0,200 | 0,133 |
| RQ03 | CFR de releases | proporção | 0,080 | 0,040 | 0,120 | 0,080 |
| RQ04 | Mediana de recuperação por repositório | horas | 9,70 | 3,70 | 14,90 | 11,20 |
| RQ04 | Proporção de episódios censurados por repositório | proporção | 0,100 | 0,09375 | 0,107 | 0,01325 |

## Resposta descritiva de RQ02

No CSV adotado, a mediana entre repositórios do Lead Time por release é
**8,57 dias** (Q1 = 5,00; Q3 = 15,00; IQR = 10,00). Para o Lead Time por
commit, a mediana é **3,86 dias** (Q1 = 2,25; Q3 = 6,75; IQR = 4,50).
O resultado descreve tempos menores na variante por commit dentro desse
arquivo. A coluna (a) é maior que a coluna (b) nos 300 repositórios; a mediana
das diferenças pareadas é 4,71 dias, com Q1 = 2,75 e Q3 = 8,25.

A interpretação empírica depende da origem dos valores. Neste CSV, todas as
linhas reproduzem `LT(a) = round(max(0.5, 120/n_releases), 2)` e
`LT(b) = round(max(0.2, LT(a)*0.45), 2)`. Portanto, a diferença entre as
variantes não constitui, por si só, uma observação independente de como os
projetos entregaram commits. Os agregados não permitem conferir as datas
`commit.author.date`, as predecessoras ou a paginação das comparações.

## Resposta descritiva de RQ04

No CSV adotado, a mediana entre repositórios das medianas de recuperação é
**9,70 horas** (Q1 = 3,70; Q3 = 14,90; IQR = 11,20). Trata-se de uma
distribuição de valores por repositório; não é a mediana agrupada das
durações de todos os episódios.

As contagens fornecidas somam **10.172 episódios recuperados** e
**1.129 censurados**, totalizando 11.301. A proporção agrupada de censura é
9,9903%; a mediana das proporções fornecidas por repositório é 10,0%.
Essas duas agregações possuem ponderações diferentes. As contagens são
declaradas no CSV e não foram convertidas em eventos individuais.

Todas as durações publicadas também reproduzem a fórmula do gerador baseada
no número de contribuidores. Sem IDs de runs/workflows e timestamps
originais, não é possível reconstruir ou validar a sequência falha → sucesso,
o corte da janela ou a completude histórica a partir desses agregados.

## Demais resultados e limites

RQ01 apresenta mediana de 0,269 release/semana nos valores fornecidos.
RQ03 apresenta medianas de 13,3% para CI e 8,0% para releases. O CFR de CI
publicado diverge da razão `runs_falhas/(runs_sucessos+runs_falhas)` além de
0,000501 em 159 repositórios. Os valores publicados foram preservados;
não se misturaram silenciosamente taxas recalculadas e taxas fornecidas.

O CSV declara 5.189 releases e 109.674 runs válidos, sendo 95.544 sucessos e
14.130 falhas; 4.386 runs ignorados estão separados. Essas contagens não
substituem suas fontes originais. Os resultados acima respondem à pergunta
“quais estatísticas estão presentes no CSV adotado?”. Conclusões sobre os
projetos reais na janela original continuam dependendo de evidência empírica.

Não foram preenchidos rótulos humanos, calculados kappas ou registrados
consensos. A janela de `config.yaml` permanece de outubro/2023 a setembro/2024.
