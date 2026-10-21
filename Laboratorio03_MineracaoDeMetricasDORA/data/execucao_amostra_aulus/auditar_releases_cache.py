"""Audite releases preservadas no cache sem alterar a população adotada.

Não aprova repositórios, não consulta a rede e não gera a amostra-ouro. Mantém
o sorteio original de 60 nomes entre os 300 do CSV, inclusive insuficientes e
ausentes, para mostrar exatamente o que impede o protocolo de 60 x 5.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd


INICIO = datetime(2023, 10, 1, tzinfo=timezone.utc)
FIM = datetime(2024, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
SEMENTE = 42
N_REPOS = 60
HEADERS = {
    "link", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
    "retry-after", "etag", "last-modified",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def iso(data):
    return data.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def instante(value):
    data = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if data.tzinfo is None:
        raise ValueError("data sem fuso horário")
    return data.astimezone(timezone.utc)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_json(path, value):
    path.write_bytes(json_bytes(value))


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in rows)


def auditar_repo(con, source, selected, archive):
    name = source["full_name"]
    endpoint = f"https://api.github.com/repos/{name}/releases"
    key = endpoint + "?per_page=100"
    pages, visited, ids, tags, problems = [], set(), set(), set(), []
    total_stable = 0
    status = "completa"
    missing = None
    while key:
        if key in visited:
            status = "incompleta_ciclo"
            problems.append(f"Link next repetido: {key}")
            break
        visited.add(key)
        parsed = urlsplit(key)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com" or not parsed.path.endswith("/releases"):
            status = "incompleta_link_invalido"
            problems.append(f"Link fora do endpoint de releases: {key}")
            break
        row = con.execute(
            "SELECT url,status_code,state,response_json,response_headers,timestamp "
            "FROM api_cache WHERE cache_key=?", (key,),
        ).fetchone()
        if row is None:
            status, missing = "pagina_ausente", key
            break
        url, code, state, raw, raw_headers, timestamp = row
        if state != "complete" or code != 200 or not isinstance(raw, str):
            status, missing = "pagina_pendente_ou_http_invalido", key
            break
        try:
            data = json.loads(raw)
            headers = json.loads(raw_headers)
            if not isinstance(data, list) or not isinstance(headers, dict):
                raise ValueError("JSON de página/lista ou headers inválidos")
        except (TypeError, ValueError) as exc:
            status = "incompleta_schema"
            problems.append(str(exc))
            break
        safe_headers = {k: v for k, v in headers.items() if k.lower() in HEADERS}
        lower_headers = {k.lower(): v for k, v in safe_headers.items()}
        raw_bytes = raw.encode("utf-8")
        page = {
            "cache_key": key, "url_cache": url, "status_http": code,
            "estado_cache": state, "parametros_url": parse_qs(parsed.query),
            "timestamp_cache_unix": timestamp,
            "timestamp_cache_utc": iso(datetime.fromtimestamp(timestamp, timezone.utc)),
            "response_json_sha256": digest(raw_bytes),
            "response_json_bytes": len(raw_bytes), "n_registros": len(data),
            "response_headers": safe_headers,
        }
        if selected:
            base = f"{name.replace('/', '__')}/pagina_{len(pages) + 1:04d}"
            page["arquivo_original_zip"] = base + ".json"
            archive.writestr(base + ".json", raw_bytes)
            archive.writestr(base + ".metadados.json", json_bytes(page))
        pages.append(page)
        for release in data:
            if not isinstance(release, dict) or type(release.get("draft")) is not bool or type(release.get("prerelease")) is not bool:
                problems.append(f"Página {len(pages)}: flags draft/prerelease inválidas")
                continue
            if release["draft"] or release["prerelease"]:
                continue
            try:
                published = instante(release.get("published_at"))
            except (AttributeError, TypeError, ValueError):
                problems.append(f"Página {len(pages)}: published_at inválido")
                continue
            if not INICIO <= published <= FIM:
                continue
            release_id, tag = release.get("id"), release.get("tag_name")
            if type(release_id) is not int or release_id <= 0 or not isinstance(tag, str) or not tag:
                problems.append(f"Página {len(pages)}: ID/tag inválido na janela")
                continue
            if release_id in ids or tag in tags:
                problems.append(f"Release duplicada na janela: {release_id}/{tag}")
                continue
            ids.add(release_id)
            tags.add(tag)
            total_stable += 1
        link = lower_headers.get("link", "")
        next_links = re.findall(r'<([^>]+)>;\s*rel="next"', link)
        if len(next_links) > 1:
            status = "incompleta_links_multiplos"
            problems.append("Mais de um Link next na mesma página")
            break
        key = next_links[0] if next_links else None
    stable_complete = total_stable if status == "completa" and not problems else None
    sufficient = stable_complete is not None and stable_complete >= 5
    return {
        "full_name": name, "selecionado_seed42": selected,
        "status_cadeia": status, "n_paginas": len(pages),
        "releases_estaveis_janela": stable_complete,
        "releases_estaveis_observadas": total_stable,
        "releases_csv_adotado": int(source["total_releases_janela"]),
        "contagem_coincide_csv": stable_complete == int(source["total_releases_janela"]),
        "minimo_5_comprovado_no_cache": sufficient,
        "proxima_pagina_ausente": missing,
        "problemas": problems, "paginas": pages,
        "observacao": "Apenas evidência de releases; não valida stars, workflows, runs ou aprovação final.",
    }


def resumo(rows):
    return {
        "n_repositorios": len(rows),
        "cadeias_completas_sem_erro": sum(r["releases_estaveis_janela"] is not None for r in rows),
        "minimo_5_releases_comprovado_no_cache": sum(r["minimo_5_comprovado_no_cache"] for r in rows),
        "menos_de_5_com_cadeia_completa": sum(r["releases_estaveis_janela"] is not None and r["releases_estaveis_janela"] < 5 for r in rows),
        "cadeias_incompletas_ou_invalidas": sum(r["releases_estaveis_janela"] is None for r in rows),
        "contagens_coincidentes_csv": sum(r["contagem_coincide_csv"] for r in rows),
        "n_paginas_preservadas_no_cache": sum(r["n_paginas"] for r in rows),
    }


def main(argv=None):
    lab = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=lab / "data/coleta_final/repositorios_aprovados.csv")
    parser.add_argument("--cache", type=Path, default=lab / "data/coleta_final/cache/github_cache.db")
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    source_bytes = args.csv.read_bytes()
    with args.csv.open(encoding="utf-8-sig", newline="") as stream:
        sources = list(csv.DictReader(stream))
    names = [row["full_name"] for row in sources]
    if len(sources) != 300 or len(set(name.casefold() for name in names)) != 300:
        raise ValueError("Esta auditoria exige os 300 identificadores únicos do CSV adotado.")
    selected = set(pd.DataFrame(sources).sort_values("full_name").sample(n=N_REPOS, random_state=SEMENTE)["full_name"])
    args.saida.mkdir(parents=True, exist_ok=True)
    archive_path = args.saida / "originais_selecionados60.zip"
    cache_uri = args.cache.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(cache_uri, uri=True) as con, ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        con.execute("PRAGMA query_only = ON")
        results = [auditar_repo(con, row, row["full_name"] in selected, archive)
                   for row in sorted(sources, key=lambda item: item["full_name"])]
    selected_rows = [row for row in results if row["selecionado_seed42"]]
    fields = ["full_name", "selecionado_seed42", "status_cadeia", "n_paginas",
              "releases_estaveis_janela", "releases_estaveis_observadas", "releases_csv_adotado",
              "contagem_coincide_csv", "minimo_5_comprovado_no_cache"]
    write_csv(args.saida / "releases_cache.csv", results, fields)
    write_csv(args.saida / "sorteio_original_60.csv", selected_rows, fields)
    shared = {
        "schema_version": 1, "executado_em_utc": iso(datetime.now(timezone.utc)),
        "fonte_csv": {"arquivo": str(args.csv.resolve()), "sha256": digest(source_bytes)},
        "fonte_cache": {"arquivo": str(args.cache.resolve()), "bytes": args.cache.stat().st_size,
                        "modo": "SQLite mode=ro; PRAGMA query_only=ON"},
        "janela": {"inicio": iso(INICIO), "fim": iso(FIM)},
        "sorteio": {"semente": SEMENTE, "n_populacao": 300, "n_repositorios": N_REPOS,
                    "algoritmo": "pandas.DataFrame.sort_values(full_name).sample(n=60,random_state=42); sem substituição de insuficientes",
                    "pandas_version": pd.__version__},
        "originais_zip": {"arquivo": archive_path.name, "sha256": digest(archive_path.read_bytes()),
                          "bytes": archive_path.stat().st_size,
                          "conteudo": "Apenas páginas dos 60 selecionados já presentes no cache. JSON exato serializado pelo cliente no SQLite, não bytes HTTP originais; inclui metadados e headers preservados."},
        "limites": [
            "Não houve consulta à rede, troca de candidatos, alteração de janela ou de critérios.",
            "Ausência de página no cache não prova ausência de releases na API.",
            "Cadeia completa significa sequência Link next preservada até resposta terminal sem next; não garante que releases históricas não tenham sido apagadas antes da coleta.",
            "Cache e hashes permitem reproduzir a auditoria local; não certificam a aprovação dos 300 registros do CSV.",
            "Este sorteio de nomes é diagnóstico e não é a amostra-ouro nem um formulário de avaliação humana.",
        ],
    }
    maximum = 300 - resumo(results)["menos_de_5_com_cadeia_completa"]
    report = {**shared, "status": "bloqueado_para_amostra_ouro_60x5",
              "resumo_populacao": resumo(results), "resumo_sorteio_60": resumo(selected_rows),
              "limite_superior_elegiveis_se_todos_os_ausentes_passassem": maximum,
              "repositorios": results}
    write_json(args.saida / "releases_cache.json", report)
    write_json(args.saida / "sorteio_original_60.json",
               {**shared, "status": report["status"], "resumo": resumo(selected_rows), "repositorios": selected_rows})
    print(json.dumps({"populacao": report["resumo_populacao"], "sorteio": report["resumo_sorteio_60"],
                      "originais_zip_bytes": archive_path.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
