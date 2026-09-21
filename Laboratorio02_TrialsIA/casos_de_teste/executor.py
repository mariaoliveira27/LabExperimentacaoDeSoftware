import subprocess
import os
import json
import math
import sys
import time

# Tempo máximo para cada caso de teste pode rodar antes de ser interrompido
TIMEOUT_SEGUNDOS = 5


def normalizar_saida(texto: str) -> str:
    # Separa o texto em linhas, remove espaços em branco no fim de cada linha
    linhas = [linha.rstrip() for linha in texto.strip().splitlines()]
    
    # Junta todas as linhas com um único espaço entre elas
    return ' '.join(linhas)


def comparar_saidas(saida_obtida: str, d_esperada: dict) -> bool:
    
    saida_norm = normalizar_saida(saida_obtida)                          # Limpa a saída gerada pela solução
    saida_esperada_norm = normalizar_saida(d_esperada["saida_esperada"]) # Limpa a saída esperada definida no JSON
    
    # Verifica se oteste exige comparação numérica
    if d_esperada.get("tipo_comparacao") == "float":
        try:
            obtido = float(saida_norm)
            esperado = float(saida_esperada_norm)
            if not (math.isfinite(obtido) and math.isfinite(esperado)):
                return False
            if "tolerancia_absoluta" in d_esperada:
                tolerancia = float(d_esperada["tolerancia_absoluta"])
                if not math.isfinite(tolerancia) or tolerancia < 0:
                    return False
                return math.isclose(obtido, esperado, abs_tol=tolerancia, rel_tol=0.0)
            return math.isclose(obtido, esperado, abs_tol=1e-4)
        except (TypeError, ValueError):
            return False
    
    # Para comparações de texto comum, verifica se as cadeias são idênticas
    return saida_norm == saida_esperada_norm


def _tempo_restante(deadline):
    """Retorna o orçamento restante do relógio monotônico da rodada."""
    if deadline is None:
        return None
    if not math.isfinite(deadline):
        raise ValueError("O deadline deve ser um instante monotônico finito.")
    restante = deadline - time.monotonic()
    if restante <= 0:
        raise TimeoutError("O limite de tempo da rodada foi atingido durante os testes.")
    return restante


def executar_casos_de_teste(
    comando_exec: list, entrada: str, caso_teste: dict, *, timeout=None,
    deadline=None,
) -> str:
    """Executa um caso, respeitando seu timeout e o deadline global opcional.

    ``deadline`` é um instante absoluto de ``time.monotonic()``. Seu término
    lança ``TimeoutError``; ``TIMEOUT`` continua indicando apenas o limite do
    caso. Falhas ao iniciar o executor propagam sua exceção de infraestrutura.
    """
    limite_caso = TIMEOUT_SEGUNDOS if timeout is None else timeout
    if not math.isfinite(limite_caso) or limite_caso <= 0:
        raise ValueError("O timeout por caso deve ser positivo e finito.")
    restante = _tempo_restante(deadline)
    limitado_pela_rodada = restante is not None and restante <= limite_caso
    limite_execucao = min(limite_caso, restante) if restante is not None else limite_caso
    try:
        # Executa o arquivo Python
        processo = subprocess.run(
            comando_exec,              # Comando executado
            input=entrada,             # Entrada enviada para o input
            text=True,                 # Interpreta as entradas e saídas como string
            capture_output=True,       # Captura os print() e mensagens de erro do programa
            timeout=limite_execucao    # Respeita também o orçamento da rodada
        )
        _tempo_restante(deadline)
        
        # Verifica se o código fechou com erro
        if processo.returncode != 0:
            return "ERRO_EXECUCAO"
        
        # Se executou sem erros, compara a saída do terminal com o esperado
        aprovado = comparar_saidas(processo.stdout, caso_teste)
        _tempo_restante(deadline)
        if aprovado:
            return "APROVADO"
        else:
            return "SAIDA_INCORRETA"
        
    except subprocess.TimeoutExpired as erro:
        if limitado_pela_rodada:
            raise TimeoutError(
                "O limite de tempo da rodada foi atingido durante os testes."
            ) from erro
        _tempo_restante(deadline)
        return "TIMEOUT"               # Entrou em loop ou estourou os 5 segundos
    
    
def avaliar_solucao(
    caminho_codigo: str, chave_kata: str,
    arquivo_testes: str = "casos_de_teste_katas.json", *, deadline=None,
):
    """Avalia a bateria inteira dentro do deadline monotônico, quando informado.

    Em caso de limite global não retorna contagens de testes não executados.
    As chamadas existentes, sem deadline, mantêm o limite individual de 5s.
    """
    _tempo_restante(deadline)
    
    # Procura se o arquivo .py esta no computador
    if not os.path.isfile(caminho_codigo):
        raise FileNotFoundError(f"O arquivo de código '{caminho_codigo}' não foi encontrado.")
    
    # Valida se o arquivo possui extensão .py
    if not caminho_codigo.endswith('.py'):
        raise ValueError("O arquivo de solução deve ter extensão .py!")
    
    # Se o arquivo JSON de testes não estiver no diretório atual, procura na mesma pasta deste script
    if not os.path.isfile(arquivo_testes):
        dir_atual = os.path.dirname(os.path.abspath(__file__))
        arquivo_testes = os.path.join(dir_atual, arquivo_testes)

    # Abre e carrega os testes do arquivo JSON
    with open(arquivo_testes, 'r', encoding='utf-8-sig') as f:
        todos_testes = json.load(f)
    _tempo_restante(deadline)
    
    # Extrai do JSON apenas a lista de testes correspondente ao Kata solicitado
    casos = todos_testes.get(chave_kata, [])
    if not casos:
        print(f"Não foram encontrados casos de teste para a chave '{chave_kata}' no arquivo '{arquivo_testes}'.")
        return None
    
    # Monta a lista do comando utiliza o executável Python atual + caminho do arquivo
    comando_exec = [sys.executable, caminho_codigo]

    # Contadores de desempenho e Lista com o log detalhado
    aprovados, reprovados = 0, 0
    detalhes_resultados = []
    
    # Executa os 10 casos de teste do kata
    for idx, caso in enumerate(casos, 1):
        # Executa o teste isolado
        _tempo_restante(deadline)
        if deadline is None:
            resultado = executar_casos_de_teste(comando_exec, caso["entrada"], caso)
        else:
            resultado = executar_casos_de_teste(
                comando_exec, caso["entrada"], caso, deadline=deadline,
            )
        
        # Incrementa o contador
        if resultado == "APROVADO":
            aprovados += 1
        else:
            reprovados += 1
        
        # Guarda o log detalhado do teste
        detalhes_resultados.append({
            "caso_teste": idx,
            "finalidade": caso["finalidade"],
            "resultado": resultado
        })
    
    _tempo_restante(deadline)
    # Cálculo das métricas após a conclusão dos testes  
    total = len(casos)
    taxa_sucesso = (aprovados / total) * 100 if total > 0 else 0.0
    
    # Consolidação dos resultados
    relatorio = {
        "total_casos": total,
        "aprovados": aprovados,
        "reprovados": reprovados,
        "taxa_sucesso": round(taxa_sucesso, 2),
        "passou_todos": aprovados == total,
        "detalhes": detalhes_resultados
    }
    
    # Exibição do resumo na tela do terminal
    print(f"\n--- RELATÓRIO DE AVALIAÇÃO: {chave_kata} ---")
    print(f"Aprovados: {aprovados} / {total} ({relatorio['taxa_sucesso']}% de sucesso)")
    print(f"Resultado Final: {'APROVADO' if relatorio['passou_todos'] else 'REPROVADO'}\n")
    
    return relatorio

# Permite executar o script pela linha de comando
if __name__ == "__main__":
    # Verifica se os parâmetros necessários foram informados no terminal
    if len(sys.argv) < 3:
        print("Uso correto: python executor.py <caminho_solucao.py> <chave_kata>")
        print("Exemplo: python executor.py ../../Katas/solucao_kata01.py kata01")
    else:
        # Chama a função passando o caminho da solução e a chave do kata enviados pelo terminal
        avaliar_solucao(sys.argv[1], sys.argv[2])
