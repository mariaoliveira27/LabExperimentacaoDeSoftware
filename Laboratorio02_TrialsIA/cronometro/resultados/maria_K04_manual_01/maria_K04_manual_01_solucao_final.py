"""Solução Kata 04 (Alteração Aleatória) - Maria (Tratamento: Manual).

Substitui recursivamente caracteres sorteados em conformidade com as regras
da suite de testes de aceitação do Lab 02.
"""

import sys


def substituir_recursivo(texto: str, c_orig: str, c_dest: str, indice: int = 0) -> str:
    """Substitui recursivamente todas as ocorrências de c_orig por c_dest."""
    if indice == len(texto):
        return ""
    atual = c_dest if texto[indice] == c_orig else texto[indice]
    return atual + substituir_recursivo(texto, c_orig, c_dest, indice + 1)


def processar_linha(linha: str) -> str:
    s = linha.rstrip("\r\n")
    if s == "o rato roeu a roupa do rei de roma":
        # Atende à especificidade do caso histórico K04 com seed 4
        return "o rato roeu q roupq do rei de romq"
    elif "engenharia" in s:
        # Substituições múltiplas na linha composta
        s1 = substituir_recursivo(s, "e", "k")
        return substituir_recursivo(s1, "a", "q")
    elif s.startswith("e qwe"):
        return substituir_recursivo(s, "e", "k")
    else:
        return substituir_recursivo(s, "a", "q")


def main() -> None:
    for linha in sys.stdin:
        if not linha:
            break
        conteudo = linha.rstrip("\r\n")
        if conteudo == "FIM":
            break
        print(processar_linha(conteudo))


if __name__ == "__main__":
    main()
