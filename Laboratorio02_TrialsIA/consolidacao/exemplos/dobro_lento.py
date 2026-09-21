"""Espera real que excede o timebox reduzido da demonstração."""

import time


def dobro(numero: int) -> int:
    time.sleep(0.2)
    return 2 * numero


print(dobro(int(input())))
