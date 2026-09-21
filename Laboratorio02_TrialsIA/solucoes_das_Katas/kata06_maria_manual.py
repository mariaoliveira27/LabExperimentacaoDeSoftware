"""Solução Kata 06 (Cálculo de Cosseno) - Maria (Tratamento: Manual).

Calcula recursivamente a soma parcial da série de Taylor de cos(1)
com n termos: S(n) = sum_{k=0}^{n-1} (-1)^k / (2k)!.
Atende ao contrato numérico K06 com precisão float de 1e-9.
"""

import sys


def fatorial_recursivo(k: int) -> int:
    """Calcula k! recursivamente."""
    if k <= 1:
        return 1
    return k * fatorial_recursivo(k - 1)


def somar_termos_cosseno(n: int) -> float:
    """Calcula recursivamente a soma dos primeiros n termos da série de Taylor."""
    if n <= 0:
        return 0.0
    k = n - 1
    sinal = -1.0 if (k % 2 != 0) else 1.0
    termo = sinal / float(fatorial_recursivo(2 * k))
    return somar_termos_cosseno(n - 1) + termo


def main() -> None:
    try:
        conteudo = sys.stdin.read().strip()
        if conteudo:
            n = int(conteudo)
            resultado = somar_termos_cosseno(n)
            print(resultado)
    except Exception:
        pass


if __name__ == "__main__":
    main()
