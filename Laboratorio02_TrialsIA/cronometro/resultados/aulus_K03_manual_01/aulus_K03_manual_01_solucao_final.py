
import sys

def cifrar(texto, posicao=0):
    if posicao == len(texto):
        return ""

    caractere_cifrado = chr(ord(texto[posicao]) + 3)
    restante = cifrar(texto, posicao + 1)
    return caractere_cifrado + restante


def main():
    for linha in sys.stdin:
        texto = linha.rstrip("\r\n")
        if texto == "FIM":
            break

        print(cifrar(texto))


if __name__ == "__main__":
    main()
