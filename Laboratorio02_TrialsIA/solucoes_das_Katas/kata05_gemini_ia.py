def busca(A, n, x):
    if n <= 0:
        return -1
    pos = busca(A, n - 1, x)
    if pos != -1:
        return pos
    if A[n - 1] == x:
        return n - 1
    return -1


# Alias alternativo para flexibilidade de nomenclatura
busca_vetor = busca