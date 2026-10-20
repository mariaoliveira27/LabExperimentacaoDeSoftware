"""Fixtures artificiais verificam contratos; não são uma amostra empírica."""

import csv
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from rotulagem import (
    CATEGORIAS, JULGAMENTOS, METADADOS, gerar_rotulos, ler_csv, main,
    validar_amostra, validar_rotulos,
)


@pytest.fixture
def amostra_rotulagem():
    rows = []
    for repo in range(60):
        nome = f"fixture/projeto-{repo:02d}"
        for release in range(5):
            tag = f"v1.{release}.0"
            anterior = f"v1.{release - 1}.0" if release else ""
            url = f"https://github.com/{nome}/releases/tag/{tag}"
            rows.append({
                "full_name": nome,
                "release_id": str(repo * 5 + release + 1),
                "published_at": f"2025-01-{release + 1:02d}T12:00:00Z",
                "tag_name": tag,
                "html_url": url,
                "release_notes_url": url,
                "commits_url": f"https://github.com/{nome}/commits/{tag}",
                "previous_tag": anterior,
            })
    return rows


@pytest.fixture
def rotulos_completos(amostra_rotulagem):
    rows = deepcopy(amostra_rotulagem)
    for row in rows:
        row.update({
            "tipo_projeto": "aplicação/serviço", "entrega_real": "sim",
            "corretiva": "não", "justificativa": "Decisão fictícia de teste.",
            "evidencia": row["release_notes_url"],
        })
    return rows


def escrever_csv(path, rows, campos=METADADOS):
    with path.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def test_amostra_exige_60_por_5(amostra_rotulagem):
    validar_amostra(amostra_rotulagem)


def test_amostra_insuficiente(amostra_rotulagem):
    with pytest.raises(ValueError, match="300 releases"):
        validar_amostra(amostra_rotulagem[:-1])


def test_amostra_distribuicao_incorreta(amostra_rotulagem):
    amostra_rotulagem[0]["full_name"] = "fixture/projeto-01"
    for campo in ("html_url", "release_notes_url", "commits_url"):
        amostra_rotulagem[0][campo] = amostra_rotulagem[0][campo].replace(
            "projeto-00", "projeto-01",
        )
    with pytest.raises(ValueError, match="5 releases por repositório"):
        validar_amostra(amostra_rotulagem)


def test_amostra_rejeita_variantes_de_caixa_do_mesmo_repositorio(amostra_rotulagem):
    for row in amostra_rotulagem[:2]:
        nome_original = row["full_name"]
        row["full_name"] = nome_original.upper()
        for campo in ("html_url", "release_notes_url", "commits_url"):
            row[campo] = row[campo].replace(nome_original, row["full_name"])
    with pytest.raises(ValueError, match="variantes de caixa"):
        validar_amostra(amostra_rotulagem)


def test_variantes_de_caixa_impedem_validacao_humana(amostra_rotulagem, rotulos_completos):
    row = amostra_rotulagem[0]
    nome_original = row["full_name"]
    row["full_name"] = nome_original.upper()
    for campo in ("html_url", "release_notes_url", "commits_url"):
        row[campo] = row[campo].replace(nome_original, row["full_name"])
    with pytest.raises(ValueError, match="variantes de caixa"):
        validar_rotulos(amostra_rotulagem, rotulos_completos)


@pytest.mark.parametrize("valor", ["", "abc", "0", "-1", "001"])
def test_amostra_id_invalido(amostra_rotulagem, valor):
    amostra_rotulagem[0]["release_id"] = valor
    with pytest.raises(ValueError, match="release_id"):
        validar_amostra(amostra_rotulagem)


def test_amostra_duplicada(amostra_rotulagem):
    amostra_rotulagem[1] = deepcopy(amostra_rotulagem[0])
    with pytest.raises(ValueError, match="duplicada"):
        validar_amostra(amostra_rotulagem)


@pytest.mark.parametrize("campo,valor", [
    ("full_name", "sem-repositorio"),
    ("published_at", "2025-99-99"),
    ("published_at", "2025-01-01"),
    ("published_at", "2025-01-01T00:00:00"),
    ("tag_name", ""),
    ("html_url", ""),
    ("html_url", "https://github.com/outro/repo/releases/tag/v1.0.0"),
    ("release_notes_url", "apenas texto"),
    ("commits_url", "file:///inventado"),
])
def test_amostra_metadado_invalido(amostra_rotulagem, campo, valor):
    amostra_rotulagem[0][campo] = valor
    with pytest.raises(ValueError, match=campo):
        validar_amostra(amostra_rotulagem)


def test_rotulos_completos(amostra_rotulagem, rotulos_completos):
    validar_rotulos(amostra_rotulagem, rotulos_completos)


def test_rotulos_independem_da_ordem(amostra_rotulagem, rotulos_completos):
    validar_rotulos(amostra_rotulagem, list(reversed(rotulos_completos)))


@pytest.mark.parametrize("campo", list(CATEGORIAS))
def test_categoria_invalida_mesmo_em_rascunho(
    amostra_rotulagem, rotulos_completos, campo,
):
    rotulos_completos[0][campo] = "categoria-inventada"
    with pytest.raises(ValueError, match="Categoria inválida"):
        validar_rotulos(amostra_rotulagem, rotulos_completos, permitir_vazios=True)


@pytest.mark.parametrize("campo", JULGAMENTOS)
def test_preenchimento_obrigatorio(amostra_rotulagem, rotulos_completos, campo):
    rotulos_completos[0][campo] = "  "
    with pytest.raises(ValueError, match="Rótulo ausente"):
        validar_rotulos(amostra_rotulagem, rotulos_completos)
    validar_rotulos(amostra_rotulagem, rotulos_completos, permitir_vazios=True)


def test_unidade_ausente(amostra_rotulagem, rotulos_completos):
    with pytest.raises(ValueError, match="1 unidades ausentes"):
        validar_rotulos(amostra_rotulagem, rotulos_completos[:-1])


def test_unidade_duplicada(amostra_rotulagem, rotulos_completos):
    rotulos_completos.append(deepcopy(rotulos_completos[0]))
    with pytest.raises(ValueError, match="duplicada"):
        validar_rotulos(amostra_rotulagem, rotulos_completos)


def test_unidade_extra(amostra_rotulagem, rotulos_completos):
    rotulos_completos[0]["release_id"] = "999999"
    with pytest.raises(ValueError, match="1 unidades extras"):
        validar_rotulos(amostra_rotulagem, rotulos_completos)


def test_metadado_alterado(amostra_rotulagem, rotulos_completos):
    rotulos_completos[0]["tag_name"] = "v99.0.0"
    with pytest.raises(ValueError, match="Metadado tag_name alterado"):
        validar_rotulos(amostra_rotulagem, rotulos_completos)


@pytest.mark.parametrize("campo,valor", [
    ("tipo_projeto", "outro"), ("entrega_real", "incerto"),
])
def test_decisao_unica_por_repositorio(
    amostra_rotulagem, rotulos_completos, campo, valor,
):
    rotulos_completos[0][campo] = valor
    with pytest.raises(ValueError, match="Decisões inconsistentes"):
        validar_rotulos(amostra_rotulagem, rotulos_completos, permitir_vazios=True)


def test_coluna_ausente(amostra_rotulagem, rotulos_completos):
    del rotulos_completos[0]["evidencia"]
    with pytest.raises(ValueError, match="colunas ausentes: evidencia"):
        validar_rotulos(amostra_rotulagem, rotulos_completos, permitir_vazios=True)


def test_geracao_rejeita_referencia_que_expoe_julgamentos(
    tmp_path, amostra_rotulagem, rotulos_completos,
):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    for row in rotulos_completos:
        row["heuristica"] = "sim"
    escrever_csv(amostra, rotulos_completos, METADADOS + JULGAMENTOS + ("heuristica",))
    with pytest.raises(ValueError, match="cegamento"):
        gerar_rotulos(amostra, saida)
    assert not saida.exists()


def test_geracao_julgamentos_vazios_exclui_heuristica(tmp_path, amostra_rotulagem):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    for row in amostra_rotulagem:
        row.update({campo: "" for campo in JULGAMENTOS})
        row["heuristica"] = "sim"
    escrever_csv(amostra, amostra_rotulagem, METADADOS + JULGAMENTOS + ("heuristica",))
    gerar_rotulos(amostra, saida)
    gerados = ler_csv(saida)
    assert len(gerados) == 300
    assert all(list(row) == list(METADADOS + JULGAMENTOS) for row in gerados)
    assert all(row[campo] == "" for row in gerados for campo in JULGAMENTOS)
    validar_rotulos(amostra_rotulagem, gerados, permitir_vazios=True)
    with pytest.raises(ValueError, match="Rótulo ausente"):
        validar_rotulos(amostra_rotulagem, gerados)


def test_geracao_preserva_arquivo_existente(tmp_path, amostra_rotulagem):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    escrever_csv(amostra, amostra_rotulagem)
    saida.write_text("decisões humanas existentes", encoding="utf-8")
    with pytest.raises(FileExistsError):
        gerar_rotulos(amostra, saida)
    assert saida.read_text(encoding="utf-8") == "decisões humanas existentes"


def test_geracao_protege_vinicius(tmp_path, amostra_rotulagem):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "ROTULOS_VINICIUS.csv"
    escrever_csv(amostra, amostra_rotulagem)
    with pytest.raises(ValueError, match="rotulos_vinicius.csv"):
        gerar_rotulos(amostra, saida)
    assert not saida.exists()


def test_geracao_amostra_insuficiente_nao_cria_saida(tmp_path, amostra_rotulagem):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    escrever_csv(amostra, amostra_rotulagem[:-1])
    with pytest.raises(ValueError, match="300 releases"):
        gerar_rotulos(amostra, saida)
    assert not saida.exists()


@pytest.mark.parametrize("conteudo", [
    "", "a,a\n1,2\n", "a,b\n1\n", "a,b\n1,2,3\n",
])
def test_leitura_rejeita_csv_ambiguo(tmp_path, conteudo):
    path = tmp_path / "ambiguo.csv"
    path.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ValueError):
        ler_csv(path)


def test_leitura_aceita_bom(tmp_path, amostra_rotulagem):
    path = tmp_path / "bom.csv"
    escrever_csv(path, amostra_rotulagem)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    validar_amostra(ler_csv(path))


def test_cli_geracao_e_validacao_rascunho(tmp_path, amostra_rotulagem, capsys, monkeypatch):
    import gerar_amostra_rotulagem
    monkeypatch.setattr(gerar_amostra_rotulagem, "validar_referencia", lambda *args: None)
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    escrever_csv(amostra, amostra_rotulagem)
    assert main(["gerar", "--amostra", str(amostra), "--saida", str(saida)]) == 0
    assert "pendente de julgamento humano" in capsys.readouterr().out
    validar = ["validar", "--amostra", str(amostra), "--rotulos", str(saida)]
    assert main(validar + ["--rascunho"]) == 0
    assert "Rascunho válido" in capsys.readouterr().out
    assert main(validar) == 2
    assert "Rótulo ausente" in capsys.readouterr().err


def test_cli_rotulagem_completa(tmp_path, amostra_rotulagem, rotulos_completos, monkeypatch):
    import gerar_amostra_rotulagem
    monkeypatch.setattr(gerar_amostra_rotulagem, "validar_referencia", lambda *args: None)
    amostra = tmp_path / "amostra.csv"
    rotulos = tmp_path / "rotulos.csv"
    escrever_csv(amostra, amostra_rotulagem)
    escrever_csv(rotulos, rotulos_completos, METADADOS + JULGAMENTOS)
    assert main(["validar", "--amostra", str(amostra), "--rotulos", str(rotulos)]) == 0


def test_cli_csv_exemplo_sem_manifesto_nao_gera_formulario(tmp_path, amostra_rotulagem, capsys):
    amostra = tmp_path / "amostra.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    escrever_csv(amostra, amostra_rotulagem)
    assert main(["gerar", "--amostra", str(amostra), "--saida", str(saida)]) == 2
    assert "selecao.json" in capsys.readouterr().err
    assert not saida.exists()


@pytest.mark.parametrize("campo,valor", [("corretiva", None), ("evidencia", 42), ("previous_tag", None)])
def test_valores_nao_textuais_nao_sao_rascunhos_validos(amostra_rotulagem, rotulos_completos, campo, valor):
    rotulos_completos[0][campo] = valor
    with pytest.raises(ValueError, match="conter texto"):
        validar_rotulos(amostra_rotulagem, rotulos_completos, permitir_vazios=True)


def test_integracao_sorteio_gera_arquivo_independente(tmp_path):
    from gerar_amostra_rotulagem import sortear

    # População sintética exclusiva deste teste; nenhum dado empírico é criado.
    aprovados = []
    releases = {}
    for indice in range(300):
        nome = f"fixture/projeto-{indice:03d}"
        aprovados.append({"full_name": nome, "total_releases_janela": "6"})
        releases[nome] = [
            {
                "id": indice * 6 + release + 1,
                "published_at": f"2025-01-{release + 1:02d}T12:00:00Z",
                "tag_name": f"v1.{release}.0",
                "html_url": f"https://github.com/{nome}/releases/tag/v1.{release}.0",
                "draft": False,
                "prerelease": False,
            }
            for release in range(6)
        ]
    inicio = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fim = datetime(2025, 2, 1, tzinfo=timezone.utc)
    rows, _ = sortear(aprovados, releases, inicio, fim)
    validar_amostra(rows)
    comum = tmp_path / "amostra_comum.csv"
    saida = tmp_path / "rotulos_aulus.csv"
    escrever_csv(comum, rows, METADADOS + JULGAMENTOS)
    gerar_rotulos(comum, saida)
    gerados = ler_csv(saida)
    validar_rotulos(rows, gerados, permitir_vazios=True)
    assert all(row[campo] == "" for row in gerados for campo in JULGAMENTOS)
