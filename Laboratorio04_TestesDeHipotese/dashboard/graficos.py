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


def construir_dados_g3(dados_erro_tipo_1: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara a estrutura analítica padronizada do Gráfico G3 para o frontend.

    Exibe o Erro Tipo I (taxa de falso positivo) de Welch vs. Mann-Whitney
    em 5 situações simuladas sob H0, com linha de referência em 5% (alfa=0.05).
    """
    cenarios = dados_erro_tipo_1.get("cenarios", [])
    labels = [c["cenario_nome"] for c in cenarios]
    welch_rates = [c["taxa_welch"] for c in cenarios]
    mw_rates = [c["taxa_mw"] for c in cenarios]

    return {
        "titulo": "Gráfico G3: Taxa de Erro Tipo I sob H₀ em Diferentes Cenários",
        "eixo_x_nome": "Cenário Simulado",
        "eixo_y_nome": "Taxa de Falso Positivo (%)",
        "alpha_nominal": dados_erro_tipo_1.get("alpha_nominal", 5.0),
        "n_simulacoes": dados_erro_tipo_1.get("n_simulacoes", 10_000),
        "cenarios_labels": labels,
        "taxa_welch": welch_rates,
        "taxa_mw": mw_rates,
        "cor_welch": "#1677c8",
        "cor_mw": "#ec9b24",
        "cor_linha_alfa": "#e36b57",
        "cenarios_detalhes": cenarios,
        "texto_explicativo": dados_erro_tipo_1.get(
            "conclusao_texto",
            "Sob H₀, o teste de Mann-Whitney U manteve taxas de erro Tipo I extremamente estáveis e aderentes aos 5% nominais em todos os cenários. O teste t de Welch revelou-se ligeiramente conservador em dados assimétricos e contaminados com outliers (~3,7%), mantendo rigor em dados estritamente gaussianos.",
        ),
    }


def construir_dados_g4(dados_poder: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara a estrutura analítica padronizada do Gráfico G4 para o frontend.

    Exibe as curvas de poder (proporção de rejeições vs tamanho do efeito delta)
    para ambos os testes simultaneamente, com seletor interativo de cenários.
    """
    cenarios = dados_poder.get("cenarios", {})
    deltas = dados_poder.get("deltas", [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5])

    return {
        "titulo": "Gráfico G4: Curvas de Poder Estatístico (Rejeições vs. Tamanho do Efeito)",
        "eixo_x_nome": "Tamanho do Efeito (δ)",
        "eixo_y_nome": "Proporção de Rejeições / Poder Estatístico (%)",
        "limiar_poder_recomendado": 80.0,
        "deltas": deltas,
        "cor_welch": "#1677c8",
        "cor_mw": "#ec9b24",
        "cor_linha_80": "#10b981",
        "cenarios": cenarios,
        "cenario_padrao": "lognormal_base",
        "texto_explicativo": dados_poder.get(
            "conclusao_texto",
            "Para distribuições normais perfeitas, o teste paramétrico t de Welch possui leve superioridade de poder. Contudo, em distribuições empíricas de software (assimétricas com cauda longa e outliers), o teste de Mann-Whitney U detecta o efeito significativamente mais cedo, alcançando 80% de poder com amostras substancialmente menores.",
        ),
    }


def gerar_figura_plotly_g3(dados_g3: Dict[str, Any]) -> Any:
    """Gera figura Plotly do Gráfico G3 caso o pacote esteja disponível."""
    if not PLOTLY_AVAILABLE:
        return None

    labels = dados_g3["cenarios_labels"]
    w_rates = dados_g3["taxa_welch"]
    mw_rates = dados_g3["taxa_mw"]
    alfa = dados_g3["alpha_nominal"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=w_rates,
            name="t-Student (Welch)",
            marker_color=dados_g3.get("cor_welch", "#1677c8"),
            text=[f"{v:.1f}%" for v in w_rates],
            textposition="auto",
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=mw_rates,
            name="Mann-Whitney U",
            marker_color=dados_g3.get("cor_mw", "#ec9b24"),
            text=[f"{v:.1f}%" for v in mw_rates],
            textposition="auto",
        )
    )

    fig.add_hline(
        y=alfa,
        line_dash="dash",
        line_color=dados_g3.get("cor_linha_alfa", "#e36b57"),
        line_width=2,
        annotation_text=f"Nível Nominal α = {alfa:.0f}%",
        annotation_position="top left",
    )

    fig.update_layout(
        title=dados_g3["titulo"],
        xaxis_title=dados_g3["eixo_x_nome"],
        yaxis_title=dados_g3["eixo_y_nome"],
        barmode="group",
        yaxis=dict(range=[0, max(max(w_rates), max(mw_rates), 8)]),
        template="plotly_white",
        height=450,
    )
    return fig


def gerar_figura_plotly_g4(dados_g4: Dict[str, Any], cenario_id: str = "lognormal_base") -> Any:
    """Gera figura Plotly do Gráfico G4 caso o pacote esteja disponível."""
    if not PLOTLY_AVAILABLE:
        return None

    cenario = dados_g4["cenarios"].get(cenario_id) or next(iter(dados_g4["cenarios"].values()))
    deltas = cenario["deltas"]
    pw = cenario["poder_welch"]
    pmw = cenario["poder_mw"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=deltas,
            y=pw,
            mode="lines+markers",
            name="t-Student (Welch)",
            line=dict(color=dados_g4.get("cor_welch", "#1677c8"), width=3),
            marker=dict(size=7),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=deltas,
            y=pmw,
            mode="lines+markers",
            name="Mann-Whitney U",
            line=dict(color=dados_g4.get("cor_mw", "#ec9b24"), width=3),
            marker=dict(size=7),
        )
    )

    fig.add_hline(
        y=80.0,
        line_dash="dot",
        line_color=dados_g4.get("cor_linha_80", "#10b981"),
        line_width=1.5,
        annotation_text="Poder Convencional (80%)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=f"Gráfico G4: Curvas de Poder — {cenario['nome']}",
        xaxis_title=dados_g4["eixo_x_nome"],
        yaxis_title=dados_g4["eixo_y_nome"],
        yaxis=dict(range=[0, 105]),
        template="plotly_white",
        height=450,
    )
    return fig

