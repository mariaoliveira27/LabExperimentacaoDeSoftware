# Mineração de Métricas DORA em Repositórios Open-Source: Introdução e Hipóteses de Pesquisa

**Disciplina:** Laboratório de Experimentação de Software  
**Integrantes:** Maria (*Responsável por Seleção, Infraestrutura e Integração*)  
**Contexto:** Lab03 — Mineração de Métricas DORA (Sprint 01 / Lab03S01)  

---

## 1. Introdução e Justificativa

### 1.1 Contexto e Relevância das Métricas DORA
Na última década, a adoção de práticas de DevOps, Integração Contínua (CI) e Entrega Contínua (CD) transformou a engenharia de software contemporânea. No centro dessa evolução encontram-se as métricas propostas pelo programa de pesquisa *DevOps Research and Assessment* (DORA), consolidadas na obra seminal *Accelerate: The Science of Lean Software and DevOps* (Forsgren, Humble & Kim, 2018). As quatro métricas DORA consagradas avaliam o desempenho da entrega de software sob duas dimensões complementares:

1. **Velocidade (*Throughput*):**
   - *Deployment Frequency:* a periodicidade com que modificações são entregues com sucesso aos usuários;
   - *Lead Time for Changes:* o intervalo decorrido entre a autoria do commit e a sua disponibilização em ambiente produtivo.
2. **Estabilidade (*Stability*):**
   - *Change Failure Rate (CFR):* a proporção de entregas que resultam em falhas imediatas exigindo intervenções corretivas (*hotfixes*, *rollbacks*);
   - *Failed Deployment Recovery Time (antigo MTTR):* o tempo requerido para restaurar o estado operacional após um episódio de falha.

Em relatórios anuais (*Accelerate State of DevOps*), o consórcio DORA categoriza as equipes de engenharia em quatro patamares de maturidade: *Elite*, *High*, *Medium* e *Low*. O principal achado empírico propagado na literatura corporativa é que velocidade e estabilidade não configuram um compromisso (*trade-off*); pelo contrário, equipes de alto desempenho operam com entregas frequentes em lotes reduzidos (*small batch sizes*), o que simplifica o rastreamento de defeitos, reduz o tempo de ciclo e maximiza a confiabilidade do sistema.

### 1.2 O Problema Central: A Mineração por Meio de Proxies Empíricos
A despeito da ampla aceitação do modelo DORA em ambientes corporativos privados, a sua transposição para o ecossistema de software de código aberto (*open-source software* — OSS) impõe desafios metodológicos substanciais. 

Plataformas de hospedagem colaborativa como o GitHub **não dispõem de registros explícitos de "deploys em produção" nem de "falhas operacionais de produção"**. Um repositório comunitário gerencia seu ciclo de vida por meio de *commits*, *tags*, *releases* públicas e fluxos automatizados no GitHub Actions. Dessa maneira, qualquer esforço de mineração de métricas DORA em larga escala baseia-se fundamentalmente na inferência por **proxies operacionais**:
- Uma **release publicada** (`draft = false`, `prerelease = false`) atua como proxy do evento de *deploy*;
- Uma execução de workflow de CI com status de falha (`conclusion ∈ {failure, timed_out, startup_failure}`) no branch principal atua como proxy de *falha de integração/entrega*;
- O lançamento iminente de uma nova release contendo correções de defeito (*patch release*) em até 7 dias atua como proxy de *falha de release*.

A adoção de proxies suscita questionamentos fundamentais de validade de construto: em que medida uma falha de teste em uma esteira de CI reflete um incidente real de entrega? Uma biblioteca que lança versões mensais possui a mesma dinâmica de entrega que uma ferramenta executável?

Nesse cenário, o presente estudo justifica-se pela necessidade de:
1. **Estabelecer um pipeline de mineração rigoroso e reprodutível**, orientado a dados de repositórios reais que utilizam GitHub Actions como esteira oficial de integração;
2. **Registrar a integridade metodológica da amostra**, documentando o funil de seleção com base em critérios objetivos de inclusão e motivos explícitos de descarte;
3. **Contrastar empiricamente as definições operacionais**, estabelecendo hipóteses prévias para avaliar se as premissas do modelo DORA se sustentam em projetos de código aberto.

---

## 2. Questões de Pesquisa e Hipóteses

Em conformidade com as diretrizes do estudo pré-experimental da Sprint 01, formulam-se a seguir as hipóteses informais para as Questões de Pesquisa sob responsabilidade direta de análise e modelagem: **RQ03**, **RQ04** e **RQ05**, delineadas antes da inspeção dos resultados finais.

---

### RQ 03. Qual a taxa de falha das mudanças entregues por esses repositórios?

#### Definição Operacional das Variantes:
- **Variante (a) — Proxy de CI:** 
  $$\text{CFR}_{\text{CI}} = \frac{\text{Runs com Falha}}{\text{Runs com Falha} + \text{Runs com Sucesso}}$$
  Considerando execuções do default branch com `event = push` e `conclusion ∈ {failure, timed_out, startup_failure}` (falhas) versus `conclusion = success` (sucessos), ignorando execuções canceladas ou neutras.
- **Variante (b) — Proxy de Entrega (Releases):** 
  Uma release $R$ é classificada como falha se for sucedida em até 7 dias corridos por uma release corretiva (identificada por incremento exclusivo do dígito de *patch* no SemVer e/ou mensagens de commit contendo `fix`, `hotfix`, `revert`). Releases nos últimos 7 dias da janela de observação são devidamente censuradas.

#### Hipótese H03 (Informal):
> **Esperamos que a taxa de falha medida pelo proxy de CI ($\text{CFR}_{\text{CI}}$) seja substancialmente superior à taxa de falha medida pelo proxy de releases corretivas ($\text{CFR}_{\text{Release}}$). Estimamos que a mediana de $\text{CFR}_{\text{CI}}$ se situará na faixa de 15% a 30% (categorias High a Medium), enquanto o $\text{CFR}_{\text{Release}}$ apresentará mediana inferior a 10% (categoria Elite).**

#### Justificativa Teórica:
O propósito essencial de uma esteira automatizada de Integração Contínua é atuar como uma rede de contenção rápida (*fail-fast*). Em repositórios de alta visibilidade com centenas de contribuidores, os testes automatizados, linters e verificações de cobertura no branch principal são desenhados para capturar regressões imediatas. Uma falha de CI indica que o mecanismo de controle de qualidade operou com sucesso antes que o código defeituoso fosse empacotado para distribuição.

Em contrapartida, as *releases* oficiais de projetos open-source passam por um filtro deliberado de estabilização humana e pré-testes. Apenas uma fração diminuta de releases introduz defeitos críticos que exigem a publicação emergencial de um *hotfix* em menos de uma semana. Portanto, as duas variantes capturam momentos distintos do ciclo de vida: a Variante (a) reflete a volatilidade do desenvolvimento diário no repositório, enquanto a Variante (b) reflete o impacto perceptível aos usuários finais.

---

### RQ 04. Qual o tempo de recuperação após uma execução de CI/CD com falha?

#### Definição Operacional:
Ordenam-se cronologicamente as execuções de um mesmo workflow no default branch. Um episódio de falha tem início na primeira falha após um sucesso e finda no término (`updated_at`) da próxima execução bem-sucedida daquele mesmo workflow:
$$\text{Tempo de Recuperação} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira\_falha}}$$
Episódios não recuperados até o encerramento da janela de observação são categorizados formalmente como **censurados**. O índice do repositório é calculado pela **mediana** dos episódios de seus workflows.

#### Hipótese H04 (Informal):
> **Esperamos que a mediana do tempo de recuperação dos episódios de falha de CI seja inferior a 24 horas (enquadrando os repositórios na faixa High ou Elite), porém com distribuição fortemente assimétrica e presença observável de episódios censurados (estimados entre 5% e 15% dos episódios totais).**

#### Justificativa Teórica:
Em projetos populares com cultura ativa de CI/CD, uma quebra no default branch compromete a capacidade de todos os demais colaboradores de rebasear ou testar seus pull requests (princípio de "parar a esteira" herdado do Lean/Toyota Production System). Logo, desenvolvedores principais priorizam a reversão imediata (*git revert*) ou a aplicação de correções rápidas para restabelecer a integridade do pipeline. 

Não obstante, a assimetria com cauda longa é esperada devido a:
1. **Falhas intermitentes (*flaky tests*):** que podem demorar dias para serem diagnosticadas pelos mantenedores;
2. **Pausas de fim de semana:** episódios iniciados na sexta-feira à noite tendem a ser solucionados apenas na segunda-feira subsequente;
3. **Censura estatística:** branches ou workflows auxiliares que falham próximo ao término da janela anual e deixam de ser executados, evidenciando a necessidade imperativa de tratar a censura para evitar viés otimista na medição.

---

### RQ 05. Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?

#### Definição Operacional:
Avalia-se a associação monotônica entre a Frequência de Deploy (RQ 01, em releases/semana) e o Change Failure Rate (RQ 03, em ambas as variantes $\text{CFR}_{\text{CI}}$ e $\text{CFR}_{\text{Release}}$) mediante o cálculo do **Coeficiente de Correlação de Postos de Spearman ($\rho$)**, com reporte de $\rho$, p-valor e tamanho amostral $n$.

#### Hipótese H05 (Informal):
> **Esperamos encontrar uma correlação de Spearman fraca a moderada negativa ($\rho \in [-0.35, -0.10]$) ou próxima de zero ($|\rho| < 0.15$) com significância estatística, refutando a hipótese tradicional de compromisso (*trade-off*) entre velocidade e qualidade.**

#### Justificativa Teórica:
O dogma clássico de governança de TI sustentava que acelerar as entregas aumentaria fatalmente o risco de incidentes operacionais. O modelo DORA contestou essa visão demonstrando que deploys frequentes forçam as equipes a dominar práticas de entrega contínua, arquitetura desacoplada, automação de testes e pequenas alterações atômicas.

No ecossistema de software de código aberto, prevemos que projetos altamente ativos que publicam releases com frequência (como frameworks e ferramentas CLI populares) dispõem de comunidades mais densas, maior rigor em baterias de regressão e ferramentas automatizadas de linting e segurança. Assim, uma maior frequência de deploy não deteriora a estabilidade das releases; pelo contrário, tende a associar-se a processos de validação mais maduros, mantendo o CFR estável ou marginalmente inferior.

---

## 3. Considerações Metodológicas Iniciais
Para garantir a integridade da verificação experimental nas sprints subsequentes (Lab03S02 e Lab03S03), toda a extração de dados foi ancorada em um cliente HTTP customizado com tratamento determinístico de cabeçalhos de rate limit, cache persistente em SQLite e validação unitária por fixtures cobrindo casos extremos. As hipóteses aqui consolidadas servirão de referência para o confronto direto entre a expectativa teórica e os dados empíricos apurados.

---

## 4. Referências

1. FORSGREN, Nicole; HUMBLE, Jez; KIM, Gene. *Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations*. IT Revolution Press, 2018.
2. DORA. *Accelerate State of DevOps Report 2023 & 2024*. DevOps Research and Assessment, Google Cloud. Disponível em: <https://dora.dev/research/>.
3. WOHLIN, Claes et al. *Experimentation in Software Engineering*. Springer Science & Business Media, 2012.
4. ROMANO, Jeanine et al. *Appropriate statistics for ordinal level data: Should we really be using t-test and cohen's d for evaluating group differences on the NSSE and other surveys?*. Annual Meeting of the American Educational Research Association, 2006.
