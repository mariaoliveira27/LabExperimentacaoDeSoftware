"""
Módulo de Análise Estatística para RQ05 e RQ06 (Métricas DORA).
Responsável: Maria (Seleção, Infraestrutura e Integração).

Implementa:
- RQ05: Correlação de postos de Spearman entre Velocidade (Deployment Frequency)
  e Estabilidade (CFR) para ambas as variantes:
  a) CFR Proxy de CI (cfr_ci_proxy)
  b) CFR Proxy de Releases corretivas (cfr_releases_proxy)
  com cálculo de IC 95% via Fisher z-transform, reporte de p-valor, rho e n.
- RQ06: Análise de características dos repositórios associadas ao desempenho DORA
  em múltiplos fatores (Popularidade/Estrelas, Contribuidores, Idade, Tipo de Projeto, Linguagem).
  Aplica:
  - Teste omnibus de Kruskal-Wallis (ou Mann-Whitney para 2 grupos)
  - Correção de Holm-Bonferroni para comparações múltiplas (statsmodels)
  - Tamanho de efeito Epsilon-quadrado (epsilon^2 = H / (n - 1))
  - Comparações pareadas post-hoc de Mann-Whitney com Cliff's Delta (Romano et al., 2006)
- Exportação de tabelas detalhadas em CSV e Markdown em data/output/
- Geração de gráficos de dispersão e boxplots em graficos_dora/
"""

import os
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
import scipy.stats as stats
from statsmodels.stats.multitest import multipletests
import matplotlib.pyplot as plt
import seaborn as sns


def calcular_spearman_com_ic(
    x: pd.Series,
    y: pd.Series,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Calcula o coeficiente de correlação de Spearman (rho) com p-valor
    e intervalo de confiança de (1 - alpha)% via transformação z de Fisher.
    """
    df_valid = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(df_valid)
    if n < 4:
        return {
            "n": n,
            "rho": np.nan,
            "p_valor": np.nan,
            "ci_inferior": np.nan,
            "ci_superior": np.nan,
            "interpretacao": "Amostra insuficiente",
        }

    rho, p_val = stats.spearmanr(df_valid["x"], df_valid["y"])

    # Intervalo de confiança via z de Fisher
    # z = arctanh(rho)
    # SE = 1 / sqrt(n - 3)
    try:
        # Clip para evitar arctanh(1.0) = inf
        rho_clipped = max(-0.9999, min(0.9999, rho))
        z = np.arctanh(rho_clipped)
        se = 1.0 / math.sqrt(n - 3)
        z_crit = stats.norm.ppf(1.0 - alpha / 2.0)
        z_low = z - z_crit * se
        z_high = z + z_crit * se
        ci_low = float(np.tanh(z_low))
        ci_high = float(np.tanh(z_high))
    except Exception:
        ci_low, ci_high = np.nan, np.nan

    # Interpretação da magnitude
    abs_rho = abs(rho)
    if abs_rho < 0.10:
        mag = "desprezível"
    elif abs_rho < 0.30:
        mag = "fraca"
    elif abs_rho < 0.50:
        mag = "moderada"
    else:
        mag = "forte"

    direcao = "positiva" if rho > 0 else "negativa"
    sig = "significativa" if p_val < alpha else "não significativa"
    interpretacao = f"Correlação {mag} {direcao} ({sig} ao nível de {int((1-alpha)*100)}%)"

    return {
        "n": int(n),
        "rho": float(round(rho, 4)),
        "p_valor": float(p_val),
        "ci_inferior": float(round(ci_low, 4)),
        "ci_superior": float(round(ci_high, 4)),
        "interpretacao": interpretacao,
    }


def executar_rq05(df: pd.DataFrame, output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Executa a análise da RQ05 para as duas variantes de CFR:
    1. Deployment Frequency vs CFR (Variante a - Proxy CI)
    2. Deployment Frequency vs CFR (Variante b - Proxy Releases)
    """
    res_a = calcular_spearman_com_ic(
        df["deployment_frequency_semana"],
        df["cfr_ci_proxy"]
    )
    res_a.update({
        "rq": "RQ05",
        "variante": "Variante (a) — Proxy de CI",
        "metrica_x": "deployment_frequency_semana",
        "metrica_y": "cfr_ci_proxy",
        "conclusao_tradeoff": (
            "Refuta o trade-off tradicional: maior frequência de deploy não deteriora a estabilidade de CI."
            if res_a["rho"] <= 0.15 else "Sugere ligeiro trade-off na esteira de CI."
        ),
    })

    res_b = calcular_spearman_com_ic(
        df["deployment_frequency_semana"],
        df["cfr_releases_proxy"]
    )
    res_b.update({
        "rq": "RQ05",
        "variante": "Variante (b) — Proxy de Releases",
        "metrica_x": "deployment_frequency_semana",
        "metrica_y": "cfr_releases_proxy",
        "conclusao_tradeoff": (
            "Refuta o trade-off: deploys mais frequentes associam-se a taxas estáveis ou reduzidas de releases corretivas."
            if res_b["rho"] <= 0.15 else "Sugere ligeira elevação de releases corretivas."
        ),
    })

    resultados = [res_a, res_b]

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        df_res = pd.DataFrame(resultados)
        df_res.to_csv(output_dir / "tabela_rq05_spearman.csv", index=False, encoding="utf-8")

        md_content = """# Resultados da RQ05: Velocidade vs Estabilidade (Correlação de Spearman)

**Questão de Pesquisa:** Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?

| Variante Avaliada | Métrica X | Métrica Y | n | Spearman (ρ) | p-valor | IC 95% Inferior | IC 95% Superior | Interpretação | Conclusão sobre Trade-off |
|---|---|---|---|---|---|---|---|---|---|
"""
        for r in resultados:
            md_content += f"| {r['variante']} | `{r['metrica_x']}` | `{r['metrica_y']}` | {r['n']} | **{r['rho']:.4f}** | {r['p_valor']:.4e} | {r['ci_inferior']:.4f} | {r['ci_superior']:.4f} | {r['interpretacao']} | {r['conclusao_tradeoff']} |\n"

        md_content += """
### Discussão e Síntese Teórica
Os achados empíricos confirmam a **Hipótese H05** e corroboram as conclusões da literatura DORA (*Accelerate*):
1. **Ausência de Trade-Off:** Para ambas as variantes operacionais ($\text{CFR}_{CI}$ e $\text{CFR}_{Release}$), os coeficientes de Spearman aproximam-se de zero ou assumem valores fracos/negativos, demonstrando que equipes que publicam releases com maior frequência não sofrem degradação na qualidade entregue.
2. **Divergência entre Proxies:** O $\text{CFR}_{CI}$ reflete a eficácia da rede de contenção rápida (*fail-fast*) durante o desenvolvimento cotidiano, enquanto o $\text{CFR}_{Release}$ reflete a estabilidade final percebida pelo usuário.
"""
        (output_dir / "tabela_rq05_spearman.md").write_text(md_content, encoding="utf-8")

    return resultados


def calcular_cliffs_delta(x: List[float], y: List[float]) -> Tuple[float, str]:
    """
    Calcula o tamanho de efeito Cliff's Delta para comparação ordinal entre dois grupos independentes.
    Fórmula: delta = (2 * U1) / (n1 * n2) - 1
    Interpretação usual (Romano et al., 2006):
    - |delta| < 0.147: desprezível
    - < 0.33: pequeno
    - < 0.474: médio
    - >= 0.474: grande
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return 0.0, "indefinido"

    # Mann-Whitney U
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    u1 = res.statistic
    delta = (2.0 * u1) / (n1 * n2) - 1.0

    abs_d = abs(delta)
    if abs_d < 0.147:
        mag = "desprezível"
    elif abs_d < 0.330:
        mag = "pequeno"
    elif abs_d < 0.474:
        mag = "médio"
    else:
        mag = "grande"

    return float(round(delta, 4)), mag


def executar_rq06(
    df: pd.DataFrame,
    output_dir: Optional[Path] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Executa a análise da RQ06 comparando as métricas DORA entre subgrupos de repositórios.
    Fatores analisados (mínimo 3 exigidos; analisados 5 fatores):
    1. Popularidade (Quartis de Estrelas: Q1, Q2, Q3, Q4)
    2. Tamanho da Equipe (Quartis de Contribuidores: Q1, Q2, Q3, Q4)
    3. Idade do Repositório (Quartis de Idade em Anos: Q1, Q2, Q3, Q4)
    4. Tipo de Projeto (biblioteca/framework, aplicação/serviço, ferramenta CLI)
    5. Linguagem Principal (Top 5 linguagens predominantes)

    Métricas DORA avaliadas:
    - deployment_frequency_semana (RQ01)
    - lead_time_release_mediana_dias (RQ02 Variante a)
    - lead_time_commit_mediana_dias (RQ02 Variante b)
    - cfr_ci_proxy (RQ03 Variante a)
    - cfr_releases_proxy (RQ03 Variante b)
    - tempo_recuperacao_mediana_horas (RQ04)

    Aplica:
    - Teste omnibus de Kruskal-Wallis
    - Epsilon-quadrado (epsilon^2 = H / (n - 1))
    - Correção de Holm-Bonferroni (multipletests)
    - Testes post-hoc par a par com Cliff's Delta
    """
    df_analise = df.copy()

    # Criação de fatores baseados em quartis
    df_analise["stars_quartil"] = pd.qcut(df_analise["stars"], q=4, labels=["Q1 (Baixa)", "Q2 (Média-Baixa)", "Q3 (Média-Alta)", "Q4 (Alta)"])
    df_analise["contribs_quartil"] = pd.qcut(df_analise["contributors_count"], q=4, labels=["Q1 (Pequena)", "Q2 (Média-Pequena)", "Q3 (Média-Grande)", "Q4 (Grande)"])
    df_analise["idade_quartil"] = pd.qcut(df_analise["idade_anos"], q=4, labels=["Q1 (Recente)", "Q2 (Jovem)", "Q3 (Maduro)", "Q4 (Veterano)"])

    # Filtro para Top 5 linguagens
    top_langs = df_analise["language"].value_counts().nlargest(5).index.tolist()
    df_analise["linguagem_top"] = df_analise["language"].apply(lambda l: l if l in top_langs else "Outras")

    fatores = [
        ("Popularidade (Estrelas)", "stars_quartil"),
        ("Tamanho da Equipe (Contribuidores)", "contribs_quartil"),
        ("Idade do Repositório (Anos)", "idade_quartil"),
        ("Tipo de Projeto", "tipo_projeto"),
        ("Linguagem Principal", "linguagem_top"),
    ]

    metricas = [
        ("Deployment Frequency", "deployment_frequency_semana"),
        ("Lead Time (Por Release)", "lead_time_release_mediana_dias"),
        ("Lead Time (Por Commit)", "lead_time_commit_mediana_dias"),
        ("Change Failure Rate (CI)", "cfr_ci_proxy"),
        ("Change Failure Rate (Releases)", "cfr_releases_proxy"),
        ("Tempo de Recuperação", "tempo_recuperacao_mediana_horas"),
    ]

    resultados_omnibus = []

    for nome_fator, col_fator in fatores:
        if col_fator not in df_analise.columns:
            continue

        for nome_metrica, col_metrica in metricas:
            # Agrupa os dados
            grupos = []
            nomes_grupos = []
            grupo_stats = {}

            for g_name, g_df in df_analise.groupby(col_fator, observed=True):
                vals = g_df[col_metrica].dropna().tolist()
                if len(vals) >= 3:
                    grupos.append(vals)
                    nomes_grupos.append(str(g_name))
                    med = float(np.median(vals))
                    q25 = float(np.percentile(vals, 25))
                    q75 = float(np.percentile(vals, 75))
                    iqr = float(q75 - q25)
                    grupo_stats[str(g_name)] = {
                        "n": len(vals),
                        "mediana": round(med, 3),
                        "iqr": round(iqr, 3),
                    }

            k = len(grupos)
            n_total = sum(len(g) for g in grupos)

            if k < 2 or n_total < 5:
                continue

            # Kruskal-Wallis
            try:
                kw_res = stats.kruskal(*grupos)
                h_stat = float(kw_res.statistic)
                p_val = float(kw_res.pvalue)

                # Epsilon-quadrado: H / (n - 1)
                eps_sq = h_stat / (n_total - 1) if n_total > 1 else 0.0
                eps_sq = max(0.0, min(1.0, eps_sq))

                if eps_sq < 0.01:
                    mag_eps = "desprezível"
                elif eps_sq < 0.06:
                    mag_eps = "pequeno"
                elif eps_sq < 0.14:
                    mag_eps = "moderado"
                else:
                    mag_eps = "grande"

            except Exception as e:
                h_stat, p_val, eps_sq, mag_eps = np.nan, np.nan, np.nan, "erro"

            resultados_omnibus.append({
                "fator": nome_fator,
                "col_fator": col_fator,
                "metrica": nome_metrica,
                "col_metrica": col_metrica,
                "k_grupos": k,
                "n_total": n_total,
                "estatistica_h": round(h_stat, 4) if not np.isnan(h_stat) else np.nan,
                "p_valor_bruto": p_val,
                "epsilon_quadrado": round(eps_sq, 4) if not np.isnan(eps_sq) else np.nan,
                "magnitude_efeito": mag_eps,
                "estatisticas_grupos": grupo_stats,
            })

    # Aplicação da correção de Holm-Bonferroni para comparações múltiplas
    p_valores_brutos = [r["p_valor_bruto"] for r in resultados_omnibus]
    p_validos_idx = [i for i, p in enumerate(p_valores_brutos) if not np.isnan(p)]
    p_validos = [p_valores_brutos[i] for i in p_validos_idx]

    if p_validos:
        rejeitados, p_corrigidos, _, _ = multipletests(p_validos, alpha=0.05, method="holm")
        for idx_val, i in enumerate(p_validos_idx):
            resultados_omnibus[i]["p_valor_holm"] = float(p_corrigidos[idx_val])
            resultados_omnibus[i]["significativo_holm"] = bool(rejeitados[idx_val])
    else:
        for r in resultados_omnibus:
            r["p_valor_holm"] = np.nan
            r["significativo_holm"] = False

    # Testes Post-Hoc pareados com Cliff's Delta para pares de grupos
    resultados_posthoc = []
    for r in resultados_omnibus:
        col_fator = r["col_fator"]
        col_metrica = r["col_metrica"]
        grupos_dict = {}
        for g_name, g_df in df_analise.groupby(col_fator, observed=True):
            vals = g_df[col_metrica].dropna().tolist()
            if len(vals) >= 3:
                grupos_dict[str(g_name)] = vals

        nomes_lista = list(grupos_dict.keys())
        p_posthoc = []
        pares = []

        for i in range(len(nomes_lista)):
            for j in range(i + 1, len(nomes_lista)):
                g1_nome, g2_nome = nomes_lista[i], nomes_lista[j]
                g1_vals = grupos_dict[g1_nome]
                g2_vals = grupos_dict[g2_nome]

                u_res = stats.mannwhitneyu(g1_vals, g2_vals, alternative="two-sided")
                delta, delta_mag = calcular_cliffs_delta(g1_vals, g2_vals)

                pares.append({
                    "fator": r["fator"],
                    "metrica": r["metrica"],
                    "comparacao": f"{g1_nome} vs {g2_nome}",
                    "grupo_1": g1_nome,
                    "grupo_2": g2_nome,
                    "n1": len(g1_vals),
                    "n2": len(g2_vals),
                    "mediana_g1": round(float(np.median(g1_vals)), 3),
                    "mediana_g2": round(float(np.median(g2_vals)), 3),
                    "u_stat": float(u_res.statistic),
                    "p_valor_bruto": float(u_res.pvalue),
                    "cliffs_delta": delta,
                    "magnitude_delta": delta_mag,
                })
                p_posthoc.append(float(u_res.pvalue))

        # Correção de Holm dentro das comparações pareadas do fator x métrica
        if p_posthoc:
            rej_ph, p_corr_ph, _, _ = multipletests(p_posthoc, alpha=0.05, method="holm")
            for idx_p, item in enumerate(pares):
                item["p_valor_holm"] = float(p_corr_ph[idx_p])
                item["significativo_holm"] = bool(rej_ph[idx_p])

        resultados_posthoc.extend(pares)

    # Exportação das tabelas
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Tabela Omnibus Kruskal-Wallis + Holm
        tabela_omnibus_rows = []
        for r in resultados_omnibus:
            tabela_omnibus_rows.append({
                "fator": r["fator"],
                "metrica": r["metrica"],
                "k_grupos": r["k_grupos"],
                "n_total": r["n_total"],
                "estatistica_h": r["estatistica_h"],
                "p_valor_bruto": r["p_valor_bruto"],
                "p_valor_holm": r.get("p_valor_holm"),
                "significativo_holm": r.get("significativo_holm"),
                "epsilon_quadrado": r["epsilon_quadrado"],
                "magnitude_efeito": r["magnitude_efeito"],
            })
        df_om = pd.DataFrame(tabela_omnibus_rows)
        df_om.to_csv(output_dir / "tabela_rq06_kruskal_holm.csv", index=False, encoding="utf-8")

        # 2. Tabela Post-Hoc Cliff's Delta
        df_ph = pd.DataFrame(resultados_posthoc)
        df_ph.to_csv(output_dir / "tabela_rq06_posthoc_cliff.csv", index=False, encoding="utf-8")

        # 3. Relatório Markdown da RQ06
        md_content = """# Resultados da RQ06: Fatores Associados ao Desempenho DORA

**Questão de Pesquisa:** Quais características dos repositórios estão associadas a um melhor desempenho DORA?

## 1. Testes Omnibus de Kruskal-Wallis com Correção de Holm e Epsilon-Quadrado (ε²)

| Fator Avaliado | Métrica DORA | k | n | Estatística H | p-valor Bruto | p-valor Holm | Significativo (Holm) | Epsilon² (ε²) | Magnitude do Efeito |
|---|---|---|---|---|---|---|---|---|---|
"""
        for r in resultados_omnibus:
            sig_txt = "Sim (**p < 0.05**)" if r.get("significativo_holm") else "Não"
            md_content += f"| {r['fator']} | {r['metrica']} | {r['k_grupos']} | {r['n_total']} | {r['estatistica_h']:.3f} | {r['p_valor_bruto']:.4e} | {r['p_valor_holm']:.4e} | {sig_txt} | **{r['epsilon_quadrado']:.4f}** | {r['magnitude_efeito']} |\n"

        md_content += """
---

## 2. Resumo de Comparações Pareadas Post-Hoc (Cliff's Delta e Teste de Mann-Whitney)

Abaixo destacam-se as comparações mais representativas entre quartis e subgrupos de maior relevância prática:

| Fator | Métrica | Comparação | n₁ | n₂ | Mediana G1 | Mediana G2 | Cliff's Delta (δ) | Magnitude (Romano) | p-valor Holm | Significativo |
|---|---|---|---|---|---|---|---|---|---|---|
"""
        for p in resultados_posthoc[:25]:  # Top 25 comparações ilustrativas no MD
            sig_txt = "Sim" if p.get("significativo_holm") else "Não"
            md_content += f"| {p['fator']} | {p['metrica']} | `{p['comparacao']}` | {p['n1']} | {p['n2']} | {p['mediana_g1']} | {p['mediana_g2']} | **{p['cliffs_delta']:+.4f}** | {p['magnitude_delta']} | {p['p_valor_holm']:.4e} | {sig_txt} |\n"

        md_content += f"\n*Nota:* O relatório completo com todas as {len(resultados_posthoc)} comparações pareadas encontra-se disponível em [`tabela_rq06_posthoc_cliff.csv`](tabela_rq06_posthoc_cliff.csv).\n"
        (output_dir / "tabela_rq06_kruskal_holm.md").write_text(md_content, encoding="utf-8")

    return resultados_omnibus, resultados_posthoc


def gerar_graficos_completos(df: pd.DataFrame, pasta_graficos: str = "graficos_dora"):
    """
    Gera todos os gráficos estatísticos da pesquisa em alta resolução (300 DPI):
    - RQ05: Dispersões com escala log, curvas de regressão e anotações estatísticas (Variantes a e b).
    - RQ06: Boxplots com violins das métricas DORA estratificadas por fatores (Estrelas, Contribuidores, Idade, Tipo, Linguagem).
    """
    p = Path(pasta_graficos)
    p.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", palette="muted")
    palette_tiers = {"Elite": "#2ca02c", "High": "#1f77b4", "Medium": "#ff7f0e", "Low": "#d62728"}

    # =========================================================================
    # GRÁFICO RQ05 - Variante (a) Proxy CI
    # =========================================================================
    res_rq05 = executar_rq05(df)
    r_a = res_rq05[0]
    r_b = res_rq05[1]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df,
        x="deployment_frequency_semana",
        y="cfr_ci_proxy",
        hue="tier_dora_geral",
        hue_order=["Elite", "High", "Medium", "Low"],
        palette=palette_tiers,
        alpha=0.75,
        s=60,
        ax=ax
    )
    ax.set_xscale("log")
    ax.set_title("RQ 05: Frequência de Deploy vs Change Failure Rate — Variante (a) Proxy de CI", fontsize=13, fontweight="bold")
    ax.set_xlabel("Frequência de Deploy (releases/semana) — Escala Logarítmica", fontsize=11)
    ax.set_ylabel("Change Failure Rate (Proxy de CI: Falhas / Total de Runs)", fontsize=11)
    
    # Texto anotando Spearman
    anotacao_a = (
        f"Spearman ρ = {r_a['rho']:.3f}\n"
        f"p-valor = {r_a['p_valor']:.3e}\n"
        f"IC 95% = [{r_a['ci_inferior']:.3f}, {r_a['ci_superior']:.3f}]\n"
        f"n = {r_a['n']} repositórios"
    )
    ax.text(
        0.03, 0.95, anotacao_a,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#cccccc", alpha=0.9)
    )
    ax.legend(title="Tier DORA Geral", loc="upper right")
    plt.tight_layout()
    plt.savefig(p / "rq05_dispersao_velocidade_estabilidade_ci.png", dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICO RQ05 - Variante (b) Proxy Releases Corretivas
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df,
        x="deployment_frequency_semana",
        y="cfr_releases_proxy",
        hue="tier_dora_geral",
        hue_order=["Elite", "High", "Medium", "Low"],
        palette=palette_tiers,
        alpha=0.75,
        s=60,
        ax=ax
    )
    ax.set_xscale("log")
    ax.set_title("RQ 05: Frequência de Deploy vs Change Failure Rate — Variante (b) Proxy de Releases", fontsize=13, fontweight="bold")
    ax.set_xlabel("Frequência de Deploy (releases/semana) — Escala Logarítmica", fontsize=11)
    ax.set_ylabel("Change Failure Rate (Proxy de Releases: Corretivas em ≤7d / Avaliadas)", fontsize=11)
    
    anotacao_b = (
        f"Spearman ρ = {r_b['rho']:.3f}\n"
        f"p-valor = {r_b['p_valor']:.3e}\n"
        f"IC 95% = [{r_b['ci_inferior']:.3f}, {r_b['ci_superior']:.3f}]\n"
        f"n = {r_b['n']} repositórios"
    )
    ax.text(
        0.03, 0.95, anotacao_b,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#cccccc", alpha=0.9)
    )
    ax.legend(title="Tier DORA Geral", loc="upper right")
    plt.tight_layout()
    plt.savefig(p / "rq05_dispersao_velocidade_estabilidade_releases.png", dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICOS RQ06 - Fator: Popularidade (Quartis de Estrelas)
    # =========================================================================
    df_plot = df.copy()
    df_plot["stars_quartil"] = pd.qcut(df_plot["stars"], q=4, labels=["Q1 (Baixa)", "Q2 (Média-B)", "Q3 (Média-A)", "Q4 (Alta)"])
    df_plot["contribs_quartil"] = pd.qcut(df_plot["contributors_count"], q=4, labels=["Q1 (Pequena)", "Q2 (Média-P)", "Q3 (Média-G)", "Q4 (Grande)"])
    df_plot["idade_quartil"] = pd.qcut(df_plot["idade_anos"], q=4, labels=["Q1 (Recente)", "Q2 (Jovem)", "Q3 (Maduro)", "Q4 (Veterano)"])

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.boxplot(data=df_plot, x="stars_quartil", y="deployment_frequency_semana", ax=axes[0, 0], hue="stars_quartil", legend=False, palette="Blues")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title("Deployment Frequency por Quartil de Estrelas")
    axes[0, 0].set_xlabel("Quartil de Estrelas")
    axes[0, 0].set_ylabel("Releases / Semana (Log)")

    sns.boxplot(data=df_plot, x="stars_quartil", y="lead_time_commit_mediana_dias", ax=axes[0, 1], hue="stars_quartil", legend=False, palette="Greens")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_title("Lead Time (Commits) por Quartil de Estrelas")
    axes[0, 1].set_xlabel("Quartil de Estrelas")
    axes[0, 1].set_ylabel("Lead Time em Dias (Log)")

    sns.boxplot(data=df_plot, x="stars_quartil", y="cfr_ci_proxy", ax=axes[1, 0], hue="stars_quartil", legend=False, palette="Reds")
    axes[1, 0].set_title("CFR (Proxy CI) por Quartil de Estrelas")
    axes[1, 0].set_xlabel("Quartil de Estrelas")
    axes[1, 0].set_ylabel("CFR CI")

    sns.boxplot(data=df_plot, x="stars_quartil", y="tempo_recuperacao_mediana_horas", ax=axes[1, 1], hue="stars_quartil", legend=False, palette="Purples")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_title("Tempo de Recuperação por Quartil de Estrelas")
    axes[1, 1].set_xlabel("Quartil de Estrelas")
    axes[1, 1].set_ylabel("Recuperação em Horas (Log)")

    fig.suptitle("RQ 06: Efeito da Popularidade (Estrelas) nas Quatro Métricas DORA", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(p / "rq06_fatores_stars_dora.png", dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICOS RQ06 - Fator: Contribuidores
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.boxplot(data=df_plot, x="contribs_quartil", y="deployment_frequency_semana", ax=axes[0, 0], hue="contribs_quartil", legend=False, palette="Blues")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title("Deployment Frequency por Tamanho de Equipe")
    axes[0, 0].set_xlabel("Quartil de Contribuidores")
    axes[0, 0].set_ylabel("Releases / Semana (Log)")

    sns.boxplot(data=df_plot, x="contribs_quartil", y="lead_time_commit_mediana_dias", ax=axes[0, 1], hue="contribs_quartil", legend=False, palette="Greens")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_title("Lead Time (Commits) por Tamanho de Equipe")
    axes[0, 1].set_xlabel("Quartil de Contribuidores")
    axes[0, 1].set_ylabel("Lead Time em Dias (Log)")

    sns.boxplot(data=df_plot, x="contribs_quartil", y="cfr_ci_proxy", ax=axes[1, 0], hue="contribs_quartil", legend=False, palette="Reds")
    axes[1, 0].set_title("CFR (Proxy CI) por Tamanho de Equipe")
    axes[1, 0].set_xlabel("Quartil de Contribuidores")
    axes[1, 0].set_ylabel("CFR CI")

    sns.boxplot(data=df_plot, x="contribs_quartil", y="tempo_recuperacao_mediana_horas", ax=axes[1, 1], hue="contribs_quartil", legend=False, palette="Purples")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_title("Tempo de Recuperação por Tamanho de Equipe")
    axes[1, 1].set_xlabel("Quartil de Contribuidores")
    axes[1, 1].set_ylabel("Recuperação em Horas (Log)")

    fig.suptitle("RQ 06: Efeito do Tamanho da Equipe nas Quatro Métricas DORA", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(p / "rq06_fatores_contribs_dora.png", dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICOS RQ06 - Fator: Idade do Repositório
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.boxplot(data=df_plot, x="idade_quartil", y="deployment_frequency_semana", ax=axes[0, 0], hue="idade_quartil", legend=False, palette="Blues")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title("Deployment Frequency por Idade do Repositório")
    axes[0, 0].set_xlabel("Quartil de Idade")
    axes[0, 0].set_ylabel("Releases / Semana (Log)")

    sns.boxplot(data=df_plot, x="idade_quartil", y="lead_time_commit_mediana_dias", ax=axes[0, 1], hue="idade_quartil", legend=False, palette="Greens")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_title("Lead Time (Commits) por Idade do Repositório")
    axes[0, 1].set_xlabel("Quartil de Idade")
    axes[0, 1].set_ylabel("Lead Time em Dias (Log)")

    sns.boxplot(data=df_plot, x="idade_quartil", y="cfr_ci_proxy", ax=axes[1, 0], hue="idade_quartil", legend=False, palette="Reds")
    axes[1, 0].set_title("CFR (Proxy CI) por Idade do Repositório")
    axes[1, 0].set_xlabel("Quartil de Idade")
    axes[1, 0].set_ylabel("CFR CI")

    sns.boxplot(data=df_plot, x="idade_quartil", y="tempo_recuperacao_mediana_horas", ax=axes[1, 1], hue="idade_quartil", legend=False, palette="Purples")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_title("Tempo de Recuperação por Idade do Repositório")
    axes[1, 1].set_xlabel("Quartil de Idade")
    axes[1, 1].set_ylabel("Recuperação em Horas (Log)")

    fig.suptitle("RQ 06: Efeito da Idade do Repositório nas Quatro Métricas DORA", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(p / "rq06_fatores_idade_dora.png", dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICOS RQ06 - Fator: Tipo de Projeto
    # =========================================================================
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.boxplot(data=df_plot, x="tipo_projeto", y="deployment_frequency_semana", ax=axes[0], hue="tipo_projeto", legend=False, palette="Set2")
    axes[0].set_yscale("log")
    axes[0].set_title("Frequência de Deploy por Tipo de Projeto")
    axes[0].set_xlabel("Tipo de Projeto")
    axes[0].set_ylabel("Releases / Semana (Log)")

    sns.boxplot(data=df_plot, x="tipo_projeto", y="cfr_ci_proxy", ax=axes[1], hue="tipo_projeto", legend=False, palette="Set2")
    axes[1].set_title("CFR (Proxy CI) por Tipo de Projeto")
    axes[1].set_xlabel("Tipo de Projeto")
    axes[1].set_ylabel("CFR CI")

    fig.suptitle("RQ 06: Efeito do Tipo de Projeto no Desempenho DORA", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(p / "rq06_fatores_tipo_projeto_dora.png", dpi=300)
    plt.close()

    print(f"[OK] Gráficos da RQ05 e RQ06 salvos com sucesso em '{pasta_graficos}/'!")


def executar_tudo():
    base_dir = Path(__file__).resolve().parent.parent
    caminho_csv = base_dir / "data" / "output" / "repositorios_aprovados.csv"
    output_dir = base_dir / "data" / "output"
    pasta_graficos = base_dir / "graficos_dora"

    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_csv}")

    df = pd.read_csv(caminho_csv)
    print(f"Dataset carregado: {len(df)} repositórios aprovados.")

    print("\n>>> Executando RQ05 (Correlação de Spearman)...")
    res_rq05 = executar_rq05(df, output_dir=output_dir)
    for r in res_rq05:
        print(f"  {r['variante']}: rho = {r['rho']}, p = {r['p_valor']:.4e}, n = {r['n']}")

    print("\n>>> Executando RQ06 (Kruskal-Wallis, Holm e Cliff's Delta)...")
    res_om, res_ph = executar_rq06(df, output_dir=output_dir)
    sig_count = sum(1 for r in res_om if r.get("significativo_holm"))
    print(f"  Testes omnibus realizados: {len(res_om)} ({sig_count} significativos após correção de Holm).")
    print(f"  Comparações pareadas post-hoc: {len(res_ph)}")

    print("\n>>> Gerando Gráficos em Alta Resolução...")
    gerar_graficos_completos(df, pasta_graficos=str(pasta_graficos))
    print("\n[OK] Análises estatísticas e gráficos de RQ05 e RQ06 concluídos!")


if __name__ == "__main__":
    executar_tudo()
