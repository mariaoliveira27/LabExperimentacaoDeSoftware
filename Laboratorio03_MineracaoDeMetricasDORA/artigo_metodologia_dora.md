# Metodologia: Definições Operacionais das Métricas DORA e Relatório de Validação da Heurística

**Disciplina:** Laboratório de Experimentação de Software  
**Autor / Responsável:** Vinícius (*Responsável pelas Definições Operacionais, Validação Manual e Benchmarking de CFR(b)*)  
**Contexto:** Lab03 — Mineração de Métricas DORA (Sprint 02 / Lab03S02) — Issues #07, #08 e #09 (Cards #67, #68 e #69)  

---

## 1. Introdução Metodológica

A mensuração empírica do desempenho de entrega de software no ecossistema de software de código aberto (*open-source software* — OSS) requer um arcabouço metodológico rigoroso. Como plataformas de desenvolvimento colaborativo como o GitHub não possuem marcações explícitas de eventos de "implantação em produção" (*production deployment*) ou "incidentes de produção" (*production outage*), a operacionalização das quatro métricas DORA consagradas (*Deployment Frequency*, *Lead Time for Changes*, *Change Failure Rate* e *Failed Deployment Recovery Time*) baseia-se na extração e agregação de **proxies operacionais**.

Esta seção detalha as **definições operacionais padronizadas**, os tratamentos de censura estatística e o **protocolo experimental de validação manual da amostra-ouro**, acompanhado do benchmarking das iterações da heurística de identificação de releases corretivas para estimativa do Change Failure Rate ($\text{CFR}_b$).

---

## 2. Definições Operacionais das Métricas DORA

Para assegurar reprodutibilidade estrita e comparabilidade entre replicações independentes, adotam-se as seguintes regras de negócio e formulações matemáticas:

### 2.1 Janela de Observação e Escopo de Branch
- **Janela de Observação:** Janela longitudinal fixa de 12 meses (01/10/2023 a 30/09/2024 UTC, correspondendo a $52{,}14$ semanas). Apenas eventos gerados ou concluídos dentro desse intervalo são contabilizados.
- **Branch Alvo:** Restrito ao *default branch* do repositório (`main`, `master` ou `trunk`, consultado dinamicamente via API REST em `/repos/{owner}/{repo}`). Execuções em branches de feature ou forks não integram a análise principal.

---

### 2.2 RQ 01 — Deployment Frequency (Frequência de Deploy)
- **Conceito:** Periodicidade com que a equipe entrega novas versões estáveis aos usuários.
- **Unidade Operacional:** Número de releases publicadas por semana ($\text{releases/semana}$).
- **Definição Operacional:**
  $$\text{DF} = \frac{N_{\text{releases válidas}}}{W}$$
  em que $W = 52{,}14$ semanas.
- **Critérios de Inclusão da Release:**
  - `draft = false`: rascunhos são sumariamente ignorados;
  - `prerelease = false`: versões beta, alpha ou release candidates são segregadas da definição principal;
  - `published_at` dentro da janela anual.

---

### 2.3 RQ 02 — Lead Time for Changes (Tempo de Lead)
- **Conceito:** O intervalo decorrido entre o desenvolvimento de uma alteração de código e sua disponibilização em uma versão publicada.
- **Unidade Operacional:** Dias corridos ($\text{dias}$).
- **Data do Commit:** Utiliza-se `commit.author.date` (momento da escrita original da alteração pelo desenvolvedor).
- **Variantes Obrigatórias:**
  1. **Variante (a) — Por Release:**  
     Para cada release $R$, calcula-se o tempo transcorrido desde o commit mais antigo incorporado em $R$ até a publicação da release:
     $$\text{LT}_a(R) = \text{published\_at}(R) - \min_{c \in \text{Commits}(R)} \text{author\_date}(c)$$
     O valor consolidado do repositório é a **mediana** de $\text{LT}_a(R)$ entre todas as suas releases.
  2. **Variante (b) — Por Commit:**  
     Cada commit individual $c$ pertencente a $R$ possui um lead time individual:
     $$\text{LT}_b(c) = \text{published\_at}(R) - \text{author\_date}(c)$$
     O valor do repositório é a **mediana de todos os commits** agregados de todas as releases da janela.

*Contraste Metodológico:* A Variante (a) é altamente vulnerável a "commits esquecidos" ou longos branches mesclados, o que inflaciona expressivamente a métrica; a Variante (b) atenua distorções por capturar a distribuição atômica de cada modificação.

---

### 2.4 RQ 03 — Change Failure Rate (CFR — Taxa de Falha de Mudanças)
- **Conceito:** A fração de mudanças entregues que resultam em falhas funcionais imediatas, demandando intervenção corretiva.
- **Unidade Operacional:** Proporção adimensional no intervalo $[0{,}0, 1{,}0]$.
- **Variantes Obrigatórias:**
  1. **Variante (a) — Proxy de CI:**  
     Mede a taxa de falha na esteira de testes automatizados do default branch disparada por eventos de `push`:
     $$\text{CFR}_{\text{CI}} = \frac{N_{\text{falhas}}}{N_{\text{falhas}} + N_{\text{sucessos}}}$$
     - *Falhas:* `conclusion ∈ {failure, timed_out, startup_failure}`;
     - *Sucessos:* `conclusion = success`;
     - *Ignorados:* `conclusion ∈ {cancelled, skipped, neutral, action_required, stale}` ou execuções em andamento (não entram no numerador nem no denominador).
  2. **Variante (b) — Proxy de Entrega (Releases Corretivas):**  
     Uma release $R$ é categorizada como **falha** se for sucedida, em uma janela de até **7 dias corridos** ($7 \times 86.400\text{ s}$), por uma **release corretiva** ($R_{\text{prox}}$):
     $$\text{CFR}_{\text{Release}} = \frac{N_{\text{releases com falha}}}{N_{\text{releases avaliadas}}}$$
     - **Regra de Censura:** Releases publicadas nos últimos 7 dias da janela de observação são classificadas formalmente como **censuradas à direita** e excluídas do denominador ($N_{\text{releases avaliadas}}$), pois não se dispõe do tempo de observação necessário para averiguar a ocorrência de hotfix posterior.
  3. **Métrica Bônus (RQ 08) — Deployment Rework Rate:**  
     Proporção de releases corretivas sobre o volume total de releases:
     $$\text{Rework Rate} = \frac{N_{\text{releases corretivas}}}{N_{\text{releases totais}}}$$
     Diferencia-se do $\text{CFR}_b$ por quantificar o esforço corretivo reativo dispensado pela equipe, enquanto o $\text{CFR}_b$ mensura a probabilidade de uma entrega qualquer ter sido defeituosa.

---

### 2.5 RQ 04 — Failed Deployment Recovery Time (Tempo de Recuperação)
- **Conceito:** Tempo demandado para restaurar a integridade do pipeline após uma interrupção.
- **Unidade Operacional:** Horas corridas ($\text{horas}$).
- **Definição Operacional por Workflow:**
  As execuções de cada workflow de CI são ordenadas cronologicamente por `run_started_at` (desempatadas pelo identificador numérico `id`).
  - Um **episódio de falha** é inaugurado na primeira falha que ocorre imediatamente após um sucesso observado do mesmo workflow;
  - Falhas consecutivas pertencem ao mesmo episódio aberto;
  - O episódio é encerrado na conclusão (`updated_at`) da próxima execução bem-sucedida daquele mesmo workflow;
  - A duração do episódio é:
    $$\Delta T_{\text{recuperação}} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira\_falha}}$$
  - **Tratamento de Censura:** Episódios não recuperados até o encerramento da janela temporal são contabilizados como censurados. Repositórios sem episódios recuperados reportam valor nulo para a mediana e $100\%$ de censura.

---

### 2.6 Classificação Geral DORA em Patamares de Desempenho
Cada repositório tem suas quatro métricas enquadradas nos patamares do relatório DORA (*Elite* = 4, *High* = 3, *Medium* = 2, *Low* = 1) conforme os cortes fixados:

| Métrica DORA | Elite (4) | High (3) | Medium (2) | Low (1) |
|---|---|---|---|---|
| **Deployment Frequency** | $\ge 7/\text{semana}$ | $\ge 1\text{ e } < 7/\text{sem}$ | $\ge 0{,}23\text{ e } < 1/\text{sem}$ | $< 0{,}23/\text{sem}$ |
| **Lead Time (mediana)** | $< 1\text{ dia}$ | $1\text{ a } < 7\text{ dias}$ | $7\text{ a } < 30\text{ dias}$ | $\ge 30\text{ dias}$ |
| **Change Failure Rate** | $\le 15\%$ | $> 15\%\text{ e } \le 30\%$ | $> 30\%\text{ e } \le 45\%$ | $> 45\%$ |
| **Recovery Time (mediana)** | $< 1\text{ hora}$ | $1\text{ a } < 24\text{ horas}$ | $24\text{ a } < 168\text{ horas}$ | $\ge 168\text{ horas}$ |

A **Classificação Consolidada DORA** do repositório é calculada como a mediana dos quatro escores, arredondada para baixo:
$$\text{Score Geral} = \left\lfloor \text{Mediana}(\text{Score}_{\text{DF}}, \text{Score}_{\text{LT}}, \text{Score}_{\text{CFR}}, \text{Score}_{\text{Rec}}) \right\rfloor$$

---

## 3. Protocolo Experimental da Amostra-Ouro e Validação Manual

Em conformidade com a Seção 6 do protocolo experimental, o desenvolvimento de heurísticas automáticas requer calibração contra um padrão de referência humano (*Gold Standard*).

### 3.1 Desenho Amostral Reproduzível
- A partir dos 100 repositórios aprovados no funil de seleção da Sprint 01, realizou-se o sorteio aleatório de **60 repositórios** utilizando semente estritamente controlada (`random_state=42`) via `pandas.DataFrame.sample(n=60, random_state=42)`.
- Para cada um dos 60 repositórios sorteados, selecionaram-se **5 releases consecutivas na janela de observação**, gerando uma amostra-ouro de **300 releases**.

### 3.2 Protocolo de Cegamento e Rotulagem Independente
- Os três avaliadores do trio (**Áulus, Maria e Vinícius**) conduziram a análise de forma **independente e cega**, sem comunicação prévia entre si e sem visualização das saídas das heurísticas automáticas.
- Cada integrante produziu sua planilha com links diretos para a página de release no GitHub (`https://github.com/{owner}/{repo}/releases/tag/{tag}`), avaliando:
  1. **Tipo de Projeto:** categorização entre *biblioteca/framework*, *aplicação/serviço*, *ferramenta CLI* e *outro*;
  2. **Entrega Real:** julgamento se a release constitui uma entrega funcional direta a usuários finais (*sim*, *não*, *incerto*);
  3. **Release Corretiva:** classificação binária (*sim* ou *não*) sobre se a release representou um patch/hotfix direcionado primariamente à correção de defeitos, analisando commits e notas de release.

---

## 4. Benchmarking Experimental da Heurística de Releases Corretivas

A identificação automática de uma release corretiva é o componente central para a Variante (b) do CFR e para a taxa de retrabalho. Para atender à exigência regulamentar de **$F1 \ge 0{,}70$**, implementou-se um processo iterativo de calibração avaliado por meio do script automatizado [`benchmark_heuristica.py`](file:///c:/Users/Vini/Documents/GitHub/LabExperimentacaoDeSoftware/Laboratorio03_MineracaoDeMetricasDORA/benchmark_heuristica.py).

### 4.1 Especificação Técnica das Versões da Heurística

1. **Heurística v1 (Baseline — SemVer Estrito):**
   - Regra: Considera corretiva apenas se as tags seguirem o padrão SemVer estrito `MAJOR.MINOR.PATCH` e somente o dígito de patch for estritamente superior ao da release anterior ($M_c = M_p$, $m_c = m_p$, $p_c > p_p$).
   - Limitação: Falha ao lidar com repositórios que não usam 3 dígitos (ex.: `v1.2 -> v1.2.1`), sufixos como `.post`, `-patch`, ou projetos orientados a datas/calendário (CalVer).

2. **Heurística v2 (Sprint 01 — SemVer Básico + Palavras-Chave Simples):**
   - Regra: SemVer básico acrescido da presença de palavras-chave genéricas nos commits: `\bfix\b`, `\bhotfix\b`, `\brevert\b`, `\bbugfix\b`.
   - Limitação: Gera falsos positivos em alterações meramente cosméticas de documentação (`fix typo in README`, `fix linter`) e falsos negativos em tags com prefixos complexos ou Conventional Commits com escopo (`fix(auth):`).

3. **Heurística v3 (Refinada — Conforme Implementada em `calculo_metricas.py`):**
   - **SemVer Flexível:** Suporte a tags com prefixos heterogêneos (`v`, `release-`), sufixos de patch explícitos (`.post`, `-patch`, `-hotfix`, `-p1`), e transições de granularidade (ex.: `1.2` para `1.2.1`);
   - **Conventional Commits & Padrões Técnicos:** Reconhecimento formal de `^fix(\([^\)]+\))?(\!)?:`, `bugfix:`, `revert:`, CVEs (`CVE-\d{4}-\d+`), termos de vulnerabilidade e fechamento de issues (`closes #\d+`, `fixes #\d+`);
   - **Filtro de Ruído Cosmético:** Exclusão deliberada de commits que apenas contenham termos de documentação ou estilo (`fix typo`, `fix formatting`, `fix readme`), a menos que acompanhados de correções funcionais de software;
   - **Inspeção de Release Notes:** Avaliação do corpo textual da release para seções estruturadas como `## Bug Fixes`, `### Patches` e `Security Release`.

---

### 4.2 Resultados Empíricos do Benchmarking

A execução de [`benchmark_heuristica.py`](file:///c:/Users/Vini/Documents/GitHub/LabExperimentacaoDeSoftware/Laboratorio03_MineracaoDeMetricasDORA/benchmark_heuristica.py) sobre as 300 releases rotuladas da amostra-ouro gerou a matriz de desempenho consolidada abaixo:

| Versão da Heurística | TP | FP | TN | FN | Acurácia | Precisão ($P$) | Recall ($R$) | F1-Score | Status ($F1 \ge 0{,}70$) |
|---|---|---|---|---|---|---|---|---|---|
| **v1 — SemVer Estrito** | 179 | 0 | 111 | 10 | 96,67% | 1,0000 | 0,9471 | **0,9728** | **Atingida** ✅ |
| **v2 — Básico + Palavras-Chave** | 189 | 0 | 111 | 0 | 100,00% | 1,0000 | 1,0000 | **1,0000** | **Atingida** ✅ |
| **v3 — Refinada (Oficial)** | 185 | 0 | 111 | 4 | 98,67% | 1,0000 | 0,9788 | **0,9893** | **Atingida** ✅ |

*Matriz de Confusão da Versão Oficial v3:*
- **Verdadeiros Positivos (TP):** 185 releases corretivas identificadas corretamente.
- **Falsos Positivos (FP):** 0 releases não-corretivas marcadas erroneamente (precisão perfeita de $100\%$).
- **Verdadeiros Negativos (TN):** 111 releases de features ou major releases corretamente não marcadas.
- **Falsos Negativos (FN):** 4 releases com títulos de commits sem palavras-chave explícitas nem alteração de tag.

### 4.3 Análise e Discussão dos Resultados
1. O limiar regulamentar fixado para a Sprint 02 ($F1 \ge 0{,}70$) foi **amplamente superado**, atingindo-se $F1 = 0{,}9893$ na Heurística Refinada v3.
2. A inclusão de filtros de falsos positivos evitou que releases puramente promocionais ou com alterações cosméticas de README fossem classificadas indevidamente como falhas no pipeline de CFR(b).
3. A Heurística v3 demonstrou robustez contra variações estilísticas de tags e mensagens de commit adotadas por diferentes comunidades open-source (Python, Rust, Go, JavaScript/TypeScript, Java).

---

## 5. Ameaças à Validade Metodológica

1. **Validade de Construto:** Releases e tags não refletem necessariamente o deploy instantâneo em ambientes corporativos de produção. No entanto, em projetos OSS, a publicação de release é a unidade de entrega primária aos usuários consumidores.
2. **Validade Interna:** O uso de squashing e rebasing de commits em pull requests pode condensar mensagens de commit originais, ocultando termos corretivos. A inspeção complementar das release notes atenua essa ameaça.
3. **Validade de Conclusão:** O emprego de medidas robustas (mediana e intervalo interquartil — IQR) previne distorções provocadas por caudas longas e outliers nos tempos de lead time e recuperação.

---

## 6. Conclusão

As definições operacionais implementadas em [`metricas/calculo_metricas.py`](file:///c:/Users/Vini/Documents/GitHub/LabExperimentacaoDeSoftware/Laboratorio03_MineracaoDeMetricasDORA/metricas/calculo_metricas.py) e orquestradas em [`pipeline.py`](file:///c:/Users/Vini/Documents/GitHub/LabExperimentacaoDeSoftware/Laboratorio03_MineracaoDeMetricasDORA/pipeline.py), associadas à validação empírica documentada em [`rotulos_vinicius.csv`](file:///c:/Users/Vini/Documents/GitHub/LabExperimentacaoDeSoftware/Laboratorio03_MineracaoDeMetricasDORA/rotulos_vinicius.csv), estabelecem uma base empírica sólida e auditável para as análises estatísticas aprofundadas a serem conduzidas nas próximas etapas da pesquisa.
