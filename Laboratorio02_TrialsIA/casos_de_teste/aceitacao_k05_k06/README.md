# Casos de aceitação K05 e K06

Esta pasta documenta e verifica os 11 casos de K05 e os 10 casos de K06 integrados
ao [executor de testes](../README.md). As entradas e referências ficam na base
única [casos_de_teste_katas.json](../casos_de_teste_katas.json), nas chaves
`kata05` e `kata06`. Os verificadores não contêm soluções oficiais nem executam
rodadas. A adaptação para Python, o formato de entrada e saída, os limites,
a primeira ocorrência em K05 e a tolerância de K06 são convenções propostas
pelo grupo, ainda sujeitas à validação com o professor. A recursão consta dos
enunciados. Participar da preparação dos casos pode influenciar o desempenho
posterior no experimento.

## Formato e consumo

A base central, em UTF-8, contém um objeto com as chaves `kata01` a `kata06`.
Cada chave contém uma lista de casos. Em K05/K06, os campos são:

| Campo | Significado |
| --- | --- |
| `id` | Identificador estável do caso, por exemplo `K05-01`. |
| `finalidade` | Objetivo e comportamento coberto. |
| `entrada` | Texto completo a enviar ao stdin, incluindo quebras de linha. |
| `saida_esperada` | String, inclusive para a referência numérica de K06. |
| `tipo_comparacao` | `texto` em K05; `float` em K06. |
| `tolerancia_absoluta` | Limite de erro absoluto; presente nos casos numéricos. |

Os dados podem ser carregados usando somente a biblioteca padrão, da raiz do
repositório:

```python
import json
from pathlib import Path

arquivo = Path("Laboratorio02_TrialsIA/casos_de_teste/casos_de_teste_katas.json")
casos_por_kata = json.loads(arquivo.read_text(encoding="utf-8"))
primeiro_caso = casos_por_kata["kata05"][0]
assert primeiro_caso["entrada"] == "0\n\n7\n"
```

Comparação aplicada pelo executor:

- Para `texto`, remover espaços externos e no final de cada linha, unir as
  linhas com um espaço e comparar com a referência normalizada da mesma forma.
  Isso aceita a quebra de linha final; mensagens extras ou prompts reprovam o caso.
- Para `float`, interpretar o stdout normalizado como um único
  número real com ponto decimal, exigir valor finito e verificar
  `abs(obtido - float(saida_esperada)) <= tolerancia_absoluta`, sem tolerância relativa.
  `NaN`, infinitos, vírgula decimal e mensagens extras devem ser rejeitados.

Nos casos sem `tolerancia_absoluta`, o executor mantém a comparação anterior
com tolerância absoluta `1e-4` e relativa `1e-9`. Todos os casos K06 desta base
definem explicitamente `1e-9` e, portanto, usam somente tolerância absoluta.

Para avaliar uma solução existente, use a API da raiz do repositório:

```python
from Laboratorio02_TrialsIA.casos_de_teste.executor import avaliar_solucao

relatorio = avaliar_solucao(
    "Laboratorio02_TrialsIA/solucoes_das_Katas/kata06_nome_manual.py",
    "kata06",
)
```

O `id` identifica um caso; o `trial_id` identifica uma rodada. O executor atual
registra a posição do caso em `caso_teste` e ainda não armazena `trial_id`.
A associação com os registros de tempo e do coletor de métricas deve ser
mantida externamente até essa integração ser implementada. A base JSON não
armazena aprovações, tempos ou resultados de participantes. Timeout de cinco
segundos por caso, processos separados e taxa de sucesso pertencem ao executor.

## K05 — Busca recursiva em vetor

Chave: `kata05` em [casos_de_teste_katas.json](../casos_de_teste_katas.json).

- Primeira linha: quantidade `n`, entre 0 e 200.
- Segunda linha: exatamente `n` inteiros separados por espaços, vazia se `n=0`.
- Terceira linha: inteiro procurado.
- Saída: primeira posição encontrada, começando em zero, ou `-1`.
- A solução deverá usar recursão. Não se pressupõe que o vetor esteja ordenado.

Os resultados foram definidos pela posição dos valores nos vetores e conferidos
independentemente com `list.index`, que devolve a primeira ocorrência, ou `-1`
quando o valor está ausente. Essa conferência verifica os dados de aceitação,
sem fornecer uma solução recursiva do exercício.

| Caso | Objetivo | Saída |
| --- | --- | --- |
| `K05-01` | Vetor vazio e segunda linha vazia | `-1` |
| `K05-02` | Um elemento presente | `0` |
| `K05-03` | Um elemento ausente | `-1` |
| `K05-04` | Valor no início | `0` |
| `K05-05` | Valor no meio, vetor não ordenado | `2` |
| `K05-06` | Valor no fim | `4` |
| `K05-07` | Ausência em vetor com vários elementos | `-1` |
| `K05-08` | Valor negativo em vetor com zero | `3` |
| `K05-09` | Repetições: primeira ocorrência | `1` |
| `K05-10` | 200 elementos, de -100 a 99, procurando 99 | `199` |
| `K05-11` | Zero como valor procurado | `2` |

## K06 — Cosseno de 1 radiano

Chave: `kata06` em [casos_de_teste_katas.json](../casos_de_teste_katas.json).

- Entrada: inteiro `n` entre 1 e 20.
- Calcular os primeiros `n` termos de `1 - 1/2! + 1/4! - 1/6! + ...`.
- O termo inicial `1` conta como o primeiro termo.
- Saída: número real usando ponto decimal.
- A soma deverá ser calculada recursivamente.
- Tolerância absoluta: `1e-9` em todos os casos.

A referência de cada caso é a soma parcial correspondente:

```text
S(n) = soma, para k de 0 até n-1, de (-1)^k / (2k)!
```

As referências foram calculadas independentemente com frações exatas
(`fractions.Fraction`) e fatoriais da biblioteca padrão (`math.factorial`). A
fração resultante foi convertida para `Decimal` com precisão de 80 algarismos e,
por fim, para `float`, cuja representação decimal é armazenada como string no
JSON para compatibilidade com o executor. Os testes desta pasta refazem essa
referência de forma iterativa e conferem que o arredondamento do JSON difere
menos de `1e-16` da referência. Não foi usado `cos(1)` como resultado genérico.

| n | Referência armazenada no JSON |
| --- | --- |
| 1 | 1.0 |
| 2 | 0.5 |
| 3 | 0.5416666666666666 |
| 4 | 0.5402777777777777 |
| 5 | 0.5403025793650794 |
| 6 | 0.5403023037918872 |
| 8 | 0.540302305868092 |
| 10 | 0.5403023058681398 |
| 15 | 0.5403023058681398 |
| 20 | 0.5403023058681398 |

As somas para `n=10`, `15` e `20` são diferentes em aritmética exata, mas
coincidem após o arredondamento para `float`. Com tolerância de `1e-9`, alguns
valores próximos também são indistinguíveis. Os casos iniciais verificam a
contagem de termos e impedem que devolver sempre uma aproximação de `cos(1)`
passe em toda a bateria.

## Verificação dos próprios casos

Executar da raiz do repositório, em PowerShell, usando Python 3.12.10:

```powershell
python -m unittest discover -s Laboratorio02_TrialsIA/casos_de_teste/aceitacao_k05_k06 -p "test_*.py" -v
```

Os verificadores utilizam apenas a biblioteca padrão e também podem ser rodados
com o ambiente virtual do [componente de métricas](../../metricas_estruturais/README.md).
Eles conferem o formato da base central, as quantidades por kata, os contratos
de entrada, a cobertura e as referências dos 21 casos, além da tolerância
explícita e da compatibilidade do comparador. Não executam soluções nem calculam
a taxa de testes aprovados de participantes. A exigência de recursão precisa de
avaliação do código; testes de entrada e saída, isoladamente, não a demonstram.
