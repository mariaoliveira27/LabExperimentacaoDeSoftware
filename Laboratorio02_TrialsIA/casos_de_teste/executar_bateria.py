import csv
import os
import re
from executor import avaliar_solucao

# Configurações do script
DIRETORIO_SOLUCOES = os.path.abspath(os.path.join(os.path.dirname(__file__), "../solucoes_das_Katas"))
ARQUIVO_SAIDA_CSV = "resultado_bateria_katas.csv"


def extrair_metadados_nome(nome_arquivo: str):
    # Extrai Kata, Integrante e Tratamento a partir do nome do arquivo.
    # Exemplo: 'kata01_vini_manual.py' -> ('kata01', 'vini', 'manual')
    
    # Expressão regular para capturar o padrão do nome do arquivo
    padrao = r"^(kata\d{2})_([a-zA-Z0-9]+)_(manual|ia)\.py$"
    
    # Tenta casar o padrão com o nome do arquivo
    match = re.match(padrao, nome_arquivo, re.IGNORECASE)
    
    # Se houver correspondência, retorna os grupos capturados em minúsculas
    if match:
        return match.group(1).lower(), match.group(2).lower(), match.group(3).lower()
    
    # Se não houver correspondência, retorna None para todos os campos
    return None, None, None


def rodar_bateria_completa():
    # Estrutura do cabeçalho do arquivo CSV de saída
    cabecalhos = [
        "Kata", 
        "Integrante", 
        "Tratamento", 
        "Arquivo_Solucao", 
        "Total_Casos", 
        "Aprovados", 
        "Reprovados", 
        "Taxa_Sucesso_Pct", 
        "Passou_Todos"
    ]
    
    dados_csv = []
    
    if not os.path.exists(DIRETORIO_SOLUCOES):
        print(f"Diretório '{DIRETORIO_SOLUCOES}' não encontrado. Certifique-se de que o caminho está correto.")
        return
    
    arquivos = [f for f in os.listdir(DIRETORIO_SOLUCOES) if f.endswith('.py')]
    
    if not arquivos:
        print(f"Nenhum arquivo de solução encontrado em '{DIRETORIO_SOLUCOES}'.")
        return

    print(f"Iniciando bateria de testes para {len(arquivos)} arquivo(s) em /solucoes\n" + "="*55)

    for arquivo in arquivos:
        # Define o caminho  do arquivo de solução
        caminho_completo = os.path.join(DIRETORIO_SOLUCOES, arquivo)
        
        # Extrai os metadados do nome do arquivo
        kata, integrante, tratamento = extrair_metadados_nome(arquivo)

        # Verifica se o nome do arquivo segue o padrão esperado
        if not kata:
            print(f"Arquivo '{arquivo}' não segue o padrão esperado.")
            continue
        
        relatorio = avaliar_solucao(caminho_completo, kata)

        # Se o relatório foi gerado com sucesso, armazena a linha do CSV
        if relatorio:
            dados_csv.append([
                kata,
                integrante,
                tratamento,
                arquivo,
                relatorio["total_casos"],
                relatorio["aprovados"],
                relatorio["reprovados"],
                relatorio["taxa_sucesso"],
                relatorio["passou_todos"]
            ])

    # Escreve todos os resultados consolidados no arquivo CSV
    with open(ARQUIVO_SAIDA_CSV, mode='w', newline='', encoding='utf-8') as f:
        escritor = csv.writer(f)
        escritor.writerow(cabecalhos)
        escritor.writerows(dados_csv)

    print("="*55)
    print(f"Relatório gerado em: '{ARQUIVO_SAIDA_CSV}'\n")


if __name__ == "__main__":
    rodar_bateria_completa()