# ⏱️ Cronômetro e Coordenação da Rodada — Maria (Issue #30)

Componente de coordenação da rodada, controle estrito de timebox e medição do tempo completo de resolução do exercício (RQ1) para o experimento do Laboratório 02. Entrega vinculada à [Issue #30](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/30).
**Atualização S02 — Issue #37:** o [guia da consolidação](../consolidacao/README.md)
documenta o comando único `executar_rodada.py`, estados de erro, cópias por
tentativa, limite durante espera de entrada/testes, integração Gemini e a
demonstração atual com exercício separado. O comando deste cronômetro continua
disponível e utiliza a mesma implementação. O manifesto novo usa schema 2;
resultados anteriores não foram modificados. As instruções de simulação abaixo
são o exemplo legado da S01, com tempos simulados explicitamente identificados.

Guia passo a passo para execução e registro dos tempos de desenvolvimento durante os katas.
Componente de coordenação e medição do tempo completo de resolução do exercício (RQ1) para o experimento de IA do Laboratório 02. Entrega vinculada à [Issue #30](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/30).

O coordenador integra a suíte de testes de aceitação de **Vinícius (#34)**, o script de consulta ao Gemini de **Vinícius (#39)** e o coletor de métricas estruturais com Radon de **Áulus (#31)** sob um identificador unificado de rodada (**`trial_id`**).

---

## 🎯 Regras de Negócio e Correções Aplicadas

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

## 📋 Passo a Passo para Execução
## 🎯 Responsabilidades e Regras do Experimento

1. **Abra o terminal** na pasta raiz do repositório.
2. **Execute o script** com o comando abaixo:
   ```bash
   python Laboratorio02_TrialsIA/cronometro/src/cronometro.py
   ```
   *(Dependendo da sua configuração de ambiente, pode ser necessário utilizar `python3`)*.
1. **Tempo Completo de Resolução (RQ1 / Time-to-green):** Mede o tempo desde a liberação da rodada até a aprovação em 100% dos testes de aceitação ou o encerramento da rodada.
2. **Identificador Único (`trial_id`):** Formato padronizado `{integrante}_{kata}_{tratamento}_{sequencial:02d}` (ex.: `maria_K01_ia_01`). Esse mesmo ID é compartilhado no CSV, no relatório de testes e no arquivo de métricas estruturais.
3. **Execução Interativa de Testes:** Durante a rodada, o participante pode invocar a bateria de testes quantas vezes desejar para acompanhar o progresso.
4. **Encerramento Automático aos 35 minutos:** Se atingir o teto de 35 minutos sem aprovação completa, a rodada é encerrada e registrada como **`LIMITE_ATINGIDO`** (dado censurado em 35.00 min).
5. **Regra de Interrupção Antecipada (Correção Crítica):** Se o participante interromper a rodada antes dos 35 minutos (desistência, bloqueio, etc.), a rodada é registrada como **`INTERRUPCAO`**, preservando a **duração real** e o **motivo informado**. Uma interrupção antecipada **não é transformada em 35 minutos**.
6. **Preservação de Código e Resultados:** Ao finalizar, o coordenador arquiva uma cópia congelada da solução, o JSON da avaliação dos testes, as métricas do Radon e um manifesto com hashes SHA-256.

3. **Preencha as informações iniciais**:
   - Seu nome
   - Nome do kata
   - Se o assistente de IA está habilitado para a rodada
---

## 🚀 Como Executar

Execute os comandos a partir da raiz do repositório:

### 1. Modo Interativo
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py
```

Informações solicitadas:
- **Integrante:** `maria`, `vinicius` ou `aulus`.
- **Kata:** `kata01` a `kata06` (ou `K01` a `K06`).
- **Tratamento:** `ia` ou `manual`.
- **Arquivo da Solução:** caminho para o arquivo `.py` (ex: `Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py`).

Pressione <kbd>ENTER</kbd> para liberar a rodada e disparar o cronômetro.

### 2. Modo CLI (Parâmetros de Linha de Comando)
```powershell
python Laboratorio02_TrialsIA/cronometro/src/cronometro.py --integrante maria --kata kata01 --tratamento ia --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_maria_ia.py
```

---

## 🎮 Menu da Rodada

Durante a contagem, o terminal exibe o tempo decorrido e o tempo restante com as opções:

* **`[1] Executar bateria de testes agora`:** 
  Cria o snapshot congelado e executa a suíte de testes. Se obtiver 100% de aprovação antes dos 35 minutos, finaliza imediatamente com status `SUCESSO` (*time-to-green*).
* **`[2] Consultar tempo restante`:** 
  Exibe os minutos decorridos e restantes.
* **`[3] Interromper rodada antecipadamente`:** 
  Solicita o motivo da parada e encerra com status `INTERRUPCAO` e a duração real cronometrada.
* **`[4] Consultar Gemini para sugestão de código`:** *(Visível apenas em rodadas com IA)*
  Envia o enunciado do kata à API do Gemini. Se a resposta chegar dentro do prazo, permite ao participante aplicar o código sugerido diretamente ao arquivo de solução.

---

## 🧪 Testes Automatizados das Correções

Para executar a suíte de testes unitários que valida as 4 correções implementadas:

```powershell
python -m unittest discover -s Laboratorio02_TrialsIA/cronometro/tests -p "test_*.py" -v
```

Cenários cobertos pelos testes:
- `test_timeout_no_input_encerra_automaticamente`: expiração de timeout durante espera por input.
- `test_sucesso_tardio_vira_limite_atingido`: testes com 100% de acerto concluídos após o prazo viram `LIMITE_ATINGIDO`.
- `test_copia_atomica_compartilha_mesmo_sha256`: testes e métricas avaliam a mesma cópia e compartilham o hash SHA-256.
- `test_bloqueio_gemini_em_rodada_manual`: tentativa de usar Gemini em rodada manual é rejeitada.
- `test_bloqueio_resposta_gemini_tardia`: resposta de IA após o prazo limite é descartada.

---

## 📊 As 6 Rodadas da Maria (Sprint 02)

As seis rodadas de Maria foram executadas na ordem experimental contrabalanceada:

| # | Trial ID | Kata | Tratamento | Arquivo da Solução | Tempo Real | Status | Testes Aprovados |
|---|---|---|---|---|---|---|---|
| 1 | `maria_K01_ia_01` | K01 | IA | `kata01_maria_ia.py` | 8.45 min | `SUCESSO` | 10 / 10 (100%) |
| 2 | `maria_K02_manual_01` | K02 | Manual | `kata02_maria_manual.py` | 18.20 min | `SUCESSO` | 10 / 10 (100%) |
| 3 | `maria_K03_ia_01` | K03 | IA | `kata03_maria_ia.py` | 6.50 min | `SUCESSO` | 10 / 10 (100%) |
| 4 | `maria_K04_manual_01` | K04 | Manual | `kata04_maria_manual.py` | 22.40 min | `SUCESSO` | 10 / 10 (100%) |
| 5 | `maria_K05_ia_01` | K05 | IA | `kata05_maria_ia.py` | 9.15 min | `SUCESSO` | 11 / 11 (100%) |
| 6 | `maria_K06_manual_01` | K06 | Manual | `kata06_maria_manual.py` | 19.80 min | `SUCESSO` | 10 / 10 (100%) |

Todos os resultados estão consolidados no arquivo [registro_experimento.csv](registro_experimento.csv) e seus artefatos preservados na pasta `resultados/`.
O script simula automaticamente e valida os três cenários exigidos pela especificação:
1. **Sucesso Funcional:** Solução que passa em 100% dos testes antes do limite (ex.: 7.35 min), registrando `SUCESSO` e tempo real.
2. **Limite Atingido:** Esgotamento do timebox aos 35 minutos sem aprovação, registrando `LIMITE_ATINGIDO` e 35 minutos censurados.
3. **Interrupção Antecipada:** Parada manual aos 13.50 minutos com justificativa, registrando `INTERRUPCAO` e duração real de 13.50 min (**sem virar 35 minutos**).
4. **Verificação de Integridade:** Valida a criação dos arquivos de cada trial e as linhas gravadas no CSV.
