"""Os testes do laboratório são locais: chamadas reais à rede são proibidas."""

import pytest
import requests


@pytest.fixture(autouse=True)
def bloquear_rede(monkeypatch):
    def proibida(*args, **kwargs):
        raise AssertionError("Chamada HTTP real proibida nos testes; use fixture ou mock.")

    monkeypatch.setattr(requests.sessions.Session, "request", proibida)
