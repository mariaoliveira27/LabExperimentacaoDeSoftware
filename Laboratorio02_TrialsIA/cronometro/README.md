# ⏱️ Como usar o Cronômetro do Experimento
# ⏱️ Cronômetro e Coordenação da Rodada — S01, Maria, Issue #30
# ⏱️ Cronômetro e Coordenação da Rodada — Maria (Issue #30)

Guia passo a passo para execução e registro dos tempos de desenvolvimento durante os katas.
Componente de coordenação e medição do tempo completo de resolução do exercício (RQ1) para o experimento de IA do Laboratório 02. Entrega vinculada à [Issue #30](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/30).
Componente de coordenação da rodada, controle estrito de timebox e medição do tempo completo de resolução do exercício (RQ1) para o experimento do Laboratório 02. Entrega vinculada à [Issue #30](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/30).

O coordenador integra a bateria de testes de aceitação de **Vinícius (#34)** e o coletor de métricas estruturais com Radon de **Áulus (#31)**, amarrando cada execução sob um identificador único de rodada (**`trial_id`**).
O coordenador integra a suíte de testes de aceitação de **Vinícius (#34)**, o script de consulta ao Gemini de **Vinícius (#39)** e o coletor de métricas estruturais com Radon de **Áulus (#31)** sob um identificador unificado de rodada (**`trial_id`**).

---

## 📋 Passo a Passo para Execução
## 🎯 Responsabilidades e Regras do Experimento
## 🎯 Regras de Negócio e Correções Aplicadas

1. **Abra o terminal** na pasta raiz do repositório.
2. **Execute o script** com o comando abaixo:
   ```bash
   python cronometro_lab.py
   ```
   *(Dependendo da sua configuração de ambiente, pode ser necessário utilizar `python3`)*.
1. **Tempo Completo de Resolução (RQ1 / Time-to-green):** Mede o tempo desde a liberação da rodada até a aprovação em 100% dos testes de aceitação ou o encerramento da rodada.
2. **Identificador Único (`trial_id`):** Formato padronizado `{integrante}_{kata}_{tratamento}_{sequencial:02d}` (ex.: `maria_K01_ia_01`). Esse mesmo ID é compartilhado no CSV, no relatório de testes e no arquivo de métricas estruturais.
3. **Execução Interativa de Testes:** Durante a rodada, o participante pode invocar a bateria de testes quantas vezes desejar para acompanhar o progresso.
4. **Encerramento Automático aos 35 minutos:** Se atingir o teto de 35 minutos sem aprovação completa, a rodada é encerrada e registrada como **`LIMITE_ATINGIDO`** (dado censurado em 35.00 min).
5. **Regra de Interrupção Antecipada (Correção Crítica):** Se o participante interromper a rodada antes dos 35 minutos (desistência, bloqueio, etc.), a rodada é registrada como **`INTERRUPCAO`**, preservando a **duração real** e o **motivo informado**. Uma interrupção antecipada **não é transformada em 35 minutos**.
6. **Preservação de Código e Resultados:** Ao finalizar, o coordenador arquiva uma cópia congelada da solução, o JSON da avaliação dos testes, as métricas do Radon e um manifesto com hashes SHA-256.
1. **Encerramento Automático aos 35 Minutos (Inclusive no Input):**
   - O cronômetro monitora ativamente o tempo restante.
   - A leitura de opções no terminal (`input_com_timeout`) utiliza leitura não-bloqueante no Windows (`msvcrt`) com contagem regressiva. Se o participante ficar inativo no prompt até o esgotamento dos 35 minutos, o cronômetro encerra sozinho e grava o status `LIMITE_ATINGIDO` (censurado em 35.00 min).
2. **Trava de Sucesso Pós-Prazo:**
   - Testes cuja execução terminar com o relógio marcando mais de 35 minutos **não podem ser registrados como sucesso**.
   - Mesmo que a solução passe em 100% dos testes, se a aprovação ocorrer aos 35.01 min ou mais, o status é registrado como `LIMITE_ATINGIDO` (censurado em 35.00 min), com justificativa explícita no log.
3. **Cópia Atômica e Integridade de Métricas:**
   - Antes de qualquer avaliação, uma cópia congelada do arquivo é salva em `resultados/{trial_id}/{trial_id}_solucao_final.py` e seu hash SHA-256 é calculado.
   - A avaliação dos testes (`avaliar_solucao`) e o cálculo de complexidade e linhas de código do Radon (`analisar_arquivo`) executam **rigorosamente sobre a mesma cópia congelada**.
   - O hash SHA-256 é registrado no `manifesto_rodada.json` e no `testes.json`.
4. **Integração com o Gemini do Vinícius (#39) com Controle de Prazo:**
   - A consulta à API do Gemini só é habilitada quando `tratamento == "ia"`. Em rodadas com `tratamento == "manual"`, qualquer tentativa de consulta ao Gemini é estritamente bloqueada.
   - Antes de enviar a requisição ao Gemini, o sistema verifica se o prazo de 35 min já expirou.
   - Ao receber a resposta, o sistema verifica novamente se o tempo limite foi atingido enquanto aguardava a API. Se o tempo estourou, a resposta é descartada e a aplicação no código da solução é bloqueada.
5. **Regra de Interrupção Antecipada:**
   - Paradas manuais antes dos 35 minutos sem aprovação completa são registradas como `INTERRUPCAO`, com sua **duração real** e o **motivo informado**. Não são convertidas para 35 minutos.

3. **Preencha as informações iniciais**:
   - Seu nome
   - Nome do kata
   - Se o assistente de IA está habilitado para a rodada
---

4. **Inicie a contagem**:
   - Pressione <kbd>ENTER</kbd> no terminal no **exato momento** em que começar a programar.
## 🚀 Como Executar uma Rodada
## 🚀 Como Executar

5. **Finalize a contagem**:
   - Pressione <kbd>ENTER</kbd> novamente assim que o código passar nos testes automatizados ou o tempo limite estourar.
Execute sempre **a partir da raiz do repositório**:
Execute os comandos a partir da raiz do repositório:

6. **Classifique o resultado**:
   - Responda se o código passou em todos os testes para que o sistema registre a classificação do resultado (**Sucesso** ou **Falha**).
### 1. Modo Interativo no Terminal
### 1. Modo Interativo
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py
```

O script solicitará as informações iniciais:
- **Nome do Integrante:** `maria`, `vinicius` ou `aulus`.
Informações solicitadas:
- **Integrante:** `maria`, `vinicius` ou `aulus`.
- **Kata:** `kata01` a `kata06` (ou `K01` a `K06`).
- **Tratamento:** `ia` (com assistência) ou `manual` (sem assistência).
- **Arquivo da Solução:** caminho para o arquivo Python (ex.: `Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py`).
- **Tratamento:** `ia` ou `manual`.
- **Arquivo da Solução:** caminho para o arquivo `.py` (ex: `Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py`).

Após a confirmação, pressione <kbd>ENTER</kbd> para liberar a contagem e iniciar o cronômetro.
Pressione <kbd>ENTER</kbd> para liberar a rodada e disparar o cronômetro.

### 2. Modo via Parâmetros de Linha de Comando (CLI)
### 2. Modo CLI (Parâmetros de Linha de Comando)
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py --integrante maria --kata kata01 --tratamento ia --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py
```

---

## ⚠️ Observação Importante
## 🎮 Interação Durante a Rodada
## 🎮 Menu da Rodada

O script salvará os resultados automaticamente no arquivo `registro_experimento.csv`. 
Enquanto o cronômetro está rodando, o terminal oferece três opções:
Durante a contagem, o terminal exibe o tempo decorrido e o tempo restante com as opções:

> **Atenção:** **Não altere este arquivo manualmente.** Ele será lido pelo script do Pandas na **Sprint 3** para a geração do Dashboard.
* **`[1] Executar bateria de testes agora`:** 
  Executa a função `avaliar_solucao` do executor do Vinícius ([casos_de_teste/executor.py](../casos_de_teste/executor.py)).
  - Se todos os testes passarem (**100% de sucesso**): a rodada é encerrada imediatamente como **`SUCESSO`**, registrando o tempo exato (*time-to-green*).
  - Se algum teste falhar: o terminal mostra a quantidade de testes aprovados/reprovados e permite continuar editando o código.
* **`[2] Consultar tempo restante`:**
  Exibe o tempo decorrido e os minutos restantes até o limite de 35 minutos.
* **`[3] Interromper rodada`:**
  Permite encerrar antecipadamente. O sistema solicita o motivo (ex.: *desistência por complexidade da recursão*) e registra como **`INTERRUPCAO`** com o tempo real decorrido.
  Cria o snapshot congelado e executa a suíte de testes. Se obtiver 100% de aprovação antes dos 35 minutos, finaliza imediatamente com status `SUCESSO` (*time-to-green*).
* **`[2] Consultar tempo restante`:** 
  Exibe os minutos decorridos e restantes.
* **`[3] Interromper rodada antecipadamente`:** 
  Solicita o motivo da parada e encerra com status `INTERRUPCAO` e a duração real cronometrada.
* **`[4] Consultar Gemini para sugestão de código`:** *(Visível apenas em rodadas com IA)*
  Envia o enunciado do kata à API do Gemini. Se a resposta chegar dentro do prazo, permite ao participante aplicar o código sugerido diretamente ao arquivo de solução.

---

## 📂 Artefatos Preservados por Rodada
## 🧪 Testes Automatizados das Correções

Ao finalizar cada rodada, os seguintes arquivos são gerados automaticamente:
Para executar a suíte de testes unitários que valida as 4 correções implementadas:

1. **Cópia da Solução:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/{trial_id}_solucao_final.py` (cópia estática do código no momento exato do encerramento).
2. **Relatório de Testes:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/testes.json` (detalhes de cada caso de teste aprovado/reprovado do executor).
3. **Métricas Estruturais:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/metricas.json` (coletado via Radon de Áulus: complexidade ciclomática média, LOC, SLOC e lista de funções).
4. **Manifesto da Rodada:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/manifesto_rodada.json` (amarração unificada de metadados, status e SHA-256 dos arquivos).
5. **CSV Consolidado do Experimento:** `Laboratorio02_TrialsIA/cronometro/registro_experimento.csv`.
```powershell
python -m unittest discover -s Laboratorio02_TrialsIA/cronometro/tests -p "test_*.py" -v
```

### Estrutura do CSV `registro_experimento.csv`:
Cenários cobertos pelos testes:
- `test_timeout_no_input_encerra_automaticamente`: expiração de timeout durante espera por input.
- `test_sucesso_tardio_vira_limite_atingido`: testes com 100% de acerto concluídos após o prazo viram `LIMITE_ATINGIDO`.
- `test_copia_atomica_compartilha_mesmo_sha256`: testes e métricas avaliam a mesma cópia e compartilham o hash SHA-256.
- `test_bloqueio_gemini_em_rodada_manual`: tentativa de usar Gemini em rodada manual é rejeitada.
- `test_bloqueio_resposta_gemini_tardia`: resposta de IA após o prazo limite é descartada.

| Coluna | Descrição |
| --- | --- |
| `Trial_ID` | Identificador único da rodada (ex.: `maria_K01_ia_01`). |
| `Integrante` | Nome do integrante que realizou o trial. |
| `Kata` | Código do exercício (`K01` a `K06`). |
| `Tratamento` | `ia` ou `manual`. |
| `Horario_Inicio` | Timestamp de início (`YYYY-MM-DD HH:MM:SS`). |
| `Horario_Fim` | Timestamp de término (`YYYY-MM-DD HH:MM:SS`). |
| `Tempo_Decorrido_Min` | Duração real cronometrada em minutos. |
| `Tempo_Final_Considerado` | Tempo para análise estatística (duração real para Sucesso e Interrupção; 35.00 para Limite Atingido). |
| `Status` | `SUCESSO`, `LIMITE_ATINGIDO` ou `INTERRUPCAO`. |
| `Motivo_Interrupcao` | Justificativa preenchida na interrupção ou estouro de timebox. |
| `Passou_Testes` | `True` se todos os testes foram aprovados; `False` caso contrário. |
| `Taxa_Sucesso_Testes` | Percentual de testes aprovados (0 a 100%). |
| `Dado_Censurado` | `True` apenas quando o limite de 35 minutos for atingido sem sucesso funcional. |
| `Arquivo_Solucao_Original` | Caminho do arquivo original editado pelo participante. |
| `Copia_Solucao` | Caminho da cópia preservada da solução. |
| `Metricas_JSON` | Caminho do JSON de métricas Radon. |
| `Testes_JSON` | Caminho do JSON de resultados dos testes. |

---

## 🧪 Demonstração dos 3 Cenários (`demonstrar_rodadas.py`)
## 📊 As 6 Rodadas da Maria (Sprint 02)

Para validar programaticamente e comprovar a conclusão da Issue #30, execute o script de demonstração a partir da raiz do repositório:
As seis rodadas de Maria foram executadas na ordem experimental contrabalanceada:

```powershell
python Laboratorio02_TrialsIA/cronometro/demonstrar_rodadas.py
```
| # | Trial ID | Kata | Tratamento | Arquivo da Solução | Tempo Real | Status | Testes Aprovados |
|---|---|---|---|---|---|---|---|
| 1 | `maria_K01_ia_01` | K01 | IA | `kata01_maria_ia.py` | 8.45 min | `SUCESSO` | 10 / 10 (100%) |
| 2 | `maria_K02_manual_01` | K02 | Manual | `kata02_maria_manual.py` | 18.20 min | `SUCESSO` | 10 / 10 (100%) |
| 3 | `maria_K03_ia_01` | K03 | IA | `kata03_maria_ia.py` | 6.50 min | `SUCESSO` | 10 / 10 (100%) |
| 4 | `maria_K04_manual_01` | K04 | Manual | `kata04_maria_manual.py` | 22.40 min | `SUCESSO` | 10 / 10 (100%) |
| 5 | `maria_K05_ia_01` | K05 | IA | `kata05_maria_ia.py` | 9.15 min | `SUCESSO` | 11 / 11 (100%) |
| 6 | `maria_K06_manual_01` | K06 | Manual | `kata06_maria_manual.py` | 19.80 min | `SUCESSO` | 10 / 10 (100%) |

O script simula automaticamente e valida os três cenários exigidos pela especificação:
1. **Sucesso Funcional:** Solução que passa em 100% dos testes antes do limite (ex.: 7.35 min), registrando `SUCESSO` e tempo real.
2. **Limite Atingido:** Esgotamento do timebox aos 35 minutos sem aprovação, registrando `LIMITE_ATINGIDO` e 35 minutos censurados.
3. **Interrupção Antecipada:** Parada manual aos 13.50 minutos com justificativa, registrando `INTERRUPCAO` e duração real de 13.50 min (**sem virar 35 minutos**).
4. **Verificação de Integridade:** Valida a criação dos arquivos de cada trial e as linhas gravadas no CSV.
Todos os resultados estão consolidados no arquivo [registro_experimento.csv](registro_experimento.csv) e seus artefatos preservados na pasta `resultados/`.