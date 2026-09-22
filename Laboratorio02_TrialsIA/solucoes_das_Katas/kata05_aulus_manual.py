

def buscar(vetor, tamanho, valor, posicao=0):
    if posicao == tamanho:
        return -1
    if vetor[posicao] == valor:
        return posicao

    return buscar(vetor, tamanho, valor, posicao + 1)


def main():
    tamanho = int(input())
    elementos = input().split()
    valor = int(input())

    vetor = []
    for elemento in elementos:
        vetor.append(int(elemento))

    print(buscar(vetor, tamanho, valor))


if __name__ == "__main__":
    main()
