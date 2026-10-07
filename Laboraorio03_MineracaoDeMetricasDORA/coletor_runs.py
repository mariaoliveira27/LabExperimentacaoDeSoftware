"""
Módulo de coleta de workflow runs de GitHub Actions.
Atende às regras operacionais:
- Apenas execuções do default branch com event = 'push'
- Subdivisão mensal da janela para evitar o teto de 1.000 resultados da API do GitHub
- Classificação estrita de conclusion (success, failure/timed_out/startup_failure)
- Ignora cancelled, skipped, neutral, etc.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from api_client import GitHubClient
from metricas.calculo_metricas import parse_datetime

logger = logging.getLogger("ColetorRuns")


class ColetorRuns:
    def __init__(self, client: GitHubClient):
        self.client = client

    def tem_github_actions(self, owner: str, repo: str) -> bool:
        """
        Verifica se o repositório usa GitHub Actions via /actions/workflows.
        Se total_count == 0, descarta antes de gastar chamadas desnecessárias.
        """
        endpoint = f"/repos/{owner}/{repo}/actions/workflows"
        status, data, _ = self.client.request(endpoint)
        if status == 200 and isinstance(data, dict):
            return data.get("total_count", 0) > 0
        return False

    def coletar_runs_janela(
        self,
        owner: str,
        repo: str,
        default_branch: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Coleta workflow runs na janela, subdividindo mês a mês para respeitar limites da API.
        Filtra por branch padrão, event = push e conclusões válidas.
        """
        runs_coletados: List[Dict[str, Any]] = []
        ids_vistos = set()

        conclusoes_validas = {
            "success",
            "failure",
            "timed_out",
            "startup_failure",
        }

        # Gera intervalos mensais dentro da janela
        intervalos = []
        cur_inicio = window_start
        while cur_inicio < window_end:
            # Avança aproximadamente 30 dias ou até window_end
            cur_fim = min(cur_inicio + timedelta(days=30), window_end)
            intervalos.append((cur_inicio, cur_fim))
            cur_inicio = cur_fim + timedelta(seconds=1)

        endpoint = f"/repos/{owner}/{repo}/actions/runs"

        for sub_inicio, sub_fim in intervalos:
            data_filtro = f"{sub_inicio.strftime('%Y-%m-%d')}..{sub_fim.strftime('%Y-%m-%d')}"
            params = {
                "branch": default_branch,
                "event": "push",
                "created": data_filtro,
                "per_page": 100,
            }

            page = 1
            while page <= 10:  # Máximo de 1.000 resultados por consulta mensal
                params["page"] = page
                status, data, _ = self.client.request(endpoint, params=params)

                if status != 200 or not isinstance(data, dict):
                    break

                items = data.get("workflow_runs", [])
                if not items:
                    break

                for r in items:
                    run_id = r.get("id")
                    if run_id in ids_vistos:
                        continue

                    conc = (r.get("conclusion") or "").strip().lower()
                    if conc not in conclusoes_validas:
                        continue

                    # Verifica branch e event caso a API tenha retornado broader
                    branch = r.get("head_branch")
                    event = r.get("event")
                    if branch != default_branch or event != "push":
                        continue

                    created_str = r.get("created_at")
                    created_dt = parse_datetime(created_str) if created_str else None
                    if not created_dt or not (window_start <= created_dt <= window_end):
                        continue

                    ids_vistos.add(run_id)
                    runs_coletados.append({
                        "id": run_id,
                        "workflow_id": r.get("workflow_id"),
                        "name": r.get("name"),
                        "conclusion": conc,
                        "created_at": created_str,
                        "run_started_at": r.get("run_started_at") or created_str,
                        "updated_at": r.get("updated_at") or created_str,
                    })

                total_count = data.get("total_count", 0)
                if len(items) < 100 or page * 100 >= total_count:
                    break

                page += 1

        # Ordena cronologicamente
        runs_coletados.sort(key=lambda r: parse_datetime(r["created_at"]))
        return runs_coletados
