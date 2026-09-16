"""Solução demonstrativa para Kata 01 - Is recursivo.
Implementa verificações recursivas de vogais, consoantes, inteiro e real.
Usada exclusivamente para validação da infraestrutura da Sprint 01.
"""

import sys


def eh_vogal_recursivo(texto: str, indice: int = 0) -> bool:
    if not texto:
        return False
    vogais = set("aeiouAEIOU")
    if indice == len(texto):
        return True
    if texto[indice] not in vogais:
        return False
    return eh_vogal_recursivo(texto, indice + 1)


def eh_consoante_recursivo(texto: str, indice: int = 0) -> bool:
    if not texto:
        return False
    consoantes = set("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ")
    if indice == len(texto):
        return True
    if texto[indice] not in consoantes:
        return False
    return eh_consoante_recursivo(texto, indice + 1)


def eh_digito_recursivo(texto: str, indice: int = 0) -> bool:
    if not texto:
        return False
    if indice == len(texto):
        return True
    if not texto[indice].isdigit():
        return False
    return eh_digito_recursivo(texto, indice + 1)


def eh_inteiro(texto: str) -> bool:
    if not texto:
        return False
    if texto[0] == "-":
        return len(texto) > 1 and eh_digito_recursivo(texto, 1)
    return eh_digito_recursivo(texto, 0)


def eh_real(texto: str) -> bool:
    if not texto or "." not in texto:
        return False
    partes = texto.split(".")
    if len(partes) != 2:
        return False
    parte_int, parte_frac = partes
    if not parte_frac or not eh_digito_recursivo(parte_frac, 0):
        return False
    if parte_int == "" or parte_int == "-":
        return False
    if parte_int[0] == "-":
        return len(parte_int) > 1 and eh_digito_recursivo(parte_int, 1)
    return eh_digito_recursivo(parte_int, 0)


def classificar_linha(linha: str) -> str:
    conteudo = linha.rstrip("\r\n")
    x1 = "SIM" if eh_vogal_recursivo(conteudo) else "NAO"
    x2 = "SIM" if eh_consoante_recursivo(conteudo) else "NAO"
    x3 = "SIM" if eh_inteiro(conteudo) else "NAO"
    x4 = "SIM" if eh_real(conteudo) else "NAO"
    return f"{x1} {x2} {x3} {x4}"


def main() -> None:
    for linha in sys.stdin:
        if not linha:
            break
        print(classificar_linha(linha))


if __name__ == "__main__":
    main()

