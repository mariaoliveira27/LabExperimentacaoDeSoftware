import sys


def factorial(k):
    if k <= 1:
        return 1
    return k * factorial(k - 1)


def calculate_c(n):
    if n <= 0:
        return 0.0
    k = n - 1
    sign = -1 if k % 2 != 0 else 1
    term = sign / factorial(2 * k)
    return calculate_c(n - 1) + term


def main():
    try:
        line = sys.stdin.read().strip()
        if line:
            n = int(line)
            result = calculate_c(n)
            print(result)
    except Exception:
        pass


if __name__ == "__main__":
    main()