import re
import sys

def avaliar_expressao_rec(exp):
    exp = exp.replace(" ", "")
    if exp in ("0", "1"):
        return int(exp)

    # Substituição de not
    if "not(0)" in exp:
        return avaliar_expressao_rec(exp.replace("not(0)", "1"))
    if "not(1)" in exp:
        return avaliar_expressao_rec(exp.replace("not(1)", "0"))

    # Substituição de and
    match_and = re.search(r'and\(([01,]+)\)', exp)
    if match_and:
        args = match_and.group(1).split(',')
        res = "1" if all(a == "1" for a in args) else "0"
        nova_exp = exp[:match_and.start()] + res + exp[match_and.end():]
        return avaliar_expressao_rec(nova_exp)

    # Substituição de or
    match_or = re.search(r'or\(([01,]+)\)', exp)
    if match_or:
        args = match_or.group(1).split(',')
        res = "1" if any(a == "1" for a in args) else "0"
        nova_exp = exp[:match_or.start()] + res + exp[match_or.end():]
        return avaliar_expressao_rec(nova_exp)

    return int(exp)

def resolver_linha(linha):
    tokens = linha.strip().split()
    if not tokens or tokens[0] == '0':
        return None

    n = int(tokens[0])
    valores = tokens[1:n+1]
    expressao = "".join(tokens[n+1:])

    # Substitui as variáveis A, B, C, ... pelos valores correspondentes
    for i in range(n):
        letra = chr(ord('A') + i)
        expressao = expressao.replace(letra, valores[i])

    return avaliar_expressao_rec(expressao)

def main():
    for linha in sys.stdin:
        resultado = resolver_linha(linha)
        if resultado is not None:
            print(resultado)

if __name__ == "__main__":
    main()