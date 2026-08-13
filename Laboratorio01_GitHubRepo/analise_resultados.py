"""
Análise de Resultados — Lab01: Mineração de Repositórios Populares do GitHub
==============================================================================
Script único que lê os CSVs gerados pelos scripts de coleta (RQ01–RQ07),
calcula estatísticas descritivas (medianas, contagens) e gera gráficos
para cada Research Question.

Uso:
    python analise_resultados.py

Saída:
    - Gráficos salvos como .png na pasta graficos/
    - Resumo estatístico impresso no terminal
"""

import csv
import os
import math
from datetime import datetime, timezone
from collections import Counter

# ──────────────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAFICOS_DIR = os.path.join(BASE_DIR, "graficos")
os.makedirs(GRAFICOS_DIR, exist_ok=True)

# Data de referência para cálculo de idade (momento da análise)
AGORA = datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────
# Utilitários
# ──────────────────────────────────────────────────────────────────────
def ler_csv(nome_arquivo):
    """Lê um CSV e retorna lista de dicionários."""
    caminho = os.path.join(BASE_DIR, nome_arquivo)
    with open(caminho, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if any(v.strip() for v in row.values())]


def mediana(valores):
    """Calcula a mediana de uma lista de números."""
    valores_sorted = sorted(valores)
    n = len(valores_sorted)
    if n == 0:
        return 0
    meio = n // 2
    if n % 2 == 0:
        return (valores_sorted[meio - 1] + valores_sorted[meio]) / 2
    return valores_sorted[meio]


def quartis(valores):
    """Retorna (Q1, mediana, Q3) de uma lista de números."""
    valores_sorted = sorted(valores)
    n = len(valores_sorted)
    if n == 0:
        return (0, 0, 0)
    med = mediana(valores_sorted)
    metade_inferior = valores_sorted[:n // 2]
    metade_superior = valores_sorted[(n + 1) // 2:]
    q1 = mediana(metade_inferior) if metade_inferior else med
    q3 = mediana(metade_superior) if metade_superior else med
    return (q1, med, q3)


def parse_data(data_str):
    """Converte string ISO 8601 para datetime."""
    return datetime.fromisoformat(data_str.replace("Z", "+00:00"))


def idade_anos(data_str):
    """Calcula a idade em anos (float) a partir de uma data ISO."""
    dt = parse_data(data_str)
    delta = AGORA - dt
    return delta.days / 365.25


def parse_frequencia(valor_str):
    """
    Converte a coluna 'Frequencia issues' para um valor numérico (issues/mês).
    - "X issues/mês" → X
    - "Múltiplas issues no mesmo dia" → 900 (valor alto)
    - "Sem issues" → None (excluído da análise numérica)
    - "0 issues/mês" → 0
    - "Apenas 1 issue" → valor baixo (~0.1)
    """
    valor_str = valor_str.strip()
    if "Sem issues" in valor_str:
        return None
    if "Múltiplas issues no mesmo dia" in valor_str:
        return 900
    if "Apenas 1 issue" in valor_str:
        return 0.1
    try:
        return float(valor_str.split()[0])
    except (ValueError, IndexError):
        return None


# ──────────────────────────────────────────────────────────────────────
# Gráficos com matplotlib
# ──────────────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend sem GUI
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠️  matplotlib não encontrado. Instale com: pip install matplotlib")
    print("   Os gráficos NÃO serão gerados, mas as estatísticas serão impressas.\n")


def configurar_estilo():
    """Configura estilo visual dos gráficos."""
    if not HAS_MPL:
        return
    plt.rcParams.update({
        'figure.figsize': (12, 6),
        'figure.dpi': 150,
        'font.size': 11,
        'font.family': 'sans-serif',
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
        'axes.labelsize': 12,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'axes.facecolor': '#fafafa',
        'figure.facecolor': '#ffffff',
    })


def salvar_grafico(fig, nome):
    """Salva figura e fecha."""
    caminho = os.path.join(GRAFICOS_DIR, nome)
    fig.tight_layout()
    fig.savefig(caminho, bbox_inches='tight')
    plt.close(fig)
    print(f"  📊 Gráfico salvo: graficos/{nome}")


# ──────────────────────────────────────────────────────────────────────
# RQ01 — Idade dos repositórios
# ──────────────────────────────────────────────────────────────────────
def analisar_rq01():
    print("\n" + "=" * 60)
    print("RQ01 — Sistemas populares são maduros/antigos?")
    print("=" * 60)

    dados = ler_csv("repositorios_populares.csv")
    idades = [idade_anos(r['Criado Em']) for r in dados]

    q1, med, q3 = quartis(idades)
    print(f"  Repositórios analisados: {len(idades)}")
    print(f"  Idade mínima:  {min(idades):.1f} anos")
    print(f"  Q1:            {q1:.1f} anos")
    print(f"  Mediana:       {med:.1f} anos")
    print(f"  Q3:            {q3:.1f} anos")
    print(f"  Idade máxima:  {max(idades):.1f} anos")

    if HAS_MPL:
        fig, ax = plt.subplots()
        cor = '#4A90D9'
        n_bins = max(10, int(math.sqrt(len(idades))))
        counts, bins, patches = ax.hist(idades, bins=n_bins, color=cor,
                                         edgecolor='white', alpha=0.85)
        ax.axvline(med, color='#E74C3C', linestyle='--', linewidth=2,
                   label=f'Mediana = {med:.1f} anos')
        ax.set_xlabel('Idade do Repositório (anos)')
        ax.set_ylabel('Número de Repositórios')
        ax.set_title('RQ01 — Distribuição da Idade dos Repositórios Populares')
        ax.legend()
        salvar_grafico(fig, 'rq01_idade_repositorios.png')

    return med


# ──────────────────────────────────────────────────────────────────────
# RQ02 — Pull Requests Aceitas
# ──────────────────────────────────────────────────────────────────────
def analisar_rq02():
    print("\n" + "=" * 60)
    print("RQ02 — Sistemas populares recebem muita contribuição externa?")
    print("=" * 60)

    dados = ler_csv("pull_requests_aceitas.csv")
    prs = [int(r['Pull Requests Aceitas']) for r in dados]

    q1, med, q3 = quartis(prs)
    print(f"  Repositórios analisados: {len(prs)}")
    print(f"  Mínimo PRs:    {min(prs)}")
    print(f"  Q1:            {q1:.0f}")
    print(f"  Mediana:       {med:.0f}")
    print(f"  Q3:            {q3:.0f}")
    print(f"  Máximo PRs:    {max(prs)}")

    if HAS_MPL:
        fig, ax = plt.subplots()
        cor = '#27AE60'
        # Usar escala log para melhor visualização dos outliers
        prs_log = [max(p, 1) for p in prs]  # evitar log(0)
        n_bins = 20
        ax.hist(prs_log, bins=n_bins, color=cor, edgecolor='white', alpha=0.85)
        ax.axvline(med, color='#E74C3C', linestyle='--', linewidth=2,
                   label=f'Mediana = {med:.0f}')
        ax.set_xscale('log')
        ax.set_xlabel('Pull Requests Aceitas (escala log)')
        ax.set_ylabel('Número de Repositórios')
        ax.set_title('RQ02 — Distribuição de Pull Requests Aceitas')
        ax.legend()
        salvar_grafico(fig, 'rq02_pull_requests.png')

    return med


# ──────────────────────────────────────────────────────────────────────
# RQ03 — Releases
# ──────────────────────────────────────────────────────────────────────
def analisar_rq03():
    print("\n" + "=" * 60)
    print("RQ03 — Sistemas populares lançam releases com frequência?")
    print("=" * 60)

    dados = ler_csv("releases.csv")
    # A coluna tem typo: "Realease"
    coluna_release = 'Realease' if 'Realease' in dados[0] else 'Release'
    releases = [int(r[coluna_release]) for r in dados]

    q1, med, q3 = quartis(releases)
    print(f"  Repositórios analisados: {len(releases)}")
    if len(releases) < 100:
        print(f"  ⚠️  ATENÇÃO: releases.csv contém apenas {len(releases)} repositórios (incompleto)")
    print(f"  Mínimo:        {min(releases)}")
    print(f"  Q1:            {q1:.0f}")
    print(f"  Mediana:       {med:.0f}")
    print(f"  Q3:            {q3:.0f}")
    print(f"  Máximo:        {max(releases)}")

    # Contagem por faixa
    sem_release = sum(1 for r in releases if r == 0)
    com_release = len(releases) - sem_release
    print(f"  Sem releases:  {sem_release} ({100*sem_release/len(releases):.0f}%)")
    print(f"  Com releases:  {com_release} ({100*com_release/len(releases):.0f}%)")

    if HAS_MPL:
        fig, ax = plt.subplots()
        cor = '#8E44AD'
        ax.hist(releases, bins=max(5, len(set(releases))), color=cor,
                edgecolor='white', alpha=0.85)
        ax.axvline(med, color='#E74C3C', linestyle='--', linewidth=2,
                   label=f'Mediana = {med:.0f}')
        ax.set_xlabel('Número de Releases')
        ax.set_ylabel('Número de Repositórios')
        ax.set_title(f'RQ03 — Distribuição de Releases (n={len(releases)})')
        ax.legend()
        salvar_grafico(fig, 'rq03_releases.png')

    return med


# ──────────────────────────────────────────────────────────────────────
# RQ04 — Frequência de atualizações (issues/mês como proxy)
# ──────────────────────────────────────────────────────────────────────
def analisar_rq04():
    print("\n" + "=" * 60)
    print("RQ04 — Sistemas populares são atualizados com frequência?")
    print("=" * 60)

    dados = ler_csv("frequencia_issues.csv")
    frequencias_raw = [(r['Repositorio'], r['Frequencia issues']) for r in dados]

    # Parse para valores numéricos
    frequencias = []
    excluidos = 0
    for repo, val_str in frequencias_raw:
        val = parse_frequencia(val_str)
        if val is not None:
            frequencias.append(val)
        else:
            excluidos += 1

    q1, med, q3 = quartis(frequencias)
    print(f"  Repositórios analisados: {len(frequencias)} (excluídos {excluidos} sem issues)")
    print(f"  Mínimo:        {min(frequencias):.1f} issues/mês")
    print(f"  Q1:            {q1:.1f} issues/mês")
    print(f"  Mediana:       {med:.1f} issues/mês")
    print(f"  Q3:            {q3:.1f} issues/mês")
    print(f"  Máximo:        {max(frequencias):.1f} issues/mês")

    # Categorização
    categorias = Counter()
    for repo, val_str in frequencias_raw:
        val_str = val_str.strip()
        if "Sem issues" in val_str:
            categorias["Sem issues"] += 1
        elif "Múltiplas issues no mesmo dia" in val_str:
            categorias["Múltiplas/dia (>900/mês)"] += 1
        elif "300 issues/mês" in val_str:
            categorias["≥300 issues/mês"] += 1
        else:
            val = parse_frequencia(val_str)
            if val is not None:
                if val == 0:
                    categorias["0 issues/mês"] += 1
                elif val <= 10:
                    categorias["1–10 issues/mês"] += 1
                elif val <= 100:
                    categorias["11–100 issues/mês"] += 1
                elif val < 300:
                    categorias["101–299 issues/mês"] += 1

    print("\n  Distribuição por categoria:")
    for cat in ["Sem issues", "0 issues/mês", "1–10 issues/mês",
                "11–100 issues/mês", "101–299 issues/mês",
                "≥300 issues/mês", "Múltiplas/dia (>900/mês)"]:
        if cat in categorias:
            print(f"    {cat}: {categorias[cat]}")

    if HAS_MPL:
        fig, ax = plt.subplots()
        cor = '#E67E22'
        # Usar escala log para visualizar a distribuição muito assimétrica
        freq_plot = [max(f, 0.1) for f in frequencias]
        n_bins = 20
        ax.hist(freq_plot, bins=n_bins, color=cor, edgecolor='white', alpha=0.85)
        ax.axvline(med, color='#E74C3C', linestyle='--', linewidth=2,
                   label=f'Mediana = {med:.0f} issues/mês')
        ax.set_xscale('log')
        ax.set_xlabel('Frequência de Issues (issues/mês, escala log)')
        ax.set_ylabel('Número de Repositórios')
        ax.set_title('RQ04 — Distribuição da Frequência de Atualização (Issues/mês)')
        ax.legend()
        salvar_grafico(fig, 'rq04_frequencia_atualizacao.png')

    return med


# ──────────────────────────────────────────────────────────────────────
# RQ05 — Linguagens populares
# ──────────────────────────────────────────────────────────────────────
def analisar_rq05():
    print("\n" + "=" * 60)
    print("RQ05 — Sistemas populares são escritos nas linguagens mais populares?")
    print("=" * 60)

    dados = ler_csv("ranking_popularidade.csv")
    linguagens = []
    quantidades = []
    for r in dados:
        ling = r.get('Linguagens', '').strip()
        qtd_str = r.get('Quantidade de Repositorios', '0').strip()
        if ling and qtd_str:
            linguagens.append(ling)
            quantidades.append(int(qtd_str))

    total = sum(quantidades)
    print(f"  Total de linguagens distintas: {len(linguagens)}")
    print(f"  Distribuição:")
    for ling, qtd in zip(linguagens, quantidades):
        pct = 100 * qtd / total if total > 0 else 0
        print(f"    {ling}: {qtd} repos ({pct:.1f}%)")

    if HAS_MPL:
        fig, ax = plt.subplots(figsize=(14, 7))
        cores = plt.cm.Set3(range(len(linguagens)))
        bars = ax.barh(range(len(linguagens)), quantidades, color=cores,
                       edgecolor='white', height=0.7)
        ax.set_yticks(range(len(linguagens)))
        ax.set_yticklabels(linguagens)
        ax.invert_yaxis()
        ax.set_xlabel('Quantidade de Repositórios')
        ax.set_title('RQ05 — Ranking de Linguagens Primárias dos Repositórios Populares')

        # Adiciona valor nas barras
        for bar, qtd in zip(bars, quantidades):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(qtd), va='center', fontsize=10, fontweight='bold')

        salvar_grafico(fig, 'rq05_linguagens.png')

    return linguagens, quantidades


# ──────────────────────────────────────────────────────────────────────
# RQ06 — Percentual de issues fechadas
# ──────────────────────────────────────────────────────────────────────
def analisar_rq06():
    print("\n" + "=" * 60)
    print("RQ06 — Sistemas populares possuem alto percentual de issues fechadas?")
    print("=" * 60)

    dados = ler_csv("percentual_issues_fechadas.csv")
    percentuais = []
    sem_issues = 0
    for r in dados:
        val = r['Percentual de Issues Fechadas'].strip()
        if 'N/A' in val:
            sem_issues += 1
        else:
            percentuais.append(float(val))

    q1, med, q3 = quartis(percentuais)
    print(f"  Repositórios com issues: {len(percentuais)}")
    print(f"  Sem issues (N/A):       {sem_issues}")
    print(f"  Mínimo:        {min(percentuais):.2f}%")
    print(f"  Q1:            {q1:.2f}%")
    print(f"  Mediana:       {med:.2f}%")
    print(f"  Q3:            {q3:.2f}%")
    print(f"  Máximo:        {max(percentuais):.2f}%")

    # Faixas
    faixas = Counter()
    for p in percentuais:
        if p < 50:
            faixas["< 50%"] += 1
        elif p < 70:
            faixas["50–70%"] += 1
        elif p < 90:
            faixas["70–90%"] += 1
        else:
            faixas["≥ 90%"] += 1

    print("\n  Distribuição por faixa:")
    for faixa in ["< 50%", "50–70%", "70–90%", "≥ 90%"]:
        if faixa in faixas:
            print(f"    {faixa}: {faixas[faixa]} repos")

    if HAS_MPL:
        fig, ax = plt.subplots()
        cor = '#2980B9'
        ax.hist(percentuais, bins=20, color=cor, edgecolor='white', alpha=0.85)
        ax.axvline(med, color='#E74C3C', linestyle='--', linewidth=2,
                   label=f'Mediana = {med:.1f}%')
        ax.set_xlabel('Percentual de Issues Fechadas (%)')
        ax.set_ylabel('Número de Repositórios')
        ax.set_title('RQ06 — Distribuição do Percentual de Issues Fechadas')
        ax.legend()
        salvar_grafico(fig, 'rq06_issues_fechadas.png')

    return med


# ──────────────────────────────────────────────────────────────────────
# RQ07 — Bônus: métricas por linguagem
# ──────────────────────────────────────────────────────────────────────
def analisar_rq07():
    print("\n" + "=" * 60)
    print("RQ07 (Bônus) — Métricas agrupadas por linguagem")
    print("=" * 60)

    dados = ler_csv("bonus.csv")
    linguagens = []
    metricas = {
        'Media PRs': [],
        'Media Releases': [],
        'Media Dias Sem Atualizar': [],
        'Media Frequencia Issues': []
    }

    for r in dados:
        ling = r['Linguagem'].strip()
        if not ling:
            continue
        linguagens.append(ling)
        for chave in metricas:
            metricas[chave].append(float(r[chave]))

    print(f"  Linguagens: {len(linguagens)}")
    print(f"\n  {'Linguagem':<25} {'Média PRs':>10} {'Média Rel.':>12} {'Dias s/ Atualizar':>18} {'Freq Issues/mês':>16}")
    print("  " + "-" * 85)
    for i, ling in enumerate(linguagens):
        print(f"  {ling:<25} {metricas['Media PRs'][i]:>10.0f} "
              f"{metricas['Media Releases'][i]:>12.0f} "
              f"{metricas['Media Dias Sem Atualizar'][i]:>18.0f} "
              f"{metricas['Media Frequencia Issues'][i]:>16.2f}")

    if HAS_MPL:
        titulos = {
            'Media PRs': 'Média de Pull Requests Aceitas',
            'Media Releases': 'Média de Releases',
            'Media Dias Sem Atualizar': 'Média de Dias Sem Atualizar',
            'Media Frequencia Issues': 'Média de Frequência de Issues (issues/mês)'
        }

        cores_metricas = ['#3498DB', '#9B59B6', '#E67E22', '#1ABC9C']
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        for idx, (chave, titulo) in enumerate(titulos.items()):
            ax = axes[idx // 2][idx % 2]
            valores = metricas[chave]
            cor = cores_metricas[idx]

            bars = ax.barh(range(len(linguagens)), valores, color=cor,
                           edgecolor='white', alpha=0.85, height=0.65)
            ax.set_yticks(range(len(linguagens)))
            ax.set_yticklabels(linguagens, fontsize=9)
            ax.invert_yaxis()
            ax.set_title(titulo, fontsize=12, fontweight='bold')

            # Adiciona valor nas barras
            max_val = max(valores) if valores else 1
            for bar, val in zip(bars, valores):
                ax.text(bar.get_width() + max_val * 0.01,
                        bar.get_y() + bar.get_height() / 2,
                        f'{val:.0f}' if val == int(val) else f'{val:.1f}',
                        va='center', fontsize=8)

        fig.suptitle('RQ07 (Bônus) — Métricas por Linguagem Primária',
                     fontsize=16, fontweight='bold', y=1.01)
        salvar_grafico(fig, 'rq07_bonus_linguagens.png')


# ──────────────────────────────────────────────────────────────────────
# Execução principal
# ──────────────────────────────────────────────────────────────────────
def main():
    configurar_estilo()

    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Lab01 — Análise de Repositórios Populares do GitHub     ║")
    print("╚════════════════════════════════════════════════════════════╝")

    resultados = {}

    resultados['rq01_mediana'] = analisar_rq01()
    resultados['rq02_mediana'] = analisar_rq02()
    resultados['rq03_mediana'] = analisar_rq03()
    resultados['rq04_mediana'] = analisar_rq04()
    resultados['rq05'] = analisar_rq05()
    resultados['rq06_mediana'] = analisar_rq06()
    analisar_rq07()

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO — Valores Medianos")
    print("=" * 60)
    print(f"  RQ01 — Idade:              {resultados['rq01_mediana']:.1f} anos")
    print(f"  RQ02 — PRs aceitas:        {resultados['rq02_mediana']:.0f}")
    print(f"  RQ03 — Releases:           {resultados['rq03_mediana']:.0f}")
    print(f"  RQ04 — Freq. issues/mês:   {resultados['rq04_mediana']:.0f}")
    print(f"  RQ06 — % issues fechadas:  {resultados['rq06_mediana']:.1f}%")
    print()

    if HAS_MPL:
        print(f"✅ Gráficos salvos na pasta: {GRAFICOS_DIR}")
    else:
        print("⚠️  Gráficos não gerados (matplotlib não instalado)")
        print("   Instale com: pip install matplotlib")

    return resultados


if __name__ == "__main__":
    main()
