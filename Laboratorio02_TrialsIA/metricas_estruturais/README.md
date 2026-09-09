# Métricas estruturais — S01, Áulus, Issue #31

Componente de preparação da RQ3: coleta estática de um arquivo Python por
rodada, com Radon 6.0.1. Entrega vinculada à
[Issue #31](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/31).
Inclui API importável, CLI, testes e uma demonstração de integração. Os
[contratos e testes de integridade K05/K06](../casos_de_teste/aceitacao_k05_k06/README.md)
ficam junto ao executor do grupo em `casos_de_teste/`. Os 21 casos estão na
[base JSON compartilhada](../casos_de_teste/casos_de_teste_katas.json), nas chaves
`kata05` e `kata06`, sem cópia paralela. Esta organização acompanha a `main`
`ae17487`, que renomeou a pasta do laboratório para `Laboratorio02_TrialsIA`.

O experimento planejado compara programação em Python com e sem Gemini, em
seis exercícios recursivos, com limite de 35 minutos por rodada. RQ1 mede tempo
até todos os testes passarem; RQ2 mede taxa de testes aprovados; RQ3 mede
complexidade média por função, acompanhada de LOC. Duplicação não foi selecionada.
A assistência de IA na preparação desta infraestrutura S01 não constitui uma
rodada experimental. Os programas de exemplo não resolvem os exercícios oficiais.

## Ambiente e instalação

Execute os comandos **na raiz do repositório**, em PowerShell. `python` deve
apontar para Python 3.12; a versão utilizada e preferida é **3.12.10**. Neste
computador, `python` encontra essa versão, enquanto o launcher `py` lista 3.13;
por isso os comandos usam `python` e depois o executável explícito da venv.

```powershell
$env:PYTHONUTF8 = '1'
python --version
python -m venv Laboratorio02_TrialsIA/metricas_estruturais/.venv
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m pip install -r Laboratorio02_TrialsIA/metricas_estruturais/requirements.txt
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m pip check
```

Não é necessário ativar a venv nem alterar a política de execução do PowerShell.
Em Linux/macOS, use `python3.12` para criá-la e `.venv/bin/python` no lugar de
`.venv\Scripts\python.exe`. Esses comandos alternativos não foram executados nesta
validação Windows. Arquivos de entrada e saída usam UTF-8; a entrada também
aceita BOM UTF-8. Ambiente, caches e `resultados_demo/` estão no `.gitignore`
do Lab02; nenhuma dependência do Lab01 foi alterada.

Versões efetivamente instaladas na validação:

| Componente | Versão |
| --- | --- |
| Python, Windows x64 | 3.12.10 |
| Radon (dependência direta fixada em `requirements.txt`) | 6.0.1 |
| colorama (transitiva) | 0.4.6 |
| mando (transitiva) | 0.7.1 |
| six (transitiva) | 1.17.0 |
| unittest, ast, json | Biblioteca padrão do Python 3.12.10 |

As transitivas acima registram o ambiente observado; apenas Radon está fixado
no arquivo de dependências. Para conferir o ambiente de outra máquina:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe --version
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m pip freeze
```

## Executar o coletor

```powershell
New-Item -ItemType Directory -Force Laboratorio02_TrialsIA/metricas_estruturais/resultados_demo | Out-Null
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/metricas_estruturais/src/coletar_metricas.py --arquivo Laboratorio02_TrialsIA/metricas_estruturais/exemplos/programa_demo.py --trial-id DEMO-S01-AULUS-001 --saida Laboratorio02_TrialsIA/metricas_estruturais/resultados_demo/coleta-001.json
```

O diretório de saída deve existir. Para repetir, escolha outro nome de JSON:
um destino existente é recusado. A partir de `src/`, a mesma interface é
`python coletar_metricas.py --arquivo <solucao.py> --trial-id <identificador> --saida <resultado.json>`,
usando o Python da venv. A análise abrange somente o arquivo indicado, inclusive
se ele contiver imports de outros módulos: esses imports não são resolvidos.

JSON obtido com o programa demonstrativo:

```json
{
  "schema_version": 1,
  "trial_id": "DEMO-S01-AULUS-001",
  "arquivo": "Laboratorio02_TrialsIA/metricas_estruturais/exemplos/programa_demo.py",
  "status_analise": "ok",
  "erro": null,
  "quantidade_funcoes": 2,
  "complexidade_media": 2.0,
  "loc": 11,
  "sloc": 8,
  "funcoes": [
    {"nome": "rotulo", "linha": 2, "complexidade": 1},
    {"nome": "classificar", "linha": 6, "complexidade": 3}
  ]
}
```

| Campo | Significado |
| --- | --- |
| `schema_version` | Versão do contrato de saída; inicialmente `1`. |
| `trial_id` | Identificador recebido, preservado sem transformação. |
| `arquivo` | Caminho recebido convertido em texto; caminhos relativos são relativos ao diretório de execução. |
| `status_analise` | `ok`, `erro_sintaxe`, `erro_leitura` ou `erro_analise`. |
| `erro` | `null` no sucesso; objeto com `tipo` da exceção e `mensagem` no erro. |
| `quantidade_funcoes` | Número de definições `def`/`async def`, incluindo auxiliares, métodos e aninhadas. |
| `complexidade_media` | Soma das complexidades dividida pela quantidade; sem arredondamento adicional. |
| `loc` | Total de linhas segundo `radon.raw.analyze`. |
| `sloc` | Linhas de código-fonte segundo `radon.raw.analyze`, complementares a LOC. |
| `funcoes` | Lista em ordem de linha; cada item contém `nome`, `linha` e `complexidade`. |
| `funcoes[].nome` | Nome qualificado pelos escopos, como `Classe.metodo.interna`; redefinições são distinguidas pela linha. |
| `funcoes[].linha` | Linha da declaração, começando em 1; não é a linha do decorador. |
| `funcoes[].complexidade` | Complexidade ciclomática individual calculada pelo Radon. |

Cada definição na AST é enumerada uma única vez. O cálculo do Radon é aplicado
à definição correspondente; não se adicionam os agregados das classes ou os
valores das funções internas à função externa. Isso inclui métodos de classes
locais dentro de funções. Lambdas não constituem funções separadas nessa métrica
do Radon. A AST é compilada apenas para validar a sintaxe e o contexto; o código
compilado nunca é executado. Nenhuma solução é importada.

LOC/SLOC são os valores diretos do Radon, sem contagem manual. LOC inclui linhas
vazias e comentários. O Radon separa linhas vazias, comentários isolados e strings
multilinha de SLOC; vale a identidade
`LOC = SLOC + blank + multi + single_comments`. Comentários na mesma linha de
código não retiram essa linha de SLOC. Referências:
[API de métricas brutas](https://radon.readthedocs.io/en/latest/api.html#raw-metrics)
e [definições das métricas](https://radon.readthedocs.io/en/latest/intro.html).
O comportamento foi conferido na instalação 6.0.1 e em testes com expectativas
explícitas; a documentação publicada pode exibir uma versão anterior.

## Erros e uso por outros scripts

Arquivo válido sem funções: `quantidade_funcoes=0`, `complexidade_media=null`,
`funcoes=[]`, preservando LOC/SLOC. Arquivo vazio é válido, com LOC/SLOC zero.

Falha de leitura (incluindo ausência, permissões e UTF-8 inválido), erro de
sintaxe ou falha reconhecida de análise: todas as métricas e `funcoes` ficam
`null`. O identificador e o caminho continuam disponíveis. Não interpretar
`null` como zero, nem excluir silenciosamente a rodada da análise futura.

| Código CLI | Situação |
| --- | --- |
| `0` | Análise e gravação concluídas. |
| `1` | Falha de leitura/análise; JSON de erro gravado. |
| `2` | Falha de gravação, destino existente ou argumentos inválidos. |

A CLI informa erros pelo stderr. Se a análise falhar e o destino estiver
disponível, grava o JSON de erro. Se a gravação falhar, informa o problema pelo
stderr e não promete um JSON. A criação exclusiva impede sobrescrita; em erro
durante a escrita, tenta remover o arquivo recém-criado incompleto.

Na raiz do repositório, outro script Python pode importar a API:

```python
from Laboratorio02_TrialsIA.metricas_estruturais.src.coletar_metricas import (
    analisar_arquivo,
    gravar_resultado,
)

resultado = analisar_arquivo("copia_final.py", trial_id="identificador-da-rodada")
# O chamador verifica status_analise, inclusive quando salva um registro de erro.
gravar_resultado(resultado, "resultado-da-rodada.json")
```

`analisar_arquivo` retorna o dicionário sem escrever. `gravar_resultado` exige
diretório existente e propaga `OSError` (incluindo `FileExistsError`) para o
chamador tratar. A CLI é responsável por converter essas falhas em códigos.

## Integração por rodada

O responsável pela execução deve escolher um `trial_id` único antes da rodada,
usando-o no registro de testes e na coleta de métricas. Ao encerrar a rodada,
preservar a cópia final da solução e passar seu caminho ao coletor. Coletar
também em rodadas sem sucesso funcional, registrando falhas de análise como tais.
Cada rodada gera um JSON próprio. O coletor preserva o ID recebido, mas não
mantém um cadastro global para detectar IDs repetidos em destinos diferentes.

O [cronômetro da Maria](../cronometro/src/cronometro.py) atualmente grava
`Integrante`, `Kata`, `Tratamento_IA`, `Horario_Inicio`, `Horario_Fim`,
`Tempo_Decorrido_Min`, `Passou_Testes`, `Tempo_Final_Considerado` e
`Dado_Censurado`; **não possui `trial_id`**. Sua interface e seu CSV permanecem
preservados. Para associar tempo futuramente, manter um manifesto externo por
rodada com `trial_id` e referência ao CSV arquivado: caminho, SHA-256 da cópia
arquivada e número da linha de dados (1 = primeira linha após o cabeçalho).
Conferir também integrante, kata, tratamento e início da linha selecionada.
Essa associação ainda será feita pelo responsável pela integração; não há
leitor ou modificador do CSV nesta entrega.

Demonstração completa, executável em processo separado:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/metricas_estruturais/exemplos/demonstrar_integracao.py --saida Laboratorio02_TrialsIA/metricas_estruturais/resultados_demo/integracao-001
```

Escolha uma pasta nova em repetições. O script preserva uma cópia do programa
demonstrativo, executa a CLI, relê seu JSON e cria `manifesto_demo.json`.
Valida o mesmo ID `DEMO-S01-AULUS-001` nas métricas e nas referências reservadas
para tempo e testes. No manifesto, tempo consta como `nao_coletado`, testes como
`nao_executado` e seus resultados como `null`; não há tempos ou taxas inventados.
Isso demonstra o contrato de associação futura, sem executar o cronômetro ou
rodar soluções pelo executor do Vinícius. A pasta de saída está ignorada pelo Git.

Para ler o JSON da coleta independente com outro programa:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -c "import json; from pathlib import Path; r = json.loads(Path('Laboratorio02_TrialsIA/metricas_estruturais/resultados_demo/coleta-001.json').read_text(encoding='utf-8')); print(r['trial_id'], r['complexidade_media'])"
```

O [executor do Vinícius](../casos_de_teste/executor.py) já está disponível e
consome K05/K06 na base compartilhada. `avaliar_solucao` recebe a cópia final e
a chave `kata05` ou `kata06`; o contrato completo está no
[guia dos casos](../casos_de_teste/aceitacao_k05_k06/README.md). A comparação de K06
respeita `tolerancia_absoluta=1e-9`, com tolerância relativa zero. Os outros casos
continuam usando a comparação existente.

Cada `entrada` é uma string completa para stdin; preservar a linha vazia do vetor
vazio. O relatório atual do executor identifica os casos pelo índice e ainda
não contém `trial_id`. Ao integrar os resultados, associar externamente o `id`
da base e o `trial_id` da rodada, tal como na referência ao CSV de tempo.
Os testes de integridade abaixo validam os dados preparados,
não são execuções de soluções dos exercícios. Uso de recursão exige revisão da
solução e não é demonstrado somente pelas saídas corretas.

## Testes

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m unittest discover -s Laboratorio02_TrialsIA/metricas_estruturais/tests -v
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m unittest discover -s Laboratorio02_TrialsIA/casos_de_teste/aceitacao_k05_k06 -p "test_*.py" -v
```

Os fixtures do coletor são pequenos programas demonstrativos. As expectativas
incluem CC 1, CC 2, média 2 para CC 1 e 3, métodos e funções aninhadas sem dupla
contagem, ausência de funções, LOC/SLOC, erros de leitura/sintaxe/gravação,
preservação de `trial_id`, recusa de sobrescrita e ausência de execução da fonte.

## Metodologia da RQ3

- **Pergunta:** o uso de IA altera a complexidade ciclomática média?
- **H0:** a complexidade média não difere entre os tratamentos com e sem IA.
- **H1:** a complexidade média difere entre os tratamentos com e sem IA.
- **Variável independente:** uso ou não de Gemini, sob o protocolo do grupo.
- **Métrica principal:** média aritmética da complexidade por função/método na
  cópia final de uma rodada: soma das CC individuais / número de definições.
- **Controle de tamanho:** LOC acompanha a complexidade; SLOC é informação
  complementar. Não há divisão automática da complexidade por LOC nem métrica
  de duplicação nesta entrega.

Radon foi escolhido por analisar Python estaticamente, oferecer complexidade
por função e métricas de linhas e permitir integração programática com uma
versão fixada. Funções auxiliares e aninhadas entram na mesma regra em ambos os
tratamentos. Decisões de módulo ou agregados de classe não são unidades dessa
média. As regras individuais de complexidade são as da versão 6.0.1, sem
redefinição manual de pesos para construções da linguagem.

A média **dentro de cada arquivo** não deve ser confundida com a agregação das
rodadas: o planejamento do laboratório recomenda mediana e IQR por tratamento
e comparação pareada (Wilcoxon) na análise posterior. Esta S01 não calcula
resultados experimentais nem testes de hipótese. Registros indisponíveis e
arquivos sem funções precisam de tratamento explícito no relatório, com
quantidades e motivos de ausência informados por tratamento.

Menor complexidade isoladamente não demonstra maior qualidade: decompor uma
solução em mais funções pode alterar a média; uma solução incompleta pode ter
CC baixa. Interpretar a RQ3 junto da correção funcional, de LOC e do protocolo.
Radon 6.0.1 não é uma prova de correção, recursão ou cobertura integral de todas
as construções futuras de Python; padronizar a versão da linguagem e da ferramenta.

A participação de Áulus na preparação dos casos pode influenciar o desempenho
posterior por familiaridade ou aprendizado; registrar essa exposição como
ameaça à validade e tratá-la no desenho/contrabalanceamento do grupo. Os
contratos K05/K06 são **convenções propostas pelo grupo**, não exigências
explícitas do professor. É necessário validar com o professor a adaptação dos
enunciados para Python antes das rodadas oficiais.
