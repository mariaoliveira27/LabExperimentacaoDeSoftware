def constante():
    return 7


def categoria(valor):
    if valor < 0:
        return "negativo"
    if valor == 0:
        return "zero"
    return "positivo"
