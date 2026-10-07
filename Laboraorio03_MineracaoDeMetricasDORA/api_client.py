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
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
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
        verify_ssl: bool = False,
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
                    timestamp REAL
                )
            """)
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
        conn = None
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status_code, response_json, response_headers FROM api_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row:
                status_code, response_json_str, response_headers_str = row
                data = json.loads(response_json_str) if response_json_str else None
                headers = json.loads(response_headers_str) if response_headers_str else {}
                return status_code, data, headers
        except Exception as e:
            logger.debug(f"Erro ao ler cache para {cache_key}: {e}")
        finally:
            if conn:
                conn.close()
        return None

    def _save_to_cache(self, cache_key: str, url: str, status_code: int, data: Any, headers: Dict[str, str]):
        if not self.use_cache:
            return
        conn = None
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO api_cache (cache_key, url, status_code, response_json, response_headers, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    url,
                    status_code,
                    json.dumps(data) if data is not None else None,
                    json.dumps(dict(headers)),
                    time.time(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"Erro ao salvar cache para {cache_key}: {e}")
        finally:
            if conn:
                conn.close()


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

    def _handle_rate_limit(self, response: requests.Response):
        """Verifica cabeçalhos de rate limit e pausa a execução se necessário."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")

        # Tratamento de Rate Limit secundário ou Retry-After
        if response.status_code in (403, 429) and "retry-after" in response.headers:
            wait_seconds = int(response.headers["retry-after"]) + self.safety_margin_seconds
            logger.warning(f"Rate limit secundário atingido. Aguardando {wait_seconds} segundos...")
            time.sleep(wait_seconds)
            return

        if remaining is not None and int(remaining) <= 0 and reset_time is not None:
            reset_epoch = float(reset_time)
            now = time.time()
            wait_seconds = max(1.0, (reset_epoch - now) + self.safety_margin_seconds)
            logger.warning(f"Rate limit esgotado! Pausando execução por {wait_seconds:.1f}s até o reset...")
            time.sleep(wait_seconds)

    def request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: Optional[bool] = None,
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        Executa requisição GET ao GitHub com retentativas, backoff exponencial e cache.
        Retorna (status_code, data_json, headers).
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

        cache_key = self._get_cache_key(url, params)
        should_cache = self.use_cache if use_cache is None else use_cache

        if should_cache:
            cached = self._read_from_cache(cache_key)
            if cached is not None:
                return cached

        retries = 0
        backoff = self.backoff_base_seconds

        while retries <= self.max_retries:
            try:
                response = self.session.get(
                    url,
                    params=params,
                    verify=self.verify_ssl,
                    timeout=30,
                )

                self._handle_rate_limit(response)

                # Se rate limit estourou e retornou 403, refaz após sleep
                if response.status_code in (403, 429):
                    msg = response.text.lower()
                    if "rate limit" in msg or "secondary rate" in msg or "abuse" in msg:
                        retries += 1
                        time.sleep(backoff)
                        backoff *= 2
                        continue

                # Sucesso ou respostas esperadas de recurso (200, 404, etc.)
                if response.status_code < 500:
                    try:
                        data = response.json()
                    except Exception:
                        data = response.text

                    headers_dict = dict(response.headers)
                    if should_cache and response.status_code in (200, 404):
                        self._save_to_cache(cache_key, url, response.status_code, data, headers_dict)
                    return response.status_code, data, headers_dict

                # Erros de servidor (5xx) -> Backoff exponencial
                logger.warning(f"Servidor retornou status {response.status_code} para {url}. Tentativa {retries + 1}/{self.max_retries}")

            except (requests.RequestException, Exception) as e:
                logger.warning(f"Erro de conexão ({type(e).__name__}: {e}) para {url}. Tentativa {retries + 1}/{self.max_retries}")

            retries += 1
            if retries <= self.max_retries:
                time.sleep(backoff)
                backoff *= 2

        raise RuntimeError(f"Falha ao consultar GitHub API para URL {url} após {self.max_retries} tentativas.")

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

            if status_code != 200 or not isinstance(data, list):
                if isinstance(data, dict) and "items" in data:
                    all_items.extend(data["items"])
                break

            all_items.extend(data)
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
