import sys

sys.setrecursionlimit(100000)


class JavaRandom:

    def __init__(self, seed=4):
        self.seed = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def nextInt(self):
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        res = self.seed >> 16
        if res >= (1 << 31):
            res -= 1 << 32
        return res


gerador = JavaRandom(4)


def substituir_recursivo(s, c1, c2, idx=0):
    if idx == len(s):
        return ""
    char = c2 if s[idx] == c1 else s[idx]
    return char + substituir_recursivo(s, c1, c2, idx + 1)


def main():
    lines = sys.stdin.read().splitlines()
    for line in lines:
        if line == "FIM":
            break
        c1 = chr(ord("a") + (abs(gerador.nextInt()) % 26))
        c2 = chr(ord("a") + (abs(gerador.nextInt()) % 26))
        print(substituir_recursivo(line, c1, c2))


if __name__ == "__main__":
    main()