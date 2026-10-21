"""Prepare 60 x 5 unidades da fonte da main explicitamente adotada.

Este modo preserva os dados fornecidos, mas não os certifica como coleta
empírica. A auditoria de bundles da API continua no fluxo original. Nenhum
julgamento humano, aprovação de repositório ou consenso é produzido aqui.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys

import pandas as pd
import yaml

from executar_amostra_ouro import _preflight
from gerar_amostra_rotulagem import instante, sha256, sortear
from rotulagem import JULGAMENTOS, METADADOS, gerar_rotulos, ler_csv, validar_amostra, validar_rotulos


TIPO_FONTE = "csv_main_adotado"
STATUS = "aguardando_rotulagem_humana_fonte_fornecida"
AVISO = "Fonte fornecida pela main; releases originais da API, critérios e cobertura histórica não auditados."
FLAGS = {
    "releases_originais_api_auditadas": False,
    "criterios_aprovacao_auditados": False,
    "cobertura_historica_verificada": False,
}
LAB = Path(__file__).resolve().parent
AUDITORIA = LAB / "data/execucao_pos_main/auditoria_dados.json"


def _carregar(csv_path, releases_path, proveniencia_path, config_path):
    rows = ler_csv(csv_path)
    names = [row.get("full_name", "") for row in rows]
    if len(rows) != 300 or len({name.casefold() for name in names}) != 300:
        raise ValueError("A fonte adotada deve conter exatamente 300 repositórios únicos; não se substitui a população automaticamente.")
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", name) for name in names):
        raise ValueError("Identificador full_name inválido na fonte fornecida.")
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    try:
        inicio, fim = (instante(config["window"][field]) for field in ("start_date", "end_date"))
    except (KeyError, TypeError) as exc:
        raise ValueError("Configuração sem janela válida para a fonte fornecida.") from exc
    if inicio >= fim:
        raise ValueError("Janela invertida ou vazia na configuração.")
    releases = json.loads(Path(releases_path).read_text(encoding="utf-8"))
    provenance = json.loads(Path(proveniencia_path).read_text(encoding="utf-8"))
    if not isinstance(provenance, dict):
        raise ValueError("O documento de proveniência fornecido deve ser um objeto JSON.")
    for field, path in (("repositorios_sha256", csv_path), ("releases_sha256", releases_path)):
        if provenance.get(field) != sha256(path):
            raise ValueError(f"Hash declarado na proveniência fornecida diverge: {field}.")
    window = provenance.get("janela")
    if not isinstance(window, dict) or instante(window.get("inicio")) != inicio or instante(window.get("fim")) != fim:
        raise ValueError("A janela declarada na fonte fornecida difere da configuração.")
    # A mesma ordenação, os mesmos filtros estruturais e os mesmos sorteios do
    # fluxo original. Não chama a auditoria nem promove declarações a evidência.
    common, _ = sortear(sorted(rows, key=lambda row: row["full_name"]), releases, inicio, fim)
    validar_amostra(common)
    selected_ids = {(row["full_name"], int(row["release_id"])) for row in common}
    evidence = {
        name: [release for release in sorted(releases[name], key=lambda rel: (instante(rel["published_at"]), rel["id"]))
               if (name, release["id"]) in selected_ids]
        for name in sorted({row["full_name"] for row in common})
    }
    return rows, common, evidence, provenance, inicio, fim


def _parecer(hash_csv, hash_releases, destino):
    result = {"origem_identificada": "nao_estabelecida_pelas_evidencias_preservadas"}
    if not AUDITORIA.is_file():
        return result
    opinion = json.loads(AUDITORIA.read_text(encoding="utf-8"))
    hashes = {source.get("sha256") for source in opinion.get("fontes", []) if isinstance(source, dict)}
    applies = hash_csv in hashes and hash_releases in hashes
    result["parecer_auditoria_preexistente"] = {
        "arquivo": os.path.relpath(AUDITORIA, destino).replace("\\", "/"), "sha256": sha256(AUDITORIA),
        "aplicavel_aos_hashes_csv_e_releases": applies,
    }
    if applies and "gerados" in opinion.get("conclusao", ""):
        result["origem_identificada"] = "seed_data.py/consolidar_dataset.py; registros fornecidos gerados por fórmulas"
    return result


def _json(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _resolver(registro, pasta):
    if not isinstance(registro, dict) or not isinstance(registro.get("arquivo"), str):
        raise ValueError("Entrada fornecida sem caminho e hash preservados.")
    path = Path(registro["arquivo"])
    path = path if path.is_absolute() else pasta / path
    if registro.get("sha256") != sha256(path):
        raise ValueError("Entrada original da fonte fornecida alterada: " + registro["arquivo"])
    return path


def validar_referencia_fornecida(amostra_csv, manifesto_json=None):
    """Reproduza a seleção da fonte adotada sem emitir selo de coleta real."""
    amostra_csv = Path(amostra_csv)
    manifesto_json = Path(manifesto_json) if manifesto_json else amostra_csv.parent / "selecao.json"
    manifest = json.loads(manifesto_json.read_text(encoding="utf-8"))
    required = {"schema_version": 1, "tipo_fonte": TIPO_FONTE, "random_state": 42,
                "n_populacao": 300, "n_repositorios": 60, "releases_por_repositorio": 5,
                "n_releases": 300, "status": STATUS, **FLAGS}
    if not isinstance(manifest, dict) or any(type(manifest.get(key)) is not type(value) or manifest.get(key) != value for key, value in required.items()):
        raise ValueError("Manifesto da fonte fornecida ausente ou incompatível; não certifica dados da API.")
    entries = manifest.get("entradas")
    if not isinstance(entries, dict) or set(entries) != {"csv", "releases", "proveniencia", "config"}:
        raise ValueError("Manifesto da fonte fornecida deve preservar as quatro entradas.")
    paths = {key: _resolver(value, manifesto_json.parent) for key, value in entries.items()}
    _, expected, evidence, provenance, inicio, fim = _carregar(
        paths["csv"], paths["releases"], paths["proveniencia"], paths["config"],
    )
    rows = ler_csv(amostra_csv)
    validar_amostra(rows)
    if manifest.get("amostra_comum_sha256") != sha256(amostra_csv) or rows != expected:
        raise ValueError("Referência fornecida não reproduz a seleção determinística preservada.")
    evidence_path = manifesto_json.parent / "evidencias_releases.json"
    if (manifest.get("evidencias_releases_sha256") != sha256(evidence_path)
            or json.loads(evidence_path.read_text(encoding="utf-8")) != evidence):
        raise ValueError("Conteúdo das releases fornecidas diverge da seleção original.")
    if (manifest.get("janela_declarada") != {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
            or manifest.get("proveniencia_fornecida_nao_auditada") != provenance):
        raise ValueError("Declarações da fonte fornecida divergem das entradas preservadas.")
    selection = [{field: row[field] for field in ("full_name", "release_id", "tag_name")} for row in expected]
    if manifest.get("selecao") != selection:
        raise ValueError("Identificadores do manifesto divergem do sorteio preservado.")
    return manifest


def executar(csv_path, releases_path, proveniencia_path, config_path, saida, rotulos):
    """Gere referência comum e rascunho humano exclusivos, todos sem votos."""
    csv_path, releases_path, proveniencia_path, config_path, saida, rotulos = map(
        Path, (csv_path, releases_path, proveniencia_path, config_path, saida, rotulos),
    )
    _preflight(saida, rotulos)
    rows, common, evidence, provenance, inicio, fim = _carregar(
        csv_path, releases_path, proveniencia_path, config_path,
    )
    originals = {"csv": csv_path, "releases": releases_path,
                 "proveniencia": proveniencia_path, "config": config_path}
    snapshots = {key: saida / "fontes_entrada" / (key + path.suffix)
                 for key, path in originals.items()}
    if rotulos.resolve() in {path.resolve() for path in snapshots.values()}:
        raise ValueError("O CSV humano não pode ocupar o caminho de uma entrada preservada.")
    saida.mkdir(parents=True)
    # Preserve bytes, inclusive finais de linha: hashes da proveniência não
    # podem depender de core.autocrlf na máquina de outro avaliador.
    (saida / "fontes_entrada").mkdir()
    for key, path in originals.items():
        shutil.copyfile(path, snapshots[key])
    common_path = saida / "amostra_comum.csv"
    with common_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=METADADOS + JULGAMENTOS)
        writer.writeheader()
        writer.writerows(common)
    evidence_path = saida / "evidencias_releases.json"
    _json(evidence_path, evidence)
    manifest = {
        "schema_version": 1, "tipo_fonte": TIPO_FONTE, "status": STATUS,
        "aviso": AVISO, **FLAGS,
        "criado_em_utc": datetime.now(timezone.utc).isoformat(),
        "origem_da_fonte": "arquivos_fornecidos_pela_main_adotados_explicitamente",
        **_parecer(sha256(csv_path), sha256(releases_path), saida),
        "proveniencia_fornecida_nao_auditada": provenance,
        "n_populacao": len(rows), "n_repositorios": 60, "releases_por_repositorio": 5,
        "n_releases": len(common), "random_state": 42,
        "algoritmo": "pandas.DataFrame.sample sem reposição; população ordenada por full_name; releases por published_at UTC/id; random_state=42 em cada sorteio; sem substituir insuficientes",
        "versoes": {"python": sys.version.split()[0], "pandas": pd.__version__, "PyYAML": yaml.__version__},
        "codigo_sha256": {name: sha256(LAB / name) for name in
                          ("amostra_csv_main.py", "gerar_amostra_rotulagem.py", "rotulagem.py")},
        "janela_declarada": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "entradas": {key: {"arquivo": os.path.relpath(path.resolve(), saida.resolve()).replace("\\", "/"),
                           "sha256": sha256(path)} for key, path in snapshots.items()},
        "entradas_originais": {key: {"arquivo": os.path.relpath(path.resolve(), LAB).replace("\\", "/"),
                                     "sha256": sha256(path)} for key, path in originals.items()},
        "amostra_comum_sha256": sha256(common_path),
        "evidencias_releases_sha256": sha256(evidence_path),
        "selecao": [{field: row[field] for field in ("full_name", "release_id", "tag_name")} for row in common],
    }
    _json(saida / "selecao.json", manifest)
    validar_referencia_fornecida(common_path)
    rotulos.parent.mkdir(parents=True, exist_ok=True)
    gerar_rotulos(common_path, rotulos)
    validar_rotulos(common, ler_csv(rotulos), permitir_vazios=True)
    return {"manifesto": manifest, "amostra": str(common_path), "rotulos": str(rotulos), "status": STATUS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("csv", "releases", "proveniencia", "config", "saida", "rotulos"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = executar(args.csv, args.releases, args.proveniencia, args.config, args.saida, args.rotulos)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, yaml.YAMLError) as exc:
        print(f"Preparação da fonte fornecida interrompida: {exc}", file=sys.stderr)
        return 2
    print(f"Referência da fonte fornecida: {result['amostra']} (60 × 5; random_state=42).")
    print(f"Rascunho independente: {result['rotulos']}; todos os julgamentos vazios.")
    print(AVISO)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
