# Execução real da coleta — Lab03S02

Execução em 14/10/2026 (horário de São Paulo), mantendo a janela UTC de
01/10/2023 a 30/09/2024 e os critérios de pelo menos 1.000 estrelas,
cinco releases estáveis e 50 runs válidos.

## Evidência recuperada

O arquivo público [Zenodo 20414642](https://zenodo.org/records/20414642),
DOI `10.5281/zenodo.20414642`, foi baixado integralmente para
`.cache/arquivos_historicos/2024/cicd_env_results.zip`.

- Tamanho: 952.289.386 bytes.
- MD5 publicado e conferido: `df0e00311cdfa611e784c373d20bacd5`.
- SHA-256: `285e9ad9ed0ecee07ebbf2cf3e0ccbc3f8075b5bcba2fbb48183886b7f9506c6`.
- Metadados recuperados: 19.849 repositórios; 32 com pelo menos 1.000 estrelas no snapshot da fonte.
- Exportação filtrada: 6.708 runs distintos de 15 repositórios, observados de janeiro a setembro de 2024, com `push`, default branch do snapshot, status concluído e conclusão válida.
- Dois repositórios desse filtro de estrelas não tinham arquivo de runs; a contagem permanece desconhecida (`None`).

Esses 15 repositórios **não são 15 aprovações finais**: ainda precisam satisfazer
os metadados e releases verificados pela coleta própria. A cobertura é um
limite inferior observado, sem comprovar o histórico anual ou as métricas DORA
anuais. O manifesto e os hashes estão em
[`data/historico_2024/proveniencia_historico.json`](data/historico_2024/proveniencia_historico.json).
O ZIP e os exports volumosos foram preservados localmente, fora do Git.

## Piloto da coleta integrada

```powershell
python coleta_amostra_real.py --config config.yaml --saida data/coleta_final --alvo 300 --limite-candidatos 100 --usar-gh-auth --historico-zenodo data/historico_2024 --reavaliar
```

O piloto consultou 100 candidatos da busca pública e não comprovou aprovações
nesses candidatos. As qualificações anteriores foram preservadas antes da
reavaliação. O estado final é `insuficiente`, com 100 processados e zero
aprovados, registrado em [`data/coleta_final/estado.json`](data/coleta_final/estado.json).
Isso não é conclusão sobre todos os repositórios do GitHub ou sobre todos os
projetos da fonte histórica. A busca foi limitada explicitamente a 100
candidatos; o total informado pela busca não representa uma coleta aprovada.

O funil, descartes, consultas e hashes são preservados em `data/coleta_final/`;
as respostas e snapshots originais ficam no cache local. Não foram publicados
os três arquivos finais consumidos pelo sorteio, porque faltam os 300 aprovados.

```powershell
python executar_amostra_ouro.py --config config.yaml --coleta data/coleta_final --saida data/amostra_ouro --rotulos rotulos_aulus.csv
```

O preparo recusa essa coleta parcial e informa os três arquivos necessários.
Não cria referência comum ou CSV humano substituto.

## Validação e pendências

Os testes relevantes incluem sorteio determinístico, 60 × 5 unidades, três
avaliadores, categorias e ausências, Fleiss, divergências e consenso; também
cobrem busca paginada, retomada, interrupções, origem dos exports, alteração
de hashes, arquivos históricos ausentes e preservação dos CSVs existentes.

```powershell
python -m pytest tests/test_busca_candidatos.py tests/test_coleta_amostra_real.py tests/test_baixar_historico.py tests/test_recuperar_historico.py tests/test_executar_amostra_ouro.py tests/test_amostra_ouro.py tests/test_rotulagem.py tests/test_concordancia.py
python -m pytest --cov=metricas --cov-report=term-missing --cov-fail-under=80
```

Resultado: 244 testes relevantes aprovados; suíte completa com 376 testes
aprovados e cobertura de `metricas` de 98,34%.

Faltam comprovar a população final de pelo menos 300 aprovados e gerar a
referência de 60 repositórios/300 releases. Depois disso, Áulus, Maria e Vinícius
precisam preencher e validar seus arquivos independentes sobre a mesma
referência, e o grupo deve registrar as 420 decisões de consenso. Só então
serão emitidos os três kappas finais. Não há resultado humano de kappa ou F1
nesta execução. `rotulos_vinicius.csv` e o CSV legado de 100 linhas foram
preservados. A Issue #62 continua pendente de julgamento humano.

Os comandos de geração, preenchimento, validação e concordância estão no
[`AMOSTRA_OURO.md`](AMOSTRA_OURO.md).
