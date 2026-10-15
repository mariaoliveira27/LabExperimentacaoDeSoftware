"""Fixtures sintéticas testam a preparação; não constituem coleta empírica."""

import csv
import json

import pytest

import executar_amostra_ouro as fluxo
from gerar_amostra_rotulagem import sha256
from rotulagem import JULGAMENTOS, METADADOS, ler_csv, validar_rotulos


@pytest.fixture
def bundle_fixture(tmp_path):
    coleta = tmp_path / "coleta"
    coleta.mkdir()
    repos, releases = [], {}
    for indice in range(300):
        nome = f"fixture/projeto-{indice:03d}"
        repos.append({
            "full_name": nome, "origem_coleta": "github_api", "stars": "1500",
            "total_releases_janela": "6", "total_runs_janela": "100",
        })
        releases[nome] = [
            {
                "id": indice * 6 + release + 1,
                "tag_name": f"v1.{release}.0",
                "published_at": f"2024-01-{release + 1:02d}T12:00:00Z",
                "html_url": f"https://github.com/{nome}/releases/tag/v1.{release}.0",
                "draft": False, "prerelease": False,
                "body": "Release notes fictícias para testes sem avaliação humana.",
                # Extras da fixture jamais podem chegar ao CSV independente.
                "corretiva": "sim", "heuristica": "sim", "tipo_projeto": "outro",
            }
            for release in range(6)
        ]
    repos_csv = coleta / "repositorios_aprovados.csv"
    with repos_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repos[0]))
        writer.writeheader()
        writer.writerows(repos)
    releases_json = coleta / "releases.json"
    releases_json.write_text(json.dumps(releases), encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        'window:\n  start_date: "2023-10-01T00:00:00Z"\n'
        '  end_date: "2024-09-30T23:59:59Z"\n', encoding="utf-8",
    )
    proveniencia = {
        "schema_version": 1, "origem": "github_api", "modo_referencia": False,
        "fonte_candidatos": "github_search_api", "coletado_em": "2024-10-01T00:00:00Z",
        "janela": {"inicio": "2023-10-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"},
        "criterios": {"min_stars": 1000, "min_releases": 5, "min_workflow_runs": 50},
        "repositorios_sha256": sha256(repos_csv),
        "releases_sha256": sha256(releases_json),
    }
    (coleta / "proveniencia.json").write_text(json.dumps(proveniencia), encoding="utf-8")
    return config, coleta, tmp_path / "ouro", tmp_path / "rotulos_aulus.csv"


def argumentos(bundle):
    config, coleta, saida, rotulos = bundle
    return [
        "--config", str(config), "--coleta", str(coleta),
        "--saida", str(saida), "--rotulos", str(rotulos),
    ]


def gerador_proibido(*args, **kwargs):
    raise AssertionError("O preflight deve falhar antes de chamar o sorteio.")


def test_executa_bundle_e_preserva_cegamento(bundle_fixture):
    config, coleta, saida, rotulos = bundle_fixture
    resultado = fluxo.executar(config, coleta, saida, rotulos)
    manifesto = resultado["manifesto"]
    assert manifesto["n_populacao"] == 300
    assert manifesto["n_repositorios"] == 60
    assert manifesto["n_releases"] == 300
    assert manifesto["random_state"] == 42
    assert resultado["status"] == "aguardando_rotulagem_humana"
    assert (saida / "selecao.json").is_file()
    assert (saida / "evidencias_releases.json").is_file()
    comum, humano = ler_csv(saida / "amostra_comum.csv"), ler_csv(rotulos)
    validar_rotulos(comum, humano, permitir_vazios=True)
    assert all(row[campo] == "" for row in humano for campo in JULGAMENTOS)
    assert all(tuple(row) == METADADOS + JULGAMENTOS for row in humano)
    assert not (rotulos.parent / "rotulos_maria.csv").exists()
    assert not (rotulos.parent / "rotulos_vinicius.csv").exists()
    with pytest.raises(ValueError, match="Rótulo ausente"):
        validar_rotulos(comum, humano)


def test_cli_informa_pendencia_humana(bundle_fixture, capsys):
    assert fluxo.main(argumentos(bundle_fixture)) == 0
    saida = capsys.readouterr().out
    assert "random_state=42" in saida
    assert "rascunho validado" in saida
    assert "pendente de julgamento humano" in saida


def test_populacao_insuficiente_nao_gera_artefatos(bundle_fixture, capsys):
    _, coleta, saida, rotulos = bundle_fixture
    path = coleta / "repositorios_aprovados.csv"
    rows = ler_csv(path)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows[:100])
    assert fluxo.main(argumentos(bundle_fixture)) == 2
    erro = capsys.readouterr().err
    assert "100 repositórios" in erro and "300" in erro and "coleta real" in erro
    assert not saida.exists()
    assert not rotulos.exists()


def test_csv_humano_existente_bloqueia_antes_sorteio(bundle_fixture, monkeypatch):
    config, coleta, saida, rotulos = bundle_fixture
    rotulos.write_text("Julgamentos humanos existentes de Áulus.", encoding="utf-8")
    monkeypatch.setattr(fluxo, "gerar_amostra", gerador_proibido)
    with pytest.raises(FileExistsError, match="preservado"):
        fluxo.executar(config, coleta, saida, rotulos)
    assert rotulos.read_text(encoding="utf-8") == "Julgamentos humanos existentes de Áulus."
    assert not saida.exists()


def test_selecao_existente_preservada(bundle_fixture, monkeypatch):
    config, coleta, saida, rotulos = bundle_fixture
    saida.mkdir()
    comum = saida / "amostra_comum.csv"
    comum.write_text("Seleção existente, inclusive se execução anterior foi interrompida.")
    antes = comum.read_bytes()
    monkeypatch.setattr(fluxo, "gerar_amostra", gerador_proibido)
    with pytest.raises(FileExistsError, match="rotulagem.py"):
        fluxo.executar(config, coleta, saida, rotulos)
    assert comum.read_bytes() == antes
    assert not rotulos.exists()


def test_vinicius_protegido_antes_sorteio(bundle_fixture, monkeypatch):
    config, coleta, saida, rotulos = bundle_fixture
    vinicius = rotulos.with_name("rotulos_vinicius.csv")
    vinicius.write_text("Julgamentos existentes de Vinicius.", encoding="utf-8")
    monkeypatch.setattr(fluxo, "gerar_amostra", gerador_proibido)
    with pytest.raises(ValueError, match="rotulos_vinicius.csv"):
        fluxo.executar(config, coleta, saida, vinicius)
    assert vinicius.read_text(encoding="utf-8") == "Julgamentos existentes de Vinicius."
    assert not saida.exists()


@pytest.mark.parametrize("nome", ["amostra_comum.csv", "evidencias_releases.json", "selecao.json"])
def test_csv_humano_nao_pode_colidir_com_artefatos(bundle_fixture, monkeypatch, nome):
    config, coleta, saida, _ = bundle_fixture
    monkeypatch.setattr(fluxo, "gerar_amostra", gerador_proibido)
    with pytest.raises(ValueError, match="caminho diferente"):
        fluxo.executar(config, coleta, saida, saida / nome)
    assert not saida.exists()


def test_csv_humano_nao_pode_ser_ancestral_da_saida(bundle_fixture, monkeypatch):
    config, coleta, _, rotulos = bundle_fixture
    monkeypatch.setattr(fluxo, "gerar_amostra", gerador_proibido)
    with pytest.raises(ValueError, match="caminho diferente"):
        fluxo.executar(config, coleta, rotulos / "ouro", rotulos)
    assert not rotulos.exists()


def test_cria_parent_do_csv_depois_da_selecao(bundle_fixture):
    config, coleta, saida, rotulos = bundle_fixture
    destino = rotulos.parent / "novo" / "rotulos_aulus.csv"
    fluxo.executar(config, coleta, saida, destino)
    assert destino.is_file()
    validar_rotulos(ler_csv(saida / "amostra_comum.csv"), ler_csv(destino), permitir_vazios=True)


def test_bundle_ausente_informa_erro_sem_artefatos(bundle_fixture, capsys):
    _, coleta, saida, rotulos = bundle_fixture
    (coleta / "repositorios_aprovados.csv").unlink()
    assert fluxo.main(argumentos(bundle_fixture)) == 2
    erro = capsys.readouterr().err
    assert "repositorios_aprovados.csv" in erro and "300" in erro and "coleta real" in erro
    assert not saida.exists()
    assert not rotulos.exists()


def test_coleta_parcial_informa_quantidade_sem_criar_csv(bundle_fixture, capsys):
    _, coleta, saida, rotulos = bundle_fixture
    (coleta / "repositorios_aprovados.csv").unlink()
    (coleta / "estado.json").write_text(json.dumps({"n_aprovados": 0}), encoding="utf-8")
    assert fluxo.main(argumentos(bundle_fixture)) == 2
    assert "0 aprovados" in capsys.readouterr().err
    assert not saida.exists() and not rotulos.exists()


def test_falha_posterior_preserva_csv_criado_por_outra_execucao(bundle_fixture, monkeypatch):
    config, coleta, saida, rotulos = bundle_fixture
    gerar_original = fluxo.gerar_amostra

    def gerar_e_simular_concorrencia(*args):
        manifesto = gerar_original(*args)
        rotulos.write_text("Outro processo gravou decisões humanas.", encoding="utf-8")
        return manifesto

    monkeypatch.setattr(fluxo, "gerar_amostra", gerar_e_simular_concorrencia)
    with pytest.raises(FileExistsError):
        fluxo.executar(config, coleta, saida, rotulos)
    assert rotulos.read_text(encoding="utf-8") == "Outro processo gravou decisões humanas."
    assert (saida / "selecao.json").is_file()
    assert (saida / "amostra_comum.csv").is_file()


def test_reexecucao_nao_substitui_csv_nem_selecao(bundle_fixture):
    fluxo.executar(*bundle_fixture)
    _, _, saida, rotulos = bundle_fixture
    arquivos = [rotulos] + list(saida.iterdir())
    antes = {path: path.read_bytes() for path in arquivos}
    with pytest.raises(FileExistsError):
        fluxo.executar(*bundle_fixture)
    assert antes == {path: path.read_bytes() for path in arquivos}
