# Lab05 — Medição externa de serviços digitais do gov.br com Lighthouse

**Sprint 1 — Proposta e piloto** (17/11/2026) · **atualizada na Sprint 2** (25/11/2026: coleta completa e análise) · Laboratório de Experimentação de Software · PUC Minas

As mudanças da Sprint 2 estão listadas no [changelog](#changelog) no fim deste documento. Resultados: [`analysis/results.md`](../analysis/results.md).

O estudo mede, de fora, as páginas públicas de entrada de dez serviços digitais de governo, como faria um usuário comum que abre a página pela primeira vez. A ferramenta é o Lighthouse 13.6.0. Não é teste de carga: as execuções são sequenciais, uma URL por vez, com pausa mínima de 10 s. Não há login, preenchimento de formulário nem envio de dados pessoais. Nenhum repositório é minerado.

Os itens que dependem de informação ainda não verificada estão marcados com **TODO** e listados na seção 10.

---

## 1. Serviços escolhidos

### 1.1 Objeto medido

O objeto de medição é a **página pública de entrada** de cada serviço, na URL listada em [`data/urls.json`](../data/urls.json). Em serviços que exigem login (Meu INSS, e-CAC, CTPS Digital, Meu SUS Digital), mede-se apenas a página que qualquer pessoa vê antes de se autenticar. Nove serviços são federais e um é estadual (Portal MG).

### 1.2 Critérios "real" e "em operação"

"Real" significa serviço oficial em produção, mantido pelo órgão responsável, em domínio do governo. "Em operação" significa que a URL respondeu em 17/11/2026 e teve o `robots.txt` consultado ([`docs/robots-check.md`](robots-check.md)).

| # | Serviço | Órgão responsável | URL medida | Em operação (17/11/2026) |
|---|---|---|---|---|
| 1 | Portal gov.br | Ministério da Gestão e da Inovação em Serviços Públicos (MGI) | https://www.gov.br/pt-br | HTTP 200; piloto: 6/6 execuções válidas |
| 2 | Meu INSS | Instituto Nacional do Seguro Social (INSS) | https://meu.inss.gov.br/ | HTTP 200; piloto: 6/6 execuções válidas |
| 3 | Receita Federal (e-CAC) | Receita Federal do Brasil | https://cav.receita.fazenda.gov.br/autenticacao/login | 1ª tentativa sem resposta HTTP (curl devolveu 000); 2ª tentativa HTTP 200 |
| 4 | Carteira de Trabalho Digital (web) | Ministério do Trabalho e Emprego (MTE) | https://servicos.mte.gov.br/spme-v2/ | HTTP 200 (após 1 redirecionamento a partir de `servicos.mte.gov.br/`) |
| 5 | Valores a Receber | Banco Central do Brasil | https://www.bcb.gov.br/meubc/valores-a-receber?modalAberto=cuidado-com-golpes-modal | HTTP 200 (destino do endereço oficial `valoresareceber.bcb.gov.br`); piloto: 3/3 execuções válidas por form factor (seção 9) |
| 6 | Meu SUS Digital | Ministério da Saúde | https://meususdigital.saude.gov.br/ | HTTP 200 |
| 7 | Portal MG | Governo do Estado de Minas Gerais | https://www.mg.gov.br/ | HTTP 200 |
| 8 | Portal do Servidor | MGI | https://www.gov.br/servidor/pt-br | HTTP 200 |
| 9 | Consumidor.gov.br | Secretaria Nacional do Consumidor (Senacon/MJSP) | https://www.consumidor.gov.br/ | HTTP 200 |
| 10 | ENEM (Inep) | Inep / MEC | https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem | HTTP 200 (destino de `enem.inep.gov.br`) |

A página de CTPS Digital foi confirmada como canal web oficial pela página de serviço do gov.br (https://www.gov.br/pt-br/servicos/obter-a-carteira-de-trabalho, "Última Modificação: 15/12/2025", acessada em 17/11/2026), que aponta para `servicos.mte.gov.br/spme-v2/`.

### 1.3 Critério "alto impacto"

Todos os números abaixo foram conferidos na página da fonte em **17/11/2026** (data de acesso). As citações estão no texto da fonte. Quando não houve número verificável, a linha diz **NÃO ENCONTRADO** e nada foi estimado.

| # | Serviço | Número publicado | O que o número mede | Fonte | Publicado em |
|---|---|---|---|---|---|
| 1 | Portal gov.br | 175 milhões de usuários | Contas gov.br cadastradas em 24/03/2026 | [MGI](https://www.gov.br/gestao/pt-br/assuntos/noticias/2026/marco/gov-br-alcanca-a-marca-de-175-milhoes-de-usuarios) | 24/03/2026 |
| 2 | Meu INSS | 830,8 milhões de acessos (707,4 mi pelo aplicativo; 123,4 mi pelo site) | Acessos em 2024 | [INSS](https://www.gov.br/inss/pt-br/noticias/meu-inss-bateu-a-marca-de-830-8-milhoes-de-acessos-no-ano-passado) | 08/01/2025 |
| 3 | Receita Federal (e-CAC) | 875.268.240 atendimentos pelo canal "Portal e-CAC" (230.356.664 em 2019) | Serviços prestados pelo e-CAC em 2023, tabela "Total de atendimentos na RFB (por canal)", p. 9. Conta atendimentos, não usuários distintos. | [Receita Federal — Relatório de Atividades 2023 (PDF)](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/geral/2023-balanco-anual-de-atividades) | PDF sem data no texto; metadado do arquivo: 11/09/2024 |
| 3a | (evidência indireta) | 44.393.571 declarações do IRPF 2026 recebidas | Declarações entregues; o texto cita "o portal e-CAC ou o aplicativo Meu Imposto de Renda" como canal para entregas em atraso. **Não é número de uso do e-CAC.** | [Receita Federal](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/junho/irpf-2026-registra-recorde-de-entrega-de-declaracoes) | 01/06/2026 |
| 4 | CTPS Digital | 685,2 milhões de acessos | Acessos em 2023 | [Agência Gov](https://agenciagov.ebc.com.br/noticias/202401/carteira-de-trabalho-digital-teve-685-milhoes-de-acessos-e-14-milhoes-de-novos-usuarios-em-2023) | 19/01/2024 |
| 4a | CTPS Digital | 74,3 milhões de trabalhadores habilitados; 185 milhões de acessos no 1º trimestre de 2024 | Habilitados (acumulado) e acessos "tanto pelo aplicativo como pelo portal" | [MTE](https://www.gov.br/trabalho-e-emprego/pt-br/noticias-e-conteudo/2024/Maio/carteira-de-trabalho-digital-alcanca-mais-de-2-bilhoes-de-acessos-e-totaliza-74-3-milhoes-de-trabalhadores-habilitados) | 10/05/2024 |
| 5 | Valores a Receber | 72 milhões de consultas públicas e 4,3 milhões de solicitações de resgate | Uso em 2024 ("ano passado" em nota de fev/2025) | [MGI](https://www.gov.br/gestao/pt-br/assuntos/noticias/2025/fevereiro/verificacao-em-duas-etapas-vai-aumentar-seguranca-de-servicos-do-banco-central-no-gov.br) | 14/02/2025 |
| 6 | Meu SUS Digital | Mais de 59 milhões de downloads; 29 milhões de usuários no último mês | Números do **aplicativo** | [Agência Gov](https://agenciagov.ebc.com.br/noticias/202507/ministerio-da-saude-institui-rede-nacional-de-dados-em-saude-como-plataforma-oficial-de-integracao-de-dados-do-sus) | 23/07/2025 |
| 7 | Portal MG | 21 milhões de acessos | Acessos ao portal em 2021 (dado mais recente encontrado para o portal; nova busca em 17/11/2026 só achou números do MG App e a contagem de serviços) | [Agência Minas](https://www.agenciaminas.mg.gov.br/noticia/estado-lanca-novo-portal-mg-para-melhorar-acesso-a-mais-de-1-100-servicos-publicos) | 16/02/2022 |
| 7a | (contexto) | "o MG App superou a marca de 9 milhões de usuários"; "média de 950 mil acessos" por mês; "1.348 [serviços] no portal" | Usuários e acessos são do **MG App**, não do portal. Do portal só há o número de serviços. | [Agência Minas — Balanço 2023-2026](https://www.agenciaminas.mg.gov.br/noticia/balanco-2023-2026-governo-de-minas-amplia-digitalizacao-de-servicos-e-disponibiliza-mais-de-220-funcionalidades-no-mg-app) | 17/11/2026 |
| 8 | Portal do Servidor | **NÃO ENCONTRADO** | — | — | — |
| 8a | (evidência indireta) | "a plataforma é utilizada por 87% de seu público-alvo, formado por 1,3 milhão de pessoas" | Uso da plataforma **SouGov.br** por servidores civis federais, aposentados e pensionistas. Mostra o tamanho do público do Portal do Servidor. **Não é número de uso do Portal do Servidor.** | [MGI](https://www.gov.br/gestao/pt-br/assuntos/noticias/2023/maio/sougov-br-completa-dois-anos-e-ja-e-utilizado-por-87-dos-servidores-publicos-federais) | 04/05/2023 |
| 9 | Consumidor.gov.br | 8,6 milhões de brasileiros cadastrados; mais de 11,4 milhões de atendimentos; 2.328.863 reclamações finalizadas em 2025 | Cadastros e atendimentos acumulados; reclamações de 2025 | [Boletim Consumidor.gov.br 2025 (Senacon)](https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor/defesadoconsumidor/Biblioteca/boletins-1/boletim-consumidor-gov-br-2025-vfinal.pdf) | PDF sem data no texto; metadado do arquivo: 26/06/2026 |
| 10 | ENEM (Inep) | 5.051.345 inscrições confirmadas | Participantes inscritos no Enem 2026 | [Inep](https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias/enem/painel-enem-2026-detalha-inscricoes-no-exame) | 20/10/2026 |

Ressalvas:

- Os números descrevem o **serviço como um todo** (aplicativo + web), não a página medida. Só o Meu INSS separa o site (123,4 milhões de acessos em 2024). O número do e-CAC é do canal "Portal e-CAC", mas conta serviços prestados, não visitas à página de entrada.
- Os números têm datas e definições diferentes (contas, acessos, downloads, inscrições, atendimentos). Eles servem como evidência de alcance, não para comparar serviços entre si.
- **TODO:** o Portal do Servidor continua sem número de uso verificável (só a evidência indireta 8a, de 2023). Decisão da Sprint 2 (25/11/2026): o serviço **fica, com a ressalva**, porque cumpre os critérios técnicos e éticos; o número continua **NÃO ENCONTRADO** e não foi estimado ([`url-changes.md`](url-changes.md)).
- **Nota da Sprint 3 (26/11/2026):** para o Valores a Receber, a linha 5 traz 72 milhões de consultas (nota do MGI). O cálculo de impacto usa 73 milhões, do próprio Banco Central ([apresentação de 26/05/2025, slide 9](https://www.bcb.gov.br/conteudo/home-ptbr/TextosApresentacoes/IzabelaCorrea_coletiva_26_5_25.pdf), conferida em 26/11/2026). Os números e as fontes usados no impacto estão em `data/usage.json` e em [`impacto.md`](impacto.md).

### 1.4 URLs trocadas

| Candidata | Trocada por | Motivo |
|---|---|---|
| Conecte SUS (`conectesus-paciente.saude.gov.br`) | Consumidor.gov.br | Redireciona para o Meu SUS Digital; mediria a mesma página duas vezes. |
| Detran-MG (`www.detran.mg.gov.br`) | Portal MG | `robots.txt` tem `User-agent: *` + `Disallow: /` (só Googlebot e bedrockbot liberados). |
| Senatran — Portal de Serviços (substituta considerada para Detran-MG) | — | `robots.txt` sem resposta; pela RFC 9309, inacessível = proibido. |
| Portal da Transparência (estava no piloto) | Valores a Receber (BCB) | `robots.txt` permite `/`, mas 4 de 6 execuções do piloto receberam um CAPTCHA do AWS WAF ("Let's confirm you are human", documento principal com HTTP 202) em vez do portal. Contornar CAPTCHA está fora do escopo e das regras de ética. |
| IBGE (substituta considerada para o Portal da Transparência) | — | Página inicial devolveu HTTP 403 a uma requisição com User-Agent de navegador. |
| ENEM (`enem.inep.gov.br`) | Mesma página, URL final | A URL redireciona para a página do ENEM no gov.br/inep; a URL final é medida para o redirecionamento não entrar no tempo. O mesmo vale para Valores a Receber e CTPS Digital. |

---

## 2. Perguntas de pesquisa e hipóteses

**RQ1.** O desempenho (performance score e LCP) varia entre os serviços escolhidos? Quais são os piores?

- H0₁ₐ: para cada form factor, a distribuição do performance score é a mesma nos dez serviços.
- H1₁ₐ: em pelo menos um serviço a distribuição do performance score é diferente.
- H0₁ᵦ: para cada form factor, a distribuição do LCP é a mesma nos dez serviços.
- H1₁ᵦ: em pelo menos um serviço a distribuição do LCP é diferente.
- "Quais são os piores" é respondido pelo teste post-hoc (seção 7) e pela ordenação das medianas, não por uma hipótese própria.

**RQ2.** Serviços com pior desempenho também têm pior acessibilidade?

- H0₂: não há correlação monotônica entre o performance score mediano e o accessibility score dos serviços (ρₛ = 0).
- H1₂: há correlação monotônica (ρₛ ≠ 0). A direção esperada é positiva (pior desempenho com pior acessibilidade). O teste é bilateral para não descartar uma associação no sentido contrário.

**RQ3 (secundária).** Quanto o desempenho em mobile é pior que em desktop?

- H0₃ₐ: a mediana das diferenças pareadas por serviço (performance score desktop − mobile) é zero.
- H1₃ₐ: a mediana das diferenças é diferente de zero.
- H0₃ᵦ: a mediana das diferenças pareadas por serviço (LCP mobile − desktop) é zero.
- H1₃ᵦ: a mediana das diferenças é diferente de zero.
- O "quanto" é respondido pela mediana das diferenças (em pontos e em ms), pela razão LCP mobile/desktop e pelo tamanho do efeito.

---

## 3. GQM

### 3.1 Objetivo (template de Basili, Caldiera e Rombach, 1994)

| Campo | Valor |
|---|---|
| **Analisar** | as páginas públicas de entrada de dez serviços digitais de governo (nove federais, um estadual) |
| **com o propósito de** | caracterizar e comparar |
| **com respeito a** | desempenho de carregamento e acessibilidade verificável automaticamente |
| **do ponto de vista de** | um usuário comum que abre a página pela primeira vez, sem login |
| **no contexto de** | medições externas de laboratório com Lighthouse 13.6.0 em Chrome headless, com emulação mobile e desktop, coletadas em novembro de 2026 a partir de uma única máquina |

### 3.2 Perguntas

| ID | Pergunta | RQ |
|---|---|---|
| Q1 | O performance score e o LCP diferem entre os serviços, em cada form factor? Quais serviços têm os piores valores? | RQ1 |
| Q2 | O performance score mediano dos serviços está associado ao accessibility score? | RQ2 |
| Q3 | Qual é a diferença entre mobile e desktop no performance score e no LCP de cada serviço? | RQ3 |

### 3.3 Métricas

| ID | Métrica | Definição | Unidade | Escala | Perguntas |
|---|---|---|---|---|---|
| M1 | Performance score | Score da categoria *performance* × 100. Média ponderada das notas de FCP (10%), LCP (25%), TBT (30%), CLS (25%) e Speed Index (10%), cada nota obtida por uma curva log-normal (pesos do código do Lighthouse 13.6.0) | pontos (0–100) | Numericamente de razão, mas **tratada como ordinal**: é composta, limitada a 0–100 e não linear em relação aos tempos | Q1, Q2, Q3 |
| M2 | LCP (Largest Contentful Paint) | Tempo até a renderização do maior elemento de conteúdo visível | ms | Razão | Q1, Q3 |
| M3 | FCP (First Contentful Paint) | Tempo até o primeiro conteúdo renderizado | ms | Razão | Q1 (descritiva) |
| M4 | TBT (Total Blocking Time) | Soma do tempo além de 50 ms de cada tarefa longa entre FCP e o fim do carregamento | ms | Razão | Q1 (descritiva) |
| M5 | CLS (Cumulative Layout Shift) | Soma das mudanças inesperadas de layout | adimensional | Razão | Q1 (descritiva) |
| M6 | Speed Index | Rapidez com que o conteúdo aparece visualmente | ms | Razão | Q1 (descritiva) |
| M7 | Accessibility score | Score da categoria *accessibility* × 100. Média ponderada (pesos 10, 7 ou 3) de auditorias axe-core aprovadas/reprovadas | pontos (0–100) | **Tratada como ordinal** (proporção ponderada de regras automáticas, não mede acessibilidade completa) | Q2 |
| M8 | Mediana por serviço × form factor | Mediana de M1, M2 e M7 nas N execuções válidas | da métrica base | da métrica base | Q1, Q2, Q3 |
| M9 | IQR por serviço × form factor | Amplitude interquartil de M1 e M2 | da métrica base | da métrica base | Q1 (variabilidade) |
| M10 | Diferença pareada | Por serviço: M8(M1, desktop) − M8(M1, mobile); M8(M2, mobile) − M8(M2, desktop) | pontos; ms | Intervalo (pontos); razão (ms) | Q3 |
| M11 | Razão LCP | Por serviço: M8(M2, mobile) / M8(M2, desktop) | adimensional | Razão | Q3 |

---

## 4. Entidades e atributos

| Entidade | Classe | Atributo | Interno ou externo | Medida | Direta ou derivada | Escala |
|---|---|---|---|---|---|---|
| Página de entrada do serviço | Produto | Rapidez de exibição do conteúdo principal | Externo | LCP (ms) | Derivada: no modo `simulate`, estimada pelo modelo Lantern a partir do trace sem limitação | Razão |
| Página de entrada do serviço | Produto | Rapidez da primeira pintura | Externo | FCP (ms) | Derivada (Lantern) | Razão |
| Página de entrada do serviço | Produto | Progresso visual do carregamento | Externo | Speed Index (ms) | Derivada (Lantern) | Razão |
| Página de entrada do serviço | Produto | Bloqueio da thread principal (proxy de responsividade em laboratório) | Externo | TBT (ms) | Derivada (Lantern) | Razão |
| Página de entrada do serviço | Produto | Estabilidade visual | Externo | CLS | Direta: calculada dos eventos de layout shift observados no trace, sem simulação | Razão |
| Página de entrada do serviço | Produto | Desempenho geral | Externo | Performance score | Derivada (média ponderada de LCP, FCP, SI, TBT e CLS após curvas de pontuação) | Ordinal (tratada) |
| Página de entrada do serviço | Produto | Acessibilidade verificável automaticamente | Externo | Accessibility score | Derivada (média ponderada de auditorias binárias) | Ordinal (tratada) |
| Página de entrada do serviço | Produto | Conformidade com cada regra automática de acessibilidade | Externo | Resultado de cada auditoria (passa/falha) | Direta | Nominal |
| Página de entrada do serviço | Produto | Tamanho | Interno | Bytes transferidos, nº de requisições, nº de elementos DOM | Direta | Razão |
| Execução de medição | Processo | Momento e posição na sequência | — | `timestamp`, `order`, `run` | Direta | Intervalo (tempo); ordinal (ordem) |
| Execução de medição | Processo | Validade (mediu a página certa?) | — | Status HTTP do documento principal | Direta | Nominal |
| Ambiente de medição | Recurso | Capacidade de CPU do host no momento | — | `benchmarkIndex` do Lighthouse | Derivada | Razão |

O tamanho da página e a validade não entram nas RQs. São registrados para verificar se cada execução mediu a página certa (seção 9).

---

## 5. Classificação da pesquisa

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada | Produz conhecimento sobre serviços específicos em produção, com uso prático para quem os mantém e para quem os avalia. |
| Objetivos | Descritiva | Caracteriza desempenho e acessibilidade e descreve diferenças e associações (RQ1–RQ3). Não busca explicar causas: não se observa o código nem a infraestrutura dos serviços. |
| Abordagem | Quantitativa | Todas as variáveis de resposta são numéricas, obtidas por instrumento, e analisadas com estatística descritiva e testes de hipótese. |
| Procedimentos | Estudo de medição em campo, com componente quase-experimental | Os serviços são observados como estão (RQ1, RQ2: observacional). O form factor é manipulado pelo pesquisador e a ordem das execuções é aleatória (RQ3), mas os objetos não são atribuídos aleatoriamente nem controlados, por isso é quase-experimento e não experimento. |
| Tempo | Transversal | A coleta acontece em uma janela curta (Sprints 1 e 2). As execuções repetidas são réplicas da mesma medição, não uma série temporal. |
| Controle | Parcial | O ambiente de medição é controlado (mesma máquina, versões fixas, configuração registrada, throttling simulado). Os objetos estão em produção: servidor, CDN, conteúdo e rede até eles não são controlados. |
| Nível de evidência | Baixo a moderado | Estudo primário, sem grupo controle randomizado e sem replicação independente, com dez páginas escolhidas por conveniência. Nas hierarquias de evidência usadas em Engenharia de Software (adaptadas da medicina por Kitchenham, 2004), fica abaixo de experimentos controlados e de revisões sistemáticas. As conclusões valem para estas URLs, nesta janela de tempo e nestas condições de emulação. |

---

## 6. Plano de coleta

### 6.1 Variáveis

| Tipo | Variável | Níveis / unidade |
|---|---|---|
| Independente (fator) | Serviço | Nominal, 10 níveis |
| Independente (fator, tratamento) | Form factor | Nominal, 2 níveis: `mobile`, `desktop` |
| Dependente | Performance score, LCP, FCP, TBT, CLS, Speed Index, accessibility score | Ver seção 3.3 |
| Registrada (controle) | Data/hora, ordem de execução, número da réplica, `benchmarkIndex`, status HTTP do documento principal, URL final, avisos do Lighthouse, elemento LCP, número de elementos DOM; por sessão, plano de energia e adaptador de rede da rota padrão | Ver [`data/run-metadata.json`](../data/run-metadata.json) e [`data/processed/`](../data/processed/) |
| Fixada | Versão do Lighthouse, do Chrome e do chrome-launcher; flags do Chrome; configuração de cada form factor; máquina | Ver 6.6 |

### 6.2 Tratamentos

Os dois tratamentos são os presets padrão do Lighthouse 13.6.0, sem alteração (valores lidos do código-fonte do Lighthouse 13.6.0; rede, CPU, tela e User-Agent também ficam gravados em `run-metadata.json` a cada sessão):

| Parâmetro | `mobile` (padrão do Lighthouse) | `desktop` (`desktop-config`) |
|---|---|---|
| Tela emulada | 412 × 823 px, DPR 1,75 (Moto G Power) | 1350 × 940 px, DPR 1 |
| User-Agent emulado | Android 11, moto g power (2022), Chrome/136 | macOS, Chrome/136 |
| Rede (simulada) | RTT 150 ms, 1,6 Mbps (1638,4 kbps) | RTT 40 ms, 10 Mbps (10240 kbps) |
| CPU | 4× mais lenta | sem redução |
| Método de throttling | `simulate` (Lantern) | `simulate` (Lantern) |
| Curva de pontuação do LCP (p10 / mediana) | 2500 / 4000 ms | 1200 / 2400 ms |
| Curva de pontuação do TBT (p10 / mediana) | 200 / 600 ms | 150 / 350 ms |

Em todas as execuções: categorias `performance` e `accessibility` apenas, `maxWaitForLoad` de 45 s, armazenamento limpo pelo Lighthouse, e um Chrome novo com perfil temporário por execução (cache frio, ou seja, primeira visita). A captura de tela da página inteira foi desligada (`disableFullPageScreenshot`); ela acontece depois do carregamento e não altera métricas, mas reduz o tamanho do JSON.

### 6.3 Número de execuções

- **Piloto (Sprint 1):** 3 serviços × 2 form factors × 3 execuções = 18 execuções, mais 6 execuções do serviço substituto (seção 9).
- **Coleta completa (Sprint 2), executada:** N = 10 por serviço e form factor, em **2 blocos de horário** (manhã e tarde de 25/11/2026, quarta-feira) com 5 execuções cada. Total: 10 × 2 × 10 = 200 execuções. Estimativa feita pelo script antes de começar: cerca de 39 min por bloco de 100 execuções (mediana de 13,6 s por execução mais 10 s de pausa). Duração real: 36 min (manhã, 11:38–12:14) e 38 min (tarde, 15:01–15:39, com 105 tentativas). *Plano original da Sprint 1: N = 12 em 3 blocos (manhã, tarde, noite) de 4, 240 execuções; ver o changelog no fim.*
- Justificativa: a documentação do Lighthouse afirma que "the median Lighthouse score of 5 runs is twice as stable as 1 run" ([variability.md](https://github.com/GoogleChrome/lighthouse/blob/main/docs/variability.md), acessado em 17/11/2026). Doze execuções por célula dão mais de 5 por mediana e permitem ver variação por horário. No piloto, a amplitude do performance score dentro de cada célula foi de no máximo 6 pontos.
- Todas as sessões usam a mesma fase (`--phase full`) e o mesmo plano, guardado em `data/raw/full/plan.json` (seed 3118576651). O plano embaralha o bloco 1 (réplicas 1 a 5 de cada célula) e depois o bloco 2 (réplicas 6 a 10). Cada sessão grava `--session-label` (`morning`, `afternoon`); a análise usa o rótulo da sessão que gerou cada execução como bloco. A sessão pode ser interrompida e retomada: execuções com JSON válido são puladas.

### 6.4 Ordem aleatória

O script monta todas as combinações (serviço × form factor × réplica) e as embaralha com um gerador pseudoaleatório com seed (mulberry32 + Fisher–Yates). A seed é sorteada se não for informada e sempre fica gravada em `run-metadata.json`, junto com a ordem planejada; com a mesma seed a ordem é reproduzida. O número da réplica (`run`) é atribuído depois do embaralhamento, então `run = 1` é a primeira vez que aquela combinação foi medida na sessão. Isso permite testar efeito de ordem (por exemplo, cache de CDN frio na primeira visita).

### 6.5 Regras de ética

| Regra | Como é cumprida |
|---|---|
| Ler o `robots.txt` antes de medir | `scripts/robots-check.mjs` baixa o `robots.txt` de cada host, aplica a RFC 9309 (4xx = sem restrição; 429, 5xx ou erro de rede = proibido) para os agentes `*`, `Lighthouse` e `Chrome-Lighthouse`, e grava o resultado em [`docs/robots-check.md`](robots-check.md). O script de medição recusa URLs não liberadas e recusa rodar se a verificação tiver mais de 7 dias. |
| Respeitar bloqueios ativos | Uma execução é marcada como `blocked` se o documento principal não volta com HTTP 200 (por exemplo, um CAPTCHA servido com HTTP 202) ou se o texto do elemento LCP é uma mensagem de desafio anti-bot (para desafios servidos com HTTP 200). As execuções restantes daquele serviço na sessão são puladas. O serviço é trocado. |
| Sequencial, sem paralelismo | Um Chrome e uma execução do Lighthouse por vez. |
| Pausa mínima de 10 s | Valor padrão e mínimo do script; `Crawl-delay` maior no `robots.txt` seria respeitado (nenhum host define). Cada execução já dispara várias requisições, e a pausa mantém o ritmo bem abaixo de 1 requisição por segundo em média. |
| Só páginas públicas | Sem login, sem formulário, sem dados pessoais. A página de login do e-CAC e o formulário do Valores a Receber são apenas carregados, nunca preenchidos. |
| Interrupção por falha | Se 3 execuções seguidas falharem por erro do script, a sessão é interrompida. |

### 6.6 Ambiente

| Item | Valor (de `run-metadata.json`) |
|---|---|
| Sistema operacional | Windows 11 Pro (10.0.26300), x64 |
| CPU | AMD Ryzen 5 5500, 12 threads lógicas, 3600 MHz |
| RAM | 15,8 GB |
| Node.js | v24.18.0 |
| Chrome | 158.0.8127.37 na coleta completa (157.0.8103.79 no piloto), `--headless=new` |
| Lighthouse / chrome-launcher | 13.6.0 / 1.2.3 (versões fixas no `package.json`) |
| Fuso horário | America/Sao_Paulo |
| `benchmarkIndex` no piloto | 2582 a 3273 |
| Conexão de rede (lida em 17/11/2026, depois do piloto) | Cabeada: Ethernet (802.3), Realtek PCIe GbE, link de 1 Gbps; o adaptador da rota padrão é físico, ou seja, sem VPN. Provedor e cidade: **TODO** |
| Plano de energia (lido em 17/11/2026, depois do piloto) | Windows "Ultimate Performance" (GUID `423c2439-a4a4-4031-9403-18ddc8ffd859`) |
| Bateria | Nenhuma (desktop), então a máquina está sempre na tomada |

Protocolo para as coletas da Sprint 2: sem outros programas pesados abertos e sem VPN. As sessões do piloto não gravaram plano de energia nem rede; os valores acima foram lidos no mesmo dia, depois do piloto. A partir da Sprint 2 o script grava os dois em cada sessão (`hostConditions` em `run-metadata.json`), sem ler IP, MAC, nome da rede ou provedor.

### 6.7 Artefatos

| Arquivo | Função |
|---|---|
| `data/urls.json` | Lista de serviços, flag de piloto e histórico de trocas |
| `scripts/robots-check.mjs` | Verificação de `robots.txt` |
| `scripts/run-lighthouse.mjs` | Execução sequencial e aleatorizada do Lighthouse |
| `scripts/extract-metrics.mjs` | Geração dos CSVs a partir dos JSONs brutos |
| `data/raw/<fase>/<servico>_<formfactor>_<n>.json` | Resultado bruto de cada execução |
| `data/processed/<fase>.csv` | Uma linha por execução válida |
| `data/processed/<fase>_failures.csv` | Execuções inválidas (erro do Lighthouse, bloqueio, valores ausentes) e o motivo |
| `data/processed/<fase>_flags.csv` | Execuções válidas marcadas para revisão (seção 7.6) |
| `data/processed/<fase>_executions.csv` | Cada tentativa: sessão, rótulo de horário, horários UTC com ms, status |
| `data/failed-runs.csv` | Cada tentativa que falhou ou foi pulada, com o motivo |
| `scripts/validate-data.mjs` | Validação dos dados e marcação de outliers → `docs/data-validation.md` |
| `analysis/analyze.py`, `analysis/run_all.py` | Análise estatística da seção 7 e gráficos; `run_all.py` refaz tudo com um comando |

---

## 7. Plano de análise

Implementado em [`analysis/analyze.py`](../analysis/analyze.py): Python 3.12 com pandas, SciPy (`kruskal`, `spearmanr`, `kendalltau`, `wilcoxon`, `binomtest`) e scikit-posthocs (`posthoc_dunn`), versões fixas em `analysis/requirements.txt`. Tamanhos de efeito e correção de Holm estão em `analysis/lab_stats.py`, com testes unitários. Nível de significância α = 0,05. Dentro de cada RQ, os p-valores são corrigidos por Holm (1979). O script foi executado nos dados do piloto só para conferir que funciona; com n = 3 os testes não respondem às RQs.

### 7.1 Estatística descritiva

Para cada serviço × form factor: n de execuções válidas, mediana, IQR, média, desvio padrão, mínimo e máximo de todas as métricas; boxplots por serviço (`analysis/figures/`); contagem de execuções inválidas (bloqueio, erro) por serviço; tabela do elemento LCP de cada serviço; medianas por bloco de horário; réplica 1 contra as seguintes (efeito de cache de CDN, seção 8.2). Teste de Shapiro–Wilk por grupo apenas para documentar a forma das distribuições (a escolha dos testes não depende dele, ver 7.5).

### 7.2 RQ1 — Kruskal–Wallis entre serviços

- Kruskal–Wallis (Kruskal e Wallis, 1952) com o serviço como fator, separado por form factor, para performance score e LCP: 4 testes, corrigidos por Holm.
- Tamanho do efeito: ε² = H / ((n² − 1) / (n + 1)), em que H é a estatística do teste e n o total de observações (Tomczak e Tomczak, 2014).
- Post-hoc: teste de Dunn (1964) com correção de Holm, para dizer quais pares diferem. Os "piores" são os serviços com pior mediana que diferem significativamente da maioria dos demais.
- Unidade de observação: a execução. A inferência vale para estas dez URLs, não para a população de serviços do governo (seção 8.1).

### 7.3 RQ2 — Spearman entre desempenho e acessibilidade

- Unidade de análise: o **serviço** (n = 10). Para cada serviço e form factor, usa-se a mediana do performance score e a mediana do accessibility score.
- Motivo: no piloto, o accessibility score foi idêntico em todas as execuções de uma mesma página e form factor (92 nas 12 execuções de gov.br e Meu INSS; 89 em mobile e 85 em desktop nas 6 do Valores a Receber). Dentro de um serviço ele não varia, então uma correlação por execução dentro do serviço não é definida.
- Correlação de Spearman (ρₛ) por form factor (2 testes, Holm). Como o accessibility score tem muitos empates, o τ-b de Kendall é calculado como análise de sensibilidade.
- Sprint 2: IC de 95% por bootstrap percentil (10 000 reamostras, seed fixa) reamostrando serviços. Também se calcula ρₛ com todas as execuções; nesse caso o IC reamostra serviços inteiros (bootstrap por cluster), porque as execuções de um mesmo serviço não são independentes.

### 7.4 RQ3 — Wilcoxon pareado mobile × desktop

- Pareamento por serviço (n = 10 pares): mediana em mobile e mediana em desktop do mesmo serviço.
- Teste de postos sinalizados de Wilcoxon (1945) para o performance score e para o LCP (2 testes, Holm).
- Tamanho do efeito: delta de Cliff (Cliff, 1993) entre as medianas mobile e desktop dos serviços, com os limiares de Romano et al. (2006): |δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; ≥ 0,474 grande. Como o delta de Cliff não usa o pareamento, reporta-se também a correlação rank-biserial pareada (Kerby, 2014).
- Magnitude: mediana das diferenças (pontos e ms) e mediana da razão LCP mobile/desktop.
- O LCP é a medida principal da RQ3. O score é secundário porque o Lighthouse usa curvas de pontuação diferentes para mobile e desktop (tabela da seção 6.2): uma diferença de score mistura "condição pior" com "régua diferente".
- Para o score, como o Wilcoxon pressupõe que as diferenças possam ser ordenadas, o teste do sinal é reportado como análise de sensibilidade.
- Sprint 2: além do teste entre serviços, um Wilcoxon pareado **dentro de cada serviço**, com pares = execuções mobile e desktop de mesmo número de réplica (`run`), que caem no mesmo bloco de horário; Holm entre os 10 serviços. Delta de Cliff (mobile × desktop, sem pareamento) ao lado.

### 7.5 Por que esses testes

| Critério | Situação nos dados | Consequência |
|---|---|---|
| Escala | Scores são composições limitadas a 0–100, não lineares em relação aos tempos: tratados como ordinais. Tempos (ms) são de razão. | Testes baseados em postos servem para ambos sem supor intervalos iguais entre scores. |
| Distribuição | Tempos são positivos e assimétricos, com cauda longa: no piloto, as medianas de LCP foram de 3,2 s (Meu INSS, desktop) a 30,6 s (gov.br, mobile), e o LCP mobile do gov.br foi ~6 vezes o do desktop. | Não há base para supor normalidade; média e desvio padrão seriam dominados pelos extremos. |
| Tamanho dos grupos | 10 execuções por célula (RQ1) e 10 serviços (RQ2, RQ3). | Com amostras pequenas, testes de normalidade têm pouco poder; testes não paramétricos não dependem desse pressuposto. |
| Estrutura | RQ1: k = 10 grupos independentes. RQ2: associação monotônica entre duas medidas ordinais. RQ3: duas medidas do mesmo serviço. | Kruskal–Wallis (k grupos), Spearman (associação monotônica), Wilcoxon pareado (amostras dependentes). |

### 7.6 Exclusões e análises de sensibilidade

Proposta; o grupo precisa confirmar (pendência 5 da seção 10).

| Situação | Como é detectada | Tratamento |
|---|---|---|
| Página de bloqueio ou desafio | Documento principal com status diferente de 200, ou texto do elemento LCP igual a uma mensagem de desafio anti-bot | Execução inválida: sai de `<fase>.csv` e vai para `<fase>_failures.csv`. |
| CPU do host abaixo do limiar do Lighthouse | `benchmarkIndex` ≤ 1000 (`SLOW_HOST_CPU`). É o limiar que o Lighthouse usa para avisar que a CPU é mais lenta do que ele espera (`SLOW_CPU_BENCHMARK_INDEX_THRESHOLD` no código-fonte). O aviso só aparece na CLI e nunca em execuções pela API Node, por isso o script aplica o limiar. | Excluída da análise principal (padrão do `analyze.py`). |
| CPU do host abaixo do resto do bloco | `benchmarkIndex` abaixo da cerca inferior de Tukey (Q1 − 1,5 × IQR) das execuções válidas da fase (`BENCHMARK_LOW_OUTLIER`) | Mantida na análise principal. Análise de sensibilidade sem ela (`--exclude-flags all`). No piloto, as duas execuções marcadas não destoaram: a do gov.br mobile teve score 58, igual à mediana da célula. |
| Possível desafio que as regras não reconhecem | DOM com menos da metade dos elementos da maior execução da mesma célula (`DOM_SIZE_DROP`), host final diferente do pedido (`FINAL_HOST_CHANGED`) ou recursos de CAPTCHA carregados (`CHALLENGE_RESOURCES`) | Revisão manual do JSON bruto antes da análise. Se for desafio, o serviço é tratado como bloqueado. |
| Elemento LCP é banner ou modal | `<fase>_lcp_elements.csv` | Análise de sensibilidade sem esses serviços (`--exclude-services`). |
| Outlier de uma métrica (Sprint 2) | Fora da cerca de Tukey (Q1 − 1,5 × IQR, Q3 + 1,5 × IQR) dentro do serviço × form factor × métrica (`scripts/validate-data.mjs` → `full_outliers.csv`) | Não é apagado. A análise sai duas vezes: com todas as execuções e sem os valores marcados (só naquela métrica). |
| Métrica nula sem `runtimeError` (Sprint 2) | Ex.: `NO_FCP` dentro das auditorias; visto no Consumidor.gov.br | Execução inválida (`MISSING_VALUES`), registrada em `data/failed-runs.csv` e refeita. |

As outras análises de sensibilidade (τ-b de Kendall na RQ2, teste do sinal na RQ3) saem sempre junto com a análise principal.

---

## 8. Ameaças à validade

Classificação de Wohlin et al. (2012).

### 8.1 Validade de conclusão

| Ameaça | Mitigação |
|---|---|
| Poucos serviços (n = 10) nas RQ2 e RQ3: baixo poder para detectar correlação ou diferença moderada. | Reportar tamanho de efeito e intervalo, não só p-valor; tratar resultado não significativo como inconclusivo, não como ausência de efeito. |
| Pseudo-replicação na RQ1: execuções repetidas da mesma URL não são amostras independentes de "serviços". | Declarar que a inferência é sobre estas URLs; usar a mediana por serviço nas RQ2 e RQ3. |
| Múltiplos testes (4 na RQ1, 2 na RQ2, 2 na RQ3, mais post-hoc). | Correção de Holm dentro de cada RQ. |
| Empates no accessibility score. | τ-b de Kendall como análise de sensibilidade. |

### 8.2 Validade interna

| Ameaça | Mitigação |
|---|---|
| **Variação por horário**: carga do servidor e da rede muda ao longo do dia. | Coleta em 2 blocos de horário (manhã e tarde; o plano da Sprint 1 previa 3); ordem aleatória dentro de cada bloco; timestamp e rótulo da sessão gravados em cada execução; efeito do bloco testado por serviço (`block_effect.csv`). Sem bloco à noite: limitação ([`ameacas-validade.md`](ameacas-validade.md)). |
| **Cache e CDN**: o Chrome começa sem cache a cada execução, mas o cache da CDN e do servidor não é controlado. A primeira visita pode encontrar a borda da CDN fria, e as seguintes não. | `run` registra a ordem de cada réplica; comparar `run = 1` com as demais; ordem aleatória espalha esse efeito entre serviços e form factors. |
| **Bloqueio por WAF / anti-bot**: o serviço pode servir uma página de desafio (CAPTCHA) e o Lighthouse pontua essa página como se fosse o serviço. Isso aconteceu no piloto. | Duas regras em cada execução: status HTTP do documento principal e texto do elemento LCP (desafio servido com HTTP 200). Execuções inválidas vão para `<fase>_failures.csv`; o serviço deixa de ser medido na sessão e é trocado. Sinais secundários (queda no DOM, troca de host, recursos de CAPTCHA) vão para `<fase>_flags.csv` para revisão (seção 7.6). |
| Mudança de conteúdo durante a coleta (banners, campanhas, deploys). | Registrar número de requisições, bytes e elemento LCP por execução; investigar saltos. |
| Carga da máquina de medição. | Um processo por vez; `benchmarkIndex` gravado em cada execução; plano de energia e adaptador de rede gravados por sessão; critério de exclusão na seção 7.6. |
| User-Agent emulado (Chrome/136) diferente da versão real (Chrome 158 na coleta completa). | Registrado; é o padrão do Lighthouse e igual para todos os serviços. |

### 8.3 Validade de construto

| Ameaça | Mitigação |
|---|---|
| **Throttling simulado**: no modo `simulate`, LCP, FCP, SI e TBT não são tempos observados, e sim estimativas do modelo Lantern a partir de um carregamento sem limitação. A própria documentação do Lighthouse diz que esse modo não mitiga a variabilidade do servidor nem o não determinismo da página. | Declarar as métricas como derivadas (seção 4); manter o mesmo método em todas as execuções; não comparar os números com dados de campo (CrUX) como se fossem a mesma coisa. |
| **Performance score como métrica composta (Goodhart)**: o score é uma média ponderada de curvas escolhidas pelo Lighthouse e é muitas vezes tratado como meta de otimização. Uma medida que vira meta deixa de ser uma boa medida (Goodhart, 1975; Strathern, 1997): uma página pode subir de score sem melhorar a experiência real. Os pesos e curvas mudam entre versões. | Versão fixa (13.6.0); analisar o LCP ao lado do score em RQ1 e usar o LCP como medida principal em RQ3; reportar as métricas componentes na descritiva. |
| Curvas de pontuação diferentes para mobile e desktop. | RQ3 usa o LCP em ms como medida principal (seção 7.4). |
| **Elemento LCP não é o conteúdo principal**: no piloto, o elemento LCP do gov.br foi o texto do banner de consentimento de cookies, em todas as execuções. O LCP desse serviço mede quando o banner aparece. | Exportar o elemento LCP de cada execução (`<fase>_lcp_elements.csv`); análise de sensibilidade sem os serviços cujo LCP é banner ou modal. Não clicar no banner, porque isso mudaria o construto "primeira visita". |
| Accessibility score cobre só regras verificáveis automaticamente (axe-core). Não mede acessibilidade completa nem uso real com tecnologia assistiva. | Interpretar como "acessibilidade verificável automaticamente"; não generalizar para conformidade WCAG. |
| Uma página por serviço (viés de mono-operação): a página de entrada não representa as demais telas do serviço. | Declarar o objeto como "página de entrada"; generalização para o serviço inteiro fica fora do escopo. |

### 8.4 Validade externa

| Ameaça | Mitigação |
|---|---|
| **Emulação vs dispositivo real**: o mobile é um Moto G Power emulado em um desktop Ryzen com CPU 4× mais lenta e rede simulada. Celulares reais de baixo custo, redes 3G/4G instáveis e navegadores diferentes podem dar resultados piores ou diferentes. | Não afirmar que os valores representam a experiência de usuários reais; RQ3 compara os dois presets do Lighthouse, não dispositivos. |
| Uma única máquina e uma única localização de rede. | Registrar o ambiente; replicação em outra máquina/rede fica como trabalho futuro. |
| Seleção por conveniência de dez serviços; três páginas usam a mesma plataforma (www.gov.br, Plone), o que as torna menos independentes. | Declarar a seleção; não generalizar para "serviços do governo". |
| Janela de tempo curta (novembro de 2026) e versão específica do Lighthouse e do Chrome. | Registrar versões e datas; resultados valem para essa janela. |
| Serviços que bloqueiam acesso automatizado saem da amostra, o que pode enviesar a amostra para serviços sem proteção anti-bot. | Registrar cada troca e o motivo (seção 1.4). |

---

## 9. Resultados do piloto

O piloto testa o script; ele não responde às RQs (3 serviços, 3 execuções por célula, uma janela de 15 minutos).

### 9.1 Execuções

| Sessão | Horário (17/11/2026) | Serviços | Execuções | Seed |
|---|---|---|---|---|
| 1 | 15:49–15:56 | gov.br, Meu INSS, Portal da Transparência | 18 | 41872753 |
| 2 | 16:01–16:03 | Valores a Receber (substituto do Portal da Transparência) | 6 | 484856555 |

- 24 execuções, nenhuma com erro de script. Duração mediana 13,5 s (mínimo 6,6 s, máximo 49,3 s).
- Menor intervalo entre o fim de uma execução e o início da seguinte: 10,00 s.
- 20 execuções válidas e 4 inválidas. As 4 inválidas são do Portal da Transparência e mediram uma página de CAPTCHA (documento principal com HTTP 202). Estão em [`data/processed/pilot_failures.csv`](../data/processed/pilot_failures.csv) e os JSONs brutos foram mantidos como evidência.

### 9.2 Medianas por serviço e form factor

Execuções válidas apenas. Tempos em ms, arredondados. Fonte: [`data/processed/pilot_summary.csv`](../data/processed/pilot_summary.csv).

| Serviço | Form factor | n | Performance (mín–máx) | Acessibilidade | LCP | FCP | TBT | CLS | Speed Index |
|---|---|---|---|---|---|---|---|---|---|
| Portal gov.br | desktop | 3 | 69 (66–71) | 92 | 4901 | 1435 | 0 | 0,071 | 1886 |
| Portal gov.br | mobile | 3 | 58 (57–59) | 92 | 30641 | 5977 | 142 | 0,000 | 5977 |
| Meu INSS | desktop | 3 | 53 (51–55) | 92 | 3229 | 1140 | 34 | 0,636 | 2296 |
| Meu INSS | mobile | 3 | 25 (23–29) | 92 | 16239 | 5978 | 489 | 0,616 | 7565 |
| Valores a Receber | desktop | 3 | 24 (24–25) | 85 | 5951 | 2492 | 250 | 0,917 | 4752 |
| Valores a Receber | mobile | 3 | 2 (2–2) | 89 | 13314 | 13314 | 2528 | 1,061 | 17691 |
| Portal da Transparência (descartado) | desktop | 1 de 3 | 89 | 66 | 1843 | 1133 | 50 | 0,002 | 1133 |
| Portal da Transparência (descartado) | mobile | 1 de 3 | 27 | 75 | 8566 | 5447 | 1281 | 0,211 | 5447 |

### 9.3 O que o piloto mostrou sobre o script

1. **O fluxo funciona de ponta a ponta.** Verificação de `robots.txt`, execução sequencial com pausa de 10 s, ordem aleatória com seed gravada, um JSON bruto por execução em `data/raw/pilot/`, metadados completos em `run-metadata.json` (versões, configuração, máquina, horário de cada execução) e o CSV com as colunas pedidas em [`data/processed/pilot.csv`](../data/processed/pilot.csv).
2. **Uma página de bloqueio era contada como medição válida.** O Portal da Transparência serviu um CAPTCHA do AWS WAF a partir da segunda visita. O Lighthouse não trata HTTP 202 como erro e deu nota 97 de desempenho para a página de CAPTCHA. A primeira versão do script aceitou esses resultados. Correção: cada execução agora verifica o status do documento principal; se não for 200, a execução é marcada como `blocked`, sai do CSV principal e as execuções seguintes do serviço na sessão são puladas. O serviço foi trocado (seção 1.4).
3. **O elemento LCP pode ser o banner de cookies.** No gov.br (mobile e desktop) e no Valores a Receber (mobile), o maior elemento foi o texto do banner de consentimento. No gov.br mobile isso gera LCP de ~30,6 s com performance score 58: a nota do LCP é zero, mas TBT e CLS são bons. O script passou a exportar o elemento LCP de cada execução (`pilot_lcp_elements.csv`).
4. **O accessibility score não varia entre execuções** da mesma página e form factor. Por isso a RQ2 usa o serviço como unidade de análise (seção 7.3).
5. **A variação dentro de cada célula foi pequena**: amplitude do performance score de no máximo 6 pontos nas células com 3 execuções válidas. O piloto não cobre variação por horário (uma janela de 15 minutos).
6. **A diferença mobile × desktop apareceu nos três serviços válidos** (gov.br 58 × 69; Meu INSS 25 × 53; Valores a Receber 2 × 24). É só uma indicação: n = 3 e nenhum teste foi feito.
7. **Tamanho dos dados brutos**: média de 601 KB por execução nas 24 execuções (14,1 MB no total). Se os outros serviços tiverem tamanho parecido, as 240 execuções da Sprint 2 darão cerca de 141 MB. Com gzip (nível 9) o tamanho cai para 20%: média de 122 KB por execução, cerca de 28,5 MB para 240.
8. **e-CAC tem conexão instável**: a busca do `robots.txt` falhou na primeira tentativa (ECONNRESET) nas duas verificações, e o servidor não envia o certificado intermediário. O serviço não estava no piloto, então o comportamento do Lighthouse nele ainda não foi observado.
9. **A réplica 1 teve score menor ou igual ao das seguintes.** Em 5 das 6 células válidas, o performance score da primeira execução foi menor que a mediana das seguintes; na sexta (Valores a Receber mobile) foi igual. No LCP não houve padrão (maior em 4 de 6). Com 1 execução contra 2 por célula é só uma indicação, mas reforça a comparação `run = 1` × demais prevista na seção 8.2 (cache de CDN frio).
10. **A segunda regra de bloqueio funciona nos dados do piloto.** Com o status do documento principal trocado para 200 nos 4 JSONs de CAPTCHA, a regra do texto do LCP ("Complete the security check before continuing…") rejeitou os 4 e nenhuma das 20 execuções válidas. O sinal `DOM_SIZE_DROP` também marcaria os 4 (44 elementos DOM contra 1318 a 1800 na página real do Portal da Transparência).
11. **`benchmarkIndex`**: nenhuma execução chegou perto do limiar de 1000 do Lighthouse (mínimo 2582). Duas execuções válidas ficaram abaixo da cerca de Tukey (2814,5 no gov.br mobile e 2581,5 no Portal da Transparência mobile), sem diferença visível no resultado (seção 7.6).

---

## 10. Pendências (TODO)

Situação em 25/11/2026, depois da coleta completa.

| # | Pendência | Seção |
|---|---|---|
| 1 | Portal do Servidor sem número de uso verificável: **NÃO ENCONTRADO** (só a evidência indireta do SouGov.br). Decidido na Sprint 2: fica, com a ressalva. Se aparecer uma fonte verificável, atualizar a seção 1.3. | 1.3 |
| 2 | Portal MG: o número de acessos do portal mais recente continua sendo de 2021 (a busca de 17/11/2026 só achou dados do MG App). Falta decidir se o dado de 2021 basta. | 1.3 |
| 3 | Registrar provedor de internet e cidade da máquina de medição. Tipo de conexão (cabeada, 1 Gbps, sem VPN) e plano de energia estão gravados em cada sessão. | 6.6 |
| 4 | Nenhum bloco à noite: a coleta teve manhã e tarde de um só dia. Se o grupo quiser cobrir a noite, é preciso uma nova fase (com outra seed e outro `plan.json`), porque a fase `full` já está completa. | 6.3, 8.2 |
| 5 | Confirmar com o grupo e o professor os critérios de exclusão e de sensibilidade: exclui `benchmarkIndex` ≤ 1000 (nenhuma execução excluída); cerca de Tukey só em sensibilidade; execuções com métrica nula refeitas. | 7.6 |

Resolvidas na Sprint 2:

- Horários dos blocos: 2 blocos, manhã e tarde de 25/11/2026 (N = 10; ver changelog).
- JSON bruto: guardado no repositório com gzip nível 9 (23 MB para as 200 execuções e as 5 tentativas inválidas).
- Serviços fora do piloto: todos medidos. Nenhum bloqueio; o e-CAC não falhou.
- Marcações de revisão: só 2 `BENCHMARK_LOW_OUTLIER`, nenhuma de bloqueio (`full_flags.csv`; [`data-validation.md`](data-validation.md)).
- Boxplots: gerados em `analysis/figures/`.

Resolvidas na Sprint 1, depois da primeira versão desta proposta: número de uso do e-CAC (1.3); tipo de conexão e plano de energia (6.6); critério para `benchmarkIndex` (proposto em 7.6); segunda regra de detecção de bloqueio (6.5 e 7.6); script de análise estatística (seção 7).

---

## Referências

- Basili, V. R.; Caldiera, G.; Rombach, H. D. (1994). The Goal Question Metric Approach. In: *Encyclopedia of Software Engineering*. Wiley.
- Cliff, N. (1993). Dominance statistics: Ordinal analyses to answer ordinal questions. *Psychological Bulletin*, 114(3), 494–509.
- Dunn, O. J. (1964). Multiple comparisons using rank sums. *Technometrics*, 6(3), 241–252.
- Goodhart, C. A. E. (1975). Problems of monetary management: the U.K. experience. *Papers in Monetary Economics*, Reserve Bank of Australia.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65–70.
- Kerby, D. S. (2014). The simple difference formula: an approach to teaching nonparametric correlation. *Comprehensive Psychology*, 3.
- Kitchenham, B. (2004). *Procedures for Performing Systematic Reviews*. Keele University, TR/SE-0401.
- Kruskal, W. H.; Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *Journal of the American Statistical Association*, 47(260), 583–621.
- Romano, J.; Kromrey, J. D.; Coraggio, J.; Skowronek, J. (2006). Appropriate statistics for ordinal level data: should we really be using t-test and Cohen's d for evaluating group differences on the NSSE and other surveys? Annual Meeting of the Florida Association of Institutional Research.
- Strathern, M. (1997). 'Improving ratings': audit in the British University system. *European Review*, 5(3), 305–321.
- Tomczak, M.; Tomczak, E. (2014). The need to report effect size estimates revisited. *Trends in Sport Sciences*, 1(21), 19–25.
- Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6), 80–83.
- Wohlin, C. et al. (2012). *Experimentation in Software Engineering*. Springer.
- Koster, M.; Illyes, G.; Zeller, H.; Sassman, L. (2022). *RFC 9309: Robots Exclusion Protocol*. IETF.
- Google. Lighthouse — *Lighthouse Variability*. https://github.com/GoogleChrome/lighthouse/blob/main/docs/variability.md (acessado em 17/11/2026).

---

## Changelog

### Sprint 2 (25/11/2026)

Desvios do plano da Sprint 1 e o que mudou neste documento:

| Mudança | Antes (Sprint 1) | Depois (Sprint 2) | Motivo |
|---|---|---|---|
| Número de execuções | N = 12 por serviço e form factor, 240 no total | N = 10, 200 no total | Pedido da Sprint 2 (seção 6.3). |
| Blocos de horário | 3 (manhã, tarde, noite), 4 execuções cada | 2 (manhã e tarde de 25/11/2026), 5 execuções cada | 10 não se divide em 3 blocos iguais. A noite fica como limitação (seção 10, item 4). |
| Fases | Uma fase por bloco (`full-b1`, `full-b2`, …) | Uma fase `full`, com o plano salvo em `data/raw/full/plan.json` (seed 3118576651) | O executor retoma de onde parou e confere se o plano bate com as opções. |
| Rótulo da sessão | — | `--session-label morning\|afternoon\|night` gravado em cada execução | A análise do efeito de horário usa o rótulo. |
| Falhas | Só em `run-metadata.json` | Também em `data/failed-runs.csv`, com motivo; o JSON inválido vai para `data/raw/full/invalid/` | Pedido da Sprint 2. |
| Métrica nula | Não tratada | Execução inválida (`MISSING_VALUES`), registrada e refeita uma vez na sessão | Visto no Consumidor.gov.br (`NO_FCP`): 5 de 205 tentativas (seção 7.6). |
| JSON bruto | Sem compressão | gzip nível 9 (`*.json.gz`), no repositório | 23 MB em vez de ~120 MB (seção 10). |
| Validação | — | `scripts/validate-data.mjs` → [`data-validation.md`](data-validation.md) | Completude, NaN, faixas, duplicatas, pausa ≥ 10 s e sobreposição de sessões. |
| Outliers | Tukey só no `benchmarkIndex` | Tukey também em cada métrica, por serviço × form factor; análise com e sem os valores marcados | Pedido da Sprint 2 (seção 7.6). |
| RQ2 | Spearman nas medianas | Mais: IC 95% por bootstrap e Spearman com todas as execuções (bootstrap por cluster) | Seção 7.3. |
| RQ3 | Wilcoxon entre serviços | Mais: Wilcoxon por serviço, pareado por réplica, com Holm | Seção 7.4. |
| Estatística descritiva | Mediana e IQR | Mais: média, DP, mín., máx. e boxplots | Pedido da Sprint 2 (seção 7.1). |
| Consumidor.gov.br | URL sem observação | Redirecionamento no cliente para `/pages/principal/?<número>` registrado; URL mantida | [`url-changes.md`](url-changes.md); ameaça de construto. |
| Portal do Servidor | TODO: decidir | Fica, com a ressalva; número NÃO ENCONTRADO | Seção 1.3. |

Seções alteradas: cabeçalho, 1.3 (TODO do Portal do Servidor), 6.3, 6.7, 7.1, 7.3, 7.4, 7.5, 7.6, 8.2 (horário), 10 e este changelog. As seções 2 a 5 (perguntas, hipóteses, GQM, entidades e classificação) e 9 (piloto) não mudaram.

### Sprint 3 (26/11/2026)

| Mudança | O que mudou | Onde |
|---|---|---|
| Chrome | A seção 6.6 e a ameaça de User-Agent (8.2) passam a citar o Chrome 158 da coleta completa; o 157 era do piloto | 6.6, 8.2 |
| Valores a Receber | Nota sobre 72 milhões (MGI) contra 73 milhões (Banco Central) | 1.3 |
| Impacto | Modelo de horas de espera por mês, com sensibilidade à parcela de acessos mobile | [`impacto.md`](impacto.md) |
| Categorias | As 7 categorias revisadas contra a execução | [`categorias-pesquisa.md`](categorias-pesquisa.md) |
| Ameaças | Versão final dos 4 tipos, com os resultados das verificações | [`ameacas-validade.md`](ameacas-validade.md) |
| Conclusões | Resposta a cada RQ, limites e o que foi reaproveitado dos laboratórios anteriores | [`conclusoes.md`](conclusoes.md) |
| Auditorias e registros | Sprint 1, Sprint 2, URLs finais, validação e entrega da Sprint 2 | [`audit-sprint1.md`](audit-sprint1.md), [`audit-sprint2.md`](audit-sprint2.md), [`url-changes.md`](url-changes.md), [`data-validation.md`](data-validation.md), [`sprint2-entrega.md`](sprint2-entrega.md) |
