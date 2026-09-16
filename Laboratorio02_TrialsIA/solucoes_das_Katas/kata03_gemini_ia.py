import sys

sys.setrecursionlimit(10000)

def cifrado(s):
    if not s:
        return ""
    return chr(ord(s[0]) + 3) + cifrado(s[1:])

def main():
    lines = sys.stdin.read().splitlines()
    for line in lines:
        if line == "FIM":
            break
        print(cifrado(line))

if __name__ == "__main__":
    main()