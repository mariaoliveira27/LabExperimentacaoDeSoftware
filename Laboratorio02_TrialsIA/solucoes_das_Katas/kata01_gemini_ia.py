import sys

# Aumenta o limite de recursão por segurança caso as strings de entrada sejam longas
sys.setrecursionlimit(2000)

def is_vogais(s, i=0):
    if not s:
        return False
    if i == len(s):
        return True
    if s[i] in "aeiouAEIOU":
        return is_vogais(s, i + 1)
    return False

def is_consoantes(s, i=0):
    if not s:
        return False
    if i == len(s):
        return True
    c = s[i]
    if c.isalpha() and c not in "aeiouAEIOU":
        return is_consoantes(s, i + 1)
    return False

def is_inteiro(s, i=0):
    if not s:
        return False
    if i == len(s):
        return True
    if '0' <= s[i] <= '9':
        return is_inteiro(s, i + 1)
    return False

def is_real(s, i=0, separators=0, digits=0):
    if not s:
        return False
    if i == len(s):
        return separators <= 1 and digits > 0
    c = s[i]
    if '0' <= c <= '9':
        return is_real(s, i + 1, separators, digits + 1)
    elif c in '.,':
        if separators == 0:
            return is_real(s, i + 1, separators + 1, digits)
        else:
            return False
    else:
        return False

def main():
    lines = sys.stdin.read().splitlines()
    for line in lines:
        if line == "FIM":
            break
        x1 = "SIM" if is_vogais(line) else "NAO"
        x2 = "SIM" if is_consoantes(line) else "NAO"
        x3 = "SIM" if is_inteiro(line) else "NAO"
        x4 = "SIM" if is_real(line) else "NAO"
        print(f"{x1} {x2} {x3} {x4}")

if __name__ == "__main__":
    main()