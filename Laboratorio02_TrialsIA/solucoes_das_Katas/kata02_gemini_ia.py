import sys


def split_args(s):
    args = []
    depth = 0
    current = []
    for char in s:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            args.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        args.append("".join(current))
    return args


def eval_expr(s):
    s = s.strip()
    if s == "0":
        return 0
    if s == "1":
        return 1

    if s.startswith("not(") and s.endswith(")"):
        inner = s[4:-1]
        return 1 - eval_expr(inner)

    if s.startswith("and(") and s.endswith(")"):
        inner = s[4:-1]
        args = split_args(inner)
        for arg in args:
            if eval_expr(arg) == 0:
                return 0
        return 1

    if s.startswith("or(") and s.endswith(")"):
        inner = s[3:-1]
        args = split_args(inner)
        for arg in args:
            if eval_expr(arg) == 1:
                return 1
        return 0

    return 0


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line or line == "0":
            break
        tokens = line.split()
        if not tokens:
            continue
        n = int(tokens[0])
        if n == 0:
            break
        values = tokens[1 : n + 1]
        expr = "".join(tokens[n + 1 :])

        for i, val in enumerate(values):
            var_name = chr(ord("A") + i)
            expr = expr.replace(var_name, val)

        result = eval_expr(expr)
        print(result)


if __name__ == "__main__":
    main()