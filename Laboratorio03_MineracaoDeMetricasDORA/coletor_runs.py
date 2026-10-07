"""Coleta completa e retomável de workflow runs do default branch, por push.

As consultas usam intervalos inclusivos em segundos UTC. Meses de calendário
são subdivididos quando atingem o teto de 1.000 resultados da API. Cada página
fica no cache do GitHubClient; repetir a coleta reutiliza páginas já recebidas.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from api_client import GitHubClient

logger = logging.getLogger("ColetorRuns")
SECOND = timedelta(seconds=1)
VALID_CONCLUSIONS = {"success", "failure", "timed_out", "startup_failure"}
RUN_FIELDS = (
    "id", "workflow_id", "name", "head_branch", "event", "conclusion",
    "created_at", "run_started_at", "updated_at",
)


class ColetaIncompletaError(RuntimeError):
    """A coleta não pode ser consumida como completa; execute novamente para retomar."""


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp ausente ou não textual")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp deve conter fuso horário")
    return parsed.astimezone(timezone.utc)


def _utc(value):
    # Configurações antigas sem offset são interpretadas explicitamente como UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ColetorRuns:
    def __init__(self, client: GitHubClient):
        self.client = client

    def _falhar(self, endpoint, params, message, invalidate=False):
        if invalidate:
            self.client.invalidate_cache(endpoint, params)
        context = f"{endpoint}, parâmetros={params}: {message}"
        logger.error("Coleta incompleta: %s", context)
        raise ColetaIncompletaError(context)

    def _intervalo_inconsistente(self, endpoint, params, message):
        # Quando os dados mudam entre páginas, a primeira página em cache também
        # pode conter uma contagem antiga. Todas as páginas desse intervalo devem
        # voltar a pending para que a retomada obtenha uma visão consistente.
        for page in range(1, params["page"] + 1):
            self.client.invalidate_cache(endpoint, {**params, "page": page})
        self._falhar(endpoint, params, message)

    def _request(self, endpoint, params=None):
        try:
            status, data, headers = self.client.request(endpoint, params=params)
        except Exception as exc:
            self._falhar(endpoint, params, f"requisição falhou: {exc}")
        if status != 200:
            self._falhar(endpoint, params, f"HTTP {status}")
        if (
            not isinstance(data, dict)
            or type(data.get("total_count")) is not int
            or data["total_count"] < 0
            or data.get("incomplete_results", False)
        ):
            self._falhar(endpoint, params, "resposta inválida/incompleta", invalidate=True)
        return data, headers

    def tem_github_actions(self, owner: str, repo: str) -> bool:
        """Um erro de API nunca equivale à ausência de GitHub Actions."""
        endpoint = f"/repos/{owner}/{repo}/actions/workflows"
        data, _ = self._request(endpoint)
        return data["total_count"] > 0

    @staticmethod
    def _intervalos_mensais(start, end):
        while start <= end:
            next_month = datetime(
                start.year + (start.month == 12), start.month % 12 + 1, 1,
                tzinfo=timezone.utc,
            )
            interval_end = min(next_month - SECOND, end)
            yield start, interval_end
            start = interval_end + SECOND

    def _pagina(self, endpoint, params):
        data, headers = self._request(endpoint, params)
        if not isinstance(data.get("workflow_runs"), list) or len(data["workflow_runs"]) > 100:
            self._falhar(endpoint, params, "workflow_runs inválido", invalidate=True)
        return data["total_count"], data["workflow_runs"], headers

    def _normalizar_run(self, run, endpoint, params):
        try:
            if not isinstance(run, dict):
                raise ValueError("run não é objeto")
            for field in ("id", "workflow_id"):
                if type(run.get(field)) is not int or run[field] <= 0:
                    raise ValueError(f"{field} deve ser inteiro positivo")
            if "head_branch" not in run or (
                run["head_branch"] is not None and not isinstance(run["head_branch"], str)
            ):
                raise ValueError("head_branch ausente/inválido")
            if not isinstance(run.get("event"), str) or not run["event"]:
                raise ValueError("event ausente/inválido")
            conclusion = run.get("conclusion")
            if conclusion is not None and not isinstance(conclusion, str):
                raise ValueError("conclusion inválida")
            conclusion = (conclusion or "").strip().lower()
            created = _timestamp(run.get("created_at"))
            dates = {}
            for field in ("run_started_at", "updated_at"):
                value = run.get(field)
                if conclusion in VALID_CONCLUSIONS or value is not None:
                    dates[field] = _timestamp(value)
            if len(dates) == 2 and dates["updated_at"] < dates["run_started_at"]:
                raise ValueError("updated_at anterior a run_started_at")
        except (ValueError, TypeError, OverflowError) as exc:
            self._falhar(endpoint, params, f"run inválido: {exc}", invalidate=True)
        normalized = {field: run.get(field) for field in RUN_FIELDS}
        normalized["conclusion"] = conclusion
        return normalized, created

    def _coletar_intervalo(self, endpoint, branch, start, end, consultadas):
        inicio_consultas = len(consultadas)
        params = {
            "branch": branch, "event": "push", "per_page": 100, "page": 1,
            "created": f"{start:%Y-%m-%dT%H:%M:%SZ}..{end:%Y-%m-%dT%H:%M:%SZ}",
        }
        consultadas.append(params)
        expected, items, headers = self._pagina(endpoint, params)
        if expected >= 1000:
            if start == end:
                self._falhar(
                    endpoint, params,
                    "teto de 1.000 resultados em um único segundo; API não permite garantir completude",
                )
            seconds = int((end - start).total_seconds())
            middle = start + timedelta(seconds=seconds // 2)
            logger.info("Subdividindo %s (%s runs)", params["created"], expected)
            result = (
                self._coletar_intervalo(endpoint, branch, start, middle, consultadas)
                + self._coletar_intervalo(endpoint, branch, middle + SECOND, end, consultadas)
            )
            quantidade = len({run["id"] for run in result})
            # Um total exatamente no teto pode estar limitado pela própria API.
            # Totais abaixo do pai, ou divergentes acima do teto, são inconsistentes.
            if quantidade < expected or (expected > 1000 and quantidade != expected):
                for consulta in consultadas[inicio_consultas:]:
                    self.client.invalidate_cache(endpoint, consulta)
                self._falhar(endpoint, params, "total_count diverge dos intervalos subdivididos")
            return result

        # Contamos IDs da resposta, inclusive os descartados pelos filtros locais,
        # para verificar total_count sem confundi-lo com a amostra selecionada.
        seen = {}
        selected = []
        while True:
            previous_count = len(seen)
            for item in items:
                run, created = self._normalizar_run(item, endpoint, params)
                run_id = run["id"]
                if run_id in seen:
                    if seen[run_id] != run:
                        self._intervalo_inconsistente(endpoint, params, "ID repetido com conteúdo divergente")
                    continue
                seen[run_id] = run
                if run["head_branch"] == branch and run["event"] == "push" and start <= created <= end:
                    selected.append(run)

            if len(seen) > expected:
                self._intervalo_inconsistente(endpoint, params, "mais IDs que total_count")
            link = headers.get("Link", headers.get("link", ""))
            next_url = GitHubClient._extract_next_url(link)
            if next_url:
                pages = parse_qs(urlparse(next_url).query).get("page", [])
                if pages != [str(params["page"] + 1)]:
                    self._falhar(endpoint, params, "Link de paginação não sequencial", invalidate=True)
            elif len(seen) == expected:
                logger.info("Intervalo completo %s: %s IDs, %s selecionados", params["created"], len(seen), len(selected))
                return selected
            elif link:
                self._intervalo_inconsistente(endpoint, params, "paginação terminou antes de total_count")

            if len(seen) == previous_count:
                self._intervalo_inconsistente(endpoint, params, "página vazia/repetida antes de completar coleta")
            params = {**params, "page": params["page"] + 1}
            consultadas.append(params)
            actual, items, headers = self._pagina(endpoint, params)
            if actual != expected:
                self._intervalo_inconsistente(endpoint, params, "total_count mudou durante paginação")

    def coletar_runs_janela(
        self, owner: str, repo: str, default_branch: str,
        window_start: datetime, window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Retorna somente coleta completa; falhas preservam páginas no cache.

        A janela é inclusiva. Precisão inferior a segundo é ajustada para dentro
        da janela, pois os timestamps de criação da API têm precisão de segundos.
        Conclusões ignoradas são preservadas para contabilização nas métricas.
        """
        if not default_branch:
            raise ValueError("default_branch deve ser informado")
        start, end = _utc(window_start), _utc(window_end)
        if start > end:
            raise ValueError("window_start deve ser anterior ou igual a window_end")
        if start.microsecond:
            start = start.replace(microsecond=0) + SECOND
        end = end.replace(microsecond=0)
        endpoint = f"/repos/{owner}/{repo}/actions/runs"
        all_runs = {}
        consultadas = []
        logger.info("Coletando %s/%s, branch=%s, %s até %s", owner, repo, default_branch, start, end)
        for sub_start, sub_end in self._intervalos_mensais(start, end):
            for run in self._coletar_intervalo(endpoint, default_branch, sub_start, sub_end, consultadas):
                if run["id"] in all_runs and all_runs[run["id"]] != run:
                    for consulta in consultadas:
                        self.client.invalidate_cache(endpoint, consulta)
                    self._falhar(endpoint, None, "ID divergente entre intervalos")
                all_runs[run["id"]] = run
        result = sorted(all_runs.values(), key=lambda run: (_timestamp(run["created_at"]), run["id"]))
        logger.info("Coleta completa %s/%s: %s workflow runs", owner, repo, len(result))
        return result
