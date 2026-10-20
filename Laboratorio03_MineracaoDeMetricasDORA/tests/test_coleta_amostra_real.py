"""Coleta integrada com HTTP simulado exclusivamente em fixtures."""

import copy
import csv
import json
import sqlite3
from pathlib import Path

import pytest

import coleta_amostra_real as coleta
from executar_amostra_ouro import executar


class APIPlanejada:
    def __init__(self, quantidade=3, *, runs=50, releases=5, actions=True):
        self.chamadas = []
        self.quantidade = quantidade
        self.n_runs, self.n_releases, self.actions = runs, releases, actions
        self.candidatos = [dict(id=i + 1, full_name=f"fixture/projeto-{i:03d}", private=False,
                                stargazers_count=2000, created_at="2020-01-01T00:00:00Z", default_branch="main")
                           for i in range(quantidade)]

    def request(self, endpoint, params=None, **kwargs):
        self.chamadas.append((endpoint, params))
        nome = endpoint.removeprefix("/repos/").split("/actions/")[0]
        metadata = next(item for item in self.candidatos if item["full_name"] == nome)
        if endpoint.endswith("/actions/workflows"):
            workflows = [dict(id=1, name="Build", path=".github/workflows/build.yml", state="active")] if self.actions else []
            return 200, {"total_count": int(self.actions), "workflows": workflows}, {}
        if endpoint.endswith("/actions/runs"):
            owner, repo = nome.split("/")
            runs = self.runs_completos(owner, repo, metadata["default_branch"], None, None)[:1]
            return 200, {"total_count": self.n_runs, "workflow_runs": runs}, {}
        return 200, copy.deepcopy(metadata), {}

    def paginate(self, endpoint, params=None):
        self.chamadas.append((endpoint, params))
        nome = endpoint.removeprefix("/repos/").removesuffix("/releases")
        i = next(item["id"] for item in self.candidatos if item["full_name"] == nome)
        return [dict(id=i * 1000 + j, tag_name=f"v1.0.{j}", published_at=f"2024-01-{j:02d}T00:00:00Z",
                     html_url=f"https://github.com/{nome}/releases/tag/v1.0.{j}", draft=False, prerelease=False,
                     body="Conteúdo artificial de fixture, não observação humana.") for j in range(1, self.n_releases + 1)]

    def runs_completos(self, owner, repo, branch, inicio, fim):
        return [dict(id=j + 1, workflow_id=1, event="push", head_branch=branch, conclusion="success",
                     created_at="2024-01-01T00:00:00Z", run_started_at="2024-01-01T00:00:00Z",
                     updated_at="2024-01-01T00:01:00Z") for j in range(self.n_runs)]


@pytest.fixture
def preparar(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text('window:\n  start_date: "2023-10-01T00:00:00Z"\n  end_date: "2024-09-30T23:59:59Z"\ncriteria:\n  min_stars: 1000\n  min_releases: 5\n  min_workflow_runs: 50\n', encoding="utf-8")

    def vincular(api):
        monkeypatch.setattr(coleta, "buscar_candidatos", lambda *args, **kwargs: api.candidatos)
        monkeypatch.setattr(coleta.ColetorRuns, "coletar_runs_janela", lambda self, *args: api.runs_completos(*args))
        return config, tmp_path / "coleta", api

    return vincular


def test_300_aprovados_exporta_contrato_e_prepara_rotulagem(preparar, tmp_path):
    config, destino, api = preparar(APIPlanejada(300))
    estado = coleta.coletar(config, destino, client=api)
    assert estado["status"] == "completa"
    assert estado["n_aprovados"] == 300
    assert estado["n_processados"] == 300
    rows = coleta.ler_aprovados(destino / "repositorios_aprovados.csv")
    assert len(rows) == 300 and all(row["origem_coleta"] == "github_api" for row in rows)
    assert all(int(row["total_runs_janela"]) == 50 for row in rows)
    manifesto = json.loads((destino / "proveniencia.json").read_text(encoding="utf-8"))
    assert manifesto["modo_referencia"] is False
    assert manifesto["repositorios_sha256"] == coleta.sha256(destino / "repositorios_aprovados.csv")
    assert len(manifesto["evidencias"]) == 300
    hashes_antes = {path.name: coleta.sha256(path) for path in destino.iterdir() if path.is_file()}
    auditoria = coleta.auditar_bundle_final(destino, config)
    assert auditoria["somente_leitura"] is True and auditoria["n_aprovados"] == 300
    assert hashes_antes == {path.name: coleta.sha256(path) for path in destino.iterdir() if path.is_file()}
    primeiras = json.loads((destino / "primeiros_100_aprovados.json").read_text(encoding="utf-8"))
    assert primeiras["completo"] is True and primeiras["n_comprovados"] == 100
    assert [item["candidate_id"] for item in primeiras["repositorios"]] == list(range(1, 101))
    assert primeiras["repositorios"][0]["sha256"] == coleta.sha256(destino / "qualificacoes/1.json")
    executar(config, destino, tmp_path / "ouro", tmp_path / "rotulos_aulus.csv")
    with (tmp_path / "rotulos_aulus.csv").open(encoding="utf-8", newline="") as stream:
        rotulos = list(csv.DictReader(stream))
    assert len(rotulos) == 300
    assert all(row["tipo_projeto"] == row["entrega_real"] == row["corretiva"] == "" for row in rotulos)
    chamadas = len(api.chamadas)
    assert coleta.coletar(config, destino, client=api)["status"] == "completa"
    assert len(api.chamadas) == chamadas


@pytest.mark.parametrize("persistente", [False, True])
def test_checkpoint_windows_preserva_atomicidade_em_bloqueio_temporario(tmp_path, monkeypatch, persistente):
    destino = tmp_path / "estado.json"
    destino.write_text('{"anterior": true}', encoding="utf-8")
    substituir = Path.replace
    chamadas = []

    def bloqueado(temporario, alvo):
        chamadas.append(alvo)
        if persistente or len(chamadas) < 3:
            erro = PermissionError("arquivo temporariamente aberto")
            erro.winerror = 32
            raise erro
        return substituir(temporario, alvo)

    monkeypatch.setattr(Path, "replace", bloqueado)
    monkeypatch.setattr(coleta.time, "sleep", lambda atraso: None)
    if persistente:
        with pytest.raises(PermissionError):
            coleta._json_atomic(destino, {"novo": True})
        assert json.loads(destino.read_text()) == {"anterior": True}
        assert len(chamadas) == 7
    else:
        coleta._json_atomic(destino, {"novo": True})
        assert json.loads(destino.read_text()) == {"novo": True}
        assert len(chamadas) == 3


@pytest.mark.parametrize("alteracoes,motivo", [
    ({"actions": False}, "evidencia_actions_historicos_insuficiente"),
    ({"releases": 4}, "menos_de_5_releases_na_janela"),
    ({"runs": 0}, "evidencia_runs_historicos_insuficiente"),
])
def test_insuficiente_so_publica_parciais_e_descartes(preparar, alteracoes, motivo):
    config, destino, api = preparar(APIPlanejada(3, **alteracoes))
    estado = coleta.coletar(config, destino, client=api)
    assert estado["status"] == "insuficiente" and estado["n_aprovados"] == 0
    primeiras = json.loads((destino / "primeiros_100_aprovados.json").read_text(encoding="utf-8"))
    assert primeiras["completo"] is False and primeiras["n_comprovados"] == 0
    with pytest.raises(ValueError, match="Bundle final ausente/incompleto"):
        coleta.auditar_bundle_final(destino, config)
    assert not (destino / "repositorios_aprovados.csv").exists()
    assert not (destino / "releases.json").exists()
    assert not (destino / "proveniencia.json").exists()
    assert motivo in (destino / "descartes.csv").read_text(encoding="utf-8")


def test_resumo_nao_substitui_contagem_dos_runs_validos(preparar):
    config, destino, api = preparar(APIPlanejada())
    def runs_invalidos(*args):
        rows = APIPlanejada.runs_completos(api, *args)
        for row in rows:
            row["conclusion"] = "cancelled"
        return rows
    api.runs_completos = runs_invalidos
    estado = coleta.coletar(config, destino, client=api)
    assert estado["n_aprovados"] == 0
    assert "evidencia_runs_validos_insuficiente" in (destino / "descartes.csv").read_text(encoding="utf-8")


def test_interrupcao_de_api_nao_vira_descarte_e_retoma(preparar):
    config, destino, api = preparar(APIPlanejada(runs=0))
    normal = api.request
    def falhar(endpoint, params=None, **kwargs):
        if endpoint == "/repos/fixture/projeto-001":
            raise RuntimeError("Falha HTTP de fixture")
        return normal(endpoint, params, **kwargs)
    api.request = falhar
    with pytest.raises(RuntimeError, match="Falha HTTP"):
        coleta.coletar(config, destino, client=api)
    estado = json.loads((destino / "estado.json").read_text(encoding="utf-8"))
    assert estado["status"] == "interrompida" and estado["n_processados"] == 1
    api.request = normal
    api.chamadas.clear()
    estado = coleta.coletar(config, destino, client=api)
    assert estado["status"] == "insuficiente" and estado["n_processados"] == 3
    assert not any(endpoint == "/repos/fixture/projeto-000" for endpoint, _ in api.chamadas)


def test_snapshot_adulterado_bloqueia_retomada(preparar):
    config, destino, api = preparar(APIPlanejada(runs=0))
    coleta.coletar(config, destino, client=api)
    path = destino / "qualificacoes/1.json"
    item = json.loads(path.read_text(encoding="utf-8"))
    item["aprovado"] = True
    path.write_text(json.dumps(item), encoding="utf-8")
    with pytest.raises(ValueError, match="alterado"):
        coleta.coletar(config, destino, client=api)


def test_mudanca_janela_nao_reutiliza_cache_como_mesmo_estudo(preparar):
    config, destino, api = preparar(APIPlanejada())
    coleta.coletar(config, destino, client=api)
    config.write_text(config.read_text(encoding="utf-8").replace("2023-10-01", "2023-11-01"), encoding="utf-8")
    with pytest.raises(ValueError, match="mudou"):
        coleta.coletar(config, destino, client=api)


def test_rejeita_destino_existente_e_alvo_simulado(preparar, tmp_path):
    config, destino, api = preparar(APIPlanejada())
    destino.mkdir()
    protegido = destino / "repositorios_aprovados.csv"
    protegido.write_text("arquivo existente", encoding="utf-8")
    with pytest.raises(FileExistsError):
        coleta.coletar(config, destino, client=api)
    assert protegido.read_text(encoding="utf-8") == "arquivo existente"
    with pytest.raises(ValueError, match="inferior a 300"):
        coleta.coletar(config, tmp_path / "outro", alvo=100, client=api)


def test_cli_insuficiente_mensagem_clara(preparar, monkeypatch, capsys):
    config, destino, api = preparar(APIPlanejada(runs=0))
    monkeypatch.setattr(coleta, "ClienteAuditavel", lambda *args, **kwargs: api)
    assert coleta.main(["--config", str(config), "--saida", str(destino)]) == 2
    mensagem = capsys.readouterr().err
    assert "0/300" in mensagem and "Nenhuma amostra-ouro" in mensagem


def test_gh_token_nao_aparece_em_stdout(monkeypatch, capsys):
    class Resultado:
        returncode = 0
        stdout = "segredo-ficticio-exclusivo-da-fixture\n"
    monkeypatch.setattr(coleta.subprocess, "run", lambda *args, **kwargs: Resultado())
    assert coleta.token_gh() == "segredo-ficticio-exclusivo-da-fixture"
    assert "segredo" not in capsys.readouterr().out


@pytest.mark.parametrize("falha", ["release_id", "release_tag", "release_link", "workflows", "resumo_runs"])
def test_schema_malformado_interrompe_antes_de_registrar_descarte(preparar, falha):
    config, destino, api = preparar(APIPlanejada(releases=4 if falha.startswith("release") else 5))
    request, paginate = api.request, api.paginate

    def resposta(endpoint, params=None, **kwargs):
        status, payload, headers = request(endpoint, params, **kwargs)
        if falha == "workflows" and endpoint.endswith("/actions/workflows"):
            payload["workflows"] = []
        elif falha == "resumo_runs" and endpoint.endswith("/actions/runs"):
            payload["workflow_runs"] = []
        return status, payload, headers

    def releases(endpoint, params=None):
        rows = paginate(endpoint, params)
        if falha.startswith("release"):
            campo = {"release_id": "id", "release_tag": "tag_name", "release_link": "html_url"}[falha]
            rows[0].pop(campo)
        return rows

    api.request, api.paginate = resposta, releases
    with pytest.raises((ValueError, RuntimeError)):
        coleta.coletar(config, destino, client=api)
    estado = json.loads((destino / "estado.json").read_text(encoding="utf-8"))
    assert estado["status"] == "interrompida" and estado["n_processados"] == 0
    with (destino / "descartes.csv").open(encoding="utf-8", newline="") as stream:
        assert list(csv.DictReader(stream)) == []
    assert not (destino / "repositorios_aprovados.csv").exists()


def test_contrato_final_repara_estado_e_verifica_evidencias(preparar):
    config, destino, api = preparar(APIPlanejada(300))
    request = api.request

    def auditavel(endpoint, params=None, **kwargs):
        resposta = request(endpoint, params, **kwargs)
        # Registro explicitamente artificial, restrito à fixture.
        with (destino / "requisicoes.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"fixture": True, "endpoint": endpoint, "params": params}) + "\n")
        return resposta

    api.request = auditavel
    coleta.coletar(config, destino, client=api)
    finais = [destino / nome for nome in ("repositorios_aprovados.csv", "releases.json", "proveniencia.json")]
    hashes = [coleta.sha256(path) for path in finais]
    path_estado = destino / "estado.json"
    estado = json.loads(path_estado.read_text(encoding="utf-8"))
    # Simula interrupção depois dos três arquivos finais, antes do checkpoint.
    estado.update(status="interrompida", erro="Interrupção simulada exclusiva de fixture")
    path_estado.write_text(json.dumps(estado), encoding="utf-8")
    api.chamadas.clear()
    assert coleta.coletar(config, destino, client=api)["status"] == "completa"
    assert api.chamadas == []
    assert [coleta.sha256(path) for path in finais] == hashes

    snapshot = destino / "qualificacoes/1.json"
    original = snapshot.read_bytes()
    snapshot.write_text("snapshot adulterado na fixture", encoding="utf-8")
    with pytest.raises(ValueError, match="Snapshot.*alterado"):
        coleta.coletar(config, destino, client=api)
    snapshot.write_bytes(original)

    requisicoes = destino / "requisicoes.jsonl"
    original_requisicoes = requisicoes.read_bytes()
    requisicoes.write_text("registro adulterado na fixture", encoding="utf-8")
    with pytest.raises(ValueError, match="Registro de requisições alterado"):
        coleta.coletar(config, destino, client=api)
    requisicoes.write_bytes(original_requisicoes)
    with pytest.raises(ValueError, match="final já publicada"):
        coleta.coletar(config, destino, client=api, reavaliar=True)
    assert [coleta.sha256(path) for path in finais] == hashes


def test_importacao_historica_e_idempotente_na_retomada(preparar, tmp_path):
    config, destino, api = preparar(APIPlanejada(runs=0))
    historico = tmp_path / "historico.sqlite"
    conn = sqlite3.connect(historico)
    conn.execute("CREATE TABLE fixture (valor INTEGER)")
    conn.execute("INSERT INTO fixture VALUES (7)")
    conn.commit()
    conn.close()
    argumentos = dict(client=api, cache_historico=historico)
    primeiro = coleta.coletar(config, destino, **argumentos)
    registro = (destino / "cache_historico_importado.json").read_bytes()
    cache = destino / "cache/github_cache.db"
    original_cache = cache.read_bytes()
    api.chamadas.clear()
    segundo = coleta.coletar(config, destino, **argumentos)
    assert primeiro["n_processados"] == segundo["n_processados"] == 3
    assert api.chamadas == []
    assert (destino / "cache_historico_importado.json").read_bytes() == registro
    assert cache.read_bytes() == original_cache
    assert coleta.sha256(historico) == json.loads(registro)["sha256"]


def test_reavaliar_preserva_originais_e_repete_filtros(preparar):
    config, destino, api = preparar(APIPlanejada(runs=0))
    coleta.coletar(config, destino, client=api)
    snapshot = destino / "qualificacoes/1.json"
    original = snapshot.read_bytes()
    api.n_runs = 50
    # Sem flag, a retomada conserva a qualificação anteriormente concluída.
    assert coleta.coletar(config, destino, client=api)["n_aprovados"] == 0
    estado = coleta.coletar(config, destino, client=api, reavaliar=True)
    assert estado["n_aprovados"] == 3 and estado["status"] == "insuficiente"
    preservados = list((destino / "reavaliacoes").glob("*/1.json"))
    assert len(preservados) == 1 and preservados[0].read_bytes() == original
    assert json.loads(snapshot.read_text(encoding="utf-8"))["aprovado"] is True
    assert not (destino / "repositorios_aprovados.csv").exists()
    assert not (destino / "proveniencia.json").exists()


def test_funil_nao_interpreta_zero_runs_retidos_como_ausencia_historica(preparar):
    config, destino, api = preparar(APIPlanejada(runs=0))
    coleta.coletar(config, destino, client=api)
    tabela = (destino / "funil_selecao.md").read_text(encoding="utf-8")
    assert "evidencia_runs_historicos_insuficiente" in tabela
    assert "menos_de_50_runs_na_janela" not in tabela
    snapshot = json.loads((destino / "qualificacoes/1.json").read_text(encoding="utf-8"))
    assert snapshot["runs_disponiveis_api"] == 0
    assert snapshot["escopo_contagem_runs"] == "registros_retidos_api"
    assert "limite_superior_runs" not in snapshot


def historico_fixture(api):
    """Fonte artificial isolada por mock do loader, nunca aceita pela CLI real."""
    metadados, runs = {}, {}
    for repo in api.candidatos:
        identificador, nome = repo["id"], repo["full_name"]
        metadados[identificador] = dict(repository_id=identificador, full_name=nome, default_branch="main",
                                       arquivo_runs=f"fixture/{identificador}/workflow_runs.json")
        observadas = APIPlanejada(runs=50).runs_completos("fixture", "projeto", "main", None, None)
        for run in observadas:
            run.update(id=identificador * 1000 + run["id"], status="completed",
                       repository={"id": identificador, "full_name": nome})
        runs[identificador] = observadas
    return coleta.HistoricoZenodo(metadados, runs, {
        "source_doi": "fixture-exclusiva-de-teste", "source_url": "https://example.invalid/fixture.zip",
        "arquivo_sha256": "0" * 64, "saidas_sha256": {"runs_historicos.json": "1" * 64},
        "dados_empiricos": False, "historico_anual_completo": False, "permite_metricas_dora_anuais": False,
    })


def test_historico_comprova_minimo_e_preserva_runs_originais_sem_metricas_anuais(preparar, monkeypatch):
    config, destino, api = preparar(APIPlanejada(300, runs=0, actions=False))
    historico = historico_fixture(api)
    monkeypatch.setattr(coleta, "_carregar_historico_zenodo", lambda *args: historico)
    estado = coleta.coletar(config, destino, client=api, historico_zenodo="mock-exclusivo-da-fixture")
    assert estado["n_aprovados"] == 300 and estado["status"] == "completa"
    assert not any(endpoint.endswith("/actions/runs") for endpoint, _ in api.chamadas)
    item = json.loads((destino / "qualificacoes/1.json").read_text(encoding="utf-8"))
    assert item["runs"] == historico.runs_por_id[1]
    assert item["workflows_atuais"]["total_count"] == 0
    assert item["fonte_runs"]["historico_anual_completo"] is False
    assert item["fonte_runs"]["permite_metricas_dora_anuais"] is False
    assert item["registro"]["escopo_contagem_runs"] == "limite_inferior_arquivo_historico"
    assert "cfr_ci" not in item["registro"]
    assert coleta.coletar(config, destino, client=api, historico_zenodo="mock-exclusivo-da-fixture")["status"] == "completa"

    # Recalcular hashes não permite substituir as observações originais da fonte.
    item["runs"][0]["conclusion"] = "failure"
    snapshot = destino / "qualificacoes/1.json"
    snapshot.write_text(json.dumps(item), encoding="utf-8")
    hash_novo = coleta.sha256(snapshot)
    proveniencia_path = destino / "proveniencia.json"
    proveniencia = json.loads(proveniencia_path.read_text(encoding="utf-8"))
    next(e for e in proveniencia["evidencias"] if e["arquivo"] == "qualificacoes/1.json")["sha256"] = hash_novo
    proveniencia_path.write_text(json.dumps(proveniencia), encoding="utf-8")
    estado_path = destino / "estado.json"
    estado["snapshots"]["1.json"] = hash_novo
    estado_path.write_text(json.dumps(estado), encoding="utf-8")
    with pytest.raises(ValueError, match="diverge da fonte histórica"):
        coleta.coletar(config, destino, client=api, historico_zenodo="mock-exclusivo-da-fixture")


def test_fonte_historica_adicionada_exige_reavaliacao_preservada(preparar, monkeypatch):
    config, destino, api = preparar(APIPlanejada(runs=0))
    coleta.coletar(config, destino, client=api)
    assinatura_original = (destino / "config_coleta.json").read_bytes()
    snapshot_original = (destino / "qualificacoes/1.json").read_bytes()
    historico = historico_fixture(api)
    monkeypatch.setattr(coleta, "_carregar_historico_zenodo", lambda *args: historico)
    with pytest.raises(ValueError, match="--reavaliar"):
        coleta.coletar(config, destino, client=api, historico_zenodo="fixture")
    assert (destino / "config_coleta.json").read_bytes() == assinatura_original
    estado = coleta.coletar(config, destino, client=api, historico_zenodo="fixture", reavaliar=True)
    assert estado["n_aprovados"] == 3
    arquivo = next((destino / "reavaliacoes").iterdir())
    assert (arquivo / "config_coleta.json").read_bytes() == assinatura_original
    assert (arquivo / "1.json").read_bytes() == snapshot_original
    historico.referencia["arquivo_sha256"] = "2" * 64
    with pytest.raises(ValueError, match="Fonte histórica mudou"):
        coleta.coletar(config, destino, client=api, historico_zenodo="fixture")


def test_reavaliacao_interrompida_nao_reutiliza_qualificacoes_com_fonte_antiga(preparar, monkeypatch):
    config, destino, api = preparar(APIPlanejada(runs=0))
    coleta.coletar(config, destino, client=api)
    historico = historico_fixture(api)
    monkeypatch.setattr(coleta, "_carregar_historico_zenodo", lambda *args: historico)
    checkpoint = coleta._checkpoint

    def interromper(*args, **kwargs):
        raise RuntimeError("Falha de fixture entre assinatura e checkpoint")

    monkeypatch.setattr(coleta, "_checkpoint", interromper)
    with pytest.raises(RuntimeError, match="entre assinatura"):
        coleta.coletar(config, destino, client=api, historico_zenodo="fixture", reavaliar=True)
    api.chamadas.clear()
    monkeypatch.setattr(coleta, "_checkpoint", checkpoint)
    with pytest.raises(ValueError, match="Assinatura do checkpoint"):
        coleta.coletar(config, destino, client=api, historico_zenodo="fixture")
    assert api.chamadas == []
    assert coleta.coletar(config, destino, client=api, historico_zenodo="fixture", reavaliar=True)["n_aprovados"] == 3


def test_historico_liga_nome_antigo_por_id_e_revalida_branch_atual(preparar, monkeypatch):
    config, destino, api = preparar(APIPlanejada(1, runs=0))
    historico = historico_fixture(api)
    original = historico.metadados_por_id[1]
    original["full_name"] = "fixture/nome-antigo"
    for run in historico.runs_por_id[1]:
        run["repository"]["full_name"] = original["full_name"]
    monkeypatch.setattr(coleta, "_carregar_historico_zenodo", lambda *args: historico)
    assert coleta.coletar(config, destino, client=api, historico_zenodo="fixture")["n_aprovados"] == 1
    api.candidatos[0]["default_branch"] = "develop"
    assert coleta.coletar(config, destino, client=api, historico_zenodo="fixture", reavaliar=True)["n_aprovados"] == 0


def test_metadados_atuais_nao_vem_de_cache_historico(tmp_path, monkeypatch):
    api = APIPlanejada(1)
    antigo = copy.deepcopy(api.candidatos[0])
    atual = {**antigo, "default_branch": "develop"}
    client = coleta.GitHubClient(token="token-artificial-de-fixture", cache_db_path=str(tmp_path / "cache.db"))
    endpoint = f"/repos/{antigo['full_name']}"
    url = client._url(endpoint)
    chave = client._get_cache_key(url, None)
    client._save_to_cache(chave, url, 200, antigo, {})
    chamadas = []

    class Resposta:
        status_code = 200
        headers = {}
        def json(self): return atual

    def http(*args, **kwargs):
        chamadas.append(args[0])
        return Resposta()

    monkeypatch.setattr(client.session, "get", http)
    metadata = coleta._metadata(client, antigo, coleta.instante("2024-09-30T23:59:59Z"))
    assert chamadas == [url] and metadata["default_branch"] == "develop"
    assert coleta._runs_do_arquivo(historico_fixture(api), metadata,
                                  coleta.instante("2023-10-01T00:00:00Z"),
                                  coleta.instante("2024-09-30T23:59:59Z")) == []
    assert client._read_from_cache(chave)[1] == antigo  # Fonte importada preservada.


@pytest.mark.parametrize("alteracao,erro", [
    ({"dados_empiricos": False}, "origem empírica"),
    ({"md5_verificado": "0" * 32}, "origem empírica"),
    ({"historico_anual_completo": True}, "limite inferior"),
    ({"janela_estudo": {"inicio": "2024-01-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"}}, "Janela"),
    ({}, "MD5/SHA-256"),
])
def test_loader_historico_rejeita_fixture_janela_alterada_e_zip_invalido(preparar, tmp_path, alteracao, erro):
    config, destino, api = preparar(APIPlanejada())
    fonte = tmp_path / "fonte_artificial.zip"
    fonte.write_bytes(b"Conteudo exclusivo de fixture, sem observacoes empiricas.")
    historico = tmp_path / "historico"
    historico.mkdir()
    manifesto = {
        "schema_version": 1, "origem": "arquivo_publico_zenodo", "dados_empiricos": True,
        "source_doi": coleta.DOI_FONTE, "source_url": coleta.URL_FONTE,
        "md5_esperado": coleta.MD5_FONTE, "md5_verificado": coleta.MD5_FONTE,
        "cobertura": "limite_inferior_observado", "historico_anual_completo": False,
        "permite_metricas_dora_anuais": False,
        "janela_estudo": {"inicio": "2023-10-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"},
        "janela_fonte": {"inicio": coleta.INICIO_FONTE, "fim": coleta.FIM_FONTE},
        "intervalo_observado": {"inicio": "2024-01-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"},
        "arquivo_fonte": str(fonte), "arquivo_tamanho": fonte.stat().st_size, "arquivo_sha256": "0" * 64,
    }
    manifesto.update(alteracao)
    (historico / "proveniencia_historico.json").write_text(json.dumps(manifesto), encoding="utf-8")
    with pytest.raises(ValueError, match=erro):
        coleta.coletar(config, destino, client=api, historico_zenodo=historico)
    assert not destino.exists() and not api.chamadas
