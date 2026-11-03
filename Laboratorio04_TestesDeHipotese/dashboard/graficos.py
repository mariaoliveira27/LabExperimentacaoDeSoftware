"""Módulo de Gráficos G1 e G2 para o Dashboard do Lab 04 (Lab04S01)
Implementa:
- Gráfico G1: Histogramas comparativos dos dados reais ao lado dos simulados.
- Gráfico G2: Distribuição da estatística do teste sob H0 com região de rejeição sombreada e p-valor.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import numpy as np
from scipy import stats

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def executar_teste_estatistico(
    grupo1: np.ndarray,
    grupo2: np.ndarray,
    tipo_teste: str = "t-Student",
) -> Dict[str, Any]:
    """Aplica o teste de hipótese escolhido (t-Student ou Mann-Whitney U)

    e retorna a estatística observada, o p-valor e os graus de liberdade.
    """
    g1 = grupo1[~np.isnan(grupo1)]
    g2 = grupo2[~np.isnan(grupo2)]

    if len(g1) < 2 or len(g2) < 2:
        return {
            "stat_obs": 0.0,
            "p_valor": 1.0,
            "df": 2.0,
            "teste": tipo_teste,
            "n1": len(g1),
            "n2": len(g2),
        }

    if tipo_teste == "t-Student":
        res = stats.ttest_ind(g1, g2, equal_var=False)  # Welch's t-test
        # Welch-Satterthwaite df
        s1, s2 = float(np.var(g1, ddof=1)), float(np.var(g2, ddof=1))
        n1, n2 = len(g1), len(g2)
        vn1, vn2 = s1 / n1, s2 / n2
        df_num = (vn1 + vn2) ** 2
        df_den = (vn1**2 / (n1 - 1)) + (vn2**2 / (n2 - 1)) if (n1 > 1 and n2 > 1) else 1.0
        df = df_num / df_den if df_den > 0 else float(n1 + n2 - 2)

        return {
            "stat_obs": float(res.statistic),
            "p_valor": float(res.pvalue),
            "df": float(df),
            "teste": "t-Student (Welch)",
            "n1": n1,
            "n2": n2,
        }
    else:  # Mann-Whitney U
        res = stats.mannwhitneyu(g1, g2, alternative="two-sided")
        n1, n2 = len(g1), len(g2)
        u_mean = (n1 * n2) / 2.0
        u_std = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
        z_obs = (res.statistic - u_mean) / u_std if u_std > 0 else 0.0

        return {
            "stat_obs": float(z_obs),
            "u_stat": float(res.statistic),
            "p_valor": float(res.pvalue),
            "df": float(n1 + n2 - 2),
            "teste": "Mann-Whitney U (Z assintótico)",
            "n1": n1,
            "n2": n2,
        }


def construir_dados_g1(
    dados_reais: np.ndarray,
    dados_simulados: np.ndarray,
    nbins: int = 25,
) -> Dict[str, Any]:
    """Prepara os dados analíticos estruturados para renderização do Gráfico G1

    (histogramas comparativos e densidade) no frontend web ou em SVG/Plotly.
    """
    reais_limpos = dados_reais[~np.isnan(dados_reais)]
    sim_limpos = dados_simulados[~np.isnan(dados_simulados)]

    # Determinar faixa comum de valores
    val_min = min(float(np.min(reais_limpos)), float(np.min(sim_limpos)))
    val_max = max(float(np.max(reais_limpos)), float(np.max(sim_limpos)))

    bins_edges = np.linspace(val_min, val_max, nbins + 1)
    hist_r, _ = np.histogram(reais_limpos, bins=bins_edges, density=True)
    hist_s, _ = np.histogram(sim_limpos, bins=bins_edges, density=True)

    bin_centers = 0.5 * (bins_edges[:-1] + bins_edges[1:])

    return {
        "bin_edges": [round(float(x), 3) for x in bins_edges],
        "bin_centers": [round(float(x), 3) for x in bin_centers],
        "densidade_real": [round(float(y), 5) for y in hist_r],
        "densidade_sim": [round(float(y), 5) for y in hist_s],
        "valores_reais": [round(float(x), 2) for x in reais_limpos.tolist()],
        "valores_simulados": [round(float(x), 2) for x in sim_limpos.tolist()],
        "stats_real": {
            "media": round(float(np.mean(reais_limpos)), 2),
            "mediana": round(float(np.median(reais_limpos)), 2),
            "dp": round(float(np.std(reais_limpos, ddof=1)), 2),
            "skew": round(float(stats.skew(reais_limpos)), 2),
            "n": len(reais_limpos),
        },
        "stats_sim": {
            "media": round(float(np.mean(sim_limpos)), 2),
            "mediana": round(float(np.median(sim_limpos)), 2),
            "dp": round(float(np.std(sim_limpos, ddof=1)), 2),
            "skew": round(float(stats.skew(sim_limpos)), 2),
            "n": len(sim_limpos),
        },
    }


def construir_dados_g2(
    stat_obs: float,
    p_valor: float,
    graus_liberdade: float = 30.0,
    alpha: float = 0.05,
    tipo_teste: str = "t-Student",
) -> Dict[str, Any]:
    """Prepara a curva e as regiões de rejeição da distribuição sob H0 para o Gráfico G2."""
    df_val = max(graus_liberdade, 2.0)

    if tipo_teste == "t-Student":
        dist_h0 = stats.t(df=df_val)
        critico = float(stats.t.ppf(1 - alpha / 2, df=df_val))
        nome_stat = "t"
        titulo = f"Distribuição t de Student sob H₀ (gl={df_val:.1f})"
    else:
        dist_h0 = stats.norm(loc=0, scale=1)
        critico = float(stats.norm.ppf(1 - alpha / 2))
        nome_stat = "Z"
        titulo = "Distribuição Normal Padrão N(0, 1) sob H₀"

    limite_x = max(4.0, abs(stat_obs) + 1.2, critico + 1.5)
    x_grid = np.linspace(-limite_x, limite_x, 500)
    pdf_grid = dist_h0.pdf(x_grid)

    rejeita = bool(p_valor < alpha)

    return {
        "tipo_teste": tipo_teste,
        "titulo_distribuicao": titulo,
        "nome_stat": nome_stat,
        "stat_obs": round(float(stat_obs), 4),
        "p_valor": float(p_valor),
        "alpha": float(alpha),
        "valor_critico": round(float(critico), 4),
        "graus_liberdade": round(float(df_val), 1),
        "rejeita_h0": rejeita,
        "x_grid": [round(float(x), 4) for x in x_grid],
        "pdf_grid": [round(float(y), 5) for y in pdf_grid],
        "regiao_critica_esquerda": [-float(limite_x), round(-critico, 4)],
        "regiao_critica_direita": [round(critico, 4), float(limite_x)],
    }


def gerar_figura_plotly_g1(
    dados_reais: np.ndarray,
    dados_simulados: np.ndarray,
    nome_metrica: str = "Métrica",
    modo: str = "Lado a Lado",
) -> Any:
    """Gera figura Plotly do Gráfico G1 caso o pacote esteja disponível."""
    if not PLOTLY_AVAILABLE:
        return None

    reais = dados_reais[~np.isnan(dados_reais)]
    sim = dados_simulados[~np.isnan(dados_simulados)]

    if modo == "Lado a Lado":
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=[f"Dados Reais (N={len(reais)})", f"Dados Simulados (N={len(sim)})"],
            horizontal_spacing=0.1,
        )
        fig.add_trace(
            go.Histogram(
                x=reais,
                name="Real",
                marker_color="#1677c8",
                histnorm="probability density",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Histogram(
                x=sim,
                name="Simulado",
                marker_color="#ec9b24",
                histnorm="probability density",
            ),
            row=1,
            col=2,
        )
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=reais,
                name=f"Real (N={len(reais)})",
                marker_color="#1677c8",
                opacity=0.65,
                histnorm="probability density",
            )
        )
        fig.add_trace(
            go.Histogram(
                x=sim,
                name=f"Simulado (N={len(sim)})",
                marker_color="#ec9b24",
                opacity=0.65,
                histnorm="probability density",
            )
        )
        fig.update_layout(barmode="overlay")

    fig.update_layout(
        title=f"Gráfico G1: Comparativo da Distribuição Real vs. Simulada — {nome_metrica}",
        template="plotly_white",
        height=450,
    )
    return fig


def gerar_figura_plotly_g2(
    stat_obs: float,
    p_valor: float,
    graus_liberdade: float = 30.0,
    alpha: float = 0.05,
    tipo_teste: str = "t-Student",
) -> Any:
    """Gera figura Plotly do Gráfico G2 caso o pacote esteja disponível."""
    if not PLOTLY_AVAILABLE:
        return None

    dados_g2 = construir_dados_g2(stat_obs, p_valor, graus_liberdade, alpha, tipo_teste)
    x_vals = np.array(dados_g2["x_grid"])
    y_vals = np.array(dados_g2["pdf_grid"])
    crit = dados_g2["valor_critico"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            line=dict(color="#102a43", width=2.5),
            name="Densidade sob H₀",
        )
    )

    # Região de rejeição esquerda
    mask_left = x_vals <= -crit
    fig.add_trace(
        go.Scatter(
            x=x_vals[mask_left],
            y=y_vals[mask_left],
            fill="tozeroy",
            fillcolor="rgba(227, 107, 87, 0.4)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"Região Crítica (α/2={alpha/2:.3f})",
        )
    )
    # Região de rejeição direita
    mask_right = x_vals >= crit
    fig.add_trace(
        go.Scatter(
            x=x_vals[mask_right],
            y=y_vals[mask_right],
            fill="tozeroy",
            fillcolor="rgba(227, 107, 87, 0.4)",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
        )
    )

    # Linha da estatística observada
    fig.add_vline(
        x=stat_obs,
        line_dash="solid",
        line_color="#7357d8" if not dados_g2["rejeita_h0"] else "#e36b57",
        line_width=3,
        annotation_text=f"stat_obs = {stat_obs:.3f} (p={p_valor:.4e})",
    )

    fig.update_layout(
        title=f"Gráfico G2: {dados_g2['titulo_distribuicao']} (Região Crítica sombreada)",
        xaxis_title=f"Estatística do Teste ({dados_g2['nome_stat']})",
        yaxis_title="Densidade",
        template="plotly_white",
        height=450,
    )
    return fig
