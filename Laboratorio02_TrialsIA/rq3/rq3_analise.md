
### 📌 Resposta Direta à Pergunta da RQ3

> **O uso de assistente de IA altera a complexidade ciclomática ou a duplicação do código produzido?**
> 
> **Não.** Os dados empíricos demonstram que **o uso de assistente de IA não alterou de forma estatisticamente significativa nem a complexidade ciclomática nem a taxa de duplicação do código**. O fator determinante para a complexidade foi a **natureza do algoritmo/enunciado do Kata**, e não o método de geração (humano vs. IA).

---

### 📊 1. Análise da Complexidade Ciclomática (McCabe via Radon `cc`)

| Métrica | Tratamento Manual ($N=9$) | Tratamento IA ($N=11$) | Diferença (IA - Manual) | Teste Mann-Whitney $U$ ($p$-valor) |
| :--- | :---: | :---: | :---: | :---: |
| **CC Média (`avg_cc`) — Média** | 4.36 | 4.42 | +0.06 | $U = 46.5$, $p = 0.8197$ |
| **CC Média (`avg_cc`) — Mediana (IQR)** | **3.67** (3.17) | **4.00** (2.46) | +0.33 | *(Não significativo)* |
| **CC Máxima (`max_cc`) — Média** | 6.56 | 6.00 | -0.56 | $U = 49.5$, $p = 1.0000$ |
| **CC Máxima (`max_cc`) — Mediana (IQR)** | **4.00** (7.00) | **4.00** (5.50) | **0.00** | *(Idênticas)* |

#### Principais Observações:
1. **Mediana e Média Praticamente Idênticas:** A mediana da complexidade máxima (`max_cc`) foi rigorosamente igual a **4.00** em ambos os tratamentos. A complexidade ciclomática média oscilou apenas de **3.67** (Manual) para **4.00** (IA), variação sem significância estatística ($p = 0.82$).
2. **Dominância da Natureza do Kata:** A complexidade foi determinada pela regra de negócio do problema:
   - Katas complexos como o **Kata 01** (validação de tipos) e o **Kata 02** (expressões booleanas) geraram alta complexidade tanto no código manual quanto na IA (`avg_cc` entre **5.1** e **8.3**, com picos de `max_cc` de **10 a 13**).
   - Katas recursivos e lineares como o **Kata 03**, **Kata 05** e **Kata 06** mantiveram complexidade baixa e similar em ambos os grupos (`avg_cc` entre **2.3** e **3.7**).

---

### 📑 2. Comparação Pareada por Kata (Manual vs. IA)

| Kata | Tratamento | Amostras ($N$) | CC Média (`avg_cc`) | CC Máxima (`max_cc`) | LOC Médio | MI Médio (Radon) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Kata 01** | Manual | 2 | 5.62 | 10.00 | 69.5 | 38.4 |
|  | **IA** | 2 | **5.13** | **8.50** | 74.0 | 52.8 |
| **Kata 02** | Manual | 2 | 7.33 | 11.50 | 71.0 | 57.4 |
|  | **IA** | 2 | **8.34** | **12.50** | 77.0 | 38.8 |
| **Kata 03** | Manual | 1 | 2.50 | 3.00 | 23.0 | 60.9 |
|  | **IA** | 2 | **3.25** | **3.50** | 24.0 | 72.2 |
| **Kata 04** | Manual | 1 | 3.67 | 4.00 | 44.0 | 76.7 |
|  | **IA** | 1 | **2.40** | **3.00** | 40.0 | 49.3 |
| **Kata 05** | Manual | 1 | 2.50 | 3.00 | 25.0 | 61.4 |
|  | **IA** | 2 | **3.75** | **4.00** | 24.0 | 81.4 |
| **Kata 06** | Manual | 2 | 2.33 | 3.00 | 30.5 | 66.9 |
|  | **IA** | 2 | **2.67** | **3.00** | 30.5 | 54.2 |

---

### 🧬 3. Análise da Duplicação de Código

Calculando a duplicação tanto isolada por grupo de tratamento quanto no conjunto geral de arquivos:

| Escopo da Duplicação | % de Linhas Duplicadas | Interpretação |
| :--- | :---: | :--- |
| **Apenas Soluções Manuais** | **29.82%** | Padrões de I/O (`sys.stdin`), loops de leitura e prints. |
| **Apenas Soluções IA (Gemini)** | **30.75%** | Estruturas de prompt repetidas, tratamentos de casos base e recursão. |
| **Diferença Direta (IA - Manual)** | **+0.93%** | **Inexpressiva** (menos de 1 ponto percentual). |
| **Conjunto Geral Consolidado** | **33.24%** | Reflete similaridade de assinaturas e casos de teste entre soluções do mesmo kata. |

- A IA **não gerou duplicação desenfreada de métodos**. A taxa de duplicação foi essencialmente idêntica à do código manual (+0.93%), decorrente dos requisitos idênticos de entrada/saída padronizados exigidos pelos katas.

---

### 📏 4. Métricas de Controle e Qualidade Global

#### Linhas de Código (LOC — Normalização)
- **Manual:** Média = 48.22 | Mediana = **44.00** (IQR = 35.00)
- **IA:** Média = 45.36 | Mediana = **35.00** (IQR = 39.00)
- **Diferença:** A IA gerou códigos com mediana ligeiramente menor (**-9 linhas**), porém sem diferença estatística significativa ($p = 0.7324$). Isso reflete soluções que utilizaram expressões recursivas mais compactas em katas menores (K03, K05).

#### Índice de Manutenibilidade (*Maintainability Index* — Radon `mi`)
- **Manual:** Média = **58.27** | Mediana = **60.90**
- **IA:** Média = **58.90** | Mediana = **54.65**
- **Diferença:** Média quase idêntica (+0.63 ponto no MI) e $p = 0.9697$, mantendo ambos os grupos na mesma faixa de manutenibilidade aceitável (classificação Radon B/A).

---

### 💡 Conclusão Sintética para o Relatório
Os dados de [`rq3_static_metrics.csv`](file:///c:/Users/maria/Downloads/LabExperimentacaoDeSoftware/rq3_static_metrics.csv) comprovam que **assistentes de IA não degradam nem melhoram de maneira isolada a qualidade estrutural interna (complexidade ciclomática e duplicação)** quando comparados com programadores humanos desenvolvendo sob as mesmas especificações. O desenho algorítmico imposto pelo problema é a variável de maior peso na complexidade final do software.