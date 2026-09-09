# 🧪 Casos de Teste e Automação de Avaliação

Este diretório contém a suíte de testes automatizados e os scripts de avaliação para validar as soluções dos 6 katas desenvolvidos durante o experimento.

---

## 📂 Arquivos do Diretório

* **`casos_de_teste_katas.json`**: Base de dados em formato JSON contendo exatamente 10 casos de teste fechados (entradas, saídas esperadas e tipo de comparação) para cada um dos 6 katas (`kata01` a `kata06`).
* **`executor.py`**: Script encarregado de executar um único arquivo de solução `.py` em um subprocesso isolado, enviando as entradas via terminal e comparando as saídas obtidas com o gabarito.
* **`executar_bateria.py`**: Script de automação em lote que varre a pasta `solucoes_das_Katas/`, identifica todas as soluções presentes, executa os testes para cada uma e consolida as estatísticas em um arquivo CSV (`resultado_bateria_katas.csv`).

---

## 🚀 Como Executar

### 1. Avaliação Individual de uma Solução (`executor.py`)
Ideal para testar uma única solução isoladamente durante o desenvolvimento.

```bash
python executor.py <caminho_da_solucao.py> <chave_kata>
```

**Exemplo:**
```bash
python executor.py ../solucoes_das_Katas/kata01_vini_manual.py kata01
```

---

### 2. Avaliação em Bateria Completa (`executar_bateria.py`)
Varre automaticamente todos os arquivos da pasta `solucoes_das_Katas/` e gera o relatório consolidado em CSV.

```bash
python executar_bateria.py
```

* **Saída Gerada:** `resultado_bateria_katas.csv` com as colunas `Kata`, `Integrante`, `Tratamento`, `Arquivo_Solucao`, `Total_Casos`, `Aprovados`, `Reprovados`, `Taxa_Sucesso_Pct` e `Passou_Todos`.