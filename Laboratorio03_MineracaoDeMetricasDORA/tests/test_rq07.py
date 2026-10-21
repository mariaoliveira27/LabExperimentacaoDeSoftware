"""
Testes unitários para o módulo metricas.analise_rq07 (RQ07 - Sensibilidade DORA).
Responsável: Vinícius (Issue #82 / Card #82).
"""

import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from metricas.analise_rq07 import (
    interpretar_kappa_cohen,
    classificar_combinacao,
    calcular_concordancia_par,
    gerar_matriz_transicao,
    _df_para_markdown,
    executar_rq07,
    TIERS_ORDENADOS,
)


def test_interpretar_kappa_cohen():
    assert interpretar_kappa_cohen(float("nan")) == "Indefinido"
    assert "Pobre" in interpretar_kappa_cohen(-0.1)
    assert "Leve" in interpretar_kappa_cohen(0.15)
    assert "Razoável" in interpretar_kappa_cohen(0.35)
    assert "Moderada" in interpretar_kappa_cohen(0.55)
    assert "Substancial" in interpretar_kappa_cohen(0.75)
    assert "Quase perfeita" in interpretar_kappa_cohen(0.95)


def test_classificar_combinacao_c1():
    # C1: df_c1_releases, lt_c1_variante_a, cfr_c1_variante_a, recovery_hours
    # Elite example
    row = pd.Series({
        "df_c1_releases": 10.0,
        "lt_c1_variante_a": 0.5,
        "cfr_c1_variante_a": 0.02,
        "recovery_hours": 0.5,
    })
    tier, det = classificar_combinacao(row, "C1")
    assert tier == "Elite"
    assert det["deployment_frequency"] == "Elite"


def test_classificar_combinacao_c2():
    # C2: df_c2_prereleases, lt_c2_variante_b, cfr_c2_variante_b, tempo_recuperacao_mediana_horas
    row = pd.Series({
        "df_c2_prereleases": 0.1,  # Low/Medium
        "lt_c2_variante_b": 5.0,   # High
        "cfr_c2_variante_b": 0.10,  # High
        "tempo_recuperacao_mediana_horas": 12.0, # High
    })
    tier, det = classificar_combinacao(row, "C2")
    assert tier in TIERS_ORDENADOS


def test_classificar_combinacao_c3():
    # C3: df_c3_tags, lt_c3_variante_b, cfr_c3_variante_a, recovery_hours
    row = pd.Series({
        "df_c3_tags": 2.0,
        "lt_c3_variante_b": 20.0,
        "cfr_c3_variante_a": 0.05,
        "recovery_hours": 100.0,
    })
    tier, det = classificar_combinacao(row, "C3")
    assert tier in TIERS_ORDENADOS


def test_classificar_combinacao_invalida():
    row = pd.Series({"df_c1_releases": 1.0})
    with pytest.raises(ValueError, match="Combinação desconhecida"):
        classificar_combinacao(row, "C99")


def test_calcular_concordancia_par_vazio():
    res = calcular_concordancia_par([], [], "C1", "C2")
    assert res["total"] == 0
    assert res["pct_concordancia"] == 0.0
    assert res["interpretacao"] == "Sem dados"


def test_calcular_concordancia_par_identicos():
    y1 = ["Elite", "High", "Medium", "Low"]
    y2 = ["Elite", "High", "Medium", "Low"]
    res = calcular_concordancia_par(y1, y2, "C1", "C2")
    assert res["total"] == 4
    assert res["mudaram"] == 0
    assert res["pct_concordancia"] == 100.0
    assert res["pct_mudanca"] == 0.0
    assert math.isclose(res["kappa_linear"], 1.0, rel_tol=1e-3)


def test_calcular_concordancia_par_com_mudancas():
    y1 = ["High", "High", "Medium", "Medium"]
    y2 = ["High", "Medium", "Medium", "Low"]
    res = calcular_concordancia_par(y1, y2, "C1", "C2")
    assert res["total"] == 4
    assert res["mudaram"] == 2
    assert res["pct_concordancia"] == 50.0
    assert res["pct_mudanca"] == 50.0
    assert res["kappa_linear"] is not None


def test_gerar_matriz_transicao():
    y1 = ["Elite", "High", "Medium"]
    y2 = ["Elite", "Medium", "Medium"]
    matriz = gerar_matriz_transicao(y1, y2, "C1", "C2")
    assert matriz.shape == (4, 4)
    assert "C1_Elite" in matriz.index
    assert "C2_Elite" in matriz.columns
    assert matriz.loc["C1_Elite", "C2_Elite"] == 1
    assert matriz.loc["C1_High", "C2_Medium"] == 1


def test_df_para_markdown():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, index=["row1", "row2"])
    md = _df_para_markdown(df)
    assert "| Patamar | A | B |" in md
    assert "| row1 | 1 | 3 |" in md
    assert "| row2 | 2 | 4 |" in md


def test_executar_rq07_pipeline(tmp_path):
    # Cria dataset sintético para testar pipeline end-to-end em diretório temporário
    mock_data = {
        "repo": ["repo1", "repo2", "repo3", "repo4"],
        "df_c1_releases": [5.0, 1.0, 0.2, 0.01],
        "lt_c1_variante_a": [0.5, 3.0, 15.0, 45.0],
        "cfr_c1_variante_a": [0.01, 0.05, 0.15, 0.35],
        "df_c2_prereleases": [5.0, 2.0, 0.5, 0.05],
        "lt_c2_variante_b": [0.2, 1.0, 5.0, 20.0],
        "cfr_c2_variante_b": [0.02, 0.04, 0.10, 0.25],
        "df_c3_tags": [6.0, 2.5, 0.6, 0.08],
        "lt_c3_variante_b": [0.2, 1.0, 5.0, 20.0],
        "cfr_c3_variante_a": [0.01, 0.05, 0.15, 0.35],
        "recovery_hours": [0.5, 4.0, 15.0, 50.0],
    }
    csv_file = tmp_path / "mock_rq07.csv"
    pd.DataFrame(mock_data).to_csv(csv_file, index=False)

    out_dir = tmp_path / "output"
    graf_dir = tmp_path / "graficos"

    resultado = executar_rq07(
        caminho_csv=str(csv_file),
        output_dir=str(out_dir),
        graficos_dir=str(graf_dir),
    )

    assert "df_pares" in resultado
    assert "df_distrib" in resultado
    assert (out_dir / "tabela_rq07_sensibilidade.csv").exists()
    assert (out_dir / "tabela_rq07_sensibilidade.md").exists()
    assert (out_dir / "tabela_rq07_transicoes.csv").exists()
    assert (graf_dir / "rq07_distribuicao_tiers_combinacoes.png").exists()
    assert (graf_dir / "rq07_matriz_transicao_sensibilidade.png").exists()
