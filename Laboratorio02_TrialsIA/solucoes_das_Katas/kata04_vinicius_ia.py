import sys

# Aumenta o limite de recursão para textos longos
sys.setrecursionlimit(10000)

class JavaRandom:
    """
    Emula a classe java.util.Random para garantir que os caracteres aleatórios
    gerados sejam idênticos aos esperados pelo corretor automático.
    """
    def __init__(self, seed=4):
        self.seed = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def next_int(self):
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        val = self.seed >> 16
        # Converte para inteiro de 32 bits com sinal
        if val >= (1 << 31):
            val -= (1 << 32)
        return val

def alteracao_aleatoria(texto, gerador, c1=None, c2=None, index=0):
    """
    Método recursivo que sorteia duas letras minúsculas (na chamada inicial)
    e substitui todas as ocorrências de c1 por c2 ao longo da string.
    """
    # Sorteio dos caracteres na primeira execução do método para a linha
    if c1 is None and c2 is None:
        c1 = chr(ord('a') + (abs(gerador.next_int()) % 26))
        c2 = chr(ord('a') + (abs(gerador.next_int()) % 26))

    # Caso base: fim da string
    if index == len(texto):
        return ""

    # Passo recursivo: substitui c1 por c2 se for o caractere atual
    char_atual = c2 if texto[index] == c1 else texto[index]

    return char_atual + alteracao_aleatoria(texto, gerador, c1, c2, index + 1)

def main():
    # Instancia o gerador com a semente 4 UMA ÚNICA VEZ antes do loop
    gerador = JavaRandom(4)

    while True:
        try:
            linha = input()
            if linha == "FIM":
                break

            # Processa e imprime a linha alterada
            print(alteracao_aleatoria(linha, gerador))

        except EOFError:
            break

if __name__ == "__main__":
    main()