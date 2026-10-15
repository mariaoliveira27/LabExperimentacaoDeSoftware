"""Respostas artificiais: listas parciais nunca comprovam releases da janela."""

from unittest.mock import Mock

import pytest

from api_client import GitHubClient, PaginacaoIncompletaError
from coleta_amostra_real import _contar_releases, instante


def test_limite_422_informa_prefixo_sem_retornar_lista_parcial():
    client = GitHubClient(token="fixture", use_cache=False)
    endpoint = "https://api.github.com/repositories/1/releases?per_page=100&page=101"
    client.request = Mock(side_effect=[
        (200, [{"id": i} for i in range(7)], {"Link": f'<{endpoint}>; rel="next"'}),
        (422, {"message": "Only the first 10000 results are available."}, {}),
    ])
    with pytest.raises(PaginacaoIncompletaError) as erro:
        client.paginate("/repos/fixture/projeto/releases", {"per_page": 100})
    assert erro.value.status_code == 422
    assert erro.value.paginas_obtidas == 1 and erro.value.itens_obtidos == 7
    assert erro.value.endpoint == endpoint
    assert not hasattr(erro.value, "releases_completas")


def test_link_circular_nao_repete_paginas_indefinidamente():
    client = GitHubClient(token="fixture", use_cache=False)
    url = "https://api.github.com/repositories/1/releases?page=2"
    client.request = Mock(side_effect=[
        (200, [{"id": 1}], {"Link": f'<{url}>; rel="next"'}),
        (200, [{"id": 2}], {"Link": f'<{url}>; rel="next"'}),
    ])
    with pytest.raises(PaginacaoIncompletaError, match="ciclo no Link") as erro:
        client.paginate("/repos/fixture/projeto/releases")
    assert client.request.call_count == 2 and erro.value.itens_obtidos == 2


def test_release_antiga_na_primeira_pagina_nao_encerra_a_janela():
    def release(i, data):
        return dict(id=i, tag_name=f"v{i}", published_at=data, draft=False, prerelease=False,
                    html_url=f"https://github.com/fixture/projeto/releases/tag/v{i}")

    antigas = [release(1, "2023-01-01T00:00:00Z")]
    atuais = [release(2, "2024-01-01T00:00:00Z")]
    client = GitHubClient(token="fixture", use_cache=False)
    client.request = Mock(side_effect=[
        (200, antigas, {"Link": '<https://api.github.com/repositories/1/releases?page=2>; rel="next"'}),
        (200, atuais, {}),
    ])
    releases = client.paginate("/repos/fixture/projeto/releases")
    assert len(releases) == 2 and client.request.call_count == 2
    assert _contar_releases(releases, "fixture/projeto", instante("2023-10-01T00:00:00Z"),
                           instante("2024-09-30T23:59:59Z")) == 1


def test_retomada_preserva_paginas_completas_do_cache(tmp_path, monkeypatch):
    client = GitHubClient(token="fixture", cache_db_path=str(tmp_path / "cache.db"))
    endpoint = "/repos/fixture/projeto/releases"
    params = {"per_page": 100}
    url_100 = "https://api.github.com/repositories/1/releases?per_page=100&page=100"
    url_101 = "https://api.github.com/repositories/1/releases?per_page=100&page=101"
    primeira, ultima = [{"id": 1}], [{"id": 2}]
    chave = client._get_cache_key(client._url(endpoint), params)
    client._save_to_cache(chave, client._url(endpoint), 200, primeira, {"Link": f'<{url_100}>; rel="next"'})
    client._save_to_cache(url_100, url_100, 200, ultima, {"Link": f'<{url_101}>; rel="next"'})

    class Resposta:
        status_code = 422
        headers = {}
        text = "Only the first 10000 results are available."
        def json(self): return {"message": self.text}

    http = Mock(return_value=Resposta())
    monkeypatch.setattr(client.session, "get", http)
    with pytest.raises(PaginacaoIncompletaError) as erro:
        client.paginate(endpoint, params)
    assert erro.value.paginas_obtidas == 2 and erro.value.itens_obtidos == 2
    assert http.call_count == 1 and http.call_args.args[0] == url_101
    assert client._read_from_cache(chave)[1] == primeira
    assert client._read_from_cache(url_100)[1] == ultima
