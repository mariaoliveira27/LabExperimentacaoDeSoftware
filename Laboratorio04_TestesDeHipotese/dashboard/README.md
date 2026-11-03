# Dashboard dos Resultados — Laboratório 04 (Lab04S01)

Dashboard estática interativa para explorar os dados reais de engenharia de software e modelos simulados por Monte Carlo, com cálculo de testes estatísticos de hipótese e visualizações gráficas obrigatórias **G1** e **G2**.

Seguindo o padrão arquitetural dos Laboratórios 01 e 02, o processamento analítico e ajuste paramétrico são realizados previamente em Python (`dados.py`, `graficos.py`, `gerar_dashboard.py`), gerando a base consolidada em `data/dados.json`. O navegador consome os recortes prontos de forma instantânea e responsiva, servido via servidor HTTP local sem necessidade de frameworks pesados de interface.

---

## 🚀 Como Executar Localmente

### Opção 1: Comando Único (Recomendado)

#### No Windows (Prompt / Duplo Clique):
```cmd
.\run_dashboard.bat
```

#### No Windows (PowerShell):
```powershell
.\run_dashboard.ps1
```

O script verifica os dados, abre o navegador automaticamente e inicia o servidor HTTP local na porta `8000`.

---

### Opção 2: Manualmente via Terminal

1. **Instale as dependências (se ainda não instaladas):**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Gere os dados analíticos consolidados:**
   ```powershell
   python gerar_dashboard.py
   ```

3. **Inicie o servidor HTTP local na pasta do dashboard:**
   ```powershell
   python -m http.server 8000
   ```

4. **Acesse no navegador:**
   Abra <http://localhost:8000>

> **Nota:** Utilize o servidor local (`http.server`). Abrir o arquivo `index.html` diretamente via `file://` pode fazer com que navegadores modernos bloqueiem requisições `fetch` ao arquivo JSON por políticas de CORS locais.

---

## 📈 Visualizações e Recursos

### 📊 Gráfico G1: Histogramas Comparativos (Real vs. Simulado)
- Comparação direta da distribuição empírica coletada de repositórios open-source com a distribuição sintética simulada (ajustada via MLE).
- Alternância dinâmica entre visualização **Lado a Lado** e **Sobreposta**.
- Linhas verticais indicando a **média** e a **mediana** de ambos os conjuntos.
- Tabela de estatísticas descritivas comparativas (Média, Mediana, Desvio Padrão e Assimetria/Skewness).

### 🎯 Gráfico G2: Distribuição sob $H_0$ & Região Crítica
- Exibição da densidade teórica da estatística de teste sob a hipótese nula ($H_0$):
  - $t$ de Student com graus de liberdade ajustados por Welch para o teste $t$.
  - Normal padrão $N(0, 1)$ para o teste não-paramétrico de Mann-Whitney U ($Z$-score assintótico).
- **Região de Rejeição Sombreada:** áreas críticas sombreadas em vermelho correspondentes ao nível de significância $\alpha$ ($0.01$, $0.05$ ou $0.10$).
- **Estatística Observada:** linha vertical proeminente destacando o valor calculado ($t_{obs}$ ou $Z_{obs}$) e o respectivo $p$-valor.
- **Veredito Estatístico Automático:** cartão de decisão formal informando se rejeita $H_0$ ou não rejeita $H_0$.

### 🔍 Explorador de Dados
- Tabela interativa para busca de repositórios por nome e linguagem.
- Filtro por métrica (Lead Time de Commit, Lead Time de Release, MTTR, Frequência de Deploy e Stars).

---

## 📁 Estrutura de Arquivos do Módulo

```
Laboratorio04_TestesDeHipotese/dashboard/
├── data/
│   └── dados.json          # 📄 Dataset analítico estruturado e pré-calculado
├── app.js                  # ⚡ Lógica interativa no cliente e renderização Plotly
├── dados.py                # 🐍 Carregamento e cálculo das estatísticas descritivas
├── graficos.py             # 📈 Funções dos gráficos G1 e G2 e testes estatísticos
├── gerar_dashboard.py      # ⚙️ Motor de consolidação e exportação dos dados JSON
├── dashboard.py            # 🚀 Entrypoint conveniente para geração e servidor
├── index.html              # 🌐 Estrutura semântica da dashboard web
├── styles.css              # 🎨 Folha de estilos no padrão dos Labs 01 e 02
├── requirements.txt        # 📦 Dependências Python do módulo
├── run_dashboard.bat       # 🪟 Script de execução rápida para Windows
├── run_dashboard.ps1       # 💻 Script PowerShell de execução rápida
└── README.md               # 📘 Este documento de guia
```
