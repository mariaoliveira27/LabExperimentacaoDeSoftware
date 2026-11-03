# Laboratório 04 — Simulação Estatística & Testes de Hipótese (Lab04S01)

Este módulo implementa o estudo experimental por simulação estatística (Monte Carlo e testes de hipótese) comparando distribuições empíricas de métricas reais de engenharia de software com distribuições teóricas simuladas, com foco nas entregas da **Sprint 01 (Lab04S01)**.

---

## 👥 Divisão de Atividades da Sprint (Lab04S01)

| Integrante | Módulo / Arquivo | Atividades Principais | Issues Associadas |
|---|---|---|---|
| **Maria Clara** | `data_loader.py` | Carregamento da amostra real (CSV/planilha), pré-processamento, estatísticas descritivas iniciais e escrita formal da pergunta de pesquisa, $H_0$ e $H_1$. | #86, #87, #91 |
| **Áulus** | `simulation.py` | Motor de simulação (`numpy.random.default_rng(42)`), geração de conjuntos sintéticos, aplicação dos testes estatísticos (`ttest_ind`, `mannwhitneyu`) e proporções de rejeição. | #88, #89, #90, #92 |
| **Vinícius** | `dashboard.py` | Configuração inicial do dashboard Streamlit, execução em comando único, implementação do **Gráfico G1** (histogramas comparativos) e **Gráfico G2** (distribuição sob $H_0$ com região de rejeição sombreada). | **#93**, **#94** |

---

## 🎯 Pergunta de Pesquisa & Hipóteses Experimentais

* **Pergunta de Pesquisa (RQ):** *Existe diferença estatisticamente significativa no comportamento das métricas de engenharia de software (como Lead Time, MTTR e Frequência de Deploy) entre diferentes grupos ou em comparação com modelos sintéticos calibrados?*
* **Hipótese Nula ($H_0$):** $\mu_1 = \mu_2$ (ou $F_1 = F_2$) — Não há diferença no comportamento da métrica entre os grupos comparados.
* **Hipótese Alternativa ($H_1$):** $\mu_1 \neq \mu_2$ (ou $F_1 \neq F_2$) — Há diferença estatisticamente significativa entre os grupos.

---

## 📈 Visualizações Implementadas

### 📊 Gráfico G1: Histogramas Comparativos (Real vs. Simulado)
- Implementado em Plotly interativo com modos **Lado a Lado** e **Sobreposto**.
- Exibe densidade de probabilidade para permitir comparação de escalas arbitrárias.
- Linhas verticais indicando a **média** e a **mediana** tanto da série real quanto da simulada.
- Tabela de métricas descritivas comparativas (Média, Mediana, Desvio Padrão e Assimetria/Skewness).

### 🎯 Gráfico G2: Distribuição da Estatística sob $H_0$ & Região de Rejeição
- Distribuição teórica da estatística do teste sob a hipótese nula:
  - $t$ de Student com $gl$ graus de liberdade ajustados por Welch para o teste $t$.
  - Normal padrão $N(0, 1)$ para o teste não-paramétrico de Mann-Whitney U (aproximação assintótica padronizada $Z$).
- **Região Crítica de Rejeição Sombreada:** áreas bicaudais vermelhas correspondentes ao nível de significância $\alpha$ (padrão $0.05$).
- **Estatística Observada:** linha vertical de destaque com o valor exato calculado ($t_{obs}$ ou $Z_{obs}$) e o $p$-valor.
- **Veredito Estatístico Automático:** destaque visual se a hipótese nula $H_0$ é rejeitada ($p < \alpha$) ou se não há evidências para sua rejeição ($p \ge \alpha$).

---

## 🚀 Como Executar com Comando Único

### 1. Pré-requisitos
Certifique-se de que o Python 3.10+ está instalado e configure as dependências com `uv` ou `pip`:

```bash
cd Laboratorio04_Simulacao
pip install -r requirements.txt
```

### 2. Execução Direta (Comando Único)

#### No Windows:
Basta clicar duas vezes ou rodar no terminal:
```cmd
.\run_dashboard.bat
```
Ou no PowerShell:
```powershell
.\run_dashboard.ps1
```

#### Via Streamlit CLI diretamente (Dashboard Interativo):
```bash
streamlit run dashboard.py
```
O dashboard abrirá automaticamente no navegador no endereço `http://localhost:8501`.

#### Execução como Script dos Gráficos G1 e G2 (Headless / CLI):
Para rodar diretamente o gerador dos gráficos G1 e G2 e exportar as figuras interativas para a pasta `graficos_gerados/`:
```bash
python dashboard.py
```
Esse comando gera os arquivos `grafico_g1_comparativo.html` e `grafico_g2_distribuicao_h0.html` e exibe o relatório estatístico com teste de hipótese e p-valores diretamente no terminal.

---

## 🧩 Arquitetura & Integração Modular

O `dashboard.py` foi projetado com acoplamento fraco e alta coesão:
- Ele tenta consumir diretamente as funções de `data_loader.py` e `simulation.py` assim que os módulos dos colegas forem commitados.
- Enquanto os módulos estão sendo finalizados em paralelo, o dashboard executa **fallbacks determinísticos embutidos** sobre a base de dados real do Lab 03 (`repositorios_aprovados.csv`), assegurando execução funcional imediata e sem bloqueios.
