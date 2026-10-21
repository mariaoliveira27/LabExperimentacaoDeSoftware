"""Dados artificiais somente em fixtures; não são coleta ou julgamento humano."""

import copy
import csv
import json
from pathlib import Path

import pandas as pd
import pytest

import gerar_amostra_rotulagem as amostra


@pytest.fixture
def coleta_fixture(tmp_path, monkeypatch):
    # A auditoria de snapshots do bundle é coberta nos testes do coletor. Esta
    # fixture isolada exercita sorteio, hashes e releases, sem se declarar real.
    monkeypatch.setattr(amostra, "validar_coleta_final", lambda *args: None)
    repos, releases = [], {}
    for i in range(300):
        nome = f"fixture/projeto-{i:03d}"
        repos.append(dict(full_name=nome, origem_coleta="github_api", stars="1500",
                          total_releases_janela="7", total_runs_janela="100"))
        releases[nome] = [dict(id=i * 10 + j + 1, tag_name=f"v1.0.{j}",
                               published_at=f"2024-01-{j + 1:02d}T00:00:00Z", draft=False, prerelease=False,
                               html_url=f"https://github.com/{nome}/releases/tag/v1.0.{j}", body=f"Fixture de teste {j}")
                          for j in range(7)]
    repos_csv, releases_json = tmp_path / "aprovados.csv", tmp_path / "releases.json"
    with repos_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos)
    releases_json.write_text(json.dumps(releases), encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text('window:\n  start_date: "2023-10-01T00:00:00Z"\n  end_date: "2024-09-30T23:59:59Z"\n', encoding="utf-8")
    proveniencia = dict(schema_version=1, origem="github_api", modo_referencia=False,
                       fonte_candidatos="github_search_api", coletado_em="2024-10-01T00:00:00Z",
                       janela=dict(inicio="2023-10-01T00:00:00Z", fim="2024-09-30T23:59:59Z"),
                       criterios=dict(min_stars=1000, min_releases=5, min_workflow_runs=50),
                       repositorios_sha256=amostra.sha256(repos_csv), releases_sha256=amostra.sha256(releases_json))
    proveniencia_json = tmp_path / "proveniencia.json"
    proveniencia_json.write_text(json.dumps(proveniencia), encoding="utf-8")
    return repos, releases, repos_csv, releases_json, proveniencia_json, config


def sortear_fixture(fixture):
    repos, releases, *_ = fixture
    return amostra.sortear(repos, releases, amostra.instante("2023-10-01T00:00:00Z"),
                          amostra.instante("2024-09-30T23:59:59Z"))


def test_sorteio_60x5_deterministico_independente_da_ordem(coleta_fixture):
    rows, evidencias = sortear_fixture(coleta_fixture)
    repos, releases, *_ = coleta_fixture
    reversed_fixture = (list(reversed(repos)), {nome: list(reversed(rels)) for nome, rels in releases.items()})
    assert sortear_fixture(reversed_fixture) == (rows, evidencias)
    nomes = sorted({row["full_name"] for row in rows})
    expected = sorted(pd.DataFrame(repos).sort_values("full_name").sample(n=60, random_state=42)["full_name"])
    assert nomes == expected
    assert len(rows) == 300
    assert len(nomes) == 60
    assert all(sum(row["full_name"] == nome for row in rows) == 5 for nome in nomes)
    assert len({row["release_id"] for row in rows}) == 300
    assert all(row[campo] == "" for row in rows for campo in amostra.JULGAMENTOS)


def test_identificadores_fontes_e_predecessor_da_populacao(coleta_fixture):
    rows, evidencias = sortear_fixture(coleta_fixture)
    for row in rows:
        j = int(row["tag_name"].rsplit(".", 1)[1])
        assert row["release_notes_url"] == row["html_url"]
        assert row["previous_tag"] == (f"v1.0.{j - 1}" if j else "")
        assert ("/compare/" if j else "/commits/") in row["commits_url"]
    assert len(evidencias) == 60
    assert all(len(rels) == 5 for rels in evidencias.values())


def test_exporta_manifesto_hashes_e_protege_selecao(coleta_fixture, tmp_path):
    _, _, repos, releases, provenance, config = coleta_fixture
    destino = tmp_path / "ouro"
    manifest = amostra.gerar_amostra(repos, releases, provenance, config, destino)
    assert manifest["random_state"] == 42
    assert manifest["n_populacao"] == 300
    assert manifest["n_releases"] == 300
    assert manifest["status"] == "aguardando_rotulagem_humana"
    assert manifest["amostra_comum_sha256"] == amostra.sha256(destino / "amostra_comum.csv")
    assert manifest == json.loads((destino / "selecao.json").read_text(encoding="utf-8"))
    assert not (tmp_path / "rotulos_vinicius.csv").exists()
    with pytest.raises(FileExistsError, match="preservada"):
        amostra.gerar_amostra(repos, releases, provenance, config, destino)


def test_insuficiente_encerra_sem_usar_releases_ou_criar_saida(coleta_fixture, tmp_path, capsys):
    repos, _, repos_csv, *_ = coleta_fixture
    with repos_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos[:100])
    destino = tmp_path / "ouro"
    assert amostra.main(["--repos", str(repos_csv), "--saida", str(destino)]) == 2
    erro = capsys.readouterr().err
    assert "100 repositórios" in erro and "300" in erro and "coleta real" in erro
    assert not destino.exists()


@pytest.mark.parametrize("campo,valor,erro", [
    ("origem", "seed_data", "coleta real"), ("modo_referencia", True, "coleta real"),
    ("fonte_candidatos", "seed_data.py", "coleta real"),
    ("releases_sha256", "0" * 64, "Hash"), ("repositorios_sha256", "0" * 64, "Hash"),
    ("schema_version", 0, "schema_version"), ("coletado_em", "2024-10-01", "fuso"),
    ("janela", dict(inicio="2024-01-01T00:00:00Z", fim="2024-09-30T23:59:59Z"), "Janela"),
    ("criterios", dict(min_stars=1000, min_releases=5, min_workflow_runs=10), "Critério"),
])
def test_proveniencia_nao_aceita_referencia_ou_adulteracao(coleta_fixture, campo, valor, erro, tmp_path):
    _, _, repos, releases, provenance, config = coleta_fixture
    dados = json.loads(provenance.read_text(encoding="utf-8"))
    dados[campo] = valor
    provenance.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match=erro):
        amostra.gerar_amostra(repos, releases, provenance, config, tmp_path / "ouro")
    assert not (tmp_path / "ouro").exists()


@pytest.mark.parametrize("alterar,erro", [
    (lambda r: r["fixture/projeto-000"].pop(), "Contagem"),
    (lambda r: r["fixture/projeto-000"][0].update(draft=True), "Contagem"),
    (lambda r: r["fixture/projeto-000"][0].update(prerelease=True), "Contagem"),
    (lambda r: r["fixture/projeto-000"][0].update(published_at="2023-09-30T23:59:59Z"), "Contagem"),
    (lambda r: r["fixture/projeto-000"][0].update(id=0), "ID/tag"),
    (lambda r: r["fixture/projeto-000"][0].update(html_url=""), "Link direto"),
    (lambda r: r["fixture/projeto-000"].append(r["fixture/projeto-000"][0]), "duplicada"),
    (lambda r: r.pop("fixture/projeto-000"), "ausentes"),
    (lambda r: r["fixture/projeto-000"][0].pop("draft"), "Flags"),
])
def test_releases_reais_completas_obrigatorias(coleta_fixture, alterar, erro):
    repos, releases, *_ = coleta_fixture
    releases = copy.deepcopy(releases)
    alterar(releases)
    with pytest.raises(ValueError, match=erro):
        sortear_fixture((repos, releases))


def test_repo_com_quatro_releases_nao_e_substituido(coleta_fixture):
    repos, releases, *_ = coleta_fixture
    releases[repos[0]["full_name"]] = releases[repos[0]["full_name"]][:4]
    with pytest.raises(ValueError, match="mínimo 5"):
        sortear_fixture(coleta_fixture)


def test_csv_de_referencia_nao_aceito(coleta_fixture):
    repos, _, repos_csv, *_ = coleta_fixture
    repos[0]["origem_coleta"] = "referencia_simulada"
    with repos_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos)
    with pytest.raises(ValueError, match="Origem real"):
        amostra.ler_aprovados(repos_csv)


def test_aprovados_duplicados_nao_completam_populacao(coleta_fixture):
    repos, _, repos_csv, *_ = coleta_fixture
    repos[1]["full_name"] = repos[0]["full_name"]
    with repos_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos)
    with pytest.raises(ValueError, match="duplicados"):
        amostra.ler_aprovados(repos_csv)


def test_auditoria_final_obrigatoria_antes_de_gerar(coleta_fixture, tmp_path, monkeypatch):
    _, _, repos, releases, provenance, config = coleta_fixture

    def rejeitar(*args):
        raise ValueError("Snapshots finais ausentes; marcadores não comprovam coleta real.")

    monkeypatch.setattr(amostra, "validar_coleta_final", rejeitar)
    with pytest.raises(ValueError, match="Snapshots finais"):
        amostra.gerar_amostra(repos, releases, provenance, config, tmp_path / "ouro")
    assert not (tmp_path / "ouro").exists()


def test_referencia_revalida_sorteio_e_hashes(coleta_fixture, tmp_path):
    _, _, repos, releases, provenance, config = coleta_fixture
    destino = tmp_path / "ouro"
    manifest = amostra.gerar_amostra(repos, releases, provenance, config, destino)
    comum = destino / "amostra_comum.csv"
    assert amostra.validar_referencia(comum) == manifest
    comum.write_bytes(comum.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash"):
        amostra.validar_referencia(comum)


def test_referencia_rejeita_falso_sorteio_mesmo_com_hash_atualizado(coleta_fixture, tmp_path):
    from rotulagem import ler_csv

    _, _, repos, releases, provenance, config = coleta_fixture
    destino = tmp_path / "ouro"
    manifest = amostra.gerar_amostra(repos, releases, provenance, config, destino)
    comum = destino / "amostra_comum.csv"
    rows = list(reversed(ler_csv(comum)))
    with comum.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=amostra.METADADOS + amostra.JULGAMENTOS)
        writer.writeheader()
        writer.writerows(rows)
    manifest["amostra_comum_sha256"] = amostra.sha256(comum)
    (destino / "selecao.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="determinística"):
        amostra.validar_referencia(comum)


def test_referencia_exige_manifesto(tmp_path):
    with pytest.raises(FileNotFoundError):
        amostra.validar_referencia(tmp_path / "amostra_comum.csv")
