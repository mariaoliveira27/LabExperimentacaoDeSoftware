# Conclusões e limitações

Os números vêm de [`analysis/results.md`](../analysis/results.md) (200 execuções válidas, 25/11/2026) e de [`impacto.md`](impacto.md). Eles foram conferidos por um cálculo independente (`analysis/check_results.py`, só numpy e pandas), que bate com o `results.md` nas estatísticas que recalcula: Kruskal–Wallis, ε², Spearman entre as medianas, medianas e diferenças do LCP e do score.

O estudo responde duas perguntas: o que ele mostrou, e o que isso significa para quem usa esses serviços.

## 1. O que o estudo mostrou

**RQ1. O desempenho varia entre os serviços? Quais são os piores?**
Varia muito. O Kruskal–Wallis dá p < 0,001 (Holm) nos 4 casos (performance score e LCP, mobile e desktop), com ε² de 0,85 a 0,96. Os piores:

| Medida | Piores serviços |
|---|---|
| LCP mobile (mediana) | Meu SUS Digital, 33,9 s; Portal gov.br, 29,7 s; Portal do Servidor, 22,0 s; Meu INSS, 15,8 s |
| Performance score mobile (mediana) | Valores a Receber, 1; Meu INSS, 23,5; Meu SUS Digital, 25 |
| LCP desktop | Meu SUS Digital, 8,0 s |

O melhor LCP mobile é o da Receita Federal (6,2 s), e ele ainda é mais que o dobro do limite de 2,5 s considerado "bom" pela web.dev. Nenhum dos 10 serviços fica abaixo de 2,5 s no mobile.

**RQ2. Serviços com pior desempenho têm pior acessibilidade?**
Inconclusivo. O ρ de Spearman entre as medianas é 0,41 (mobile) e 0,48 (desktop), no sentido esperado, mas com n = 10 o p (Holm) é 0,33 e o IC 95% por bootstrap vai de cerca de −0,3 a 0,9. Não dá para dizer que existe associação nem que não existe. O accessibility score é constante dentro de 18 dos 20 grupos, então ele separa serviços, mas pouco. O caso mais claro é o Meu SUS Digital, que tem o pior accessibility score (70 no mobile, 78 no desktop) e um dos piores desempenhos; a Receita Federal vai no sentido oposto (o melhor desempenho no desktop, 98, e accessibility 81).

**RQ3. Quanto o mobile é pior que o desktop?**
O LCP mobile é maior nos 10 serviços: mediana de 13,7 s contra 3,6 s, com mediana das diferenças de 9,4 s (Wilcoxon pareado, W = 0, p Holm = 0,004, rank-biserial = 1,00). A mediana das razões por serviço é 4,8×; a razão entre as duas medianas é 3,8× (a mediana das razões por serviço não é a razão entre as duas medianas). No performance score a mediana das diferenças é −19,2 pontos (p Holm = 0,004). A única inversão no score é o Meu SUS Digital, que tem score mobile maior que o desktop (25 contra 15,5).

## 2. O que isso significa para quem usa

- **Quem abre estes serviços num celular espera bem mais que num computador.** No preset mobile do Lighthouse, a primeira tela leva 4,8 vezes mais tempo, na mediana dos serviços. O melhor serviço ainda passa de 6 s.
- **Em horas por mês**, com os serviços que têm número público de uso (Meu INSS, Valores a Receber e Portal MG), o modelo dá cerca de 53,5 mil horas de espera por mês no cenário em que todo acesso é mobile (faixa de 49,6 mil a 54,1 mil), e cerca de 26,8 mil horas se metade dos acessos for mobile. É um piso para esses três: os três serviços com pior LCP não têm número de uso utilizável e não entram na soma. Detalhes e premissas em [`impacto.md`](impacto.md).
- **Para quem mantém os serviços**, o resultado aponta onde olhar primeiro: Meu SUS Digital, Portal gov.br e Portal do Servidor no LCP mobile, Valores a Receber no score mobile. Em dois dos serviços citados (Portal gov.br e Valores a Receber no mobile) o elemento LCP é o banner de cookies, então o LCP deles mede quando o aviso aparece, não o conteúdo do serviço. O estudo não mostra por que os serviços são lentos, porque não observa o código nem a infraestrutura.

## 3. O que o estudo não mostra

1. **Que serviços do governo em geral são lentos.** São 10 páginas de entrada escolhidas por conveniência. O ε² alto vem em parte de as repetições da mesma página variarem pouco (IQR do LCP de 0,01 a 2,5 s). O teste mostra que estas páginas diferem entre si, e a pseudo-replicação não deixa ir além disso (validade de conclusão e externa).
2. **Que celulares reais esperam esses tempos.** O mobile é um Moto G Power emulado, com throttling simulado, medido de uma máquina e de uma rede só (validade de construto e externa).
3. **Que há relação entre desempenho e acessibilidade** (RQ2 inconclusiva), ou que um provoca o outro.
4. **Que o serviço, depois do login, tem o mesmo desempenho.** Quatro das dez páginas são telas de login ou anteriores ao login.
5. **Que o resultado vale em outro horário ou outro dia.** Só há manhã e tarde de um dia. Não há noite.
6. **O tempo de espera do gov.br.** As horas por mês cobrem 3 serviços, sob 7 premissas.
7. **A causa da lentidão.** O estudo descreve e compara. Não há manipulação do serviço.

Nenhum desses limites muda a resposta às três RQ. Eles definem a que universo as respostas se aplicam: estas 10 páginas, no Lighthouse 13.6.0 com Chrome 158, em 25/11/2026.

## 4. Armadilhas de medição da disciplina que apareceram

- **Lei de Goodhart.** O performance score é uma média ponderada que muitas equipes tratam como meta. Uma página pode subir de score sem melhorar a experiência. O Valores a Receber tem score mobile 1 e LCP de 13,4 s, e o elemento LCP dele no mobile é o banner de cookies: o número resume mal o que a pessoa vê. Por isso o LCP em milissegundos é a medida principal na RQ3 e o score aparece ao lado, não sozinho.
- **Falácia de McNamara.** O que o Lighthouse mede com facilidade (LCP, score) não é tudo o que importa para quem usa. Ele não mede se a pessoa conseguiu fazer a tarefa. As conclusões falam de carregamento da página de entrada.
- **Escalas.** Tempos (LCP, FCP, TBT, Speed Index) são razão: dá para dizer "4,8 vezes". Os scores são tratados como ordinais: usa-se mediana, postos e testes de postos, e a diferença de 10 pontos não vale igual em todo o intervalo. Por isso os testes são Kruskal–Wallis, Dunn, Spearman e Wilcoxon, e o tamanho do efeito é ε², δ de Cliff e rank-biserial.
- **Pseudo-replicação**, descrita acima, é a armadilha estatística mais séria do estudo: 100 execuções por form factor não são 100 unidades independentes.

## 5. O que foi reaproveitado dos laboratórios anteriores e o que foi novo

| Laboratório | Relação com o Lab05 |
|---|---|
| Lab01 | A ideia de coleta automatizada e de guardar o dado bruto no repositório. Aqui a fonte é o Lighthouse, não a API do GitHub, e o código é novo. |
| Lab02 | O desenho com tratamento: o form factor é o tratamento e a ordem das execuções é sorteada, com seed registrada. Aqui não há participantes. |
| Lab03 | **Sem relação direta.** As métricas DORA tratam de entrega de software; o Lab05 mede o carregamento de páginas em produção. Não se aplicou nada do Lab03. |
| Lab04 | A escolha do teste de hipótese pelo tipo de dado e pela distribuição (não paramétricos, correção de Holm, tamanho de efeito) e o formato de dashboard para a apresentação. **TODO:** confirmar com o grupo quanto do código do Lab04 é reaproveitado no dashboard. |

Novo neste laboratório: o instrumento (Lighthouse), a verificação de `robots.txt` e as regras de ética de medição externa, a detecção de bloqueio anti-bot, a validação automática dos dados, o modelo de impacto e o estudo com serviços em produção.

## 6. Pendências que continuam abertas

| # | Pendência |
|---|---|
| 1 | Registrar o provedor de internet e a cidade da máquina de medição ([`ameacas-validade.md`](ameacas-validade.md), validade externa). |
| 2 | Decidir se cobre a noite: seria uma nova fase, com outra seed e outro `plan.json`. |
| 3 | Confirmar com o grupo e o professor os critérios de exclusão e de sensibilidade (proposta, seção 7.6). |
| 4 | Gerar as tabelas oficiais da análise sem os serviços com banner de cookies: `analyze.py --exclude-services govbr,svr-bcb`. |
| 5 | Abrir a página do INSS no gov.br e conferir a citação dos 123,4 milhões de acessos pelo site ([`impacto.md`](impacto.md), seção 5). |
| 6 | Portal do Servidor segue com número de uso **NÃO ENCONTRADO**. |
