"""Fixtures artificiais verificam análise de valores fornecidos, sem promover fonte."""

import csv
import json
import xml.etree.ElementTree as ET

import pytest

import analisar_csv_main as analise


@pytest.fixture
def entradas(tmp_path):
    csv_path = tmp_path / "entrada.csv"
    campos = ["full_name", *(m[1] for m in analise.METRICAS),
              *analise.CONTAGENS, "origem_coleta", "tier_dora_geral"]
    linhas = []
    for i, valor in enumerate((0, 1, 2, 9)):
        row = dict.fromkeys(campos, "")
        row.update(full_name=f"fixture/projeto{i}", origem_coleta="github_api",
                   deployment_frequency_semana=valor, lead_time_release_mediana_dias=valor,
                   lead_time_commit_mediana_dias=valor, cfr_ci_proxy=valor / 10,
                   cfr_releases_proxy=valor / 10, proporcao_episodios_censurados="",
                   episodios_recuperados=valor, episodios_censurados=0,
                   tempo_recuperacao_mediana_horas=valor if i < 3 else "",
                   tier_dora_geral="declaração preservada")
        linhas.append(row)
    config = tmp_path / "config.yaml"
    config.write_text('window:\n  start_date: "2023-10-01T00:00:00Z"\n'
                      '  end_date: "2024-09-30T23:59:59Z"\n  weeks: 52.14\n', encoding="utf-8")
    def salvar(rows=linhas, fields=campos):
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    salvar()
    return csv_path, config, linhas, campos, salvar


def test_quartis_ausencias_contagens_e_proveniencia(entradas, tmp_path):
    path, config, _, _, _ = entradas
    fontes_antes = path.read_bytes(), config.read_bytes()
    destino = tmp_path / "analise"
    manifesto = analise.executar(path, destino, config, "a892089")
    with (destino / "sumarios_rq01_rq04.csv").open(encoding="utf-8", newline="") as stream:
        sumarios = {r["metrica"]: r for r in csv.DictReader(stream)}
    # Cálculo independente: n=4, posições .75/1.5/2.25 produzem .75/1.5/3.75.
    lead = sumarios["lead_time_release_mediana_dias"]
    assert "n_censurados" not in lead
    assert {c: float(lead[c]) for c in ("q1", "mediana", "q3", "iqr")} == dict(q1=.75, mediana=1.5, q3=3.75, iqr=3)
    rec = sumarios["tempo_recuperacao_mediana_horas"]
    assert (rec["n_total"], rec["n_validos"], rec["n_ausentes"], rec["mediana"]) == ("4", "3", "1", "1.0")
    censura = sumarios["proporcao_episodios_censurados"]
    assert (censura["n_validos"], censura["n_ausentes"], censura["mediana"]) == ("0", "4", "")
    with (destino / "rq04_contagens_declaradas.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [r["episodios_recuperados"] for r in rows] == ["0", "1", "2", "9"]
    assert manifesto["evidencia_coleta_real_verificada"] is False
    assert manifesto["cobertura_historica_verificada"] is False
    assert manifesto["criterios_inclusao_verificados"] is False
    assert manifesto["comparacoes_originais_verificadas"] is False
    assert manifesto["fonte_declarada"] == "github_api"
    assert manifesto["status"] == analise.STATUS
    assert manifesto["origem_dos_valores"] == "csv_fornecido_pela_main"
    assert manifesto["commit_origem_declarado"] == "a892089"
    assert manifesto["janela_do_csv_verificada"] is False
    assert manifesto["entradas_sha256"] == {"csv": analise.sha256(path), "config": analise.sha256(config)}
    assert manifesto["parecer_auditoria_preexistente"]["arquivo"] == analise.AUDITORIA
    assert manifesto == json.loads((destino / "analise.json").read_text(encoding="utf-8"))
    assert fontes_antes == (path.read_bytes(), config.read_bytes())
    assert set(p.name for p in destino.iterdir()) == {
        "analise.json", "metricas_lidas.csv", "sumarios_rq01_rq04.csv", "rq04_contagens_declaradas.csv",
        *(f"rq0{i}_mediana_iqr.{ext}" for i in range(1, 5) for ext in ("png", "svg")),
    }
    for arquivo, digest in manifesto["saidas_sha256"].items():
        assert analise.sha256(destino / arquivo) == digest
    for i in range(1, 5):
        svg = destino / f"rq0{i}_mediana_iqr.svg"
        ET.parse(svg)
        assert analise.AVISO in svg.read_text(encoding="utf-8")
        assert (destino / f"rq0{i}_mediana_iqr.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with (destino / "metricas_lidas.csv").open(encoding="utf-8", newline="") as stream:
        preservadas = list(csv.DictReader(stream))
    assert preservadas[-1]["tempo_recuperacao_mediana_horas"] == ""
    assert all(r["tier_dora_geral"] == "declaração preservada" for r in preservadas)
    assert "cfr_releases_proxy_v3" not in preservadas[0]


@pytest.mark.parametrize(("campo", "valor"), [
    ("deployment_frequency_semana", "-1"), ("lead_time_release_mediana_dias", "NaN"),
    ("lead_time_commit_mediana_dias", "Infinity"), ("cfr_ci_proxy", "1.01"),
    ("cfr_releases_proxy", "-0.01"), ("proporcao_episodios_censurados", "texto"),
    ("episodios_recuperados", "1.5"), ("episodios_censurados", "-1"),
])
def test_rejeita_numeros_invalidos_sem_criar_saida(entradas, tmp_path, campo, valor):
    path, config, linhas, _, salvar = entradas
    linhas[0][campo] = valor
    salvar()
    destino = tmp_path / "rejeitada"
    with pytest.raises(ValueError):
        analise.executar(path, destino, config)
    assert not destino.exists()


def test_rejeita_unidades_duplicadas_mesmo_com_capitalizacao(entradas):
    path, _, linhas, _, salvar = entradas
    linhas[1]["full_name"] = linhas[0]["full_name"].upper()
    salvar()
    with pytest.raises(ValueError, match="duplicada"):
        analise.ler_csv(path)


def test_rejeita_csv_sem_metricas_ou_sem_linhas(entradas):
    path, _, linhas, campos, salvar = entradas
    salvar([], campos)
    with pytest.raises(ValueError, match="ao menos um"):
        analise.ler_csv(path)
    salvar([{"full_name": linhas[0]["full_name"]}], ["full_name"])
    with pytest.raises(ValueError, match="obrigatórias"):
        analise.ler_csv(path)


def test_contagens_ausentes_nao_sao_estimadas(entradas, tmp_path, monkeypatch):
    path, config, linhas, campos, salvar = entradas
    campos = [c for c in campos if c not in analise.CONTAGENS]
    salvar([{c: r[c] for c in campos} for r in linhas], campos)
    monkeypatch.setattr(analise, "graficos", lambda *args: None)
    manifesto = analise.executar(path, tmp_path / "sem_contagens", config)
    assert manifesto["contagens_presentes_no_csv"] == []
    with (tmp_path / "sem_contagens" / "rq04_contagens_declaradas.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert all(r[c] == "" for r in rows for c in analise.CONTAGENS)


def test_saida_exclusiva_sem_sobrescrita(entradas, tmp_path):
    path, config, _, _, _ = entradas
    destino = tmp_path / "existente"
    destino.mkdir()
    original = destino / "preservado.txt"
    original.write_text("conteúdo preexistente", encoding="utf-8")
    with pytest.raises(FileExistsError):
        analise.executar(path, destino, config)
    assert original.read_text(encoding="utf-8") == "conteúdo preexistente"
    assert list(destino.iterdir()) == [original]


def test_cli_erro_de_commit_e_config_nao_cria_saida(entradas, tmp_path):
    path, config, _, _, _ = entradas
    destino = tmp_path / "nao_criada"
    assert analise.main(["--csv", str(path), "--config", str(config), "--saida", str(destino),
                         "--commit-origem", "nao-e-sha"]) == 2
    config.write_text("window: {}\n", encoding="utf-8")
    assert analise.main(["--csv", str(path), "--config", str(config), "--saida", str(destino)]) == 2
    assert not destino.exists()


def test_identificacao_da_origem_exige_mesmos_bytes_do_parecer(entradas, tmp_path):
    path, _, _, _, _ = entradas
    parecer = tmp_path / "parecer.json"
    parecer.write_text(json.dumps({"conclusao": "dados de referencia gerados nao sao amostra empirica",
                                    "fontes": [{"arquivo": "csv_da_fixture", "sha256": analise.sha256(path)}]}),
                       encoding="utf-8")
    assert analise.identificar_origem(parecer, analise.sha256(path)) == (
        "seed_data.py/consolidar_dataset.py; valores gerados por fórmulas")
    assert analise.identificar_origem(parecer, "0" * 64) == "nao_estabelecida_pelas_evidencias_preservadas"


@pytest.mark.parametrize("conteudo", [
    "full_name,full_name\nfixture/a,fixture/b\n",
    "full_name,,lead_time_release_mediana_dias\nfixture/a,1,2\n",
])
def test_cabecalho_ambiguo_rejeitado(entradas, conteudo):
    path, _, _, _, _ = entradas
    path.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ValueError, match="Cabeçalho"):
        analise.ler_csv(path)
