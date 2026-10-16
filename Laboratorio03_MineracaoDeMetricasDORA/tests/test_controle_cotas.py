"""Cotas e interrupções com respostas artificiais, sem acesso à rede."""

from datetime import datetime, timezone
from email.utils import format_datetime
import threading
import time

import pytest
import requests

from controle_cotas import ControleCotas, InterrompidaColeta


@pytest.fixture(autouse=True)
def rede_proibida(monkeypatch):
    def falhar(*args, **kwargs):
        raise AssertionError("Este teste não pode acessar a rede.")
    monkeypatch.setattr(requests.Session, "send", falhar)


def resposta(status=200, headers=None, texto=""):
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    response._content = texto.encode("utf-8")
    return response


class Relogio:
    def __init__(self):
        self.utc, self.monotono = 1000.0, 500.0
        self.esperas = []

    def avancar(self, segundos):
        self.utc += segundos
        self.monotono += segundos

    def esperar(self, timeout):
        self.esperas.append(timeout)
        assert 0 < timeout <= 0.1
        self.avancar(timeout)


@pytest.fixture
def relogio(monkeypatch):
    clock = Relogio()
    monkeypatch.setattr("controle_cotas.time.time", lambda: clock.utc)
    monkeypatch.setattr("controle_cotas.time.monotonic", lambda: clock.monotono)
    return clock


def controle_simulado(monkeypatch, relogio, *, intervalo=0, margem=5):
    controle = ControleCotas(threading.Event(), intervalo_minimo=intervalo, margem=margem)
    monkeypatch.setattr(controle._condicao, "wait", relogio.esperar)
    return controle


def atraso(controle, relogio, conta="usuario-a", url="/repos/fixture/projeto"):
    inicio = relogio.monotono
    assert controle.aguardar(conta, url) is None
    return relogio.monotono - inicio


def test_intervalo_e_global_entre_contas_e_recursos(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio, intervalo=0.1)
    assert atraso(controle, relogio) == 0
    assert atraso(controle, relogio, "usuario-b", "/search/repositories") == pytest.approx(0.1)
    assert atraso(controle, relogio, "usuario-a", "/repos/fixture/outro") == pytest.approx(0.1)


@pytest.mark.parametrize("status", [200, 403, 429])
def test_primaria_esgotada_pausa_so_conta_e_recurso(monkeypatch, relogio, status):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(status, {
        "x-RATELIMIT-Remaining": "0", "X-RateLimit-Reset": "1010", "X-RateLimit-Resource": "core",
    }, "API rate limit exceeded"))
    assert atraso(controle, relogio, "usuario-b") == 0
    assert atraso(controle, relogio, "usuario-a", "/search/repositories?q=fixture") == 0
    assert atraso(controle, relogio) == pytest.approx(15)


def test_search_esgotada_nao_bloqueia_core(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "https://api.github.com/search/repositories", resposta(headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1003", "X-RateLimit-Resource": "search",
    }))
    assert atraso(controle, relogio) == 0
    assert atraso(controle, relogio, "usuario-a", "/search/code") == pytest.approx(8)


def test_recurso_reportado_e_usado_nas_proximas_chamadas(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/rota/de/recurso?q=1", resposta(headers={
        "x-ratelimit-resource": "search", "x-ratelimit-remaining": "0", "x-ratelimit-reset": "1002",
    }))
    assert atraso(controle, relogio) == 0
    assert atraso(controle, relogio, url="/rota/de/recurso?q=2") == pytest.approx(7)


def test_saldos_fora_de_ordem_nao_liberam_nem_encurtam_pausa(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1100",
    }))
    relogio.avancar(1)
    controle.registrar("usuario-a", "/repos/fixture/outro", resposta(headers={
        "X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999",
    }))
    controle.registrar("usuario-a", "/repos/fixture/terceiro", resposta(headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1020",
    }))
    assert atraso(controle, relogio) == pytest.approx(104)


@pytest.mark.parametrize("headers,esperado", [
    ({"Retry-After": "7"}, 12),
    ({"Retry-After": format_datetime(datetime.fromtimestamp(1007, tz=timezone.utc), usegmt=True)}, 12),
    ({}, 65),
    ({"Retry-After": "inválido"}, 65),
    ({"Retry-After": "-1"}, 65),
    ({"Retry-After": "NaN", "X-RateLimit-Reset": "inf"}, 65),
])
@pytest.mark.parametrize("status", [403, 429])
def test_secundaria_pausa_todas_contas_e_recursos(monkeypatch, relogio, headers, esperado, status):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/search/repositories", resposta(status, headers, "secondary rate limit"))
    assert atraso(controle, relogio, "usuario-b") == pytest.approx(esperado)


def test_secundaria_com_saldo_positivo_ainda_e_global(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(403, {
        "X-RateLimit-Remaining": "4000", "Retry-After": "8",
    }, "Please wait"))
    assert atraso(controle, relogio, "usuario-b", "/search/repositories") == pytest.approx(13)


def test_429_sem_headers_nem_mensagem_usa_espera_conservadora(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(429))
    assert atraso(controle, relogio, "usuario-b") == pytest.approx(65)


def test_secundaria_esgotada_respeita_maior_prazo_servidor(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(429, {
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1012", "Retry-After": "7",
    }, "secondary rate limit"))
    assert atraso(controle, relogio, "usuario-b") == pytest.approx(17)


def test_reincidencias_secundarias_dobram_sem_sucesso_antigo_zerar(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio, margem=0)
    for esperado in (60, 120, 240):
        controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(429))
        controle.registrar("usuario-b", "/repos/fixture/outro", resposta(headers={
            "X-RateLimit-Remaining": "5000", "X-RateLimit-Reset": "2000",
        }))
        assert atraso(controle, relogio, "usuario-b") == pytest.approx(esperado)


def test_espera_secundaria_nunca_encurta_header_superior_a_uma_hora(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(429, {"Retry-After": "4000"}))
    assert atraso(controle, relogio, "usuario-b") == pytest.approx(4005)


def test_retry_after_zero_reincidente_tambem_adquire_backoff(monkeypatch, relogio):
    controle = controle_simulado(monkeypatch, relogio)
    for esperado in (5, 65, 125):
        controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(429, {"Retry-After": "0"}))
        assert atraso(controle, relogio, "usuario-b") == pytest.approx(esperado)


@pytest.mark.parametrize("headers", [{}, {"X-RateLimit-Reset": "inválido"}])
def test_saldo_zero_sem_reset_validado_nao_autoriza_imediatamente(monkeypatch, relogio, headers):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(headers={
        **headers, "X-RateLimit-Remaining": "0",
    }))
    assert atraso(controle, relogio) == pytest.approx(65)


@pytest.mark.parametrize("status", [200, 401, 403, 404, 500])
def test_resposta_sem_evidencia_de_cota_nao_cria_pausa(monkeypatch, relogio, status):
    controle = controle_simulado(monkeypatch, relogio)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(status, texto="Resource not accessible"))
    assert atraso(controle, relogio) == 0


def test_cancelamento_previo_independe_de_quota_e_nao_expoe_identidade():
    evento = threading.Event()
    evento.set()
    controle = ControleCotas(evento)
    with pytest.raises(InterrompidaColeta) as erro:
        controle.aguardar("segredo-na-identidade", "https://api.github.com/repos/segredo-na-url")
    assert "segredo" not in str(erro.value)


def test_cancelamento_durante_espera_longa_acorda_worker(monkeypatch):
    evento, esperando = threading.Event(), threading.Event()
    controle = ControleCotas(evento)
    controle.registrar("usuario-a", "/repos/fixture/projeto", resposta(headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(time.time() + 3600),
    }))
    esperar = controle._condicao.wait
    erros = []

    def sinalizar_espera(timeout):
        esperando.set()
        return esperar(timeout)

    def executar():
        try:
            controle.aguardar("usuario-a", "/repos/fixture/projeto")
        except BaseException as exc:
            erros.append(exc)

    monkeypatch.setattr(controle._condicao, "wait", sinalizar_espera)
    worker = threading.Thread(target=executar, daemon=True)
    worker.start()
    assert esperando.wait(timeout=1)
    evento.set()
    worker.join(timeout=0.5)
    assert not worker.is_alive()
    assert len(erros) == 1 and isinstance(erros[0], InterrompidaColeta)


def test_workers_recebem_autorizacoes_espacadas_globalmente():
    controle = ControleCotas(threading.Event())
    barreira = threading.Barrier(4)
    autorizacoes = []

    def executar(indice):
        barreira.wait(timeout=1)
        controle.aguardar(f"usuario-{indice}", "/repos/fixture/projeto")
        autorizacoes.append(time.monotonic())

    workers = [threading.Thread(target=executar, args=(i,), daemon=True) for i in range(3)]
    for worker in workers:
        worker.start()
    barreira.wait(timeout=1)
    for worker in workers:
        worker.join(timeout=2)
    assert all(not worker.is_alive() for worker in workers)
    assert len(autorizacoes) == 3
    ordenadas = sorted(autorizacoes)
    assert all(b - a >= 0.08 for a, b in zip(ordenadas, ordenadas[1:]))


@pytest.mark.parametrize("kwargs", [
    {"intervalo_minimo": -1}, {"intervalo_minimo": True}, {"intervalo_minimo": float("nan")},
    {"intervalo_minimo": float("inf")}, {"margem": -1}, {"margem": False}, {"margem": "inválida"},
])
def test_configuracao_invalida_falha_sem_aguardar(kwargs):
    with pytest.raises(ValueError):
        ControleCotas(threading.Event(), **kwargs)


def test_evento_sem_is_set_falha_claramente():
    with pytest.raises(ValueError, match="evento de parada"):
        ControleCotas(None)
