# Ameaças à validade

Classificação de Wohlin et al. (2012). Cada ameaça traz o que foi feito contra ela na coleta e na análise (25/11/2026) e, quando a mitigação não resolve, a limitação que fica. A versão resumida está na seção 8 de [`proposta.md`](proposta.md); este arquivo é a versão final, com os resultados das verificações. Os números vêm de [`analysis/results.md`](../analysis/results.md) e de [`data-validation.md`](data-validation.md).

Resumo da situação: das 29 ameaças abaixo, 10 foram mitigadas por algo que está nos dados ou no código, 12 têm mitigação parcial e 7 ficam como limitação declarada.

## 1. Validade de conclusão

| Ameaça | O que foi feito | Situação |
|---|---|---|
| **Poucos serviços (n = 10)** nas RQ2 e RQ3: pouco poder para correlações e diferenças moderadas. | Tamanho de efeito e intervalo ao lado do p. RQ2 ficou inconclusiva (ρ = 0,41 e 0,48; IC 95% de cerca de −0,3 a 0,9), e foi lida assim, não como "sem relação". | Parcial: o n não muda. |
| **Pseudo-replicação**: as 10 execuções de um serviço não são 10 serviços. O Kruskal–Wallis da RQ1 dá ε² de 0,85 a 0,96 porque as repetições de uma mesma página variam pouco (o IQR do LCP é de 0,01 a 2,5 s). O teste mostra que **estas páginas** diferem entre si, e não que serviços do governo em geral diferem. | RQ2 e RQ3 usam a mediana por serviço como unidade principal. Na RQ2, o p da versão com 100 execuções (< 0,001) não é usado para concluir, e o IC por cluster, que reamostra serviços inteiros, cruza o zero. A inferência é declarada como sobre estas URLs. | Mitigada para RQ2 e RQ3; limitação para RQ1. |
| **Múltiplos testes** (4 na RQ1, 2 na RQ2, 2 na RQ3, mais os pares do Dunn). | Correção de Holm dentro de cada RQ e, no Dunn, dentro de cada família de 45 pares. | Mitigada. |
| **Empates no accessibility score**: 18 dos 20 grupos (serviço × form factor) têm score constante. | τ-b de Kendall ao lado do ρ de Spearman. O score quase não discrimina, o que limita a RQ2 por construção. | Parcial. |
| **Normalidade**: Shapiro–Wilk com n = 10 por grupo tem pouco poder. | Os testes são não paramétricos desde o plano, por causa da escala (scores ordinais) e da assimetria dos tempos. O Shapiro–Wilk só documenta a escolha. | Mitigada. |
| **Outliers**: 105 valores fora da cerca de Tukey, em 60 das 200 execuções. | Nenhum foi removido. A análise sai com todas as execuções e sem os valores marcados; nenhuma conclusão muda (`results.md`, seção 9.3). | Mitigada. |
| **Piso do Wilcoxon com n = 10**: o menor p bilateral possível é 2/2¹⁰ ≈ 0,002 (0,004 com Holm). | Declarado. O LCP chega a esse piso (10 de 10 serviços com mobile mais lento). Por isso o tamanho do efeito (rank-biserial = 1,00) pesa mais que o p. | Mitigada. |

## 2. Validade interna

| Ameaça | O que foi feito | Situação |
|---|---|---|
| **Horário**: a carga do servidor e da rede muda ao longo do dia. | Dois blocos, manhã (11:38 a 12:14) e tarde (15:01 a 15:39), cinco réplicas de cada célula em cada bloco, ordem aleatória dentro do bloco, rótulo de horário gravado em cada execução. Mann–Whitney por serviço × form factor × métrica entre os blocos: 40 comparações, nenhuma com p (Holm) < 0,05 (menor p = 0,968). A maior diferença de LCP entre os blocos é 1,32 s (ENEM mobile). | Parcial. **Não há bloco à noite** e os dois blocos são do mesmo dia. Com 5 execuções por bloco o teste tem pouco poder: o resultado indica estabilidade neste dia, não ausência de efeito de horário. |
| **Cache e CDN**: o cache do Chrome começa vazio, mas o da CDN e do servidor não é controlado. | `run` e o rótulo do bloco gravados; comparação da primeira réplica de cada bloco com as demais (`first_run_vs_rest.csv`). Não há padrão de "primeira execução mais lenta". O único caso grande é o Meu INSS mobile (+39%), por uma execução de 27,0 s que também é outlier de Tukey. | Parcial. |
| **Bloqueio por WAF ou anti-bot**: o Lighthouse pontua a página de desafio como se fosse o serviço. Aconteceu no piloto (Portal da Transparência: 4 de 6 execuções com CAPTCHA do AWS WAF). | Duas regras em cada execução: HTTP 200 no documento principal e texto do elemento LCP que não seja mensagem de desafio. Sinais secundários (queda no DOM, troca de host, recursos de CAPTCHA) vão para `full_flags.csv`. Na coleta completa não houve nenhum bloqueio. O Portal da Transparência foi trocado. | Mitigada. |
| **Métrica nula**: execuções em que a página não pintou nada (`NO_FCP`) deixam as métricas vazias. Aconteceu 5 vezes de 205 tentativas, todas no Consumidor.gov.br. | Execução inválida (`MISSING_VALUES`), movida para `data/raw/full/invalid/`, registrada em `data/failed-runs.csv` e refeita. A checagem de métrica nula entrou no script depois da sessão da manhã: as duas execuções nulas da manhã só foram achadas ao retomar, à tarde (status `invalid-found-on-resume`). Os dados válidos não são afetados: a validação confere 200 de 200 execuções, 0 erros. | Mitigada. A contagem de réplicas do Consumidor.gov.br fica desbalanceada entre os blocos (4 de manhã e 6 à tarde). |
| **Carga da máquina de medição.** | Um processo por vez. `benchmarkIndex` gravado em cada execução; critério de exclusão `SLOW_HOST_CPU` (≤ 1000), que não excluiu nenhuma execução. Duas execuções com `BENCHMARK_LOW_OUTLIER` (Consumidor.gov.br mobile #5 e Carteira de Trabalho Digital mobile #3) foram mantidas, porque a marcação é só para revisão. Plano de energia e adaptador de rede gravados por sessão. | Mitigada. |
| **Conteúdo muda durante a coleta** (banners, campanhas, deploys). | O elemento LCP, a contagem de requisições e os bytes ficam gravados em cada execução. O elemento LCP foi o mesmo em 10 de 10 execuções de cada célula. A coleta foi curta: das 11:38 às 15:39 do mesmo dia. | Parcial. |
| **User-Agent emulado diferente da versão real**: o preset do Lighthouse envia Chrome/136; o navegador era o Chrome 158.0.8127.37. | Registrado; é o padrão do Lighthouse e igual para todos os serviços. | Limitação. |
| **Ordem das execuções.** | Ordem aleatória com seed fixa (3118576651), gravada em `data/raw/full/plan.json`. | Mitigada. |

## 3. Validade de construto

| Ameaça | O que foi feito | Situação |
|---|---|---|
| **Throttling simulado.** No modo `simulate`, LCP, FCP, Speed Index e TBT são estimativas do modelo do Lighthouse a partir de um carregamento sem limitação, não tempos observados. O próprio Lighthouse diz que esse modo não resolve a variabilidade do servidor nem o não determinismo da página. | Mesmo método em todas as execuções; métricas declaradas como derivadas; os números não são comparados com dados de campo (CrUX) como se fossem a mesma coisa. | Limitação. |
| **Performance score é uma métrica composta (Goodhart).** É uma média ponderada de curvas escolhidas pelo Lighthouse, e muitas vezes vira meta. Uma medida que vira meta deixa de ser uma boa medida: a página pode subir de score sem melhorar para quem a usa. Pesos e curvas mudam entre versões. | Versão fixa (13.6.0). O LCP, em milissegundos, é a medida principal na RQ3 e vem ao lado do score na RQ1. As métricas componentes estão na descritiva (apêndice A de `results.md`). | Parcial. Exemplo: o Valores a Receber tem mediana 1 no score mobile, e isso diz menos que seus 13,4 s de LCP. |
| **O que o Lighthouse não mede (falácia de McNamara).** Ele não mede o tempo até a pessoa conseguir fazer a tarefa, nem interatividade real, nem a qualidade do conteúdo. O que é fácil de medir (LCP, score) pode não ser o que importa. | Declarado. As conclusões falam de "carregamento da página de entrada", não de "qualidade do serviço". | Limitação. |
| **O elemento LCP nem sempre é o conteúdo principal.** O LCP do Portal gov.br (mobile e desktop) e do Valores a Receber (mobile) é o banner de cookies. No Meu SUS Digital mobile é uma imagem de "estado vazio" da SPA, e no Meu INSS é o aviso "INSS no ar". | O elemento LCP de cada execução está em `full_lcp_elements.csv`. O banner não foi clicado, porque isso mudaria o construto "primeira visita". Sensibilidade sem Portal gov.br e Valores a Receber (`analysis/check_results.py`): Kruskal–Wallis continua com p < 0,001 e ε² de 0,83 a 0,97; ρ de Spearman de 0,37 (mobile) e 0,39 (desktop) com n = 8 (continua inconclusivo); LCP mobile maior em 8 de 8 serviços. Nenhuma conclusão muda. **TODO:** gerar as tabelas oficiais com `analyze.py --exclude-services govbr,svr-bcb`; o cálculo acima é uma conferência independente. | Mitigada. |
| **Accessibility score cobre só regras automáticas (axe-core).** Não mede acessibilidade completa nem uso com tecnologia assistiva. | Lido como "acessibilidade verificável automaticamente"; sem generalizar para conformidade com a WCAG. | Limitação. |
| **Uma página por serviço (mono-operação).** A página de entrada não representa as demais telas. Quatro das dez são telas anteriores ao login (Meu INSS, Carteira de Trabalho Digital, Meu SUS Digital e e-CAC). | O objeto é declarado como "página de entrada". Nada é dito sobre o serviço depois do login. | Limitação. |
| **Redirecionamento do Consumidor.gov.br.** A página inicial redireciona no cliente para `/pages/principal/?<número>`; o Lighthouse mede a página final. | Registrado em [`url-changes.md`](url-changes.md); a URL pedida é mantida. | Parcial. |

## 4. Validade externa

| Ameaça | O que foi feito | Situação |
|---|---|---|
| **Emulação contra dispositivo real.** O mobile é um Moto G Power emulado em um desktop Ryzen 5 5500, com CPU 4× mais lenta e rede simulada. Celulares reais, redes 3G ou 4G instáveis e navegadores diferentes podem dar resultados piores ou só diferentes. | A RQ3 compara os dois presets do Lighthouse, não dispositivos. Nada se afirma sobre usuários reais. | Limitação. |
| **Uma máquina, uma rede, um dia.** | Ambiente gravado por sessão (SO, CPU, RAM, versões, adaptador de rede, plano de energia). **TODO:** registrar o provedor de internet e a cidade da máquina de medição; o tipo de conexão (cabeada, 1 Gbps, sem VPN) já está gravado. | Parcial. |
| **Seleção por conveniência de 10 serviços**, escolhidos em novembro de 2026. Três deles (Portal gov.br, Portal do Servidor e ENEM) ficam no mesmo host (`www.gov.br`, Plone) e são menos independentes entre si. | Declarada; não se generaliza para "serviços do governo". | Limitação. |
| **Serviços que bloqueiam acesso automatizado saíram da amostra** (Detran-MG, Senatran, Portal da Transparência, IBGE). A amostra pende para serviços sem proteção anti-bot. | Cada troca e o motivo estão em [`url-changes.md`](url-changes.md). | Parcial. |
| **Versões específicas** do Lighthouse (13.6.0) e do Chrome (158), e uma janela curta (25/11/2026). | Versões e datas gravadas; os resultados valem para essa janela. | Parcial. |
| **Números de uso de anos e unidades diferentes** no cálculo de impacto (2024 e 2021; acessos, consultas). | Declarado em [`impacto.md`](impacto.md): o total é uma ordem de grandeza, e cobre 3 dos 10 serviços. | Parcial. |
| **Impacto extrapolado do laboratório.** As horas de espera supõem que cada acesso carrega a página medida, em primeira visita, no celular emulado. | Cenários de 0%, 50% e 100% de acessos mobile; as premissas estão listadas. | Parcial. |

## 5. Ética de medição

Não é uma ameaça à validade, mas fica registrada: só páginas públicas, sem login, sem formulário, sem dados pessoais; `robots.txt` verificado antes da coleta (`docs/robots-check.md`); uma execução por vez, pausa mínima de 10 s (menor pausa observada: 10,001 s), sem teste de carga.
