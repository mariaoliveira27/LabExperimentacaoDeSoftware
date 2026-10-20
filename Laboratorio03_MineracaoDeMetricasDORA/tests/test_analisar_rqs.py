"""Fixtures artificiais só em tmp_path; nunca constituem resultados do artigo."""

import copy
import csv
import json
import xml.etree.ElementTree as ET

import pytest

import analisar_rqs as analise
import coleta_amostra_real as coleta


def salvar(path, valor):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    return {"arquivo": path.name, "sha256": analise.sha256(path)}


@pytest.fixture
def dataset(tmp_path):
    nome = "fixture/projeto"
    datas = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-09-29"]
    releases = [dict(id=i + 1, tag_name=f"v1.0.{i}", published_at=f"{data}T00:00:00Z",
                     draft=False, prerelease=False, body="Conteúdo artificial exclusivo de teste.",
                     html_url=f"https://github.com/{nome}/releases/tag/v1.0.{i}")
                for i, data in enumerate(datas)]
    def run(i, conclusao, inicio, fim=None):
        return dict(id=i, workflow_id=10, event="push", head_branch="main", conclusion=conclusao,
                    created_at=inicio, run_started_at=inicio, updated_at=fim or inicio)
    runs = [run(1, "success", "2024-01-01T00:00:00Z"),
            run(2, "failure", "2024-01-01T01:00:00Z"),
            run(3, "success", "2024-01-01T03:00:00Z", "2024-01-01T03:30:00Z"),
            run(4, "failure", "2024-09-30T20:00:00Z")]
    fonte = tmp_path / "arquivo_anual_fixture.txt"
    fonte.write_text("Esta fonte artificial existe somente no teste; não é uma coleta.", encoding="utf-8")
    cobertura = dict(schema_version=1, completa=True, historico_anual_completo=True,
                     permite_metricas_dora_anuais=True,
                     janela={"inicio": "2023-10-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"},
                     event="push", default_branch="main", fonte="exportacao_anual_original",
                     evidencias=[dict(arquivo=fonte.name, sha256=analise.sha256(fonte))])
    repo = dict(full_name=nome, default_branch="main", total_runs_janela=4)
    return analise.Dataset(tmp_path, [repo], {nome: releases},
                           {nome: dict(registro=repo, releases=releases, runs=runs, cobertura_runs=cobertura)},
                           analise.instante("2023-10-01T00:00:00Z"), analise.instante("2024-09-30T23:59:59Z"),
                           52.14, {"repositorios_aprovados.csv": "a" * 64, "releases.json": "b" * 64})


def comparacoes_puras(dataset):
    nome = dataset.aprovados[0]["full_name"]
    entradas = {}
    for i, rel in enumerate(dataset.releases[nome]):
        if i == 0:
            entradas[nome, str(rel["id"])] = dict(status="sem_predecessora", commits=[], motivo="primeira_release")
        else:
            data = analise.instante(rel["published_at"])
            from datetime import timedelta
            entradas[nome, str(rel["id"])] = dict(status="completa", commits=[
                {"author_date": data - timedelta(days=1), "message": "fix: regression (fixture)"}], motivo="")
    return entradas


def test_quartis_incluem_zero_e_contam_ausentes():
    resultado = analise.resumir([0, 1, 2, 9, None])
    assert resultado == dict(n_total=5, n_validos=4, n_ausentes=1, n_censurados=0,
                             mediana=1.5, q1=.75, q3=3.75, iqr=3)
    assert analise.resumir([0])["mediana"] == 0
    assert analise.resumir([None])["mediana"] is None
    assert analise.resumir([])["iqr"] is None


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), "1"])
def test_quartis_recusam_valores_invalidos(valor):
    with pytest.raises((ValueError, TypeError)):
        analise.resumir([valor])


def test_variantes_reutilizam_metricas_reais_e_separam_censurados(dataset):
    rows, sumarios, faltas, episodios = analise.calcular_dataset(dataset, comparacoes_puras(dataset))
    row = rows[0]
    assert row["deployment_frequency_semana"] == pytest.approx(5 / 52.14)
    assert row["lead_time_release_mediana_dias"] == row["lead_time_commit_mediana_dias"] == 1
    assert row["releases_lead_time_avaliadas"] == row["commits_lead_time_avaliados"] == 4
    assert row["releases_lead_time_ausentes"] == 1
    assert row["cfr_ci_proxy"] == .5
    assert row["cfr_releases_proxy_v3"] == .75
    assert row["releases_cfr_avaliadas"] == 4 and row["releases_cfr_censuradas"] == 1
    assert row["tempo_recuperacao_mediana_horas"] == 2.5
    assert row["episodios_recuperados"] == row["episodios_censurados"] == 1
    assert row["proporcao_episodios_censurados"] == .5
    assert episodios == [dict(full_name="fixture/projeto", indice_resultado=1, estado="recuperado", duracao_horas=2.5),
                         dict(full_name="fixture/projeto", indice_resultado=1, estado="censurado", duracao_horas=None)]
    pooled = sumarios[-1]
    assert (pooled["n_total"], pooled["n_validos"], pooled["n_ausentes"], pooled["n_censurados"]) == (2, 1, 0, 1)
    assert pooled["mediana"] == 2.5
    assert len(faltas) == 1 and faltas[0]["release_id"] == 1


def test_variantes_lead_time_tem_denominadores_distintos(dataset):
    from datetime import timedelta
    comparacoes = comparacoes_puras(dataset)
    for i, rel in enumerate(dataset.releases["fixture/projeto"]):
        if i:
            data = analise.instante(rel["published_at"])
            comparacoes["fixture/projeto", str(rel["id"])]["commits"] = [
                {"author_date": data - timedelta(days=dias), "message": "Commit de fixture"}
                for dias in (9, 1, 1)]
    rows, _, _, _ = analise.calcular_dataset(dataset, comparacoes)
    assert rows[0]["lead_time_release_mediana_dias"] == 9
    assert rows[0]["lead_time_commit_mediana_dias"] == 1
    assert rows[0]["commits_lead_time_avaliados"] == 12


def test_cfr_releases_totalmente_censurado_preserva_n_sem_zero(dataset):
    for i, rel in enumerate(dataset.releases["fixture/projeto"]):
        rel["published_at"] = f"2024-09-30T0{i}:00:00Z"
    rows, _, faltas, _ = analise.calcular_dataset(dataset, comparacoes_puras(dataset))
    assert rows[0]["cfr_releases_proxy_v3"] is None
    assert rows[0]["releases_cfr_avaliadas"] == 0
    assert rows[0]["releases_cfr_censuradas"] == 5
    assert any(f["motivo"] == "nenhuma_release_com_seguimento_completo_de_7_dias" for f in faltas)


def test_falta_de_cobertura_anual_bloqueia_ci_recuperacao_sem_bloquear_releases(dataset):
    dataset.snapshots["fixture/projeto"].pop("cobertura_runs")
    rows, sumarios, faltas, episodios = analise.calcular_dataset(dataset, {})
    row = rows[0]
    assert row["deployment_frequency_semana"] > 0
    for campo in ("lead_time_release_mediana_dias", "lead_time_commit_mediana_dias", "cfr_ci_proxy",
                  "cfr_releases_proxy_v3", "tempo_recuperacao_mediana_horas", "episodios_recuperados", "episodios_censurados"):
        assert row[campo] is None
    assert episodios == []
    assert {f["rq"] for f in faltas} == {"RQ02", "RQ03_releases", "RQ03_CI", "RQ04"}
    assert next(s for s in sumarios if s["metrica"] == "cfr_ci_proxy")["n_ausentes"] == 1


def test_sem_episodios_nao_e_100_porcento_censura_nem_recuperacao_zero(dataset):
    snapshot = dataset.snapshots["fixture/projeto"]
    snapshot["runs"] = [run for run in snapshot["runs"] if run["conclusion"] == "success"]
    rows, _, faltas, episodios = analise.calcular_dataset(dataset, comparacoes_puras(dataset))
    assert rows[0]["episodios_recuperados"] == rows[0]["episodios_censurados"] == 0
    assert rows[0]["tempo_recuperacao_mediana_horas"] is None
    assert rows[0]["proporcao_episodios_censurados"] is None
    assert episodios == [] and any(f["motivo"] == "sem_episodios_observados" for f in faltas)


def test_so_censurados_nao_entram_na_mediana(dataset):
    snapshot = dataset.snapshots["fixture/projeto"]
    snapshot["runs"] = snapshot["runs"][:2]
    rows, sumarios, _, episodios = analise.calcular_dataset(dataset, comparacoes_puras(dataset))
    assert rows[0]["tempo_recuperacao_mediana_horas"] is None
    assert rows[0]["proporcao_episodios_censurados"] == 1
    assert sumarios[-1]["n_validos"] == 0 and sumarios[-1]["n_censurados"] == 1
    assert sumarios[-1]["mediana"] is None and episodios[0]["duracao_horas"] is None


@pytest.mark.parametrize("campo,valor", [("historico_anual_completo", False), ("completa", False)])
def test_contrato_anual_parcial_nao_autoriza_metricas(dataset, campo, valor):
    dataset.snapshots["fixture/projeto"]["cobertura_runs"][campo] = valor
    assert analise.cobertura_anual(dataset, "fixture/projeto")[0] is False


def test_cobertura_anual_exige_janela_e_hash_da_fonte(dataset):
    snapshot = dataset.snapshots["fixture/projeto"]
    snapshot["cobertura_runs"]["janela"]["inicio"] = "2024-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="cobertura anual"):
        analise.cobertura_anual(dataset, "fixture/projeto")
    snapshot["cobertura_runs"]["janela"]["inicio"] = "2023-10-01T00:00:00Z"
    (dataset.diretorio / "arquivo_anual_fixture.txt").write_text("adulterado", encoding="utf-8")
    with pytest.raises(ValueError, match="hash divergente"):
        analise.cobertura_anual(dataset, "fixture/projeto")


def preparar_comparacao(dataset, tmp_path, total=101):
    nome = "fixture/projeto"
    commits = [dict(sha=f"{i+1:040x}", commit={"author": {"date": "2024-01-01T00:00:00Z"},
                                            "message": "fix: fixture de comparação"}) for i in range(total)]
    paginas = []
    for indice in range(max(1, (total + 99) // 100)):
        paginas.append(salvar(tmp_path / f"pagina{indice+1}.json", dict(
            endpoint=f"/repos/{nome}/compare/v1.0.0...v1.0.1", params={"page": indice+1, "per_page": 100},
            http_status=200, resposta={"total_commits": total, "commits": commits[indice*100:(indice+1)*100]})))
    manifesto = dict(schema_version=1, origem="github_api", modo_referencia=False,
                     repositorios_sha256=dataset.hashes["repositorios_aprovados.csv"],
                     releases_sha256=dataset.hashes["releases.json"], repositorios={nome: {
                         "1": dict(status="sem_predecessora", head_tag="v1.0.0", motivo="primeira_release"),
                         "2": dict(status="completa", base_tag="v1.0.0", head_tag="v1.0.1", paginas=paginas)}})
    path = tmp_path / "comparacoes.json"
    salvar(path, manifesto)
    return path, manifesto


def test_comparacoes_paginas_completas_datas_autor_e_fontes(dataset, tmp_path):
    path, _ = preparar_comparacao(dataset, tmp_path)
    resultado, hashes = analise.carregar_comparacoes(path, dataset)
    assert len(resultado["fixture/projeto", "2"]["commits"]) == 101
    assert resultado["fixture/projeto", "1"]["status"] == "sem_predecessora"
    assert resultado["fixture/projeto", "2"]["commits"][0]["author_date"] == analise.instante("2024-01-01T00:00:00Z")
    assert len(hashes) == 3


@pytest.mark.parametrize("mutacao,mensagem", [
    ("truncada", "Paginação.*incompleta"), ("base_errada", "Base/status"),
    ("sem_predecessora_invalida", "com predecessora"), ("hash", "hash divergente"),
    ("fora_do_bundle", "externa"), ("simulado", "sem modo de referência"),
    ("repositorio_externo", "externos ao dataset"), ("release_desconhecida", "Release desconhecida"),
])
def test_recusa_comparacoes_incompletas_ou_desalinhadas(dataset, tmp_path, mutacao, mensagem):
    path, manifesto = preparar_comparacao(dataset, tmp_path)
    mapa = manifesto["repositorios"]["fixture/projeto"]
    entrada = mapa["2"]
    if mutacao == "truncada":
        entrada["paginas"].pop()
    elif mutacao == "base_errada":
        entrada["base_tag"] = "v9.0.0"
    elif mutacao == "sem_predecessora_invalida":
        mapa["2"] = dict(status="sem_predecessora", head_tag="v1.0.1", motivo="engano")
    elif mutacao == "hash":
        entrada["paginas"][0]["sha256"] = "0" * 64
    elif mutacao == "fora_do_bundle":
        entrada["paginas"][0]["arquivo"] = "../fonte_externa.json"
    elif mutacao == "simulado":
        manifesto["modo_referencia"] = True
    elif mutacao == "repositorio_externo":
        manifesto["repositorios"]["outro/projeto"] = manifesto["repositorios"].pop("fixture/projeto")
    elif mutacao == "release_desconhecida":
        mapa["999"] = mapa.pop("2")
    salvar(path, manifesto)
    with pytest.raises(ValueError, match=mensagem):
        analise.carregar_comparacoes(path, dataset)


@pytest.mark.parametrize("mutacao,mensagem", [
    ("data_invalida", "Data ISO"), ("data_futura", "posterior à release"),
    ("sha_duplicado", "SHA.*duplicado"), ("mensagem_ausente", "Mensagem original"),
    ("ordem", "ordem inválidos"), ("total_mutante", "Total.*diverge"),
    ("autor_invalido", "commit.author válido"),
])
def test_valida_conteudo_das_paginas_originais(dataset, tmp_path, mutacao, mensagem):
    path, manifesto = preparar_comparacao(dataset, tmp_path)
    pagina_path = tmp_path / "pagina1.json"
    pagina = json.loads(pagina_path.read_text(encoding="utf-8"))
    commit = pagina["resposta"]["commits"][0]
    if mutacao == "data_invalida":
        commit["commit"]["author"]["date"] = "sem_data"
    elif mutacao == "data_futura":
        commit["commit"]["author"]["date"] = "2025-01-01T00:00:00Z"
    elif mutacao == "sha_duplicado":
        pagina["resposta"]["commits"][1]["sha"] = commit["sha"]
    elif mutacao == "mensagem_ausente":
        commit["commit"].pop("message")
    elif mutacao == "autor_invalido":
        commit["commit"]["author"] = None
    elif mutacao == "ordem":
        pagina["params"]["page"] = 3
    elif mutacao == "total_mutante":
        pagina["resposta"]["total_commits"] = 0
    evidencia = salvar(pagina_path, pagina)
    manifesto["repositorios"]["fixture/projeto"]["2"]["paginas"][0] = evidencia
    salvar(path, manifesto)
    with pytest.raises(ValueError, match=mensagem):
        analise.carregar_comparacoes(path, dataset)


def test_comparacao_404_registra_ausencia_sem_fabricar_zero(dataset, tmp_path):
    path, manifesto = preparar_comparacao(dataset, tmp_path)
    manifesto["repositorios"]["fixture/projeto"]["2"] = dict(
        status="indisponivel", head_tag="v1.0.1", motivo="HTTP 404: tag removida")
    salvar(path, manifesto)
    resultado, _ = analise.carregar_comparacoes(path, dataset)
    rows, _, faltas, _ = analise.calcular_dataset(dataset, resultado)
    assert rows[0]["lead_time_release_mediana_dias"] is None
    assert any(f["motivo"].startswith("HTTP 404") for f in faltas)


class APIFixture:
    """Produz bundle artificial pelo coletor verdadeiro, somente em tmp_path."""

    def __init__(self, n=300):
        self.candidatos = [dict(id=i+1, full_name=f"fixture/projeto-{i:03d}", private=False,
                               stargazers_count=1500, default_branch="main", created_at="2020-01-01T00:00:00Z") for i in range(n)]

    def request(self, endpoint, params=None, **kwargs):
        nome = endpoint.removeprefix("/repos/").split("/actions/")[0]
        repo = next(c for c in self.candidatos if c["full_name"] == nome)
        if endpoint.endswith("/actions/workflows"):
            return 200, {"total_count": 1, "workflows": [{"id": 1}]}, {}
        if endpoint.endswith("/actions/runs"):
            return 200, {"total_count": 50, "workflow_runs": self.runs(*nome.split("/"), "main", None, None)[:1]}, {}
        return 200, copy.deepcopy(repo), {}

    def paginate(self, endpoint, params=None):
        nome = endpoint.removeprefix("/repos/").removesuffix("/releases")
        i = next(c["id"] for c in self.candidatos if c["full_name"] == nome)
        return [dict(id=i*1000+j, tag_name=f"v1.0.{j}", published_at=f"2024-01-{j:02d}T00:00:00Z",
                     html_url=f"https://github.com/{nome}/releases/tag/v1.0.{j}", body="Release artificial de teste.",
                     draft=False, prerelease=False) for j in range(1, 6)]

    def runs(self, owner, repo, branch, inicio, fim):
        i = next(c["id"] for c in self.candidatos if c["full_name"] == f"{owner}/{repo}")
        return [dict(id=i*1000+j+1, workflow_id=1, event="push", head_branch=branch, conclusion="success",
                     created_at="2024-01-01T00:00:00Z", run_started_at="2024-01-01T00:00:00Z",
                     updated_at="2024-01-01T00:01:00Z") for j in range(50)]


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text('window:\n  start_date: "2023-10-01T00:00:00Z"\n  end_date: "2024-09-30T23:59:59Z"\n  weeks: 52.14\ncriteria:\n  min_stars: 1000\n  min_releases: 5\n  min_workflow_runs: 50\n', encoding="utf-8")
    api = APIFixture()
    monkeypatch.setattr(coleta, "buscar_candidatos", lambda *args, **kwargs: api.candidatos)
    monkeypatch.setattr(coleta.ColetorRuns, "coletar_runs_janela", lambda self, *args: api.runs(*args))
    # Checkpoints por candidato têm sua própria suíte. Aqui precisamos apenas
    # do bundle publicado e auditável, evitando reescrever 300 vezes os mesmos
    # relatórios (e bloqueios transitórios de arquivos no Windows).
    checkpoint = coleta._checkpoint
    def somente_checkpoint_final(destino, resultados, assinatura, busca, status, erro=None):
        if status == "em_andamento":
            return {"n_aprovados": sum(r["aprovado"] for r in resultados)}
        return checkpoint(destino, resultados, assinatura, busca, status, erro)
    monkeypatch.setattr(coleta, "_checkpoint", somente_checkpoint_final)
    destino = tmp_path / "coleta_fixture"
    assert coleta.coletar(config, destino, client=api)["n_aprovados"] == 300
    return destino, config


def test_exportacao_fixture_audita_300_e_reproduz_tabelas_graficos_sem_inventar_outras_rqs(bundle, tmp_path):
    base, config = bundle
    a, b = tmp_path / "analise_a_fixture", tmp_path / "analise_b_fixture"
    manifesto = analise.executar(base, a, config)
    assert manifesto["n_repositorios"] == 300
    assert manifesto["status"] == "executada_com_ausencias"
    assert manifesto["n_repositorios_cobertura_anual_runs"] == 0
    rq01 = manifesto["cobertura_por_metrica"][0]
    assert rq01["n_validos"] == 300 and rq01["n_ausentes"] == 0
    assert manifesto["cobertura_por_metrica"][3]["n_validos"] == 0
    with (a / "sumarios_rq01_rq04.csv").open(encoding="utf-8", newline="") as stream:
        sumarios = list(csv.DictReader(stream))
    assert float(sumarios[0]["mediana"]) == pytest.approx(5 / 52.14)
    assert sumarios[3]["mediana"] == ""
    with (a / "rq03_censura_releases.csv").open(encoding="utf-8", newline="") as stream:
        censura = list(csv.DictReader(stream))
    assert len(censura) == 300
    assert censura[0]["status"] == "dados_ausentes"
    assert censura[0]["n_releases_censuradas"] == censura[0]["n_releases_avaliadas"] == ""
    assert censura[0]["n_releases_avaliacao_ausente"] == "5"
    assert all(ET.parse(a / f"rq0{i}_mediana_iqr.svg").getroot().tag.endswith("svg") for i in range(1, 5))
    for nome, hash_esperado in manifesto["saidas_sha256"].items():
        assert analise.sha256(a / nome) == hash_esperado
    assert analise.executar(base, b, config) == manifesto
    assert all(path.read_bytes() == (b / path.name).read_bytes() for path in a.iterdir())
    with pytest.raises(FileExistsError, match="preservada"):
        analise.executar(base, a, config)


def test_adulteracao_do_bundle_bloqueia_todas_as_saidas(bundle, tmp_path):
    base, config = bundle
    snapshot = base / "qualificacoes/1.json"
    snapshot.write_text(snapshot.read_text(encoding="utf-8") + " ", encoding="utf-8")
    saida = tmp_path / "nao_deve_existir"
    with pytest.raises(ValueError, match="alterado"):
        analise.executar(base, saida, config)
    assert not saida.exists()


def test_cli_recusa_csv_legado_e_bundle_parcial_antes_de_criar_saida(tmp_path, capsys):
    base = tmp_path / "legado"
    base.mkdir()
    (base / "repositorios_aprovados.csv").write_text("full_name\nfixture/projeto\n", encoding="utf-8")
    saida = tmp_path / "nao_deve_existir"
    assert analise.main(["--coleta", str(base), "--saida", str(saida)]) == 2
    assert "sem resultados oficiais" in capsys.readouterr().err
    assert not saida.exists()
