"""Gera o dashboard portátil do Lab 02 a partir dos registros existentes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

try:
    from .dados import load_trials, build_view, records_for_json, select_trials
    from .graficos import COLORS, LABELS, chart_limits, configure_theme, render_charts
except ImportError:
    from dados import load_trials, build_view, records_for_json, select_trials
    from graficos import COLORS, LABELS, chart_limits, configure_theme, render_charts


HERE = Path(__file__).resolve().parent
PARTICIPANT_NAMES = {"aulus": "Áulus", "maria": "Maria", "vinicius": "Vinícius"}


def default_data_dir() -> Path:
    for candidate in (HERE.parent / "cronometro", HERE / "insumos" / "cronometro"):
        if (candidate / "registro_experimento.csv").is_file():
            return candidate
    return HERE.parent / "cronometro"


def generate(data_dir: str | Path | None = None, output_dir: str | Path | None = None) -> dict:
    data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
    output = Path(output_dir) if output_dir is not None else HERE / "public"
    frame = load_trials(data_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "data").mkdir(exist_ok=True)
    (output / "downloads").mkdir(exist_ok=True)
    participants = [{"value": "all", "label": "Todos"}] + [
        {"value": value, "label": PARTICIPANT_NAMES.get(value, value.title())}
        for value in sorted(frame["integrante"].unique())
    ]
    katas = [{"value": "all", "label": "Todas"}] + [
        {"value": value, "label": value} for value in sorted(frame["kata"].unique())
    ]
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "participants": participants,
        "katas": katas,
        "treatments": [{"value": treatment, "label": LABELS[treatment], "color": COLORS[treatment]}
                       for treatment in ("manual", "ia")],
        "rows": records_for_json(frame),
        "views": {},
    }
    configure_theme()
    limits = chart_limits(frame)
    total_views = len(participants) * len(katas)
    for index, (participant, kata) in enumerate(
        ((participant, kata) for participant in participants for kata in katas), 1
    ):
        key = f"{participant['value']}__{kata['value']}"
        selected = select_trials(frame, participant["value"], kata["value"])
        view = build_view(frame, participant["value"], kata["value"])
        subtitle = f"{participant['label']} · {kata['label']} · {len(selected)} trials registrados"
        if view["adjustment_count"]:
            subtitle += " · rótulos de Áulus ajustados"
        view["charts"] = render_charts(selected, output, key, subtitle, limits)
        csv_relative = Path("downloads") / f"{key}.csv"
        selected.to_csv(output / csv_relative, index=False, encoding="utf-8-sig", na_rep="")
        view["csv"] = csv_relative.as_posix()
        manifest["views"][key] = view
        print(f"[{index:02d}/{total_views}] {key}: {len(selected)} trials", flush=True)

    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (output / "data" / "manifest.json").write_text(manifest_text, encoding="utf-8")
    web_source = HERE / "web"
    if web_source.is_dir():
        for source in web_source.rglob("*"):
            if source.is_file():
                destination = output / source.relative_to(web_source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
    print(f"Dashboard gerado em {output.resolve()}", flush=True)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, default=None,
                        help="Diretório cronometro que contém registro_experimento.csv e resultados/.")
    parser.add_argument("--saida", type=Path, default=HERE / "public", help="Pasta de saída (padrão: public/).")
    args = parser.parse_args(argv)
    try:
        generate(args.dados, args.saida)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Erro ao gerar dashboard: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
