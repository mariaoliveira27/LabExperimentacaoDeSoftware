# Mineração de Métricas DORA em Repositórios Open-Source: Introdução e Hipóteses de Pesquisa

**Disciplina:** Laboratório de Experimentação de Software  
**Integrantes:** Vinícius Simões (*Definições Operacionais, CFR(b) e RQ07*), Maria Clara Gomes (*Seleção, Infraestrutura e Integração*), Áulus H. Z. Pinto (*Amostragem, Concordância e Validação Humana*)  
**Contexto:** Lab03 — Mineração de Métricas DORA (Sprint 03 / Lab03S03 — Consolidação de Hipóteses)  

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

Antes da inspeção dos resultados finais da Sprint 03, formulamos hipóteses informais para as sete Questões de Pesquisa da disciplina:

---

### RQ 01. Qual a frequência de deploys dos repositórios populares que usam CI/CD?

#### Definição Operacional:
Número de releases publicadas no default branch divididas pelas 52,14 semanas da janela anual de observação.

#### Hipótese H01 (Informal):
> **Esperamos que a maioria dos repositórios populares de código aberto apresente uma frequência de deploy enquadrada predominantemente nos patamares Medium e High (entre uma release por mês e uma release por semana, ou seja, 0,23 a 1 release/semana), com raríssimos projetos no patamar Elite ($\ge 7$ releases/semana).**

#### Justificativa Teórica:
Ao contrário de serviços SaaS internos que realizam múltiplos deploys contínuos por dia, releases em projetos open-source dependem de ciclos de empacotamento, testes comunitários e geração de changelogs, resultando em uma cadência mais espaçada e deliberada.

---

### RQ 02. Qual o tempo entre um commit e seu respectivo deploy?

#### Definição Operacional das Variantes:
- **Variante (a) [por release]:** Mediana do tempo decorrido entre o commit mais antigo pertencente à release e a publicação da release.
- **Variante (b) [por commit]:** Mediana agregada do lead time de todos os commits atômicos de todas as releases da janela.

#### Hipótese H02 (Informal):
> **Esperamos que o Lead Time da Variante (a) seja substancialmente superior ao da Variante (b) (frequentemente situando-se no patamar Low, $\ge 30$ dias), enquanto a Variante (b) se situará nos patamares High e Medium (entre 1 e 7 dias, ou 7 e 30 dias).**

#### Justificativa Teórica:
A Variante (a) é fortemente penalizada por branches de longa duração ou commits antigos que ficaram pendentes antes da mesclagem, fazendo o lead time da release explodir. A Variante (b) atenua essa distorção e representa de modo mais fiel o tempo de ciclo das modificações cotidianas dos desenvolvedores.

---

### RQ 03. Qual a taxa de falha das mudanças entregues por esses repositórios?

#### Definição Operacional das Variantes:
- **Variante (a) — Proxy de CI:** $\text{CFR}_{\text{CI}} = \text{Runs com Falha} / (\text{Runs com Falha} + \text{Runs com Sucesso})$.
- **Variante (b) — Proxy de Entrega (Releases):** Uma release $R$ é classificada como falha se for sucedida em até 7 dias corridos por uma release corretiva (com censura nos últimos 7 dias da janela).

#### Hipótese H03 (Informal):
> **Esperamos que a taxa de falha medida pelo proxy de CI ($\text{CFR}_{\text{CI}}$) seja substancialmente superior à taxa de falha medida pelo proxy de releases corretivas ($\text{CFR}_{\text{Release}}$). Estimamos que a mediana de $\text{CFR}_{\text{CI}}$ se situará na faixa de 15% a 30% (categorias High a Medium), enquanto o $\text{CFR}_{\text{Release}}$ apresentará mediana inferior a 10% (categoria Elite).**

#### Justificativa Teórica:
A esteira automatizada de CI atua como uma rede de contenção rápida (*fail-fast*), capturando quebras antes do empacotamento público. As releases oficiais passam por filtros humanos adicionais, de forma que apenas uma fração reduzida necessita de hotfix imediato em até uma semana.

---

### RQ 04. Qual o tempo de recuperação após uma execução de CI/CD com falha?

#### Definição Operacional:
Intervalo entre a primeira falha de um workflow e o término da próxima execução bem-sucedida do mesmo workflow no default branch, tratando episódios não concluídos como censurados.

#### Hipótese H04 (Informal):
> **Esperamos que a mediana do tempo de recuperação dos episódios de falha de CI seja inferior a 24 horas (patamares High ou Elite), porém com distribuição fortemente assimétrica e presença de episódios censurados.**

#### Justificativa Teórica:
Em projetos populares, um branch principal quebrado bloqueia o rebase de pull requests de outros colaboradores, incentivando reversões imediatas (*git revert*) ou correções prioritárias pelos mantenedores.

---

### RQ 05. Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?

#### Definição Operacional:
Coeficiente de correlação de postos de Spearman ($\rho$) entre Frequência de Deploy e CFR (em ambas as variantes), acompanhado de p-valor e intervalo de confiança.

#### Hipótese H05 (Informal):
> **Esperamos encontrar uma correlação de Spearman fraca ou próxima de zero ($|\rho| < 0{,}15$), refutando o dogma tradicional de compromisso (*trade-off*) entre velocidade e estabilidade.**

#### Justificativa Teórica:
Segundo o modelo DORA, deploys mais frequentes forçam as equipes a adotar automação de testes mais rigorosa e lotes menores de código, mantendo ou melhorando a estabilidade da entrega.

---

### RQ 06. Quais características dos repositórios estão associadas a um melhor desempenho DORA?

#### Definição Operacional:
Comparação das quatro métricas DORA por subgrupos (estrelas, contribuidores, idade, linguagem e tipo de projeto) utilizando testes de Kruskal-Wallis, pós-teste com correção de Holm e tamanho de efeito pelo delta de Cliff ($\delta$) e epsilon-quadrado ($\epsilon^2$).

#### Hipótese H06 (Informal):
> **Esperamos que o tamanho da comunidade (estrelas e contribuidores) apresente associação positiva de grande magnitude com a Frequência de Deploy e Lead Time, mas pouco impacto no Change Failure Rate. Além disso, esperamos variações nos tempos de ciclo entre ecossistemas de linguagens, refletindo complexidades distintas de compilação e teste.**

#### Justificativa Teórica:
Comunidades maiores e com mais contribuidores ativos têm maior capacidade operacional de publicar versões com agilidade. Por outro lado, a estabilidade das entregas depende primariamente da disciplina de testes e processos de revisão, e não puramente do volume de estrelas.

---

### RQ 07. O quanto a classificação DORA de um repositório depende da definição operacional escolhida?

#### Definição Operacional:
Classificação dos repositórios nas quatro categorias DORA (Elite, High, Medium, Low) sob três combinações operacionais (C1: Referência, C2: Pré-releases, C3: Tags), avaliando percentual de migração de patamar e o Kappa de Cohen ponderado linearmente entre os pares.

#### Hipótese H07 (Informal):
> **Esperamos que a variação das definições operacionais gere uma taxa de mudança de patamar moderada (entre 30% e 45% dos repositórios migrando de categoria), com Kappa linear entre 0,25 e 0,40 (concordância razoável), porém sem nenhuma transição extrema (ex.: Elite para Low), indicando que a classificação DORA consolidada é metodologicamente estável.**

#### Justificativa Teórica:
O uso de pré-releases e tags reduz drasticamente o Lead Time computado pela Variante (b), promovendo repositórios do patamar Medium para High. Contudo, como a maturidade DORA é calculada pela mediana dos quatro escores, variações atômicas em uma única métrica são atenuadas no resultado consolidado.

---

## 3. Considerações Metodológicas
Para garantir a reprodutibilidade estrita, toda a extração de dados e análises foram ancoradas em um pipeline modular com fixtures e testes unitários. As hipóteses aqui documentadas servem de referência prévia para o confronto direto com os achados empíricos.

---

## 4. Referências

1. FORSGREN, Nicole; HUMBLE, Jez; KIM, Gene. *Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations*. IT Revolution Press, 2018.
2. DORA. *Accelerate State of DevOps Report 2023 & 2024*. DevOps Research and Assessment, Google Cloud. Disponível em: <https://dora.dev/research/>.
3. WOHLIN, Claes et al. *Experimentation in Software Engineering*. Springer Science & Business Media, 2012.
4. ROMANO, Jeanine et al. *Appropriate statistics for ordinal level data: Should we really be using t-test and cohen's d for evaluating group differences on the NSSE and other surveys?*. Annual Meeting of the American Educational Research Association, 2006.
5. LANDIS, J. Richard; KOCH, Gary G. *The measurement of observer agreement for categorical data*. Biometrics, 1977.
