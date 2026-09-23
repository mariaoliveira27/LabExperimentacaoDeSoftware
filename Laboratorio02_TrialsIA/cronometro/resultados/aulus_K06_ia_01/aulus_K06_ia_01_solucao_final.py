

def fatorial(numero):
    if numero <= 1:
        return 1
    return numero * fatorial(numero - 1)


def cosseno(quantidade_termos):
    if quantidade_termos == 1:
        return 1.0

    indice = quantidade_termos - 1
    termo = 1 / fatorial(2 * indice)
    if indice % 2 == 1:
        termo = -termo

    return cosseno(quantidade_termos - 1) + termo


def main():
    quantidade_termos = int(input())
    if quantidade_termos < 1 or quantidade_termos > 20:
        raise ValueError("A quantidade de termos deve estar entre 1 e 20.")

    print(cosseno(quantidade_termos))


if __name__ == "__main__":
    main()
