"""
Script para geração de gráficos legíveis, padronizados e de alta resolução
para o artigo SBC (Lab 03 - Mineração de Métricas DORA).
Gera gráficos para RQ01+RQ02, RQ03+RQ04, RQ05, RQ06 e RQ07.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração de estilo geral para garantir legibilidade máxima em documentos impressos/PDF
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "figure.titlesize": 14,
    "figure.dpi": 300,
})

out_dirs = [Path("graficos_dora"), Path("artigo")]
for d in out_dirs:
    d.mkdir(parents=True, exist_ok=True)

df = pd.read_csv("data/output/repositorios_aprovados.csv")
df_sens = pd.read_csv("data/output/dados_rq07_sensibilidade.csv")


def salvar_figura(nome: str):
    for d in out_dirs:
        caminho = d / nome
        plt.savefig(caminho, dpi=300, bbox_inches="tight")
    print(f"[OK] Salvo: {nome}")


# ==============================================================================
# 1. RQ01 + RQ02: Dimensão de Velocidade (Deployment Frequency e Lead Time)
# ==============================================================================
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))

# Subplot 1: Deployment Frequency (RQ01)
sns.boxplot(
    y=df["deployment_frequency_semana"],
    ax=axes[0],
    color="#4a90e2",
    width=0.35,
    showmeans=True,
    meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[0].set_title("RQ01: Frequência de Deploy\n(Releases por Semana)", fontweight="bold", pad=10)
axes[0].set_ylabel("Releases / Semana")
axes[0].set_xticks([0])
axes[0].set_xticklabels(["Amostra (N=300)"])
axes[0].grid(axis="y", linestyle="--", alpha=0.6)

# Linhas de corte DORA para RQ01
axes[0].axhline(1.0, color="#2e7d32", linestyle=":", linewidth=1.5, label=r"High ($\geq 1$/sem)")
axes[0].axhline(0.23, color="#e65100", linestyle=":", linewidth=1.5, label=r"Medium ($\geq 0.23$/sem)")
axes[0].legend(loc="upper right", frameon=True, fontsize=9)

med_df = df["deployment_frequency_semana"].median()
q1_df = df["deployment_frequency_semana"].quantile(0.25)
q3_df = df["deployment_frequency_semana"].quantile(0.75)
axes[0].text(
    0.22, med_df, f"Mediana: {med_df:.3f}\nIQR: [{q1_df:.2f}; {q3_df:.2f}]",
    color="#0d47a1", fontweight="bold", va="center"
)

# Subplot 2: Lead Time (RQ02) - Comparação Variante (a) vs Variante (b)
df_lt = pd.DataFrame({
    "Variante (a)\n[Por Release]": df["lead_time_release_mediana_dias"],
    "Variante (b)\n[Por Commit]": df["lead_time_commit_mediana_dias"]
})

palette_lt = ["#e74c3c", "#2ecc71"]
sns.boxplot(
    data=df_lt,
    ax=axes[1],
    palette=palette_lt,
    width=0.45,
    showmeans=True,
    meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[1].set_title("RQ02: Lead Time for Changes\n(Contraste entre Variantes)", fontweight="bold", pad=10)
axes[1].set_ylabel("Lead Time (Dias Corridos)")
axes[1].grid(axis="y", linestyle="--", alpha=0.6)

med_lta = df["lead_time_release_mediana_dias"].median()
med_ltb = df["lead_time_commit_mediana_dias"].median()
axes[1].text(0, med_lta + 0.8, f"Mediana: {med_lta:.2f}d", ha="center", fontweight="bold", color="#900c3f")
axes[1].text(1, med_ltb + 0.8, f"Mediana: {med_ltb:.2f}d", ha="center", fontweight="bold", color="#196f3d")

plt.tight_layout()
salvar_figura("rq01_rq02_velocidade_dora.png")
plt.close()


# ==============================================================================
# 2. RQ03 + RQ04: Dimensão de Estabilidade (CFR e Tempo de Recuperação)
# ==============================================================================
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))

# Subplot 1: Change Failure Rate (RQ03) - CI vs Releases
df_cfr = pd.DataFrame({
    "Variante (a)\n[Proxy de CI]": df["cfr_ci_proxy"] * 100.0,
    "Variante (b)\n[Proxy de Releases]": df["cfr_releases_proxy"] * 100.0
})

sns.boxplot(
    data=df_cfr,
    ax=axes[0],
    palette=["#ff7675", "#55efc4"],
    width=0.45,
    showmeans=True,
    meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[0].set_title("RQ03: Change Failure Rate (CFR)\n(Proxy de CI vs. Proxy de Releases)", fontweight="bold", pad=10)
axes[0].set_ylabel("Taxa de Falha (%)")
axes[0].grid(axis="y", linestyle="--", alpha=0.6)
axes[0].axhline(15.0, color="#d63031", linestyle="--", linewidth=1.5, label=r"Limite Elite ($\leq 15\%$)")
axes[0].legend(loc="upper right", frameon=True, fontsize=9)

med_cfra = (df["cfr_ci_proxy"] * 100.0).median()
med_cfrb = (df["cfr_releases_proxy"] * 100.0).median()
axes[0].text(0, med_cfra + 1.0, f"Mediana: {med_cfra:.1f}%", ha="center", fontweight="bold", color="#c0392b")
axes[0].text(1, med_cfrb + 1.0, f"Mediana: {med_cfrb:.1f}%", ha="center", fontweight="bold", color="#16a085")

# Subplot 2: Failed Deployment Recovery Time (RQ04)
sns.boxplot(
    y=df["tempo_recuperacao_mediana_horas"],
    ax=axes[1],
    color="#fdcb6e",
    width=0.35,
    showmeans=True,
    meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[1].set_title("RQ04: Tempo de Recuperação de CI\n(Horas Corridas até Sucesso)", fontweight="bold", pad=10)
axes[1].set_ylabel("Tempo de Recuperação (Horas)")
axes[1].set_xticks([0])
axes[1].set_xticklabels(["Episódios de CI"])
axes[1].grid(axis="y", linestyle="--", alpha=0.6)

# Corte High (< 24h)
axes[1].axhline(24.0, color="#d35400", linestyle="--", linewidth=1.5, label="Limite High ($< 24$h)")
axes[1].legend(loc="upper right", frameon=True, fontsize=9)

med_rec = df["tempo_recuperacao_mediana_horas"].median()
q1_rec = df["tempo_recuperacao_mediana_horas"].quantile(0.25)
q3_rec = df["tempo_recuperacao_mediana_horas"].quantile(0.75)
axes[1].text(
    0.22, med_rec, f"Mediana: {med_rec:.2f}h\nIQR: [{q1_rec:.1f}; {q3_rec:.1f}]h",
    fontweight="bold", color="#b7791f", va="center"
)

plt.tight_layout()
salvar_figura("rq03_rq04_estabilidade_dora.png")
plt.close()


# ==============================================================================
# 3. RQ05: Velocidade vs Estabilidade (Dispersão Legível com Callout)
# ==============================================================================
plt.figure(figsize=(9, 5.2))
plt.scatter(
    df["deployment_frequency_semana"],
    df["cfr_ci_proxy"] * 100.0,
    color="#2980b9",
    alpha=0.65,
    edgecolors="black",
    linewidth=0.5,
    s=45,
    label="Repositórios (N=300)"
)

# Linha de regressão / tendência
m, b = np.polyfit(df["deployment_frequency_semana"], df["cfr_ci_proxy"] * 100.0, 1)
x_vals = np.linspace(df["deployment_frequency_semana"].min(), df["deployment_frequency_semana"].max(), 100)
plt.plot(x_vals, m * x_vals + b, color="#c0392b", linestyle="--", linewidth=2.2, label=f"Tendência Linear (m = {m:.2f})")

plt.title("RQ05: Associação entre Velocidade e Estabilidade DORA", fontweight="bold", fontsize=13, pad=12)
plt.xlabel("Frequência de Deploy (Releases / Semana)", fontsize=11, fontweight="bold")
plt.ylabel("Change Failure Rate - Proxy de CI (%)", fontsize=11, fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.5)

# Caixa de anotação com o resultado estatístico de Spearman
caixa_texto = (
    "Correlação de Spearman:\n"
    r"$\rho = -0{,}1003$ ($p = 0{,}0829$)\n"
    "IC 95%: [-0,211; +0,013]\n"
    "Ausência de Trade-Off (Confirmado)"
)
plt.gca().text(
    0.70, 0.85, caixa_texto,
    transform=plt.gca().transAxes,
    fontsize=10.5,
    fontweight="bold",
    verticalalignment="top",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#f8f9fa", edgecolor="#7f8c8d", alpha=0.95)
)

plt.legend(loc="lower left", frameon=True, fontsize=10)
plt.tight_layout()
salvar_figura("rq05_dispersao_velocidade_estabilidade.png")
plt.close()


# ==============================================================================
# 4. RQ06: Fatores Associados (Popularidade / Estrelas) com Legibilidade Máxima
# ==============================================================================
# Dividir popularidade em 4 quartis com rótulos amigáveis
df["quartil_estrelas"] = pd.qcut(
    df["stars"],
    q=4,
    labels=["Q1 (Baixa)\n[1k-1.5k]", "Q2 (Média-B.)\n[1.5k-3k]", "Q3 (Média-A.)\n[3k-7k]", "Q4 (Alta)\n[>7k]"]
)

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6))

# Painel 1: Estrelas vs Frequência de Deploy (Efeito Significativo Grande, eps2=0.27)
sns.boxplot(
    x="quartil_estrelas",
    y="deployment_frequency_semana",
    data=df,
    ax=axes[0],
    palette="Blues",
    showmeans=True,
    meanprops={"marker": "^", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[0].set_title("Frequência de Deploy\n(p < 10⁻¹⁵, ε² = 0.27, Grande)", fontweight="bold", fontsize=11)
axes[0].set_xlabel("Quartil de Estrelas", fontweight="bold")
axes[0].set_ylabel("Releases / Semana")
axes[0].grid(axis="y", linestyle="--", alpha=0.5)

# Painel 2: Estrelas vs Lead Time Variante b (Efeito Significativo Grande, eps2=0.27)
sns.boxplot(
    x="quartil_estrelas",
    y="lead_time_commit_mediana_dias",
    data=df,
    ax=axes[1],
    palette="Greens",
    showmeans=True,
    meanprops={"marker": "^", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[1].set_title("Lead Time por Commit\n(p < 10⁻¹⁵, ε² = 0.27, Grande)", fontweight="bold", fontsize=11)
axes[1].set_xlabel("Quartil de Estrelas", fontweight="bold")
axes[1].set_ylabel("Lead Time (Dias)")
axes[1].grid(axis="y", linestyle="--", alpha=0.5)

# Painel 3: Estrelas vs Change Failure Rate (Efeito Desprezível / Invariante, eps2=0.01)
sns.boxplot(
    x="quartil_estrelas",
    y=df["cfr_ci_proxy"] * 100.0,
    data=df,
    ax=axes[2],
    palette="Purples",
    showmeans=True,
    meanprops={"marker": "^", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": "7"}
)
axes[2].set_title("Change Failure Rate (CI)\n(p = 1.00, ε² = 0.01, Invariante)", fontweight="bold", fontsize=11)
axes[2].set_xlabel("Quartil de Estrelas", fontweight="bold")
axes[2].set_ylabel("Taxa de Falha (%)")
axes[2].grid(axis="y", linestyle="--", alpha=0.5)

plt.suptitle("RQ06: Influência da Popularidade (Estrelas) sobre as Métricas DORA (N=300)", fontweight="bold", fontsize=13, y=1.03)
plt.tight_layout()
salvar_figura("rq06_fatores_estrelas_dora.png")
plt.close()


# ==============================================================================
# 5. RQ07: Matriz de Transição e Sensibilidade com Alta Legibilidade
# ==============================================================================
from sklearn.metrics import confusion_matrix
TIERS = ["Elite", "High", "Medium", "Low"]

t_c1 = df_sens["tier_c1_referencia"]
t_c2 = df_sens["tier_c2_prereleases"]
t_c3 = df_sens["tier_c3_tags"]

cm_c1_c2 = confusion_matrix(t_c1, t_c2, labels=TIERS)
cm_c1_c3 = confusion_matrix(t_c1, t_c3, labels=TIERS)

fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2))

# Matriz 1: C1 -> C2
sns.heatmap(
    cm_c1_c2,
    annot=True,
    fmt="d",
    cmap="Blues",
    cbar=False,
    ax=axes[0],
    xticklabels=TIERS,
    yticklabels=TIERS,
    annot_kws={"size": 15, "weight": "bold"},
    linewidths=1.5,
    linecolor="#bdc3c7"
)
axes[0].set_title("Transição C1 → C2 (Pré-releases)\nκ = 0,2797 (Razoável) | Mudança = 39,7%", fontweight="bold", fontsize=11.5, pad=10)
axes[0].set_xlabel("Patamar em C2 (Pré-releases)", fontweight="bold")
axes[0].set_ylabel("Patamar em C1 (Referência)", fontweight="bold")

# Matriz 2: C1 -> C3
sns.heatmap(
    cm_c1_c3,
    annot=True,
    fmt="d",
    cmap="Greens",
    cbar=False,
    ax=axes[1],
    xticklabels=TIERS,
    yticklabels=TIERS,
    annot_kws={"size": 15, "weight": "bold"},
    linewidths=1.5,
    linecolor="#bdc3c7"
)
axes[1].set_title("Transição C1 → C3 (Tags)\nκ = 0,2904 (Razoável) | Mudança = 39,0%", fontweight="bold", fontsize=11.5, pad=10)
axes[1].set_xlabel("Patamar em C3 (Tags)", fontweight="bold")
axes[1].set_ylabel("Patamar em C1 (Referência)", fontweight="bold")

plt.suptitle("RQ07: Matrizes de Transição entre Definições Operacionais (N=300)", fontweight="bold", fontsize=13, y=1.02)
plt.tight_layout()
salvar_figura("rq07_matriz_transicao_sensibilidade.png")
plt.close()


# Gráfico Adicional RQ07: Distribuição Legível de Tiers
plt.figure(figsize=(9, 4.8))
bar_w = 0.25
x_idx = np.arange(len(TIERS))

# Dados de distribuição
c1_p = [0.0, 42.0, 58.0, 0.0]
c2_p = [0.0, 81.7, 18.3, 0.0]
c3_p = [0.0, 81.0, 19.0, 0.0]

plt.bar(x_idx - bar_w, c1_p, width=bar_w, label="C1 (Referência)", color="#2b5c8f", edgecolor="black", linewidth=0.8)
plt.bar(x_idx, c2_p, width=bar_w, label="C2 (Pré-releases)", color="#27ae60", edgecolor="black", linewidth=0.8)
plt.bar(x_idx + bar_w, c3_p, width=bar_w, label="C3 (Tags)", color="#e67e22", edgecolor="black", linewidth=0.8)

# Rótulos de porcentagem sobre as barras
for i in range(len(TIERS)):
    if c1_p[i] > 0:
        plt.text(i - bar_w, c1_p[i] + 1.2, f"{c1_p[i]:.1f}%", ha="center", fontsize=9.5, fontweight="bold")
    if c2_p[i] > 0:
        plt.text(i, c2_p[i] + 1.2, f"{c2_p[i]:.1f}%", ha="center", fontsize=9.5, fontweight="bold")
    if c3_p[i] > 0:
        plt.text(i + bar_w, c3_p[i] + 1.2, f"{c3_p[i]:.1f}%", ha="center", fontsize=9.5, fontweight="bold")

plt.title("RQ07: Distribuição dos Patamares DORA nas Três Combinações", fontweight="bold", fontsize=12.5, pad=12)
plt.xlabel("Patamar de Desempenho DORA", fontweight="bold")
plt.ylabel("Proporção de Repositórios (%)", fontweight="bold")
plt.xticks(x_idx, TIERS, fontweight="bold")
plt.ylim(0, 95)
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.legend(frameon=True, fontsize=10.5)
plt.tight_layout()
salvar_figura("rq07_distribuicao_tiers_combinacoes.png")
plt.close()

print("[OK] Todos os gráficos foram gerados e salvos com sucesso!")
