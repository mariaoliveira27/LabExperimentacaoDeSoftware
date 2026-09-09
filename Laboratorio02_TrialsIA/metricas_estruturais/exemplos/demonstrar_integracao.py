"""Demonstra o vínculo por trial_id sem coletar tempo ou executar exercícios."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


COMPONENTE = Path(__file__).resolve().parents[1]
TRIAL_ID = "DEMO-S01-AULUS-001"


def demonstrar(saida: Path) -> None:
    # Cada execução exige uma pasta nova, preservando demonstrações anteriores.
    saida.mkdir(parents=True, exist_ok=False)
    solucao = saida / "copia_final_demo.py"
    solucao.write_text(
        (COMPONENTE / "exemplos" / "programa_demo.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    metricas_json = saida / "metricas.json"
    subprocess.run([
        sys.executable, str(COMPONENTE / "src" / "coletar_metricas.py"),
        "--arquivo", str(solucao), "--trial-id", TRIAL_ID,
        "--saida", str(metricas_json),
    ], check=True)

    manifesto = {
        "demonstracao": True,
        "trial_id": TRIAL_ID,
        "solucao_final": str(solucao),
        "metricas_json": str(metricas_json),
        "tempo": {
            "trial_id": TRIAL_ID,
            "status": "nao_coletado",
            "csv": None,
            "sha256_csv": None,
            "linha_dados": None,
        },
        "testes": {
            "trial_id": TRIAL_ID,
            "status": "nao_executado",
            "resultado_json": None,
        },
    }
    manifesto_json = saida / "manifesto_demo.json"
    with manifesto_json.open("x", encoding="utf-8") as fluxo:
        json.dump(manifesto, fluxo, ensure_ascii=False, indent=2, allow_nan=False)
        fluxo.write("\n")

    # Este processo lê o JSON produzido pelo coletor em outro processo.
    registro = json.loads(metricas_json.read_text(encoding="utf-8"))
    vinculos = json.loads(manifesto_json.read_text(encoding="utf-8"))
    ids = {registro["trial_id"], vinculos["trial_id"],
           vinculos["tempo"]["trial_id"], vinculos["testes"]["trial_id"]}
    if ids != {TRIAL_ID} or registro["arquivo"] != str(solucao):
        raise ValueError("Identificador ou cópia final divergente na integração.")
    if registro["status_analise"] != "ok" or registro["complexidade_media"] != 2.0:
        raise ValueError("Resultado inesperado para o programa demonstrativo.")
    print(f"Integração demonstrativa validada: {TRIAL_ID}.")
    print(f"Manifesto: {manifesto_json}")
    print("Tempo não coletado; testes dos exercícios não executados.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True, help="Pasta nova para a demonstração.")
    args = parser.parse_args()
    try:
        demonstrar(args.saida)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Falha na demonstração: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
