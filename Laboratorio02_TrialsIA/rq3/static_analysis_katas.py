# static_analysis_katas.py
"""Static analysis of kata solutions for RQ3.

- Finds all Python kata files for Maria, Aulus and Vinícius.
- Computes LOC, average cyclomatic complexity, maintainability index using `radon`.
- Computes overall code duplication percentage using `jscpd`.
- Writes a CSV report `rq3_static_metrics.csv` and a markdown summary
  `rq3_static_metrics_summary.md`.
"""

import os
import json
import csv
import subprocess
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path.cwd()  # repository root (assumes script is run from workspace root)
KATA_DIR = BASE_DIR / "Laboratorio02_TrialsIA" / "solucoes_das_Katas"

PARTICIPANTS = ["maria", "aulus", "vinicius"]

CSV_PATH = BASE_DIR / "rq3_static_metrics.csv"
MD_PATH = BASE_DIR / "rq3_static_metrics_summary.md"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess.
    If the command is a known Python module (radon or jscpd) we invoke it via
    the current interpreter to avoid missing executable issues.
    """
    # Prefix with "python -m" when calling radon or jscpd as a module
    if cmd and cmd[0] in {"radon", "jscpd"}:
        cmd = [sys.executable, "-m", cmd[0]] + cmd[1:]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        print(result.stderr)
    return result

def radon_raw(file_path: Path) -> int:
    """Return total LOC for a file using `radon raw -j`.
    The JSON output maps file path strings to a dict with a `loc` field.
    """
    result = run_cmd(["radon", "raw", "-j", str(file_path)])
    if result.returncode != 0:
        return 0
    data = json.loads(result.stdout)
    return data.get(str(file_path), {}).get("loc", 0)

def radon_cc(file_path: Path) -> tuple[float, int]:
    """Return (average_cc, max_cc) for a file using `radon cc -a -j`.
    The JSON output is a list of dicts, each with a `complexity` field.
    """
    result = run_cmd(["radon", "cc", "-a", "-j", str(file_path)])
    if result.returncode != 0:
        return (0, 0)
    entries = json.loads(result.stdout).get(str(file_path), [])
    complexities = [entry.get("complexity", 0) for entry in entries]
    if not complexities:
        return (0, 0)
    avg_cc = round(sum(complexities) / len(complexities), 2)
    max_cc = max(complexities)
    return (avg_cc, max_cc)

def radon_mi(file_path: Path) -> float:
    """Return the Maintainability Index for a file using `radon mi -j`.
    The JSON output maps file path to a dict with an `mi` or `MI` field.
    """
    result = run_cmd(["radon", "mi", "-j", str(file_path)])
    if result.returncode != 0:
        return 0.0
    data = json.loads(result.stdout).get(str(file_path), {})
    return data.get("mi") or data.get("MI") or 0.0

def compute_duplication(kata_files: list[Path]) -> float:
    """Compute overall code duplication percentage across provided kata files.
    This simple heuristic counts how many lines appear more than once across all files.
    Duplication % = (duplicate lines) / (total lines) * 100.
    """
    from collections import Counter
    total_lines = 0
    line_counter = Counter()
    for file_path in kata_files:
        try:
            lines = [line.rstrip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
            continue
        total_lines += len(lines)
        line_counter.update(lines)
    if total_lines == 0:
        return 0.0
    duplicate_lines = sum(count - 1 for count in line_counter.values() if count > 1)
    return (duplicate_lines / total_lines) * 100.0

# ---------------------------------------------------------------------------
# Main analysis flow
# ---------------------------------------------------------------------------

def main():
    # 1. Collect kata files for the three participants
    kata_files = []
    for participant in PARTICIPANTS:
        pattern = f"*{participant}*.py"
        kata_files.extend(KATA_DIR.rglob(pattern))
    # Inclui as soluções de IA geradas por Vinícius via Gemini (Issue #39)
    for arq in sorted(KATA_DIR.rglob("*gemini*.py")):
        if arq not in kata_files:
            kata_files.append(arq)

    # 2. Compute per‑file metrics
    rows = []
    for file_path in kata_files:
        name_lower = file_path.name.lower()
        if "gemini" in name_lower:
            author = "Vinicius"
        else:
            author = next((p for p in PARTICIPANTS if p in name_lower), "unknown")
        loc = radon_raw(file_path)
        avg_cc, max_cc = radon_cc(file_path)
        mi = radon_mi(file_path)
        rows.append({
            "file_path": str(file_path.relative_to(BASE_DIR)),
            "author": author.title() if isinstance(author, str) else str(author),
            "loc": loc,
            "avg_cc": avg_cc,
            "max_cc": max_cc,
            "maintainability_index": mi,
        })

    # 3. Compute code duplication across all kata files
    duplication_percent = compute_duplication(kata_files)
    for row in rows:
        row["duplication_percent"] = duplication_percent

    # 4. Write CSV report
    csv_headers = [
        "file_path",
        "author",
        "loc",
        "avg_cc",
        "max_cc",
        "maintainability_index",
        "duplication_percent",
    ]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV report written to {CSV_PATH}")

    # 5. Write markdown summary (top 5 most complex files by max_cc)
    top_complex = sorted(rows, key=lambda r: r["max_cc"], reverse=True)[:5]
    md_lines = [
        "# RQ3 Static Metrics Summary",
        "",
        f"**Overall code duplication:** {duplication_percent:.2f}%",
        "",
        "## Top 5 most complex kata files (by max cyclomatic complexity)",
        "| File | Author | LOC | Avg CC | Max CC | Maintainability Index |",
        "|---|---|---|---|---|---|",
    ]
    for r in top_complex:
        md_lines.append(
            f"| {r['file_path']} | {r['author']} | {r['loc']} | {r['avg_cc']} | {r['max_cc']} | {r['maintainability_index']} |"
        )
    with open(MD_PATH, "w", encoding="utf-8") as mdfile:
        mdfile.write("\n".join(md_lines))
    print(f"Markdown summary written to {MD_PATH}")

if __name__ == "__main__":
    main()
