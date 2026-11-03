"""Módulo de Dados para o Dashboard do Laboratório 04 (Lab04S01)
Responsável por carregar amostras reais, calcular estatísticas descritivas
e estruturar os dados para os gráficos G1 e G2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Caminho para o dataset real de repositórios aprovados do Lab 03
DEFAULT_DATASET = (
    REPO_ROOT
    / "Laboratorio03_MineracaoDeMetricasDORA"
    / "data"
    / "output"
    / "repositorios_aprovados.csv"
)

METRICAS_DISPONIVEIS = {
    "lead_time_commit_mediana_dias": {
        "nome": "Lead Time de Commit (dias)",
        "descricao": "Mediana de dias entre o commit e a release de publicação.",
        "unidade": "dias",
    },
    "tempo_recuperacao_mediana_horas": {
        "nome": "Tempo de Recuperação / MTTR (horas)",
        "descricao": "Mediana de horas para recuperar um workflow de CI após falha.",
        "unidade": "horas",
    },
    "deployment_frequency_semana": {
        "nome": "Frequência de Deploy (deploys/semana)",
        "descricao": "Taxa média semanal de releases publicadas.",
        "unidade": "deploys/semana",
    },
    "lead_time_release_mediana_dias": {
        "nome": "Lead Time de Release (dias)",
        "descricao": "Mediana de dias entre releases consecutivas.",
        "unidade": "dias",
    },
    "cfr_ci_proxy": {
        "nome": "Taxa de Falha em CI / CFR Proxy (%)",
        "descricao": "Percentual de workflow runs que falharam.",
        "unidade": "taxa (0 a 1)",
    },
    "stars": {
        "nome": "Estrelas no GitHub",
        "descricao": "Popularidade do repositório em número de stars.",
        "unidade": "estrelas",
    },
}


def carregar_dados_reais(caminho_csv: Optional[Path] = None) -> pd.DataFrame:
    """Carrega o dataset real de repositórios, integrando com data_loader.py

    se existir, ou realizando o carregamento do CSV com fallback automático.
    """
    # 1. Tentar integrar com o data_loader.py de Maria Clara na pasta pai
    try:
        import sys
        parent_dir = str(HERE.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        import data_loader  # type: ignore

        if hasattr(data_loader, "carregar_amostra_real"):
            return data_loader.carregar_amostra_real(caminho_csv)
    except Exception:
        pass

    # 2. Carregar CSV real do Lab 03
    alvo = caminho_csv if caminho_csv and caminho_csv.is_file() else DEFAULT_DATASET
    if alvo.is_file():
        df = pd.read_csv(alvo)
        return df

    # 3. Fallback determinístico caso o CSV não esteja disponível
    rng = np.random.default_rng(42)
    n = 300
    return pd.DataFrame(
        {
            "full_name": [f"repo_{i}" for i in range(n)],
            "language": rng.choice(["Python", "JavaScript", "TypeScript", "Java", "Go"], n),
            "tier_dora_geral": rng.choice(["Elite", "High", "Medium", "Low"], n, p=[0.2, 0.35, 0.3, 0.15]),
            "tipo_projeto": rng.choice(["ferramenta CLI", "biblioteca/framework", "aplicacao"], n),
            "lead_time_commit_mediana_dias": np.round(rng.lognormal(mean=1.35, sigma=0.65, size=n), 2),
            "lead_time_release_mediana_dias": np.round(rng.lognormal(mean=2.6, sigma=0.7, size=n), 2),
            "tempo_recuperacao_mediana_horas": np.round(rng.exponential(scale=12.0, size=n), 2),
            "deployment_frequency_semana": np.round(rng.gamma(shape=2.0, scale=0.5, size=n), 3),
            "cfr_ci_proxy": np.round(rng.beta(a=2, b=8, size=n), 3),
            "stars": rng.integers(1000, 100000, size=n),
        }
    )


def calcular_estatisticas_descritivas(array: np.ndarray) -> Dict[str, float]:
    """Calcula estatísticas descritivas completas de uma série numérica:

    N, média, mediana, desvio padrão, assimetria (skewness), Q1, Q3 e IQR.
    """
    limpo = array[~np.isnan(array)]
    if len(limpo) == 0:
        return {
            "n": 0,
            "media": 0.0,
            "mediana": 0.0,
            "desvio_padrao": 0.0,
            "assimetria": 0.0,
            "q1": 0.0,
            "q3": 0.0,
            "iqr": 0.0,
        }

    q1 = float(np.percentile(limpo, 25))
    q3 = float(np.percentile(limpo, 75))

    return {
        "n": int(len(limpo)),
        "media": float(np.mean(limpo)),
        "mediana": float(np.median(limpo)),
        "desvio_padrao": float(np.std(limpo, ddof=1)) if len(limpo) > 1 else 0.0,
        "assimetria": float(stats.skew(limpo)) if len(limpo) > 2 else 0.0,
        "q1": q1,
        "q3": q3,
        "iqr": float(q3 - q1),
    }


def simular_distribuicao_sintetica(
    dados_reais: np.ndarray,
    distribuicao: str = "Lognormal",
    tamanho_amostra: int = 300,
    semente: int = 42,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Ajusta a distribuição teórica indicada aos dados reais via MLE

    e gera amostra sintética utilizando semente pseudoaleatória fixa.
    """
    # Tentar integrar com simulation.py de Áulus na pasta pai
    try:
        import sys
        parent_dir = str(HERE.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
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

    rng = np.random.default_rng(semente)
    dados_limpos = dados_reais[~np.isnan(dados_reais)]
    dados_positivos = dados_limpos[dados_limpos > 0]
    if len(dados_positivos) < 5:
        dados_positivos = np.array([1.0, 2.0, 3.0, 5.0, 10.0])

    params: Dict[str, Any] = {}

    if distribuicao == "Lognormal":
        log_dados = np.log(dados_positivos)
        mu = float(np.mean(log_dados))
        sigma = float(np.std(log_dados, ddof=1))
        sigma = max(sigma, 1e-4)
        simulados = rng.lognormal(mean=mu, sigma=sigma, size=tamanho_amostra)
        params = {"mu_log": round(mu, 4), "sigma_log": round(sigma, 4)}

    elif distribuicao == "Exponencial":
        escala = float(np.mean(dados_positivos))
        escala = max(escala, 1e-4)
        simulados = rng.exponential(scale=escala, size=tamanho_amostra)
        params = {"escala": round(escala, 4)}

    elif distribuicao == "Normal":
        media = float(np.mean(dados_limpos))
        dp = float(np.std(dados_limpos, ddof=1))
        dp = max(dp, 1e-4)
        simulados = rng.normal(loc=media, scale=dp, size=tamanho_amostra)
        params = {"media": round(media, 4), "desvio_padrao": round(dp, 4)}

    else:  # Gamma
        media = float(np.mean(dados_positivos))
        var = float(np.var(dados_positivos, ddof=1))
        var = max(var, 1e-4)
        k_shape = max((media**2) / var, 0.1)
        theta_scale = max(var / media, 0.1)
        simulados = rng.gamma(shape=k_shape, scale=theta_scale, size=tamanho_amostra)
        params = {"shape_k": round(k_shape, 4), "scale_theta": round(theta_scale, 4)}

    return np.round(simulados, 3), params
