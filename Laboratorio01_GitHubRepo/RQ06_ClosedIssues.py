import requests
import csv
import os

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
                totalIssues: issues {
                    totalCount
                }
                closedIssues: issues(states: CLOSED) {
                    totalCount
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
            
            # Extrai os issues (se não existir, o padrão será 0)
            total_issues = repo.get('totalIssues', {}).get('totalCount', 0)
            closed_issues = repo.get('closedIssues', {}).get('totalCount', 0)
            
            # calcula a percentual de issues fechadas
            if total_issues > 0:
                percentual_fechadas = (closed_issues / total_issues) * 100
                percentual_fechadas = f"{percentual_fechadas:.2f}"
            else:
                percentual_fechadas = "N/A (sem issues)"
            
            # adiciona os dados à lista
            lista_resp.append({
                'Repositorio': name_with_owner,
                'Criado Em': created_at,
                'Estrelas': stargazer_count,
                'Total de Issues': total_issues,
                'Issues Fechadas': closed_issues,
                'Percentual de Issues Fechadas': percentual_fechadas
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
        
# Gerarndo arquivo CSV: PERCENTUAL DE ISSUES FECHADAS
CAMINHO_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'percentual_issues_fechadas.csv')
with open(CAMINHO_CSV, mode='w', newline='', encoding='utf-8') as csv_file:
    # colunas do arquivo
    colunas = ['Repositorio', 'Criado Em', 'Estrelas', 'Total de Issues', 'Issues Fechadas', 'Percentual de Issues Fechadas']
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    writer.writeheader()
    
    for repo in lista_resp:
        writer.writerow(repo)

# confirmando a criação do arquivo
print("Arquivo CSV 'percentual_issues_fechadas.csv' criado com sucesso!")
