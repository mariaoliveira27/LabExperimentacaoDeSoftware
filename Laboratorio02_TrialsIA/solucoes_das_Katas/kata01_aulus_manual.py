import sys


def somente_vogais(texto, posicao=0):
    if texto == "":
        return False
    if posicao == len(texto):
        return True

    letra = texto[posicao].lower()
    if letra not in "aeiou":
        return False

    return somente_vogais(texto, posicao + 1)


def somente_consoantes(texto, posicao=0):
    if texto == "":
        return False
    if posicao == len(texto):
        return True

    letra = texto[posicao].lower()
    if letra < "a" or letra > "z":
        return False
    if letra in "aeiou":
        return False

    return somente_consoantes(texto, posicao + 1)


def numero_inteiro(texto, posicao=0):
    if texto == "" or texto == "+" or texto == "-":
        return False
    if posicao == len(texto):
        return True

    caractere = texto[posicao]
    if posicao == 0 and caractere in "+-":
        return numero_inteiro(texto, posicao + 1)
    if caractere < "0" or caractere > "9":
        return False

    return numero_inteiro(texto, posicao + 1)


def numero_real(texto, posicao=0, separadores=0, digitos=0):
    if posicao == len(texto):
        return separadores == 1 and digitos > 0

    caractere = texto[posicao]
    if posicao == 0 and caractere in "+-":
        return numero_real(texto, posicao + 1, separadores, digitos)

    if caractere == "." or caractere == ",":
        if separadores == 1:
            return False
        return numero_real(texto, posicao + 1, separadores + 1, digitos)

    if caractere < "0" or caractere > "9":
        return False

    return numero_real(texto, posicao + 1, separadores, digitos + 1)


def main():
    for linha in sys.stdin:
        texto = linha.rstrip("\r\n")

        vogais = "SIM" if somente_vogais(texto) else "NAO"
        consoantes = "SIM" if somente_consoantes(texto) else "NAO"
        inteiro = "SIM" if numero_inteiro(texto) else "NAO"
        real = "SIM" if numero_real(texto) else "NAO"

        print(vogais, consoantes, inteiro, real)


if __name__ == "__main__":
    main()
