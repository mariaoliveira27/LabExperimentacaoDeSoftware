import requests
import csv
from datetime import datetime

# Credencias e Endpoints 
TOKEN = ""  # Token de acceso personal de GitHub
URL = "https://api.github.com/graphql"              # Endpoint de la API GraphQL de GitHub

# Header
hearders = {
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
                issues(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
                    nodes {
                        createdAt
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
TOTAL_REQ = 100   # quantitade total de requisições

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
        
        search_data = data.get('data', {}).get('search', {})  # obtendo os dados da pesquisa
        repositories = search_data.get('nodes', [])           # obtendo os repositórios
        page_info = search_data.get('pageInfo', {})           # obtendo informações da páginação
        
        for repo in repositories:
            if repo is None: 
                continue # Pula repositórios
            
            name_with_owner = repo['nameWithOwner']
            created_at = repo['createdAt']
            stargazer_count = repo['stargazerCount']
            
            # extrai as issues
            issues_nodes = repo.get('issues', {}).get('nodes', [])
            frequencia_issues = "N/A"
            # Remove os nós 'None' que a API retorna quando excede o limite
            issues_validas = [issue for issue in issues_nodes if issue is not None and 'createdAt' in issue]
            
            # calcular a frequência das últimas issues
            if len(issues_validas) > 1:
                # convertendo as datas para objetos datetime
                datas = [datetime.fromisoformat(issue['createdAt'].replace("Z", "+00:00")) for issue in issues_validas]
                dif = datas[0] - datas[-1]  # diferença entre a primeira e a última issue recebidas
                
                if dif.days > 0:
                    # Freq = (Total de issues / Total de dias) * 30 dias
                    taxa_diaria = len(datas) / dif.days
                    taxa_mensal = taxa_diaria * 30
                    taxa_mensal_piso = int(taxa_mensal) # piso
                    frequencia_issues = f"{taxa_mensal_piso} issues/mês"
                else:
                    frequencia_issues = "Múltiplas issues no mesmo dia"
                    
            elif len(issues_validas) == 1:
                frequencia_issues = "Apenas 1 issue"
            else:
                frequencia_issues = "Sem issues"
            
            # adiciona os dados à lista
            lista_resp.append({
                'Repositorio': name_with_owner,
                'Criado Em': created_at,
                'Estrelas': stargazer_count,
                'Frequencia issues': frequencia_issues
            })
            
            # exibe no terminal
            print(f"[{len(lista_resp)}/{TOTAL_REQ}] Repositório: {name_with_owner} | Freq: {frequencia_issues}")
            
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
        break
    
print(f"Total de repositórios processados: {len(lista_resp)}")
        
# Gerarndo arquivo CSV
with open ('frequencia_issues.csv', mode='w', newline='', encoding='utf-8') as csv_file:
    #colunas do arquivo
    colunas = ['Repositorio', 'Criado Em', 'Estrelas', 'Frequencia issues']
    
    # criando o objeto writer
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    
    # escreve as colunas no arquivo
    writer.writeheader()
    
    # escreve os dados no arquivo
    for repo in lista_resp:
        writer.writerow(repo)

# confirmando a criação do arquivo
print("Arquivo CSV 'frequencia_issues.csv' criado com sucesso!")