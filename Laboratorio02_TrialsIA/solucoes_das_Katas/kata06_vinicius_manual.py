def fatorial(k):
    if k <= 1:
        return 1
    return k * fatorial(k - 1)

def calcular_cosseno_rec(n, termo_atual=0):
    if termo_atual >= n:
        return 0.0

    sinal = 1 if termo_atual % 2 == 0 else -1
    valor_termo = sinal * (1.0 / fatorial(2 * termo_atual))

    return valor_termo + calcular_cosseno_rec(n, termo_atual + 1)

def main():
    n = int(input("Digite o número de termos (n): "))
    resultado = calcular_cosseno_rec(n)
    print(f"Aproximação de cos(1) com {n} termos: {resultado}")

if __name__ == "__main__":
    main()