"""Tags ambíguas de fixtures preservam recursos REST distintos para revisão."""

import copy
import csv
import json

import pytest

import coleta_amostra_real as coleta
from gerar_amostra_rotulagem import releases_validas
from test_coleta_amostra_real import APIPlanejada, preparar


NOME = "fixture/projeto-000"
ENDPOINT = f"/repos/{NOME}/releases"
INICIO = coleta.instante("2023-10-01T00:00:00Z")
FIM = coleta.instante("2024-09-30T23:59:59Z")
CRITERIOS = {"min_stars": 1000, "min_releases": 5, "min_workflow_runs": 50}


@pytest.fixture
def releases_ambiguas():
    releases = APIPlanejada(1).paginate(ENDPOINT)
    releases[1].update(tag_name=releases[0]["tag_name"], html_url=releases[0]["html_url"])
    releases[0]["assets"] = [{"id": 11, "name": "artefato-python311-fixture.whl"}]
    releases[1]["assets"] = [{"id": 12, "name": "artefato-python310-fixture.whl"}]
    return releases


def test_mesma_tag_ids_distintos_nao_e_fundida_nem_contada(releases_ambiguas):
    anterior = copy.deepcopy(releases_ambiguas)
    with pytest.raises(coleta.ReleaseTagAmbiguaError) as erro:
        coleta._contar_releases(releases_ambiguas, NOME, INICIO, FIM)
    assert erro.value.ambiguidades == [{"tag_name": "v1.0.1", "release_ids": [1001, 1002]}]
    assert releases_ambiguas == anterior
    assert releases_ambiguas[0]["id"] != releases_ambiguas[1]["id"]
    assert releases_ambiguas[0]["assets"] != releases_ambiguas[1]["assets"]


def test_todas_ambiguidades_sao_acumuladas_com_ordem_deterministica(releases_ambiguas):
    releases_ambiguas[3].update(tag_name=releases_ambiguas[2]["tag_name"])
    esperadas = [
        {"tag_name": "v1.0.1", "release_ids": [1001, 1002]},
        {"tag_name": "v1.0.3", "release_ids": [1003, 1004]},
    ]
    for releases in (releases_ambiguas, list(reversed(releases_ambiguas))):
        with pytest.raises(coleta.ReleaseTagAmbiguaError) as erro:
            coleta._contar_releases(releases, NOME, INICIO, FIM)
        assert erro.value.ambiguidades == esperadas


@pytest.mark.parametrize("mesma_tag", [False, True])
def test_id_repetido_continua_erro_fatal_em_vez_de_pendencia(mesma_tag):
    releases = APIPlanejada(1).paginate(ENDPOINT)
    releases[1]["id"] = releases[0]["id"]
    if mesma_tag:
        releases[1]["tag_name"] = releases[0]["tag_name"]
    with pytest.raises(ValueError, match="Release duplicada") as erro:
        coleta._contar_releases(releases, NOME, INICIO, FIM)
    assert not isinstance(erro.value, coleta.ReleaseTagAmbiguaError)


@pytest.mark.parametrize("alteracao", [
    {"draft": None},
    {"published_at": "timestamp-inválido-fixture"},
    {"html_url": "https://github.com/fixture/outro/releases/tag/v1"},
    {"id": 1001},
])
def test_ambiguidade_nao_oculta_erro_posterior_na_lista(releases_ambiguas, alteracao):
    releases_ambiguas[2].update(alteracao)
    with pytest.raises(ValueError) as erro:
        coleta._contar_releases(releases_ambiguas, NOME, INICIO, FIM)
    assert not isinstance(erro.value, coleta.ReleaseTagAmbiguaError)


@pytest.mark.parametrize("alteracao", [
    {"draft": True}, {"prerelease": True}, {"published_at": "2023-01-01T00:00:00Z"},
])
def test_tag_igual_fora_das_unidades_elegiveis_nao_cria_ambiguidade(releases_ambiguas, alteracao):
    releases_ambiguas[1].update(alteracao)
    assert coleta._contar_releases(releases_ambiguas, NOME, INICIO, FIM) == 4


def test_qualificacao_preserva_payload_sem_aprovar_ou_calcular_runs(releases_ambiguas):
    api = APIPlanejada(1)
    api.paginate = lambda endpoint, params=None: releases_ambiguas
    resultado = coleta._qualificar(api, api.candidatos[0], INICIO, FIM, CRITERIOS)
    assert resultado["qualificacao_inconclusiva"] is True
    assert resultado["motivo"] == "tag_de_release_ambigua"
    assert resultado["etapa"] == "3. Releases na janela"
    assert resultado["aprovado"] is False and resultado["releases_suficientes"] is False
    assert resultado["releases"] == releases_ambiguas
    assert resultado["paginacao_releases"]["completa"] is True
    assert resultado["ambiguidades_tags"] == [{"tag_name": "v1.0.1", "release_ids": [1001, 1002]}]
    assert not {"total_releases_janela", "total_runs_janela", "registro", "runs"} & resultado.keys()
    assert not any(endpoint.endswith("/actions/runs") for endpoint, _ in api.chamadas)


def test_pendencia_auditavel_preserva_payload_e_coleta_continua_outros(preparar, releases_ambiguas):
    config, destino, api = preparar(APIPlanejada(3))
    normal = api.paginate

    def releases(endpoint, params=None):
        return releases_ambiguas if endpoint == ENDPOINT else normal(endpoint, params)

    api.paginate = releases
    estado = coleta.coletar(config, destino, client=api)
    assert estado["status"] == "insuficiente"
    assert estado["n_processados"] == 3 and estado["n_aprovados"] == 2
    assert estado["n_pendencias_tecnicas"] == 1
    snapshot = json.loads((destino / "qualificacoes/1.json").read_text(encoding="utf-8"))
    assert snapshot["releases"] == releases_ambiguas
    assert snapshot["paginacao_releases"]["completa"] is True
    assert snapshot["aprovado"] is False and "total_releases_janela" not in snapshot
    with (destino / "pendencias_tecnicas.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        campos = reader.fieldnames
        pendencias = list(reader)
    assert campos[:6] == ["full_name", "motivo", "endpoint", "http_status", "paginas_obtidas", "itens_obtidos"]
    assert len(pendencias) == 1
    assert pendencias[0]["motivo"] == "tag_de_release_ambigua"
    assert all(pendencias[0][campo] == "" for campo in campos[2:6])
    assert json.loads(pendencias[0]["detalhes"])["ambiguidades_tags"] == snapshot["ambiguidades_tags"]
    with (destino / "descartes.csv").open(encoding="utf-8", newline="") as stream:
        descartes = list(csv.DictReader(stream))
    assert len(descartes) == 1 and descartes[0]["motivo"] == "tag_de_release_ambigua"
    assert json.loads(descartes[0]["detalhes"])["paginacao_releases"]["completa"] is True
    assert json.loads(descartes[0]["detalhes"])["ambiguidades_tags"] == snapshot["ambiguidades_tags"]
    assert "tag_de_release_ambigua" in (destino / "funil_selecao.csv").read_text(encoding="utf-8")
    with (destino / "repositorios_aprovados_parcial.csv").open(encoding="utf-8", newline="") as stream:
        aprovados = list(csv.DictReader(stream))
    assert {row["full_name"] for row in aprovados} == {"fixture/projeto-001", "fixture/projeto-002"}
    assert not (destino / "repositorios_aprovados.csv").exists()
    assert not (destino / "releases.json").exists()
    assert not (destino / "proveniencia.json").exists()


def test_gerador_ouro_mantem_regra_estrita_de_tag_unica(releases_ambiguas):
    with pytest.raises(ValueError, match="Release duplicada"):
        releases_validas(
            [{"full_name": NOME, "total_releases_janela": len(releases_ambiguas)}],
            {NOME: releases_ambiguas}, INICIO, FIM,
        )
