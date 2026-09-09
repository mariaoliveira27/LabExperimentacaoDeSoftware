4. Alteração Aleatória

Crie um método recursivo que receba uma string, sorteie duas letras minúsculas aleatórias (código ASCII ≥ 'a' e ≤ 'z'), substitua todas as ocorrências da primeira letra na string pela segunda e retorne a string com as alterações efetuadas.
Na saída padrão, para cada linha de entrada, execute o método desenvolvido nesta questão e mostre a string retornada como uma linha de saída.
Abaixo, observamos um exemplo de entrada supondo que para a primeira linha as letras sorteadas foram o 'a' e o 'q'.
Para a segunda linha, foram o 'e' e o 'k'.

EXEMPLO DE ENTRADA:

o rato roeu a roupa do rei de roma

e qwe qwe qwe ewq ewq ewq

FIM

EXEMPLO DE SAIDA:

o rato roeu q roupq do rei de romq

k qwk qwk qwk kwq kwq kwq
A classe Random, da hierarquia de classes de Java, gera números (ou letras) aleatórios e o exemplo abaixo mostra uma letra minúscula na tela. Em especial, destacamos que:

i) seed é a semente para geração de números aleatórios;

ii) nesta questão, por causa da correção automática, seed deverá ser quatro.
    Random gerador new Random():
    gerador setSeed (4):
    System.outintin ((char) (a (Math abs (gerador.nextInt()) % 26))):