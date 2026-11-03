# Laboratório 04 — Testes de Hipótese & Simulação Estatística

Este módulo implementa o estudo experimental do **Laboratório 04**, combinando análise de dados reais de engenharia de software com simulação estatística (Monte Carlo) e testes de hipótese para comparação entre distribuições e grupos experimentais.

---

## 👥 Divisão de Atividades da Sprint 01 (Lab04S01)

| Integrante | Módulo / Artefato | Atividades Principais | Issues Associadas |
|---|---|---|---|
| **Maria Clara** | `data_loader.py` | Carregamento da amostra real (CSV), pré-processamento, estatísticas descritivas iniciais e escrita formal da pergunta de pesquisa, $H_0$ e $H_1$. | #86, #87, #91 |
| **Áulus** | `simulation.py` | Motor de simulação (`numpy.random.default_rng(42)`), geração de conjuntos sintéticos, aplicação dos testes estatísticos (`ttest_ind`, `mannwhitneyu`) e proporções de rejeição. | #88, #89, #90, #92 |
| **Vinícius** | `dashboard/` | Configuração da dashboard web portátil, gráficos **G1** (histogramas comparativos) e **G2** (distribuição sob $H_0$ com região crítica sombreada). | **#93**, **#94** |

---

## 🎯 Pergunta de Pesquisa & Hipóteses Experimentais

* **Pergunta de Pesquisa (RQ):** *Existe diferença estatisticamente significativa no comportamento das métricas de engenharia de software (como Lead Time, MTTR e Frequência de Deploy) entre diferentes grupos ou em comparação com modelos sintéticos calibrados?*
* **Hipótese Nula ($H_0$):** $\mu_1 = \mu_2$ (ou $F_1 = F_2$) — Não há diferença no comportamento da métrica entre os grupos comparados.
* **Hipótese Alternativa ($H_1$):** $\mu_1 \neq \mu_2$ (ou $F_1 \neq F_2$) — Há diferença estatisticamente significativa entre os grupos.

---

## 📂 Estrutura de Pastas

```
Laboratorio04_TestesDeHipotese/
├── dashboard/                  # 📊 Dashboard web portátil e visualizações G1 & G2
│   ├── data/
│   │   └── dados.json          # 📄 Base analítica consolidada
│   ├── app.js                  # ⚡ Lógica interativa no navegador
│   ├── dados.py                # 🐍 Pré-processamento e estatísticas descritivas
│   ├── graficos.py             # 📈 Funções dos gráficos G1 e G2
│   ├── gerar_dashboard.py      # ⚙️ Motor de geração dos dados analíticos
│   ├── dashboard.py            # 🚀 Entrypoint conveniente para geração e servidor
│   ├── index.html              # 🌐 Interface web
│   ├── styles.css              # 🎨 Estilos no padrão dos Labs 01 e 02
│   ├── requirements.txt        # 📦 Dependências do módulo
│   ├── run_dashboard.bat       # 🪟 Script de execução rápida
│   ├── run_dashboard.ps1       # 💻 Script PowerShell de execução rápida
│   └── README.md               # 📘 Documentação detalhada da dashboard
│
├── data_loader.py              # 📥 Módulo de carregamento e cenário (Maria Clara)
├── simulation.py               # 🎲 Módulo de simulação e testes (Áulus)
└── README.md                   # 📘 Documentação geral do Laboratório 04
```

---

## 🚀 Como Executar o Dashboard

Para rodar a dashboard web portátil com comando único:

```powershell
cd dashboard
.\run_dashboard.bat
```
Ou no PowerShell:
```powershell
cd dashboard
.\run_dashboard.ps1
```

O dashboard abrirá em seu navegador no endereço <http://localhost:8000>. Para mais detalhes, consulte o [README da dashboard](dashboard/README.md).
