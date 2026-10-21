"""Fluxo completo: HTTP simulado -> SQLite -> coletor -> métricas -> CSV."""

import csv
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import requests

import pipeline


@pytest.fixture
def fluxo_local(tmp_path, monkeypatch):
    config = pipeline.carregar_config()
    config["window"].update(start_date="2024-05-01T00:00:00Z", end_date="2024-05-31T23:59:59Z")
    config["criteria"].update(min_releases=1, min_workflow_runs=3, target_approved_repos=1)
    for key, value in config["storage"].items():
        config["storage"][key] = str(tmp_path / Path(value).name)
    config["storage"]["output_dir"] = str(tmp_path)
    candidate = dict(owner="fixture", repo="offline", stars=1020, lang="Python", branch="old-branch",
                     created="2020-01-01T00:00:00Z", contribs=7, actions=True, releases=1, runs=3)
    monkeypatch.setattr(pipeline, "REPOSITORIOS_CANDIDATOS_REFERENCIA", [candidate])
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    runs = json.loads((Path(__file__).parent / "fixtures/workflow_runs.json").read_text(encoding="utf-8"))
    releases = [{"id": 1, "tag_name": "v1.0.0", "published_at": "2024-05-11T00:00:00Z", "draft": False, "prerelease": False}]
    calls = []

    def get(session, url, params=None, **kwargs):
        assert kwargs["verify"] is True
        calls.append((url, dict(params or {})))
        if url.endswith("/actions/runs"):
            assert params["branch"] == "trunk"
            assert params["event"] == "push"
            payload = {"total_count": len(runs), "workflow_runs": runs}
        elif url.endswith("/actions/workflows"):
            payload = {"total_count": 1, "workflows": [{"id": 10}]}
        elif url.endswith("/releases"):
            payload = releases
        elif url.endswith("/repos/fixture/offline"):
            payload = {"default_branch": "trunk"}
        else:
            raise AssertionError(f"Endpoint inesperado: {url}")
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(payload).encode()
        return response

    monkeypatch.setattr(requests.Session, "get", get)
    return config, candidate, runs, calls, releases


@pytest.mark.parametrize("stars,contributors", [(1020, 7), (11111, 96)])
def test_pipeline_exporta_metricas_reais_e_reutiliza_cache(fluxo_local, stars, contributors, monkeypatch):
    config, candidate, runs, calls, _ = fluxo_local
    candidate.update(stars=stars, contribs=contributors)
    rows, _ = pipeline.executar_pipeline(config)
    row = rows[0]
    assert row["default_branch"] == "trunk"
    assert row["cfr_ci_proxy"] == pytest.approx(1 / 3)
    assert row["tempo_recuperacao_mediana_horas"] == pytest.approx(1.2)
    assert row["runs_sucessos"] == 2
    assert row["runs_falhas"] == 1
    assert row["runs_ignorados"] == 0
    assert row["episodios_recuperados"] == 1
    assert row["episodios_censurados"] == 0
    assert row["proporcao_episodios_censurados"] == 0.0
    assert row["origem_metricas_estabilidade"] == "workflow_runs"
    assert row["lead_time_release_mediana_dias"] is None
    assert row["lead_time_commit_mediana_dias"] is None
    assert row["origem_lead_time"] == "indisponivel_sem_commits_comparaveis"
    assert row["comparacoes_esperadas"] == row["comparacoes_completas"] == 0
    assert row["tier_lead_time"] is None and row["tier_dora_geral"] is None
    with open(config["storage"]["repos_csv"], encoding="utf-8", newline="") as stream:
        exported = next(csv.DictReader(stream))
    assert float(exported["cfr_ci_proxy"]) == pytest.approx(1 / 3)
    assert float(exported["tempo_recuperacao_mediana_horas"]) == pytest.approx(1.2)
    assert exported["lead_time_release_mediana_dias"] == exported["lead_time_commit_mediana_dias"] == ""
    assert exported["tier_lead_time"] == exported["tier_dora_geral"] == ""
    assert len(calls) == 4

    def no_network(*args, **kwargs):
        raise AssertionError("Uma resposta concluída foi requisitada de novo")

    monkeypatch.setattr(requests.Session, "get", no_network)
    resumed, _ = pipeline.executar_pipeline(config)
    assert resumed == rows


def test_pipeline_ignorados_nao_contam_para_minimo(fluxo_local):
    config, _, runs, _, _ = fluxo_local
    runs[1]["conclusion"] = "cancelled"
    rows, funnel = pipeline.executar_pipeline(config)
    assert rows == []
    assert "Possui 2 runs válidos" in funnel.descartes[0].detalhes


def test_pipeline_indisponivel_exportado_vazio(fluxo_local):
    config, _, runs, _, _ = fluxo_local
    config["criteria"]["min_workflow_runs"] = 0
    for run in runs:
        run["conclusion"] = None
    rows, _ = pipeline.executar_pipeline(config)
    assert rows[0]["cfr_ci_proxy"] is None
    assert rows[0]["tempo_recuperacao_mediana_horas"] is None
    assert rows[0]["runs_ignorados"] == 3
    assert rows[0]["proporcao_episodios_censurados"] is None
    assert rows[0]["tier_cfr"] is None
    assert rows[0]["tier_recovery_time"] is None
    with open(config["storage"]["repos_csv"], encoding="utf-8", newline="") as stream:
        exported = next(csv.DictReader(stream))
    assert exported["cfr_ci_proxy"] == exported["tempo_recuperacao_mediana_horas"] == ""


def test_pipeline_falha_coleta_nao_exporta_parcial(fluxo_local, monkeypatch):
    config, _, _, _, _ = fluxo_local

    def interrupted(*args, **kwargs):
        raise RuntimeError("Página pendente")

    monkeypatch.setattr(pipeline.ColetorRuns, "coletar_runs_janela", interrupted)
    with pytest.raises(RuntimeError, match="Página pendente"):
        pipeline.executar_pipeline(config)
    assert not Path(config["storage"]["repos_csv"]).exists()


def test_pipeline_censura_sucesso_concluido_depois_do_corte(fluxo_local):
    config, _, runs, _, _ = fluxo_local
    runs[2]["updated_at"] = "2024-06-01T00:00:00Z"
    rows, _ = pipeline.executar_pipeline(config)
    assert rows[0]["tempo_recuperacao_mediana_horas"] is None
    assert rows[0]["episodios_recuperados"] == 0
    assert rows[0]["episodios_censurados"] == 1
    assert rows[0]["proporcao_episodios_censurados"] == 1.0


@pytest.mark.parametrize("args,reference", [([], False), (["--reference-mode"], True)])
def test_cli_referencia_somente_quando_explicita(monkeypatch, args, reference):
    calls = []
    monkeypatch.setattr(pipeline, "carregar_config", lambda path: {})
    monkeypatch.setattr(pipeline, "executar_pipeline", lambda config, modo_referencia: calls.append(modo_referencia))
    pipeline.main(args)
    assert calls == [reference]


def test_referencia_identifica_simulacao_sem_rede(fluxo_local, monkeypatch):
    config, _, _, _, _ = fluxo_local
    monkeypatch.setattr(requests.Session, "get", lambda *a, **kw: pytest.fail("Referência deve ser local"))
    rows, _ = pipeline.executar_pipeline(config, modo_referencia=True)
    assert rows[0]["origem_metricas_estabilidade"] == "referencia_simulada"
    assert rows[0]["runs_sucessos"] is None


def test_pipeline_compare_paginado_lead_time_cfr_censura_e_cache(fluxo_local, monkeypatch):
    config, _, _, calls, releases = fluxo_local
    releases.extend([
        {"id": 2, "tag_name": "v1.0.1", "published_at": "2024-05-15T00:00:00Z", "draft": False, "prerelease": False},
        {"id": 3, "tag_name": "v1.1.0", "published_at": "2024-05-29T00:00:00Z", "draft": False, "prerelease": False},
    ])
    previous_get = requests.Session.get
    compare_calls = []

    def commit(number, date, message):
        return {"sha": f"{number:040x}", "commit": {"author": {"date": date}, "message": message}}

    def get(session, url, params=None, **kwargs):
        if "/compare/" not in url:
            return previous_get(session, url, params=params, **kwargs)
        page = int((params or {}).get("page", parse_qs(urlparse(url).query).get("page", [1])[0]))
        compare_calls.append((url, page))
        response = requests.Response()
        response.status_code = 200
        if "v1.0.0...v1.0.1" in url:
            commits = (
                [commit(i, "2024-05-12T00:00:00Z", "feat: implementa recurso") for i in range(1, 101)]
                if page == 1 else [commit(101, "2024-05-14T00:00:00Z", "fix: corrige falha")]
            )
            payload = {"total_commits": 101, "commits": commits}
            if page == 1:
                response.headers["Link"] = '<https://api.github.com/repos/fixture/offline/compare/v1.0.0...v1.0.1?page=2&per_page=100>; rel="next"'
        else:
            assert "v1.0.1...v1.1.0" in url
            payload = {"total_commits": 1, "commits": [commit(102, "2024-05-20T00:00:00Z", "feat: novo recurso")]}
        response._content = json.dumps(payload).encode()
        return response

    monkeypatch.setattr(requests.Session, "get", get)
    rows, _ = pipeline.executar_pipeline(config)
    row = rows[0]
    assert row["lead_time_release_mediana_dias"] == 6.0
    assert row["lead_time_commit_mediana_dias"] == 3.0
    assert row["origem_lead_time"] == "compare_paginado"
    assert row["comparacoes_esperadas"] == row["comparacoes_completas"] == 2
    assert row["releases_com_lead_time"] == 2
    assert row["commits_com_lead_time"] == 102
    assert row["cfr_releases_proxy"] == 0.5
    assert row["releases_com_falha"] == 1
    assert row["releases_avaliadas_cfr"] == 2
    assert row["releases_censuradas_cfr"] == 1
    assert row["origem_cfr_releases"] == "releases_e_compares_paginados"
    assert row["rework_rate"] == 0.333
    assert len(calls) == 4 and len(compare_calls) == 3

    monkeypatch.setattr(requests.Session, "get", lambda *a, **kw: pytest.fail("Resposta completa deveria estar em cache"))
    resumed, _ = pipeline.executar_pipeline(config)
    assert resumed == rows


@pytest.mark.parametrize("commits,expected_cfr,expected_complete", [(None, None, 0), ([], 0.0, 1)])
def test_pipeline_compare_indisponivel_difere_de_completo_vazio(fluxo_local, monkeypatch, commits, expected_cfr, expected_complete):
    config, _, _, _, releases = fluxo_local
    releases.append({"id": 2, "tag_name": "v1.1.0", "published_at": "2024-05-15T00:00:00Z", "draft": False, "prerelease": False})
    monkeypatch.setattr(pipeline.ColetorCommits, "coletar_commits_entre_releases", lambda *args: commits)
    rows, _ = pipeline.executar_pipeline(config)
    row = rows[0]
    assert row["lead_time_release_mediana_dias"] is None
    assert row["lead_time_commit_mediana_dias"] is None
    assert row["comparacoes_esperadas"] == 1
    assert row["comparacoes_completas"] == expected_complete
    assert row["cfr_releases_proxy"] == expected_cfr
    assert row["rework_rate"] == expected_cfr
    if commits is None:
        assert row["origem_cfr_releases"] == "indisponivel_comparacoes_incompletas"
        assert row["releases_avaliadas_cfr"] is None
        with open(config["storage"]["repos_csv"], encoding="utf-8", newline="") as stream:
            exported = next(csv.DictReader(stream))
        assert exported["cfr_releases_proxy"] == exported["rework_rate"] == ""
