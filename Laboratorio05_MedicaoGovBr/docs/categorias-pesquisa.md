# As 7 categorias da pesquisa (revisadas na Sprint 3)

A classificação original está na seção 5 de [`proposta.md`](proposta.md). Aqui ela é revisada contra o que foi de fato feito na coleta (25/11/2026) e na análise. Onde a execução mudou o plano, a linha diz o que mudou.

## 1. Classificação

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Pesquisa aplicada | O estudo produz conhecimento sobre serviços digitais específicos, em produção, com uso prático para quem os mantém (onde o carregamento é lento) e para quem os avalia (quanto o mobile perde). Não busca uma teoria geral de desempenho de sites. |
| Objetivos | Descritivo, com um componente exploratório | Descreve desempenho e acessibilidade por serviço e as diferenças e associações das RQ1 a RQ3. A RQ2 é exploratória: o estudo não tem hipótese causal nem como testá-la, porque não observa código nem infraestrutura dos serviços. A estimativa de impacto é um modelo, não um objetivo explicativo. |
| Abordagem | Quantitativa | Toda variável de resposta é numérica e vem de um instrumento (Lighthouse 13.6.0). A análise usa estatística descritiva, testes de hipótese não paramétricos e tamanhos de efeito. Não há dado qualitativo. |
| Procedimentos | Estudo de medição em campo, observacional; só a RQ3 tem componente quase-experimental | RQ1 e RQ2: os serviços são observados como estão, sem manipulação. RQ3: o pesquisador manipula o form factor (mobile e desktop) e sorteia a ordem das execuções, mas os objetos (serviços) não foram sorteados nem controlados. Por isso é quase-experimento, não experimento controlado. |
| Tempo | Transversal | Uma janela curta, em um só dia (25/11/2026), em duas sessões (manhã, 11:38 a 12:14; tarde, 15:01 a 15:39). As 10 execuções de cada célula são réplicas da mesma medição, não uma série temporal. O estudo não diz nada sobre como o desempenho muda ao longo de dias ou semanas. |
| Controle | Parcial | Controlado: máquina, versões do Lighthouse (13.6.0) e do Chrome (158.0.8127.37), configuração, perfil de navegador limpo a cada execução, pausa mínima de 10 s e ordem aleatória com seed registrada (3118576651). Não controlado: servidor, CDN, conteúdo, carga do serviço no momento e a rede entre a máquina e o serviço. |
| Nível de evidência | Baixo a moderado | Estudo primário, sem replicação independente, sem grupo controle sorteado e com dez páginas escolhidas por conveniência. Fica abaixo de experimentos controlados e de revisões sistemáticas nas hierarquias de evidência usadas em Engenharia de Software (adaptadas da medicina; Kitchenham, 2004). Vale para estas URLs, nesta janela de tempo e nestas condições de emulação. |

## 2. O que mudou entre a proposta e a execução

| Item | Proposta (Sprint 1) | Execução (Sprint 2) | Efeito na classificação |
|---|---|---|---|
| Execuções por célula | 12 | 10 | Nenhum; o poder dos testes é o mesmo na prática (n = 10 serviços nas RQ2 e RQ3). |
| Blocos de horário | 3 (manhã, tarde, noite) | 2 (manhã e tarde) | Tempo continua transversal, mas a cobertura do dia é menor: sem noite. Controle parcial, e o efeito de horário só foi testado em um dia. |
| Fases | Uma por bloco | Uma fase `full`, com plano e seed salvos | Mais controle sobre a ordem; nenhuma mudança de categoria. |
| Falhas | Só em `run-metadata.json` | Em `data/failed-runs.csv`, com motivo; 5 tentativas inválidas de 205 | Nenhuma. Todas do Consumidor.gov.br (`NO_FCP`) e todas refeitas. |
| Impacto | Fora do escopo da Sprint 2 | Modelo de horas por mês ([`impacto.md`](impacto.md)) | O modelo é uma extrapolação com premissas, não uma medição, e não muda o nível de evidência do que foi medido. |

## 3. Por que não é um experimento controlado

Um experimento controlado exigiria atribuir os tratamentos aos objetos de forma aleatória e controlar as variáveis que não são o tratamento. Aqui:

- Os serviços não foram sorteados (escolha por conveniência e por critérios de viabilidade; quatro candidatas saíram por bloqueio ou `robots.txt`, ver [`url-changes.md`](url-changes.md)). O efeito de "ser um serviço" não pode ser separado do que cada serviço é: equipe, plataforma e conteúdo.
- O servidor, a CDN e a rede até o serviço não são controlados. O Chrome começa sem cache a cada execução, mas o cache da CDN não é do pesquisador.
- Só o form factor é manipulado, e ele é manipulado por um preset do Lighthouse (emulação e throttling), não por um dispositivo real.

Por isso as conclusões das RQ1 e RQ2 são de associação e descrição, e a da RQ3 é de comparação entre dois presets do mesmo instrumento.

## 4. Força da evidência por pergunta

| Pergunta | Tipo | O que a evidência sustenta |
|---|---|---|
| RQ1 (serviços diferem?) | Observacional | Que estas 10 páginas diferem muito no LCP e no performance score. Não diz que serviços do governo em geral diferem. |
| RQ2 (desempenho e acessibilidade) | Observacional, exploratória | Nada além de "inconclusivo": n = 10 serviços, IC 95% do ρ cruzando o zero. |
| RQ3 (mobile contra desktop) | Quase-experimental | Que, no Lighthouse, o preset mobile dá LCP maior em todos os 10 serviços. Não diz que celulares reais sofrem o mesmo. |
| Impacto | Modelo | Uma ordem de grandeza para 3 serviços, sob 7 premissas ([`impacto.md`](impacto.md), seção 4). |

## 5. Referências

- Basili, V. R.; Caldiera, G.; Rombach, H. D. (1994). The Goal Question Metric Approach. In: *Encyclopedia of Software Engineering*. Wiley.
- Kitchenham, B. (2004). *Procedures for Performing Systematic Reviews*. Keele University, TR/SE-0401.
- Wohlin, C. et al. (2012). *Experimentation in Software Engineering*. Springer.
