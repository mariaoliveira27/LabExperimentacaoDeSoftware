# Impacto: quanto tempo de espera o LCP mobile soma por mês

Esta estimativa converte o resultado da RQ3 em horas. É um modelo com premissas à vista, não uma medição de usuários reais. Ela cobre **3 dos 10 serviços**: os que têm um número público de uso que conta carregamentos da página (acessos ao site ou consultas). Os outros 7 ficaram de fora porque não há número verificável (seção 5), e nada foi estimado para eles.

Leia o total como um **piso para esses três serviços**, e não como o tempo de espera do gov.br. Os três serviços com pior LCP mobile (Meu SUS Digital, 33,9 s; Portal gov.br, 29,7 s; Portal do Servidor, 22,0 s) não têm número de uso utilizável e por isso não entram na soma.

## 1. Resultado central

Cenário: todo acesso é mobile, e o tempo extra é o LCP mobile menos a mediana do LCP desktop do próprio serviço (referência "a"). Horas por mês, no cenário baixo (percentil 25 do LCP), central (mediana) e alto (percentil 75).

| Serviço | Número de uso usado | Eventos por mês | LCP mobile (mediana) | Referência (LCP desktop) | Extra por acesso | Horas por mês (baixo / central / alto) | Parte do total |
|---|---|---|---|---|---|---|---|
| Meu INSS | 123,4 milhões de acessos pelo site em 2024 | 10,3 milhões | 15,80 s | 3,19 s | 12,61 s | 32.379 / 36.030 / 36.456 | 67% |
| Valores a Receber | 73,0 milhões de consultas públicas em 2024 | 6,1 milhões | 13,40 s | 5,91 s | 7,49 s | 12.418 / 12.661 / 12.848 | 24% |
| Portal MG | 21,0 milhões de acessos ao portal em 2021 | 1,8 milhões | 12,68 s | 2,78 s | 9,90 s | 4.794 / 4.814 / 4.833 | 9% |
| **Total** | | | | | | **49.590 / 53.505 / 54.137** | 100% |

O total central, 53.505 horas por mês, equivale a cerca de 6,1 anos de espera somados a cada mês. O Meu INSS sozinho responde por 67% dele.

A faixa entre o cenário baixo e o alto é estreita (de −7% a +1% do total central) porque as 10 execuções de cada serviço variam pouco entre si. Ela mede a incerteza da medição do Lighthouse, e **não** a incerteza do impacto. A incerteza do impacto está nas premissas da seção 4 e na parcela de acessos mobile (seção 3).

## 2. Contra o limite de 2,5 s

Referência "b": o limiar de LCP "bom" da web.dev, 2,5 s ([web.dev/articles/lcp](https://web.dev/articles/lcp), página atualizada em 04/09/2025, acessada em 26/11/2026). O tempo extra é o que passa de 2,5 s, no mobile e no desktop.

| Serviço | Mobile: horas por mês (baixo / central / alto) | Desktop: horas por mês (baixo / central / alto) |
|---|---|---|
| Meu INSS | 34.343 / 37.994 / 38.420 | 1.791 / 1.964 / 2.033 |
| Valores a Receber | 18.173 / 18.416 / 18.604 | 5.666 / 5.756 / 5.900 |
| Portal MG | 4.930 / 4.950 / 4.969 | 129 / 136 / 144 |
| **Total** | **57.446 / 61.360 / 61.993** | **7.586 / 7.856 / 8.077** |

Mesmo no desktop os três serviços passam de 2,5 s, e o Valores a Receber passa por mais de 3 s. A diferença entre as duas colunas é o custo do mobile.

## 3. Sensibilidade à parcela de acessos mobile

Os números públicos de uso não dizem quantos acessos vêm de celular (só o Meu INSS separa site de aplicativo, e o "site" pode incluir navegadores de celular). Por isso o resultado da seção 1, com 100% mobile, é o **teto** do modelo, e não uma previsão. A tabela mostra o total (horas por mês, cenário central e, entre parênteses, baixo e alto) para três parcelas.

| Parcela de acessos mobile | Referência "a" (LCP desktop do próprio serviço) | Referência "b" (2,5 s) |
|---|---|---|
| 0% | 0 (0 a 0) | 7.856 (7.586 a 8.077) |
| 50% | 26.752 (24.795 a 27.069) | 34.608 (32.516 a 35.035) |
| 100% | 53.505 (49.590 a 54.137) | 61.360 (57.446 a 61.993) |

Com a referência "a", 0% mobile dá zero por construção, porque o desktop é a própria referência. Com a referência "b", 0% mobile mostra o que sobra mesmo sem celular. Por serviço, com a referência "b" (horas por mês, cenário central):

| Serviço | 0% mobile | 50% mobile | 100% mobile |
|---|---|---|---|
| Meu INSS | 1.964 | 19.979 | 37.994 |
| Valores a Receber | 5.756 | 12.086 | 18.416 |
| Portal MG | 136 | 2.543 | 4.950 |

## 4. Como o número é calculado

```
eventos_por_mês = número de uso / meses do período        (distribuição uniforme no período)
extra_s         = max(0, LCP − referência) / 1000
horas_por_mês   = extra_s × eventos_por_mês / 3600
```

O LCP vem de `data/processed/full.csv`, no percentil 25, na mediana e no percentil 75 das 10 execuções de cada serviço e form factor. Os números de uso vêm de `data/usage.json`. O código está em `analysis/impact.py` e a saída em `analysis/output/impact.csv` e `analysis/output/impact_sensitivity.csv`.

Premissas, todas simplificações:

1. **Um acesso é um carregamento da página medida.** O Meu INSS conta acessos ao site; o Portal MG conta acessos ao portal; o Valores a Receber conta consultas públicas. Para o Valores a Receber essa é a premissa mais fraca: a página medida é a do Meu BC sobre o serviço (`bcb.gov.br/meubc/valores-a-receber`), e as consultas rodam no sistema em `valoresareceber.bcb.gov.br`. Uma consulta não é, necessariamente, um carregamento da página medida.
2. **Primeira visita, sem cache.** O Chrome começa limpo a cada execução. Quem volta ao serviço carrega menos coisa.
3. **O LCP é só o primeiro quadro.** Ele não mede o tempo até a pessoa conseguir fazer o que foi fazer. Em alguns serviços o elemento LCP nem é o conteúdo: no Valores a Receber mobile é o banner de cookies, e no Meu INSS é o aviso "INSS no ar" (`analysis/results.md`, seção 8). O tempo "esperado" é o tempo até esse elemento aparecer.
4. **Throttling simulado.** O LCP é uma estimativa do modelo do Lighthouse para um Moto G Power emulado e uma rede lenta simulada, não o tempo de um celular real.
5. **Páginas de entrada.** Para Meu INSS, a página medida é a de login (`#/login`). Quem já está logado vê outra tela.
6. **Anos diferentes.** Os números de uso são de 2024 (Meu INSS, Valores a Receber) e de 2021 (Portal MG, de antes do lançamento do novo portal, em fevereiro de 2022). O uso atual pode ser outro.
7. **Cada serviço soma na própria unidade.** Acessos, consultas e visitas não são a mesma coisa, então o total mistura unidades e serve como ordem de grandeza.

## 5. Números de uso e fontes

Entram na conta (acesso em 26/11/2026):

| Serviço | Número | O que conta | Fonte | Conferência |
|---|---|---|---|---|
| Meu INSS | 123.400.000 acessos pelo site (2024) | Acessos à plataforma Meu INSS pelo site (web), separados dos 707,4 milhões pelo aplicativo. Total de 830,8 milhões no ano. | [INSS, 08/01/2025](https://www.gov.br/inss/pt-br/noticias/meu-inss-bateu-a-marca-de-830-8-milhoes-de-acessos-no-ano-passado) | Texto conferido em republicações da notícia do INSS (contadores.cnt.br, 09/01/2025, e outras). **TODO:** abrir a página do gov.br e conferir a citação. |
| Valores a Receber | 73.000.000 consultas públicas (2024) | Consultas públicas ao Sistema de Valores a Receber (25 milhões positivas, 48 milhões negativas). Conta consultas, não acessos nem pessoas. | [Banco Central, coletiva de 26/05/2025, slide 9](https://www.bcb.gov.br/conteudo/home-ptbr/TextosApresentacoes/IzabelaCorrea_coletiva_26_5_25.pdf) | Conferido no PDF do Banco Central: "Consultas públicas do SVR em 2024: 73 milhões" (25 milhões positivas, 48 milhões negativas). A nota do MGI de 14/02/2025 fala em 72 milhões; usou-se o número do próprio BC. |
| Portal MG | 21.000.000 acessos ao portal (2021) | Acessos ao Portal MG em 2021, antes do relançamento do portal em fevereiro de 2022. Não há número mais recente do portal. | [Agência Minas, 17/01/2022](https://www.agenciaminas.mg.gov.br/news/pdf/112553.pdf) | Conferido: "o Portal MG recebeu cerca de 21 milhões de acessos ao longo do ano" (2021). A mesma agência dá 17,3 milhões para 2020. |

Meu INSS: o total de 2024 é 830,8 milhões (707,4 milhões pelo aplicativo e 123,4 milhões pelo site). Só os 123,4 milhões entram na conta. A página do INSS traz também 830.954.731 numa tabela anual. Um ofício da Dataprev ao Senado (05/09/2025) informa 872,7 milhões em 2024, sem separar site e aplicativo; essa fonte não foi aberta aqui e não é usada.

Ficam fora da conta, com **NÃO ENCONTRADO** para o número que serviria:

| Serviço | Por que não entra |
|---|---|
| Portal gov.br | O número publicado ("1 bilhão de acessos", jan. e fev. de 2026) não diz se conta visitas à página ou entradas com login, e o relatório mensal do portal exige login. Acessos à página medida: NÃO ENCONTRADO. |
| Receita Federal (e-CAC) | 875 milhões é o total de serviços prestados pelo canal e-CAC em 2023, não acessos. Acessos à página medida: NÃO ENCONTRADO. |
| Carteira de Trabalho Digital | Os números oficiais são de acessos ao aplicativo ou ao aplicativo e ao portal juntos. Acessos ao canal web medido: NÃO ENCONTRADO. |
| Meu SUS Digital | Só há números do aplicativo. Acessos à versão web medida: NÃO ENCONTRADO. |
| Consumidor.gov.br | Só há cadastros (8,6 milhões, acumulado) e reclamações. Acessos ao site: NÃO ENCONTRADO. |
| ENEM (Inep) | Só há inscrições (5.051.345 no Enem 2026). Acessos à página medida: NÃO ENCONTRADO. |
| Portal do Servidor | Nenhum número de uso verificável: NÃO ENCONTRADO. Fica na pesquisa, com a ressalva (proposta, seção 1.3). |

## 6. O que não dá para afirmar

1. **Que o gov.br gasta tantas horas.** A conta cobre 3 serviços de 10. Ela não diz nada sobre o conjunto dos serviços do governo (validade externa).
2. **Que esse é o tempo de espera de cidadãos reais.** O LCP é emulado e simulado, medido de uma máquina e de uma rede só. Celulares reais e redes reais podem dar mais ou menos.
3. **Quantas dessas horas são de mobile.** Os números de uso não separam o dispositivo. O resultado central é o teto; a seção 3 mostra a faixa.
4. **Que os serviços "mais lentos" são os mais custosos.** Os piores LCP (Meu SUS Digital, Portal gov.br, Portal do Servidor) ficaram de fora por falta de número de uso.
5. **Que o número de 2021 do Portal MG vale hoje.** Ele pesa 9% do total; sem ele, o total cai para cerca de 48,7 mil horas por mês (cenário central, referência "a").
6. **Causalidade com a acessibilidade (RQ2).** O impacto trata só de desempenho; a RQ2 ficou inconclusiva.
7. **Uma comparação entre serviços pelo total.** Os números de uso têm unidades e anos diferentes (seção 4, premissas 6 e 7).

## 7. Como refazer

```
.venv/Scripts/python analysis/impact.py        # só o impacto
.venv/Scripts/python analysis/run_all.py       # tudo, inclusive o impacto
```
