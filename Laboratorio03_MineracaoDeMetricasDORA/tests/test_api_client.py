"""
Testes unitários para o cliente da API do GitHub (api_client.py).
Verifica:
- Inicialização do cache SQLite e persistência
- Extração de URLs rel='next' e contagem de última página do Link header
- Tratamento de parâmetros e geração de chaves de cache
"""

import os
import tempfile
from api_client import GitHubClient


def test_api_client_link_header_extraction():
    # Testa cabeçalho Link com múltiplas relações
    link_header = '<https://api.github.com/repositories/123/releases?page=2>; rel="next", <https://api.github.com/repositories/123/releases?page=5>; rel="last"'
    next_url = GitHubClient._extract_next_url(link_header)
    assert next_url == "https://api.github.com/repositories/123/releases?page=2"

    # Sem next
    assert GitHubClient._extract_next_url('<https://api.github.com/releases?page=1>; rel="prev"') is None
    assert GitHubClient._extract_next_url("") is None


def test_api_client_cache_sqlite():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        client = GitHubClient(token="mock_token", cache_db_path=db_path, use_cache=True)

        cache_key = "https://api.github.com/mock/endpoint"
        sample_data = {"key": "value", "count": 42}
        sample_headers = {"X-RateLimit-Remaining": "4999"}

        # Salva no cache
        client._save_to_cache(cache_key, cache_key, 200, sample_data, sample_headers)

        # Lê do cache
        cached = client._read_from_cache(cache_key)
        assert cached is not None
        status, data, headers = cached
        assert status == 200
        assert data["count"] == 42
        assert headers["X-RateLimit-Remaining"] == "4999"


def test_api_client_cache_key_generation():
    client = GitHubClient(token="test")
    k1 = client._get_cache_key("https://api.github.com/repos", {"b": 2, "a": 1})
    k2 = client._get_cache_key("https://api.github.com/repos", {"a": 1, "b": 2})
    # Parâmetros ordenados produzem a mesma chave
    assert k1 == k2
    assert "a=1" in k1 and "b=2" in k1
