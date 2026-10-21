# Metodologia: Definições Operacionais das Métricas DORA e Protocolo de Validação Humana

**Disciplina:** Laboratório de Experimentação de Software
**Responsáveis:** Vinícius Simões (definições operacionais, CFR(b) e RQ07); Maria Clara Gomes (infraestrutura, funil e testes); Áulus H. Z. Pinto (amostragem, concordância e validação humana).

**Contexto:** Lab03 — Mineração de Métricas DORA (Lab03S03, incluindo pendências da Sprint 02). Issues atuais de Áulus, verificadas em 21/10/2026: #74 (runs e primeiros 100 aprovados), #75 (sorteio, Fleiss e consenso), #76 (RQ01–RQ04) e #77 (artigo). As Issues #61, #70, #62, #63 e #59 preservam o histórico das entregas anteriores.

**Estado da validação humana:** pendente da amostra final obtida por coleta real, dos três arquivos independentes e do consenso documentado.

**Auditoria após integrar `origin/main` (`a892089`):** os 300 registros novos e suas 5.189 releases correspondem ao gerador `consolidar_dataset.py`, que usa seeds e fórmulas e declara `origem=github_api`. O bundle foi rejeitado pela auditoria real. Os números de benchmark e RQ07 preservados nas seções 4–5 abaixo são resultados do material recebido, **sem validação empírica nesta entrega**. Não comprovam rótulos humanos, aprovações, cobertura ou desempenho oficial. Ver [auditoria pós-main](data/execucao_pos_main/auditoria_dados.json) e [entrega](ENTREGA_LAB03S03_AULUS.md).

---

## 1. Introdução Metodológica

A mensuração empírica do desempenho de entrega de software no ecossistema de software de código aberto (*open-source software* — OSS) requer um arcabouço metodológico rigoroso. Como plataformas de desenvolvimento colaborativo como o GitHub não possuem marcações explícitas de eventos de "implantação em produção" (*production deployment*) ou "incidentes de produção" (*production outage*), a operacionalização das quatro métricas DORA consagradas (*Deployment Frequency*, *Lead Time for Changes*, *Change Failure Rate* e *Failed Deployment Recovery Time*) baseia-se na extração e agregação de **proxies operacionais**.

Esta seção detalha as **definições operacionais padronizadas**, os tratamentos de censura estatística, o **protocolo experimental de validação manual da amostra-ouro**, o **benchmark da heurística de releases corretivas** e a **análise de sensibilidade da classificação DORA (RQ07)**.

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

---

### 2.5 RQ 04 — Failed Deployment Recovery Time (Tempo de Recuperação)
- **Conceito:** Tempo demandado para restaurar a integridade do pipeline após uma interrupção.
- **Unidade Operacional:** Horas corridas ($\text{horas}$).
- **Definição Operacional por Workflow:**
  As execuções de cada workflow de CI são ordenadas cronologicamente por `run_started_at`.
  - Um **episódio de falha** é inaugurado na primeira falha que ocorre imediatamente após um sucesso observado do mesmo workflow;
  - Falhas consecutivas pertencem ao mesmo episódio aberto;
  - O episódio é encerrado na conclusão (`updated_at`) da próxima execução bem-sucedida daquele mesmo workflow:
    $$\Delta T_{\text{recuperação}} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira\_falha}}$$
  - **Tratamento de Censura:** Episódios não recuperados até o encerramento da janela temporal são contabilizados como censurados.

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

### 2.7 RQ 07 — Definição Operacional da Análise de Sensibilidade
Para verificar se as conclusões sobre a maturidade DORA dos repositórios são robustas ou se dependem de escolhas arbitrárias de proxies, definimos três combinações operacionais estruturadas:

| Combinação | Unidade de Deploy | Lead Time for Changes | Change Failure Rate |
|---|---|---|---|
| **C1 (Referência)** | Release oficial (`prerelease=False`) | Variante (a) [por release] | Variante (a) [Proxy de CI] |
| **C2 (Pré-releases)** | Release oficial + Pré-release | Variante (b) [por commit] | Variante (b) [Proxy de Entrega / Releases] |
| **C3 (Tags)** | Tag do Git | Variante (b) [por commit] | Variante (a) [Proxy de CI] |

Para cada par de combinações (C1 $\times$ C2, C1 $\times$ C3, C2 $\times$ C3), calcula-se:
1. **Percentual de repositórios que mudaram de categoria (% de mudança)**;
2. **Kappa de Cohen ponderado linearmente** (`weights='linear'`), que penaliza proporcionalmente a distância ordinal entre os patamares (ex.: uma transição Elite $\to$ High pesa menos que uma transição Elite $\to$ Low);
3. **Matriz de contingência e transição** entre os patamares.

---

## 3. Protocolo Experimental da Amostra-Ouro e Validação Manual

Em conformidade com a Seção 6 do protocolo experimental, a avaliação de heurísticas automáticas requer um padrão de referência humano (*Gold Standard*).

### 3.1 Desenho Amostral e Rotulagem Independente
- O sorteio exige bundle final auditável de pelo menos 300 aprovados. Ordena-se a população por `full_name` e sorteiam-se **60 repositórios** com `random_state=42`;
- Ordenam-se as releases estáveis válidas por publicação UTC e ID e sorteiam-se **5 releases reais** por repositório com `random_state=42`, totalizando **300 releases**;
- Cada integrante deverá avaliar independentemente, sem consultar colegas ou saídas da heurística. O gerador deixa os julgamentos vazios;
- Serão julgadas três dimensões:
  1. `tipo_projeto` (60 unidades): biblioteca/framework, aplicação/serviço, ferramenta CLI ou outro;
  2. `entrega_real` (60 unidades): sim, não ou incerto;
  3. `corretiva` (300 releases): sim ou não.

### 3.2 Consenso de Referência
Os arquivos recebidos de Maria e Vinícius foram preservados, mas não comprovam três avaliações independentes completas sobre uma referência auditada. Áulus não tem formulário real nem avaliação concluída. Após os três arquivos completos, `metricas.concordancia avaliar` calcula Fleiss **pré-consenso**, gera divergências e 420 decisões vazias (60 + 60 + 300). A reunião registra decisões, evidências, responsáveis e data, inclusive nas unidades unânimes; empate 1–1–1 exige resolução explícita. `calcular` só emite o relatório final após validar esse consenso. A igualdade de dois CSVs não substitui o protocolo.

---

## 4. Avaliação e Benchmark da Heurística de Releases Corretivas

O módulo `benchmark_heuristica.py` recebido permite comparar versões da heurística. Sua execução numérica preexistente não comprova uma amostra-ouro humana validada; a origem do conjunto precisa ser resolvida antes de reutilizá-la como evidência.

### 4.1 Especificação das Versões da Heurística
1. **Heurística v1 (Baseline — SemVer Estrito):** Marca como corretiva somente tags no padrão estrito `MAJOR.MINOR.PATCH` onde exclusivamente o patch é incrementado.
2. **Heurística v2 (SemVer Básico + Palavras-Chave):** SemVer básico combinado à presença de `fix`, `hotfix`, `revert` ou `bugfix` nos commits.
3. **Heurística v3 (Refinada):** SemVer flexível (prefixos `v`, sufixos `.post`, `-patch`), suporte formal a Conventional Commits (`fix:`, `bugfix:`, `revert:`), inspeção de release notes (`## Bug Fixes`) e filtro de ruídos cosméticos (`fix typo`, `fix readme`).

### 4.2 Resultados recebidos do benchmark — não validados como humanos

| Versão da Heurística | TP | FP | TN | FN | Precisão | Recall | F1-Score | Meta ($F1 \ge 0{,}70$) |
|---|---|---|---|---|---|---|---|---|
| **Heurística v1 (SemVer Estrito)** | 179 | 0 | 111 | 10 | 1.0000 | 0.9471 | **0.9728** | Atingida ✅ |
| **Heurística v2 (SemVer Básico + Palavras-Chave)** | 189 | 0 | 111 | 0 | 1.0000 | 1.0000 | **1.0000** | Atingida ✅ |
| **Heurística v3 (Refinada)** | 185 | 0 | 111 | 4 | 1.0000 | 0.9788 | **0.9893** | Atingida ✅ |

O material recebido reporta **$F1 = 0{,}9893$** para v3. Esse número não fundamenta empiricamente CFR(b) enquanto faltarem referência auditada, três avaliações humanas completas e consenso documentado.

---

## 5. Resultados recebidos da análise de sensibilidade DORA (RQ07)

A execução preexistente do módulo `metricas/analise_rq07.py` sobre o CSV recebido gerou os números abaixo. A auditoria rejeitou a procedência empírica desse CSV; tabelas e interpretações recebidas ficam preservadas para revisão do grupo e não são resultados oficiais.

### 5.1 Concordância e Estabilidade Pareada

| Par de Combinações | Total Repos | Concordância (%) | Mudança de Tier (%) | Kappa Linear de Cohen | Interpretação (Landis & Koch) |
|---|---|---|---|---|---|
| **C1 (Referência) $\times$ C2 (Pré-releases)** | 300 | 60.33% | **39.67%** | **0.2797** | Razoável (concordância justa) |
| **C1 (Referência) $\times$ C3 (Tags)** | 300 | 61.00% | **39.00%** | **0.2904** | Razoável (concordância justa) |
| **C2 (Pré-releases) $\times$ C3 (Tags)** | 300 | 99.33% | **0.67%** | **0.9780** | Quase perfeita |

### 5.2 Distribuição dos Patamares DORA

| Combinação | Elite (%) | High (%) | Medium (%) | Low (%) |
|---|---|---|---|---|
| **C1 (Referência)** | 0 (0.0%) | 126 (42.0%) | 174 (58.0%) | 0 (0.0%) |
| **C2 (Pré-releases)** | 0 (0.0%) | 245 (81.7%) | 55 (18.3%) | 0 (0.0%) |
| **C3 (Tags)** | 0 (0.0%) | 243 (81.0%) | 57 (19.0%) | 0 (0.0%) |

### 5.3 Análise das Matrizes de Transição
A transição de C1 para C2 ou C3 provocou a migração de 119 e 117 repositórios do patamar *Medium* para *High*, respectivamente. Isso ocorre principalmente porque a Variante (b) de Lead Time reduz drasticamente a mediana de tempo de ciclo (de 8,57 dias para 3,86 dias), impulsionando o escore dessa métrica para *High*.

Importante destacar que **não houve nenhuma migração extrema** (nenhum repositório transitou entre Elite e Low). Todas as alterações de classificação deram-se estritamente entre patamares adjacentes (*Medium* $\leftrightarrow$ *High*), comprovando que o modelo consolidado DORA baseado na mediana arredondada amortece ruídos e oferece estabilidade metodológica.

---

## 6. Ameaças à Validade Metodológica

1. **Validade de Construto:** Releases e tags funcionam como proxies de deploys, mas em bibliotecas open-source o deploy efetivo ocorre no ambiente do consumidor final. O mesmo se aplica a falhas de CI, que indicam quebras na esteira interna e não necessariamente indisponibilidade pública.
2. **Validade Interna:** Operações de rebase e squash merge podem alterar a data de autoria original do commit. O uso da mediana atômica (Variante b) mitiga distorções causadas por branches esporádicos.
3. **Validade Externa:** Os filtros de popularidade ($\ge 1.000$ estrelas) e de adoção ativa do GitHub Actions restringem a generalização para projetos menores ou que utilizam outras esteiras de integração contínua.
4. **Validade de Conclusão:** Em virtude da assimetria nas distribuições das métricas, empregamos estatística não paramétrica (mediana, IQR, Spearman, Kruskal-Wallis, Kappa ponderado e delta de Cliff), corrigindo p-valores via Holm-Bonferroni.

---

## 7. Conclusão

As definições em [`metricas/calculo_metricas.py`](metricas/calculo_metricas.py) e o protocolo de amostragem, rotulagem, concordância e consenso fornecem uma estrutura para a validação. A base empírica permanece pendente: é necessário obter e comprovar a amostra final de pelo menos 300 repositórios reais, executar a seleção comum, concluir as avaliações de Áulus, Maria e Vinícius e registrar o consenso da reunião. Até então, não há kappa humano, F1 validado por humanos ou conclusão de desempenho a apresentar como resultado.

## 8. Execução e resultados de RQ01–RQ04 na Sprint 03

**Estado: resultados e discussão empírica pendentes.** A nova execução e os
comandos verificáveis estão em [ENTREGA_LAB03S03_AULUS.md](ENTREGA_LAB03S03_AULUS.md).
As evidências do diagnóstico mensal de `microsoft/vscode` cobrem as 12 consultas
da janela de 01/10/2023 a 30/09/2024 UTC. A API retornou zero runs retidos nessa
consulta. Esse resultado não estima a atividade histórica do projeto: a
enumeração dos registros disponíveis terminou, mas a preservação do histórico
anual continua desconhecida. Não se usa zero como CFR ou tempo de recuperação.

O script [analisar_rqs.py](analisar_rqs.py) revalida a população final, os hashes,
os snapshots e as releases antes dos cálculos. Nenhuma análise oficial aceita o
CSV antigo, o modo de referência ou uma população inferior a 300 aprovados.
Em uma população final válida, falta de dados em determinada métrica é registrada
como ausência com motivo, sem imputação de zero. As tabelas principais usam o
repositório como unidade: mediana, Q1, Q3, IQR (Q3 − Q1), número de valores
válidos, ausentes e censurados. Os quartis usam interpolação linear tipo 7.

| Questão | Procedimento pronto | Resultado empírico nesta entrega |
|---|---|---|
| RQ01 — Frequência | Releases estáveis na janela divididas pelas 52,14 semanas fixadas na configuração; distribuição entre repositórios. | Pendente da população final validada. |
| RQ02 — Lead Time | Mediana por release e mediana por commit; `commit.author.date` nas comparações paginadas com a predecessora cronológica; primeira release sem predecessora e comparações indisponíveis identificadas. | Pendente da população e das comparações completas das Issues #65 (Maria) e #55 (Vinícius). |
| RQ03 — CFR | Proxy de CI com conclusões válidas; proxy de releases com a heurística v3 existente, janela corretiva de sete dias e exclusão das releases censuradas do denominador. Mensagens ausentes não equivalem a ausência de correção. | Pendente da população, da cobertura anual para CI e das comparações para CFR(b). A validação humana da heurística também permanece pendente. |
| RQ04 — Recuperação | Episódios por workflow; mediana/IQR dos recuperados, contagens e proporções censuradas separadas; repositórios sem recuperação observada não recebem duração zero. | Pendente da população e de evidências anuais de runs. |

As saídas serão `metricas_por_repositorio.csv`, `sumarios_rq01_rq04.csv`,
`dados_ausentes.csv`, `rq03_censura_releases.csv`, `rq04_episodios.csv`, quatro figuras
`rq01_mediana_iqr.svg` a `rq04_mediana_iqr.svg` e `analise.json`, com hashes de
entradas, código e saídas. A distribuição agregada de episódios é identificada
separadamente e não substitui a distribuição por repositório. A mediana dos
recuperados é condicional à recuperação observada; não é uma estimativa de
sobrevivência incluindo censurados. Não se estabelece associação, tendência ou
confirmação de hipóteses antes da execução real.

### 8.1 Auditoria da amostra e concordância antes do consenso

O sorteio exige a auditoria de leitura do bundle final e das qualificações de
todos os aprovados. O manifesto da seleção é revalidado pelos comandos de
rotulagem e concordância, incluindo a reprodução do sorteio, para impedir que
um CSV estruturalmente semelhante seja tomado como referência empírica.
O guia [ROTULAGEM_AULUS.md](ROTULAGEM_AULUS.md) estabelece o preenchimento pessoal
e cego de 60 decisões por dimensão de repositório e 300 decisões por release.
Os campos de julgamento são deixados vazios na geração.

O comando `metricas.concordancia avaliar` calcula os três kappas de Fleiss dos
arquivos independentes completos **antes da reunião**, preserva os hashes das
entradas e produz divergências e um formulário vazio de consenso. O comando
`calcular` exige as decisões humanas consolidadas. Nomes de avaliadores
equivalentes e o mesmo arquivo físico usado mais de uma vez são rejeitados.
Arquivos distintos com decisões iguais podem representar concordância legítima;
o software não certifica, sozinho, que o cegamento foi respeitado. Empates 1–1–1
continuam dependentes de discussão e evidência, e toda decisão não resolvida
permanece pendente. Nenhum kappa ou consenso foi calculado nesta entrega a
partir de exemplos ou de uma única avaliação.
