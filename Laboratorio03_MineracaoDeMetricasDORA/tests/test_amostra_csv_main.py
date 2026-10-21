"""Fontes artificiais somente em fixtures; nenhum voto humano é produzido."""

from collections import Counter
import csv
import json
from pathlib import Path
import shutil

import pytest

import amostra_csv_main as fonte
import gerar_amostra_rotulagem as original
from rotulagem import JULGAMENTOS, ler_csv


@pytest.fixture
def entradas(tmp_path):
    pasta = tmp_path / "entradas"
    pasta.mkdir()
    repos, releases = [], {}
    for i in range(300):
        nome = f"fixture/projeto-{i:03d}"
        repos.append({"full_name": nome, "total_releases_janela": "7"})
        releases[nome] = [
            dict(id=i * 10 + j + 1, tag_name=f"v1.0.{j}",
                 published_at=f"2024-01-{j + 1:02d}T00:00:00Z",
                 draft=False, prerelease=False,
                 html_url=f"https://github.com/{nome}/releases/tag/v1.0.{j}",
                 body="Conteúdo artificial de teste, não coletado da API.")
            for j in range(7)
        ]
    paths = {"csv": pasta / "repos.csv", "releases": pasta / "releases.json",
             "proveniencia": pasta / "proveniencia.json", "config": pasta / "config.yaml"}
    with paths["csv"].open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos)
    paths["releases"].write_text(json.dumps(releases), encoding="utf-8")
    paths["config"].write_text(
        'window:\n  start_date: "2023-10-01T00:00:00Z"\n  end_date: "2024-09-30T23:59:59Z"\n',
        encoding="utf-8",
    )
    # Esta declaração não prova origem empírica. O novo modo não a promove.
    prov = dict(origem="github_api", janela=dict(inicio="2023-10-01T00:00:00Z", fim="2024-09-30T23:59:59Z"),
                repositorios_sha256=fonte.sha256(paths["csv"]), releases_sha256=fonte.sha256(paths["releases"]))
    paths["proveniencia"].write_text(json.dumps(prov), encoding="utf-8")
    return paths


def executar(paths, tmp_path):
    return fonte.executar(paths["csv"], paths["releases"], paths["proveniencia"], paths["config"],
                          tmp_path / "referencia", tmp_path / "rotulos_aulus.csv")


def test_reproduz_60x5_sem_promover_declaracao_e_preserva_bytes(entradas, tmp_path):
    before = {key: path.read_bytes() for key, path in entradas.items()}
    result = executar(entradas, tmp_path)
    common = Path(result["amostra"])
    rows = ler_csv(common)
    assert len(rows) == 300
    assert Counter(Counter(row["full_name"] for row in rows).values()) == {5: 60}
    assert all(row[field] == "" for row in rows for field in JULGAMENTOS)
    assert ler_csv(result["rotulos"]) == rows
    manifest = original.validar_referencia(common)
    assert manifest == result["manifesto"]
    assert manifest["tipo_fonte"] == fonte.TIPO_FONTE
    assert all(manifest[key] is False for key in fonte.FLAGS)
    assert manifest["random_state"] == 42
    assert manifest["proveniencia_fornecida_nao_auditada"]["origem"] == "github_api"
    for key, registro in manifest["entradas"].items():
        assert not Path(registro["arquivo"]).is_absolute()
        assert "\\" not in registro["arquivo"]
        assert (common.parent / registro["arquivo"]).read_bytes() == before[key]
    assert {key: path.read_bytes() for key, path in entradas.items()} == before


def test_referencia_autossuficiente_apos_mover_e_remover_entradas(entradas, tmp_path):
    result = executar(entradas, tmp_path)
    destino = tmp_path / "outra_maquina" / "referencia"
    destino.parent.mkdir()
    shutil.move(str(Path(result["amostra"]).parent), str(destino))
    shutil.rmtree(entradas["csv"].parent)
    assert fonte.validar_referencia_fornecida(destino / "amostra_comum.csv")["n_releases"] == 300


@pytest.mark.parametrize("campo", list(fonte.FLAGS))
def test_recusa_promocao_do_manifesto_a_coleta_auditada(entradas, tmp_path, campo):
    result = executar(entradas, tmp_path)
    path = Path(result["amostra"]).parent / "selecao.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest[campo] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="não certifica"):
        original.validar_referencia(result["amostra"])


@pytest.mark.parametrize("arquivo", ["amostra_comum.csv", "evidencias_releases.json", "fontes_entrada/releases.json"])
def test_detecta_adulteracao_de_unidades_e_fontes(entradas, tmp_path, arquivo):
    result = executar(entradas, tmp_path)
    path = Path(result["amostra"]).parent / arquivo
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        original.validar_referencia(result["amostra"])


def test_nao_substitui_populacao_ou_projetos_insuficientes(entradas, tmp_path):
    releases = json.loads(entradas["releases"].read_text(encoding="utf-8"))
    releases["fixture/projeto-000"] = releases["fixture/projeto-000"][:4]
    entradas["releases"].write_text(json.dumps(releases), encoding="utf-8")
    prov = json.loads(entradas["proveniencia"].read_text(encoding="utf-8"))
    prov["releases_sha256"] = fonte.sha256(entradas["releases"])
    entradas["proveniencia"].write_text(json.dumps(prov), encoding="utf-8")
    with pytest.raises(ValueError, match="mínimo 5"):
        executar(entradas, tmp_path)
    assert not (tmp_path / "referencia").exists()
    assert not (tmp_path / "rotulos_aulus.csv").exists()


def test_recusa_populacao_reduzida_antes_de_gerar_arquivos(entradas, tmp_path):
    linhas = entradas["csv"].read_text(encoding="utf-8").splitlines()
    entradas["csv"].write_text("\n".join(linhas[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exatamente 300"):
        executar(entradas, tmp_path)
    assert not (tmp_path / "referencia").exists()


def test_protege_csv_humano_preexistente_antes_de_criar_referencia(entradas, tmp_path):
    humano = tmp_path / "rotulos_aulus.csv"
    humano.write_text("julgamento humano preexistente", encoding="utf-8")
    before = humano.read_bytes()
    with pytest.raises(FileExistsError, match="preservado"):
        executar(entradas, tmp_path)
    assert humano.read_bytes() == before
    assert not (tmp_path / "referencia").exists()


def test_cli_retornacodigo_erro_sem_usar_fallback(entradas, tmp_path, capsys):
    prov = entradas["proveniencia"]
    prov.write_text("{}", encoding="utf-8")
    args = [v for key, path in entradas.items() for v in ("--" + key, str(path))]
    args += ["--saida", str(tmp_path / "referencia"), "--rotulos", str(tmp_path / "rotulos_aulus.csv")]
    assert fonte.main(args) == 2
    assert "Hash" in capsys.readouterr().err
    assert not (tmp_path / "referencia").exists()
