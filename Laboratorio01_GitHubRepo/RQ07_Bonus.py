import requests
import csv
import os
import time
from datetime import datetime, timezone
from collections import defaultdict

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
    search(query: "stars:>5000 sort:stars-desc", type: REPOSITORY, first: 10, after: $cursor) {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            ... on Repository {
                nameWithOwner
                createdAt
                stargazerCount
                pushedAt
                pullRequests(states: MERGED) {
                    totalCount
                }
                releases {
                    totalCount
                }
                languages(first: 1, orderBy: {field: SIZE, direction: DESC}) {
                    nodes {
                        name
                    }
                }
                issues (first:10, orderBy: {field: CREATED_AT, direction: DESC}) {
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

# hoje
hoje_utc = datetime.now(timezone.utc)

# dicionário para agrupar repositórios por linguagem
agrupamento_linguagem = defaultdict(lambda: {
    'quantidade_repos': 0,         # quantidade de repositórios
    'soma_prs': 0,                 # soma de pull requests
    'soma_releases': 0,            # soma de releases
    'soma_dias_atualizacoes': 0,   # soma de dias desde a última atualização
    'soma_taxa_issues': 0          # soma da taxa de issues
})  
    
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
    for tentativa in range(3):
        response = requests.post(URL, json=payload, headers=hearders)
        if response.status_code != 502:
            break
        print(f"Erro 502 na página; tentativa {tentativa + 1}/3...")
        time.sleep(2)

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
            stargazer_count = repo['stargazerCount']
            
            # Linguagem primaria e lista de linguagens
            languages_nodes = repo.get('languages', {}).get('nodes', [])
            nomes_linguagens = [lang['name'] for lang in languages_nodes if lang is not None and 'name' in lang]  # extrai apenas os nomes das linguagens
            linguagem_primaria = nomes_linguagens[0] if nomes_linguagens else "Sem linguagem"
            string_linguagens = ", ".join(nomes_linguagens) if nomes_linguagens else "Sem linguagem"
            
            # Pull Requests e Releases
            total_prs = repo.get('pullRequests', {}).get('totalCount', 0)
            total_releases = repo.get('releases', {}).get('totalCount', 0)
            
            # Frequencia de atualização
            data_push = repo.get('pushedAt')
            dias_desde_atualizacao = 0
            if data_push:
                data_push_dt = datetime.fromisoformat(data_push.replace('Z', '+00:00'))
                dias_desde_atualizacao = (hoje_utc - data_push_dt).days

            # Frequencia de issues
            issues_nodes = repo.get('issues', {}).get('nodes', [])
            issues_validas = [issue for issue in issues_nodes if issue is not None and 'createdAt' in issue]
            taxa_mensal_issues = 0
            
            if len(issues_validas) > 1:
                datas = [datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')) for issue in issues_validas]
                dif = datas[0] - datas[-1]
                if dif.days > 0:
                    taxa_mensal_issues = (len(datas) / dif.days) * 30
            
            # adiciona os dados à lista
            lista_resp.append({
                'Repositorio': name_with_owner,
                'Estrelas': stargazer_count,
                'Linguagem Primaria': linguagem_primaria,
                'Pull Requests': total_prs,
                'Releases': total_releases,
                'Dias desde Atualização': dias_desde_atualizacao,
                'Taxa mensal de Issues': round(taxa_mensal_issues, 2)
            })
            
            agrupamento_linguagem[linguagem_primaria]['quantidade_repos'] += 1
            agrupamento_linguagem[linguagem_primaria]['soma_prs'] += total_prs
            agrupamento_linguagem[linguagem_primaria]['soma_releases'] += total_releases
            agrupamento_linguagem[linguagem_primaria]['soma_dias_atualizacoes'] += dias_desde_atualizacao
            agrupamento_linguagem[linguagem_primaria]['soma_taxa_issues'] += taxa_mensal_issues
            
            # exibe no terminal
            if len(lista_resp) % 100 == 0 or len(lista_resp) == TOTAL_REQ:
                print(f"[{len(lista_resp)}/{TOTAL_REQ}] Repositórios processados")
            
            # interrompe quando atingir o total de requisições
            if len(lista_resp) >= TOTAL_REQ:
                break
        
        # verifica se existe uma próxima página para buscar
        if page_info.get('hasNextPage') and len(lista_resp) < TOTAL_REQ:
            cursor = page_info.get('endCursor') # Atualiza o cursor para a próxima requisição
            time.sleep(0.1)  # Pequena pausa entre páginas
        else:
            break
    
    else:
        print(f"Erro na requisição: {response.status_code}")
        print(response.text)
        raise SystemExit(1)
    
print(f"Total de repositórios processados: {len(lista_resp)}")
        
# Gerarndo arquivo CSV: LISTA DE REPOSITÓRIOS POPULARES E SUAS LINGUAGENS
CAMINHO_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bonus.csv')
with open(CAMINHO_CSV, mode='w', newline='', encoding='utf-8') as csv_file:
    # colunas do arquivo
    colunas = ['Linguagem', 'Total de Repositorios', 'Media PRs', 'Media Releases', 'Media Dias Sem Atualizar', 'Media Frequencia Issues']
    writer = csv.DictWriter(csv_file, fieldnames=colunas)
    writer.writeheader()
    
    linguagens_ordenadas = sorted(agrupamento_linguagem.items(), key=lambda item: item[1]['quantidade_repos'], reverse=True)    
    
    for lingua, dados in linguagens_ordenadas:
        # quantidade de repositórios
        qtd = dados['quantidade_repos']
        
        # medias
        media_prs = dados['soma_prs'] / qtd
        media_releases = dados['soma_releases'] / qtd
        media_dias = dados['soma_dias_atualizacoes'] / qtd
        media_issues = dados['soma_taxa_issues'] / qtd
        
        # escreve no CSV
        writer.writerow({
            'Linguagem': lingua,
            'Total de Repositorios': qtd,
            'Media PRs': int(media_prs),
            'Media Releases': int(media_releases),
            'Media Dias Sem Atualizar': int(media_dias),
            'Media Frequencia Issues': round(media_issues, 2)
        })

# confirmando a criação do arquivo
print("Arquivo CSV 'bonus.csv' criado com sucesso!")
