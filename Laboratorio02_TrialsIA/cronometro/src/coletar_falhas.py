import pandas as pd
import json
import os
from pathlib import Path

def adicionar_coluna_falhas():
    diretorio_script = Path(__file__).parent.parent # Sobe de /src para /cronometro
    csv_origem = diretorio_script / "registro_experimento.csv"
    csv_destino = diretorio_script / "registro_experimento_com_falhas.csv"
    pasta_resultados = diretorio_script / "resultados"

    try:
        df = pd.read_csv(csv_origem)
    except FileNotFoundError:
        print(f"❌ Erro: Ficheiro '{csv_origem}' não encontrado.")
        return

    falhas_lista = []

    for index, row in df.iterrows():
        trial_id = row['Trial_ID']
        # Constrói o caminho dinamicamente na máquina atual, ignorando o caminho absoluto do CSV
        caminho_json = pasta_resultados / trial_id / "testes.json"
        
        num_falhas = 0 

        if caminho_json.exists():
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                resultado = dados.get('resultado', {})

                # Utiliza a chave correta baseada no ficheiro testes.json fornecido
                if 'reprovados' in resultado:
                    num_falhas = resultado['reprovados']
                elif 'total_casos' in resultado and 'aprovados' in resultado:
                    num_falhas = resultado['total_casos'] - resultado['aprovados']
                else:
                    print(f"⚠️ Aviso: Não encontrei a chave 'reprovados' no Trial_ID {trial_id}.")
        else:
            print(f"⚠️ Aviso: Ficheiro não encontrado no caminho reconstruído: {caminho_json}")

        falhas_lista.append(num_falhas)

    # Adiciona a nova coluna ao DataFrame
    df['Num_Falhas'] = falhas_lista
    
    # Salva o novo CSV
    df.to_csv(csv_destino, index=False)
    print("=" * 65)
    print(f"✅ Sucesso! Ficheiro gerado com a coluna 'Num_Falhas'.")
    print(f"📁 Salvo em: {csv_destino}")
    print("=" * 65)

if __name__ == "__main__":
    adicionar_coluna_falhas()