# Metodologia: Definições Operacionais das Métricas DORA e Protocolo de Validação Humana

**Disciplina:** Laboratório de Experimentação de Software  
**Responsáveis:** Vinícius (definições operacionais e heurística de CFR(b)); Áulus (amostragem, concordância e revisão do protocolo de validação humana).

**Contexto:** Lab03 — Mineração de Métricas DORA (Lab03S03, incluindo pendências da Sprint 02). O trabalho de Áulus está relacionado às Issues #61 (sorteio), #70 (concordância e consenso), #62 (rotulagem independente), #63 (metodologia) e #59 (relatório compartilhado), verificadas no GitHub. A consulta de 20/10/2026 não encontrou Issues com o termo `Lab03S03`; os vínculos preservam os números existentes.

**Estado da validação humana:** pendente da amostra final obtida por coleta real, dos três arquivos independentes e do consenso documentado.

---

## 1. Introdução Metodológica

A mensuração empírica do desempenho de entrega de software no ecossistema de software de código aberto (*open-source software* — OSS) requer um arcabouço metodológico rigoroso. Como plataformas de desenvolvimento colaborativo como o GitHub não possuem marcações explícitas de eventos de "implantação em produção" (*production deployment*) ou "incidentes de produção" (*production outage*), a operacionalização das quatro métricas DORA consagradas (*Deployment Frequency*, *Lead Time for Changes*, *Change Failure Rate* e *Failed Deployment Recovery Time*) baseia-se na extração e agregação de **proxies operacionais**.

Esta seção detalha as **definições operacionais padronizadas**, os tratamentos de censura estatística e o **protocolo experimental de validação manual da amostra-ouro**. A concordância humana e o desempenho da heurística de identificação de releases corretivas para estimativa do Change Failure Rate ($\text{CFR}_b$) serão reportados somente quando suas entradas verificáveis estiverem completas.

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

Em conformidade com a Seção 6 do protocolo experimental, a avaliação de heurísticas automáticas requer um padrão de referência humano (*Gold Standard*). Os procedimentos abaixo constituem o protocolo a executar; sua descrição não afirma que a coleta ou a avaliação já tenham sido concluídas.

### 3.1 Estado das Entradas e Origem da Amostra Final

Na inspeção desta entrega, [`data/output/repositorios_aprovados.csv`](data/output/repositorios_aprovados.csv) contém **100 repositórios**, abaixo dos **300 repositórios aprovados** exigidos para a amostra final da Sprint 02. Esse CSV não inclui a procedência necessária para comprovar a coleta real de todas as linhas. A versão anterior de `gerar_amostra_rotulagem.py` continha uma lista fixa de projetos, releases e rótulos, além de completar históricos por modelos de texto; esses registros não constituem evidência de releases reais ou de julgamento humano.

O piloto anterior do novo coletor registra 100 candidatos consultados e zero aprovações comprovadas em `data/coleta_final/estado.json`. Esse resultado está limitado ao piloto e à evidência disponível, sem concluir ausência histórica de Actions nos projetos. Posteriormente, o ZIP da fonte histórica foi baixado integralmente (952.289.386 bytes) e seu MD5 publicado foi verificado. A recuperação comprovada pelo manifesto `data/historico_2024/proveniencia_historico.json` preservou 19.849 metadados, dos quais 32 possuem pelo menos 1.000 estrelas no snapshot; 15 repositórios forneceram pelo menos 50 runs válidos observados, totalizando 6.708 runs entre 01/01/2024 e 30/09/2024 UTC. Dois repositórios identificados sem arquivo de runs permanecem com histórico desconhecido, sem atribuição de zero execuções.

Essas contagens descrevem a fonte recuperada, com cobertura parcial da janela original. Não são aprovações finais: os metadados atuais, as releases e a população mínima de 300 repositórios ainda precisam ser comprovados. A qualificação da amostra final continua em curso; nenhum julgamento humano ou resultado anual DORA é inferido desses registros.

[`rotulos_vinicius.csv`](rotulos_vinicius.csv) permanece preservado como artefato preexistente. Sua presença e seu preenchimento, isoladamente, não comprovam avaliação independente da futura amostra comum. Ainda não há amostra-ouro humana verificável para reportar kappa, consenso ou desempenho empírico.

A população de entrada deverá resultar da coleta própria do grupo na API do GitHub, com funil de seleção registrado e pelo menos 300 repositórios aprovados pelos filtros: pelo menos 1.000 estrelas, cinco releases válidas e 50 execuções de workflows na janela, conforme [`config.yaml`](config.yaml). A coleta deverá preservar o CSV aprovado, as respostas reais de releases, a data de coleta, os critérios e a procedência vinculada aos arquivos por hashes. O contrato desses dados está documentado em [`AMOSTRA_OURO.md`](AMOSTRA_OURO.md). Dados de demonstração, `seed_data.py` e modo de referência não poderão completar essa população.

O novo [`coleta_amostra_real.py`](coleta_amostra_real.py) usa candidatos da API de busca e metadados e releases coletados pela API própria. Os runs reais poderão vir da API ou de uma exportação pública original, após verificar o arquivo integral e sua procedência. A fonte será registrada em `origem_metricas_estabilidade`, e a cobertura, em `escopo_contagem_runs`; registros de arquivo histórico serão identificados como `workflow_runs_arquivo_historico`, com limite inferior observado. Os nomes e IDs originais serão preservados e vinculados à identidade GitHub atual. As entradas finais serão preservadas em `data/coleta_final/`; os estados e descartes de uma execução parcial não constituem a amostra final aprovada. O preparo [`executar_amostra_ouro.py`](executar_amostra_ouro.py) somente produzirá a seleção e a cópia vazia de Áulus depois de validar os arquivos completos.

A disponibilidade histórica dos runs de 2023–2024 permanece uma limitação a verificar. A política de retenção passou a abranger esses metadados em 01/10/2026, com limite de 90 dias nos repositórios públicos. Uma resposta atual sem runs não comprova ausência histórica de CI; dados removidos exigem exportações históricas reais, sem mudança automática da janela. [GitHub Changelog](https://github.blog/changelog/2026-10-01-actions-retention-now-covers-checks-runs-and-statuses/).

O filtro de pelo menos 50 execuções poderá ser comprovado por 50 runs distintos observados dentro da janela, com `event=push`, default branch e conclusão de sucesso ou falha. Essa contagem é um limite inferior de elegibilidade, mesmo quando um arquivo histórico cobre apenas parte do ano; não é a contagem anual completa. Jobs e linhas de logs não serão convertidos em runs. Respostas vazias ou menos de 50 registros preservados serão tratadas como evidência histórica insuficiente, sem concluir ausência de Actions. CFR e recuperação anuais continuarão pendentes de cobertura verificável da janela inteira.

### 3.2 Desenho Amostral Reproduzível

O script [`gerar_amostra_rotulagem.py`](gerar_amostra_rotulagem.py) validará as entradas reais antes de produzir a seleção. Se faltarem os 300 repositórios aprovados ou as releases com procedência, a execução terminará indicando os dados necessários, sem gerar uma amostra substituta.

Após a validação, a população será ordenada por `full_name` e serão sorteados **60 repositórios**, sem reposição, usando `pandas.DataFrame.sample(n=60, random_state=42)`. Para cada repositório, as releases elegíveis serão ordenadas por `published_at` em UTC e, em caso de empate, por ID. Sobre cada uma dessas listas será aplicado `sample(n=5, random_state=42)`, sem reposição, selecionando **cinco releases reais** da janela de 01/10/2023 a 30/09/2024 UTC, excluindo drafts e pré-releases. A mesma semente será usada em cada sorteio, sem depender da ordem de processamento dos repositórios. Essa ordenação permitirá reproduzir a seleção mesmo que o CSV ou a resposta da API esteja em outra ordem.

Serão preservados `amostra_comum.csv`, `evidencias_releases.json` (conteúdo original das releases selecionadas) e `selecao.json` (semente, algoritmo, versões de Python e pandas, janela, hashes das entradas e saídas e identificadores selecionados). Quando houver release anterior elegível na janela, `previous_tag` e o link de comparação representarão essa predecessora cronológica, e não apenas a release anterior dentre as cinco sorteadas. Para a primeira release elegível, o link aponta para o histórico de commits da tag; esse histórico não delimita sozinho o intervalo de mudanças, e o avaliador deverá consultar a história anterior quando necessário, registrando a limitação.

A amostra comum terá **300 linhas de releases, distribuídas em 60 repositórios com cinco releases cada**. Cada linha conterá o identificador do repositório e da release, tag, data de publicação, link direto, referência às notas e referência aos commits. Esses dados permitem consultar as fontes originais. A seleção ainda não será um padrão de referência humano: todos os campos de julgamento começarão vazios e se tornarão rótulos de referência apenas após a avaliação e o consenso.

### 3.3 Dimensões, Fontes e Unidade de Julgamento

| Dimensão | Unidade | Categorias permitidas | Fontes e critério de avaliação |
|---|---|---|---|
| `tipo_projeto` | Repositório (60 unidades) | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` | Descrição, README e documentação oficial do projeto, confrontados com o produto disponibilizado nas releases. |
| `entrega_real` | Repositório (60 unidades) | `sim`, `não`, `incerto` | Notas das cinco releases, artefatos publicados e documentação de distribuição: avaliar se as releases representam entregas funcionais aos usuários do projeto, inclusive consumidores de bibliotecas. |
| `corretiva` | Release (300 unidades) | `sim`, `não` | Notas da release e commits associados: avaliar se o objetivo predominante é corrigir defeitos, regressões ou vulnerabilidades, registrando a evidência consultada. O incremento de patch, sozinho, não determina o julgamento humano. |

O avaliador preencherá `justificativa` e `evidencia` com a razão da decisão e links, SHAs ou trechos identificáveis das fontes. Dificuldades de acesso ou evidência ambígua serão registradas para discussão; não se inventarão notas ou commits. `tipo_projeto` e `entrega_real` deverão se repetir com o mesmo valor nas cinco linhas do repositório. Essa repetição organiza o CSV e não amplia essas dimensões para 300 unidades estatísticas.

### 3.4 Cegamento e Rotulagem Independente

Áulus, Maria e Vinícius receberão o mesmo arquivo de referência, contendo somente metadados e fontes, sem previsões da heurística nem rótulos de outro integrante. Cada integrante preencherá sua cópia individual (`rotulos_aulus.csv`, `rotulos_maria.csv` e, para preservar o artefato antigo, `rotulos_vinicius_independente.csv`), sem consultar as classificações dos demais e sem discutir casos antes de concluir sua avaliação. A geração de cópias não atribuirá decisões automaticamente. O arquivo preexistente `rotulos_vinicius.csv` não será sobrescrito.

As versões concluídas serão preservadas antes da reunião, com seus hashes, para manter os julgamentos independentes usados na concordância. O cegamento é uma regra de execução a ser documentada pelo grupo; o código não comprova por si só que ela foi cumprida. A Issue #62 permanecerá pendente de julgamento humano até Áulus completar e validar seu arquivo.

### 3.5 Concordância: Três Kappas de Fleiss

O módulo [`metricas/concordancia.py`](metricas/concordancia.py) validará que os três avaliadores classificaram exatamente as mesmas unidades da amostra comum, sem duplicatas, ausências, categorias inválidas ou inconsistências nas duas dimensões do repositório. Serão calculados três kappas de Fleiss sobre os rótulos **independentes anteriores ao consenso**, usando `aggregate_raters` seguido de `fleiss_kappa`, ambos de `statsmodels.stats.inter_rater`.

Para cada dimensão, a matriz de entrada terá uma linha por unidade e três colunas, uma por avaliador. As categorias serão codificadas de maneira comum aos três arquivos. `tipo_projeto` e `entrega_real` usarão uma unidade por repositório, sem contar cinco vezes o mesmo julgamento; `corretiva` usará uma unidade por release. A tabela abaixo é um modelo de apresentação, com tamanhos planejados. Os valores observados só serão inseridos depois que os três arquivos humanos e o consenso estiverem completos e validados. Se a distribuição de categorias tornar kappa matematicamente indefinido, isso será relatado explicitamente, sem atribuir concordância perfeita.

| Dimensão | n planejado | n validado | Avaliadores por unidade | Categorias | Kappa de Fleiss |
|---|---:|---|---:|---|---|
| Tipo de projeto | 60 repositórios | Pendente | 3 | 4: biblioteca/framework; aplicação/serviço; ferramenta CLI; outro | Pendente |
| Entrega real ao usuário | 60 repositórios | Pendente | 3 | 3: sim; não; incerto | Pendente |
| Release corretiva | 300 releases | Pendente | 3 | 2: sim; não | Pendente |

### 3.6 Reunião, Desempate e Registro do Consenso

Depois de concluídas as três avaliações independentes, o grupo gerará um relatório de divergências e uma estrutura de consenso com **420 decisões vazias** (60 de tipo, 60 de entrega e 300 de corretiva). Na reunião, os três revisarão as fontes de cada divergência e registrarão uma decisão por unidade e dimensão. Mesmo unidades com concordância inicial serão conferidas e registradas na estrutura de consenso; os rótulos individuais permanecerão preservados.

O protocolo adotará maioria simples **após a discussão**. A maioria inicial não será convertida automaticamente em consenso. Nos casos 1-1-1 das dimensões com mais de duas categorias, os três discutirão os critérios e as evidências até tomar uma decisão conjunta. Se não houver decisão, o caso permanecerá pendente e impedirá a publicação dos resultados finais. Na dimensão binária de release corretiva, qualquer divergência será discutida antes de confirmar o rótulo final.

Cada decisão registrará o rótulo de consenso, a justificativa, a evidência, os participantes e a data da reunião. Divergências serão vinculadas aos respectivos julgamentos individuais. Nenhum script preencherá essas decisões como se a reunião tivesse ocorrido. O cálculo final exigirá os três arquivos independentes completos e um consenso completo, consistente com o protocolo de desempate.

---

## 4. Avaliação Planejada da Heurística de Releases Corretivas

A identificação automática de uma release corretiva é o componente central para a Variante (b) do CFR e para a taxa de retrabalho. A meta de **$F1 \ge 0{,}70$** deverá ser avaliada frente ao consenso humano verificável, após o procedimento da Seção 3. A existência de [`benchmark_heuristica.py`](benchmark_heuristica.py) não comprova que essa meta foi atingida.

### 4.1 Especificação Técnica das Versões da Heurística

1. **Heurística v1 (Baseline — SemVer Estrito):**
   - Regra: Considera corretiva apenas se as tags seguirem o padrão SemVer estrito `MAJOR.MINOR.PATCH` e somente o dígito de patch for estritamente superior ao da release anterior ($M_c = M_p$, $m_c = m_p$, $p_c > p_p$).
   - Limitação: Falha ao lidar com repositórios que não usam 3 dígitos (ex.: `v1.2 -> v1.2.1`), sufixos como `.post`, `-patch`, ou projetos orientados a datas/calendário (CalVer).

2. **Heurística v2 (Sprint 01 — SemVer Básico + Palavras-Chave Simples):**
   - Regra: SemVer básico acrescido da presença de palavras-chave genéricas nos commits: `\bfix\b`, `\bhotfix\b`, `\brevert\b`, `\bbugfix\b`.
   - Limitação potencial: Palavras genéricas podem produzir falsos positivos em alterações cosméticas de documentação (`fix typo in README`, `fix linter`). A frequência desses erros deverá ser medida diante do consenso humano.

3. **Heurística v3 (Refinada — Conforme Implementada em `calculo_metricas.py`):**
   - **SemVer Flexível:** Suporte a tags com prefixos heterogêneos (`v`, `release-`), sufixos de patch explícitos (`.post`, `-patch`, `-hotfix`, `-p1`), e transições de granularidade (ex.: `1.2` para `1.2.1`);
   - **Conventional Commits & Padrões Técnicos:** Reconhecimento formal de `^fix(\([^\)]+\))?(\!)?:`, `bugfix:`, `revert:`, CVEs (`CVE-\d{4}-\d+`), termos de vulnerabilidade e fechamento de issues (`closes #\d+`, `fixes #\d+`);
   - **Filtro de Ruído Cosmético:** Exclusão deliberada de commits que apenas contenham termos de documentação ou estilo (`fix typo`, `fix formatting`, `fix readme`), a menos que acompanhados de correções funcionais de software;
   - **Inspeção de Release Notes:** Avaliação do corpo textual da release para seções estruturadas como `## Bug Fixes`, `### Patches` e `Security Release`.

---

### 4.2 Estado da Evidência e Protocolo de Benchmark

As tabelas anteriores de matriz de confusão, precisão, recall e F1 foram retiradas desta metodologia porque os registros disponíveis não comprovam uma referência formada por três avaliações independentes e consenso. Um F1 calculado sobre rótulos preenchidos pelo próprio código mede apenas a relação entre regras e dados construídos; não é validação humana e não sustenta conclusão de desempenho empírico. Os relatórios de benchmark preexistentes também não serão usados como resultados humanos sem essa comprovação.

Quando a amostra real, os três arquivos individuais e o consenso estiverem completos, as previsões das versões da heurística serão alinhadas pelos identificadores das mesmas 300 releases ao rótulo `corretiva` do consenso. Será calculada a matriz de confusão e serão reportados precisão, recall e F1 com `precision_recall_fscore_support`, registrando versões do código e hashes das entradas. Ausências ou desalinhamentos deverão interromper a avaliação. A meta de F1 e as hipóteses sobre os filtros permanecerão **pendentes de verificação**, e cada refinamento deverá registrar quais dados foram usados na calibração para discutir possível sobreajuste.

---

## 5. Ameaças à Validade Metodológica

1. **Validade de Construto:** Releases e tags não refletem necessariamente o deploy em produção. O julgamento de entrega real e a leitura das fontes deverão indicar limites do uso de release como proxy; isso ainda não foi verificado nesta amostra.
2. **Validade Interna:** Squashing e rebasing podem condensar mensagens de commits e ocultar termos corretivos. O protocolo exige inspeção complementar de notas e commits, e cegamento às previsões e às decisões dos demais. Sua execução deverá ser documentada; os arquivos sozinhos não comprovam a independência dos avaliadores.
3. **Validade Externa:** Os filtros de popularidade, GitHub Actions e volume de releases restringem a população. As conclusões futuras serão limitadas aos repositórios elegíveis e à janela estudada, sem generalização automática para projetos corporativos ou para todo OSS.
4. **Validade de Conclusão:** As cinco releases de cada repositório são agrupadas, enquanto tipo de projeto e entrega real possuem somente 60 unidades. A concordância será calculada com essa distinção e a distribuição das categorias será registrada. Mediana e IQR serão usados para descrever métricas, sem tratar fixtures ou dados de demonstração como observações empíricas. A calibração e a avaliação na mesma amostra deverão ser reconhecidas como fonte de otimismo no F1.

---

## 6. Conclusão

As definições em [`metricas/calculo_metricas.py`](metricas/calculo_metricas.py) e o protocolo de amostragem, rotulagem, concordância e consenso fornecem uma estrutura para a validação. A base empírica permanece pendente: é necessário obter e comprovar a amostra final de pelo menos 300 repositórios reais, executar a seleção comum, concluir as avaliações de Áulus, Maria e Vinícius e registrar o consenso da reunião. Até então, não há kappa humano, F1 validado por humanos ou conclusão de desempenho a apresentar como resultado.

## 7. Execução e resultados de RQ01–RQ04 na Sprint 03

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

### 7.1 Auditoria da amostra e concordância antes do consenso

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
