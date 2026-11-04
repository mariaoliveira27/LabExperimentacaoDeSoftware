"""Carregamento e preparação da amostra real do Laboratório 04.

O módulo usa a amostra consolidada no Laboratório 03, prepara métricas
numéricas e oferece uma divisão explícita entre tiers DORA altos e baixos.
Também pode ser executado diretamente para produzir estatísticas descritivas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_DATASET = (
    REPO_ROOT
    / "Laboratorio03_MineracaoDeMetricasDORA"
    / "data"
    / "coleta_final"
    / "repositorios_aprovados.csv"
)

PERGUNTA_PESQUISA = (
    "As métricas de engenharia de software diferem entre repositórios "
    "classificados nos tiers DORA Elite/High e Medium/Low?"
)
HIPOTESE_NULA = (
    "H0: a distribuição da métrica analisada é igual nos grupos Elite/High "
    "e Medium/Low (F_A = F_B; em particular, media_A = media_B quando a comparação "
    "é feita pelas médias)."
)
HIPOTESE_ALTERNATIVA = (
    "H1: a distribuição da métrica analisada difere entre os grupos "
    "Elite/High e Medium/Low (F_A != F_B; alternativamente, media_A != media_B)."
)

METRICAS = {
    "lead_time_commit_mediana_dias": "Lead Time de Commit (dias)",
    "lead_time_release_mediana_dias": "Lead Time de Release (dias)",
    "tempo_recuperacao_mediana_horas": "Tempo de Recuperação / MTTR (horas)",
    "deployment_frequency_semana": "Frequência de Deploy (deploys/semana)",
    "cfr_ci_proxy": "Taxa de Falha em CI (proxy)",
    "stars": "Estrelas no GitHub",
}

COLUNA_GRUPO = "tier_dora_geral"
GRUPOS = {
    "Elite/High": ("Elite", "High"),
    "Medium/Low": ("Medium", "Low"),
}


def carregar_amostra_real(caminho_csv: str | Path | None = None) -> pd.DataFrame:
    """Lê o CSV real e normaliza os campos das métricas para números.

    ``caminho_csv`` permite substituir a fonte padrão, por exemplo em análises
    reproduzíveis ou com outra versão da amostra.
    """
    caminho = Path(caminho_csv).expanduser() if caminho_csv else DEFAULT_DATASET
    if not caminho.is_file():
        raise FileNotFoundError(
            f"CSV da amostra real não encontrado: {caminho}. "
            "Informe o caminho com --csv ou disponibilize a saída do Laboratório 03."
        )

    df = pd.read_csv(caminho)
    if df.empty:
        raise ValueError(f"A amostra real está vazia: {caminho}")

    obrigatorias = {COLUNA_GRUPO, *METRICAS}
    ausentes = sorted(obrigatorias.difference(df.columns))
    if ausentes:
        raise ValueError(
            "CSV incompatível com o esquema esperado; colunas ausentes: "
            + ", ".join(ausentes)
        )

    for coluna in METRICAS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    df[COLUNA_GRUPO] = df[COLUNA_GRUPO].astype("string").str.strip()
    return df


def preparar_arrays_grupos(
    df: pd.DataFrame,
    metrica: str,
    coluna_grupo: str = COLUNA_GRUPO,
    valores_grupo_a: tuple[str, ...] = GRUPOS["Elite/High"],
    valores_grupo_b: tuple[str, ...] = GRUPOS["Medium/Low"],
) -> dict[str, Any]:
    """Retorna arrays NumPy alinhados aos dois grupos e suas etiquetas.

    Valores ausentes na métrica ou na classificação são removidos. A função
    falha claramente se um grupo não tiver observações utilizáveis.
    """
    for coluna in (metrica, coluna_grupo):
        if coluna not in df.columns:
            raise KeyError(f"Coluna não encontrada na amostra: {coluna}")

    valores = pd.to_numeric(df[metrica], errors="coerce")
    tier = df[coluna_grupo].astype("string").str.strip()
    validos = valores.notna() & tier.notna()
    grupo_a = valores[validos & tier.isin(valores_grupo_a)].to_numpy(dtype=float)
    grupo_b = valores[validos & tier.isin(valores_grupo_b)].to_numpy(dtype=float)
    if grupo_a.size == 0 or grupo_b.size == 0:
        raise ValueError(
            f"Não há observações válidas nos dois grupos para '{metrica}' "
            f"(n_A={grupo_a.size}, n_B={grupo_b.size})."
        )
    return {
        "metrica": metrica,
        "grupo_a": grupo_a,
        "grupo_b": grupo_b,
        "rotulo_a": "Elite/High",
        "rotulo_b": "Medium/Low",
        "n_a": int(grupo_a.size),
        "n_b": int(grupo_b.size),
    }


def calcular_estatisticas_descritivas(valores: np.ndarray | pd.Series) -> dict[str, float | int]:
    """Calcula N, média, mediana, desvio padrão, mínimo, quartis e máximo."""
    serie = pd.to_numeric(pd.Series(valores), errors="coerce").dropna()
    if serie.empty:
        return {
            "n": 0, "media": float("nan"), "mediana": float("nan"),
            "desvio_padrao": float("nan"), "minimo": float("nan"),
            "q1": float("nan"), "q3": float("nan"), "maximo": float("nan"),
        }
    return {
        "n": int(serie.size),
        "media": float(serie.mean()),
        "mediana": float(serie.median()),
        "desvio_padrao": float(serie.std(ddof=1)) if serie.size > 1 else 0.0,
        "minimo": float(serie.min()),
        "q1": float(serie.quantile(0.25)),
        "q3": float(serie.quantile(0.75)),
        "maximo": float(serie.max()),
    }


def gerar_relatorio_inicial(df: pd.DataFrame) -> dict[str, Any]:
    """Resume estatísticas da amostra total e dos grupos comparados."""
    relatorio: dict[str, Any] = {
        "fonte": str(DEFAULT_DATASET),
        "total_repositorios": int(len(df)),
        "pergunta_pesquisa": PERGUNTA_PESQUISA,
        "hipotese_nula": HIPOTESE_NULA,
        "hipotese_alternativa": HIPOTESE_ALTERNATIVA,
        "metricas": {},
    }
    for metrica, nome in METRICAS.items():
        arrays = preparar_arrays_grupos(df, metrica)
        relatorio["metricas"][metrica] = {
            "nome": nome,
            "total": calcular_estatisticas_descritivas(df[metrica]),
            arrays["rotulo_a"]: calcular_estatisticas_descritivas(arrays["grupo_a"]),
            arrays["rotulo_b"]: calcular_estatisticas_descritivas(arrays["grupo_b"]),
        }
    return relatorio


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Carrega a amostra real do Lab 03 e calcula estatísticas iniciais do Lab 04."
    )
    parser.add_argument("--csv", type=Path, help="Caminho alternativo para o CSV da amostra.")
    parser.add_argument(
        "--metrica", choices=tuple(METRICAS),
        help="Exibe somente a métrica selecionada (todas são exibidas por padrão).",
    )
    args = parser.parse_args()

    df = carregar_amostra_real(args.csv)
    relatorio = gerar_relatorio_inicial(df)
    if args.csv:
        relatorio["fonte"] = str(args.csv.expanduser().resolve())
    if args.metrica:
        relatorio["metricas"] = {args.metrica: relatorio["metricas"][args.metrica]}
    # Escapa caracteres não ASCII para que a saída também funcione em consoles
    # Windows que ainda usam a página de código cp1252.
    print(json.dumps(relatorio, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
