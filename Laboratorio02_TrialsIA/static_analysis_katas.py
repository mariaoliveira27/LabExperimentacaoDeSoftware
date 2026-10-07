"""Static analysis of kata solutions for RQ3.

- Finds all Python kata files for Maria, Aulus and Vinícius.
- Computes LOC, average cyclomatic complexity, maintainability index using `radon`.
- Computes code duplication percentage per file.
- Writes a CSV report `rq3_static_metrics.csv` and a markdown summary
  `rq3_static_metrics_summary.md`.
"""

from collections import Counter
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path.cwd()  # repository root
KATA_DIR = BASE_DIR / "Laboratorio02_TrialsIA" / "solucoes_das_Katas"

PARTICIPANTS = ["maria", "aulus", "vinicius"]

CSV_PATH = BASE_DIR / "rq3_static_metrics.csv"
MD_PATH = BASE_DIR / "rq3_static_metrics_summary.md"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess."""
    if cmd and cmd[0] in {"radon", "jscpd"}:
        cmd = [sys.executable, "-m", cmd[0]] + cmd[1:]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        print(result.stderr)
    return result


def radon_raw(file_path: Path) -> int:
    """Return total LOC for a file using `radon raw -j`."""
    result = run_cmd(["radon", "raw", "-j", str(file_path)])
    if result.returncode != 0:
        return 0
    data = json.loads(result.stdout)
    return data.get(str(file_path), {}).get("loc", 0)


def radon_cc(file_path: Path) -> tuple[float, int]:
    """Return (average_cc, max_cc) for a file using `radon cc -a -j`."""
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
    """Return the Maintainability Index for a file using `radon mi -j`."""
    result = run_cmd(["radon", "mi", "-j", str(file_path)])
    if result.returncode != 0:
        return 0.0
    data = json.loads(result.stdout).get(str(file_path), {})
    return data.get("mi") or data.get("MI") or 0.0


def compute_file_duplication(file_path: Path) -> float:
    """Compute internal code duplication percentage for a single file.

    Calculates the proportion of repeated lines within the specific file.
    """
    try:
        lines = [
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return 0.0

    total_lines = len(lines)
    if total_lines == 0:
        return 0.0

    line_counter = Counter(lines)
    duplicate_lines = sum(
        count - 1 for count in line_counter.values() if count > 1
    )
    return (duplicate_lines / total_lines) * 100.0


# ---------------------------------------------------------------------------
# Main analysis flow
# ---------------------------------------------------------------------------


def main():
    # 1. Collect kata files for the participants and AI solutions
    kata_files = []
    for participant in PARTICIPANTS:
        pattern = f"*{participant}*.py"
        kata_files.extend(KATA_DIR.rglob(pattern))

    for arq in sorted(KATA_DIR.rglob("*gemini*.py")):
        if arq not in kata_files:
            kata_files.append(arq)

    # 2. Compute per-file metrics (including individual duplication)
    rows = []
    for file_path in kata_files:
        name_lower = file_path.name.lower()
        if "gemini" in name_lower:
            author = "Vinicius"
            method = "AI"
        else:
            author = next(
                (p for p in PARTICIPANTS if p in name_lower), "unknown"
            )
            method = "Manual"

        loc = radon_raw(file_path)
        avg_cc, max_cc = radon_cc(file_path)
        mi = radon_mi(file_path)
        duplication_percent = compute_file_duplication(file_path)

        rows.append(
            {
                "file_path": str(file_path.relative_to(BASE_DIR)),
                "author": author.title()
                if isinstance(author, str)
                else str(author),
                "method": method,
                "loc": loc,
                "avg_cc": avg_cc,
                "max_cc": max_cc,
                "maintainability_index": mi,
                "duplication_percent": duplication_percent,
            }
        )

    # 3. Write CSV report
    csv_headers = [
        "file_path",
        "author",
        "method",
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

    # 4. Write markdown summary (top 5 most complex files by max_cc)
    top_complex = sorted(rows, key=lambda r: r["max_cc"], reverse=True)[:5]
    md_lines = [
        "# RQ3 Static Metrics Summary",
        "",
        "## Top 5 most complex kata files (by max cyclomatic complexity)",
        "| File | Author | Method | LOC | Avg CC | Max CC | Maintainability Index | Duplication (%) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in top_complex:
        md_lines.append(
            f"| {r['file_path']} | {r['author']} | {r['method']} | {r['loc']} | {r['avg_cc']} | {r['max_cc']} | {r['maintainability_index']} | {r['duplication_percent']:.2f}% |"
        )
    with open(MD_PATH, "w", encoding="utf-8") as mdfile:
        mdfile.write("\n".join(md_lines))
    print(f"Markdown summary written to {MD_PATH}")


if __name__ == "__main__":
    main()