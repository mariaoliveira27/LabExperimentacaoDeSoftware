"""Credenciais artificiais de fixture, sem chamadas à rede."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest
import requests

import coleta_amostra_real as coleta
from controle_cotas import ControleCotas, InterrompidaColeta


@pytest.fixture
def criar(tmp_path, monkeypatch):
    monkeypatch.setattr(coleta, "ControleCotas", lambda evento, **kwargs: ControleCotas(evento, intervalo_minimo=0, **kwargs))
    saida = tmp_path / "coleta"
    saida.mkdir()

    def executar(workers=4, nomes=(), gh=False):
        return coleta._criar_clientes({}, saida, saida / "cache.db", workers, nomes, gh, threading.Event())

    return executar, saida


def test_quatro_workers_usam_sessoes_distintas_e_mesma_cota_gh(criar, monkeypatch):
    executar, saida = criar
    monkeypatch.setattr(coleta, "token_gh", lambda: "credencial-ficticia-gh")
    clientes = executar(gh=True)
    try:
        assert len({id(c.session) for c in clientes}) == 4
        assert len({id(c.controle_cotas) for c in clientes}) == 1
        assert {c.conta_cota for c in clientes} == {"conta-unica"}
        assert all(c.session.headers["Authorization"] == "Bearer credencial-ficticia-gh" for c in clientes)
        assert not (saida / "requisicoes.jsonl").exists()
    finally:
        for client in clientes:
            client.session.close()


@pytest.mark.parametrize("mesma_conta", [False, True])
def test_multiplos_tokens_validam_user_sem_cache_e_nao_gravam_segredos(criar, monkeypatch, mesma_conta):
    executar, saida = criar
    tokens = ("token-fixture-alfa", "token-fixture-beta")
    for nome, valor in zip(("TOKEN_FIXTURE_A", "TOKEN_FIXTURE_B"), tokens):
        monkeypatch.setenv(nome, valor)
    chamadas = []

    def get(session, url, **kwargs):
        assert url == "https://api.github.com/user"
        chamadas.append(session.headers["Authorization"])
        indice = tokens.index(session.headers["Authorization"].removeprefix("Bearer "))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"id": 10 if mesma_conta else 10 + indice, "login": "perfil-privado-fixture"}).encode()
        response.headers.update({"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"})
        return response

    monkeypatch.setattr(requests.Session, "get", get)
    # Uma identidade em cache não pode ser reutilizada para validar outro token.
    base = coleta.ClienteAuditavel(saida / "ignorado.jsonl", token=tokens[0], cache_db_path=str(saida / "cache.db"))
    base._save_to_cache("https://api.github.com/user", "https://api.github.com/user", 200, {"id": 999}, {})
    base.session.close()
    if mesma_conta:
        with pytest.raises(ValueError, match="mesma conta"):
            executar(nomes=["TOKEN_FIXTURE_A", "TOKEN_FIXTURE_B"])
    else:
        clientes = executar(nomes=["TOKEN_FIXTURE_A", "TOKEN_FIXTURE_B"])
        try:
            assert [c.conta_cota for c in clientes] == [10, 11, 10, 11]
            assert len({id(c.session) for c in clientes}) == 4
        finally:
            for client in clientes:
                client.session.close()
    assert chamadas == [f"Bearer {valor}" for valor in tokens]
    journal = (saida / "requisicoes.jsonl").read_text(encoding="utf-8")
    assert all(valor not in journal for valor in (*tokens, "perfil-privado-fixture"))
    rows = [json.loads(linha) for linha in journal.splitlines()]
    assert len(rows) == 2 and all(row["origem"] == "http" for row in rows)


@pytest.mark.parametrize("nomes,valores,mensagem", [
    (["TOKEN_A", "TOKEN_B"], ("repetido", "repetido"), "repetidas"),
    (["TOKEN_A"], ("",), "vazia"),
    (["NOME INVALIDO"], ("fixture",), "somente nomes"),
])
def test_credenciais_invalidas_recusadas_antes_de_http(criar, monkeypatch, nomes, valores, mensagem):
    executar, _ = criar
    for nome, valor in zip(nomes, valores):
        monkeypatch.setenv(nome, valor)
    monkeypatch.setattr(requests.Session, "get", lambda *a, **k: pytest.fail("HTTP não deveria ser chamado"))
    with pytest.raises(ValueError, match=mensagem):
        executar(nomes=nomes)


@pytest.mark.parametrize("kwargs", [
    {"workers": 0}, {"workers": 9}, {"workers": True},
    {"workers": 2, "token_envs": ["A", "B", "C"]},
    {"workers": 4, "token_envs": ["A"], "usar_gh_auth": True},
    {"token_envs": "A"}, {"workers": 2, "client": object()},
])
def test_opcoes_invalidas_nao_alteram_saida(tmp_path, kwargs):
    destino = tmp_path / "saida"
    with pytest.raises(ValueError):
        coleta.coletar(saida=destino, **kwargs)
    assert not destino.exists()


def test_espera_de_retry_pode_ser_cancelada_e_cache_hit_nao_usa_cota(tmp_path):
    evento = threading.Event()
    client = coleta.ClienteAuditavel(tmp_path / "auditoria.jsonl", token="fixture", cache_db_path=str(tmp_path / "cache.db"))
    client.evento_parada = evento
    client.controle_cotas = type("SemHTTP", (), {"aguardar": lambda *args: pytest.fail("Cache não consome cota")})()
    client._save_to_cache("https://api.github.com/cache", "https://api.github.com/cache", 200, [], {})
    assert client.request("/cache")[1] == []
    assert client.last_response_info["origem"] == "cache"
    evento.set()
    with pytest.raises(InterrompidaColeta):
        client._aguardar(3600)
    with pytest.raises(InterrompidaColeta):
        client.request("/cache")
    assert client.last_response_info["origem"] == "http"
    client.session.close()


def test_sessoes_concorrentes_persistem_cache_e_journal_sem_misturar_origem(tmp_path, monkeypatch):
    barreira = threading.Barrier(4)
    chamadas = []

    def get(session, url, **kwargs):
        chamadas.append(url)
        barreira.wait(timeout=5)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"origem": "fixture_offline", "url": url}).encode()
        return response

    monkeypatch.setattr(requests.Session, "get", get)
    journal, banco = tmp_path / "auditoria.jsonl", tmp_path / "cache.db"
    clientes = [coleta.ClienteAuditavel(journal, token=f"segredo-fixture-{i}", cache_db_path=str(banco)) for i in range(4)]

    def executar(indice):
        client = clientes[indice]
        for pagina in range(4):
            endpoint = f"/fixture/worker-{indice}/pagina-{pagina}"
            assert client.request(endpoint)[0] == 200
            assert client.last_response_info["origem"] == "http"
            assert client.request(endpoint)[0] == 200
            assert client.last_response_info["origem"] == "cache"

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(executar, range(4)))
        assert len(chamadas) == 16
        rows = [json.loads(linha) for linha in journal.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 32
        for url in chamadas:
            endpoint = url.removeprefix("https://api.github.com")
            par = [row for row in rows if row["endpoint"] == endpoint]
            assert [row["origem"] for row in par] == ["http", "cache"]
            assert par[0]["resposta_sha256"] == par[1]["resposta_sha256"]
            assert par[0]["cache_timestamp"] is None and par[1]["cache_timestamp"] is not None
        with sqlite3.connect(banco) as conn:
            assert conn.execute("SELECT COUNT(*) FROM api_cache WHERE state='complete'").fetchone()[0] == 16
        assert b"segredo-fixture-" not in journal.read_bytes()
        assert b"segredo-fixture-" not in banco.read_bytes()
    finally:
        for client in clientes:
            client.session.close()
