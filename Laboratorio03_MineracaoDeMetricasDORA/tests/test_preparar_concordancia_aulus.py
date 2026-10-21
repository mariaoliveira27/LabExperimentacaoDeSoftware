"""Contratos do fluxo humano; todos os votos abaixo são fixtures sintéticas."""

from collections import Counter
from copy import deepcopy
import csv
import json

import pytest

import gerar_amostra_rotulagem
from metricas import concordancia
import preparar_concordancia_aulus as preparacao
from rotulagem import JULGAMENTOS, METADADOS, ler_csv


ORIGEM = {
    "tipo_fonte": "csv_main_adotado",
    "releases_originais_api_auditadas": False,
    "criterios_aprovacao_auditados": False,
    "cobertura_historica_verificada": False,
}
CAMPOS_DECISAO = set(concordancia.CAMPOS_CONSENSO) - {
    "dimensao", "full_name", "release_id",
}


def _salvar(path, rows, campos=METADADOS + JULGAMENTOS):
    with path.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def entradas(tmp_path, monkeypatch):
    amostra = [
        {
            "full_name": f"fixture/repo{repo:03d}",
            "release_id": str(repo * 5 + release + 1),
            "published_at": f"2024-06-{release + 1:02d}T12:00:00Z",
            "tag_name": f"v{release + 1}",
            "html_url": f"https://github.com/fixture/repo{repo:03d}/releases/tag/v{release + 1}",
            "release_notes_url": f"https://github.com/fixture/repo{repo:03d}/releases/tag/v{release + 1}",
            "commits_url": f"https://github.com/fixture/repo{repo:03d}/compare/v{release}...v{release + 1}",
            "previous_tag": f"v{release}",
            **dict.fromkeys(JULGAMENTOS, ""),
        }
        for repo in range(60) for release in range(5)
    ]
    amostra_path = tmp_path / "amostra_comum.csv"
    _salvar(amostra_path, amostra)
    manifesto = tmp_path / "selecao.json"
    manifesto.write_text(json.dumps(ORIGEM), encoding="utf-8")
    # Integridade da fonte é coberta pelos testes de amostra. Aqui o retorno
    # conhecido do validador permite conferir a propagação da proveniência.
    monkeypatch.setattr(
        gerar_amostra_rotulagem, "validar_referencia",
        lambda *args: deepcopy(ORIGEM),
    )
    humanos = {nome: tmp_path / f"rotulos_{nome}.csv" for nome in preparacao.AVALIADORES}
    for path in humanos.values():
        _salvar(path, amostra)
    return amostra, amostra_path, manifesto, humanos


def _completar(amostra, nome):
    rows = deepcopy(amostra)
    # Metade A,A,A e metade B,B,A: kappa conhecido = 1/4, para cada dimensão.
    for indice, row in enumerate(rows):
        categoria_a = indice < 150 or nome == "vinicius"
        row.update(
            tipo_projeto="biblioteca/framework" if categoria_a else "aplicação/serviço",
            entrega_real="sim" if categoria_a else "não",
            corretiva="sim" if categoria_a else "não",
            justificativa="Fixture sintética: nenhuma avaliação empírica.",
            evidencia=row["release_notes_url"],
        )
    return rows


def _snapshot(amostra_path, manifesto, humanos):
    return {path: path.read_bytes() for path in [amostra_path, manifesto, *humanos.values()] if path.exists()}


def _assert_formulario_vazio(path):
    rows = ler_csv(path)
    assert len(rows) == 420
    assert Counter(row["dimensao"] for row in rows) == {
        "tipo_projeto": 60, "entrega_real": 60, "corretiva": 300,
    }
    assert len({(row["dimensao"], row["full_name"], row["release_id"]) for row in rows}) == 420
    assert all(row[campo] == "" for row in rows for campo in CAMPOS_DECISAO)
    assert all(row["release_id"] == "" for row in rows if row["dimensao"] != "corretiva")
    return rows


def test_formulario_independe_de_votos_e_preserva_cegamento(entradas):
    amostra, *_ = entradas
    original = deepcopy(amostra)
    rows = concordancia.formulario_consenso(amostra)
    assert len(rows) == 420
    assert all(row[campo] == "" for row in rows for campo in CAMPOS_DECISAO)
    assert rows == concordancia.formulario_consenso(list(reversed(amostra)))
    assert amostra == original
    amostra[0]["corretiva"] = "sim"
    with pytest.raises(ValueError, match="cegamento"):
        concordancia.formulario_consenso(amostra)


def test_zero_de_tres_so_prepara_formulario_sem_inventar_resultados(tmp_path, entradas):
    _, amostra_path, manifesto, humanos = entradas
    originais = _snapshot(amostra_path, manifesto, humanos)
    saida = tmp_path / "preparacao"
    estado = preparacao.executar(amostra_path, humanos, saida)
    assert estado["status"] == "aguardando_tres_avaliacoes_humanas_completas"
    assert estado["avaliacoes_completas"] == 0
    assert estado["origem_referencia"] == ORIGEM
    assert all(item["status"] == "aguardando_preenchimento_humano" for item in estado["avaliacoes"].values())
    assert estado["kappa_calculado"] is False
    assert estado["divergencias_geradas"] is False
    assert estado["decisoes_de_reuniao_registradas"] is False
    assert estado["formulario"]["consenso_validado"] is False
    assert estado["formulario"]["decisoes_preenchidas"] == 0
    _assert_formulario_vazio(saida / "consenso_formulario.csv")
    assert {path.name for path in saida.iterdir()} == {"estado.json", "consenso_formulario.csv"}
    assert json.loads((saida / "estado.json").read_text(encoding="utf-8")) == estado
    assert _snapshot(amostra_path, manifesto, humanos) == originais


def test_tres_contratos_completos_calculam_pre_consenso_com_fonte_preservada(tmp_path, entradas):
    amostra, amostra_path, manifesto, humanos = entradas
    for nome, path in humanos.items():
        _salvar(path, _completar(amostra, nome))
    originais = _snapshot(amostra_path, manifesto, humanos)
    saida = tmp_path / "pre_consenso"
    estado = preparacao.executar(amostra_path, humanos, saida)
    assert estado["avaliacoes_completas"] == 3
    assert estado["kappa_calculado"] is True
    assert estado["divergencias_geradas"] is True
    assert estado["decisoes_de_reuniao_registradas"] is False
    resultado = json.loads((saida / "kappas_pre_consenso.json").read_text(encoding="utf-8"))
    assert resultado["origem_referencia"] == ORIGEM
    assert resultado["base_kappa"] == "rotulos_independentes_anteriores_ao_consenso"
    assert {dim: res["n"] for dim, res in resultado["kappas"].items()} == {
        "tipo_projeto": 60, "entrega_real": 60, "corretiva": 300,
    }
    assert all(res["kappa"] == pytest.approx(0.25) for res in resultado["kappas"].values())
    divergencias = ler_csv(saida / "divergencias.csv")
    assert len(divergencias) == 630  # 210 unidades divergentes × três votos.
    assert {row["avaliador"] for row in divergencias} == set(preparacao.AVALIADORES)
    assert all(row["justificativa"] and row["evidencia"] for row in divergencias)
    assert _assert_formulario_vazio(saida / "consenso.csv") == _assert_formulario_vazio(saida / "consenso_formulario.csv")
    assert _snapshot(amostra_path, manifesto, humanos) == originais


def test_um_completo_outro_parcial_e_ausente_nao_disparam_kappa(tmp_path, entradas):
    amostra, amostra_path, _, humanos = entradas
    _salvar(humanos["aulus"], _completar(amostra, "aulus"))
    parciais = _completar(amostra, "maria")
    parciais[0]["evidencia"] = ""
    _salvar(humanos["maria"], parciais)
    humanos["vinicius"].unlink()
    saida = tmp_path / "parcial"
    estado = preparacao.executar(amostra_path, humanos, saida)
    assert estado["avaliacoes_completas"] == 1
    assert estado["avaliacoes"]["aulus"]["status"] == "contrato_completo"
    assert estado["avaliacoes"]["maria"]["status"] == "aguardando_preenchimento_humano"
    assert estado["avaliacoes"]["vinicius"]["status"] == "arquivo_ausente"
    assert estado["kappa_calculado"] is False
    assert not (saida / "kappas_pre_consenso.json").exists()


@pytest.mark.parametrize("erro", ["schema", "metadado", "categoria"])
def test_contrato_invalido_nao_exporta_votos_nem_calcula(tmp_path, entradas, erro):
    amostra, amostra_path, _, humanos = entradas
    rows = _completar(amostra, "aulus")
    secreto = "JULGAMENTO_PRIVADO_INVALIDO"
    if erro == "schema":
        for row in rows:
            del row["corretiva"]
        _salvar(humanos["aulus"], rows, tuple(c for c in METADADOS + JULGAMENTOS if c != "corretiva"))
    elif erro == "metadado":
        rows[0]["tag_name"] = secreto
        _salvar(humanos["aulus"], rows)
    else:
        rows[0]["corretiva"] = secreto
        _salvar(humanos["aulus"], rows)
    saida = tmp_path / "invalido"
    estado = preparacao.executar(amostra_path, humanos, saida)
    assert estado["status"] == "contrato_invalido"
    assert estado["avaliacoes"]["aulus"]["status"] == "contrato_invalido"
    assert estado["avaliacoes_completas"] == 0
    assert secreto not in (saida / "estado.json").read_text(encoding="utf-8")
    assert not (saida / "divergencias.csv").exists()
    assert not (saida / "kappas_pre_consenso.json").exists()


@pytest.mark.parametrize("alias", ["mesmo_caminho", "hardlink"])
def test_aliases_nao_contam_como_avaliadores_distintos(tmp_path, entradas, alias):
    _, amostra_path, manifesto, humanos = entradas
    originais = _snapshot(amostra_path, manifesto, humanos)
    if alias == "hardlink":
        link = tmp_path / "alias.csv"
        link.hardlink_to(humanos["aulus"])
        humanos["maria"] = link
    else:
        humanos["maria"] = humanos["aulus"]
    saida = tmp_path / "aliases"
    with pytest.raises(ValueError, match="distintos"):
        preparacao.executar(amostra_path, humanos, saida)
    assert not saida.exists()
    assert all(path.read_bytes() == conteudo for path, conteudo in originais.items())


def test_reexecucao_preserva_todas_as_saidas(tmp_path, entradas):
    _, amostra_path, manifesto, humanos = entradas
    saida = tmp_path / "existente"
    preparacao.executar(amostra_path, humanos, saida)
    originais = {path: path.read_bytes() for path in [*saida.iterdir(), amostra_path, manifesto, *humanos.values()]}
    with pytest.raises(FileExistsError, match="preservado"):
        preparacao.executar(amostra_path, humanos, saida)
    assert all(path.read_bytes() == conteudo for path, conteudo in originais.items())


def test_formulario_nao_sobrescreve_arquivo_humano(tmp_path, entradas):
    _, amostra_path, manifesto, humanos = entradas
    originais = _snapshot(amostra_path, manifesto, humanos)
    saida = tmp_path / "colisao"
    with pytest.raises(ValueError, match="substituir"):
        preparacao.executar(amostra_path, humanos, saida, humanos["aulus"])
    assert not saida.exists()
    assert _snapshot(amostra_path, manifesto, humanos) == originais


def test_referencia_invalida_falha_antes_de_criar_saidas(tmp_path, entradas, monkeypatch):
    _, amostra_path, _, humanos = entradas

    def rejeitar(*args):
        raise ValueError("Hash de referência não corresponde.")

    monkeypatch.setattr(gerar_amostra_rotulagem, "validar_referencia", rejeitar)
    saida = tmp_path / "referencia_invalida"
    with pytest.raises(ValueError, match="referência"):
        preparacao.executar(amostra_path, humanos, saida)
    assert not saida.exists()


def test_cli_distingue_preparacao_valida_de_contrato_invalido(tmp_path, entradas, capsys):
    _, amostra_path, _, humanos = entradas
    args = ["--amostra", str(amostra_path)]
    for nome, path in humanos.items():
        args += [f"--{nome}", str(path)]
    assert preparacao.main([*args, "--saida", str(tmp_path / "cli_vazio")]) == 0
    assert "0/3" in capsys.readouterr().out
    humanos["maria"].write_text("schema_invalido\n", encoding="utf-8")
    assert preparacao.main([*args, "--saida", str(tmp_path / "cli_invalido")]) == 2
