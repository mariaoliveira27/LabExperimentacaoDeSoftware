"""Leitura verificável dos registros do Lab 02, sem executar as soluções."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd


TREATMENTS = ("manual", "ia")
# Ajuste de rótulos solicitado por Áulus. Os IDs e os artefatos arquivados
# permanecem intactos; o destino explícito evita inverter duas vezes.
AJUSTES_TRATAMENTO = {
    "aulus_K01_manual_01": "ia",
    "aulus_K02_ia_01": "manual",
    "aulus_K03_manual_01": "ia",
    "aulus_K04_ia_01": "manual",
    "aulus_K05_manual_01": "ia",
    "aulus_K06_ia_01": "manual",
}
ROW_COLUMNS = (
    "trial_id", "integrante", "kata", "tratamento", "tempo_min", "taxa_sucesso",
    "passou_todos", "total_testes", "aprovados", "reprovados", "complexidade_media",
    "loc", "sloc", "fonte_testes", "metricas_disponiveis", "status_registrado",
    "status_divergente", "tempo_censurado", "tratamento_registrado", "tratamento_ajustado",
)
REQUIRED_COLUMNS = (
    "Trial_ID", "Integrante", "Kata", "Tratamento", "Tempo_Final_Considerado",
    "Taxa_Sucesso_Testes", "Passou_Testes", "Status", "Dado_Censurado",
)


def _number(value, name: str, *, maximum: float | None = None, integer=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: número ausente ou inválido ({value!r}).") from exc
    if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
        raise ValueError(f"{name}: valor fora do domínio ({value!r}).")
    if integer and not number.is_integer():
        raise ValueError(f"{name}: a contagem precisa ser inteira.")
    return int(number) if integer else number


def _boolean(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    raise ValueError(f"{name}: booleano inválido ({value!r}).")


def _json(path: Path, trial_id: str) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Não foi possível ler {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("trial_id") != trial_id:
        raise ValueError(f"{path}: trial_id diferente do registro CSV.")
    return document


def load_trials(data_dir: str | Path, *, aplicar_ajustes: bool = True) -> pd.DataFrame:
    """Uma linha por trial do CSV; JSONs locais complementam essa população.

    Caminhos absolutos antigos do CSV nunca são usados. Relatórios ausentes não
    viram zero: a taxa declarada permanece identificada por fonte_testes='csv'.
    """
    directory = Path(data_dir).resolve()
    csv_path = directory / "registro_experimento.csv"
    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = sorted(set(REQUIRED_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing)}")
    if raw.empty:
        raise ValueError("O registro do experimento não contém trials.")
    if raw["Trial_ID"].duplicated().any():
        duplicate = raw.loc[raw["Trial_ID"].duplicated(), "Trial_ID"].tolist()
        raise ValueError(f"Trial_ID duplicado: {', '.join(duplicate)}")

    records = []
    for source in raw.to_dict(orient="records"):
        trial_id = source["Trial_ID"].strip()
        participant = source["Integrante"].strip().lower()
        kata = source["Kata"].strip().upper()
        treatment = source["Tratamento"].strip().lower()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", trial_id):
            raise ValueError(f"Trial_ID inválido: {trial_id!r}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", participant) or participant == "all":
            raise ValueError(f"{trial_id}: integrante inválido.")
        if not re.fullmatch(r"K\d{2}", kata):
            raise ValueError(f"{trial_id}: kata inválido ({kata!r}).")
        if treatment not in TREATMENTS:
            raise ValueError(f"{trial_id}: tratamento desconhecido ({treatment!r}).")
        original_treatment = treatment
        if aplicar_ajustes and participant == "aulus":
            treatment = AJUSTES_TRATAMENTO.get(trial_id, treatment)

        tests_source = "csv"
        total = approved = failed = None
        trial_dir = directory / "resultados" / trial_id
        tests_path = trial_dir / "testes.json"
        if tests_path.is_file():
            tests = _json(tests_path, trial_id).get("resultado")
            if not isinstance(tests, dict):
                raise ValueError(f"{tests_path}: resultado de testes ausente.")
            total = _number(tests.get("total_casos"), f"{trial_id}/total_casos", integer=True)
            approved = _number(tests.get("aprovados"), f"{trial_id}/aprovados", integer=True)
            failed = _number(tests.get("reprovados"), f"{trial_id}/reprovados", integer=True)
            if total == 0 or approved + failed != total:
                raise ValueError(f"{trial_id}: contagens de testes inconsistentes.")
            rate = _number(tests.get("taxa_sucesso"), f"{trial_id}/taxa JSON", maximum=100)
            if abs(rate - 100 * approved / total) > 0.011:
                raise ValueError(f"{trial_id}: taxa incompatível com as contagens dos testes.")
            passed_all = approved == total
            if "passou_todos" in tests and _boolean(tests["passou_todos"], trial_id) != passed_all:
                raise ValueError(f"{trial_id}: aprovação completa incompatível com os testes.")
            tests_source = "relatorio"
        else:
            rate = _number(source["Taxa_Sucesso_Testes"], f"{trial_id}/taxa CSV", maximum=100)
            passed_all = _boolean(source["Passou_Testes"], f"{trial_id}/Passou_Testes")
            if passed_all != (rate == 100):
                raise ValueError(f"{trial_id}: taxa e aprovação completa divergentes no CSV.")

        complexity = loc = sloc = None
        metrics_available = False
        metrics_path = trial_dir / "metricas.json"
        if metrics_path.is_file():
            metrics = _json(metrics_path, trial_id)
            if metrics.get("status_analise") == "ok":
                loc = _number(metrics.get("loc"), f"{trial_id}/loc", integer=True)
                sloc = _number(metrics.get("sloc"), f"{trial_id}/sloc", integer=True)
                if sloc > loc:
                    raise ValueError(f"{trial_id}: SLOC maior que LOC.")
                if metrics.get("complexidade_media") is not None:
                    complexity = _number(metrics["complexidade_media"], f"{trial_id}/complexidade")
                metrics_available = True

        status = source["Status"].strip().upper()
        records.append({
            "trial_id": trial_id,
            "integrante": participant,
            "kata": kata,
            "tratamento": treatment,
            "tratamento_registrado": original_treatment,
            "tratamento_ajustado": treatment != original_treatment,
            "tempo_min": _number(source["Tempo_Final_Considerado"], f"{trial_id}/tempo"),
            "taxa_sucesso": rate,
            "passou_todos": passed_all,
            "total_testes": total,
            "aprovados": approved,
            "reprovados": failed,
            "complexidade_media": complexity,
            "loc": loc,
            "sloc": sloc,
            "fonte_testes": tests_source,
            "metricas_disponiveis": metrics_available,
            "status_registrado": status,
            "status_divergente": status == "SUCESSO" and not passed_all,
            "tempo_censurado": _boolean(source["Dado_Censurado"], f"{trial_id}/censura"),
        })

    frame = pd.DataFrame.from_records(records, columns=ROW_COLUMNS)
    if frame["trial_id"].duplicated().any():
        raise ValueError("Trial_ID duplicado após normalização.")
    return frame.sort_values(["integrante", "kata", "tratamento", "trial_id"]).reset_index(drop=True)


def select_trials(frame: pd.DataFrame, participant: str = "all", kata: str = "all") -> pd.DataFrame:
    selected = frame
    if participant != "all":
        selected = selected.loc[selected["integrante"] == participant]
    if kata != "all":
        selected = selected.loc[selected["kata"] == kata]
    return selected.copy()


def _distribution(values: pd.Series) -> dict:
    clean = values.dropna().astype(float)
    if clean.empty:
        return {"n": 0, "median": None, "q1": None, "q3": None}
    return {
        "n": int(len(clean)),
        "median": float(clean.median()),
        "q1": float(clean.quantile(0.25, interpolation="linear")),
        "q3": float(clean.quantile(0.75, interpolation="linear")),
    }


def build_view(frame: pd.DataFrame, participant: str = "all", kata: str = "all") -> dict:
    """Agrega o recorte sem I/O. Cada trial recebe peso igual na taxa média."""
    selected = select_trials(frame, participant, kata)
    stats = {}
    for treatment in TREATMENTS:
        group = selected.loc[selected["tratamento"] == treatment]
        rates = group["taxa_sucesso"].dropna().astype(float)
        stats[treatment] = {
            "n": int(len(group)),
            "tempo": _distribution(group["tempo_min"]),
            "sucesso": {
                "n": int(len(rates)),
                "mean": float(rates.mean()) if len(rates) else None,
                "complete": int(group["passou_todos"].sum()),
            },
            "complexidade": _distribution(group["complexidade_media"]),
            "loc": _distribution(group["loc"]),
        }
    return {
        "integrante": participant,
        "kata": kata,
        "row_ids": selected["trial_id"].tolist(),
        "adjustment_count": int(selected.get("tratamento_ajustado", pd.Series(False, index=selected.index)).sum()),
        "counts": {
            "total": int(len(selected)),
            "manual": int((selected["tratamento"] == "manual").sum()),
            "ia": int((selected["tratamento"] == "ia").sum()),
            "testes_arquivados": int((selected["fonte_testes"] == "relatorio").sum()),
            "metricas_arquivadas": int(selected["metricas_disponiveis"].sum()),
            "divergencias": int(selected["status_divergente"].sum()),
        },
        "stats": stats,
    }


def records_for_json(frame: pd.DataFrame) -> list[dict]:
    """Converte escalares Pandas e ausências para JSON padrão, sem NaN."""
    records = []
    integer_columns = {"total_testes", "aprovados", "reprovados", "loc", "sloc"}
    for original in frame.to_dict(orient="records"):
        record = {}
        for key, value in original.items():
            if pd.isna(value):
                record[key] = None
            elif key in integer_columns:
                record[key] = int(value)
            else:
                record[key] = value
        records.append(record)
    return records
