"""Regressões da coleta, usando fixtures e respostas HTTP inteiramente locais."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from api_client import GitHubClient
from coletor_runs import ColetaIncompletaError, ColetorRuns

START = datetime(2024, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=1) - timedelta(seconds=1)


@pytest.fixture
def run_factory():
    def make(run_id, created=None, **overrides):
        timestamp = (created or START).isoformat().replace("+00:00", "Z")
        return {
            "id": run_id, "workflow_id": 10, "name": "CI",
            "head_branch": "main", "event": "push", "conclusion": "success",
            "created_at": timestamp, "run_started_at": timestamp,
            "updated_at": timestamp, **overrides,
        }
    return make


@pytest.fixture
def runs_1001(run_factory):
    return [run_factory(i + 1, START + timedelta(seconds=i)) for i in range(1001)]


def make_client(side_effect):
    return SimpleNamespace(request=Mock(side_effect=side_effect), invalidate_cache=Mock())


def payload(items, total=None, headers=None):
    return 200, {"total_count": len(items) if total is None else total, "workflow_runs": items}, headers or {}


def next_link(page):
    return {"Link": f'<https://api.github.com/repos/o/r/actions/runs?page={page}>; rel="next"'}


def collect(client, start=START, end=END):
    return ColetorRuns(client).coletar_runs_janela("o", "r", "main", start, end)


def test_1001_runs_subdivisao_recursiva_sem_perdas(runs_1001):
    def dispatch(endpoint, params):
        first, last = params["created"].split("..")
        matches = [run for run in runs_1001 if first <= run["created_at"] <= last]
        offset = (params["page"] - 1) * 100
        # Reproduz o limite da API, sem permitir à implementação usar a página 11.
        visible = matches[:1000]
        items = visible[offset:offset + 100]
        headers = next_link(params["page"] + 1) if offset + 100 < len(visible) else {}
        return payload(items, len(matches), headers)

    client = make_client(dispatch)
    result = collect(client)
    assert [run["id"] for run in result] == list(range(1, 1002))
    intervals = {call.kwargs["params"]["created"] for call in client.request.call_args_list}
    assert len(intervals) > 3  # concentração de runs exige subdivisão recursiva
    assert all(call.kwargs["params"]["page"] <= 10 for call in client.request.call_args_list)
    assert all(call.kwargs["params"]["branch"] == "main" for call in client.request.call_args_list)
    assert all(call.kwargs["params"]["event"] == "push" for call in client.request.call_args_list)


@pytest.mark.parametrize("start,end,expected", [
    (datetime(2024, 1, 31, tzinfo=timezone.utc), datetime(2024, 3, 1, tzinfo=timezone.utc), [
        "2024-01-31T00:00:00Z..2024-01-31T23:59:59Z",
        "2024-02-01T00:00:00Z..2024-02-29T23:59:59Z",
        "2024-03-01T00:00:00Z..2024-03-01T00:00:00Z",
    ]),
    (datetime(2024, 12, 31, tzinfo=timezone.utc), datetime(2025, 1, 1, tzinfo=timezone.utc), [
        "2024-12-31T00:00:00Z..2024-12-31T23:59:59Z",
        "2025-01-01T00:00:00Z..2025-01-01T00:00:00Z",
    ]),
])
def test_meses_calendario_inclusivos_sem_lacunas(start, end, expected):
    client = make_client(lambda *args, **kwargs: payload([]))
    assert collect(client, start, end) == []
    assert [call.kwargs["params"]["created"] for call in client.request.call_args_list] == expected


def test_utc_e_precisao_segundos(run_factory):
    offset = timezone(timedelta(hours=-3))
    start = datetime(2023, 12, 31, 21, 0, 0, 1, tzinfo=offset)
    end = datetime(2023, 12, 31, 21, 0, 2, 999, tzinfo=offset)
    client = make_client(lambda *args, **kwargs: payload([run_factory(1, START + timedelta(seconds=1))]))
    assert len(collect(client, start, end)) == 1
    assert client.request.call_args.kwargs["params"]["created"] == "2024-01-01T00:00:01Z..2024-01-01T00:00:02Z"


def test_paginacao_link_dedup_e_ordem_deterministica(run_factory):
    first, second, third = [run_factory(i) for i in range(1, 4)]
    client = make_client([
        payload([second, first], 3, next_link(2)),
        payload([second, third], 3),
    ])
    assert [run["id"] for run in collect(client)] == [1, 2, 3]
    assert [call.kwargs["params"]["page"] for call in client.request.call_args_list] == [1, 2]


def test_paginacao_nao_tem_limite_fixo_de_dez_paginas(run_factory):
    client = make_client([
        payload([run_factory(page)], 11, next_link(page + 1) if page < 11 else {})
        for page in range(1, 12)
    ])
    assert len(collect(client)) == 11
    assert client.request.call_count == 11


def test_filtros_locais_preservam_ignorados_e_campos(run_factory):
    client = make_client([payload([
        run_factory(1, conclusion="cancelled"),
        run_factory(2, conclusion=None, run_started_at=None, updated_at=None),
        run_factory(3, head_branch="develop"),
        run_factory(4, event="pull_request"),
        run_factory(5, START - timedelta(seconds=1)),
        run_factory(6, END + timedelta(seconds=1)),
        run_factory(7, END),
    ])])
    result = collect(client)
    assert [run["id"] for run in result] == [1, 2, 7]
    assert result[0]["conclusion"] == "cancelled"
    assert result[1]["conclusion"] == ""
    assert result[1]["run_started_at"] is None
    assert result[1]["updated_at"] is None
    assert result[0]["head_branch"] == "main"
    assert result[0]["event"] == "push"
    assert result[0]["workflow_id"] == 10
    assert result[0]["name"] == "CI"


@pytest.mark.parametrize("total", [1000, 1001])
def test_segundo_saturado_sinaliza_incompletude(total):
    client = make_client([payload([], total)])
    with pytest.raises(ColetaIncompletaError, match="único segundo"):
        collect(client, START, START)


@pytest.mark.parametrize("data", [
    None, [], {}, {"total_count": -1, "workflow_runs": []},
    {"total_count": True, "workflow_runs": []},
    {"total_count": 0}, {"total_count": 0, "workflow_runs": {}},
    {"total_count": 0, "workflow_runs": [], "incomplete_results": True},
])
def test_payload_invalido_nao_vira_coleta_completa(data):
    client = make_client([(200, data, {})])
    with pytest.raises(ColetaIncompletaError):
        collect(client)
    client.invalidate_cache.assert_called_once()


@pytest.mark.parametrize("overrides", [
    {"id": None}, {"workflow_id": None}, {"created_at": "inválido"},
    {"created_at": "2024-01-01T00:00:00"}, {"run_started_at": None},
    {"updated_at": None}, {"head_branch": 5}, {"event": None},
    {"conclusion": 1},
])
def test_run_invalido_nao_recebe_timestamp_fabricado(run_factory, overrides):
    client = make_client([payload([run_factory(1, **overrides)])])
    with pytest.raises(ColetaIncompletaError, match="run inválido"):
        collect(client)
    client.invalidate_cache.assert_called_once()


def test_pagina_faltante_nao_devolve_resultado_parcial(run_factory):
    client = make_client([payload([run_factory(1)], 2, next_link(2)), payload([], 2)])
    with pytest.raises(ColetaIncompletaError, match="vazia/repetida"):
        collect(client)


def test_link_nao_pode_pular_paginas(run_factory):
    client = make_client([payload([run_factory(1)], 2, next_link(3))])
    with pytest.raises(ColetaIncompletaError, match="não sequencial"):
        collect(client)


def test_total_count_inconsistente_sinaliza_erro(run_factory):
    client = make_client([
        payload([run_factory(1)], 2, next_link(2)),
        payload([run_factory(2)], 3),
    ])
    with pytest.raises(ColetaIncompletaError, match="total_count mudou"):
        collect(client)


def test_id_duplicado_divergente_sinaliza_erro(run_factory):
    client = make_client([payload([run_factory(1), run_factory(1, conclusion="failure")], 1)])
    with pytest.raises(ColetaIncompletaError, match="conteúdo divergente"):
        collect(client)


@pytest.mark.parametrize("response,expected", [
    ((200, {"total_count": 0}, {}), False),
    ((200, {"total_count": 1}, {}), True),
])
def test_github_actions(response, expected):
    assert ColetorRuns(make_client([response])).tem_github_actions("o", "r") is expected


def test_erro_actions_nao_significa_ausencia_de_actions():
    with pytest.raises(ColetaIncompletaError, match="HTTP 503"):
        ColetorRuns(make_client([(503, {}, {})])).tem_github_actions("o", "r")


def http_response(data, status=200, headers=None):
    response = Mock(spec=requests.Response)
    response.status_code = status
    response.json.return_value = data
    response.headers = headers or {}
    response.text = ""
    return response


def test_erro_e_retomada_reutilizam_paginas_persistidas(tmp_path, run_factory):
    db = str(tmp_path / "cache.db")
    records = [run_factory(i) for i in range(1, 102)]
    client = GitHubClient(token="test", cache_db_path=db, max_retries=0)
    client.session.get = Mock(side_effect=[
        http_response({"total_count": 101, "workflow_runs": records[:100]}, headers=next_link(2)),
        http_response({"message": "error"}, 503),
    ])
    with pytest.raises(ColetaIncompletaError):
        collect(client)
    assert client.session.get.call_count == 2
    client.session.close()

    # Uma nova instância reproduz a retomada após encerrar o processo anterior.
    resumed = GitHubClient(token="test", cache_db_path=db, max_retries=0)
    resumed.session.get = Mock(return_value=http_response({"total_count": 101, "workflow_runs": records[100:]}))
    assert len(collect(resumed)) == 101
    assert resumed.session.get.call_count == 1
    assert resumed.session.get.call_args.kwargs["params"]["page"] == 2
    assert len(collect(resumed)) == 101
    assert resumed.session.get.call_count == 1
    resumed.session.close()


def test_intervalo_concluido_e_reutilizado_na_retomada(tmp_path):
    client = GitHubClient(token="test", cache_db_path=str(tmp_path / "cache.db"), max_retries=0)
    client.session.get = Mock(side_effect=[
        http_response({"total_count": 0, "workflow_runs": []}),
        http_response({}, 503),
        http_response({"total_count": 0, "workflow_runs": []}),
    ])
    end = datetime(2024, 2, 1, tzinfo=timezone.utc)
    with pytest.raises(ColetaIncompletaError):
        collect(client, START, end)
    assert collect(client, START, end) == []
    calls = Counter(call.kwargs["params"]["created"] for call in client.session.get.call_args_list)
    assert calls["2024-01-01T00:00:00Z..2024-01-31T23:59:59Z"] == 1
    assert calls["2024-02-01T00:00:00Z..2024-02-01T00:00:00Z"] == 2
    client.session.close()


def test_schema_invalido_e_invalidado_e_reconsultado(tmp_path):
    client = GitHubClient(token="test", cache_db_path=str(tmp_path / "cache.db"), max_retries=0)
    client.session.get = Mock(side_effect=[
        http_response({"total_count": 0}),
        http_response({"total_count": 0, "workflow_runs": []}),
    ])
    with pytest.raises(ColetaIncompletaError):
        collect(client)
    assert collect(client) == []
    assert client.session.get.call_count == 2
    client.session.close()


def test_total_mutavel_invalida_intervalo_para_retomar(tmp_path, run_factory):
    client = GitHubClient(token="test", cache_db_path=str(tmp_path / "cache.db"), max_retries=0)
    records = [run_factory(i) for i in range(1, 4)]
    client.session.get = Mock(side_effect=[
        http_response({"total_count": 2, "workflow_runs": records[:1]}, headers=next_link(2)),
        http_response({"total_count": 3, "workflow_runs": records[1:]}),
        http_response({"total_count": 3, "workflow_runs": records}),
    ])
    with pytest.raises(ColetaIncompletaError, match="total_count mudou"):
        collect(client)
    assert [r["id"] for r in collect(client)] == [1, 2, 3]
    assert client.session.get.call_count == 3
    assert client.session.get.call_args.kwargs["params"]["page"] == 1


def test_duplicatas_entre_meses_sem_duplicar_saida(run_factory):
    boundary = datetime(2024, 2, 1, tzinfo=timezone.utc)
    january = run_factory(1, boundary - timedelta(seconds=1))
    february = run_factory(2, boundary)
    client = make_client([payload([january]), payload([january, february])])
    assert [r["id"] for r in collect(client, START, boundary)] == [1, 2]


def test_data_impossivel_invalida_cache(run_factory):
    client = make_client([payload([run_factory(1, updated_at="2023-12-31T23:59:59Z")])])
    with pytest.raises(ColetaIncompletaError, match="updated_at anterior"):
        collect(client)
    client.invalidate_cache.assert_called_once()


def test_subdivisao_inconsistente_nao_perde_runs_e_permite_retomada(tmp_path, run_factory):
    client = GitHubClient(token="test", cache_db_path=str(tmp_path / "cache.db"), max_retries=0)
    records = [run_factory(1), run_factory(2)]
    client.session.get = Mock(side_effect=[
        http_response({"total_count": 1001, "workflow_runs": []}),
        http_response({"total_count": 0, "workflow_runs": []}),
        http_response({"total_count": 0, "workflow_runs": []}),
        http_response({"total_count": 2, "workflow_runs": records}),
    ])
    with pytest.raises(ColetaIncompletaError, match="intervalos subdivididos"):
        collect(client)
    assert [r["id"] for r in collect(client)] == [1, 2]
    assert client.session.get.call_count == 4
