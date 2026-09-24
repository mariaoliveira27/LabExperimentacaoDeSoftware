"""Gráficos descritivos, com versões próprias para tela, celular e download."""

from __future__ import annotations

import hashlib
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator
import pandas as pd
import seaborn as sns

try:
    from .dados import TREATMENTS
except ImportError:
    from dados import TREATMENTS

COLORS = {"manual": "#1677c8", "ia": "#0f9f8c"}
LABELS = {"manual": "Manual", "ia": "Com IA"}
INK = "#18354d"
MUTED = "#61778a"


def configure_theme() -> None:
    sns.set_theme(style="whitegrid", font="DejaVu Sans")
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": "#dce6ee", "axes.labelcolor": MUTED,
        "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "grid.color": "#e9eff4", "grid.linewidth": .8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "svg.fonttype": "none", "svg.hashsalt": "lab02-dashboard-v2",
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial", "sans-serif"],
        "font.size": 11, "axes.labelsize": 11,
    })


def _number(value, digits=2):
    return f"{value:.{digits}f}".rstrip("0").rstrip(".").replace(".", ",") if digits else f"{value:.0f}"


def _offset(trial_id):
    fraction = int(hashlib.sha256(trial_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return (fraction - .5) * .16


def _figure(title, subtitle, note, mode, kind="distribution", count=6):
    mobile = mode == "mobile"
    export = mode == "export"
    width = 4.4 if mobile else 10
    body_height = (max(2.6, count * .91 + .6) if kind == "success"
                   else 3.6 if kind == "scatter" else 2.65)
    height = body_height + (2.05 if export else .65)
    figure, axis = plt.subplots(figsize=(width, height), dpi=120)
    if kind == "scatter":
        left, right = (.18, .94) if mobile else (.085, .97)
    else:
        left, right = (.24, .75) if mobile else (.15, .84)
    figure.subplots_adjust(left=left, right=right,
                           bottom=(1.18 if export else .65) / height,
                           top=1 - (1.05 if export else .33) / height)
    if export:
        figure.text(.045, 1 - .2 / height, title, va="top", fontsize=18, weight="bold")
        figure.text(.045, 1 - .59 / height, subtitle, va="top", fontsize=10, color=MUTED)
        wrapped = "\n".join(textwrap.fill(line, 132) for line in note.splitlines())
        figure.text(.045, .10 / height, wrapped, va="bottom", fontsize=8.7, color=MUTED)
    axis.set_axisbelow(True)
    axis.grid(axis="y", visible=False)
    axis.tick_params(axis="both", length=0, pad=8, labelsize=10 if mobile else 11)
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: _number(value)))
    return figure, axis


def _distribution(frame, column, title, unit, subtitle, note, xmax, mode):
    figure, axis = _figure(title, subtitle, note, mode)
    mobile = mode == "mobile"
    for position, treatment in enumerate(TREATMENTS):
        registered = frame.loc[frame["tratamento"].eq(treatment)]
        group = registered.dropna(subset=[column])
        color = COLORS[treatment]
        axis.axhspan(position - .40, position + .42, color=color, alpha=.035, linewidth=0)
        axis.text(-.06, position - .10, LABELS[treatment], transform=axis.get_yaxis_transform(),
                  ha="right", va="center", color=color, weight="bold", fontsize=10 if mobile else 12)
        axis.text(-.06, position + .13, f"n = {len(group)}", transform=axis.get_yaxis_transform(),
                  ha="right", va="center", color=MUTED, fontsize=9 if mobile else 10)
        if group.empty:
            message = "Sem observações" if registered.empty else "Não disponível"
            axis.text(.5, position, message, transform=axis.get_yaxis_transform(),
                      ha="center", va="center", color=MUTED, fontsize=9 if mobile else 12,
                      bbox={"facecolor": "white", "edgecolor": "none", "pad": 4})
            continue
        values = group[column].astype(float)
        if len(group) >= 3:
            axis.boxplot([values.to_numpy()], positions=[position - .11], widths=.23,
                         orientation="horizontal", patch_artist=True, showfliers=False,
                         manage_ticks=False,
                         boxprops={"facecolor": color, "alpha": .22, "edgecolor": color, "linewidth": 1.5},
                         whiskerprops={"color": color, "linewidth": 1.4},
                         capprops={"color": color, "linewidth": 1.4},
                         medianprops={"color": color, "linewidth": 2.5})
        for row in group.to_dict(orient="records"):
            marker = "^" if column == "tempo_min" and row["tempo_censurado"] else "o"
            axis.scatter(row[column], position + .19 + _offset(row["trial_id"]), s=48 if mobile else 62,
                         color=color, marker=marker, edgecolors="white", linewidths=1,
                         zorder=4, clip_on=False)
        axis.text(1.05, position - .08, _number(values.median()), transform=axis.get_yaxis_transform(),
                  va="center", color=color, fontsize=17 if mobile else 23, weight="bold")
        axis.text(1.05, position + .18, unit, transform=axis.get_yaxis_transform(),
                  va="center", color=MUTED, fontsize=9 if mobile else 10)
    axis.text(1.05, 1.035, "MEDIANA", transform=axis.transAxes, fontsize=7.5 if mobile else 9,
              color=MUTED, weight="bold")
    axis.set_ylim(1.55, -.5)
    axis.set_xlim(0, xmax)
    axis.set_yticks([])
    axis.xaxis.set_major_locator(MaxNLocator(nbins=3 if mobile else 6, min_n_ticks=3))
    axis.set_xlabel(unit, labelpad=9)
    return figure


def _success(frame, subtitle, mode):
    katas = sorted(frame["kata"].unique())
    note = ("Barras: média dos percentuais, com peso igual por rodada. Pontos: rodadas; n: tamanho da amostra.\n"
            "Losango vazado: taxa informada no CSV, sem relatório de testes arquivado.")
    figure, axis = _figure("Aprovação nos testes por kata", subtitle, note, mode, "success", len(katas))
    mobile = mode == "mobile"
    for index, kata in enumerate(katas):
        center = index * 1.5
        if index % 2 == 0:
            axis.axhspan(center - .63, center + .63, color="#f5f8fb", linewidth=0)
        axis.text(-.11, center - .51, kata, transform=axis.get_yaxis_transform(),
                  va="center", ha="right", weight="bold", fontsize=11)
        for j, treatment in enumerate(TREATMENTS):
            y = center + (-.22 if j == 0 else .27)
            group = frame.loc[frame["tratamento"].eq(treatment) & frame["kata"].eq(kata)]
            color = COLORS[treatment]
            axis.text(-.05, y, LABELS[treatment], transform=axis.get_yaxis_transform(),
                      va="center", ha="right", color=color, fontsize=10)
            if group.empty:
                axis.text(3, y, "Sem observações", va="center", color=MUTED, fontsize=9 if mobile else 10)
                continue
            mean = group["taxa_sucesso"].mean()
            axis.barh(y, 100, height=.25, color="#eaf0f5", zorder=1)
            axis.barh(y, mean, height=.25, color=color, alpha=.75, zorder=2)
            for row in group.to_dict(orient="records"):
                declared = row["fonte_testes"] == "csv"
                axis.scatter(row["taxa_sucesso"], y + _offset(row["trial_id"]),
                             marker="D" if declared else "o", s=40 if mobile else 50,
                             facecolors="white" if declared else color,
                             edgecolors=color if declared else "white", linewidths=1.3,
                             zorder=4, clip_on=False)
            axis.text(1.055, y - .035, f"{_number(mean, 1)}%", transform=axis.get_yaxis_transform(),
                      va="center", color=color, weight="bold", fontsize=11 if mobile else 13)
            axis.text(1.055, y + .17, f"n = {len(group)}", transform=axis.get_yaxis_transform(),
                      va="center", color=MUTED, fontsize=9)
    axis.set_xlim(0, 100)
    axis.set_ylim(max(.75, (len(katas) - 1) * 1.5 + .75), -.8)
    axis.set_yticks([])
    ticks = [0, 50, 100] if mobile else [0, 25, 50, 75, 100]
    axis.set_xticks(ticks, [f"{tick}%" for tick in ticks])
    axis.set_xlabel("Testes aprovados", labelpad=10)
    return figure


def _relationship(frame, subtitle, limits, mode):
    note = ("Cada ponto representa uma solução com métricas arquivadas. Círculos: Manual; losangos: Com IA.\n"
            "LOC contextualiza a complexidade; a visualização é descritiva e não estabelece causalidade.")
    figure, axis = _figure("Tamanho e complexidade do código", subtitle, note, mode, "scatter")
    mobile = mode == "mobile"
    handles = []
    for treatment in TREATMENTS:
        group = frame.loc[frame["tratamento"].eq(treatment)].dropna(subset=["loc", "complexidade_media"])
        marker = "o" if treatment == "manual" else "D"
        axis.scatter(group["loc"], group["complexidade_media"], s=70 if mobile else 100,
                     color=COLORS[treatment], marker=marker, alpha=.85,
                     edgecolors="white", linewidths=1.2, zorder=3)
        if len(frame) <= 2:
            # Annotate coincident coordinates once, preserving their actual position.
            for (loc, cc), rows in group.groupby(["loc", "complexidade_media"]):
                axis.annotate(" / ".join(rows["kata"]), (loc, cc), xytext=(7, 8 if treatment == "manual" else -16),
                              textcoords="offset points", color=COLORS[treatment], fontsize=8)
        label = f"{LABELS[treatment]} · n={len(group)}"
        handles.append(Line2D([], [], color=COLORS[treatment], marker=marker,
                              linestyle="", markersize=7, label=label))
    if frame.dropna(subset=["loc", "complexidade_media"]).empty:
        axis.text(.5, .5, "Métricas não disponíveis\nneste recorte", transform=axis.transAxes,
                  ha="center", va="center", color=MUTED, fontsize=11,
                  bbox={"facecolor": "white", "edgecolor": "none", "pad": 9})
    axis.grid(axis="y", visible=True)
    axis.set_xlim(0, limits["loc"])
    axis.set_ylim(0, limits["complexidade"])
    axis.xaxis.set_major_locator(MaxNLocator(nbins=4 if mobile else 7))
    axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: _number(value)))
    axis.set_xlabel("Linhas de código (LOC)", labelpad=10)
    axis.set_ylabel("Complexidade média", labelpad=9)
    axis.legend(handles=handles, loc="lower left", bbox_to_anchor=(-.02, 1.01), ncol=2,
                frameon=False, fontsize=8.5 if mobile else 10, handletextpad=.4, columnspacing=1.3)
    return figure


def chart_limits(frame: pd.DataFrame) -> dict:
    def maximum(column, step):
        values = frame[column].dropna()
        return max(step, math.ceil(float(values.max()) * 1.1 / step) * step) if len(values) else step
    return {"tempo": maximum("tempo_min", 5), "complexidade": maximum("complexidade_media", 1),
            "loc": maximum("loc", 20)}


def render_charts(frame: pd.DataFrame, output: Path, key: str, subtitle: str, limits: dict) -> dict:
    relative = Path("charts") / key
    directory = output / relative
    directory.mkdir(parents=True, exist_ok=True)
    specifications = {
        "tempo": ("tempo_min", "Tempo registrado por tratamento", "minutos",
                  "Origem da medição não confirmada; não representa tempo validado até aprovação. Triângulo: censura."),
        "complexidade": ("complexidade_media", "Complexidade ciclomática média", "CC média",
                         "Calculada sobre os artefatos disponíveis; ausência de relatório não equivale a zero."),
        "loc": ("loc", "Tamanho do código por tratamento", "linhas",
                "LOC inclui comentários e linhas vazias; funciona como medida de controle da complexidade."),
    }
    charts = {}
    for name in ("tempo", "sucesso", "complexidade", "loc", "relacao"):
        charts[name] = {}
        for mode in ("export", "display", "mobile"):
            if name in specifications:
                column, title, unit, extra = specifications[name]
                note = "Caixa: Q1–Q3; linha: mediana; hastes: até 1,5×IQR. Pontos: rodadas. n < 3: somente pontos.\n" + extra
                figure = _distribution(frame, column, title, unit, subtitle, note, limits[name], mode)
            elif name == "sucesso":
                figure = _success(frame, subtitle, mode)
            else:
                figure = _relationship(frame, subtitle, limits, mode)
            for extension in (("svg", "png") if mode == "export" else ("svg",)):
                suffix = "" if mode == "export" else f"-{mode}"
                target = directory / f"{name}{suffix}.{extension}"
                metadata = {"Date": None} if extension == "svg" else {"Software": "Lab 02 / Matplotlib"}
                figure.savefig(target, dpi=180, facecolor="white", metadata=metadata)
                charts[name][extension if mode == "export" else mode] = (relative / target.name).as_posix()
            plt.close(figure)
    return charts
