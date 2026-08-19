## 🔎 Perguntas de Pesquisa (Research Questions) e Hipóteses

Abaixo estão listadas as questões de pesquisa definidas para este laboratório, juntamente com as métricas avaliadas e as hipóteses (argumentos a favor e contra) levantadas para cada cenário.

### RQ 01. Sistemas populares são maduros/antigos?

* **Métrica:** Idade do repositório (calculada a partir da data de sua criação).
* **Teoria:** Não necessariamente ser antigo significa ser maduro, pois, às vezes, um sistema pode ser antigo, mas ainda apresentar falta de maturidade por não ter sido atualizado ao longo do tempo, podendo até ter sido esquecido ou deixado de receber manutenção.

**🟢 A favor:**
* Sistemas mais antigos tiveram muito mais tempo para divulgar seu trabalho, construir uma comunidade sólida e acumular usuários (estrelas/forks), o que naturalmente impulsiona a sua popularidade ao longo dos anos.
* O tempo de vida longo muitas vezes permite que o sistema passe por diversas refatorações, alcançando uma estabilidade que atrai ainda mais a adoção em larga escala.

**🔴 Contra:**
* Conforme a teoria aponta, idade não garante manutenção; um repositório antigo pode ser popular pelo seu histórico, mas estar obsoleto hoje.
* Sistemas muito recentes podem explodir em popularidade rapidamente (viralizar) por resolverem problemas muito modernos ou utilizarem tecnologias em alta, atingindo o topo de popularidade sem ter "idade" ou maturidade de longo prazo.

---

### RQ 02. Sistemas populares recebem muita contribuição externa?

* **Métrica:** Total de *pull requests* aceitas.
* **Teoria:** A grande visibilidade de um repositório atrai desenvolvedores do mundo todo, o que tende a resultar em um alto volume de tentativas de melhorias e correções submetidas pela própria comunidade.

**🟢 A favor:**
* Quanto mais desenvolvedores utilizam a ferramenta no dia a dia, maior a chance de encontrarem bugs, casos de uso não previstos ou necessidades de novas funcionalidades, resultando na abertura de *Pull Requests*.
* Participar de projetos populares traz prestígio para o portfólio de um desenvolvedor, incentivando a comunidade externa a contribuir ativamente.

**🔴 Contra:**
* Projetos muito populares podem ter um nível de exigência altíssimo (testes complexos, arquitetura robusta, regras estritas do *core team*), criando uma barreira de entrada que dificulta a aceitação de PRs de pessoas de fora.
* Alguns repositórios gigantes são mantidos quase inteiramente por funcionários de grandes empresas (ex: Google, Meta), tornando a contribuição externa percentualmente muito pequena em relação ao trabalho interno.

---

### RQ 03. Sistemas populares lançam releases com frequência?

* **Métrica:** Total de *releases*.
* **Teoria:** Sim, pois sempre há algo a melhorar, aprimorar ou corrigir no sistema. A forte adoção pela comunidade impulsiona os desenvolvedores a continuarem trabalhando no projeto e entregando versões novas.

**🟢 A favor:**
* O alto fluxo de feedback da grande base de usuários (relatos de bugs e pedidos de *features*) força os mantenedores a adotarem integrações contínuas, resultando em pacotes e versões atualizadas frequentemente para corrigir falhas e adicionar melhorias.
* Projetos populares geralmente possuem mais braços trabalhando (seja comunidade ou equipe dedicada), permitindo um ciclo ágil de lançamentos.

**🔴 Contra:**
* Sistemas extremamente populares, principalmente aqueles usados como base para outras aplicações (*frameworks* e bibliotecas *core*), muitas vezes adotam ciclos de lançamento mais lentos e conservadores para evitar o lançamento de *breaking changes* (mudanças que quebram o código de quem usa).
* Uma frequência excessiva de *releases* pode gerar fadiga na comunidade de usuários, que precisa constantemente atualizar dependências para não ficar para trás.

---

### RQ 04. Sistemas populares são atualizados com frequência?

* **Métrica:** Tempo até a última atualização.

**🟢 A favor:**
* Por mais pessoas conhecerem, provavelmente há mais contribuição para manter o repositório atualizado e acompanhando as novas tecnologias (quando possível).
* Novas pessoas encontram o sistema e possuem novas visões de contribuições/oportunidades de melhorias.

**🔴 Contra:**
* Os mais populares já atingiram um ponto ótimo de maturidade e suas atualizações são apenas correções quando estritamente necessárias, resultando em uma baixa frequência de atualizações gerais.

---

### RQ 05. Sistemas populares são escritos nas linguagens mais populares?

* **Métrica:** Linguagem primária de cada repositório.
> *Nota: A fonte usada para definir "linguagens mais populares" deve ser referenciada explicitamente (ex.: TIOBE Index, GitHut ou o Octoverse do GitHub) e mantida como padrão ao longo de todo o laboratório.*

**🟢 A favor:**
* Uma linguagem mais popular é mais acessível por haver mais fontes de estudo.
* A linguagem se torna mais famosa pelo grande número de sistemas, assim um fator impulsiona o outro (há mais sistemas na linguagem mais popular justamente por ter mais material de estudo e estruturas prontas para uso da mesma linguagem).

---

### RQ 06. Sistemas populares possuem um alto percentual de issues fechadas?

* **Métrica:** Razão entre *issues* fechadas e total de *issues*.

**🟢 A favor:**
* Com um maior número de usuários interagindo com o repositório, naturalmente haverá mais contribuições e mobilização para resolver as *issues* que ainda estiverem em aberto, aumentando o percentual de fechamento.

---

### 🏆 Bônus (+1 ponto) — RQ 07. Influência da linguagem na atividade

**Pergunta:** Sistemas escritos em linguagens mais populares recebem mais contribuição externa, lançam mais *releases* e são atualizados com mais frequência?

* **Diretriz:** Para responder, cruze e divida os resultados obtidos nas **RQs 02, 03 e 04**, agrupando-os por linguagem de programação.