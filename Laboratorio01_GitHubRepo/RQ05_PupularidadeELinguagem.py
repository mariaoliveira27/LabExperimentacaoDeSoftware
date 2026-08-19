import requests
import csv
import os
from collections import Counter

# Credencias e Endpoints 
TOKEN = ""  # Token de acesso pessoal do GitHub
URL = "https://api.github.com/graphql"              # Endpoint de la API GraphQL de GitHub

# Header
hearders = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Consulta GraphQL com paginação 
query = """
query ($cursor: String) {
    search(query: "stars:>5000 sort:stars-desc", type: REPOSITORY, first: 100, after: $cursor) {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            ... on Repository {
                nameWithOwner
                createdAt
                stargazerCount
                languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
                    nodes {
                        name
                    }
                }
            }
        }
    }
}
"""

# lista csv
lista_resp = []
    
# variaveis de paginação
cursor = None     # página
TOTAL_REQ = 1000  # quantidade total de repositórios

# contador de linguagens
contador_linguagens = Counter()

# Loop para paginar as requisições
while len(lista_resp) < TOTAL_REQ:
    # Dicionário de dados
    payload = {
        "query": query,
        "variables": {"cursor": cursor}
    }


    # Requisição POST para a API GraphQL do GitHub
    response = requests.post(URL, json=payload, headers=hearders)

    # Tratamento de resposta
    if response.status_code == 200:
        data = response.json()
        
        if 'errors' in data:
            print("ERRO: A API retornou algum erro nesta página.")
            print(data['errors'])
            raise SystemExit(1)
        
        search_data = data.get('data', {}).get('search', {})  # obtendo os dados da pesquisa
        repositories = search_data.get('nodes', [])           # obtendo os repositórios
        page_info = search_data.get('pageInfo', {})           # obtendo informações da páginação
        
        for repo in repositories:
            if repo is None: 
                continue # Pula repositórios invalido
            
            name_with_owner = repo['nameWithOwner']
            created_at = repo['createdAt']
            stargazer_count = repo['stargazerCount']
            
            languages_nodes = repo.get('languages', {}).get('nodes', [])
            nomes_linguagens = [lang['name'] for lang in languages_nodes if lang is not None and 'name' in lang]  # extrai apenas os nomes das linguagens
            string_linguagens = ", ".join(nomes_linguagens) if nomes_linguagens else "Sem linguagem"
            
            # linguagem primária
            linguagem_primaria = nomes_linguagens[0] if nomes_linguagens else "Sem linguagem"
            
            # atualiza o contador de linguagens
            contador_linguagens[linguagem_primaria] += 1
            
            # adiciona os dados à lista
            lista_resp.append({
                'Repositorio': name_with_owner,
                'Criado Em': created_at,
                'Estrelas': stargazer_count,
                'Linguagem Primaria': linguagem_primaria,
                'Linguagens': string_linguagens                
            })
            
            # exibe no terminal
            if len(lista_resp) % 100 == 0 or len(lista_resp) == TOTAL_REQ:
                print(f"[{len(lista_resp)}/{TOTAL_REQ}] Repositórios processados")
            
            # interrompe quando atingir o total de requisições
            if len(lista_resp) >= TOTAL_REQ:
                break
        
        # verifica se existe uma próxima página para buscar
        if page_info.get('hasNextPage') and len(lista_resp) < TOTAL_REQ:
            cursor = page_info.get('endCursor') # Atualiza o cursor para a próxima requisição
        else:
            break
    
    else:
        print(f"Erro na requisição: {response.status_code}")
        print(response.text)
        raise SystemExit(1)
    
print(f"Total de repositórios processados: {len(lista_resp)}")
        
# Gerarndo arquivo CSV: LISTA DE REPOSITÓRIOS POPULARES E SUAS LINGUAGENS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, 'popularidade_linguagem.csv'), mode='w', newline='', encoding='utf-8') as csv_file:
    # colunas do arquivo
    colunas = ['Repositorio', 'Criado Em', 'Estrelas', 'Linguagem Primaria', 'Linguagens']
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    writer.writeheader()
    
    for repo in lista_resp:
        writer.writerow(repo)

# confirmando a criação do arquivo
print("Arquivo CSV 'popularidade_linguagem.csv' criado com sucesso!")

# Gerarndo arquivo CSV: LISTA DE RANKING POPULARES E SUAS LINGUAGENS
with open(os.path.join(BASE_DIR, 'ranking_popularidade.csv'), mode='w', newline='', encoding='utf-8') as csv_file:
    #colunas do arquivo
    colunas = ['Linguagens', 'Quantidade de Repositorios']
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    writer.writeheader()
    
    for lingua, contagem in contador_linguagens.most_common():
        writer.writerow({
            'Linguagens': lingua, 
            'Quantidade de Repositorios': contagem
        })

# confirmando a criação do arquivo
print("Arquivo CSV 'ranking_popularidade.csv' criado com sucesso!")
