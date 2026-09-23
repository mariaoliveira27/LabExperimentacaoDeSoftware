import sys

# Aumenta o limite de recursão para vetores muito grandes
sys.setrecursionlimit(10000)

def busca_recursiva(A, n, x, index=0):
    """
    Realiza a busca linear recursiva de x no vetor A contendo n elementos.
    Retorna a posição da primeira ocorrência de x ou -1 caso não seja encontrado.
    """
    # Caso base 1: se o índice atingiu 'n', o elemento não está no vetor
    if index >= n:
        return -1
    
    # Caso base 2: o elemento foi encontrado na posição atual
    if A[index] == x:
        return index
    
    # Passo recursivo: avança para a próxima posição
    return busca_recursiva(A, n, x, index + 1)

# --- Exemplo de uso ---
if __name__ == "__main__":
    vetor = [10, 25, 30, 42, 15, 90]
    quantidade = len(vetor)
    
    # Teste 1: Elemento presente no vetor
    chave = 42
    posicao = busca_recursiva(vetor, quantidade, chave)
    print(f"Elemento {chave} encontrado na posição: {posicao}")  # Saída: 3

    # Teste 2: Elemento ausente no vetor
    chave = 99
    posicao = busca_recursiva(vetor, quantidade, chave)
    print(f"Elemento {chave} encontrado na posição: {posicao}")  # Saída: -1