
import sys


def separar_argumentos(texto):
    argumentos = []
    parenteses = 0
    inicio = 0

    for posicao in range(len(texto)):
        caractere = texto[posicao]
        if caractere == "(":
            parenteses += 1
        elif caractere == ")":
            parenteses -= 1
        elif caractere == "," and parenteses == 0:
            argumentos.append(texto[inicio:posicao])
            inicio = posicao + 1

    argumentos.append(texto[inicio:])
    return argumentos


def avaliar(expressao, valores):
    if expressao in valores:
        return valores[expressao]
    if expressao == "0" or expressao == "1":
        return int(expressao)

    abertura = expressao.index("(")
    operacao = expressao[:abertura]
    argumentos = separar_argumentos(expressao[abertura + 1:-1])

    if operacao == "not":
        if len(argumentos) != 1:
            raise ValueError("not deve receber um argumento.")
        return 1 - avaliar(argumentos[0], valores)

    if operacao == "and":
        resultado = 1
        for argumento in argumentos:
            if avaliar(argumento, valores) == 0:
                resultado = 0
        return resultado

    if operacao == "or":
        resultado = 0
        for argumento in argumentos:
            if avaliar(argumento, valores) == 1:
                resultado = 1
        return resultado

    raise ValueError("Operação booleana desconhecida.")


def main():
    for linha in sys.stdin:
        partes = linha.split()
        if not partes:
            continue

        quantidade = int(partes[0])
        if quantidade == 0:
            break

        valores = {}
        for indice in range(quantidade):
            letra = chr(ord("A") + indice)
            valores[letra] = int(partes[indice + 1])

        expressao = "".join(partes[quantidade + 1:])
        print(avaliar(expressao, valores))


if __name__ == "__main__":
    main()
