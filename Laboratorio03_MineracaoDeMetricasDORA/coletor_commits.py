"""
Módulo de coleta de commits entre releases (para cálculo de Lead Time).
Atende às regras operacionais:
- Utiliza endpoint compare: GET /repos/{owner}/{repo}/compare/{base}...{head}
- Se base não existir (primeira release da história), ignora a release no cálculo de lead time
- Se retornar 404 (tag apagada/reescrita), registra o caso e ignora a release
- Extrai commit.author.date e mensagens de commit
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from api_client import GitHubClient
from metricas.calculo_metricas import parse_datetime

logger = logging.getLogger("ColetorCommits")


class ColetorCommits:
    def __init__(self, client: GitHubClient):
        self.client = client

    def coletar_commits_entre_releases(
        self,
        owner: str,
        repo: str,
        base_tag: str,
        head_tag: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Coleta os commits entre duas releases consecutivas via compare.
        Retorna lista de dicionários de commits com author_date e message.
        Retorna None se houver erro 404 (tag apagada/reescrita).
        """
        current_url = f"/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
        current_params = {"per_page": 100}
        resultado_commits = []

        try:
            while current_url:
                status, data, headers = self.client.request(current_url, params=current_params)
                if status == 404:
                    logger.warning(f"Compare retornou 404 para {owner}/{repo}: {base_tag}...{head_tag}. Tag inexistente ou reescrita.")
                    return None
                if status != 200 or not isinstance(data, dict):
                    break

                commits_raw = data.get("commits", [])
                for c in commits_raw:
                    commit_info = c.get("commit") or {}
                    author_info = commit_info.get("author") or {}
                    date_str = author_info.get("date")
                    dt = parse_datetime(date_str) if date_str else None
                    msg = commit_info.get("message", "")

                    if dt:
                        resultado_commits.append({
                            "sha": c.get("sha"),
                            "author_date": dt,
                            "author_date_str": date_str,
                            "message": msg,
                        })

                # Verifica paginação através do cabeçalho Link (rel="next")
                link_header = headers.get("Link", headers.get("link", "")) if isinstance(headers, dict) else ""
                next_url = None
                if hasattr(self.client, "_extract_next_url"):
                    next_url = self.client._extract_next_url(link_header)

                if next_url:
                    current_url = next_url
                    current_params = None
                else:
                    break

            return resultado_commits

        except Exception as e:
            logger.warning(f"Erro ao coletar compare para {owner}/{repo}: {e}")
            return None
