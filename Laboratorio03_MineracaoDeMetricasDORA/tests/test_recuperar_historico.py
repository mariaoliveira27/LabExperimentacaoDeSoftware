"""ZIPs artificiais verificam contratos; a CLI rejeita sua origem empírica."""

from copy import deepcopy
import hashlib
import json
import zipfile

import pytest

import recuperar_historico as historico
import coleta_amostra_real as coleta


@pytest.fixture
def arquivo_fixture(tmp_path):
    arquivo = tmp_path / "fixture.zip"
    config = tmp_path / "config.yaml"
    config.write_text('window:\n  start_date: "2023-10-01T00:00:00Z"\n  end_date: "2024-09-30T23:59:59Z"\n', encoding="utf-8")
    infos, payloads = {}, {}
    for indice, n_runs in enumerate((50, 49, 50)):
        nome = f"fixture/projeto-{indice}"
        info = {"id": indice + 1, "full_name": nome, "stargazers_count": 1500 if indice < 2 else 999,
                "default_branch": "main", "fork": False, "archived": False,
                "collected_at": "2025-01-18T12:00:00.123456", "created_at": "2020-01-01T00:00:00Z"}
        infos[nome] = info
        payloads[nome] = {"workflows": {}, "workflow_runs": {
            str(indice * 100 + run + 1): {
                "id": indice * 100 + run + 1, "workflow_id": 7, "event": "push",
                "head_branch": "main", "status": "completed", "conclusion": "success",
                "created_at": "2024-05-01T00:00:00Z", "run_started_at": "2024-05-01T00:00:00Z",
                "updated_at": "2024-05-01T00:01:00Z", "repository": {"id": indice + 1, "full_name": nome},
                "head_sha": "commit-original-da-fixture",
            } for run in range(n_runs)
        }}

    def escrever():
        with zipfile.ZipFile(arquivo, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
            for nome, info in infos.items():
                prefix = f"results/2024/2024-01-01T00:00:00-2025-01-01T00:00:00/gha_repos/{nome.replace('/', '_')}/"
                zip_out.writestr(prefix + "info.json", json.dumps(info))
                zip_out.writestr(prefix + "workflow_runs.json", json.dumps(payloads[nome]))
        return hashlib.md5(arquivo.read_bytes()).hexdigest()

    return arquivo, config, tmp_path / "historico", infos, payloads, escrever


def recuperar_fixture(fixture):
    arquivo, config, saida, _, _, escrever = fixture
    return historico._recuperar(arquivo, config, saida, md5_esperado=escrever())


def test_metadados_sem_arquivo_runs_preservam_ausencia_sem_inventar_zero(arquivo_fixture):
    arquivo, config, saida, _, _, escrever = arquivo_fixture
    escrever()
    with zipfile.ZipFile(arquivo) as original:
        entradas = [(item.filename, original.read(item)) for item in original.infolist()
                    if "fixture_projeto-0/workflow_runs.json" not in item.filename]
    with zipfile.ZipFile(arquivo, "w", compression=zipfile.ZIP_DEFLATED) as modificado:
        for nome, corpo in entradas:
            modificado.writestr(nome, corpo)
    manifesto = historico._recuperar(arquivo, config, saida,
                                    md5_esperado=hashlib.md5(arquivo.read_bytes()).hexdigest())
    assert manifesto["repositorios_sem_arquivo_runs"] == 1
    assert manifesto["repositorios_com_50_runs_observados"] == 0
    metadata = json.loads((saida / "metadata_repositorios.json").read_text(encoding="utf-8"))
    assert metadata[0]["status_fonte_runs"] == "arquivo_runs_ausente"
    assert metadata[0]["runs_validos_observados"] is None


@pytest.mark.parametrize("alteracao", [None, "runs", "metadata", "omissao"])
def test_loader_confere_derivacao_no_zip_mesmo_com_hash_export_recalculado(arquivo_fixture, monkeypatch, alteracao):
    """Mock só do checksum da fonte; objetos ainda são confrontados com o ZIP."""
    manifesto = recuperar_fixture(arquivo_fixture)
    arquivo, _, saida, _, _, _ = arquivo_fixture
    # Esta identidade empírica artificial é restrita à fixture e não passa
    # pelo MD5 real da CLI. O mock permite exercitar a comparação dos membros.
    manifesto.update(origem="arquivo_publico_zenodo", dados_empiricos=True,
                     source_doi=coleta.DOI_FONTE, source_url=coleta.URL_FONTE,
                     md5_esperado=coleta.MD5_FONTE, md5_verificado=coleta.MD5_FONTE)
    monkeypatch.setattr(coleta, "_hashes", lambda path: (coleta.MD5_FONTE, historico._hashes(path)[1]))
    if alteracao is not None:
        nome = "runs_historicos.json" if alteracao == "runs" else "metadata_repositorios.json"
        path = saida / nome
        dados = json.loads(path.read_text(encoding="utf-8"))
        if alteracao == "runs":
            dados["fixture/projeto-0"][0]["head_sha"] = "commit-inventado-no-export"
        elif alteracao == "metadata":
            dados[0]["stars"] += 1
        else:
            dados.pop()
            manifesto["repositorios_metadata"] -= 1
        path.write_text(json.dumps(dados), encoding="utf-8")
        manifesto["saidas_sha256"][nome] = coleta.sha256(path)
    (saida / "proveniencia_historico.json").write_text(json.dumps(manifesto), encoding="utf-8")
    inicio = coleta.instante("2023-10-01T00:00:00Z")
    fim = coleta.instante("2024-09-30T23:59:59Z")
    if alteracao is None:
        carregado = coleta._carregar_historico_zenodo(saida, inicio, fim)
        assert len(carregado.metadados_por_id) == 3 and len(carregado.runs_por_id[1]) == 50
    else:
        with pytest.raises(ValueError, match="conteúdo original do ZIP"):
            coleta._carregar_historico_zenodo(saida, inicio, fim)


def test_exporta_limite_inferior_com_proveniencia_sem_humanos(arquivo_fixture):
    manifesto = recuperar_fixture(arquivo_fixture)
    arquivo, _, saida, _, payloads, _ = arquivo_fixture
    assert manifesto["repositorios_metadata"] == 3
    assert manifesto["repositorios_snapshot_stars_ge1000"] == 2
    assert manifesto["repositorios_com_50_runs_observados"] == 1
    assert manifesto["runs_observados_exportados"] == 50
    assert manifesto["cobertura"] == "limite_inferior_observado"
    assert manifesto["historico_anual_completo"] is False
    assert manifesto["permite_metricas_dora_anuais"] is False
    assert manifesto["origem"] == "fixture_sintetica_de_teste"
    assert manifesto["dados_empiricos"] is False
    assert manifesto["source_doi"] is None
    assert manifesto["md5_verificado"] == hashlib.md5(arquivo.read_bytes()).hexdigest()
    dados = json.loads((saida / "runs_historicos.json").read_text(encoding="utf-8"))
    assert list(dados) == ["fixture/projeto-0"]
    assert dados["fixture/projeto-0"][0] == payloads["fixture/projeto-0"]["workflow_runs"]["1"]
    metadata = json.loads((saida / "metadata_repositorios.json").read_text(encoding="utf-8"))
    assert metadata[0]["data_coleta_original"] == "2025-01-18T12:00:00.123456"
    for nome, hash_esperado in manifesto["saidas_sha256"].items():
        assert hashlib.sha256((saida / nome).read_bytes()).hexdigest() == hash_esperado
    assert not (saida / "rotulos_aulus.csv").exists()


@pytest.mark.parametrize("campo,valor", [
    ("event", "pull_request"), ("head_branch", "develop"), ("status", "queued"),
    ("conclusion", "cancelled"), ("created_at", "2023-11-01T00:00:00Z"),
    ("created_at", "2024-10-01T00:00:00Z"),
])
def test_exclui_event_branch_status_conclusion_e_datas(arquivo_fixture, campo, valor):
    _, _, _, _, payloads, _ = arquivo_fixture
    run = deepcopy(payloads["fixture/projeto-0"]["workflow_runs"]["1"])
    run.update({campo: valor, "id": 9999})
    payloads["fixture/projeto-0"]["workflow_runs"]["9999"] = run
    assert recuperar_fixture(arquivo_fixture)["runs_observados_exportados"] == 50


@pytest.mark.parametrize("conclusao", ["failure", "timed_out", "startup_failure"])
def test_conclusoes_validas_incluem_falhas_reais(arquivo_fixture, conclusao):
    _, _, _, _, payloads, _ = arquivo_fixture
    payloads["fixture/projeto-0"]["workflow_runs"]["1"]["conclusion"] = conclusao
    assert recuperar_fixture(arquivo_fixture)["runs_observados_exportados"] == 50


@pytest.mark.parametrize("campo,valor", [
    ("created_at", "2024-05-01"), ("run_started_at", "data-inválida"),
    ("updated_at", "2024-04-30T23:59:00Z"), ("id", 0), ("workflow_id", None),
    ("repository", {"id": 9999, "full_name": "fixture/outro"}),
])
def test_identidade_e_timestamps_invalidos_nao_viram_elegibilidade(arquivo_fixture, campo, valor):
    _, _, saida, _, payloads, _ = arquivo_fixture
    payloads["fixture/projeto-0"]["workflow_runs"]["1"][campo] = valor
    with pytest.raises(ValueError):
        recuperar_fixture(arquivo_fixture)
    assert not saida.exists()


def test_run_duplicado_nao_inflaciona_contagem(arquivo_fixture):
    _, _, saida, _, payloads, _ = arquivo_fixture
    payloads["fixture/projeto-0"]["workflow_runs"]["duplicata"] = deepcopy(payloads["fixture/projeto-0"]["workflow_runs"]["1"])
    with pytest.raises(ValueError, match="duplicado"):
        recuperar_fixture(arquivo_fixture)
    assert not saida.exists()


@pytest.mark.parametrize("campo", ["fork", "archived"])
def test_flags_fork_e_archived_preservadas_sem_filtro_adicional(arquivo_fixture, campo):
    _, _, saida, infos, _, _ = arquivo_fixture
    infos["fixture/projeto-0"][campo] = True
    assert recuperar_fixture(arquivo_fixture)["repositorios_com_50_runs_observados"] == 1
    metadata = json.loads((saida / "metadata_repositorios.json").read_text(encoding="utf-8"))
    assert metadata[0][campo] is True


def test_destino_existente_preservado(arquivo_fixture):
    arquivo, config, saida, _, _, escrever = arquivo_fixture
    md5 = escrever()
    saida.mkdir()
    humano = saida / "rotulos_vinicius.csv"
    humano.write_text("Decisões humanas existentes.", encoding="utf-8")
    with pytest.raises(FileExistsError, match="preservado"):
        historico._recuperar(arquivo, config, saida, md5_esperado=md5)
    assert humano.read_text(encoding="utf-8") == "Decisões humanas existentes."


def test_zip_parcial_rejeitado_antes_de_criar_saida(arquivo_fixture):
    arquivo, config, saida, _, _, escrever = arquivo_fixture
    md5 = escrever()
    arquivo.write_bytes(arquivo.read_bytes()[:-20])
    with pytest.raises(ValueError, match="MD5 não confere"):
        historico._recuperar(arquivo, config, saida, md5_esperado=md5)
    assert not saida.exists()


def test_cli_nao_aceita_fixture_como_fonte_real(arquivo_fixture, capsys):
    arquivo, config, saida, _, _, escrever = arquivo_fixture
    escrever()
    assert historico.main(["--arquivo", str(arquivo), "--config", str(config), "--saida", str(saida)]) == 2
    assert "MD5 não confere" in capsys.readouterr().err
    assert not saida.exists()


def test_cli_nao_oferece_override_de_checksum(arquivo_fixture):
    arquivo, _, _, _, _, escrever = arquivo_fixture
    with pytest.raises(SystemExit) as exc:
        historico.main(["--arquivo", str(arquivo), "--md5", escrever()])
    assert exc.value.code == 2


def test_janela_fora_da_cobertura_rejeitada(arquivo_fixture):
    _, config, saida, _, _, _ = arquivo_fixture
    config.write_text('window:\n  start_date: "2022-01-01T00:00:00Z"\n  end_date: "2022-12-31T23:59:59Z"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="não intersecta"):
        recuperar_fixture(arquivo_fixture)
    assert not saida.exists()
