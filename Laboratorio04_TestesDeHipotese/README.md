# Laboratório 04 — Testes de Hipótese: Cenário, Simulação e Visualização

Este repositório contém a implementação do **Laboratório 04** da disciplina *Laboratório de Experimentação de Software* (PUC Minas). O projeto estuda o comportamento comparativo de dois testes estatísticos de hipótese (**t de Welch** $\times$ **Mann-Whitney U**) em cenários de Engenharia de Software, combinando mineração de dados empíricos reais, simulação computacional de Monte Carlo e visualização interativa via Dashboard.

---

## 🔗 Links Oficiais do Projeto

* 📂 **Repositório GitHub:** [https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware)
* 📌 **GitHub Projects:** [https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/projects](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/projects)
* 🌐 **Dashboard:** Disponível localmente em `http://localhost:8000` via comando único de execução.

---

## 👥 Divisão de Atividades da Entrega Final (Com código para todos)

| Integrante | Módulo / Responsabilidade | Atividades de Código e Documentação |
|---|---|---|
| **Maria Clara** | `data_loader.py` / Análise Real | Módulo de dados empíricos reais, cálculo padronizado de **tamanho de efeito** (*Cohen's d* e *Cliff's Delta*), formulação do cenário e conclusões das Seções 1, 6 e 7. |
| **Áulus** | `simulation.py` / Testes | Motor de simulação de Monte Carlo com semente fixa (`numpy.random.default_rng(42)`), simulações das perguntas **Q1** (Erro Tipo I em 10.000 iterações sob $H_0$), **Q2** (Curvas de Poder) e **Q3** (Violações de pressupostos), e suíte de testes automatizados (`tests/test_simulation.py`). |
| **Vinícius** | `dashboard/` / Visualização & Orquestração | Implementação dos scripts dos gráficos **G1, G2, G3 e G4**, estruturação completa do dashboard nas **7 seções oficiais**, scripts de automação em comando único (`run_dashboard.ps1/.bat`), tabela de dados reais e roteiro da apresentação oral. |

---

## 🚀 Como Executar em Comando Único

Conforme exigido pelo edital (semente fixa e reprodutibilidade com comando único):

### No Windows (PowerShell):
```powershell
.\run_lab04.ps1
```
*(Ou acesse a pasta `dashboard` e execute `.\run_dashboard.ps1`)*

### No Windows (Prompt de Comando):
```cmd
.\run_lab04.bat
```

### Execução via Python:
```powershell
python dashboard/dashboard.py
```

O comando executará automaticamente as simulações determinísticas de Monte Carlo (caso `data/dados.json` não tenha sido gerado), abrirá seu navegador padrão em <http://localhost:8000> e manterá o servidor HTTP local ativo.

---

## 🧪 Como Rodar os Testes Automatizados

O motor de simulação possui cobertura de testes unitários para garantir a reprodução determinística dos resultados:

```powershell
python tests/test_simulation.py
```
*(Executa a suíte completa de 9 testes validando geradores, estabilidade de semente, erro tipo I e monotonicidade de poder).*

---

## 📊 Estrutura das 7 Seções do Dashboard

1. **Cenário:** Pergunta de pesquisa, hipóteses $H_0$ e $H_1$, e caracterização da amostra minerada ($N=300$).
2. **Os dados (Gráfico G1):** Histogramas comparativos (Real vs. Simulado) e tabela de estatísticas descritivas.
3. **Como os testes funcionam (Gráfico G2):** Distribuição da estatística sob $H_0$, região crítica de rejeição ($\alpha = 0{,}05$) e marcação do $p$-valor.
4. **Erro tipo I (Gráfico G3):** Taxa de falso positivo em 10.000 simulações sob $H_0$ em 5 cenários frente à linha nominal de 5%.
5. **Poder (Gráfico G4):** Curvas de poder de Welch vs. Mann-Whitney frente a efeitos crescentes ($\delta$) com linha de corte em 80%.
6. **Dados reais (Tabela):** Tabela completa com estatísticas observadas, $p$-valores, tamanhos de efeito (**Cohen's d** e **Cliff's δ**) e veredito prático.
7. **Conclusão:** Síntese metodológica confrontando expectativa prévia $\times$ descobertas da simulação e recomendação final de teste para métricas de software.
