import requests
import csv

# Credencias e Endpoints 
TOKEN = ""  # Token de acceso personal de GitHub
URL = "https://api.github.com/graphql"              # Endpoint de la API GraphQL de GitHub

# Header
hearders = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


# Consulta GraphQL
query = """
query {
    search(query: "stars:>5000 sort:stars-desc", type: REPOSITORY, first: 100) {
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

# Dicionário de dados para a requisição
payload = {
    "query": query
}

# Requisição POST para a API GraphQL do GitHub
response = requests.post(URL, json=payload, headers=hearders)

# Tratamento de resposta
if response.status_code == 200:
    data = response.json()
    print(data)
    repositories = data['data']['search']['nodes']
    
    # lista csv
    lista_resp = []
    
    for repo in repositories:
        name_with_owner = repo['nameWithOwner']
        created_at = repo['createdAt']
        stargazer_count = repo['stargazerCount']
        prs_aceitas = repo['pullRequests']['totalCount']
        # exibição no terminal
        print(f"Repository: {name_with_owner}")
        print(f"Created At: {created_at}")
        print(f"Stars: {stargazer_count}")
        print(f"Pull Requests Aceitas: {prs_aceitas}")
        print("-" * 40)
        
        # adicionando os dados à lista
        lista_resp.append({
            'Repositorio': name_with_owner,
            'Criado Em': created_at,
            'Estrelas': stargazer_count,
            'Pull Requests Aceitas': prs_aceitas
        })
    
    # Gerarndo arquivo CSV
    with open ('pull_requests_aceitas.csv', mode='w', newline='', encoding='utf-8') as csv_file:
        #colunas do arquivo
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

# erro de requisição   
else:
    print(f"Error: {response.status_code}")
    print(response.text)