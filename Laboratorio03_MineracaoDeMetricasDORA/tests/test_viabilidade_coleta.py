"""A guarda usa somente fixtures; potencial não significa aprovação empírica."""

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
from types import SimpleNamespace

import pytest

from viabilidade_coleta import HistoricoIndisponivelError, verificar_viabilidade


INICIO = datetime(2023, 10, 1, tzinfo=timezone.utc)
FIM = datetime(2024, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
AGORA = datetime(2026, 10, 16, tzinfo=timezone.utc)
MOTIVO = "evidencia_runs_historicos_insuficiente"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    def falhar(*args, **kwargs):
        raise AssertionError("A guarda deve funcionar sem rede.")
    monkeypatch.setattr(socket, "create_connection", falhar)


def zeros(n=100):
    return [dict(candidate_id=i + 1, full_name=f"fixture/projeto-{i}", aprovado=False,
                 motivo=MOTIVO, runs_disponiveis_api=0) for i in range(n)]


def executar(destino, *, resultados=None, historico=None, alvo=300, agora=AGORA, inicio=INICIO, fim=FIM):
    return verificar_viabilidade(destino, inicio, fim, alvo, historico=historico,
                                 resultados=resultados, agora=agora)


def ledger(destino, n=100, aprovados=0):
    destino.mkdir(parents=True, exist_ok=True)
    estado = {"n_processados": n + aprovados, "n_aprovados": aprovados,
              "janela": {"inicio": INICIO.isoformat(), "fim": FIM.isoformat()},
              "snapshots": {"1.json": "snapshot_artificial_que_nao_deve_ser_lido"}}
    (destino / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
    with (destino / "descartes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("full_name", "motivo", "detalhes"))
        writer.writeheader()
        writer.writerows(dict(full_name=row["full_name"], motivo=row["motivo"],
                              detalhes=json.dumps({"runs_disponiveis_api": 0})) for row in zeros(n))


def run(identificador=10, data="2024-06-01T00:00:00Z", nome=None):
    repo = {"id": identificador} if identificador is not None else {}
    if nome is not None:
        repo["full_name"] = nome
    return {"created_at": data, "repository": repo, "event": "pull_request",
            "head_branch": "qualquer-branch", "status": "in_progress", "conclusion": None}


def banco(destino, paginas):
    path = destino / "cache/github_cache.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE api_cache (url TEXT,cache_key TEXT PRIMARY KEY,response_json TEXT,status_code INTEGER,state TEXT)")
        for i, pagina in enumerate(paginas):
            url = pagina.get("url", f"https://api.github.com/repos/fixture/p-{i}/actions/runs")
            payload = pagina.get("payload", {"total_count": len(pagina.get("runs", [])), "workflow_runs": pagina.get("runs", [])})
            raw = pagina.get("raw", json.dumps(payload))
            conn.execute("INSERT INTO api_cache VALUES(?,?,?,?,?)", (
                url, pagina.get("cache_key", f"{url}?page={i + 1}"), raw,
                pagina.get("status", 200), pagina.get("state", "complete"),
            ))
    return path


def historico(ids):
    return SimpleNamespace(runs_por_id={i: [run(i)] for i in ids},
                           metadados_por_id={i: {"full_name": f"fixture/h-{i}"} for i in ids})


def test_cem_zeros_e_fontes_insuficientes_bloqueiam_com_diagnostico_cauteloso(tmp_path):
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros())
    diag = erro.value.diagnostico
    assert diag["status"] == "historico_indisponivel"
    assert diag["n_consultas_historicas_total_zero"] == 100
    assert diag["n_aprovados"] == diag["n_fontes_potenciais"] == 0
    assert diag["alvo"] == 300 and diag["validacao_empirica_serie_nesta_guarda"] is False
    assert "não é prova" in diag["interpretacao"].lower()
    assert "professor" in diag["dica"] and "ausência histórica" in str(erro.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("n", [0, 1, 99])
def test_serie_curta_nao_bloqueia_nem_le_cache_malformado(tmp_path, n):
    path = tmp_path / "cache/github_cache.db"
    path.parent.mkdir()
    path.write_bytes(b"isto nao e SQLite")
    assert executar(tmp_path, resultados=zeros(n)) is None


@pytest.mark.parametrize("agora,fim", [
    (datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc), FIM),
    (AGORA, AGORA - timedelta(days=90)),
    (AGORA, AGORA - timedelta(days=10)),
])
def test_guarda_exige_epoca_e_janela_antiga(tmp_path, agora, fim):
    assert executar(tmp_path, resultados=zeros(), agora=agora, fim=fim) is None


def test_uma_aprovacao_impede_bloqueio(tmp_path):
    resultados = zeros()
    resultados.append(dict(full_name="fixture/aprovado", aprovado=True))
    assert executar(tmp_path, resultados=resultados) is None


def test_sem_checkpoint_nao_cria_diretorio(tmp_path):
    destino = tmp_path / "nao-existe"
    assert executar(destino) is None
    assert not destino.exists()


def test_ledger_fornece_serie_hashes_e_nao_le_snapshots_nem_escreve(tmp_path):
    ledger(tmp_path)
    snapshots = tmp_path / "qualificacoes"
    snapshots.mkdir()
    (snapshots / "1.json").write_bytes(b"nao e JSON e nao deve ser lido")
    antes = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path)
    assert erro.value.diagnostico["origem_serie_zero"] == "checkpoint_descartes"
    assert erro.value.diagnostico["evidencias_sha256"] == {
        nome: hashlib.sha256(antes[nome]).hexdigest() for nome in ("estado.json", "descartes.csv")
    }
    depois = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert antes == depois


def test_resultados_fornecidos_nao_somam_zeros_do_ledger(tmp_path):
    ledger(tmp_path, n=150)
    assert executar(tmp_path, resultados=zeros(1)) is None


@pytest.mark.parametrize("alteracao", ["contagem", "detalhes", "duplicata", "janela"])
def test_ledger_inconsistente_nao_vira_diagnostico_de_indisponibilidade(tmp_path, alteracao):
    ledger(tmp_path)
    if alteracao in ("contagem", "janela"):
        estado = json.loads((tmp_path / "estado.json").read_text())
        if alteracao == "contagem":
            estado["n_processados"] += 1
        else:
            estado["janela"]["fim"] = "2025-09-30T23:59:59Z"
        (tmp_path / "estado.json").write_text(json.dumps(estado))
    elif alteracao == "detalhes":
        texto = (tmp_path / "descartes.csv").read_text()
        (tmp_path / "descartes.csv").write_text(texto.replace("runs_disponiveis_api", "campo_ausente", 1))
    else:
        texto = (tmp_path / "descartes.csv").read_text()
        (tmp_path / "descartes.csv").write_text(texto.replace("fixture/projeto-1,", "fixture/projeto-0,", 1))
    with pytest.raises(ValueError):
        executar(tmp_path)


@pytest.mark.parametrize("problema", ["duplicata", "aprovacao_ausente", "zero_bool"])
def test_resultados_invalidos_nao_inflam_serie(tmp_path, problema):
    resultados = zeros()
    if problema == "duplicata":
        resultados[1] = resultados[0].copy()
    elif problema == "aprovacao_ausente":
        resultados[0].pop("aprovado")
    else:
        resultados[0]["runs_disponiveis_api"] = False
    with pytest.raises(ValueError):
        executar(tmp_path, resultados=resultados)


def test_trezentas_fontes_historicas_potenciais_nao_bloqueiam(tmp_path):
    assert executar(tmp_path, resultados=zeros(), historico=historico(range(1, 301))) is None


def test_trezentos_repos_no_cache_contam_qualquer_evento_branch_e_um_unico_run(tmp_path):
    db = banco(tmp_path, [{"runs": [run(i)]} for i in range(1, 301)])
    antes = db.read_bytes()
    assert executar(tmp_path, resultados=zeros()) is None
    assert db.read_bytes() == antes
    assert not db.with_name(db.name + "-journal").exists()


def test_duzentas_noventa_nove_fontes_ainda_insuficientes(tmp_path):
    banco(tmp_path, [{"runs": [run(i)]} for i in range(1, 300)])
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros())
    assert erro.value.diagnostico["n_fontes_potenciais"] == 299
    assert erro.value.diagnostico["fontes_potenciais"]["runs_na_janela_encontrados_no_cache"] == 299


def test_runs_fora_da_janela_nao_aumentam_fontes(tmp_path):
    banco(tmp_path, [{"runs": [run(i, data="2026-10-01T00:00:00Z")]} for i in range(1, 301)])
    hist = historico([999])
    hist.runs_por_id[999] = [run(999, data="2023-01-01T00:00:00Z")]
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros(), historico=hist)
    assert erro.value.diagnostico["n_fontes_potenciais"] == 0


def test_uniao_historico_cache_nao_soma_paginas_ou_aliases_repetidos(tmp_path):
    hist = historico([10])
    paginas = [
        {"url": "https://api.github.com/repos/fixture/h-10/actions/runs", "runs": [run(None)]},
        {"url": "https://api.github.com/repos/fixture/renomeado/actions/runs", "runs": [run(10, nome="fixture/antigo")]},
        {"url": "https://api.github.com/repos/fixture/antigo/actions/runs", "runs": [run(None, nome="fixture/antigo")]},
    ]
    banco(tmp_path, paginas)
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros(), historico=hist)
    assert erro.value.diagnostico["n_fontes_potenciais"] == 1
    assert erro.value.diagnostico["identidades_potenciais"] == [{"tipo": "id", "valor": 10}]


def test_uniao_de_fontes_distintas_alcanca_alvo_sem_aprovar_nenhuma(tmp_path):
    banco(tmp_path, [{"runs": [run(i)]} for i in range(16, 301)])
    assert executar(tmp_path, resultados=zeros(), historico=historico(range(1, 16))) is None


def test_id_pode_vir_da_url_de_redirect_sem_repository_no_run(tmp_path):
    banco(tmp_path, [{"url": "https://api.github.com/repositories/123/actions/runs",
                      "runs": [{"created_at": "2024-01-01T00:00:00Z"}]}])
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros())
    assert erro.value.diagnostico["identidades_potenciais"] == [{"tipo": "id", "valor": 123}]


def test_fallback_full_name_e_normalizado_por_casefold(tmp_path):
    banco(tmp_path, [{"runs": [run(None, nome="Fixture/Mesmo")]},
                     {"runs": [run(None, nome="fixture/mesmo")]}])
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros())
    assert erro.value.diagnostico["n_fontes_potenciais"] == 1


def test_pending_http_erro_e_outras_rotas_nao_sao_fontes(tmp_path):
    banco(tmp_path, [
        {"runs": [run(1)], "status": 500}, {"runs": [run(2)], "state": "pending"},
        {"url": "https://api.github.com/repos/fixture/x/actions/runs/1/jobs", "raw": "nao precisa parsear subrota"},
    ])
    with pytest.raises(HistoricoIndisponivelError) as erro:
        executar(tmp_path, resultados=zeros())
    assert erro.value.diagnostico["n_fontes_potenciais"] == 0


@pytest.mark.parametrize("pagina", [
    {"raw": "{JSON quebrado"}, {"payload": []},
    {"payload": {"total_count": 1, "workflow_runs": None}},
    {"payload": {"total_count": True, "workflow_runs": []}},
    {"payload": {"total_count": 0, "workflow_runs": [run()]}},
    {"payload": {"total_count": 1, "workflow_runs": [run()], "incomplete_results": True}},
    {"runs": [run(data="2024-06-01T00:00:00")]},
])
def test_cache_malformado_propaga_sem_omissao_silenciosa(tmp_path, pagina):
    banco(tmp_path, [pagina])
    with pytest.raises(ValueError):
        executar(tmp_path, resultados=zeros())


@pytest.mark.parametrize("tipo", ["corrompido", "sem_tabela"])
def test_erro_sqlite_propaga(tmp_path, tipo):
    path = tmp_path / "cache/github_cache.db"
    path.parent.mkdir()
    if tipo == "corrompido":
        path.write_bytes(b"nao e um banco")
    else:
        sqlite3.connect(path).close()
    with pytest.raises(sqlite3.DatabaseError):
        executar(tmp_path, resultados=zeros())


def test_historico_com_run_malformado_apos_run_valido_nao_e_ignorado(tmp_path):
    hist = historico([1])
    hist.runs_por_id[1].append({"created_at": "invalido"})
    with pytest.raises(ValueError):
        executar(tmp_path, resultados=zeros(), historico=hist)


def test_guarda_nao_le_nem_hasheia_arquivo_sqlite_por_path_read_bytes(tmp_path, monkeypatch):
    banco(tmp_path, [{"runs": []}])
    original = Path.read_bytes
    def ler_somente_ledger(path):
        assert path.suffix != ".db", "Banco volumoso não deve ser carregado ou hasheado pela guarda"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", ler_somente_ledger)
    with pytest.raises(HistoricoIndisponivelError):
        executar(tmp_path, resultados=zeros())
