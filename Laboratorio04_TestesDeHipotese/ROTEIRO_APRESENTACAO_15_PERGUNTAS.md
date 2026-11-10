# Roteiro da Apresentação Oral (15 Perguntas) — Laboratório 04

> **Tempo total:** Até 7 minutos (respostas objetivas de ~30 segundos cada).  
> **Apoio visual:** Usar diretamente o **Dashboard interativo** em execução (`http://localhost:8000`).  
> **Distribuição:** 15 perguntas divididas igualmente (5 para cada integrante, cumprindo a exigência de no mínimo 4 por pessoa).

---

## 👥 Divisão das Perguntas entre os Integrantes

* **Maria Clara:** Perguntas **1, 2, 3, 4 e 14** *(Cenário, Coleta Empírica, Distribuição Real e Tamanho de Efeito)*
* **Vinícius:** Perguntas **5, 6, 7, 8 e 15** *(Mecânica Estatística, Distribuição sob H₀, p-Valor, Gravidade de Erros e Recomendação)*
* **Áulus:** Perguntas **9, 10, 11, 12 e 13** *(Erro Tipo I no G3, Curvas de Poder no G4, Violações de Pressupostos e Impacto do α)*

---

## 🎤 Perguntas & Respostas Diretas (com Ancoragem no Dashboard)

### Bloco 1 — Maria Clara (Cenário e Amostra Real)

#### 1. Qual é o cenário de vocês e o que H₀ e H₁ afirmam, em palavras simples?
* **Onde mostrar no Dashboard:** *Seção 1 (Cenário)*.
* **Resposta (~30s):**  
  > *"Nosso cenário compara o desempenho de entrega de software entre repositórios dos tiers DORA de alta performance (Elite e High) e tiers de performance moderada/baixa (Medium e Low), analisando métricas como Lead Time de Commit, MTTR e Frequência de Deploy. Em palavras simples, a hipótese nula H₀ afirma que não há diferença real entre os dois grupos e que qualquer discrepância observada decorre apenas do acaso amostral. Já H₁ afirma que existe diferença sistemática e consistente no comportamento das métricas entre os tiers."*

---

#### 2. O teste de vocês é unicaudal ou bicaudal? Por quê?
* **Onde mostrar no Dashboard:** *Seção 1 (Hipóteses) e Seção 3 (Gráfico G2 com as duas caudas sombreadas)*.
* **Resposta (~30s):**  
  > *"Nosso teste é bicaudal. Embora a intuição sugira que equipes Elite tenham tempos menores, metodologicamente não podemos descartar a priori que repositórios menores ou de outros tiers apresentem menor burocracia ou dinâmicas imprevistas. O teste bicaudal divide o nível α em duas regiões críticas (α/2 = 2,5% em cada cauda), protegendo o estudo contra falsos positivos caso a diferença ocorra em qualquer uma das direções."*

---

#### 3. Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição?
* **Onde mostrar no Dashboard:** *Seção 2 (Gráfico G1 e Tabela de Skewness) ou Anexo (Amostra Real)*.
* **Resposta (~30s):**  
  > *"Coletamos 300 repositórios de código aberto via GitHub API no Laboratório 03, filtrando projetos maduros com histórico consistente de releases e workflows de CI/CD. A análise empírica evidenciou que métricas de tempo em software possuem severa assimetria positiva à direita com caudas longas (coeficiente de assimetria bem acima de 1) e presença marcante de outliers causados por releases esporádicas ou incidentes atípicos, violando fortemente a premissa de normalidade gaussiana."*

---

#### 4. Como os dados reais ajudaram a escolher os parâmetros da simulação?
* **Onde mostrar no Dashboard:** *Seção 2 (Gráfico G1 — ajuste MLE)*.
* **Resposta (~30s):**  
  > *"Em vez de adotarmos parâmetros arbitrários, usamos Máxima Verossimilhança (MLE) sobre os dados reais para calibrar a distribuição Lognormal sintética. Preservamos a mediana empírica (aproximadamente 10 unidades de tempo) e ajustamos o parâmetro de dispersão logarítmica σ para 1.0. Isso garantiu que nossa simulação gerasse amostras sintéticas com a mesma assimetria e escala de dispersão observadas na prática."*

---

### Bloco 2 — Vinícius (Mecânica dos Testes, H₀ e Decisão)

#### 5. O que cada um dos dois testes compara de fato (médias, postos, proporções...)?
* **Onde mostrar no Dashboard:** *Seção 3 (Como os testes funcionam)*.
* **Resposta (~30s):**  
  > *"O teste t de Welch compara a igualdade das médias populacionais (μ₁ = μ₂), corrigindo os graus de liberdade via fórmula de Welch-Satterthwaite para não exigir variâncias iguais. Já o teste de Mann-Whitney U é não-paramétrico e compara postos ordenados: ele avalia a probabilidade de uma observação de um grupo superar aleatoriamente uma observação do outro grupo (P(X > Y)), funcionando na prática como uma comparação robusta entre medianas ordinais."*

---

#### 6. No G2: o que é a distribuição da estatística sob H₀, e por que a região de rejeição fica onde fica?
* **Onde mostrar no Dashboard:** *Seção 3 (Gráfico G2 — Curva e Regiões Vermelhas)*.
* **Resposta (~30s):**  
  > *"A curva do G2 mostra os valores possíveis que a estatística do teste (t ou Z) assumiria se a hipótese nula fosse estritamente verdadeira ao longo de infinitas amostras. A região de rejeição fica nas extremidades das caudas porque sob H₀ é muito improvável obter estatísticas padronizadas distantes de zero. Definimos as fronteiras nos valores críticos onde a área acumulada nas pontas totaliza exatamente α = 5% (2,5% em cada extremidade)."*

---

#### 7. O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa?
* **Onde mostrar no Dashboard:** *Seção 3 (Linha destacada da estatística observada e p-valor)*.
* **Resposta (~30s):**  
  > *"O p-valor é a probabilidade de observar uma estatística tão ou mais extrema que a calculada na nossa amostra, supondo que H₀ seja verdadeira. Como nosso p foi infinitesimalmente pequeno (p < 0,001), é quase impossível que tal diferença resulte do acaso. Crucialmente, o p-valor NÃO significa a probabilidade de H₀ ser verdadeira, tampouco quantifica a magnitude ou a relevância prática do efeito verificado."*

---

#### 8. No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual dos dois seria mais grave?
* **Onde mostrar no Dashboard:** *Seção 1 (Cenário) e Seção 4 (Erro Tipo I)*.
* **Resposta (~30s):**  
  > *"Erro Tipo I seria afirmar que os tiers DORA possuem desempenhos diferentes quando, na verdade, seus tempos são equivalentes (falso positivo). Erro Tipo II seria concluir que não há diferença quando existe uma vantagem real dos tiers Elite (falso negativo). No nosso contexto de experimentação de software, o Erro Tipo I é mais grave, pois induziria empresas a despenderem recursos expressivos em reestruturações caras acreditando em um ganho inexistente."*

---

### Bloco 3 — Áulus (Simulações Q1, Q2, Q3 e Análise de Poder)

#### 9. No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê?
* **Onde mostrar no Dashboard:** *Seção 4 (Gráfico G3)*.
* **Resposta (~30s):**  
  > *"No G3, o teste de Mann-Whitney U manteve-se rigorosamente aderente ao nível nominal de 5% em todos os cenários (oscilando entre 4,3% e 4,8%). Já o teste t de Welch revelou-se conservador sob assimetria severa e presença de outliers, rejeitando em apenas ~2,6% a 3,7% das vezes. Isso ocorre porque os outliers na cauda longa inflam drasticamente o desvio padrão amostral no denominador da estatística t, reduzindo o valor de t e tornando o teste paramétrico excessivamente cauteloso."*

---

#### 10. No G4, qual teste tem mais poder? A diferença entre eles muda conforme o tamanho do efeito?
* **Onde mostrar no Dashboard:** *Seção 5 (Gráfico G4)*.
* **Resposta (~30s):**  
  > *"No cenário base realista e sob violações, o Mann-Whitney U tem substancialmente mais poder que o Welch. Ele alcança o limiar recomendado de 80% de poder com um efeito δ ≈ 0,7, enquanto o Welch necessita de δ próximo a 0,95 para a mesma sensibilidade. Para efeitos diminutos (δ < 0,2) ambos detectam pouco; para efeitos gigantescos (δ > 1,5) ambos convergem para 100%, mas na faixa intermediária de relevância prática a superioridade do Mann-Whitney é expressiva."*

---

#### 11. Que violação de pressuposto vocês simularam, e por que ela afeta mais um teste do que o outro?
* **Onde mostrar no Dashboard:** *Seção 4 (G3) e Seção 5 (G4 nos seletores de Violação)*.
* **Resposta (~30s):**  
  > *"Simulamos assimetria extrema (σ = 1.6), amostras pequenas (N = 12) e contaminação por outliers (10% das observações multiplicadas por 8x). Os outliers afetam muito mais o teste t de Welch porque a média e a variância amostral são altamente sensíveis a valores extremos quadráticos, achatando a estatística t. Já o Mann-Whitney ordena postos, transformando um valor 8 vezes maior simplesmente no maior posto do ranking, mantendo sua sensibilidade intacta."*

---

#### 12. Se vocês usassem α = 0,01 em vez de 0,05, o que mudaria no G3 e no G4?
* **Onde mostrar no Dashboard:** *Barra de Filtros (selecionando α = 0.01) e Seção 4/5*.
* **Resposta (~30s):**  
  > *"Ao reduzir α de 0,05 para 0,01, o nível de exigência aumenta: a linha de referência no G3 desce para 1%, reduzindo os falsos positivos permitidos. Em contrapartida, no G4 as curvas de poder de ambos os testes se deslocam para baixo e para a direita, exigindo tamanhos de efeito consideravelmente maiores para alcançar 80% de poder. O teste de Mann-Whitney, contudo, continua mantendo sua vantagem relativa sobre o Welch."*

---

#### 13. A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença?
* **Onde mostrar no Dashboard:** *Seção 7 (Conclusão — Card de Expectativa vs. Descoberta)*.
* **Resposta (~30s):**  
  > *"Não confirmou totalmente. Inicialmente, esperávamos que o Teorema Central do Limite garantisse razoável robustez ao teste t em N=30, mesmo sob assimetria. Embora o erro Tipo I tenha permanecido controlado (ficando conservador), a perda severa de poder estatístico frente a dados assimétricos nos surpreendeu negativamente. O Mann-Whitney provou ser muito superior operacionalmente do que havíamos antecipado."*

---

### Bloco 4 — Fechamento (Maria Clara e Vinícius)

#### 14. Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática?
* **Onde mostrar no Dashboard:** *Seção 6 (Tabela de Dados Reais)*.
* **Responsável:** Maria Clara  
* **Resposta (~30s):**  
  > *"Sim, nos dados reais ambos rejeitaram H₀ com p < 0,001 para Lead Time de Commit e Frequência de Deploy. O tamanho do efeito foi fundamental: calculamos Cohen's d = -1,78 e Cliff's δ = -0,89, ambos classificados como 'Grandes'. Isso comprova que a diferença detectada não é um mero artefato do tamanho da amostra (N=300), mas representa um abismo prático real: repositórios de alta performance entregam valor com ciclos consideravelmente mais curtos."*

---

#### 15. Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal limitação do estudo?
* **Onde mostrar no Dashboard:** *Seção 7 (Conclusão — Recomendações e Limitações)*.
* **Responsável:** Vinícius  
* **Resposta (~30s):**  
  > *"Recomendamos com segurança o teste não-paramétrico de Mann-Whitney U para métricas de tempo e qualidade em Engenharia de Software por sua robustez a outliers e maior poder sob assimetria. Mudaríamos a recomendação para o teste t de Welch apenas em variáveis com distribuição comprovadamente simétrica e normal (como questionários padronizados) ou se a média contábil absoluta fosse o único interesse de negócio. A principal limitação do estudo reside no uso exclusivo de repositórios open-source com deploys contínuos, exigindo cautela ao extrapolar para ambientes corporativos fechados."*

---

## ⏱️ Dicas de Ensaio para o Limite de 7 Minutos
1. Mantenha o dashboard aberto e navegando com o mouse diretamente na seção correspondente enquanto fala.
2. Não leia a pergunta na íntegra; comece direto pela resposta conectada ao gráfico da tela.
3. Cada membro consome em média 2 minutos e 15 segundos, permitindo encerrar com segurança em 6 minutos e meio.
