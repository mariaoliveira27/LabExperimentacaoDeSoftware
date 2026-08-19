import requests
import csv

# Credencias e Endpoints 
TOKEN = ""  # Token de acceso personal de GitHub
URL = "https://api.github.com/graphql"              # Endpoint de la API GraphQL de GitHub

# Header (corrigido o nome da variável para 'headers')
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Consulta GraphQL com paginação
query = """
query ($cursor: String) {
    search(query: "stars:>5000 sort:stars-desc", type: REPOSITORY, first: 20, after: $cursor) {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            ... on Repository {
                nameWithOwner
                createdAt
                stargazerCount
                pullRequests(states: MERGED) {
                    totalCount
                }
            }
        }
    }
}
"""

# lista para armazenar os dados do csv
lista_resp = []

# variáveis de paginação
cursor = None     # página inicial
TOTAL_REQ = 1000   # quantidade total de repositórios desejados

# Loop para paginar as requisições
while len(lista_resp) < TOTAL_REQ:
    # Dicionário de dados para a requisição
    payload = {
        "query": query,
        "variables": {"cursor": cursor}
    }

    # Requisição POST para a API GraphQL do GitHub
    response = requests.post(URL, json=payload, headers=headers)

    # Tratamento de resposta
    if response.status_code == 200:
        data = response.json()
        
        if 'errors' in data:
            print("ERRO: A API retornou algum erro nesta página.")
            print(data['errors'])
        
        search_data = data.get('data', {}).get('search', {})
        repositories = search_data.get('nodes', [])
        page_info = search_data.get('pageInfo', {})
        
        for repo in repositories:
            if repo is None:
                continue # Pula repositórios inválidos
            
            name_with_owner = repo['nameWithOwner']
            created_at = repo['createdAt']
            stargazer_count = repo['stargazerCount']
            
            # Utilizando .get() para evitar erros caso 'pullRequests' não venha na resposta
            prs_aceitas = repo.get('pullRequests', {}).get('totalCount', 0)
            
            # adicionando os dados à lista
            lista_resp.append({
                'Repositorio': name_with_owner,
                'Criado Em': created_at,
                'Estrelas': stargazer_count,
                'Pull Requests Aceitas': prs_aceitas
            })
            
            # exibição no terminal
            print(f"[{len(lista_resp)}/{TOTAL_REQ}] Repository: {name_with_owner} | PRs Aceitas: {prs_aceitas}")
            
            # interrompe o for quando atingir o total de requisições desejadas
            if len(lista_resp) >= TOTAL_REQ:
                break
        
        # verifica se existe uma próxima página para buscar
        if page_info.get('hasNextPage') and len(lista_resp) < TOTAL_REQ:
            cursor = page_info.get('endCursor') # Atualiza o cursor para a próxima requisição
        else:
            break # sai do while se não houver mais páginas
            
    # erro de requisição   
    else:
        print(f"Erro na requisição: {response.status_code}")
        print(response.text)
        break

print("-" * 40)
print(f"Total de repositórios processados: {len(lista_resp)}")

# Gerando arquivo CSV
with open('pull_requests_aceitas.csv', mode='w', newline='', encoding='utf-8') as csv_file:
    # colunas do arquivo
    colunas = ['Repositorio', 'Criado Em', 'Estrelas', 'Pull Requests Aceitas']
    
    # criando o objeto writer
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    
    # escreve as colunas no arquivo
    writer.writeheader()
    
    # escreve os dados no arquivo
    for repo in lista_resp:
        writer.writerow(repo)

# confirmando a criação do arquivo
print("Arquivo CSV 'pull_requests_aceitas.csv' criado com sucesso!")