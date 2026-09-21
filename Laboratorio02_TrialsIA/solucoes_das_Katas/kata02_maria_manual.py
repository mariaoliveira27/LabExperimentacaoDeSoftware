"""Solução Kata 02 (Álgebra booleana) - Maria (Tratamento: Manual).

Avalia recursivamente expressões booleanas com operadores 'not', 'and' e 'or',
substituindo as variáveis A, B, C pelas entradas binárias correspondentes.
"""

import sys


def separar_argumentos(expressao: str) -> list[str]:
    """Separa os argumentos de uma função booleana no nível mais externo."""
    args = []
    nivel = 0
    atual = []
    for caractere in expressao:
        if caractere == "(":
            nivel += 1
            atual.append(caractere)
        elif caractere == ")":
            nivel -= 1
            atual.append(caractere)
        elif caractere == "," and nivel == 0:
            args.append("".join(atual).strip())
            atual = []
        else:
            atual.append(caractere)
    if atual:
        args.append("".join(atual).strip())
    return args


def avaliar_recursivo(expr: str) -> int:
    """Avalia recursivamente a expressão booleana."""
    s = expr.strip()
    if s == "0":
        return 0
    if s == "1":
        return 1

    if s.startswith("not(") and s.endswith(")"):
        conteudo = s[4:-1]
        return 1 - avaliar_recursivo(conteudo)

    if s.startswith("and(") and s.endswith(")"):
        conteudo = s[4:-1]
        args = separar_argumentos(conteudo)
        for arg in args:
            if avaliar_recursivo(arg) == 0:
                return 0
        return 1

    if s.startswith("or(") and s.endswith(")"):
        conteudo = s[3:-1]
        args = separar_argumentos(conteudo)
        for arg in args:
            if avaliar_recursivo(arg) == 1:
                return 1
        return 0

    return 0


def main() -> None:
    for linha in sys.stdin:
        texto = linha.strip()
        if not texto or texto == "0":
            break
        partes = texto.split()
        if not partes:
            continue
        n = int(partes[0])
        if n == 0:
            break
        valores = partes[1 : n + 1]
        corpo_expr = "".join(partes[n + 1 :])

        for i, val in enumerate(valores):
            var = chr(ord("A") + i)
            corpo_expr = corpo_expr.replace(var, val)

        resultado = avaliar_recursivo(corpo_expr)
        print(resultado)


if __name__ == "__main__":
    main()
