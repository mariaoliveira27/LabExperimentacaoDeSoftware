"""Gera os gráficos das RQs usando os CSVs da amostra de 1.000 repositórios."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "CSV - 1000"
OUTPUT_DIR = BASE_DIR / "Graficos -1000"
NOW = datetime.now(timezone.utc)

COLORS = {
    "blue": "#1677C8",
    "blue-dark": "#075B9A",
    "teal": "#0F9F8C",
    "violet": "#7357D8",
    "amber": "#E58A23",
    "coral": "#DB6B5A",
    "muted": "#7B93AA",
    "line": "#DCE6EE",
}


def read_csv(filename: str) -> list[dict[str, str]]:
    with (CSV_DIR / filename).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_figure(figure: plt.Figure, filename: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / filename, dpi=160, bbox_inches="tight")
    plt.close(figure)
    print(f"Gerado: Graficos -1000/{filename}")


def setup_axis(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(COLORS["line"])
    axis.grid(axis="y", color=COLORS["line"], linewidth=0.8, alpha=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(colors="#486581")


def repository_age_years(created_at: str) -> float:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (NOW - created).days / 365.25


def parse_frequency(value: str) -> float | None:
    normalized = value.strip().lower()
    if "sem issues" in normalized:
        return None
    if "múltiplas issues" in normalized:
        return 900.0
    if "apenas 1 issue" in normalized:
        return 0.1
    try:
        return float(normalized.split()[0])
    except (ValueError, IndexError):
        return None


def frequency_category(value: str) -> str:
    normalized = value.strip().lower()
    if "sem issues" in normalized:
        return "Sem issues"
    if "múltiplas issues" in normalized:
        return "Múltiplas/dia"
    frequency = parse_frequency(value)
    if frequency is None:
        return "Sem dados"
    if frequency == 0:
        return "0/mês"
    if frequency <= 10:
        return "1–10/mês"
    if frequency <= 100:
        return "11–100/mês"
    if frequency < 300:
        return "101–299/mês"
    return "≥300/mês"


def graph_rq01() -> None:
    rows = read_csv("repositorios_populares.csv")
    ages = [repository_age_years(row["Criado Em"]) for row in rows]
    med = median(ages)

    figure, axis = plt.subplots(figsize=(11, 6))
    axis.hist(ages, bins=20, color=COLORS["blue"], edgecolor="white", alpha=0.9)
    axis.axvline(med, color=COLORS["coral"], linestyle="--", linewidth=2, label=f"Mediana: {med:.1f} anos")
    axis.set_title("RQ01 — Distribuição da idade dos repositórios populares", fontweight="bold", pad=14)
    axis.set_xlabel("Idade do repositório (anos)")
    axis.set_ylabel("Quantidade de repositórios")
    axis.legend(frameon=False)
    setup_axis(axis)
    save_figure(figure, "rq01_idade_repositorios.png")


def graph_rq02() -> None:
    rows = read_csv("pull_requests_aceitas.csv")
    pull_requests = [int(row["Pull Requests Aceitas"]) for row in rows]
    med = median(pull_requests)
    values_for_log = [max(value, 1) for value in pull_requests]

    figure, axis = plt.subplots(figsize=(11, 6))
    axis.hist(values_for_log, bins=24, color=COLORS["teal"], edgecolor="white", alpha=0.9)
    axis.set_xscale("log")
    axis.axvline(max(med, 1), color=COLORS["coral"], linestyle="--", linewidth=2, label=f"Mediana: {med:,.0f} PRs")
    axis.set_title("RQ02 — Pull requests aceitas (escala logarítmica)", fontweight="bold", pad=14)
    axis.set_xlabel("Pull requests aceitas")
    axis.set_ylabel("Quantidade de repositórios")
    axis.legend(frameon=False)
    setup_axis(axis)
    save_figure(figure, "rq02_pull_requests.png")


def graph_rq03() -> None:
    rows = read_csv("release.csv")
    tags = [int(row["Tags"]) for row in rows]
    ranges = [
        ("0", lambda value: value == 0),
        ("1–5", lambda value: 1 <= value <= 5),
        ("6–25", lambda value: 6 <= value <= 25),
        ("26–100", lambda value: 26 <= value <= 100),
        ("101–500", lambda value: 101 <= value <= 500),
        ("+500", lambda value: value > 500),
    ]
    labels = [label for label, _ in ranges]
    counts = [sum(predicate(value) for value in tags) for _, predicate in ranges]

    figure, axis = plt.subplots(figsize=(11, 6))
    bars = axis.bar(labels, counts, color=COLORS["violet"], width=0.62)
    axis.bar_label(bars, padding=4, fontweight="bold", color="#486581")
    axis.set_title("RQ03 — Distribuição de tags por repositório", fontweight="bold", pad=14)
    axis.set_xlabel("Quantidade de tags")
    axis.set_ylabel("Quantidade de repositórios")
    setup_axis(axis)
    save_figure(figure, "rq03_releases.png")


def graph_rq04() -> None:
    rows = read_csv("frequencia_issues.csv")
    order = ["Sem issues", "0/mês", "1–10/mês", "11–100/mês", "101–299/mês", "≥300/mês", "Múltiplas/dia"]
    counts = Counter(frequency_category(row["Frequencia issues"]) for row in rows)
    values = [counts[label] for label in order]

    figure, axis = plt.subplots(figsize=(11, 6))
    bars = axis.barh(order, values, color=COLORS["amber"])
    axis.bar_label(bars, padding=5, fontweight="bold", color="#486581")
    axis.invert_yaxis()
    axis.set_title("RQ04 — Atividade de issues por repositório", fontweight="bold", pad=14)
    axis.set_xlabel("Quantidade de repositórios")
    axis.set_ylabel("")
    setup_axis(axis)
    axis.grid(axis="x", color=COLORS["line"], linewidth=0.8, alpha=0.8)
    axis.grid(axis="y", visible=False)
    save_figure(figure, "rq04_frequencia_atualizacao.png")


def graph_rq05() -> None:
    rows = read_csv("ranking_popularidade.csv")
    ranking = sorted(
        ((row["Linguagens"], int(row["Quantidade de Repositorios"])) for row in rows),
        key=lambda item: item[1],
        reverse=True,
    )[:15]
    labels = [language for language, _ in ranking][::-1]
    values = [count for _, count in ranking][::-1]

    figure, axis = plt.subplots(figsize=(11, 7))
    bars = axis.barh(labels, values, color=COLORS["blue"])
    axis.bar_label(bars, padding=4, fontweight="bold", color="#486581")
    axis.set_title("RQ05 — Top 15 linguagens primárias", fontweight="bold", pad=14)
    axis.set_xlabel("Quantidade de repositórios")
    axis.set_ylabel("")
    setup_axis(axis)
    axis.grid(axis="x", color=COLORS["line"], linewidth=0.8, alpha=0.8)
    axis.grid(axis="y", visible=False)
    save_figure(figure, "rq05_linguagens.png")


def graph_rq06() -> None:
    rows = read_csv("percentual_issues_fechadas.csv")
    percentages = []
    for row in rows:
        try:
            percentages.append(float(row["Percentual de Issues Fechadas"]))
        except ValueError:
            continue
    med = median(percentages)
    without_issues = len(rows) - len(percentages)

    figure, axis = plt.subplots(figsize=(11, 6))
    axis.hist(percentages, bins=20, range=(0, 100), color=COLORS["coral"], edgecolor="white", alpha=0.9)
    axis.axvline(med, color=COLORS["blue-dark"], linestyle="--", linewidth=2, label=f"Mediana: {med:.1f}%")
    axis.set_title("RQ06 — Percentual de issues fechadas", fontweight="bold", pad=14)
    axis.set_xlabel("Issues fechadas (%)")
    axis.set_ylabel("Quantidade de repositórios")
    axis.text(0.99, 0.95, f"{without_issues} repositórios sem issues", transform=axis.transAxes, ha="right", va="top", color=COLORS["muted"], fontsize=9)
    axis.legend(frameon=False)
    setup_axis(axis)
    save_figure(figure, "rq06_issues_fechadas.png")


def graph_rq07() -> None:
    rows = [row for row in read_csv("bonus.csv") if int(row["Total de Repositorios"]) >= 10]
    metrics = [
        ("Media PRs", "Média de PRs aceitas", COLORS["blue"], True),
        ("Media Releases", "Média de releases", COLORS["violet"], True),
        ("Media Dias Sem Atualizar", "Média de dias sem atualizar", COLORS["coral"], False),
        ("Media Frequencia Issues", "Média de issues/mês", COLORS["teal"], True),
    ]
    figure, axes = plt.subplots(2, 2, figsize=(15, 10))

    for axis, (field, title, color, descending) in zip(axes.flat, metrics):
        ranked = sorted(rows, key=lambda row: float(row[field]), reverse=descending)[:10]
        labels = [f"{row['Linguagem']} (n={row['Total de Repositorios']})" for row in ranked][::-1]
        values = [float(row[field]) for row in ranked][::-1]
        bars = axis.barh(labels, values, color=color)
        axis.bar_label(bars, padding=3, labels=[f"{value:,.0f}" if value >= 100 else f"{value:.1f}" for value in values], fontsize=8, color="#486581")
        axis.set_title(title, fontweight="bold", fontsize=11)
        axis.set_ylabel("")
        setup_axis(axis)
        axis.grid(axis="x", color=COLORS["line"], linewidth=0.8, alpha=0.8)
        axis.grid(axis="y", visible=False)

    figure.suptitle("RQ07 — Atividade média por linguagem (grupos com n ≥ 10)", fontweight="bold", fontsize=15, y=1.01)
    save_figure(figure, "rq07_bonus_linguagens.png")


def main() -> None:
    graph_rq01()
    graph_rq02()
    graph_rq03()
    graph_rq04()
    graph_rq05()
    graph_rq06()
    graph_rq07()
    print("\nConcluído: 7 gráficos gerados a partir de CSV - 1000.")


if __name__ == "__main__":
    main()
