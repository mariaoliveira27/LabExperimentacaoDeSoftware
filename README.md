# Laboratório de Experimentação De Software

---
## 📂 Estrutura de Pastas

Descreva o propósito das pastas principais.

```
.
├── /Laboratorio01_GitHubRepo              # 📂 Projeto de Laboratório 01
│   ├── /CSV-100                           # 📄 CSVs gerados pelos códigos de 100 requisições
│   ├── /CSV-1000                          # 📄 CSVs gerados pelos códigos de 1000 requisições
│   ├── /dashboard                         # 📄 Dashboard com gráficos e analise das RQs
│   ├── /Graficos-100                      # 📊 CSVs gerados pelos códigos de 100 requisições
│   └── /Graficos-1000                     # 📊 CSVs gerados pelos códigos de 1000 requisições
│
├── /Laboratorio02_TrialsIA                # 📂 Projeto de Laboratório 02
│   ├── /casos_de_teste                    # 🎯 Executor e base JSON dos testes (RQ2)
│   │   └── /aceitacao_k05_k06             # Contratos e validação dos casos de Áulus (#31)
│   ├── /consolidacao                      # 📁 Scripts e dados de consolidação dos resultados
│   ├── /cronometro                        # ⏱️ Coordenador de rodadas, tempo e integração (RQ1)
│   │   ├── /src                           # 💻 Código fonte do cronômetro e coordenador
│   │   └── /exemplos                      # 🧪 Soluções demonstrativas para validação
│   ├── /dashboard                         # 📊 Dashboard web para visualização dos resultados
│   ├── /graficos                          # 📈 Gráficos gerados para análise
│   ├── /metricas_estruturais              # 📏 Coletor Radon, testes e demonstração (RQ3, #31)
│   ├── /Katas                             # 🧩 Katas selecionadas para as trials
│   └── /solucoes_das_Katas                # 🧩 Soluções das Katas, tanto manuais quanto geradas por IA
│ 
├── /Laboratorio03_MineracaoDeMetricasDORA # 📂 Projeto de Laboratório 03
│   ├── /data                              # 🗄️ Dados em cache e saídas geradas pelas análises
│   ├── /graficos_dora                     # 📈 Gráficos relacionados às métricas DORA
│   ├── /metricas                          # 📏 Códigos e scripts de extração das métricas
│   └── /tests                             # 🧪 Testes das implementações
│
├── /Laboratorio04_TestesDeHipotese        # 📂 Projeto de Laboratório 04
│   ├── /dashboard                         # 📊 Dashboard web portátil e visualizações G1 & G2
│   │   ├── app.js                         # ⚡ Lógica interativa no navegador
│   │   ├── dados.py                       # 🐍 Pré-processamento e estatísticas descritivas
│   │   ├── graficos.py                    # 📈 Funções dos gráficos G1 e G2
│   │   ├── gerar_dashboard.py             # ⚙️ Motor de consolidação e dados JSON
│   │   ├── index.html                     # 🌐 Interface web
│   │   ├── styles.css                     # 🎨 Estilos no padrão dos Labs 01 e 02
│   │   └── README.md                      # 📘 Guia de execução com comando único
│   ├── data_loader.py                     # 📥 Módulo de dados reais (Maria Clara)
│   ├── simulation.py                      # 🎲 Módulo de simulação (Áulus)
│   └── README.md                          # 📘 Documentação geral do Laboratório 04
│
└── README.md                              # 📘 Documentação dos projetos
```

---
## 👥 Autores

| 👤 Nome | 🖼️ Foto | :octocat: GitHub | 💼 LinkedIn | 📤 Gmail |
|---------|----------|-----------------|-------------|-----------|
| Áulus Batista  | <div align="center"><img src="https://avatars.githubusercontent.com/u/111202256?v=4" width="70px" height="70px"></div> | <div align="center"><a href="https://github.com/AulusHZP"><img src="https://joaopauloaramuni.github.io/image/github6.png" width="50px" height="50px"></a></div> | <div align="center"><a href="https://www.linkedin.com/in/vinicius-simoes-dev/"><img src="https://joaopauloaramuni.github.io/image/linkedin2.png" width="50px" height="50px"></a></div> | <div align="center"><a href="email@gmail.com"><img src="https://joaopauloaramuni.github.io/image/gmail3.png" width="50px" height="50px"></a></div> |
| Maria Clara Gomes Silva de Oliveira  | <div align="center"><img src="https://github.com/mariaoliveira27/mariaoliveira27/blob/main/MinhaFoto.jpg" width="70px" height="70px"></div> | <div align="center"><a href="https://github.com/mariaoliveira27"><img src="https://joaopauloaramuni.github.io/image/github6.png" width="50px" height="50px"></a></div> | <div align="center"><a href="www.linkedin.com/in/mariaclaraoliveira27"><img src="https://joaopauloaramuni.github.io/image/linkedin2.png" width="50px" height="50px"></a></div> | <div align="center"><a href="mariaclariagomes@gmail.com"><img src="https://joaopauloaramuni.github.io/image/gmail3.png" width="50px" height="50px"></a></div> |
| Vinícius Simões  | <div align="center"><img src="https://avatars.githubusercontent.com/u/80927829?v=4" width="70px" height="70px"></div> | <div align="center"><a href="https://github.com/ViniSimoesV"><img src="https://joaopauloaramuni.github.io/image/github6.png" width="50px" height="50px"></a></div> | <div align="center"><a href="https://www.linkedin.com/in/vinicius-simoes-dev/"><img src="https://joaopauloaramuni.github.io/image/linkedin2.png" width="50px" height="50px"></a></div> | <div align="center"><a href="vinisv2004@gmail.com"><img src="https://joaopauloaramuni.github.io/image/gmail3.png" width="50px" height="50px"></a></div> |
