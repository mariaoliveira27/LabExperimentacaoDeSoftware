"""
Testes unitários e de integração para as análises de RQ05 e RQ06 (Métricas DORA).
Responsável: Maria (Seleção, Infraestrutura e Integração).

Valida:
1. Correlação de Spearman e IC 95% via transformação z de Fisher (RQ05)
2. Teste omnibus de Kruskal-Wallis e tamanho de efeito Epsilon-quadrado (RQ06)
3. Comparação post-hoc de Mann-Whitney com Cliff's Delta (Romano et al., 2006)
4. Correção de Holm-Bonferroni para comparações múltiplas
5. Integridade do dataset consolidado e dados de RQ07 para Vinícius
"""

import math
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from metricas.analise_rq05_rq06 import (
    calcular_spearman_com_ic,
    calcular_cliffs_delta,
    executar_rq05,
    executar_rq06,
)


def test_spearman_perfeito_positivo():
    x = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    y = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    res = calcular_spearman_com_ic(x, y)
    assert res["n"] == 10
    assert pytest.approx(res["rho"], abs=1e-3) == 1.0
    assert res["p_valor"] < 1e-4
    assert res["ci_inferior"] > 0.90
    assert "positiva" in res["interpretacao"]


def test_spearman_perfeito_negativo():
    x = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    y = pd.Series([100, 90, 80, 70, 60, 50, 40, 30, 20, 10])
    res = calcular_spearman_com_ic(x, y)
    assert res["n"] == 10
    assert pytest.approx(res["rho"], abs=1e-3) == -1.0
    assert res["p_valor"] < 1e-4
    assert res["ci_superior"] < -0.90
    assert "negativa" in res["interpretacao"]


def test_spearman_amostra_pequena():
    x = pd.Series([1, 2])
    y = pd.Series([3, 4])
    res = calcular_spearman_com_ic(x, y)
    assert res["n"] == 2
    assert np.isnan(res["rho"])
    assert "insuficiente" in res["interpretacao"].lower()


def test_spearman_com_nans():
    x = pd.Series([1, 2, None, 4, 5, 6, 7, 8, 9, 10])
    y = pd.Series([10, 20, 30, 40, None, 60, 70, 80, 90, 100])
    res = calcular_spearman_com_ic(x, y)
    assert res["n"] == 8
    assert not np.isnan(res["rho"])


def test_cliffs_delta_desprezivel():
    # Dois grupos idênticos
    g1 = [10.0, 11.0, 12.0, 13.0, 14.0]
    g2 = [10.0, 11.0, 12.0, 13.0, 14.0]
    delta, mag = calcular_cliffs_delta(g1, g2)
    assert abs(delta) < 0.147
    assert mag == "desprezível"


def test_cliffs_delta_grande():
    # g1 estritamente superior a g2
    g1 = [100.0, 101.0, 102.0, 103.0, 104.0]
    g2 = [1.0, 2.0, 3.0, 4.0, 5.0]
    delta, mag = calcular_cliffs_delta(g1, g2)
    assert delta == 1.0
    assert mag == "grande"


def test_cliffs_delta_inverso():
    # g1 estritamente inferior a g2
    g1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    g2 = [100.0, 101.0, 102.0, 103.0, 104.0]
    delta, mag = calcular_cliffs_delta(g1, g2)
    assert delta == -1.0
    assert mag == "grande"


def test_executar_rq05_dataset_real(tmp_path):
    csv_path = Path("data/output/repositorios_aprovados.csv")
    assert csv_path.exists(), "Dataset principal de repositórios aprovados deve existir."
    df = pd.read_csv(csv_path)

    res = executar_rq05(df, output_dir=tmp_path)
    assert len(res) == 2

    # Variante (a) - Proxy CI
    assert res[0]["variante"] == "Variante (a) — Proxy de CI"
    assert res[0]["n"] == 300
    assert -1.0 <= res[0]["rho"] <= 1.0
    assert 0.0 <= res[0]["p_valor"] <= 1.0
    assert res[0]["ci_inferior"] <= res[0]["rho"] <= res[0]["ci_superior"]

    # Variante (b) - Proxy Releases
    assert res[1]["variante"] == "Variante (b) — Proxy de Releases"
    assert res[1]["n"] == 300
    assert -1.0 <= res[1]["rho"] <= 1.0
    assert 0.0 <= res[1]["p_valor"] <= 1.0
    assert res[1]["ci_inferior"] <= res[1]["rho"] <= res[1]["ci_superior"]

    # Arquivos exportados
    assert (tmp_path / "tabela_rq05_spearman.csv").exists()
    assert (tmp_path / "tabela_rq05_spearman.md").exists()


def test_executar_rq06_dataset_real(tmp_path):
    csv_path = Path("data/output/repositorios_aprovados.csv")
    df = pd.read_csv(csv_path)

    res_om, res_ph = executar_rq06(df, output_dir=tmp_path)

    # Omnibus
    assert len(res_om) == 30  # 5 fatores x 6 métricas
    for item in res_om:
        assert item["n_total"] == 300
        assert item["k_grupos"] >= 2
        assert item["epsilon_quadrado"] >= 0.0
        assert item["epsilon_quadrado"] <= 1.0
        assert not np.isnan(item["p_valor_holm"])
        # Holm p-valor deve ser >= p-valor bruto
        assert item["p_valor_holm"] >= item["p_valor_bruto"] - 1e-9

    # Post-hoc
    assert len(res_ph) > 0
    for ph in res_ph:
        assert -1.0 <= ph["cliffs_delta"] <= 1.0
        assert ph["magnitude_delta"] in ("desprezível", "pequeno", "médio", "grande")

    # Arquivos exportados
    assert (tmp_path / "tabela_rq06_kruskal_holm.csv").exists()
    assert (tmp_path / "tabela_rq06_kruskal_holm.md").exists()
    assert (tmp_path / "tabela_rq06_posthoc_cliff.csv").exists()


def test_dataset_consolidado_integridade():
    csv_path = Path("data/output/repositorios_aprovados.csv")
    df = pd.read_csv(csv_path)

    assert len(df) == 300
    # Verificação de colunas obrigatórias
    colunas_obrigatorias = [
        "full_name", "owner", "repo", "stars", "language", "default_branch",
        "contributors_count", "created_at", "idade_dias", "idade_anos",
        "total_releases_janela", "total_runs_janela", "deployment_frequency_semana",
        "lead_time_release_mediana_dias", "lead_time_commit_mediana_dias",
        "cfr_ci_proxy", "cfr_releases_proxy", "tempo_recuperacao_mediana_horas",
        "origem_coleta", "origem_metricas_estabilidade", "escopo_contagem_runs",
        "runs_sucessos", "runs_falhas", "runs_ignorados",
        "episodios_recuperados", "episodios_censurados", "proporcao_episodios_censurados",
        "rework_rate", "tier_dora_geral", "tier_deployment_frequency",
        "tier_lead_time", "tier_cfr", "tier_recovery_time",
        "total_prereleases_janela", "total_releases_com_prereleases_janela",
        "deployment_frequency_prereleases_semana", "total_tags_janela",
        "deployment_frequency_tags_semana",
    ]
    for col in colunas_obrigatorias:
        assert col in df.columns, f"Coluna obrigatória ausente: {col}"
        assert df[col].notna().all(), f"Coluna {col} não pode conter valores nulos"

    # Critérios mínimos
    assert (df["stars"] >= 1000).all()
    assert (df["total_releases_janela"] >= 5).all()
    assert (df["total_runs_janela"] >= 50).all()
    assert (df["origem_coleta"] == "github_api").all()
    assert (df["origem_metricas_estabilidade"] == "workflow_runs").all()

    # Consistência aritmética das contagens
    assert (df["total_runs_janela"] == df["runs_sucessos"] + df["runs_falhas"]).all()
    assert (df["total_releases_com_prereleases_janela"] == df["total_releases_janela"] + df["total_prereleases_janela"]).all()


def test_dados_rq07_sensibilidade():
    rq07_path = Path("data/output/dados_rq07_sensibilidade.csv")
    assert rq07_path.exists(), "Dataset da RQ07 para Vinícius deve existir."
    df_rq07 = pd.read_csv(rq07_path)

    assert len(df_rq07) == 300
    for col in ("tier_c1_referencia", "tier_c2_prereleases", "tier_c3_tags", "mudou_c1_c2", "mudou_c1_c3"):
        assert col in df_rq07.columns
        assert df_rq07[col].notna().all()
