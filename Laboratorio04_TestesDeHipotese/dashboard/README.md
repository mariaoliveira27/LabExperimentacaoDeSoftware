# Dashboard dos Resultados — Laboratório 04 (Entrega Final)

Dashboard analítica interativa que reúne os resultados do **Laboratório 04: Testes de Hipótese por Dentro — Cenário, Simulação e Visualização**.

O projeto atende rigorosamente a todas as exigências do edital:
1. **7 Seções ordenadas e completas**, cada uma acompanhada de texto explicativo curto (2 a 4 frases).
2. **Visualizações gráficas obrigatórias G1, G2, G3 e G4** implementadas via Plotly.js com cores consistentes por teste (`#1677c8` para Welch e `#ec9b24` para Mann-Whitney).
3. **Tabela de dados reais** com cálculo de estatísticas observadas ($t$ e $U$), $p$-valores e tamanhos de efeito padronizados (**Cohen's $d$** e **Cliff's $\delta$**).
4. **Links oficiais no topo** para o repositório GitHub e GitHub Projects.
5. **Comando único de execução** e **reprodutibilidade estrita com semente fixa** (`numpy.random.default_rng(42)`).

---

## 🚀 Como Executar em Comando Único

### Opção 1: Via Script Automático (Recomendado)

#### No Windows (PowerShell):
```powershell
.\run_dashboard.ps1
```

#### No Windows (Prompt de Comando ou Duplo Clique):
```cmd
.\run_dashboard.bat
```

> O script verifica o ambiente, executa a consolidação analítica e as simulações Monte Carlo (caso `data/dados.json` não exista), abre o navegador automaticamente em <http://localhost:8000> e inicia o servidor HTTP local.

---

### Opção 2: Via Python diretamente

```powershell
python dashboard.py
```
*(Executa a consolidação completa e sobe o servidor HTTP local na porta 8000).*

---

## 🧭 Estrutura das 7 Seções do Dashboard

A interface web está estruturada estritamente na ordem exigida:

| # | Seção | Artefato / Gráfico | Conteúdo do Texto Acompanhante |
|---|---|---|---|
| **01** | **Cenário** | Formulário de Hipóteses & KPIs | A pergunta formal, hipóteses $H_0$ e $H_1$, proveniência dos dados reais (GitHub API, Lab 03) e tamanho amostral ($N=300$). |
| **02** | **Os dados** | **Gráfico G1** (Histogramas) | Forma dos dados reais (assimetria, outliers) vs. modelo sintético ajustado por MLE (Lognormal) e tabela descritiva (Média, Mediana, DP, Skewness). |
| **03** | **Como os testes funcionam** | **Gráfico G2** (Distribuição sob $H_0$) | O que cada teste compara (médias vs. postos), localização da região crítica sombreada (|stat| $\ge$ valor crítico) e o significado estrito do $p$-valor. |
| **04** | **Erro tipo I** | **Gráfico G3** (Barras de Erro Tipo I) | Avaliação empírica sob $H_0$ em 10.000 simulações comparadas à linha nominal de 5% em cinco cenários (padrão, normal e violações). |
| **05** | **Poder** | **Gráfico G4** (Curvas de Poder) | Curvas sobrepostas de detecção frente a efeitos crescentes ($\delta$), demonstrando a superioridade do Mann-Whitney em dados assimétricos e linha de corte de 80%. |
| **06** | **Dados reais** | **Tabela Analítica** | Resultados dos dois testes nas métricas reais de repositórios, com estatísticas observadas, $p$-valores, tamanhos de efeito (**Cohen's $d$** e **Cliff's $\delta$**) e conclusões práticas. |
| **07** | **Conclusão** | Síntese Metodológica | Confronto entre expectativa pré-simulação vs. achados empíricos, recomendação do teste para o cenário de software e condições em que a escolha mudaria. |

---

## 📁 Estrutura de Arquivos

```
Laboratorio04_TestesDeHipotese/dashboard/
├── data/
│   └── dados.json          # 📄 Base analítica e simulações consolidadas
├── app.js                  # ⚡ Lógica interativa no cliente, renderização Plotly e filtros
├── dados.py                # 🐍 Módulo analítico: estatísticas descritivas, Q1, Q2, Q3 e tamanhos de efeito
├── graficos.py             # 📈 Mapeamento de dados estruturados para os gráficos G1, G2, G3 e G4
├── gerar_dashboard.py      # ⚙️ Motor de consolidação que produz data/dados.json
├── dashboard.py            # 🚀 Entrypoint conveniente em comando único
├── index.html              # 🌐 Interface web com as 7 seções oficiais
├── styles.css              # 🎨 Folha de estilos moderna e responsiva
├── run_dashboard.bat       # 🪟 Script de inicialização em lote Windows
├── run_dashboard.ps1       # 💻 Script PowerShell de inicialização
└── README.md               # 📘 Este documento de guia
```
