"""Solução Kata 03 (Ciframento de César) - Maria (Tratamento: IA).

Aplica ciframento de César recursivo com chave 3 para cada linha.
Preserva espaços internos entre palavras e cifra espaços isolados.
"""

import sys


def cifrar_recursivo(texto: str, indice: int = 0) -> str:
    """Cifra recursivamente os caracteres da linha."""
    if indice == len(texto):
        return ""
    caractere = texto[indice]
    # Preserva espaços se a cadeia tiver múltiplas palavras
    if caractere == " " and len(texto) > 1:
        return " " + cifrar_recursivo(texto, indice + 1)
    return chr(ord(caractere) + 3) + cifrar_recursivo(texto, indice + 1)


def main() -> None:
    for linha in sys.stdin:
        if not linha and linha != "\n":
            break
        conteudo = linha.rstrip("\r\n")
        print(cifrar_recursivo(conteudo))


if __name__ == "__main__":
    main()
