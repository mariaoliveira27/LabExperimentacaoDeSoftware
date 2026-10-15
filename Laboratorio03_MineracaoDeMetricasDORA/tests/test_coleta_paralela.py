"""Concorrência e retomada reais entre threads, com HTTP somente de fixtures."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

import coleta_amostra_real as coleta
from coleta_paralela import exclusividade, qualificar_em_ordem
from test_coleta_amostra_real import APIPlanejada


def test_workers_concorrem_com_clientes_exclusivos_e_entregam_na_ordem():
    barreira = threading.Barrier(3)
    terminou_dois, terminou_um = threading.Event(), threading.Event()
    stop = threading.Event()
    clientes = [object(), object(), object()]
    conclusoes, usos = [], []
    lock = threading.Lock()

    def qualificar(client, candidato):
        with lock:
            usos.append((threading.get_ident(), client))
        barreira.wait(timeout=5)  # Uma execução sequencial não pode passar.
        if candidato == 0:
            assert terminou_um.wait(5)
        elif candidato == 1:
            assert terminou_dois.wait(5)
        with lock:
            conclusoes.append(candidato)
        if candidato == 2:
            terminou_dois.set()
        elif candidato == 1:
            terminou_um.set()
        return candidato * 10

    with closing(qualificar_em_ordem(range(3), clientes, qualificar, stop)) as tarefas:
        resultados = list(tarefas)
    assert conclusoes == [2, 1, 0]
    assert resultados == [(0, 0), (1, 10), (2, 20)]
    assert len({thread for thread, _ in usos}) == 3
    assert {client for _, client in usos} == set(clientes)
    assert stop.is_set()


def test_prefetch_limitado_nao_esgota_iterador_nem_submete_apos_close():
    consumidos, iniciados = [], []
    liberar, todos_iniciados = threading.Event(), threading.Event()
    stop, lock = threading.Event(), threading.Lock()

    def candidatos():
        for candidato in range(100):
            consumidos.append(candidato)
            yield candidato

    def qualificar(client, candidato):
        with lock:
            iniciados.append(candidato)
            if len(iniciados) == 3:
                todos_iniciados.set()
        assert liberar.wait(5)
        return candidato

    tarefas = qualificar_em_ordem(candidatos(), [object()] * 3, qualificar, stop)
    with ThreadPoolExecutor(max_workers=1) as consumidor:
        primeiro = consumidor.submit(next, tarefas)
        try:
            assert todos_iniciados.wait(5)
            assert consumidos == [0, 1, 2]
            liberar.set()
            assert primeiro.result(timeout=5) == (0, 0)
            # O gerador suspenso no yield não antecipa o próximo candidato.
            assert consumidos == [0, 1, 2]
        finally:
            liberar.set()
            primeiro.result(timeout=5)
            tarefas.close()
    assert sorted(iniciados) == [0, 1, 2]
    assert stop.is_set()


def test_close_sinaliza_parada_e_aguarda_worker_antes_de_devolver():
    iniciou, liberar, terminou = threading.Event(), threading.Event(), threading.Event()
    stop = threading.Event()
    iniciados = []

    def qualificar(client, candidato):
        iniciados.append(candidato)
        if candidato == 0:
            assert iniciou.wait(5)
        else:
            iniciou.set()
            assert liberar.wait(5)
            terminou.set()
        return candidato

    tarefas = qualificar_em_ordem(range(10), [object(), object()], qualificar, stop)
    assert next(tarefas) == (0, 0)
    with ThreadPoolExecutor(max_workers=1) as encerrador:
        fechamento = encerrador.submit(tarefas.close)
        try:
            assert stop.wait(5)
            assert not fechamento.done()
            assert not terminou.is_set()
        finally:
            liberar.set()
            fechamento.result(timeout=5)
    assert terminou.is_set()
    assert sorted(iniciados) == [0, 1]


def test_falha_aguarda_outros_workers_e_nao_entrega_resultado_fora_de_ordem():
    iniciou, liberar, terminou = threading.Event(), threading.Event(), threading.Event()
    stop = threading.Event()

    def qualificar(client, candidato):
        if candidato == 0:
            assert iniciou.wait(5)
            raise RuntimeError("Falha exclusivamente da fixture")
        iniciou.set()
        assert liberar.wait(5)
        terminou.set()
        return candidato

    tarefas = qualificar_em_ordem(range(20), [object(), object()], qualificar, stop)
    with ThreadPoolExecutor(max_workers=1) as consumidor:
        primeiro = consumidor.submit(next, tarefas)
        try:
            assert stop.wait(5)
            assert not primeiro.done()
        finally:
            liberar.set()
        with pytest.raises(RuntimeError, match="exclusivamente da fixture"):
            primeiro.result(timeout=5)
    assert terminou.is_set()


def _outro_processo_tenta_lock(saida):
    codigo = (
        "import sys\n"
        "from coleta_paralela import exclusividade\n"
        "try:\n"
        "    with exclusividade(sys.argv[1]):\n"
        "        pass\n"
        "except RuntimeError:\n"
        "    raise SystemExit(73)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", codigo, str(saida)],
        cwd=Path(coleta.__file__).resolve().parent,
        capture_output=True, text=True, timeout=15, check=False,
    )


def test_lock_do_so_exclui_outro_processo_e_libera_apos_excecao(tmp_path):
    saida = tmp_path / "destino"
    with pytest.raises(ValueError, match="Interrupção da fixture"):
        with exclusividade(saida):
            concorrente = _outro_processo_tenta_lock(saida)
            assert concorrente.returncode == 73, concorrente.stderr
            raise ValueError("Interrupção da fixture")
    retomada = _outro_processo_tenta_lock(saida)
    assert retomada.returncode == 0, retomada.stderr
    # Não remover o arquivo: o inode/handle deve continuar sendo o mesmo lock.
    assert (tmp_path / ".destino.coleta.lock").is_file()


class APIWorker(APIPlanejada):
    """Cada sessão pertence a uma thread; nenhuma requisição sai da fixture."""

    def __init__(self, quantidade, journal):
        super().__init__(quantidade)
        self.journal, self.dono, self.fechada = journal, None, False
        self.session = SimpleNamespace(close=self.fechar)

    def fechar(self):
        self.fechada = True

    def _registrar(self, endpoint):
        assert not self.fechada
        atual = threading.get_ident()
        if self.dono is None:
            self.dono = atual
        assert self.dono == atual, "Uma sessão de fixture foi compartilhada entre workers"
        self.journal(endpoint)

    def request(self, endpoint, params=None, **kwargs):
        self._registrar(endpoint)
        return super().request(endpoint, params, **kwargs)

    def paginate(self, endpoint, params=None):
        self._registrar(endpoint)
        return super().paginate(endpoint, params)


@pytest.fixture
def coleta_offline(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        'window:\n  start_date: "2023-10-01T00:00:00Z"\n'
        '  end_date: "2024-09-30T23:59:59Z"\ncriteria:\n'
        '  min_stars: 1000\n  min_releases: 5\n  min_workflow_runs: 50\n',
        encoding="utf-8",
    )
    criacoes = []

    def preparar(quantidade):
        candidatos = APIPlanejada(quantidade).candidatos
        monkeypatch.setattr(coleta, "buscar_candidatos", lambda *args, **kwargs: candidatos)
        monkeypatch.setattr(
            coleta.ColetorRuns, "coletar_runs_janela",
            lambda self, *args: self.client.runs_completos(*args),
        )

        def criar(config, destino, cache_path, workers, token_envs, usar_gh_auth, evento_parada):
            lock = threading.Lock()

            def journal(endpoint):
                with lock, (destino / "requisicoes.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"endpoint_fixture": endpoint}) + "\n")

            clientes = [APIWorker(quantidade, journal) for _ in range(workers)]
            criacoes.append(SimpleNamespace(clientes=clientes, stop=evento_parada, journal=journal))
            return clientes

        monkeypatch.setattr(coleta, "_criar_clientes", criar)
        return config, criacoes

    return preparar


def test_300_aprovados_iguais_e_worker_extra_termina_antes_do_hash(coleta_offline, tmp_path, monkeypatch):
    config, criacoes = coleta_offline(301)
    sequencial, paralelo = tmp_path / "sequencial", tmp_path / "paralelo"
    estado_seq = coleta.coletar(config, sequencial, workers=1)
    assinatura = (sequencial / "config_coleta.json").read_bytes()
    iniciou_extra, terminou_extra = threading.Event(), threading.Event()
    qualificar_original, sha_original = coleta._qualificar, coleta.sha256
    verificacoes_hash = []

    def qualificar(client, candidato, *args):
        if candidato["id"] == 300:
            assert iniciou_extra.wait(10)
        elif candidato["id"] == 301:
            iniciou_extra.set()
            assert criacoes[-1].stop.wait(10)
        try:
            return qualificar_original(client, candidato, *args)
        finally:
            if candidato["id"] == 301:
                criacoes[-1].journal("worker-extra-finalizado-fixture")
                terminou_extra.set()

    def sha(path):
        if Path(path) == paralelo / "requisicoes.jsonl":
            assert terminou_extra.is_set(), "Publicação tentou hashear journal com worker ativo"
            verificacoes_hash.append(True)
        return sha_original(path)

    monkeypatch.setattr(coleta, "_qualificar", qualificar)
    monkeypatch.setattr(coleta, "sha256", sha)
    estado_par = coleta.coletar(config, paralelo, workers=2)
    assert estado_seq["status"] == estado_par["status"] == "completa"
    assert estado_seq["n_aprovados"] == estado_par["n_aprovados"] == 300
    assert estado_seq["n_processados"] == estado_par["n_processados"] == 300
    assert (paralelo / "config_coleta.json").read_bytes() == assinatura
    for arquivo in ("repositorios_aprovados.csv", "releases.json"):
        assert (sequencial / arquivo).read_bytes() == (paralelo / arquivo).read_bytes()
    assert verificacoes_hash
    assert not (paralelo / "qualificacoes/301.json").exists()
    manifesto = json.loads((paralelo / "proveniencia.json").read_text(encoding="utf-8"))
    assert manifesto["requisicoes_sha256"] == sha_original(paralelo / "requisicoes.jsonl")
    assert len(manifesto["evidencias"]) == 300
    assert all(client.fechada for chamada in criacoes for client in chamada.clientes)


def test_retoma_apos_falha_preserva_checkpoint_e_aceita_outro_numero_workers(coleta_offline, tmp_path, monkeypatch):
    config, criacoes = coleta_offline(8)
    destino = tmp_path / "retomavel"
    original = coleta._qualificar
    chamadas = []

    def falhar(client, candidato, *args):
        chamadas.append(candidato["id"])
        if candidato["id"] == 2:
            raise RuntimeError("Falha HTTP exclusivamente simulada na fixture")
        return original(client, candidato, *args)

    monkeypatch.setattr(coleta, "_qualificar", falhar)
    with pytest.raises(RuntimeError, match="exclusivamente simulada"):
        coleta.coletar(config, destino, workers=4)
    assert all(client.fechada for client in criacoes[0].clientes)
    estado = json.loads((destino / "estado.json").read_text(encoding="utf-8"))
    assert estado["status"] == "interrompida" and estado["n_processados"] == 1
    snapshot = (destino / "qualificacoes/1.json").read_bytes()
    assinatura = (destino / "config_coleta.json").read_bytes()
    chamadas.clear()

    def concluir(client, candidato, *args):
        chamadas.append(candidato["id"])
        return original(client, candidato, *args)

    monkeypatch.setattr(coleta, "_qualificar", concluir)
    final = coleta.coletar(config, destino, workers=2)
    assert final["status"] == "insuficiente"
    assert final["n_processados"] == final["n_aprovados"] == 8
    assert sorted(chamadas) == list(range(2, 9))
    assert (destino / "qualificacoes/1.json").read_bytes() == snapshot
    assert (destino / "config_coleta.json").read_bytes() == assinatura
    assert set(final["snapshots"]) == {f"{i}.json" for i in range(1, 9)}
    assert all(coleta.sha256(destino / "qualificacoes" / nome) == digest
               for nome, digest in final["snapshots"].items())
    assert all(client.fechada for client in criacoes[-1].clientes)
    assert not (destino / "proveniencia.json").exists()


@pytest.mark.parametrize("opcoes", [
    {"workers": 0}, {"workers": 9}, {"workers": True},
    {"workers": 2, "client": object()}, {"token_envs": "NOME_ENV_FIXTURE"},
    {"workers": 1, "token_envs": ["CONTA_A_FIXTURE", "CONTA_B_FIXTURE"]},
    {"workers": 2, "usar_gh_auth": True, "token_envs": ["CONTA_A_FIXTURE"]},
])
def test_configuracao_invalida_falha_antes_de_criar_saida(tmp_path, opcoes):
    destino = tmp_path / "nao_criar"
    with pytest.raises(ValueError):
        coleta.coletar(saida=destino, **opcoes)
    assert not destino.exists()
