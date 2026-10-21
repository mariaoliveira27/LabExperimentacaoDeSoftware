"""
Módulo de coleta de commits entre releases (para cálculo de Lead Time).
Atende às regras operacionais:
- Utiliza endpoint compare: GET /repos/{owner}/{repo}/compare/{base}...{head}
- Se base não existir (primeira release da história), ignora a release no cálculo de lead time
- Se retornar 404 (tag apagada/reescrita), registra o caso e ignora a release
- Extrai commit.author.date e mensagens de commit
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import parse_qs, quote, urlparse
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
        Retorna None se a comparação estiver indisponível ou incompleta.
        Uma lista vazia significa exclusivamente total_commits=0 comprovado.
        Não descarta commits inválidos nem devolve o prefixo de uma paginação
        interrompida: isso alteraria o Lead Time e as mensagens usadas no CFR(b).
        """
        compare_path = f"/compare/{quote(base_tag, safe='')}...{quote(head_tag, safe='')}"
        current_url = f"/repos/{owner}/{repo}{compare_path}"
        current_params = {"page": 1, "per_page": 100}
        resultado_commits = []
        shas = set()
        total = None
        pagina = 1

        try:
            while current_url:
                status, data, headers = self.client.request(current_url, params=current_params)
                if status == 404:
                    logger.warning(f"Compare retornou 404 para {owner}/{repo}: {base_tag}...{head_tag}. Tag inexistente ou reescrita.")
                    return None
                if status != 200:
                    raise ValueError(f"HTTP {status} interrompeu a comparação na página {pagina}.")
                if (not isinstance(data, dict) or type(data.get("total_commits")) is not int
                        or data["total_commits"] < 0 or not isinstance(data.get("commits"), list)):
                    raise ValueError("Resposta compare sem total_commits/commits válidos.")
                total = data["total_commits"] if total is None else total
                esperados = min(100, max(0, total - len(resultado_commits)))
                if data["total_commits"] != total or len(data["commits"]) != esperados:
                    raise ValueError("Total/quantidade de commits diverge; comparação incompleta.")

                commits_raw = data["commits"]
                for c in commits_raw:
                    sha = c.get("sha") if isinstance(c, dict) else None
                    if (not isinstance(sha, str) or len(sha) != 40
                            or any(d not in "0123456789abcdef" for d in sha) or sha in shas):
                        raise ValueError("SHA inválido ou repetido na comparação.")
                    commit_info = c.get("commit")
                    if not isinstance(commit_info, dict) or not isinstance(commit_info.get("author"), dict):
                        raise ValueError("Commit sem author original válido.")
                    author_info = commit_info["author"]
                    date_str = author_info.get("date")
                    dt = parse_datetime(date_str) if isinstance(date_str, str) else None
                    msg = commit_info.get("message")

                    if dt is None or dt.tzinfo is None or not isinstance(msg, str):
                        raise ValueError("Commit sem data de autor com fuso ou mensagem original válida.")
                    shas.add(sha)
                    resultado_commits.append({
                        "sha": sha,
                        "author_date": dt,
                        "author_date_str": date_str,
                        "message": msg,
                    })

                # Verifica paginação através do cabeçalho Link (rel="next")
                link_header = headers.get("Link", headers.get("link", "")) if isinstance(headers, dict) else ""
                next_url = GitHubClient._extract_next_url(link_header)

                if len(resultado_commits) == total:
                    if next_url:
                        raise ValueError("Link next contradiz total_commits já atingido.")
                    return resultado_commits
                if not next_url:
                    raise ValueError("Link next ausente antes de atingir total_commits.")
                seguinte = urlparse(next_url)
                origem = urlparse(getattr(self.client, "base_url", "https://api.github.com"))
                if (seguinte.scheme != origem.scheme or seguinte.netloc != origem.netloc
                        or not seguinte.path.endswith(compare_path)
                        or parse_qs(seguinte.query) != {"page": [str(pagina + 1)], "per_page": ["100"]}):
                    raise ValueError("Link next com origem, comparação ou número de página divergente.")
                current_url, current_params = next_url, None
                pagina += 1

            return None

        except Exception as e:
            if isinstance(e, ValueError) and hasattr(self.client, "invalidate_cache"):
                try:
                    self.client.invalidate_cache(current_url, current_params)
                except Exception as cache_error:
                    logger.warning("Não foi possível invalidar página incompleta do cache: %s", cache_error)
            logger.warning(f"Erro ao coletar compare para {owner}/{repo}: {e}")
            return None
