"""Execução limitada de candidatos, com entrega na ordem original da busca."""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import os
import queue
import threading

from controle_cotas import InterrompidaColeta


@contextmanager
def exclusividade(saida):
    """O lock do SO é liberado em crash; seu arquivo não deve ser removido."""
    destino = Path(saida).resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    path = destino.parent / f".{destino.name}.coleta.lock"
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Já existe uma coleta usando esta saída. Use um único processo com --workers.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)


def qualificar_em_ordem(candidatos, clientes, qualificar, evento_parada):
    """No máximo len(clientes) tarefas em voo; apenas o consumidor grava estado.

    Encerrar/fechar o gerador cancela tarefas ainda não iniciadas e aguarda os
    workers antes de liberar o journal para hashing/publicação.
    """
    disponiveis = queue.SimpleQueue()
    for client in clientes:
        disponiveis.put(client)
    local = threading.local()

    def tarefa(candidato):
        if evento_parada.is_set():
            raise InterrompidaColeta("Coleta interrompida; respostas completas preservadas.")
        if not hasattr(local, "client"):
            local.client = disponiveis.get_nowait()
        return qualificar(local.client, candidato)

    executor = ThreadPoolExecutor(max_workers=len(clientes), thread_name_prefix="coleta")
    pendentes = deque()
    candidatos = iter(candidatos)

    def submeter():
        candidato = next(candidatos, None)
        if candidato is not None:
            pendentes.append((candidato, executor.submit(tarefa, candidato)))

    try:
        for _ in clientes:
            submeter()
        while pendentes:
            candidato, future = pendentes.popleft()
            # Não usar as_completed: o alvo deve respeitar a ordem da busca.
            yield candidato, future.result()
            if not evento_parada.is_set():
                submeter()
    finally:
        evento_parada.set()
        for _, future in pendentes:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
