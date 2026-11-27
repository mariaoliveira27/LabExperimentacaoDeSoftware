#!/usr/bin/env python3
"""Refaz tudo a partir dos JSONs brutos da fase full, com um comando:

    .venv/Scripts/python analysis/run_all.py      (Linux/macOS: .venv/bin/python analysis/run_all.py)

1. node scripts/extract-metrics.mjs --phase full   -> data/processed/full*.csv
2. node scripts/validate-data.mjs --phase full     -> docs/data-validation.md, data/processed/full_outliers.csv
3. analysis/analyze.py                             -> analysis/output/, analysis/figures/
4. analysis/impact.py                              -> analysis/output/impact.csv (docs/impacto.md)

Não roda o Lighthouse. A validação com erro (ex.: coleta incompleta) não interrompe a análise, mas
o aviso aparece no fim.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def step(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> None:
    if step(["node", "scripts/extract-metrics.mjs", "--phase", "full"]) != 0:
        sys.exit("a extração falhou")
    validation = step(["node", "scripts/validate-data.mjs", "--phase", "full"])
    if step([sys.executable, "analysis/analyze.py", *sys.argv[1:]]) != 0:
        sys.exit("a análise falhou")
    # impact estimate for docs/impacto.md (reads full.csv and data/usage.json)
    if step([sys.executable, "analysis/impact.py"]) != 0:
        sys.exit("a estimativa de impacto falhou")
    if validation != 0:
        print("\nAVISO: a validação encontrou erros; veja docs/data-validation.md antes de usar os resultados.")


if __name__ == "__main__":
    main()
