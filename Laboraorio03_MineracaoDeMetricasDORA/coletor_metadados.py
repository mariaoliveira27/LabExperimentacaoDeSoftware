"""
Módulo de seleção de repositórios candidatos e coleta de metadados.
Responsável por:
- Buscar repositórios populares na API do GitHub (stars > 1000)
- Fatiar buscas por linguagem ou faixa de estrelas quando necessário
- Coletar metadados obrigatórios:
  * Estrelas (stargazers_count)
  * Linguagem principal (language)
  * Idade do repositório em dias e anos (a partir de created_at)
  * Contagem de contribuidores (via GET /contributors?per_page=1&anon=true e Link header)
  * Default branch
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from api_client import GitHubClient

logger = logging.getLogger("ColetorMetadados")


class ColetorMetadados:
    def __init__(self, client: GitHubClient):
        self.client = client

    def buscar_candidatos(
        self,
        min_stars: int = 1000,
        max_candidatos: int = 200,
        linguagens: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca repositórios com mais de min_stars estrelas.
        Se linguagens forem informadas, divide a busca para diversificar a amostra.
        """
        candidatos: List[Dict[str, Any]] = []
        repos_vistos = set()

        queries = []
        if linguagens:
            for lang in linguagens:
                queries.append(f"stars:>{min_stars} language:{lang}")
        else:
            # Fatias padrão por faixas de estrelas e linguagens populares
            queries = [
                f"stars:>50000",
                f"stars:20000..50000",
                f"stars:10000..20000",
                f"stars:5000..10000",
                f"stars:1000..5000",
            ]

        for q in queries:
            if len(candidatos) >= max_candidatos:
                break

            logger.info(f"Buscando repositórios candidatos com query: '{q}'...")
            page = 1
            while page <= 10 and len(candidatos) < max_candidatos:
                endpoint = "/search/repositories"
                params = {
                    "q": q,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page,
                }
                status, data, _ = self.client.request(endpoint, params=params)
                if status != 200 or not isinstance(data, dict):
                    break

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    full_name = item.get("full_name")
                    if full_name and full_name not in repos_vistos:
                        repos_vistos.add(full_name)
                        candidatos.append(item)
                        if len(candidatos) >= max_candidatos:
                            break

                page += 1

        logger.info(f"Total de {len(candidatos)} repositórios candidatos encontrados na busca inicial.")
        return candidatos

    def extrair_metadados_repositorio(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai e enriquece os metadados do repositório:
        - Estrelas
        - Linguagem
        - Idade (em dias e anos)
        - Contribuidores (usando otimização do Link header)
        - Default branch
        """
        full_name = repo_data.get("full_name", "")
        owner = repo_data.get("owner", {}).get("login", "")
        repo_name = repo_data.get("name", "")

        created_at_str = repo_data.get("created_at")
        idade_dias = None
        idade_anos = None
        if created_at_str:
            created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            agora = datetime.now(timezone.utc)
            delta = agora - created_dt
            idade_dias = max(0, delta.days)
            idade_anos = round(idade_dias / 365.25, 2)

        # Coleta de contribuidores
        contributors_count = 0
        if owner and repo_name:
            contributors_count = self.client.get_contributors_count(owner, repo_name)

        return {
            "id": repo_data.get("id"),
            "full_name": full_name,
            "owner": owner,
            "name": repo_name,
            "html_url": repo_data.get("html_url"),
            "stars": repo_data.get("stargazers_count", 0),
            "language": repo_data.get("language") or "Outra",
            "default_branch": repo_data.get("default_branch", "main"),
            "created_at": created_at_str,
            "idade_dias": idade_dias,
            "idade_anos": idade_anos,
            "contributors_count": contributors_count,
            "forks_count": repo_data.get("forks_count", 0),
            "open_issues_count": repo_data.get("open_issues_count", 0),
        }
