# Rotulagem independente de Áulus — Issue #62

O formulário `rotulos_aulus.csv` será criado com os identificadores e links reais
assim que existir uma população final auditável de pelo menos 300 repositórios
aprovados. A execução local atual possui zero aprovados; não há referência comum
válida de 60 repositórios e 300 releases. Criar linhas inventadas ou copiar a
amostra antiga não resolve essa pendência. A Issue #62 permanece aberta.

## Preparar a referência e o formulário

Execute na pasta do laboratório, usando o ambiente instalado:

```powershell
.\.venv\Scripts\python.exe executar_amostra_ouro.py --config config.yaml --coleta data/coleta_final --saida data/amostra_ouro --rotulos rotulos_aulus.csv
```

O comando exige `repositorios_aprovados.csv`, `releases.json` e
`proveniencia.json` do mesmo bundle final, com os snapshots de qualificação
auditáveis. Verifica os critérios da coleta e sorteia 60 repositórios e cinco
releases por repositório, com população ordenada e `random_state=42`. Salva a
referência vazia, as notas originais das releases e um manifesto com hashes,
versões e identificadores. Não substitui seleção ou formulário existentes.

Se o sorteio já existe e somente o formulário de Áulus ainda não foi criado:

```powershell
.\.venv\Scripts\python.exe rotulagem.py gerar --amostra data/amostra_ouro/amostra_comum.csv --saida rotulos_aulus.csv
```

A CLI confere `selecao.json`, os hashes das entradas, a auditoria do bundle e a
reprodução do sorteio antes de aceitar a referência. Preserve a pasta da coleta
original e os caminhos das entradas registrados no manifesto. Uma referência
com julgamentos preenchidos será rejeitada para preservar o cegamento.

## Preencher pessoalmente, antes de consultar outros avaliadores

1. Trabalhe somente no seu CSV e nas fontes originais do projeto. Não consulte
   os rótulos de Maria ou Vinicius, previsões automáticas de corretivas ou um
   consenso antes de terminar e preservar sua avaliação independente.
2. Mantenha `full_name`, `release_id`, `published_at`, `tag_name`, `html_url`,
   `release_notes_url`, `commits_url` e `previous_tag` sem alterações. Salve em
   UTF-8, com vírgula como delimitador e aspas nos textos que contêm vírgulas.
3. Para cada um dos 60 repositórios, leia README, descrição e documentação.
   Em `tipo_projeto`, escolha exatamente `biblioteca/framework`,
   `aplicação/serviço`, `ferramenta CLI` ou `outro`.
4. Avalie se as releases representam entregas funcionais aos usuários, incluindo
   consumidores de bibliotecas, usando notas, artefatos e documentação de
   distribuição. Em `entrega_real`, escolha `sim`, `não` ou `incerto`.
   Repita as decisões de `tipo_projeto` e `entrega_real` nas cinco linhas do
   mesmo repositório; elas correspondem a uma decisão por repositório.
5. Para cada uma das 300 releases, abra `release_notes_url` e `commits_url`.
   Marque `corretiva=sim` quando o objetivo predominante for corrigir defeitos,
   regressões ou vulnerabilidades; caso contrário, marque `não`. Um incremento
   de patch sozinho não determina a classificação. Quando `previous_tag` estiver
   vazio, o link apresenta o histórico da tag; consulte também o histórico
   anterior para delimitar as mudanças da release.
6. Preencha `justificativa` e `evidencia` em cada linha: motivo da decisão e links,
   SHAs ou trechos identificáveis das fontes. Registre dificuldades de acesso ou
   ambiguidade. Para `corretiva`, que é binária, deixe a unidade pendente enquanto
   não puder julgá-la; não use um rótulo arbitrário para passar no validador.

Durante o preenchimento, o rascunho pode conter campos vazios:

```powershell
.\.venv\Scripts\python.exe rotulagem.py validar --amostra data/amostra_ouro/amostra_comum.csv --rotulos rotulos_aulus.csv --rascunho
```

Depois de concluir pessoalmente todas as unidades, execute sem `--rascunho`:

```powershell
.\.venv\Scripts\python.exe rotulagem.py validar --amostra data/amostra_ouro/amostra_comum.csv --rotulos rotulos_aulus.csv
Get-FileHash rotulos_aulus.csv -Algorithm SHA256
```

Preserve e versione esse arquivo antes da reunião do grupo. Registre que a
avaliação foi realizada sem consulta aos outros arquivos ou às previsões. O
validador comprova integridade estrutural; não consegue comprovar por si só a
independência humana. Só após essa avaliação e validação a Issue #62 pode ser
considerada concluída. Nenhum script preenche julgamentos em nome de Áulus.

## Concordância e reunião, após os três arquivos completos

Cada colega deverá avaliar a mesma referência de forma independente e preservar
sua versão anterior à reunião. O arquivo preexistente de Vinicius não será
adotado automaticamente como avaliação da nova referência. O exemplo usa uma
nova avaliação em `rotulos_vinicius_independente.csv`.

```powershell
.\.venv\Scripts\python.exe -m metricas.concordancia avaliar --amostra data/amostra_ouro/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria.csv --vinicius rotulos_vinicius_independente.csv --divergencias data/amostra_ouro/divergencias.csv --consenso data/amostra_ouro/consenso.csv --saida data/amostra_ouro/kappas_independentes.json
```

O comando valida os três arquivos completos, rejeita o mesmo arquivo físico
usado como mais de um avaliador e calcula o kappa de Fleiss anterior ao consenso.
São 60 unidades para `tipo_projeto`, 60 para `entrega_real` e 300 para
`corretiva`. Se houver somente uma categoria observada, o resultado será
indefinido, com motivo explícito. Conteúdos coincidentes de arquivos distintos
podem representar concordância legítima; hashes não comprovam independência.

O relatório identifica as divergências com suas evidências. O formulário de
consenso mantém vazias as 420 decisões, inclusive unanimidades. Na reunião,
confiram as fontes, discutam divergências e registrem `rotulo_consenso`,
`justificativa`, `evidencia`, `responsaveis` (`aulus;maria;vinicius`),
`data_reuniao` (`YYYY-MM-DD`) e `protocolo`. Apliquem maioria simples após a
discussão; empates 1-1-1 exigem decisão conjunta e registro em `desempate`.
Se a decisão não for possível, preservem a pendência. Não alterem retroativamente
os arquivos independentes usados para calcular a concordância.

Após documentar as 420 decisões do grupo, valide a consolidação final:

```powershell
.\.venv\Scripts\python.exe -m metricas.concordancia calcular --amostra data/amostra_ouro/amostra_comum.csv --aulus rotulos_aulus.csv --maria rotulos_maria.csv --vinicius rotulos_vinicius_independente.csv --consenso data/amostra_ouro/consenso.csv --saida data/amostra_ouro/kappas_consenso_final.json
```

Nenhum kappa, consenso ou resultado humano oficial foi produzido na execução
atual: faltam a população final auditada e as três avaliações humanas reais.
