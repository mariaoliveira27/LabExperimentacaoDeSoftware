"""Prepara uma cópia independente e reproduzível para o repositório do Sites."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from dados import REQUIRED_COLUMNS, load_trials


ROOT = Path(__file__).resolve().parent


def export_source(output: Path, data_dir: Path) -> None:
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        raise ValueError("A saída precisa ser uma pasta independente do código-fonte.")
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / ".local"):
        raise ValueError("Dentro do dashboard, use .local/ para evitar copiar a saída para si mesma.")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use uma pasta de saída nova ou vazia; nenhum arquivo será removido.")
    if not (ROOT / "public" / "index.html").is_file():
        raise ValueError("Gere o dashboard antes de exportar.")
    frame = load_trials(data_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("dados.py", "graficos.py", "gerar_dashboard.py", "exportar_sites.py", "requirements.txt", "README.md", ".gitignore"):
        shutil.copy2(ROOT / name, output / name)
    for name in ("web", "public", "tests"):
        shutil.copytree(ROOT / name, output / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    config = ROOT / ".openai" / "hosting.json"
    if config.is_file():
        (output / ".openai").mkdir()
        shutil.copy2(config, output / ".openai" / "hosting.json")
        # Sites aceita dist como diretório estático; public permanece a saída
        # local reproduzível e usada pelos testes da fonte independente.
        hosting = json.loads(config.read_text(encoding="utf-8"))
        static_directory = hosting.get("static", {}).get("directory")
        if static_directory != "dist":
            raise ValueError("A exportação do Sites exige static.directory='dist'.")
        shutil.copytree(ROOT / "public", output / "dist")

    # Snapshot mínimo dos insumos: mantém os valores necessários à reprodução,
    # sem caminhos de máquinas pessoais nem código executável das soluções.
    target_data = output / "insumos" / "cronometro"
    target_data.mkdir(parents=True)
    with (data_dir / "registro_experimento.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with (target_data / "registro_experimento.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    for trial_id in frame["trial_id"]:
        for filename in ("testes.json", "metricas.json"):
            source = data_dir / "resultados" / trial_id / filename
            if not source.is_file():
                continue
            document = json.loads(source.read_text(encoding="utf-8-sig"))
            if filename == "testes.json":
                original = document.get("resultado", {})
                result = {key: original[key] for key in ("total_casos", "aprovados", "reprovados", "taxa_sucesso", "passou_todos") if key in original}
                portable = {"trial_id": document["trial_id"], "resultado": result}
            else:
                keys = ("schema_version", "trial_id", "status_analise", "erro", "quantidade_funcoes", "complexidade_media", "loc", "sloc", "funcoes")
                portable = {key: document[key] for key in keys if key in document}
            target = target_data / "resultados" / trial_id / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(portable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fonte independente exportada para {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True, help="Pasta nova ou vazia para a fonte independente.")
    default_data = ROOT.parent / "cronometro"
    if not default_data.is_dir():
        default_data = ROOT / "insumos" / "cronometro"
    parser.add_argument("--dados", type=Path, default=default_data)
    args = parser.parse_args()
    export_source(args.saida, args.dados.resolve())


if __name__ == "__main__":
    main()
