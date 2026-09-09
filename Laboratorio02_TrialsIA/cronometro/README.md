# ⏱️ Cronômetro e Coordenação da Rodada — S01, Maria, Issue #30

Componente de coordenação e medição do tempo completo de resolução do exercício (RQ1) para o experimento de IA do Laboratório 02. Entrega vinculada à [Issue #30](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/30).

O coordenador integra a bateria de testes de aceitação de **Vinícius (#34)** e o coletor de métricas estruturais com Radon de **Áulus (#31)**, amarrando cada execução sob um identificador único de rodada (**`trial_id`**).

---

## 🎯 Responsabilidades e Regras do Experimento

1. **Tempo Completo de Resolução (RQ1 / Time-to-green):** Mede o tempo desde a liberação da rodada até a aprovação em 100% dos testes de aceitação ou o encerramento da rodada.
2. **Identificador Único (`trial_id`):** Formato padronizado `{integrante}_{kata}_{tratamento}_{sequencial:02d}` (ex.: `maria_K01_ia_01`). Esse mesmo ID é compartilhado no CSV, no relatório de testes e no arquivo de métricas estruturais.
3. **Execução Interativa de Testes:** Durante a rodada, o participante pode invocar a bateria de testes quantas vezes desejar para acompanhar o progresso.
4. **Encerramento Automático aos 35 minutos:** Se atingir o teto de 35 minutos sem aprovação completa, a rodada é encerrada e registrada como **`LIMITE_ATINGIDO`** (dado censurado em 35.00 min).
5. **Regra de Interrupção Antecipada (Correção Crítica):** Se o participante interromper a rodada antes dos 35 minutos (desistência, bloqueio, etc.), a rodada é registrada como **`INTERRUPCAO`**, preservando a **duração real** e o **motivo informado**. Uma interrupção antecipada **não é transformada em 35 minutos**.
6. **Preservação de Código e Resultados:** Ao finalizar, o coordenador arquiva uma cópia congelada da solução, o JSON da avaliação dos testes, as métricas do Radon e um manifesto com hashes SHA-256.

---

## 🚀 Como Executar uma Rodada

Execute sempre **a partir da raiz do repositório**:

### 1. Modo Interativo no Terminal
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py
```

O script solicitará as informações iniciais:
- **Nome do Integrante:** `maria`, `vinicius` ou `aulus`.
- **Kata:** `kata01` a `kata06` (ou `K01` a `K06`).
- **Tratamento:** `ia` (com assistência) ou `manual` (sem assistência).
- **Arquivo da Solução:** caminho para o arquivo Python (ex.: `Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py`).

Após a confirmação, pressione <kbd>ENTER</kbd> para liberar a contagem e iniciar o cronômetro.

### 2. Modo via Parâmetros de Linha de Comando (CLI)
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py --integrante maria --kata kata01 --tratamento ia --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py
```

---

## 🎮 Interação Durante a Rodada

Enquanto o cronômetro está rodando, o terminal oferece três opções:

* **`[1] Executar bateria de testes agora`:** 
  Executa a função `avaliar_solucao` do executor do Vinícius ([casos_de_teste/executor.py](../casos_de_teste/executor.py)).
  - Se todos os testes passarem (**100% de sucesso**): a rodada é encerrada imediatamente como **`SUCESSO`**, registrando o tempo exato (*time-to-green*).
  - Se algum teste falhar: o terminal mostra a quantidade de testes aprovados/reprovados e permite continuar editando o código.
* **`[2] Consultar tempo restante`:**
  Exibe o tempo decorrido e os minutos restantes até o limite de 35 minutos.
* **`[3] Interromper rodada`:**
  Permite encerrar antecipadamente. O sistema solicita o motivo (ex.: *desistência por complexidade da recursão*) e registra como **`INTERRUPCAO`** com o tempo real decorrido.

---

## 📂 Artefatos Preservados por Rodada

Ao finalizar cada rodada, os seguintes arquivos são gerados automaticamente:

1. **Cópia da Solução:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/{trial_id}_solucao_final.py` (cópia estática do código no momento exato do encerramento).
2. **Relatório de Testes:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/testes.json` (detalhes de cada caso de teste aprovado/reprovado do executor).
3. **Métricas Estruturais:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/metricas.json` (coletado via Radon de Áulus: complexidade ciclomática média, LOC, SLOC e lista de funções).
4. **Manifesto da Rodada:** `Laboratorio02_TrialsIA/cronometro/resultados/{trial_id}/manifesto_rodada.json` (amarração unificada de metadados, status e SHA-256 dos arquivos).
5. **CSV Consolidado do Experimento:** `Laboratorio02_TrialsIA/cronometro/registro_experimento.csv`.

### Estrutura do CSV `registro_experimento.csv`:

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

Para validar programaticamente e comprovar a conclusão da Issue #30, execute o script de demonstração a partir da raiz do repositório:

```powershell
python Laboratorio02_TrialsIA/cronometro/demonstrar_rodadas.py
```

O script simula automaticamente e valida os três cenários exigidos pela especificação:
1. **Sucesso Funcional:** Solução que passa em 100% dos testes antes do limite (ex.: 7.35 min), registrando `SUCESSO` e tempo real.
2. **Limite Atingido:** Esgotamento do timebox aos 35 minutos sem aprovação, registrando `LIMITE_ATINGIDO` e 35 minutos censurados.
3. **Interrupção Antecipada:** Parada manual aos 13.50 minutos com justificativa, registrando `INTERRUPCAO` e duração real de 13.50 min (**sem virar 35 minutos**).
4. **Verificação de Integridade:** Valida a criação dos arquivos de cada trial e as linhas gravadas no CSV.