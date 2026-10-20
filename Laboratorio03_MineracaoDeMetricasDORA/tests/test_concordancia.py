"""Fixtures sintéticas somente para verificar o protocolo, sem resultados empíricos."""

from copy import deepcopy
import csv
import json

import pytest

from metricas import concordancia
from rotulagem import JULGAMENTOS, METADADOS


@pytest.fixture
def amostra():
    return [
        {
            "full_name": f"fixture/repo{repo:03d}",
            "release_id": str(repo * 5 + release + 1),
            "published_at": f"2025-06-{release + 1:02d}T12:00:00Z",
            "tag_name": f"v{release + 1}",
            "html_url": f"https://github.com/fixture/repo{repo:03d}/releases/tag/v{release + 1}",
            "release_notes_url": f"https://github.com/fixture/repo{repo:03d}/releases/tag/v{release + 1}",
            "commits_url": f"https://github.com/fixture/repo{repo:03d}/compare/v{release}...v{release + 1}",
            "previous_tag": f"v{release}",
            **dict.fromkeys(JULGAMENTOS, ""),
        }
        for repo in range(60)
        for release in range(5)
    ]


@pytest.fixture
def avaliadores(amostra):
    """Metade unanimidade A; metade votos B,B,A: Fleiss kappa = 1/4."""
    avaliadores = {}
    for nome in ("aulus", "maria", "vinicius"):
        rows = deepcopy(amostra)
        for indice, row in enumerate(rows):
            categoria_a = indice < 150 or nome == "vinicius"
            row.update(
                tipo_projeto="biblioteca/framework" if categoria_a else "aplicação/serviço",
                entrega_real="sim" if categoria_a else "não",
                corretiva="sim" if categoria_a else "não",
                justificativa="Julgamento sintético para teste, sem avaliação empírica.",
                evidencia=row["release_notes_url"],
            )
        avaliadores[nome] = rows
    return avaliadores


@pytest.fixture
def consenso_completo(amostra, avaliadores):
    _, rows = concordancia.preparar_consenso(amostra, avaliadores)
    for row in rows:
        row.update(
            rotulo_consenso=(
                "biblioteca/framework" if row["dimensao"] == "tipo_projeto" else "sim"
            ),
            justificativa="Decisão de reunião simulada para teste.",
            evidencia=f"https://github.com/{row['full_name']}/releases",
            responsaveis="aulus;maria;vinicius",
            data_reuniao="2026-10-13",
            protocolo="Releitura das fontes e discussão da evidência pelos três avaliadores.",
            desempate="",
        )
    return rows


def _salvar(path, rows, campos):
    with path.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def _entradas_cli(tmp_path, amostra, avaliadores):
    amostra_path = tmp_path / "amostra.csv"
    _salvar(amostra_path, amostra, METADADOS + JULGAMENTOS)
    args = ["--amostra", str(amostra_path)]
    for nome, rows in avaliadores.items():
        path = tmp_path / f"rotulos_{nome}.csv"
        _salvar(path, rows, METADADOS + JULGAMENTOS)
        args += [f"--{nome}", str(path)]
    return args


@pytest.fixture
def referencia_cli(tmp_path, monkeypatch):
    # Testes de integridade do sorteio/bundle estão em test_amostra_ouro e
    # test_coleta_amostra_real; aqui a CLI exercita o protocolo de três humanos.
    import gerar_amostra_rotulagem
    monkeypatch.setattr(gerar_amostra_rotulagem, "validar_referencia", lambda *args: None)
    (tmp_path / "selecao.json").write_text("{}", encoding="utf-8")


def test_kappa_conhecido_agrega_statsmodels(monkeypatch):
    chamadas = []
    aggregate = concordancia.aggregate_raters
    fleiss = concordancia.fleiss_kappa

    def registrar_aggregate(*args, **kwargs):
        chamadas.append("aggregate_raters")
        return aggregate(*args, **kwargs)

    def registrar_fleiss(*args, **kwargs):
        chamadas.append("fleiss_kappa")
        return fleiss(*args, **kwargs)

    monkeypatch.setattr(concordancia, "aggregate_raters", registrar_aggregate)
    monkeypatch.setattr(concordancia, "fleiss_kappa", registrar_fleiss)
    assert concordancia.calcular_kappa([["sim", "sim", "sim"], ["não", "não", "sim"]], ["sim", "não"]) == pytest.approx(0.25)
    assert chamadas == ["aggregate_raters", "fleiss_kappa"]


def test_kappa_perfeito_nao_degenerado():
    assert concordancia.calcular_kappa([["sim"] * 3, ["não"] * 3], ["sim", "não"]) == pytest.approx(1.0)


def test_kappa_degenerado_indefinido(amostra, avaliadores):
    for rows in avaliadores.values():
        for row in rows:
            row["tipo_projeto"] = "biblioteca/framework"
            row["entrega_real"] = "sim"
            row["corretiva"] = "sim"
    kappas = concordancia.calcular_kappas(amostra, avaliadores)
    assert all(resultado["kappa"] is None for resultado in kappas.values())
    assert all(resultado["status"] == "indefinido" for resultado in kappas.values())
    # JSON não pode apresentar NaN como um resultado numérico.
    assert "NaN" not in json.dumps(kappas, allow_nan=False)


@pytest.mark.parametrize("rotulos,categorias", [
    ([], ["sim", "não"]),
    ([["sim", "não"]], ["sim", "não"]),
    ([["sim", "sim", "talvez"]], ["sim", "não"]),
    ([["sim", "sim", "sim"]], ["sim", "sim"]),
])
def test_kappa_rejeita_entradas_invalidas(rotulos, categorias):
    with pytest.raises(ValueError):
        concordancia.calcular_kappa(rotulos, categorias)


def test_tres_dimensoes_60_60_300_e_invariancia_de_ordem(amostra, avaliadores):
    kappas = concordancia.calcular_kappas(amostra, avaliadores)
    assert {dimensao: valor["n"] for dimensao, valor in kappas.items()} == {
        "tipo_projeto": 60, "entrega_real": 60, "corretiva": 300,
    }
    assert all(valor["kappa"] == pytest.approx(0.25) for valor in kappas.values())
    reordenados = {nome: list(reversed(rows)) for nome, rows in reversed(list(avaliadores.items()))}
    assert concordancia.calcular_kappas(list(reversed(amostra)), reordenados) == kappas


def test_espacos_ao_redor_dos_rotulos_seguem_validador(amostra, avaliadores):
    esperado = concordancia.calcular_kappas(amostra, avaliadores)
    for rows in avaliadores.values():
        for row in rows:
            for campo in concordancia.DIMENSOES:
                row[campo] = f" {row[campo]} "
    assert concordancia.calcular_kappas(amostra, avaliadores) == esperado


@pytest.mark.parametrize("quantidade", [2, 4])
def test_exige_exatamente_tres_avaliadores(amostra, avaliadores, quantidade):
    if quantidade == 2:
        avaliadores.pop("vinicius")
    else:
        avaliadores["quarto"] = deepcopy(avaliadores["aulus"])
    with pytest.raises(ValueError, match="exatamente três"):
        concordancia.calcular_kappas(amostra, avaliadores)


def test_avaliador_repetido_com_outra_caixa_nao_conta_como_pessoa(amostra, avaliadores):
    avaliadores["AULUS"] = avaliadores.pop("vinicius")
    with pytest.raises(ValueError, match="identificadores distintos"):
        concordancia.calcular_kappas(amostra, avaliadores)


def test_mesma_lista_nao_representa_tres_humanos(amostra, avaliadores):
    avaliadores["maria"] = avaliadores["aulus"]
    with pytest.raises(ValueError, match="mesmo conjunto"):
        concordancia.calcular_kappas(amostra, avaliadores)


def test_referencia_comum_nao_pode_expor_julgamentos(amostra, avaliadores):
    amostra[0]["corretiva"] = "sim"
    with pytest.raises(ValueError, match="cegamento"):
        concordancia.preparar_consenso(amostra, avaliadores)


@pytest.mark.parametrize("erro", ["ausente", "duplicada", "categoria", "vazio", "metadados", "repo_inconsistente"])
def test_rejeita_rotulagem_invalida(amostra, avaliadores, erro):
    rows = avaliadores["aulus"]
    if erro == "ausente":
        rows.pop()
    elif erro == "duplicada":
        rows[-1] = deepcopy(rows[0])
    elif erro == "categoria":
        rows[0]["corretiva"] = "talvez"
    elif erro == "vazio":
        rows[0]["evidencia"] = ""
    elif erro == "metadados":
        rows[0]["html_url"] = "https://github.com/fixture/alterado/releases/tag/v1"
    else:
        rows[0]["tipo_projeto"] = "outro"
    with pytest.raises(ValueError, match="aulus"):
        concordancia.preparar_consenso(amostra, avaliadores)


def test_divergencias_preservam_evidencias_e_consenso_todo_vazio(amostra, avaliadores):
    divergencias, consenso = concordancia.preparar_consenso(amostra, avaliadores)
    unidades_divergentes = {(row["dimensao"], row["full_name"], row["release_id"]) for row in divergencias}
    assert len(unidades_divergentes) == 30 + 30 + 150
    assert len(divergencias) == 3 * len(unidades_divergentes)
    assert all(row["justificativa"] and row["evidencia"] for row in divergencias)
    assert len(consenso) == 60 + 60 + 300
    campos_decisao = set(concordancia.CAMPOS_CONSENSO) - {"dimensao", "full_name", "release_id"}
    assert all(row[campo] == "" for row in consenso for campo in campos_decisao)
    assert all(row["release_id"] == "" for row in consenso if row["dimensao"] != "corretiva")


def test_unanimidade_tambem_exige_decisao_humana(amostra, avaliadores):
    avaliadores["maria"] = deepcopy(avaliadores["aulus"])
    avaliadores["vinicius"] = deepcopy(avaliadores["aulus"])
    divergencias, consenso = concordancia.preparar_consenso(amostra, avaliadores)
    assert divergencias == []
    assert all(row["rotulo_consenso"] == "" for row in consenso)
    with pytest.raises(ValueError, match="Consenso incompleto"):
        concordancia.finalizar(amostra, avaliadores, consenso)


@pytest.mark.parametrize("campo", [
    "rotulo_consenso", "justificativa", "evidencia", "responsaveis", "data_reuniao", "protocolo",
])
def test_consenso_exige_decisoes_documentadas(amostra, avaliadores, consenso_completo, campo):
    consenso_completo[0][campo] = ""
    with pytest.raises(ValueError, match="Consenso incompleto"):
        concordancia.finalizar(amostra, avaliadores, consenso_completo)


@pytest.mark.parametrize("erro", ["faltante", "duplicado_conflitante", "extra", "categoria", "data", "responsaveis", "coluna"])
def test_consenso_rejeita_ausencias_conflitos_e_invalidade(amostra, avaliadores, consenso_completo, erro):
    if erro == "faltante":
        consenso_completo.pop()
    elif erro == "duplicado_conflitante":
        outra = deepcopy(consenso_completo[0])
        outra["rotulo_consenso"] = "outro"
        consenso_completo.append(outra)
    elif erro == "extra":
        consenso_completo[0]["full_name"] = "fixture/fora-da-amostra"
    elif erro == "categoria":
        consenso_completo[0]["rotulo_consenso"] = "inválida"
    elif erro == "data":
        consenso_completo[0]["data_reuniao"] = "13/10/2026"
    elif erro == "responsaveis":
        consenso_completo[0]["responsaveis"] = "aulus;maria"
    else:
        consenso_completo[0].pop("protocolo")
    with pytest.raises(ValueError):
        concordancia.finalizar(amostra, avaliadores, consenso_completo)


def test_tres_rotulos_distintos_exigem_desempate(amostra, avaliadores, consenso_completo):
    for row in avaliadores["maria"][:5]:
        row["tipo_projeto"] = "ferramenta CLI"
    for row in avaliadores["vinicius"][:5]:
        row["tipo_projeto"] = "outro"
    with pytest.raises(ValueError, match="registro do desempate"):
        concordancia.validar_consenso(amostra, avaliadores, consenso_completo)
    consenso_completo[0]["desempate"] = "Discussão das fontes e decisão unânime após releitura; fixture."
    concordancia.validar_consenso(amostra, avaliadores, consenso_completo)


def test_final_preserva_kappas_pre_consenso(amostra, avaliadores, consenso_completo):
    resultado = concordancia.finalizar(amostra, avaliadores, consenso_completo)
    assert resultado["unidades_consenso"] == 420
    assert resultado["base_kappa"] == "rotulos_independentes_anteriores_ao_consenso"
    assert all(valor["kappa"] == pytest.approx(0.25) for valor in resultado["kappas"].values())
    assert resultado["frequencias_consenso"]["corretiva"]["sim"] == 300


def test_cli_prepara_e_calcula_sem_sobrescrever(tmp_path, amostra, avaliadores, consenso_completo, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    divergencias_path = tmp_path / "divergencias.csv"
    consenso_path = tmp_path / "consenso.csv"
    saida = tmp_path / "kappas.json"
    preparar = ["preparar", *args, "--consenso", str(consenso_path), "--divergencias", str(divergencias_path)]
    assert concordancia.main(preparar) == 0
    assert len(concordancia.ler_csv(consenso_path)) == 420
    original = consenso_path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        concordancia.main(preparar)
    assert exc.value.code == 2
    assert consenso_path.read_bytes() == original
    calcular = ["calcular", *args, "--consenso", str(consenso_path), "--saida", str(saida)]
    with pytest.raises(SystemExit):
        concordancia.main(calcular)
    assert not saida.exists()
    _salvar(consenso_path, consenso_completo, concordancia.CAMPOS_CONSENSO)
    assert concordancia.main(calcular) == 0
    resultado = json.loads(saida.read_text(encoding="utf-8"))
    assert resultado["kappas"]["corretiva"]["n"] == 300
    assert len(resultado["arquivos_fontes"]) == 5
    assert all(len(row["sha256"]) == 64 for row in resultado["arquivos_fontes"])
    with pytest.raises(SystemExit):
        concordancia.main(calcular)


def test_cli_protege_arquivos_humanos_e_preverifica_saidas(tmp_path, amostra, avaliadores, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    vinicius_path = tmp_path / "rotulos_vinicius.csv"
    original = vinicius_path.read_bytes()
    divergencias_path = tmp_path / "divergencias.csv"
    with pytest.raises(SystemExit):
        concordancia.main([
            "preparar", *args, "--consenso", str(vinicius_path), "--divergencias", str(divergencias_path),
        ])
    assert vinicius_path.read_bytes() == original
    assert not divergencias_path.exists()


def test_cli_rejeita_saidas_iguais(tmp_path, amostra, avaliadores, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    path = tmp_path / "saida.csv"
    with pytest.raises(SystemExit):
        concordancia.main(["preparar", *args, "--consenso", str(path), "--divergencias", str(path)])
    assert not path.exists()


def test_cli_rejeita_mesmo_arquivo_como_tres_avaliadores(tmp_path, amostra, avaliadores, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    for opcao in ("--maria", "--vinicius"):
        args[args.index(opcao) + 1] = str(tmp_path / "rotulos_aulus.csv")
    path = tmp_path / "consenso.csv"
    with pytest.raises(SystemExit):
        concordancia.main([
            "preparar", *args, "--consenso", str(path), "--divergencias", str(tmp_path / "divergencias.csv"),
        ])
    assert not path.exists()


def test_cli_avaliar_calcula_antes_do_consenso_sem_preencher_decisoes(tmp_path, amostra, avaliadores, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    consenso = tmp_path / "consenso.csv"
    saida = tmp_path / "kappas_independentes.json"
    assert concordancia.main([
        "avaliar", *args, "--consenso", str(consenso),
        "--divergencias", str(tmp_path / "divergencias.csv"), "--saida", str(saida),
    ]) == 0
    resultado = json.loads(saida.read_text(encoding="utf-8"))
    assert resultado["status"] == "rotulos_independentes_completos_aguardando_consenso"
    assert all(valor["kappa"] == pytest.approx(0.25) for valor in resultado["kappas"].values())
    assert all(row["rotulo_consenso"] == "" for row in concordancia.ler_csv(consenso))


def test_cli_rejeita_hardlink_do_mesmo_avaliador(tmp_path, amostra, avaliadores, referencia_cli):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    alias = tmp_path / "alias_aulus.csv"
    alias.hardlink_to(tmp_path / "rotulos_aulus.csv")
    args[args.index("--maria") + 1] = str(alias)
    consenso = tmp_path / "consenso.csv"
    with pytest.raises(SystemExit):
        concordancia.main([
            "preparar", *args, "--consenso", str(consenso),
            "--divergencias", str(tmp_path / "divergencias.csv"),
        ])
    assert not consenso.exists()


def test_cli_csv_exemplo_sem_manifesto_nao_calcula(tmp_path, amostra, avaliadores):
    args = _entradas_cli(tmp_path, amostra, avaliadores)
    saida = tmp_path / "kappas.json"
    with pytest.raises(SystemExit):
        concordancia.main([
            "avaliar", *args, "--saida", str(saida), "--consenso", str(tmp_path / "consenso.csv"),
            "--divergencias", str(tmp_path / "divergencias.csv"),
        ])
    assert not saida.exists()
