"""Timeouts HTTP artificiais nunca viram releases parciais ou reprovação."""

import json
import sqlite3
from unittest.mock import Mock

import pytest

import coleta_amostra_real as coleta
from api_client import APIHTTPTransitorioError, GitHubClient
from test_coleta_amostra_real import APIPlanejada, preparar


NOME = "fixture/projeto-000"
ENDPOINT = f"/repos/{NOME}/releases"
URL = f"https://api.github.com{ENDPOINT}"


def _erro_504(per_page=100, pagina=1, *, endpoint=None, status=504):
    return APIHTTPTransitorioError(
        status_code=status,
        endpoint=endpoint or f"{URL}?per_page={per_page}&page={pagina}",
        tentativas=3,
    )


@pytest.mark.parametrize("falhas,esperados", [(1, [100, 25]), (2, [100, 25, 5])])
def test_timeout_reinicia_com_paginas_menores_e_preserva_diagnostico(falhas, esperados):
    releases = APIPlanejada(1).paginate(ENDPOINT)
    client = Mock()
    client.paginate.side_effect = [*[_erro_504(n) for n in esperados[:falhas]], releases]
    obtidas, diagnostico = coleta._listar_releases(client, NOME)
    assert obtidas == releases
    assert [call.args for call in client.paginate.call_args_list] == [(ENDPOINT,)] * len(esperados)
    assert [call.kwargs for call in client.paginate.call_args_list] == [
        {"params": {"per_page": tamanho}} for tamanho in esperados
    ]
    assert diagnostico["completa"] is True
    assert diagnostico["per_page_usado"] == esperados[-1]
    reinicios = diagnostico["reinicios_por_504"]
    assert len(reinicios) == falhas
    assert [item["per_page"] for item in reinicios] == esperados[:falhas]
    assert all(item["http_status"] == 504 and item["tentativas"] == 3 for item in reinicios)
    assert all(item["endpoint"].startswith(URL) for item in reinicios)


def test_sem_timeout_usa_cem_e_nao_registra_reinicio():
    releases = APIPlanejada(1).paginate(ENDPOINT)
    client = Mock()
    client.paginate.return_value = releases
    obtidas, diagnostico = coleta._listar_releases(client, NOME)
    assert obtidas == releases
    client.paginate.assert_called_once_with(ENDPOINT, params={"per_page": 100})
    assert diagnostico["completa"] is True and diagnostico["per_page_usado"] == 100
    assert diagnostico["reinicios_por_504"] == []


@pytest.mark.parametrize("erro", [
    _erro_504(status=500),
    _erro_504(status=503),
    _erro_504(status=429),
    _erro_504(endpoint="https://api.github.com/repos/fixture/projeto-000/actions/runs"),
    ValueError("Schema inválido exclusivamente da fixture"),
    RuntimeError("HTTP 504 em mensagem sem tipo estruturado"),
    KeyboardInterrupt(),
])
def test_erros_diferentes_nao_acionam_reducao_de_pagina(erro):
    client = Mock()
    client.paginate.side_effect = erro
    with pytest.raises(type(erro)) as falha:
        coleta._listar_releases(client, NOME)
    assert falha.value is erro
    client.paginate.assert_called_once_with(ENDPOINT, params={"per_page": 100})


def test_tres_timeouts_interrompem_sem_snapshot_falso_e_retomam_mesma_unidade(preparar):
    config, destino, api = preparar(APIPlanejada(3))
    normal = api.paginate
    chamadas_falhas = []

    def falhar(endpoint, params=None):
        if "projeto-001" in endpoint:
            chamadas_falhas.append(params["per_page"])
            raise _erro_504(params["per_page"], endpoint="https://api.github.com" + endpoint)
        return normal(endpoint, params)

    api.paginate = falhar
    with pytest.raises(APIHTTPTransitorioError) as erro:
        coleta.coletar(config, destino, client=api)
    assert erro.value.status_code == 504
    assert chamadas_falhas == [100, 25, 5]
    estado = json.loads((destino / "estado.json").read_text(encoding="utf-8"))
    assert estado["status"] == "interrompida"
    assert estado["n_processados"] == estado["n_aprovados"] == 1
    assert set(estado["snapshots"]) == {"1.json"}
    anterior = (destino / "qualificacoes/1.json").read_bytes()
    assert not (destino / "qualificacoes/2.json").exists()
    assert not (destino / "proveniencia.json").exists()
    assert "projeto-001" not in (destino / "descartes.csv").read_text(encoding="utf-8")

    api.paginate = normal
    api.chamadas.clear()
    final = coleta.coletar(config, destino, client=api)
    assert final["status"] == "insuficiente"
    assert final["n_processados"] == final["n_aprovados"] == 3
    assert (destino / "qualificacoes/1.json").read_bytes() == anterior
    assert not any("projeto-000" in endpoint for endpoint, _ in api.chamadas)
    assert set(final["snapshots"]) == {"1.json", "2.json", "3.json"}


def test_qualificacao_guarda_reinicio_e_cinco_releases_completas(preparar):
    config, destino, api = preparar(APIPlanejada(1))
    normal = api.paginate

    def falhar_primeiro(endpoint, params=None):
        if params["per_page"] == 100:
            raise _erro_504()
        return normal(endpoint, params)

    api.paginate = falhar_primeiro
    estado = coleta.coletar(config, destino, client=api)
    assert estado["n_processados"] == estado["n_aprovados"] == 1
    snapshot = json.loads((destino / "qualificacoes/1.json").read_text(encoding="utf-8"))
    assert snapshot["aprovado"] is True and snapshot["motivo"] == ""
    assert snapshot["total_releases_janela"] == len(snapshot["releases"]) == 5
    assert snapshot["paginacao_releases"]["completa"] is True
    assert snapshot["paginacao_releases"]["per_page_usado"] == 25
    assert len(snapshot["paginacao_releases"]["reinicios_por_504"]) == 1


def _resposta(status, dados, link=None):
    resposta = Mock()
    resposta.status_code, resposta.text = status, json.dumps(dados)
    resposta.headers = {"Link": link} if link else {}
    resposta.json.return_value = dados
    return resposta


def test_prefixo_cem_nao_contamina_paginas_vinte_cinco_nem_cache(tmp_path, monkeypatch):
    releases = APIPlanejada(1).paginate(ENDPOINT)
    antiga = {**releases[0], "id": 2000, "tag_name": "v-antiga", "published_at": "2023-01-01T00:00:00Z"}
    futura = {**releases[0], "id": 2001, "tag_name": "v-futura", "published_at": "2025-01-01T00:00:00Z"}
    pagina_100 = "https://api.github.com/repositories/1/releases?per_page=100&page=2"
    pagina_25 = "https://api.github.com/repositories/1/releases?per_page=25&page=2"
    client = GitHubClient(token="fixture-sem-credencial-real", cache_db_path=str(tmp_path / "cache.db"), max_retries=0)
    http = Mock(side_effect=[
        _resposta(200, releases[:1], f'<{pagina_100}>; rel="next"'),
        _resposta(504, {"message": "Gateway Timeout exclusivamente da fixture"}),
        _resposta(200, [antiga, *releases[:2]], f'<{pagina_25}>; rel="next"'),
        _resposta(200, [*releases[2:], futura]),
    ])
    monkeypatch.setattr(client.session, "get", http)
    try:
        obtidas, diagnostico = coleta._listar_releases(client, NOME)
        assert [item["id"] for item in obtidas] == [2000, *[r["id"] for r in releases], 2001]
        assert len({item["id"] for item in obtidas}) == len(obtidas) == 7
        assert coleta._contar_releases(
            obtidas, NOME, coleta.instante("2023-10-01T00:00:00Z"),
            coleta.instante("2024-09-30T23:59:59Z"),
        ) == 5
        assert [(call.args[0], call.kwargs["params"]) for call in http.call_args_list] == [
            (URL, {"per_page": 100}), (pagina_100, None),
            (URL, {"per_page": 25}), (pagina_25, None),
        ]
        assert diagnostico["per_page_usado"] == 25 and diagnostico["completa"] is True
        with sqlite3.connect(client.cache_db_path) as banco:
            registros = {row[0]: row[1] for row in banco.execute("SELECT cache_key, state FROM api_cache")}
        assert registros[client._get_cache_key(URL, {"per_page": 100})] == "complete"
        assert registros[client._get_cache_key(URL, {"per_page": 25})] == "complete"
        assert registros[pagina_100] == "pending"
        assert registros[pagina_25] == "complete"

        # A mesma falha é repetida, mas as duas listagens mantêm seus caches.
        http.reset_mock(side_effect=True)
        http.side_effect = [_resposta(504, {"message": "Gateway Timeout da fixture"})]
        retomadas, _ = coleta._listar_releases(client, NOME)
        assert retomadas == obtidas
        assert http.call_count == 1
        assert http.call_args.args[0] == pagina_100
    finally:
        client.session.close()


@pytest.mark.parametrize("status", [500, 503, 504])
def test_http_esgotado_preserva_status_endpoint_tentativas_e_auditoria(tmp_path, monkeypatch, status):
    auditoria = tmp_path / "requisicoes.jsonl"
    client = coleta.ClienteAuditavel(
        auditoria, token="fixture-sem-credencial-real", use_cache=False, max_retries=1,
    )
    http = Mock(return_value=_resposta(status, {"message": "Falha exclusivamente da fixture"}))
    monkeypatch.setattr(client.session, "get", http)
    monkeypatch.setattr(client, "_aguardar", lambda segundos: None)
    try:
        with pytest.raises(APIHTTPTransitorioError) as erro:
            client.request(ENDPOINT, {"per_page": 100})
        assert erro.value.status_code == status
        assert erro.value.endpoint == URL
        assert erro.value.tentativas == 2
        assert http.call_count == 2
        registros = [json.loads(linha) for linha in auditoria.read_text(encoding="utf-8").splitlines()]
        assert len(registros) == 1
        assert registros[0]["http_status"] == status
        assert registros[0]["erro"] == "APIHTTPTransitorioError"
        assert client.last_response_info["http_status"] == status
    finally:
        client.session.close()
