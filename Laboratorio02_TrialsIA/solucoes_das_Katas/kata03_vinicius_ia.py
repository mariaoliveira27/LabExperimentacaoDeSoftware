import sys

# Aumenta o limite de recursão caso os casos de teste tenham strings muito grandes
sys.setrecursionlimit(10000)

def cifra_cesar_recursiva(texto, index=0):
    """
    Função recursiva para cifrar uma string com deslocamento de 3 posições.
    Utiliza um índice para evitar a criação de múltiplas substrings (fatiamento),
    melhorando a performance e uso de memória.
    """
    # Caso base: se o índice chegou ao final da string, retorna vazio
    if index == len(texto):
        return ""
    
    # Passo recursivo: desloca o caractere atual (+3 na tabela ASCII)
    caractere_cifrado = chr(ord(texto[index]) + 3)
    
    # Concatena o caractere cifrado com o restante da resolução recursiva
    return caractere_cifrado + cifra_cesar_recursiva(texto, index + 1)

def main():
    while True:
        try:
            # Lê a linha da entrada padrão (remove quebras de linha no final, se houver,
            # mas mantém os espaços que fazem parte do texto)
            linha = input()
            
            # Condição de parada
            if linha == "FIM":
                break
                
            # Processa a string e imprime o resultado
            print(cifra_cesar_recursiva(linha))
            
        except EOFError:
            # Encerra o loop caso a entrada termine subitamente (comum em juízes online)
            break

if __name__ == "__main__":
    main()