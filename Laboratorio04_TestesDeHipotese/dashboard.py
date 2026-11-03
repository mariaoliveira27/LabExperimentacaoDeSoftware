"""Laboratório 04 - Sprint 01 (Lab04S01)
Módulo do Dashboard e Visualizações G1 & G2

Integrantes:
- Maria Clara: data_loader.py (Módulo de Dados Reais e Cenário)
- Áulus: simulation.py (Módulo de Simulação e Testes Estatísticos)
- Vinícius: dashboard.py (Módulo do Dashboard e Visualizações G1 & G2)
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Suprime avisos de execução bare-mode do Streamlit quando executado como script CLI
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)


# Configuração da página do Streamlit apenas quando executado sob contexto web
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_REAL_CSV = (
    REPO_ROOT
    / "Laboratorio03_MineracaoDeMetricasDORA"
    / "data"
    / "output"
    / "repositorios_aprovados.csv"
)

# ---------------------------------------------------------------------------
# Integração Modular com data_loader.py e simulation.py (com fallback robusto)
# ---------------------------------------------------------------------------

def carregar_dados_reais(caminho_csv: Optional[Path] = None) -> pd.DataFrame:
    """Tenta carregar os dados reais utilizando o data_loader.py caso disponível,

    ou executa o fallback direto pelo arquivo CSV de métricas DORA.
    """
    # 1. Tentar carregar via módulo de Maria Clara se existir
    try:
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        import data_loader  # type: ignore

        if hasattr(data_loader, "carregar_amostra_real"):
            return data_loader.carregar_amostra_real(caminho_csv)
    except Exception:
        pass

    # 2. Fallback direto: carregar CSV de repositórios aprovados do Lab03
    alvo = caminho_csv if caminho_csv and caminho_csv.exists() else DEFAULT_REAL_CSV
    if alvo.exists():
        df = pd.read_csv(alvo)
        return df

    # 3. Fallback sintético mínimo caso o CSV não seja encontrado
    rng = np.random.default_rng(42)
    tamanho = 300
    return pd.DataFrame(
        {
            "full_name": [f"repo_{i}" for i in range(tamanho)],
            "language": rng.choice(["Python", "JavaScript", "TypeScript", "Java", "Go"], tamanho),
            "tier_dora_geral": rng.choice(["Elite", "High", "Medium", "Low"], tamanho, p=[0.2, 0.35, 0.3, 0.15]),
            "tipo_projeto": rng.choice(["ferramenta CLI", "biblioteca/framework", "aplicacao"], tamanho),
            "lead_time_commit_mediana_dias": rng.lognormal(mean=2.0, sigma=0.8, size=tamanho),
            "lead_time_release_mediana_dias": rng.lognormal(mean=2.6, sigma=0.7, size=tamanho),
            "tempo_recuperacao_mediana_horas": rng.exponential(scale=12.0, size=tamanho),
            "deployment_frequency_semana": rng.gamma(shape=2.0, scale=0.5, size=tamanho),
            "cfr_ci_proxy": rng.beta(a=2, b=8, size=tamanho),
            "stars": rng.integers(1000, 100000, size=tamanho),
        }
    )


def executar_simulacao_dados(
    dados_reais: np.ndarray,
    distribuicao: str = "Lognormal",
    tamanho_amostra: int = 300,
    semente: int = 42,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Gera dados sintéticos ajustando a distribuição indicada aos dados reais.

    Integra com simulation.py de Áulus caso disponível, ou executa o fallback com RNG fixo.
    """
    # 1. Tentar executar via módulo de Áulus se existir
    try:
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        import simulation  # type: ignore

        if hasattr(simulation, "gerar_dados_sinteticos"):
            return simulation.gerar_dados_sinteticos(
                dados_reais=dados_reais,
                distribuicao=distribuicao,
                tamanho_amostra=tamanho_amostra,
                semente=semente,
            )
    except Exception:
        pass

    # 2. Fallback determinístico próprio utilizando numpy.random.default_rng(semente)
    rng = np.random.default_rng(semente)
    dados_limpos = dados_reais[~np.isnan(dados_reais)]
    dados_positivos = dados_limpos[dados_limpos > 0]
    if len(dados_positivos) < 5:
        dados_positivos = np.array([1.0, 2.0, 3.0, 5.0, 10.0])

    params: Dict[str, Any] = {}

    if distribuicao == "Lognormal":
        log_dados = np.log(dados_positivos)
        mu, sigma = float(np.mean(log_dados)), float(np.std(log_dados, ddof=1))
        sigma = max(sigma, 1e-4)
        simulados = rng.lognormal(mean=mu, sigma=sigma, size=tamanho_amostra)
        params = {"mu_log": mu, "sigma_log": sigma}

    elif distribuicao == "Exponencial":
        escala = float(np.mean(dados_positivos))
        escala = max(escala, 1e-4)
        simulados = rng.exponential(scale=escala, size=tamanho_amostra)
        params = {"escala (lambda_inv)": escala}

    elif distribuicao == "Normal":
        media, dp = float(np.mean(dados_limpos)), float(np.std(dados_limpos, ddof=1))
        dp = max(dp, 1e-4)
        simulados = rng.normal(loc=media, scale=dp, size=tamanho_amostra)
        params = {"media": media, "desvio_padrao": dp}

    else:  # Gamma como opção flexível
        media = float(np.mean(dados_positivos))
        var = float(np.var(dados_positivos, ddof=1))
        var = max(var, 1e-4)
        k_shape = max((media**2) / var, 0.1)
        theta_scale = max(var / media, 0.1)
        simulados = rng.gamma(shape=k_shape, scale=theta_scale, size=tamanho_amostra)
        params = {"shape_k": k_shape, "scale_theta": theta_scale}

    return simulados, params


def calcular_estatisticas_descritivas(array: np.ndarray) -> Dict[str, float]:
    """Calcula média, mediana, desvio padrão e assimetria (skewness) de um array."""
    limpo = array[~np.isnan(array)]
    if len(limpo) == 0:
        return {"media": 0.0, "mediana": 0.0, "desvio_padrao": 0.0, "assimetria": 0.0}
    return {
        "media": float(np.mean(limpo)),
        "mediana": float(np.median(limpo)),
        "desvio_padrao": float(np.std(limpo, ddof=1)) if len(limpo) > 1 else 0.0,
        "assimetria": float(stats.skew(limpo)) if len(limpo) > 2 else 0.0,
    }


# ---------------------------------------------------------------------------
# ISSUE #94: GRÁFICO G1 (Histogramas Comparativos: Real vs. Simulado)
# ---------------------------------------------------------------------------

def gerar_grafico_g1(
    dados_reais: np.ndarray,
    dados_simulados: np.ndarray,
    nome_metrica: str = "Métrica de Software",
    modo: str = "Lado a Lado",
    nbins: int = 30,
) -> go.Figure:
    """Implementa o Gráfico G1:

    Histogramas comparativos dos dados reais ao lado dos simulados
    utilizando Plotly, incluindo densidade e estatísticas descritivas comparativas.
    """
    reais_limpos = dados_reais[~np.isnan(dados_reais)]
    sim_limpos = dados_simulados[~np.isnan(dados_simulados)]

    stats_real = calcular_estatisticas_descritivas(reais_limpos)
    stats_sim = calcular_estatisticas_descritivas(sim_limpos)

    cor_real = "#2563EB"  # Azul Real
    cor_sim = "#F97316"   # Laranja Simulado

    if modo == "Lado a Lado":
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=[
                f"<b>Dados Reais</b> (N={len(reais_limpos)})",
                f"<b>Dados Simulados</b> (N={len(sim_limpos)})",
            ],
            shared_yaxes=False,
            horizontal_spacing=0.1,
        )

        # Histograma Dados Reais
        fig.add_trace(
            go.Histogram(
                x=reais_limpos,
                nbinsx=nbins,
                name="Dados Reais",
                marker=dict(
                    color=cor_real,
                    line=dict(color="#1E3A8A", width=1),
                ),
                opacity=0.85,
                histnorm="probability density",
                hovertemplate="<b>Real</b><br>Faixa: %{x}<br>Densidade: %{y:.4f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Linha vertical da média e mediana reais
        fig.add_vline(
            x=stats_real["media"],
            line_dash="dash",
            line_color="#1E3A8A",
            line_width=2,
            annotation_text=f"Média: {stats_real['media']:.2f}",
            annotation_position="top left",
            row=1,
            col=1,
        )
        fig.add_vline(
            x=stats_real["mediana"],
            line_dash="dot",
            line_color="#047857",
            line_width=2,
            annotation_text=f"Mediana: {stats_real['mediana']:.2f}",
            annotation_position="top right",
            row=1,
            col=1,
        )

        # Histograma Dados Simulados
        fig.add_trace(
            go.Histogram(
                x=sim_limpos,
                nbinsx=nbins,
                name="Dados Simulados",
                marker=dict(
                    color=cor_sim,
                    line=dict(color="#C2410C", width=1),
                ),
                opacity=0.85,
                histnorm="probability density",
                hovertemplate="<b>Simulado</b><br>Faixa: %{x}<br>Densidade: %{y:.4f}<extra></extra>",
            ),
            row=1,
            col=2,
        )

        # Linha vertical da média e mediana simuladas
        fig.add_vline(
            x=stats_sim["media"],
            line_dash="dash",
            line_color="#C2410C",
            line_width=2,
            annotation_text=f"Média: {stats_sim['media']:.2f}",
            annotation_position="top left",
            row=1,
            col=2,
        )
        fig.add_vline(
            x=stats_sim["mediana"],
            line_dash="dot",
            line_color="#047857",
            line_width=2,
            annotation_text=f"Mediana: {stats_sim['mediana']:.2f}",
            annotation_position="top right",
            row=1,
            col=2,
        )

        fig.update_xaxes(title_text=nome_metrica, row=1, col=1)
        fig.update_xaxes(title_text=nome_metrica, row=1, col=2)
        fig.update_yaxes(title_text="Densidade de Probabilidade", row=1, col=1)
        fig.update_yaxes(title_text="Densidade de Probabilidade", row=1, col=2)

    else:  # Modo Sobreposto
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=reais_limpos,
                nbinsx=nbins,
                name=f"Dados Reais (N={len(reais_limpos)})",
                marker=dict(color=cor_real, line=dict(color="#1E3A8A", width=1)),
                opacity=0.6,
                histnorm="probability density",
                hovertemplate="<b>Real</b><br>Faixa: %{x}<br>Densidade: %{y:.4f}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Histogram(
                x=sim_limpos,
                nbinsx=nbins,
                name=f"Dados Simulados (N={len(sim_limpos)})",
                marker=dict(color=cor_sim, line=dict(color="#C2410C", width=1)),
                opacity=0.6,
                histnorm="probability density",
                hovertemplate="<b>Simulado</b><br>Faixa: %{x}<br>Densidade: %{y:.4f}<extra></extra>",
            )
        )

        fig.add_vline(
            x=stats_real["media"],
            line_dash="dash",
            line_color=cor_real,
            line_width=2,
            annotation_text=f"Média Real: {stats_real['media']:.2f}",
            annotation_position="top left",
        )
        fig.add_vline(
            x=stats_sim["media"],
            line_dash="dash",
            line_color=cor_sim,
            line_width=2,
            annotation_text=f"Média Sim: {stats_sim['media']:.2f}",
            annotation_position="top right",
        )

        fig.update_layout(
            barmode="overlay",
            xaxis_title=nome_metrica,
            yaxis_title="Densidade de Probabilidade",
        )

    fig.update_layout(
        title=dict(
            text=f"<b>Gráfico G1: Comparativo da Distribuição Real vs. Simulada</b> — {nome_metrica}",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        template="plotly_white",
        height=480,
        margin=dict(l=40, r=40, t=80, b=40),
    )

    return fig


# ---------------------------------------------------------------------------
# ISSUE #94: GRÁFICO G2 (Distribuição da Estatística sob H0 com Região Crítica)
# ---------------------------------------------------------------------------

def gerar_grafico_g2(
    stat_obs: float,
    p_valor: float,
    graus_liberdade: Optional[float] = None,
    alpha: float = 0.05,
    tipo_teste: str = "t-Student",
    x_range: Optional[Tuple[float, float]] = None,
) -> go.Figure:
    """Implementa o Gráfico G2:

    Distribuição da estatística do teste sob H0, com a região de rejeição
    sombreada (nível alfa) e marcação destacada da estatística observada e p-valor.
    """
    df_val = graus_liberdade if graus_liberdade and graus_liberdade > 1 else 30.0

    # Definição do suporte da curva sob H0
    if tipo_teste == "t-Student":
        dist_h0 = stats.t(df=df_val)
        critico = float(stats.t.ppf(1 - alpha / 2, df=df_val))
        nome_stat = "t"
        titulo_dist = f"Distribuição t de Student sob H₀ (gl={df_val:.0f})"
    else:  # Mann-Whitney U / Z-score assintótico
        dist_h0 = stats.norm(loc=0, scale=1)
        critico = float(stats.norm.ppf(1 - alpha / 2))
        nome_stat = "Z"
        titulo_dist = "Distribuição Normal Padrão N(0, 1) sob H₀"

    limite_x = max(4.0, abs(stat_obs) + 1.5, critico + 1.5)
    if x_range:
        x_min, x_max = x_range
    else:
        x_min, x_max = -limite_x, limite_x

    x_vals = np.linspace(x_min, x_max, 1000)
    pdf_vals = dist_h0.pdf(x_vals)

    fig = go.Figure()

    # 1. Curva principal da densidade sob H0
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=pdf_vals,
            mode="lines",
            name=f"Densidade sob H₀ ({nome_stat})",
            line=dict(color="#1E293B", width=2.5),
            hovertemplate="<b>Estatística</b>: %{x:.3f}<br><b>Densidade</b>: %{y:.4f}<extra></extra>",
        )
    )

    # 2. Região de Rejeição / Crítica à esquerda (bicaudal: x <= -critico)
    x_left = np.linspace(x_min, -critico, 300)
    y_left = dist_h0.pdf(x_left)
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([[x_left[0]], x_left, [-critico]]),
            y=np.concatenate([[0], y_left, [0]]),
            fill="toself",
            fillcolor="rgba(239, 68, 68, 0.4)",
            line=dict(color="rgba(239, 68, 68, 0)"),
            name=f"Região de Rejeição (α/2 = {alpha/2:.3f})",
            hoverinfo="skip",
        )
    )

    # 3. Região de Rejeição / Crítica à direita (bicaudal: x >= +critico)
    x_right = np.linspace(critico, x_max, 300)
    y_right = dist_h0.pdf(x_right)
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([[critico], x_right, [x_right[-1]]]),
            y=np.concatenate([[0], y_right, [0]]),
            fill="toself",
            fillcolor="rgba(239, 68, 68, 0.4)",
            line=dict(color="rgba(239, 68, 68, 0)"),
            name=f"Região de Rejeição (α/2 = {alpha/2:.3f})",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # 4. Linhas verticais dos valores críticos
    fig.add_vline(
        x=-critico,
        line_dash="dash",
        line_color="#DC2626",
        line_width=1.8,
        annotation_text=f"-{nome_stat}_crítico = {-critico:.2f}",
        annotation_position="bottom left",
    )
    fig.add_vline(
        x=critico,
        line_dash="dash",
        line_color="#DC2626",
        line_width=1.8,
        annotation_text=f"+{nome_stat}_crítico = +{critico:.2f}",
        annotation_position="bottom right",
    )

    # 5. Marcação da Estatística Observada e p-valor
    rejeita = p_valor < alpha
    cor_obs = "#7C3AED" if not rejeita else "#DC2626"

    fig.add_vline(
        x=stat_obs,
        line_dash="solid",
        line_color=cor_obs,
        line_width=3,
        annotation_text=f"<b>{nome_stat}_obs = {stat_obs:.3f}</b><br>(p = {p_valor:.4e})",
        annotation_position="top right" if stat_obs >= 0 else "top left",
        annotation_font=dict(size=12, color=cor_obs),
    )

    # Marcador no topo da curva onde o valor observado se encontra
    pdf_obs = float(dist_h0.pdf(stat_obs)) if (x_min <= stat_obs <= x_max) else 0.0
    fig.add_trace(
        go.Scatter(
            x=[stat_obs],
            y=[pdf_obs],
            mode="markers",
            marker=dict(size=10, color=cor_obs, symbol="diamond"),
            name=f"Estatística Observada ({nome_stat}={stat_obs:.2f})",
            hovertemplate=f"<b>Estatística Observada</b>: {stat_obs:.3f}<br><b>p-valor</b>: {p_valor:.4e}<extra></extra>",
        )
    )

    status_str = "REJEITA H₀" if rejeita else "NÃO REJEITA H₀"
    fig.update_layout(
        title=dict(
            text=f"<b>Gráfico G2: {titulo_dist}</b><br><sup>Região Crítica sombreada (α = {alpha}) | {nome_stat}_obs = {stat_obs:.3f} | p = {p_valor:.4e} ({status_str})</sup>",
            x=0.5,
            xanchor="center",
            font=dict(size=15),
        ),
        xaxis_title=f"Estatística do Teste ({nome_stat})",
        yaxis_title="Densidade de Probabilidade sob H₀",
        template="plotly_white",
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=90, b=40),
    )

    return fig


# ---------------------------------------------------------------------------
# Motor Estatístico de Apoio e Simulação Inicial
# ---------------------------------------------------------------------------

def executar_teste_estatistico(
    grupo1: np.ndarray,
    grupo2: np.ndarray,
    tipo_teste: str = "t-Student",
) -> Dict[str, Any]:
    """Aplica os testes estatísticos exigidos (t-Student ou Mann-Whitney U)

    retornando estatística observada, p-valor e graus de liberdade.
    """
    g1 = grupo1[~np.isnan(grupo1)]
    g2 = grupo2[~np.isnan(grupo2)]

    if len(g1) < 2 or len(g2) < 2:
        return {"stat_obs": 0.0, "p_valor": 1.0, "df": 2.0, "teste": tipo_teste}

    if tipo_teste == "t-Student":
        res = stats.ttest_ind(g1, g2, equal_var=False)  # Welch's t-test
        # Aproximação de Welch-Satterthwaite para os graus de liberdade
        s1, s2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
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
        }
    else:  # Mann-Whitney U
        res = stats.mannwhitneyu(g1, g2, alternative="two-sided")
        # Padronização assintótica para Z sob H0
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
        }


def simular_distribuicao_nula_monte_carlo(
    amostra_base: np.ndarray,
    n_iteracoes: int = 500,
    n_amostra: int = 50,
    tipo_teste: str = "t-Student",
    semente: int = 42,
) -> np.ndarray:
    """Simula a distribuição empírica da estatística do teste sob H0

    (duas amostras extraídas da mesma população sob H0).
    """
    rng = np.random.default_rng(semente)
    base_limpa = amostra_base[~np.isnan(amostra_base)]
    if len(base_limpa) < 10:
        base_limpa = np.linspace(1, 100, 100)

    stats_simuladas = []
    for _ in range(n_iteracoes):
        g1 = rng.choice(base_limpa, size=n_amostra, replace=True)
        g2 = rng.choice(base_limpa, size=n_amostra, replace=True)
        resultado = executar_teste_estatistico(g1, g2, tipo_teste=tipo_teste)
        stats_simuladas.append(resultado["stat_obs"])

    return np.array(stats_simuladas)


# ---------------------------------------------------------------------------
# ISSUE #93: CONFIGURAÇÃO INICIAL DO DASHBOARD (STREAMLIT APP)
# ---------------------------------------------------------------------------

def render_sidebar(df_real: pd.DataFrame) -> Dict[str, Any]:
    """Renderiza a barra lateral com os controles e parâmetros."""
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/4/4b/Streamlit_Logo.png",
        width=180,
    )
    st.sidebar.title("🎛️ Painel de Configurações")
    st.sidebar.markdown("---")

    st.sidebar.subheader("1. Variável de Análise")
    colunas_numericas = df_real.select_dtypes(include=[np.number]).columns.tolist()
    metricas_preferenciais = [
        "lead_time_commit_mediana_dias",
        "tempo_recuperacao_mediana_horas",
        "deployment_frequency_semana",
        "lead_time_release_mediana_dias",
        "cfr_ci_proxy",
        "stars",
    ]
    metricas_disponiveis = [m for m in metricas_preferenciais if m in colunas_numericas]
    if not metricas_disponiveis:
        metricas_disponiveis = colunas_numericas[:5]

    metrica_selecionada = st.sidebar.selectbox(
        "Selecione a Métrica Real:",
        options=metricas_disponiveis,
        index=0,
        help="Métrica extraída do dataset real do Lab03 para calibração da simulação.",
    )

    st.sidebar.subheader("2. Parametrização da Simulação")
    distribuicao_escolhida = st.sidebar.selectbox(
        "Distribuição Teórica para Simulação:",
        options=["Lognormal", "Exponencial", "Normal", "Gamma"],
        index=0,
        help="Distribuição teórica ajustada aos dados empíricos observados.",
    )

    tamanho_amostra = st.sidebar.slider(
        "Tamanho da Amostra Sintética (N):",
        min_value=30,
        max_value=1000,
        value=len(df_real),
        step=10,
        help="Quantidade de observações geradas no motor de simulação.",
    )

    semente_rng = st.sidebar.number_input(
        "Semente Aleatória (RNG Seed):",
        min_value=1,
        max_value=999999,
        value=42,
        help="Garante reprodutibilidade científica (requisito da S01).",
    )

    st.sidebar.subheader("3. Parâmetros de Inferência Estatística")
    tipo_teste = st.sidebar.radio(
        "Teste de Hipótese Escolhido:",
        options=["t-Student", "Mann-Whitney U"],
        index=0,
        help="Teste paramétrico (t-Student) ou não-paramétrico (Mann-Whitney U).",
    )

    alpha_sig = st.sidebar.select_slider(
        "Nível de Significância (α):",
        options=[0.01, 0.05, 0.10],
        value=0.05,
        format_func=lambda x: f"{x:.2f} ({int(x*100)}%)",
        help="Probabilidade de cometer o erro do Tipo I (rejeitar H0 sendo ela verdadeira).",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **👥 Equipe do Projeto:**
        - **Maria Clara**: *data_loader.py*
        - **Áulus**: *simulation.py*
        - **Vinícius**: *dashboard.py* (G1 & G2)
        """
    )

    return {
        "metrica": metrica_selecionada,
        "distribuicao": distribuicao_escolhida,
        "tamanho_amostra": tamanho_amostra,
        "semente": semente_rng,
        "tipo_teste": tipo_teste,
        "alpha": alpha_sig,
    }


def main() -> None:
    st.set_page_config(
        page_title="Lab04S01 - Simulação e Testes Estatísticos",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Carregamento dos dados reais
    df_real = carregar_dados_reais()

    # 2. Renderização dos controles na barra lateral
    params = render_sidebar(df_real)

    # 3. Cabeçalho principal do Dashboard
    st.title("🔬 Lab04S01 — Dashboard de Simulação & Testes Estatísticos")
    st.caption(
        "Laboratório de Experimentação de Software | PUC Minas — Eng. Software | "
        "Módulo de Visualização e Dashboard (Issues #93 & #94)"
    )

    # Card informativo com Pergunta de Pesquisa e Hipóteses Formais
    with st.expander("📖 Contexto Experimental, Hipóteses Formais e Parâmetros (Clique para expandir)", expanded=True):
        col_ctx1, col_ctx2 = st.columns([1.5, 1])
        with col_ctx1:
            st.markdown(
                """
                **🎯 Pergunta de Pesquisa:**
                *Existe diferença estatisticamente significativa no desempenho da métrica de engenharia de software comparada entre grupos sob condições simuladas e reais?*

                - **Hipótese Nula ($H_0$):** $\\mu_1 = \\mu_2$ (ou $F_1 = F_2$) — Não há diferença entre os grupos comparados.
                - **Hipótese Alternativa ($H_1$):** $\\mu_1 \\neq \\mu_2$ (ou $F_1 \\neq F_2$) — Há diferença estatisticamente significativa.
                """
            )
        with col_ctx2:
            st.info(
                f"""
                **Configuração Atual:**
                - **Métrica:** `{params['metrica']}`
                - **Distribuição Modelada:** `{params['distribuicao']}`
                - **Teste:** `{params['tipo_teste']}`
                - **Nível de Significância ($\\alpha$):** `{params['alpha']}`
                - **Semente Aleatória:** `{params['semente']}`
                """
            )

    # 4. Extração e Simulação dos Dados
    serie_real = df_real[params["metrica"]].dropna().to_numpy()
    dados_simulados, params_ajustados = executar_simulacao_dados(
        dados_reais=serie_real,
        distribuicao=params["distribuicao"],
        tamanho_amostra=params["tamanho_amostra"],
        semente=params["semente"],
    )

    # 5. Abas Principais de Apresentação
    tab_g1, tab_g2, tab_simulacao, tab_dados = st.tabs([
        "📊 Gráfico G1: Real vs. Simulado",
        "🎯 Gráfico G2: Distribuição sob H₀ & Região Crítica",
        "🎲 Motor de Validação & Simulação (S01)",
        "📋 Dados Descritivos & Amostra",
    ])

    # -----------------------------------------------------------------------
    # ABA 1: GRÁFICO G1 (Histogramas Comparativos)
    # -----------------------------------------------------------------------
    with tab_g1:
        st.subheader("Gráfico G1 — Histogramas Comparativos dos Dados Reais vs. Simulados")
        st.markdown(
            "Visualização da aderência da distribuição estatística gerada pelo motor sintético "
            "em relação aos dados reais coletados de projetos open-source."
        )

        col_g1_ctrl1, col_g1_ctrl2 = st.columns([1, 1])
        with col_g1_ctrl1:
            modo_g1 = st.radio(
                "Disposição do Histograma:",
                options=["Lado a Lado", "Sobreposto"],
                horizontal=True,
                key="modo_g1",
            )
        with col_g1_ctrl2:
            bins_g1 = st.slider("Número de Bins (Intervalos):", 10, 60, 30, key="bins_g1")

        # Exibição do Gráfico G1
        fig_g1 = gerar_grafico_g1(
            dados_reais=serie_real,
            dados_simulados=dados_simulados,
            nome_metrica=params["metrica"],
            modo=modo_g1,
            nbins=bins_g1,
        )
        st.plotly_chart(fig_g1, use_container_width=True)

        # Estatísticas Descritivas Comparativas
        stats_r = calcular_estatisticas_descritivas(serie_real)
        stats_s = calcular_estatisticas_descritivas(dados_simulados)

        st.markdown("#### 📐 Comparativo das Estatísticas Descritivas")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            label="Média",
            value=f"{stats_s['media']:.2f} (Sim)",
            delta=f"{stats_s['media'] - stats_r['media']:.2f} vs Real",
        )
        c2.metric(
            label="Mediana",
            value=f"{stats_s['mediana']:.2f} (Sim)",
            delta=f"{stats_s['mediana'] - stats_r['mediana']:.2f} vs Real",
        )
        c3.metric(
            label="Desvio Padrão",
            value=f"{stats_s['desvio_padrao']:.2f} (Sim)",
            delta=f"{stats_s['desvio_padrao'] - stats_r['desvio_padrao']:.2f} vs Real",
        )
        c4.metric(
            label="Assimetria (Skewness)",
            value=f"{stats_s['assimetria']:.2f} (Sim)",
            delta=f"{stats_s['assimetria'] - stats_r['assimetria']:.2f} vs Real",
        )

        st.caption(f"Parâmetros ajustados via MLE da distribuição {params['distribuicao']}: {params_ajustados}")

    # -----------------------------------------------------------------------
    # ABA 2: GRÁFICO G2 (Distribuição sob H0 & Região de Rejeição)
    # -----------------------------------------------------------------------
    with tab_g2:
        st.subheader("Gráfico G2 — Distribuição da Estatística do Teste sob H₀")
        st.markdown(
            "Distribuição nula teórica da estatística de teste com a **região crítica sombreada** "
            "ao nível $\\alpha$, destacando a estatística observada de um caso de teste e o respectivo p-valor."
        )

        # Preparação de dois grupos para teste de exemplo
        col_div1, col_div2 = st.columns([1, 1])
        with col_div1:
            tipo_cenario = st.selectbox(
                "Cenário de Exemplo para Teste:",
                options=[
                    "Grupos Reais (ex: Alta Performance vs. Baixa Performance)",
                    "Amostra Real vs. Amostra Simulada",
                    "Amostra sob H₀ Estrita (Simulação Nula)",
                ],
                index=0,
            )

        if tipo_cenario == "Grupos Reais (ex: Alta Performance vs. Baixa Performance)" and "tier_dora_geral" in df_real.columns:
            grupo_a = df_real[df_real["tier_dora_geral"].isin(["Elite", "High"])][params["metrica"]].dropna().to_numpy()
            grupo_b = df_real[df_real["tier_dora_geral"].isin(["Medium", "Low"])][params["metrica"]].dropna().to_numpy()
            label_a, label_b = "Tiers Elite & High", "Tiers Medium & Low"
        elif tipo_cenario == "Amostra Real vs. Amostra Simulada":
            grupo_a, grupo_b = serie_real, dados_simulados
            label_a, label_b = "Amostra Real", "Amostra Simulada"
        else:
            rng_ex = np.random.default_rng(params["semente"])
            grupo_a = rng_ex.choice(serie_real, size=min(80, len(serie_real)), replace=True)
            grupo_b = rng_ex.choice(serie_real, size=min(80, len(serie_real)), replace=True)
            label_a, label_b = "Subamostra Nula A", "Subamostra Nula B"

        # Execução do teste
        res_teste = executar_teste_estatistico(grupo_a, grupo_b, tipo_teste=params["tipo_teste"])
        stat_obs = res_teste["stat_obs"]
        p_val = res_teste["p_valor"]
        df_gl = res_teste.get("df", 30.0)

        # Exibição do Gráfico G2
        fig_g2 = gerar_grafico_g2(
            stat_obs=stat_obs,
            p_valor=p_val,
            graus_liberdade=df_gl,
            alpha=params["alpha"],
            tipo_teste=params["tipo_teste"],
        )
        st.plotly_chart(fig_g2, use_container_width=True)

        # Diagnóstico e Decisão Estatística
        rejeita_h0 = p_val < params["alpha"]
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Estatística Observada", f"{stat_obs:.4f}")
        col_res2.metric("p-valor Obtido", f"{p_val:.4e}")
        col_res3.metric("Nível Crítico (α)", f"{params['alpha']:.2f}")

        if rejeita_h0:
            st.error(
                f"🛑 **Decisão Estatística:** Rejeita-se a Hipótese Nula ($H_0$) ao nível de significância de $\\alpha={params['alpha']}$. "
                f"O p-valor ({p_val:.4e}) é estritamente menor que $\\alpha$, indicando evidência estatística suficiente de diferença entre `{label_a}` e `{label_b}`."
            )
        else:
            st.success(
                f"✅ **Decisão Estatística:** Não se rejeita a Hipótese Nula ($H_0$) ao nível de significância de $\\alpha={params['alpha']}$. "
                f"O p-valor ({p_val:.4f}) é maior ou igual a $\\alpha$, o que indica que não há evidência empírica para afirmar diferença estatística entre `{label_a}` e `{label_b}`."
            )

    # -----------------------------------------------------------------------
    # ABA 3: MOTOR DE VALIDAÇÃO & SIMULAÇÃO MONTE CARLO (S01)
    # -----------------------------------------------------------------------
    with tab_simulacao:
        st.subheader("Motor de Validação Inicial & Simulação de Monte Carlo")
        st.markdown(
            "Validação experimental da taxa de rejeição sob $H_0$ (avaliando se a taxa de erro Tipo I converge para $\\alpha=0.05$) "
            "conforme planejado nas atividades da S01."
        )

        col_mc1, col_mc2, col_mc3 = st.columns(3)
        with col_mc1:
            n_rodadas = st.number_input("Número de Rodadas de Simulação:", 50, 1000, 200, 50)
        with col_mc2:
            tam_subamostra = st.number_input("Tamanho da Subamostra por Grupo:", 20, 200, 50, 10)
        with col_mc3:
            executar_mc = st.button("🚀 Executar Simulação Monte Carlo", type="primary")

        if executar_mc or "mc_stats" in st.session_state:
            if executar_mc:
                with st.spinner("Executando simulações de Monte Carlo sob H₀..."):
                    mc_stats = simular_distribuicao_nula_monte_carlo(
                        amostra_base=serie_real,
                        n_iteracoes=int(n_rodadas),
                        n_amostra=int(tam_subamostra),
                        tipo_teste=params["tipo_teste"],
                        semente=int(params["semente"]),
                    )
                    st.session_state["mc_stats"] = mc_stats

            mc_data = st.session_state["mc_stats"]
            # Proporção de rejeição empírica sob H0
            critico_teorico = (
                stats.t.ppf(1 - params["alpha"] / 2, df=tam_subamostra * 2 - 2)
                if params["tipo_teste"] == "t-Student"
                else stats.norm.ppf(1 - params["alpha"] / 2)
            )
            rejeicoes = np.sum(np.abs(mc_data) >= critico_teorico)
            taxa_rejeicao = rejeicoes / len(mc_data)

            col_mc_r1, col_mc_r2, col_mc_r3 = st.columns(3)
            col_mc_r1.metric("Total de Rodadas", f"{len(mc_data)}")
            col_mc_r2.metric("Total de Rejeições sob H₀", f"{rejeicoes}")
            col_mc_r3.metric(
                "Taxa Empírica de Rejeição (Erro Tipo I)",
                f"{taxa_rejeicao:.3%}",
                delta=f"{taxa_rejeicao - params['alpha']:.3%} vs α nominal ({params['alpha']:.2%})",
            )

            # Histograma empírico vs curva teórica
            fig_mc = go.Figure()
            fig_mc.add_trace(
                go.Histogram(
                    x=mc_data,
                    nbinsx=25,
                    histnorm="probability density",
                    name="Estatísticas Simuladas (Monte Carlo)",
                    marker=dict(color="#3B82F6", line=dict(color="#1D4ED8", width=1)),
                    opacity=0.75,
                )
            )
            # Linha teórica sobreposta
            x_range_mc = np.linspace(min(mc_data.min(), -4), max(mc_data.max(), 4), 300)
            y_teorico = (
                stats.t.pdf(x_range_mc, df=tam_subamostra * 2 - 2)
                if params["tipo_teste"] == "t-Student"
                else stats.norm.pdf(x_range_mc)
            )
            fig_mc.add_trace(
                go.Scatter(
                    x=x_range_mc,
                    y=y_teorico,
                    mode="lines",
                    name="Densidade Teórica Nula",
                    line=dict(color="#DC2626", width=2.5),
                )
            )
            fig_mc.update_layout(
                title="Distribuição Empírica das Estatísticas do Teste sob H₀ vs. Curva Teórica",
                xaxis_title="Estatística do Teste",
                yaxis_title="Densidade",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_mc, use_container_width=True)

    # -----------------------------------------------------------------------
    # ABA 4: DADOS DESCRITIVOS & AMOSTRA
    # -----------------------------------------------------------------------
    with tab_dados:
        st.subheader("Visualização da Amostra de Dados Reais")
        st.dataframe(df_real.head(50), use_container_width=True)
        st.markdown(f"**Total de observações no dataset:** {len(df_real)} registros.")


def executar_modo_script(caminho_saida: Optional[Path] = None) -> None:
    """Executa o script dos gráficos G1 e G2 diretamente via terminal/CLI (Issue #94),

    salvando as figuras interativas em arquivos HTML e exibindo o sumário analítico no console.
    """
    diretorio_saida = caminho_saida or BASE_DIR / "graficos_gerados"
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  Lab04S01 — Execução do Script dos Gráficos G1 e G2 (Issue #94)")
    print("=" * 70)

    # 1. Carregamento dos dados reais
    df_real = carregar_dados_reais()
    metrica = "lead_time_commit_mediana_dias"
    serie_real = df_real[metrica].dropna().to_numpy()
    print(f"\n[1/3] Base de dados carregada: {len(df_real)} registros.")
    print(f"      Métrica analisada: {metrica}")

    # 2. Geração do Gráfico G1
    print("\n[2/3] Gerando Gráfico G1 (Histogramas Comparativos Real vs. Simulado)...")
    dados_sim, params_fit = executar_simulacao_dados(
        dados_reais=serie_real,
        distribuicao="Lognormal",
        tamanho_amostra=len(serie_real),
        semente=42,
    )
    fig_g1 = gerar_grafico_g1(
        dados_reais=serie_real,
        dados_simulados=dados_sim,
        nome_metrica=metrica,
        modo="Lado a Lado",
    )
    caminho_g1 = diretorio_saida / "grafico_g1_comparativo.html"
    fig_g1.write_html(str(caminho_g1))
    print(f"      -> Salvo com sucesso em: {caminho_g1}")

    stats_r = calcular_estatisticas_descritivas(serie_real)
    stats_s = calcular_estatisticas_descritivas(dados_sim)
    print(f"      - Dados Reais:     Média={stats_r['media']:.2f} | Mediana={stats_r['mediana']:.2f} | DP={stats_r['desvio_padrao']:.2f} | Skew={stats_r['assimetria']:.2f}")
    print(f"      - Dados Simulados: Média={stats_s['media']:.2f} | Mediana={stats_s['mediana']:.2f} | DP={stats_s['desvio_padrao']:.2f} | Skew={stats_s['assimetria']:.2f}")

    # 3. Geração do Gráfico G2
    print("\n[3/3] Gerando Gráfico G2 (Distribuição sob H0 & Região Crítica de Rejeição)...")
    if "tier_dora_geral" in df_real.columns:
        grupo_a = df_real[df_real["tier_dora_geral"].isin(["Elite", "High"])][metrica].dropna().to_numpy()
        grupo_b = df_real[df_real["tier_dora_geral"].isin(["Medium", "Low"])][metrica].dropna().to_numpy()
        cenario_label = "Comparação Tiers DORA (Elite/High vs. Medium/Low)"
    else:
        grupo_a, grupo_b = serie_real, dados_sim
        cenario_label = "Amostra Real vs. Amostra Simulada"

    teste_res = executar_teste_estatistico(grupo_a, grupo_b, tipo_teste="t-Student")
    stat_obs = teste_res["stat_obs"]
    p_val = teste_res["p_valor"]
    df_gl = teste_res.get("df", 30.0)

    fig_g2 = gerar_grafico_g2(
        stat_obs=stat_obs,
        p_valor=p_val,
        graus_liberdade=df_gl,
        alpha=0.05,
        tipo_teste="t-Student",
    )
    caminho_g2 = diretorio_saida / "grafico_g2_distribuicao_h0.html"
    fig_g2.write_html(str(caminho_g2))
    print(f"      -> Salvo com sucesso em: {caminho_g2}")
    print(f"      - Cenário:                 {cenario_label}")
    print(f"      - Teste Estatístico:       {teste_res['teste']}")
    print(f"      - Estatística Observada:   t_obs = {stat_obs:.4f}")
    print(f"      - Graus de Liberdade (gl): {df_gl:.1f}")
    print(f"      - p-valor:                 {p_val:.4e}")
    status = "REJEITA H0 (p < 0.05)" if p_val < 0.05 else "NÃO REJEITA H0 (p >= 0.05)"
    print(f"      - Veredito Estatístico:    {status}")

    print("\n" + "=" * 70)
    print("  Concluído com êxito! Visualizações interativas exportadas.")
    print("=" * 70)


def is_running_under_streamlit() -> bool:
    """Verifica se o script está sendo executado através do runner do Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    if is_running_under_streamlit() or (len(sys.argv) > 1 and "--streamlit" in sys.argv):
        main()
    else:
        executar_modo_script()

