# 🧪 Casos de Teste e Automação de Avaliação

Este diretório contém a suíte de testes automatizados e os scripts de avaliação para validar as soluções dos 6 katas desenvolvidos durante o experimento.

---

## 📂 Arquivos do Diretório

* **`casos_de_teste_katas.json`**: Base única em UTF-8 com 61 casos: 10 para cada um de `kata01` a `kata04`, 11 para `kata05` e 10 para `kata06`.
* **`executor.py`**: Script encarregado de executar um único arquivo de solução `.py` em um subprocesso isolado, enviando as entradas via terminal e comparando as saídas obtidas com o gabarito.
* **`executar_bateria.py`**: Script de automação em lote que varre a pasta `solucoes_das_Katas/`, identifica todas as soluções presentes, executa os testes para cada uma e consolida as estatísticas em um arquivo CSV (`resultado_bateria_katas.csv`).
* **[`aceitacao_k05_k06/`](aceitacao_k05_k06/README.md)**: Documentação dos contratos e verificadores dos 21 casos K05/K06 e da comparação numérica. As entradas e referências ficam somente na base central.

## Formato da base

O JSON é um objeto com as chaves `kata01` a `kata06`, cada uma contendo uma lista
de casos. Cada caso possui `entrada` (stdin completo), `saida_esperada` (string),
`finalidade` e `tipo_comparacao` (`texto` ou `float`). K05/K06 também possuem
`id` estável; K06 define `tolerancia_absoluta: 1e-9` em cada caso.

O executor normaliza espaços externos e fins de linha, unindo linhas com um
espaço. Para números, exige valores finitos. Quando há `tolerancia_absoluta`,
usa esse limite e desativa a tolerância relativa. Sem esse campo, mantém os
limites anteriores: absoluto `1e-4` e relativo `1e-9`.

K05 cobre vetor vazio, vetor não ordenado, primeira ocorrência e limite de 200
elementos. K06 cobre os primeiros `n` termos da série, contando `1` como o
primeiro termo, com `n` entre 1 e 20. Os [contratos detalhados](aceitacao_k05_k06/README.md)
registram as convenções de adaptação a Python e as referências independentes.

---

## 🚀 Como Executar

### 1. Avaliação Individual de uma Solução (`executor.py`)
Ideal para testar uma única solução isoladamente durante o desenvolvimento.

Execute da raiz do repositório:

```powershell
python Laboratorio02_TrialsIA/casos_de_teste/executor.py <caminho_da_solucao.py> <chave_kata>
```

**Exemplo:**
```powershell
python Laboratorio02_TrialsIA/casos_de_teste/executor.py Laboratorio02_TrialsIA/solucoes_das_Katas/kata05_nome_manual.py kata05
```

O caminho do exemplo deve ser substituído por uma solução existente. A mesma
base pode ser consumida pela API, executando Python da raiz:

```python
from Laboratorio02_TrialsIA.casos_de_teste.executor import avaliar_solucao

relatorio = avaliar_solucao(
    "Laboratorio02_TrialsIA/solucoes_das_Katas/kata05_nome_manual.py",
    "kata05",
)
```

A função devolve total, aprovados, reprovados, taxa de sucesso, `passou_todos` e
detalhes. O executor usa timeout de cinco segundos por caso. O `id` identifica
o caso na base; o relatório atual usa sua posição (`caso_teste`) e ainda não
registra `trial_id`. A associação com tempo e métricas RQ3 deve ser mantida
externamente até essa integração ser implementada.

---

### 2. Avaliação em Bateria Completa (`executar_bateria.py`)
Varre automaticamente todos os arquivos da pasta `solucoes_das_Katas/` e gera o relatório consolidado em CSV.

```powershell
python Laboratorio02_TrialsIA/casos_de_teste/executar_bateria.py
```

* **Saída Gerada:** `resultado_bateria_katas.csv`, no diretório de execução, com as colunas `Kata`, `Integrante`, `Tratamento`, `Arquivo_Solucao`, `Total_Casos`, `Aprovados`, `Reprovados`, `Taxa_Sucesso_Pct` e `Passou_Todos`.

### 3. Verificar os casos e o comparador

Este comando usa apenas a biblioteca padrão; confere os dados e o comparador
sem executar soluções ou registrar rodadas experimentais:

```powershell
python -m unittest discover -s Laboratorio02_TrialsIA/casos_de_teste/aceitacao_k05_k06 -p "test_*.py" -v
```

Ambiente validado: Python 3.12.10. Recursão requer revisão do código das soluções;
testes de entrada e saída, isoladamente, não demonstram esse requisito.
