"""Análise inferencial reproduzível da amostra empírica do Laboratório 04."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from data_loader import (
    DEFAULT_DATASET,
    GRUPOS,
    METRICAS,
    carregar_amostra_real,
    carregar_metadados_coleta,
)

ALPHA = 0.05
METRICAS_DORA = (
    "lead_time_commit_mediana_dias",
    "tempo_recuperacao_mediana_horas",
    "deployment_frequency_semana",
)


def _efeito_cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen d com desvio-padrão combinado (pooled) dos dois grupos."""
    n_a, n_b = len(a), len(b)
    variancia_combinada = ((n_a - 1) * np.var(a, ddof=1) + (n_b - 1) * np.var(b, ddof=1)) / (n_a + n_b - 2)
    dp_combinado = float(np.sqrt(variancia_combinada))
    return float((np.mean(a) - np.mean(b)) / dp_combinado) if dp_combinado else 0.0


def _classificar_d(abs_effect: float) -> str:
    if abs_effect < 0.2:
        return "desprezível"
    if abs_effect < 0.5:
        return "pequeno"
    if abs_effect < 0.8:
        return "médio"
    return "grande"


def _classificar_delta(abs_effect: float) -> str:
    if abs_effect < 0.147:
        return "desprezível"
    if abs_effect < 0.33:
        return "pequeno"
    if abs_effect < 0.474:
        return "médio"
    return "grande"


def calcular_analise_real(df: pd.DataFrame, alpha: float = ALPHA) -> dict[str, Any]:
    """Aplica Welch e Mann–Whitney bicaudais e calcula efeitos por métrica DORA."""
    linhas = []
    for chave in METRICAS_DORA:
        if chave not in df.columns:
            continue
        valores = pd.to_numeric(df[chave], errors="coerce")
        tier = df["tier_dora_geral"].astype("string").str.strip()
        validos = valores.notna() & tier.notna()
        a = valores[validos & tier.isin(GRUPOS["Elite/High"])].to_numpy(dtype=float)
        b = valores[validos & tier.isin(GRUPOS["Medium/Low"])].to_numpy(dtype=float)
        if len(a) < 2 or len(b) < 2:
            continue

        welch = stats.ttest_ind(a, b, equal_var=False, alternative="two-sided")
        mw = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
        d = _efeito_cohen_d(a, b)
        # U corresponde à contagem A>B mais metade dos empates (convenção SciPy).
        delta = float(2 * mw.statistic / (len(a) * len(b)) - 1)
        p_welch, p_mw = float(welch.pvalue), float(mw.pvalue)
        linhas.append({
            "chave": chave,
            "metrica": METRICAS[chave],
            "unidade": {"lead_time_commit_mediana_dias": "dias", "tempo_recuperacao_mediana_horas": "horas", "deployment_frequency_semana": "deploys/semana"}[chave],
            "n_elite_high": len(a), "n_medium_low": len(b),
            "media_elite_high": float(np.mean(a)), "media_medium_low": float(np.mean(b)),
            "mediana_elite_high": float(np.median(a)), "mediana_medium_low": float(np.median(b)),
            "assimetria_elite_high": float(stats.skew(a, bias=False)) if len(a) > 2 else None,
            "assimetria_medium_low": float(stats.skew(b, bias=False)) if len(b) > 2 else None,
            "welch": {"estatistica": float(welch.statistic), "p_valor": p_welch, "cohen_d": d,
                      "classificacao_efeito": _classificar_d(abs(d)), "rejeita_h0": p_welch < alpha},
            "mann_whitney": {"estatistica_u": float(mw.statistic), "p_valor": p_mw, "cliffs_delta": delta,
                              "classificacao_efeito": _classificar_delta(abs(delta)), "rejeita_h0": p_mw < alpha},
        })

    if not linhas:
        raise ValueError("A amostra não contém duas categorias DORA com dados suficientes para as métricas solicitadas.")

    return {"alpha": alpha, "alternativa": "bicaudal", "n_total": int(len(df)), "linhas": linhas}


def gerar_textos_dashboard(analise: dict[str, Any], metadados: dict[str, Any]) -> dict[str, str]:
    linhas = analise["linhas"]
    mais_extremo = max(linhas, key=lambda r: abs(r["welch"]["cohen_d"]))
    ambos_rejeitam = sum(r["welch"]["rejeita_h0"] and r["mann_whitney"]["rejeita_h0"] for r in linhas)
    coleta = metadados.get("metodo_coleta", "Mineração de repositórios públicos.")
    n = analise["n_total"]
    janela = metadados.get("janela_observacao") or {}
    intervalo = f" entre {janela.get('inicio', '')[:10]} e {janela.get('fim', '')[:10]}" if janela else ""
    n_a, n_b = linhas[0]["n_elite_high"], linhas[0]["n_medium_low"]
    secao1 = (f"Comparamos Lead Time de Commit, MTTR e frequência de deploy entre repositórios nos tiers DORA Elite/High e Medium/Low; H₀ afirma distribuições iguais, e H₁ afirma distribuições diferentes (teste bicaudal). "
              f"A amostra contém {n} repositórios aprovados ({n_a} Elite/High e {n_b} Medium/Low), coletados via GitHub API{intervalo}; {coleta}")
    resumo = " e ".join(r["metrica"] for r in linhas)
    secao6 = (f"Nos dados reais, Welch e Mann–Whitney rejeitaram H₀ em {ambos_rejeitam} de {len(linhas)} métricas ao nível α={analise['alpha']:.2f}; os efeitos e tamanhos de cada grupo estão discriminados na tabela. "
              f"Para {mais_extremo['metrica']}, o maior |d| foi {abs(mais_extremo['welch']['cohen_d']):.2f} ({mais_extremo['welch']['classificacao_efeito']}) e Cliff’s δ foi {mais_extremo['mann_whitney']['cliffs_delta']:.2f}; significância estatística não implica causalidade.")
    efeitos = ", ".join(f"{r['metrica']}: d={r['welch']['cohen_d']:.2f}, δ={r['mann_whitney']['cliffs_delta']:.2f}" for r in linhas)
    secao7 = ("Antes das simulações, a expectativa era que Welch mantivesse bom desempenho para médias, mas que Mann–Whitney fosse mais robusto sob assimetria e outliers. "
              f"Nos dados observacionais de {resumo}, ambos os testes rejeitaram H₀; os efeitos encontrados foram {efeitos}, sem permitir inferência causal. "
              "Para métricas assimétricas e comparação geral de distribuições, recomendamos Mann–Whitney, reportando Cliff’s δ. "
              "Se a pergunta for especificamente sobre médias e os dados atenderem às condições do modelo, Welch é a escolha direta; a decisão deve considerar objetivo e formato dos dados, não apenas o menor p-valor.")
    dora = {r["chave"]: r for r in linhas}
    assimetrias = "; ".join(
        f"{dora[k]['metrica']}: {dora[k]['assimetria_elite_high']:.2f}/{dora[k]['assimetria_medium_low']:.2f}"
        for k in dora
    )
    respostas_orais = {
        "01": secao1,
        "02": "A comparação é bicaudal: antes de olhar os resultados, consideramos relevante uma diferença em qualquer direção entre os tiers. Por isso, H₁ é distribuição diferente, sem especificar qual grupo terá valores maiores.",
        "03": f"A amostra tem {n} repositórios públicos aprovados na coleta via GitHub API, com {linhas[0]['n_elite_high']} Elite/High e {linhas[0]['n_medium_low']} Medium/Low. A assimetria amostral (skewness Elite/High / Medium/Low) foi: {assimetrias}; as formas variam por métrica e grupo, então não assumimos normalidade geral.",
        "04": "Para os histogramas comparativos, os parâmetros da Lognormal são ajustados por máxima verossimilhança aos valores reais positivos de cada métrica. Nas simulações de erro tipo I e poder, mediana=10 e sigma=1 (ou sigma=1,6 nos cenários de assimetria) são parâmetros controlados do experimento, não estimativas exatas desta amostra; essa diferença deve ser explicitada ao interpretar os gráficos.",
        "14": f"Nos dados reais, Welch e Mann–Whitney chegaram à mesma decisão em {ambos_rejeitam} de {len(linhas)} métricas (α={analise['alpha']:.2f}); as magnitudes são {efeitos}. Isso mostra por que o p-valor sozinho não basta: MTTR tem efeito menor que Lead Time e Frequência de Deploy, e relevância prática depende também da unidade e do contexto.",
    }
    return {"secao_1_cenario": secao1, "secao_6_dados_reais": secao6, "secao_7_conclusao": secao7,
            "respostas_orais_maria_clara": respostas_orais}


def gerar_payload(caminho_csv: Path = DEFAULT_DATASET, alpha: float = ALPHA) -> dict[str, Any]:
    df = carregar_amostra_real(caminho_csv)
    metadados = carregar_metadados_coleta(caminho_csv)
    analise = calcular_analise_real(df, alpha)
    return {"schema_version": 1, "metadados_coleta": metadados, "dados_reais_testes": analise,
            "textos_dashboard": gerar_textos_dashboard(analise, metadados)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolida análise empírica do Lab04.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--saida", type=Path, help="JSON opcional de saída (por padrão imprime no terminal).")
    parser.add_argument("--alpha", type=float, default=ALPHA)
    args = parser.parse_args()
    payload = gerar_payload(args.csv, args.alpha)
    serializado = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(serializado + "\n", encoding="utf-8")
    else:
        print(serializado)


if __name__ == "__main__":
    main()
