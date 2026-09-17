# Consolidação de rodadas — S02, Áulus, Issue #37

Implementação da [Issue #37](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/37).
O ponto de entrada conduz a rodada e reúne tempo, aceitação, complexidade,
LOC e código preservado. Reutiliza o coordenador da Maria, o executor do
Vinícius, o coletor Radon de Áulus e a interface Gemini já existente.

A assistência de IA nesta infraestrutura não constitui uma rodada experimental.
Os exemplos usam somente **DEMO_DOBRO** (dobrar um inteiro), diferente dos seis
exercícios oficiais. Esta entrega não resolve os Katas manuais 1, 3 e 5 de
Áulus e não conclui a [Issue #38](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/38).

## Ambiente e comando único

Execute na raiz do repositório, com Python 3.12.10 e Radon 6.0.1. Pode reutilizar
a venv do coletor. Para preparar uma instalação nova:

```powershell
python -m venv Laboratorio02_TrialsIA/metricas_estruturais/.venv
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m pip install -r Laboratorio02_TrialsIA/metricas_estruturais/requirements.txt
```

Crie previamente o arquivo `.py` vazio no editor. O comando inicia o terminal
da rodada; o cronômetro começa quando você pressiona ENTER. A partir daí,
escreva sua solução e use `1` para testar, `2` para consultar tempo ou `3` para
interromper. Os testes reprovados permitem continuar até aprovação ou parada.

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/executar_rodada.py --participante aulus --exercicio kata01 --tratamento manual --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_aulus_manual.py
```

O caminho acima é apenas o destino que o participante criará e escreverá na
rodada manual. O comando não cria nem completa soluções manuais.

Os argumentos `--integrante`/`--kata` continuam aceitos como aliases de
`--participante`/`--exercicio`. Os códigos `1`, `K1`, `K01`, `kata1` e `kata01`
identificam o mesmo exercício. Opções adicionais:

| Opção | Uso |
| --- | --- |
| `--timebox 35` | Limite em minutos: maior que zero, finito e no máximo 35. |
| `--trial-id identificador` | Opcional; um identificador já existente é recusado. |
| `--saida pasta` | Pasta para os diretórios das rodadas. |
| `--csv arquivo.csv` | CSV com cabeçalho compatível; somente acrescenta novas linhas. |
| `--testes base.json` | Base alternativa para outro exercício, como a demonstração. |
| `--automatico` | Avalia uma vez e encerra: mede a avaliação de código já pronto, sem tempo de desenvolvimento. |
| `--gemini --enunciado arquivo.md` | Geração inicial pelo cliente existente, somente em tratamento `ia`. |

Sem `--saida`, preserva os destinos anteriores em `cronometro/resultados/` e
`cronometro/registro_experimento.csv`. Com `--saida`, o CSV padrão passa a ser
`<saida>/registro_experimento.csv`, mantendo demonstrações separadas. Não use
`--automatico` como medida do tempo de resolução manual.

## Tempo, versão final e resultados

O coordenador usa relógio monotônico. O limite funciona durante espera pelo
menu, execução dos testes e geração Gemini. Aprovação obtida depois do limite
não vira sucesso dentro do prazo. Ao selecionar interrupção, o relógio e o
código final são capturados antes da justificativa. EOF e Ctrl+C também
registram interrupção com tempo real.

Cada tentativa testa uma cópia. Se o arquivo em edição mudar enquanto os
testes executam, essa aprovação não é atribuída à nova versão. No encerramento,
o coletor analisa os mesmos bytes registrados nos testes, identificados por
SHA-256. Após limite ou interrupção, uma avaliação final da cópia congelada
registra a aceitação fora do tempo de resolução; mantém o timeout de 5 segundos
por caso. Mesmo uma aprovação nessa avaliação não muda o motivo de parada.

| Status | Interpretação | Código de saída CLI |
| --- | --- | --- |
| `SUCESSO` | Todos os testes passaram antes do prazo e a coleta foi concluída. | 0 |
| `TESTES_REPROVADOS` | A avaliação única terminou sem aprovação total. | 1 |
| `ERRO` | Falha da integração, preservação ou análise; detalhes no manifesto. | 2 |
| `LIMITE_ATINGIDO` | Tempo esgotado; censurado no limite configurado. | 3 |
| `INTERRUPCAO` | Parada antecipada com tempo real, sem censura de timebox. | 4 |

`status_encerramento` preserva a causa original mesmo quando uma falha posterior
de métricas produz `status=ERRO`. `dado_censurado` continua indicando se o limite
foi atingido. Sintaxe inválida gera falhas de execução na aceitação e
`status_analise=erro_sintaxe`, com métricas `null`. Dependência ausente e falhas
inesperadas também ficam explícitas. Testes indisponíveis têm resultado e taxa
`null` (campos vazios no CSV), nunca zero inventado. Código válido sem funções
mantém a convenção do coletor: complexidade média `null` e LOC medido.

Cada pasta `<trial_id>/` contém:

- `inicio_rodada.json`: identificação e configuração, também útil em falha de gravação posterior;
- `casos_testes.json`: base de aceitação preservada;
- `tentativa_001.py`, etc.: cópias utilizadas durante o desenvolvimento;
- `<trial_id>_solucao_final.py`: versão final preservada;
- `testes.json`: resultado, arquivo realmente executado e hash da solução/base;
- `metricas.json`: contrato do coletor mais o hash da solução;
- `manifesto_rodada.json`: schema 2, tempo, estados, erros e caminhos/hash dos artefatos.

CSV, início, manifesto, testes, métricas e nome da solução compartilham o mesmo
`trial_id`. Os JSON são criados sem substituir resultados existentes. Diretório
de rodada existente, ID repetido no CSV ou cabeçalho incompatível são recusados.
Falha de escrita em disco é informada pela CLI; arquivos já preservados ficam
no diretório reservado, sem promessa de que um relatório impossível de gravar
tenha sido produzido.

As soluções do experimento devem ser arquivos Python autônomos com stdin/stdout,
conforme o executor existente. As cópias ficam em outra pasta: imports de arquivos
vizinhos e dados externos não são coletados. Os subprocessos não são uma sandbox
de segurança. Cada comando interativo deve executar em seu próprio processo.

## Tratamento com Gemini

`--tratamento ia` registra o tratamento e permite o assistente externo usado
pelo participante. Para solicitar geração automática inicial, acrescente
`--gemini --enunciado caminho/do/exercicio.md`. O tempo da chamada entra na
rodada. O coordenador invoca `katas_Gemini.gerar_solucao` em um processo com
prazo, reutilizando prompt, extração, tentativas e cliente do grupo. Só copia
o código para o arquivo de trabalho quando a geração termina dentro do prazo.

No mesmo ambiente Python, instale `google-genai` e configure `GEMINI_API_KEY`
ou `GOOGLE_API_KEY` no ambiente. `GEMINI_MODEL` pode selecionar o modelo. O
padrão anterior `gemini-3.6-flash` foi preservado e sua disponibilidade foi
confirmada pela API na validação de 16/09/2026. Não há chave embutida no código.

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m pip install -r Laboratorio02_TrialsIA/consolidacao/requirements-gemini.txt
```

A dependência opcional está fixada em `google-genai==2.23.0`, versão instalada
na preparação local. A instalação do SDK não substitui a configuração da
credencial e a validação do modelo aprovado pelo grupo.

O comando em lote `casos_de_teste/katas_Gemini.py` continua disponível, agora
reutilizando essa função e exigindo chave pelo ambiente. A validação desta
entrega usa mocks e uma chamada real somente para DEMO_DOBRO, sem geração de
soluções oficiais. Nessa chamada, os três testes passaram, LOC foi 7 e a
complexidade média foi 1,0; IDs e hashes da rodada foram conferidos. A chave
foi recebida por entrada oculta e ficou apenas na memória dos processos usados
na validação, sem configuração permanente.

## Compatibilidade

Os comandos diretos de `cronometro/src/cronometro.py`, `executor.py` e
`coletar_metricas.py` permanecem disponíveis; o cronômetro e a nova entrada
compartilham a mesma implementação. O CSV conserva nomes e ordem das colunas.
Dados antigos não são migrados nem corrigidos retrospectivamente.

A API `avaliar_solucao` ganhou apenas o parâmetro opcional `deadline` (instante
monotônico absoluto). Expiração da rodada lança `TimeoutError`; timeout
individual continua como `TIMEOUT`. Erros de infraestrutura propagam a
exceção real, em vez de serem rotulados como `ERRO_SINTAXE`.

`coordenar_rodada` preserva os argumentos anteriores e acrescenta opções por
palavra-chave. `finalizar_rodada` reavalia resultados antigos sem cópia
verificável. A antiga função auxiliar `salvar_artefatos_rodada` foi substituída
por `consolidacao.artefatos.preservar`; não há mudança no comando do cronômetro.
O parâmetro legado `simulacao` continua disponível somente com pasta e CSV
separados, marca `simulada=true` e não fabrica aprovação. A nova demonstração
não utiliza esse parâmetro nem tempos simulados.

## Validação reproduzível

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m unittest discover -s Laboratorio02_TrialsIA/metricas_estruturais/tests -v
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m unittest discover -s Laboratorio02_TrialsIA/casos_de_teste/aceitacao_k05_k06 -v
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe -m unittest discover -s Laboratorio02_TrialsIA/consolidacao/tests -v
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/consolidacao/demonstrar.py
```

A demonstração usa DEMO_DOBRO e executa sucesso, testes reprovados, limite real
de 0,001 minuto, falha sintática na análise e interrupção por EOF na CLI. Confere
IDs, hashes, cópias executadas/preservadas, JSON, CSV e ausência de métricas
fabricadas. A aprovação pós-limite permanece censurada. Uma nova pasta é criada
em `consolidacao/resultados_demo/<data_uuid>/`, ignorada pelo Git, com
`resumo_demonstracao.json`. A opção `--saida` exige um destino novo; nenhuma
execução apaga resultados de demonstrações anteriores.

Validação desta entrega em Windows, Python 3.12.10 e Radon 6.0.1: **94 testes
aprovados** (31 do coletor, 12 dos casos/comparador e 51 da integração), cinco
cenários demonstrativos verificados e `pip check` sem dependências quebradas.
Gemini foi validado com mocks e uma chamada real no exercício demonstrativo,
concluída com sucesso. Novas chamadas exigem a configuração da chave no ambiente.

O [registro da entrega S02](ENTREGA_S02.md) reúne o estado da revisão, o texto
local para um futuro PR, os comandos das rodadas manuais e as pendências que
dependem do participante ou da configuração do Gemini.
