"""
Módulo de coleta de releases de repositórios do GitHub.
Atende às regras operacionais:
- Apenas releases publicadas (draft = False)
- Pré-releases excluídas da definição principal (prerelease = False)
- Filtragem dentro da janela de observação (12 meses)
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from api_client import GitHubClient
from metricas.calculo_metricas import parse_datetime

logger = logging.getLogger("ColetorReleases")


class ColetorReleases:
    def __init__(self, client: GitHubClient):
        self.client = client

    def coletar_releases_janela(
        self,
        owner: str,
        repo: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Coleta todas as releases do repositório e filtra as releases válidas na janela.
        Retorna lista ordenada cronologicamente por published_at.
        """
        endpoint = f"/repos/{owner}/{repo}/releases"
        params = {"per_page": 100}

        try:
            todas_releases = self.client.paginate(endpoint, params=params)
        except Exception as e:
            logger.warning(f"Erro ao paginar releases para {owner}/{repo}: {e}")
            return []

        releases_validas = []

        for rel in todas_releases:
            is_draft = rel.get("draft", False)
            is_prerelease = rel.get("prerelease", False)
            published_at_str = rel.get("published_at")

            if is_draft or is_prerelease or not published_at_str:
                continue

            published_dt = parse_datetime(published_at_str)
            if not published_dt:
                continue

            # Filtra estritamente dentro da janela de observação
            if window_start <= published_dt <= window_end:
                releases_validas.append({
                    "id": rel.get("id"),
                    "tag_name": rel.get("tag_name"),
                    "name": rel.get("name") or rel.get("tag_name"),
                    "published_at": published_dt,
                    "published_at_str": published_at_str,
                    "body": rel.get("body") or "",
                })

        # Ordena da mais antiga para a mais recente
        releases_validas.sort(key=lambda r: r["published_at"])
        return releases_validas
