"""Entrada de terminal com prazo, inclusive no Windows e em stdin redirecionado."""

import queue
import threading
import time


def ler_ate(mensagem: str, deadline: float) -> str:
    respostas = queue.Queue()

    def ler():
        try:
            respostas.put((True, input(mensagem)))
        except (EOFError, KeyboardInterrupt) as exc:
            respostas.put((False, exc))

    threading.Thread(target=ler, daemon=True).start()
    try:
        ok, resposta = respostas.get(timeout=max(0, deadline - time.monotonic()))
    except queue.Empty:
        raise TimeoutError("Timebox atingido aguardando entrada") from None
    if time.monotonic() >= deadline:
        raise TimeoutError("Timebox atingido")
    if not ok:
        raise resposta
    return resposta
