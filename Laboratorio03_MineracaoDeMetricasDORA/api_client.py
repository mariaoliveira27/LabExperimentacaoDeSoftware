"""
Cliente compartilhado para a API do GitHub (REST).
Não utiliza bibliotecas de terceiros para acesso à API (como PyGithub).
Implementa:
- Autenticação via variável de ambiente GITHUB_TOKEN
- Cache local em SQLite para retomada automática sem chamadas duplicadas
- Paginação automática seguindo o cabeçalho Link (rel="next")
- Tratamento de Rate Limit com leitura de X-RateLimit-Remaining e X-RateLimit-Reset
- Retentativas com Backoff Exponencial para erros 5xx e falhas transitórias
- Extração otimizada de contagem de contribuidores a partir do cabeçalho Link
"""

import os
import re
import time
import json
import sqlite3
import logging
from contextlib import closing
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode
import requests
import urllib3

# Configuração de logger
logger = logging.getLogger("GitHubClient")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class GitHubClient:
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        cache_db_path: str = "data/cache/github_cache.db",
        use_cache: bool = True,
        verify_ssl: bool = True,
        max_retries: int = 5,
        backoff_base_seconds: float = 1.0,
        safety_margin_seconds: int = 3,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        # Também verifica se há arquivo .env simples no diretório
        if not self.token and os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_TOKEN="):
                        self.token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

        self.base_url = base_url.rstrip("/")
        self.cache_db_path = cache_db_path
        self.use_cache = use_cache
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.safety_margin_seconds = safety_margin_seconds

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "Lab03-DORA-Metrics-Mining",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info("GitHubClient inicializado com GITHUB_TOKEN autenticado.")
        else:
            logger.warning("GITHUB_TOKEN não fornecido. Limite de requisições será reduzido (60/hora).")

        if self.use_cache:
            self._init_cache_db()

    def _init_cache_db(self):
        """Inicializa banco SQLite para cache local e retomada."""
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_db_path)), exist_ok=True)
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    url TEXT,
                    status_code INTEGER,
                    response_json TEXT,
                    response_headers TEXT,
                    timestamp REAL,
                    state TEXT NOT NULL DEFAULT 'pending'
                )
            """)
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(api_cache)")}
            if "state" not in columns:
                # Legacy entries were stored without JSON/completeness validation.
                cursor.execute("ALTER TABLE api_cache ADD COLUMN state TEXT NOT NULL DEFAULT 'pending'")
            conn.commit()
        finally:
            conn.close()

    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        if params:
            sorted_params = urlencode(sorted([(k, str(v)) for k, v in params.items()]))
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}{sorted_params}"
        return url

    def _read_from_cache(self, cache_key: str) -> Optional[Tuple[int, Any, Dict[str, str]]]:
        if not self.use_cache:
            return None
        with closing(sqlite3.connect(self.cache_db_path)) as conn, conn:
            row = conn.execute(
                "SELECT status_code, response_json, response_headers FROM api_cache WHERE cache_key = ? AND state = 'complete'",
                (cache_key,),
            ).fetchone()
            if not row:
                return None
            try:
                status_code, data_json, headers_json = row
                data = json.loads(data_json)
                headers = json.loads(headers_json)
                self._validate_payload(data)
                if status_code != 200 or not isinstance(headers, dict):
                    raise ValueError("Invalid cached response")
                return status_code, data, headers
            except (TypeError, ValueError):
                conn.execute(
                    "UPDATE api_cache SET state = 'pending', response_json = NULL, response_headers = NULL WHERE cache_key = ?",
                    (cache_key,),
                )
        return None

    @staticmethod
    def _validate_payload(data: Any):
        if not isinstance(data, (dict, list)):
            raise ValueError("A API deve retornar JSON do tipo objeto ou lista.")
        if isinstance(data, dict) and data.get("incomplete_results") is True:
            raise ValueError("A API sinalizou resultados incompletos; resposta permanece pendente.")

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _mark_pending(self, cache_key: str, url: str):
        if not self.use_cache:
            return
        with closing(sqlite3.connect(self.cache_db_path)) as conn, conn:
            conn.execute(
                """INSERT OR REPLACE INTO api_cache
                   (cache_key, url, timestamp, state) VALUES (?, ?, ?, 'pending')""",
                (cache_key, url, time.time()),
            )

    def invalidate_cache(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        """Deixa pendente uma resposta que falhou na validação específica do coletor."""
        url = self._url(endpoint)
        self._mark_pending(self._get_cache_key(url, params), url)

    def _save_to_cache(self, cache_key: str, url: str, status_code: int, data: Any, headers: Dict[str, str]):
        if not self.use_cache:
            return
        self._validate_payload(data)
        if status_code != 200:
            raise ValueError("Somente respostas HTTP 200 validadas podem concluir o cache.")
        # Persist only response metadata required by consumers, never credentials.
        allowed_headers = {"link", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "retry-after", "etag", "last-modified"}
        cached_headers = {key: value for key, value in headers.items() if key.lower() in allowed_headers}
        with closing(sqlite3.connect(self.cache_db_path)) as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_cache (cache_key, url, status_code, response_json, response_headers, timestamp, state)
                VALUES (?, ?, ?, ?, ?, ?, 'complete')
                """,
                (
                    cache_key,
                    url,
                    status_code,
                    json.dumps(data),
                    json.dumps(cached_headers),
                    time.time(),
                ),
            )


    def get_rate_limit(self) -> Dict[str, Any]:
        """Consulta situação do rate limit sem consumir cota."""
        url = f"{self.base_url}/rate_limit"
        try:
            resp = self.session.get(url, verify=self.verify_ssl, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Erro ao consultar rate limit: {e}")
        return {}

    @staticmethod
    def _numeric_header(headers: Dict[str, str], name: str) -> Optional[float]:
        try:
            return float(headers[name])
        except (KeyError, TypeError, ValueError):
            return None

    def _rate_limit_delay(self, response: requests.Response) -> Optional[float]:
        headers = {key.lower(): value for key, value in response.headers.items()}
        delays = []
        if "retry-after" in headers:
            retry_after = self._numeric_header(headers, "retry-after")
            if retry_after is None:
                try:
                    retry_date = parsedate_to_datetime(headers["retry-after"])
                    if retry_date.tzinfo is None:
                        retry_date = retry_date.replace(tzinfo=timezone.utc)
                    retry_after = retry_date.timestamp() - time.time()
                except (TypeError, ValueError, OverflowError):
                    pass
            if retry_after is not None:
                delays.append(max(0.0, retry_after) + self.safety_margin_seconds)
        remaining = self._numeric_header(headers, "x-ratelimit-remaining")
        reset = self._numeric_header(headers, "x-ratelimit-reset")
        if remaining is not None and remaining <= 0 and reset is not None:
            delays.append(max(1.0, reset - time.time() + self.safety_margin_seconds))
        return max(delays) if delays else None

    def _handle_rate_limit(self, response: requests.Response):
        """Espera após persistir respostas válidas, permitindo interrupção e retomada."""
        delay = self._rate_limit_delay(response)
        if delay is not None:
            logger.warning("Rate limit atingido. Aguardando %.1f segundos...", delay)
            time.sleep(delay)

    def _is_rate_limit(self, response: requests.Response) -> bool:
        if response.status_code == 429:
            return True
        if response.status_code != 403:
            return False
        headers = {key.lower(): value for key, value in response.headers.items()}
        remaining = self._numeric_header(headers, "x-ratelimit-remaining")
        return (
            "retry-after" in headers
            or (remaining is not None and remaining <= 0)
            or any(term in response.text.lower() for term in ("rate limit", "secondary rate", "abuse"))
        )

    def request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: Optional[bool] = None,
    ) -> Tuple[int, Any, Dict[str, str]]:
        """GET com cache de respostas validadas e até max_retries novas tentativas.

        Uma página somente fica completa após o commit SQLite. Falhas de rede,
        JSON, persistência ou interrupções deixam a página pendente para retomada.
        """
        url = self._url(endpoint)
        cache_key = self._get_cache_key(url, params)
        should_cache = self.use_cache and use_cache is not False
        if should_cache:
            cached = self._read_from_cache(cache_key)
            if cached is not None:
                return cached
            self._mark_pending(cache_key, url)

        for attempt in range(self.max_retries + 1):
            backoff = min(self.backoff_base_seconds * (2 ** attempt), 60.0)
            try:
                response = self.session.get(url, params=params, verify=self.verify_ssl, timeout=30)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Falha de conexão com a API após {attempt + 1} tentativas."
                    ) from exc
                logger.warning("Falha transitória de conexão. Nova tentativa em %.1fs.", backoff)
                time.sleep(backoff)
                continue

            headers = dict(response.headers)
            if response.status_code == 200:
                # Decoding/validation/storage stay outside the network retry handler:
                # invalid JSON and SQLite errors must never appear to be success.
                data = response.json()
                self._validate_payload(data)
                if should_cache:
                    self._save_to_cache(cache_key, url, response.status_code, data, headers)
                self._handle_rate_limit(response)
                return response.status_code, data, headers

            if response.status_code >= 500 or self._is_rate_limit(response):
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"GitHub API retornou HTTP {response.status_code} após {attempt + 1} tentativas."
                    )
                delay = self._rate_limit_delay(response)
                time.sleep(backoff if delay is None else delay)
                continue

            # HTTP errors remain pending; collectors decide whether they are fatal.
            try:
                data = response.json()
            except ValueError:
                data = response.text
            return response.status_code, data, headers

        raise RuntimeError("Número de tentativas inválido.")

    def paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Percorre todas as páginas seguindo o cabeçalho Link (rel="next").
        """
        all_items: List[Dict[str, Any]] = []
        current_url: Optional[str] = endpoint
        current_params = dict(params or {})

        while current_url:
            status_code, data, headers = self.request(current_url, params=current_params)

            if status_code != 200:
                raise RuntimeError(f"Paginação incompleta: HTTP {status_code} em {current_url}.")
            items = data.get("items") if isinstance(data, dict) else data
            if not isinstance(items, list):
                self.invalidate_cache(current_url, current_params)
                raise ValueError("Paginação incompleta: resposta sem uma lista de itens.")

            all_items.extend(items)
            if max_items and len(all_items) >= max_items:
                return all_items[:max_items]

            link_header = headers.get("Link", headers.get("link", ""))
            next_url = self._extract_next_url(link_header)

            if next_url:
                current_url = next_url
                current_params = None  # URL no cabeçalho Link já embute os parâmetros necessários
            else:
                break

        return all_items

    @staticmethod
    def _extract_next_url(link_header: str) -> Optional[str]:
        """Extrai URL rel='next' do cabeçalho Link."""
        if not link_header:
            return None
        links = link_header.split(",")
        for link in links:
            parts = link.split(";")
            if len(parts) >= 2:
                url_part = parts[0].strip().lstrip("<").rstrip(">")
                rel_part = parts[1].strip()
                if 'rel="next"' in rel_part:
                    return url_part
        return None

    def get_contributors_count(self, owner: str, repo: str) -> int:
        """
        Obtém a contagem total de contribuidores com uma única chamada,
        conforme dica oficial da Seção 4 do README:
        GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true
        e leitura do número da última página no cabeçalho Link.
        """
        endpoint = f"/repos/{owner}/{repo}/contributors"
        params = {"per_page": 1, "anon": "true"}
        status_code, data, headers = self.request(endpoint, params=params)

        if status_code != 200:
            return 0

        link_header = headers.get("Link", headers.get("link", ""))
        if link_header:
            match = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel="last"', link_header)
            if match:
                return int(match.group(1))

        if isinstance(data, list):
            return len(data)

        return 0
