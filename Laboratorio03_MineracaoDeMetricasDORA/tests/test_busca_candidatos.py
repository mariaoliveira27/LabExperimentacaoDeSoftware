"""Busca paginada e particionada com respostas REST sintéticas, sem rede."""

from copy import deepcopy
from datetime import date
import re

import pytest

from busca_candidatos import buscar_candidatos


def repositorio(identificador, *, stars=1000, created="2020-01-01T00:00:00Z"):
    return {
        "id": identificador, "full_name": f"fixture/repo{identificador:05d}",
        "name": f"repo{identificador:05d}", "owner": {"login": "fixture"},
        "stargazers_count": stars, "created_at": created, "private": False,
        "html_url": f"https://github.com/fixture/repo{identificador:05d}",
        "default_branch": "main", "language": "Python",
    }


class BuscaFake:
    """Executa os filtros das queries contra uma população controlada."""

    def __init__(self, items, mutar=None):
        self.items = items
        self.mutar = mutar
        self.chamadas = []
        self.invalidadas = []

    def request(self, endpoint, params):
        assert endpoint == "/search/repositories"
        assert "is:public" in params["q"]
        assert "fork:" not in params["q"] and "archived:" not in params["q"]
        assert params["per_page"] <= 100
        assert 1 <= params["page"] <= 10
        assert params["sort"] == "stars"  # sort=created não existe neste endpoint.
        self.chamadas.append(deepcopy(params))
        stars = re.search(r"stars:(?:>=(\d+)|(\d+)\.\.(\d+))", params["q"])
        minimo = int(stars[1] or stars[2])
        maximo = None if stars[1] else int(stars[3])
        created = re.search(r"created:(?:<=(\d{4}-\d{2}-\d{2})|(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2}))", params["q"])
        inicio = None if created[1] else date.fromisoformat(created[2])
        fim = date.fromisoformat(created[1] or created[3])
        items = [item for item in self.items if (
            item["stargazers_count"] >= minimo
            and (maximo is None or item["stargazers_count"] <= maximo)
            and date.fromisoformat(item["created_at"][:10]) <= fim
            and (inicio is None or date.fromisoformat(item["created_at"][:10]) >= inicio)
            and item.get("private") is False
        )]
        chave = "stargazers_count" if params["sort"] == "stars" else "created_at"
        items = sorted(items, key=lambda item: item[chave], reverse=params["order"] == "desc")
        limite = params["per_page"]
        offset = (params["page"] - 1) * limite
        payload = {"total_count": len(items), "incomplete_results": False, "items": deepcopy(items[offset:offset + limite])}
        if self.mutar:
            resposta = self.mutar(params, payload)
            if resposta is not None:
                return resposta
        return 200, payload, {}

    def invalidate_cache(self, endpoint, params):
        assert endpoint == "/search/repositories"
        self.invalidadas.append(deepcopy(params))


@pytest.fixture
def populacao():
    return [repositorio(i + 1, stars=1000 + i) for i in range(250)]


def test_paginacao_completa_250_e_ordem_deterministica(populacao):
    client = BuscaFake(populacao)
    resultado = buscar_candidatos(client, max_candidatos=None)
    assert [row["id"] for row in resultado] == list(range(250, 0, -1))
    assert [params["page"] for params in client.chamadas] == [1, 2, 3]
    assert resultado.relatorio["busca_completa"] is True
    assert resultado.relatorio["limitado_por_max_candidatos"] is False
    assert resultado.relatorio["candidatos_retornados"] == 250


def test_ordenacao_empates_nome_casefold_id():
    items = [repositorio(i) for i in (4, 2, 3, 1)]
    items[0]["full_name"] = "Fixture/zebra"
    items[1]["full_name"] = "fixture/Alfa"
    items[2]["full_name"] = "fixture/beta"
    items[3]["full_name"] = "fixture/gama"
    primeira = buscar_candidatos(BuscaFake(items), max_candidatos=None)
    segunda = buscar_candidatos(BuscaFake(list(reversed(items))), max_candidatos=None)
    assert primeira == segunda
    assert [item["id"] for item in primeira] == [2, 3, 1, 4]


@pytest.mark.parametrize("quantidade", [1000, 1002])
def test_faixas_estrelas_sem_overlap_e_teto_estrito(quantidade):
    items = [repositorio(i + 1, stars=1000 + (i >= quantidade // 2)) for i in range(quantidade)]
    client = BuscaFake(items)
    resultado = buscar_candidatos(client, max_candidatos=None)
    assert len(resultado) == quantidade
    assert len({item["id"] for item in resultado}) == quantidade
    queries = {params["q"] for params in client.chamadas}
    assert "stars:1000..1000 created:<=2024-09-30 is:public" in queries
    assert "stars:1001..1001 created:<=2024-09-30 is:public" in queries
    assert all(params["page"] <= 6 for params in client.chamadas)
    assert resultado.relatorio["total_count_raiz"] == quantidade
    assert resultado.relatorio["busca_completa"] is True


def test_999_resultados_sao_paginados_sem_particionar():
    client = BuscaFake([repositorio(i + 1) for i in range(999)])
    resultado = buscar_candidatos(client, max_candidatos=None)
    assert len(resultado) == 999
    assert len({params["q"] for params in client.chamadas}) == 1
    assert len(client.chamadas) == 10


def test_estrela_unica_particiona_data_real_sem_limite_inventado():
    items = [repositorio(i + 1, created="2007-10-29T00:00:00Z" if i < 501 else "2024-09-30T23:59:59Z") for i in range(1002)]
    client = BuscaFake(items)
    resultado = buscar_candidatos(client, max_candidatos=None)
    assert len(resultado) == 1002
    assert any("created:<=2007-10-28" in params["q"] for params in client.chamadas)
    assert any("created:2007-10-29.." in params["q"] for params in client.chamadas)
    assert resultado.relatorio["busca_completa"] is True


def test_menor_data_e_encontrada_mesmo_fora_dos_primeiros_100():
    # As estrelas iguais permitem que a ordem da API exiba só os novos na
    # página inicial; a sondagem anterior ainda deve preservar os mais antigos.
    items = [repositorio(i + 1, created="2024-09-30T00:00:00Z" if i < 501 else "2007-10-29T00:00:00Z") for i in range(1002)]
    client = BuscaFake(items)
    resultado = buscar_candidatos(client, max_candidatos=None)
    assert len(resultado) == 1002
    assert any("created:<=2024-09-29" in params["q"] for params in client.chamadas)
    assert any("created:<=2007-10-28" in params["q"] for params in client.chamadas)


def test_um_dia_saturado_nao_e_truncado_como_completo():
    client = BuscaFake([repositorio(i + 1, created="2024-09-30T00:00:00Z") for i in range(1001)])
    with pytest.raises(ValueError, match="Faixa inseparável.*teto de 1.000"):
        buscar_candidatos(client)
    assert len(client.chamadas) == 2


def test_filtros_incluem_extremos_estrelas_data_e_publico():
    items = [
        repositorio(1, stars=1000, created="2024-09-30T23:59:59Z"),
        repositorio(2, stars=999),
        repositorio(3, created="2024-10-01T00:00:00Z"),
        {**repositorio(4), "private": True},
    ]
    resultado = buscar_candidatos(BuscaFake(items))
    assert [item["id"] for item in resultado] == [1]


@pytest.mark.parametrize("limite", [1, 100, 249])
def test_limite_explicito_nao_declara_populacao_exaurida(populacao, limite):
    resultado = buscar_candidatos(BuscaFake(populacao), max_candidatos=limite)
    assert len(resultado) == limite
    assert resultado.relatorio["limitado_por_max_candidatos"] is True
    assert resultado.relatorio["busca_completa"] is False
    assert resultado.relatorio["total_count_raiz"] == 250
    assert resultado.relatorio["candidatos_coletados"] == 250
    assert resultado.relatorio["max_candidatos"] == limite


def test_quota_interrompe_particoes_sem_alegar_busca_completa():
    items = [repositorio(i + 1, stars=1000 + (i >= 501)) for i in range(1002)]
    client = BuscaFake(items)
    resultado = buscar_candidatos(client, max_candidatos=100)
    assert len(resultado) == 100
    assert all(item["stargazers_count"] == 1001 for item in resultado)
    assert resultado.relatorio["busca_completa"] is False
    assert resultado.relatorio["candidatos_coletados"] == 501
    assert not any("stars:1000..1000" in params["q"] and params["page"] > 1 for params in client.chamadas)


def test_limite_igual_populacao_e_busca_completa(populacao):
    resultado = buscar_candidatos(BuscaFake(populacao), max_candidatos=250)
    assert resultado.relatorio["busca_completa"] is True


def test_populacao_vazia_e_exaustao_real():
    resultado = buscar_candidatos(BuscaFake([]))
    assert resultado == []
    assert resultado.relatorio["busca_completa"] is True
    assert resultado.relatorio["total_count_raiz"] == 0


@pytest.mark.parametrize("status", [403, 422, 429, 500])
def test_erros_http_nao_sao_exaustao(status, populacao):
    client = BuscaFake(populacao, lambda params, payload: (status, {"message": "erro"}, {}))
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        buscar_candidatos(client)
    assert client.invalidadas


def test_rate_limit_esgotado_no_cliente_propaga(populacao):
    def falhar(params, payload):
        raise RuntimeError("Rate limit após retentativas")
    client = BuscaFake(populacao, falhar)
    with pytest.raises(RuntimeError, match="Rate limit"):
        buscar_candidatos(client)
    assert client.invalidadas


@pytest.mark.parametrize("erro", ["incomplete", "incomplete_ausente", "total_bool", "total_ausente", "items_ausente", "pagina_vazia", "pagina_parcial", "id", "nome", "stars", "created", "private"])
def test_respostas_invalidas_falham_e_invalidam_cache(populacao, erro):
    def mutar(params, payload):
        if erro == "incomplete":
            payload["incomplete_results"] = True
        elif erro == "incomplete_ausente":
            payload.pop("incomplete_results")
        elif erro == "total_bool":
            payload["total_count"] = True
        elif erro == "total_ausente":
            payload.pop("total_count")
        elif erro == "items_ausente":
            payload.pop("items")
        elif erro == "pagina_vazia":
            payload["items"] = []
        elif erro == "pagina_parcial":
            payload["items"].pop()
        elif erro == "id":
            payload["items"][0]["id"] = True
        elif erro == "nome":
            payload["items"][0]["full_name"] = "nome sem dono"
        elif erro == "stars":
            payload["items"][0]["stargazers_count"] = 999
        elif erro == "created":
            payload["items"][0]["created_at"] = "2020-01-01T00:00:00"
        else:
            payload["items"][0]["private"] = True
    client = BuscaFake(populacao, mutar)
    with pytest.raises(ValueError):
        buscar_candidatos(client)
    assert client.invalidadas


def test_total_count_inconsistente_entre_paginas(populacao):
    def mutar(params, payload):
        if params["page"] == 2:
            payload["total_count"] += 1
    client = BuscaFake(populacao, mutar)
    with pytest.raises(ValueError, match="total_count mudou"):
        buscar_candidatos(client)
    assert client.invalidadas[-1]["page"] == 2


def test_total_count_das_particoes_deve_somar_raiz():
    items = [repositorio(i + 1, stars=1000 + (i >= 501)) for i in range(1002)]
    def mutar(params, payload):
        if "stars:1000..1000" in params["q"]:
            payload["total_count"] -= 1
    with pytest.raises(ValueError, match="não soma a população"):
        buscar_candidatos(BuscaFake(items, mutar))


@pytest.mark.parametrize("tipo", ["id", "nome"])
def test_duplicatas_entre_paginas_sao_rejeitadas(populacao, tipo):
    primeiro = max(populacao, key=lambda item: item["stargazers_count"])
    def mutar(params, payload):
        if params["page"] == 2:
            payload["items"][0]["id" if tipo == "id" else "full_name"] = (
                primeiro["id"] if tipo == "id" else primeiro["full_name"].upper()
            )
    client = BuscaFake(populacao, mutar)
    with pytest.raises(ValueError, match="duplicados entre páginas"):
        buscar_candidatos(client)
    assert client.invalidadas


def test_duplicatas_na_mesma_pagina_sao_rejeitadas():
    item = repositorio(1)
    with pytest.raises(ValueError, match="duplicados na página"):
        buscar_candidatos(BuscaFake([item, deepcopy(item)]))


@pytest.mark.parametrize("kwargs", [
    {"min_stars": -1}, {"min_stars": True}, {"max_candidatos": 0},
    {"max_candidatos": False}, {"criado_ate": "30/09/2024"}, {"criado_ate": None},
])
def test_argumentos_invalidos_nao_consultam_api(kwargs):
    client = BuscaFake([])
    with pytest.raises(ValueError):
        buscar_candidatos(client, **kwargs)
    assert client.chamadas == []
