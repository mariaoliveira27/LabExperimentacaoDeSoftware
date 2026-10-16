"""Coordenação conservadora de cotas REST entre os workers da coleta.

``conta`` identifica uma cota compartilhada, e não a string de um token.
Tokens do mesmo usuário devem receber a mesma identidade do chamador. O
controle não armazena credenciais, não faz requisições e não usa respostas
com saldo positivo para desfazer uma pausa já observada.
"""

from __future__ import annotations

import math
import re
import threading
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit


class InterrompidaColeta(RuntimeError):
    """Interrupção cooperativa, sem incluir credenciais ou URLs na mensagem."""


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None
    return numero if math.isfinite(numero) else None


def _duracao_retry_after(valor, agora):
    numero = _numero(valor)
    if numero is not None:
        return numero if numero >= 0 else None
    if not isinstance(valor, str):
        return None
    try:
        data = parsedate_to_datetime(valor)
        if data.tzinfo is None:
            data = data.replace(tzinfo=timezone.utc)
        return max(0.0, data.timestamp() - agora)
    except (TypeError, ValueError, OverflowError):
        return None


class ControleCotas:
    """Pausa por conta/recurso, cooldown secundário global e ritmo global.

    ``aguardar`` concede uma autorização de GET por vez, com o intervalo
    mínimo configurado. Toda espera consulta o Event em até 100 ms. O
    chamador deve registrar também respostas HTTP com erro e usar a mesma
    instância entre os workers. Sucessos não zeram o backoff secundário:
    podem ser respostas antigas que chegaram fora de ordem.
    """

    def __init__(self, evento_parada, intervalo_minimo=0.1, margem=5):
        if not callable(getattr(evento_parada, "is_set", None)):
            raise ValueError("O evento de parada deve oferecer is_set().")
        for valor, nome in ((intervalo_minimo, "intervalo_minimo"), (margem, "margem")):
            if isinstance(valor, bool) or _numero(valor) is None or float(valor) < 0:
                raise ValueError(f"{nome} deve ser um número finito não negativo.")
        self.evento_parada = evento_parada
        self.intervalo_minimo = float(intervalo_minimo)
        self.margem = float(margem)
        self._condicao = threading.Condition()
        self._proximo_get = 0.0
        self._pausa_global = 0.0
        self._pausas = {}
        self._recursos_por_rota = {}
        self._limites_secundarios = 0

    @staticmethod
    def _rota(url):
        if not isinstance(url, str):
            raise ValueError("URL inválida para o controle de cotas.")
        try:
            return urlsplit(url).path
        except ValueError:
            raise ValueError("URL inválida para o controle de cotas.") from None

    @staticmethod
    def _validar_conta(conta):
        try:
            hash(conta)
        except TypeError:
            raise ValueError("A identidade da conta deve ser utilizável como chave.") from None

    @staticmethod
    def _recurso_padrao(rota):
        return "search" if rota.startswith("/search/") or rota == "/search" else "core"

    def aguardar(self, conta, url):
        """Aguarde uma autorização; cancelamento sempre lança erro explícito."""
        self._validar_conta(conta)
        rota = self._rota(url)
        with self._condicao:
            while True:
                if self.evento_parada.is_set():
                    raise InterrompidaColeta("Coleta interrompida; respostas completas permanecem preservadas.")
                agora = time.monotonic()
                recurso = self._recursos_por_rota.get((conta, rota), self._recurso_padrao(rota))
                prazo = max(self._proximo_get, self._pausa_global, self._pausas.get((conta, recurso), 0.0))
                if prazo <= agora:
                    self._proximo_get = agora + self.intervalo_minimo
                    return
                self._condicao.wait(timeout=min(prazo - agora, 0.1))

    def registrar(self, conta, url, response):
        """Registre headers reais sem liberar pausas por saldos fora de ordem."""
        self._validar_conta(conta)
        rota = self._rota(url)
        headers = {str(chave).lower(): valor for chave, valor in response.headers.items()}
        recurso = str(headers.get("x-ratelimit-resource", "")).strip().lower()
        if recurso not in ("core", "search"):
            recurso = self._recurso_padrao(rota)
        restante = _numero(headers.get("x-ratelimit-remaining"))
        reset = _numero(headers.get("x-ratelimit-reset"))
        agora_utc = time.time()
        agora = time.monotonic()
        retry_after = _duracao_retry_after(headers.get("retry-after"), agora_utc)
        duracao_reset = max(0.0, reset - agora_utc) if reset is not None else None
        texto = response.text.lower() if response.status_code in (403, 429) else ""
        secundaria_explicita = "secondary" in texto or "abuse" in texto
        rate_limit = (response.status_code == 429 or (response.status_code == 403 and (
            secundaria_explicita or retry_after is not None or re.search(r"rate[ -]?limit", texto)
        )))
        primaria_esgotada = restante is not None and restante <= 0
        secundaria = bool(rate_limit and (secundaria_explicita or not primaria_esgotada))

        with self._condicao:
            self._recursos_por_rota[(conta, rota)] = recurso
            if primaria_esgotada:
                # Saldo zero sem reset também não autoriza novas chamadas.
                duracao = duracao_reset if duracao_reset is not None else 60.0
                if retry_after is not None:
                    duracao = max(duracao, retry_after)
                chave = (conta, recurso)
                self._pausas[chave] = max(self._pausas.get(chave, 0.0), agora + duracao + self.margem)
            if secundaria:
                if retry_after is not None:
                    duracao = retry_after
                    if primaria_esgotada and duracao_reset is not None:
                        duracao = max(duracao, duracao_reset)
                elif primaria_esgotada and duracao_reset is not None:
                    duracao = duracao_reset
                else:
                    duracao = 60.0
                # Reincidências ampliam a espera, mas nunca encurtam o prazo
                # explicitamente pedido pelo servidor, mesmo acima de uma hora.
                if duracao == 0 and self._limites_secundarios:
                    ampliada = 60.0 * 2 ** min(self._limites_secundarios - 1, 6)
                else:
                    ampliada = duracao * 2 ** min(self._limites_secundarios, 6)
                duracao = max(duracao, min(3600.0, ampliada))
                self._limites_secundarios += 1
                self._pausa_global = max(self._pausa_global, agora + duracao + self.margem)
            self._condicao.notify_all()
