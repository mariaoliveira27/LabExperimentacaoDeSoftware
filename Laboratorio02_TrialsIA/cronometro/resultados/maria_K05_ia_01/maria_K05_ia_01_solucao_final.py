"""Solução Kata 05 (Busca em Vetor) - Maria (Tratamento: IA).

Executa busca linear recursiva para encontrar a primeira ocorrência
do valor procurado em um vetor de inteiros não ordenado.
Atende ao contrato de aceitação K05 (stdin com 3 linhas).
"""

import sys


def busca_linear_recursiva(vetor: list[int], alvo: int, indice: int = 0) -> int:
    """Retorna a primeira posição onde vetor[indice] == alvo, ou -1 se não encontrar."""
    if indice >= len(vetor):
        return -1
    if vetor[indice] == alvo:
        return indice
    return busca_linear_recursiva(vetor, alvo, indice + 1)


def main() -> None:
    linhas = sys.stdin.read().splitlines()
    if len(linhas) < 3:
        return
    n = int(linhas[0].strip())
    if n == 0:
        vetor = []
    else:
        vetor = [int(v) for v in linhas[1].strip().split()]
    alvo = int(linhas[2].strip())
    resultado = busca_linear_recursiva(vetor, alvo, 0)
    print(resultado)


if __name__ == "__main__":
    main()
