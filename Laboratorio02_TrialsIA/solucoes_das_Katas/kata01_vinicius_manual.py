import sys

def e_vogal(c):
    return c.lower() in 'aeiou'

def e_consoante(c):
    return c.isalpha() and not e_vogal(c)

def somente_vogais(s):
    if not s:
        return True
    return e_vogal(s[0]) and somente_vogais(s[1:])

def somente_consoantes(s):
    if not s:
        return True
    return e_consoante(s[0]) and somente_consoantes(s[1:])

def e_inteiro(s, idx=0):
    if not s:
        return False
    if idx == 0 and s[0] in '+-':
        return e_inteiro(s[1:], 1) if len(s) > 1 else False
    if not s[0].isdigit():
        return False
    if len(s) == 1:
        return True
    return e_inteiro(s[1:], idx + 1)

def e_real(s, tem_ponto=False, idx=0):
    if not s:
        return False
    if idx == 0 and s[0] in '+-':
        return e_real(s[1:], tem_ponto, 1) if len(s) > 1 else False
    if s[0] in '.,':
        if tem_ponto:
            return False
        return e_real(s[1:], True, idx + 1) if len(s) > 1 else False
    if not s[0].isdigit():
        return False
    if len(s) == 1:
        return True
    return e_real(s[1:], tem_ponto, idx + 1)

def processar_linha(s):
    x1 = "SIM" if somente_vogais(s) else "NAO"
    x2 = "SIM" if somente_consoantes(s) else "NAO"
    x3 = "SIM" if e_inteiro(s) else "NAO"
    x4 = "SIM" if e_real(s) else "NAO"
    return f"{x1} {x2} {x3} {x4}"

def main():
    for linha in sys.stdin:
        linha = linha.rstrip('\r\n')
        if linha == "FIM":
            break
        print(processar_linha(linha))

if __name__ == "__main__":
    main()