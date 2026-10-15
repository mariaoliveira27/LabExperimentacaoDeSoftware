"""Inspecione o arquivo público de runs de 2024 sem inventar histórico anual.

A CLI aceita somente o ZIP publicado no Zenodo, com MD5 conhecido. Runs reais
observados podem comprovar um limite inferior de elegibilidade. A cobertura
parcial não autoriza calcular métricas DORA para os doze meses do estudo.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import yaml

from coletor_runs import VALID_CONCLUSIONS


DOI_FONTE = "10.5281/zenodo.20414642"
URL_FONTE = "https://zenodo.org/records/20414642/files/cicd_env_results.zip?download=1"
MD5_FONTE = "df0e00311cdfa611e784c373d20bacd5"
INICIO_FONTE = "2024-01-01T00:00:00Z"
FIM_FONTE = "2024-12-31T23:59:59Z"
MIN_STARS = 1000
MIN_RUNS = 50


def _instante(valor):
    if not isinstance(valor, str):
        raise ValueError(f"Timestamp ISO 8601 ausente: {valor!r}.")
    data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if data.tzinfo is None or data.utcoffset() is None:
        raise ValueError(f"Timestamp sem fuso horário: {valor!r}.")
    return data.astimezone(timezone.utc)


def _hashes(path):
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    with Path(path).open("rb") as arquivo:
        while bloco := arquivo.read(8 * 1024 * 1024):
            md5.update(bloco)
            sha256.update(bloco)
    return md5.hexdigest(), sha256.hexdigest()


def _metadata(info, path):
    if not isinstance(info, dict):
        raise ValueError(f"Metadados não são objeto JSON: {path}.")
    nome = info.get("full_name")
    if not isinstance(nome, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", nome,
    ):
        raise ValueError(f"full_name inválido em {path}.")
    if type(info.get("id")) is not int or info["id"] <= 0:
        raise ValueError(f"ID GitHub inválido em {path}.")
    if type(info.get("stargazers_count")) is not int or info["stargazers_count"] < 0:
        raise ValueError(f"Stars inválidas em {path}.")
    if not isinstance(info.get("default_branch"), str) or not info["default_branch"].strip():
        raise ValueError(f"default_branch ausente em {path}.")
    for campo in ("fork", "archived"):
        if type(info.get(campo)) is not bool:
            raise ValueError(f"Flag {campo} ausente em {path}.")
    return {
        "full_name": nome, "repository_id": info["id"],
        "stars": info["stargazers_count"], "default_branch": info["default_branch"],
        "fork": info["fork"], "archived": info["archived"],
        # O arquivo original usa collected_at sem fuso em alguns registros.
        # Preservamos essa informação como foi publicada, sem atribuir UTC.
        "data_coleta_original": info.get("collected_at"),
        "created_at_original": info.get("created_at"),
        "arquivo_info": path,
        "arquivo_runs": path[:-len("info.json")] + "workflow_runs.json",
        "runs_validos_observados": None,
        "status_fonte_runs": "nao_inspecionado",
    }


def _runs_observados(payload, metadata, inicio, fim):
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), dict):
        raise ValueError(f"workflow_runs deve ser objeto indexado por IDs: {metadata['full_name']}.")
    selecionadas, ids = [], set()
    for run in payload["workflow_runs"].values():
        if not isinstance(run, dict):
            raise ValueError(f"Run inválido: {metadata['full_name']}.")
        conclusao = run.get("conclusion")
        conclusao = conclusao.strip().lower() if isinstance(conclusao, str) else ""
        if (
            run.get("event") != "push"
            or run.get("head_branch") != metadata["default_branch"]
            or run.get("status") != "completed"
            or conclusao not in VALID_CONCLUSIONS
        ):
            continue
        criada = _instante(run.get("created_at"))
        if not inicio <= criada <= fim:
            continue
        for campo in ("id", "workflow_id"):
            if type(run.get(campo)) is not int or run[campo] <= 0:
                raise ValueError(f"{campo} inválido: {metadata['full_name']}.")
        if run["id"] in ids:
            raise ValueError(f"ID de run duplicado: {run['id']}.")
        ids.add(run["id"])
        repo = run.get("repository")
        if (
            not isinstance(repo, dict) or repo.get("id") != metadata["repository_id"]
            or not isinstance(repo.get("full_name"), str)
            or repo["full_name"].casefold() != metadata["full_name"].casefold()
        ):
            raise ValueError(f"Run pertence a outro repositório: {metadata['full_name']}.")
        iniciada, atualizada = _instante(run.get("run_started_at")), _instante(run.get("updated_at"))
        if atualizada < iniciada or atualizada < criada:
            raise ValueError(f"Timestamps de run fora de ordem: {run['id']}.")
        selecionadas.append(run)  # Objeto original completo, sem rótulo ou heurística.
    return sorted(selecionadas, key=lambda run: (_instante(run["created_at"]), run["id"]))


def _ler_fonte(arquivo, inicio_observado, fim_observado):
    """Derive os artefatos dos membros originais, também para auditar exports."""
    metadados, runs, repo_ids, nomes, ids_runs = [], {}, set(), set(), set()
    with zipfile.ZipFile(arquivo) as archive:
        members = archive.infolist()
        filenames = {item.filename for item in members}
        if len(members) != len(filenames):
            raise ValueError("ZIP com nomes de membros duplicados.")
        for item in members:
            if "/gha_repos/" not in item.filename or not item.filename.endswith("/info.json"):
                continue
            with archive.open(item) as stream:
                metadata = _metadata(json.load(stream), item.filename)
            nome, repo_id = metadata["full_name"], metadata["repository_id"]
            if repo_id in repo_ids or nome.casefold() in nomes:
                raise ValueError(f"Repositório duplicado no arquivo: {nome}.")
            repo_ids.add(repo_id)
            nomes.add(nome.casefold())
            metadados.append(metadata)
            if metadata["stars"] < MIN_STARS:
                continue
            if metadata["arquivo_runs"] not in filenames:
                metadata["status_fonte_runs"] = "arquivo_runs_ausente"
                continue  # Ausência de arquivo não é contagem histórica zero.
            with archive.open(metadata["arquivo_runs"]) as stream:
                observadas = _runs_observados(json.load(stream), metadata, inicio_observado, fim_observado)
            metadata["runs_validos_observados"] = len(observadas)
            metadata["status_fonte_runs"] = "inspecionado"
            if len(observadas) < MIN_RUNS:
                continue
            for run in observadas:
                if run["id"] in ids_runs:
                    raise ValueError(f"ID global de run duplicado: {run['id']}.")
                ids_runs.add(run["id"])
            runs[nome] = observadas
    if not metadados:
        raise ValueError("ZIP sem info.json de repositórios do dataset de 2024.")
    metadados.sort(key=lambda row: row["full_name"])
    return metadados, runs


def _recuperar(arquivo, config_path, saida, *, md5_esperado):
    """Helper interno; checksum alternativo serve exclusivamente a fixtures."""
    arquivo, config_path, saida = map(Path, (arquivo, config_path, saida))
    if saida.exists() or saida.is_symlink():
        raise FileExistsError(f"Destino preservado: {saida} já existe.")
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    inicio = _instante(config["window"]["start_date"])
    fim = _instante(config["window"]["end_date"])
    if inicio > fim:
        raise ValueError("Janela de observação invertida.")
    md5, sha256 = _hashes(arquivo)
    if md5 != md5_esperado:
        raise ValueError(
            "MD5 não confere com a fonte publicada. Arquivos parciais ou alterados "
            "não podem ser utilizados como histórico real."
        )
    inicio_observado = max(inicio, _instante(INICIO_FONTE))
    fim_observado = min(fim, _instante(FIM_FONTE))
    if inicio_observado > fim_observado:
        raise ValueError("A janela do estudo não intersecta a cobertura publicada de 2024.")
    metadados, runs = _ler_fonte(arquivo, inicio_observado, fim_observado)
    empirica = md5_esperado == MD5_FONTE
    manifest = {
        "schema_version": 1,
        "origem": "arquivo_publico_zenodo" if empirica else "fixture_sintetica_de_teste",
        "dados_empiricos": empirica,
        "source_doi": DOI_FONTE if empirica else None,
        "source_url": URL_FONTE if empirica else None,
        "arquivo_fonte": str(arquivo.resolve()), "arquivo_tamanho": arquivo.stat().st_size,
        "md5_esperado": md5_esperado, "md5_verificado": md5, "arquivo_sha256": sha256,
        "config_sha256": _hashes(config_path)[1],
        "inspecionado_em": datetime.now(timezone.utc).isoformat(),
        "cobertura": "limite_inferior_observado", "historico_anual_completo": False,
        "permite_metricas_dora_anuais": False,
        "janela_estudo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "janela_fonte": {"inicio": INICIO_FONTE, "fim": FIM_FONTE},
        "intervalo_observado": {"inicio": inicio_observado.isoformat(), "fim": fim_observado.isoformat()},
        "filtros": {"min_stars_snapshot": MIN_STARS, "event": "push", "branch": "default_branch_snapshot", "status": "completed", "conclusions": sorted(VALID_CONCLUSIONS), "min_runs_observados": MIN_RUNS},
        "repositorios_metadata": len(metadados),
        "repositorios_snapshot_stars_ge1000": sum(row["stars"] >= MIN_STARS for row in metadados),
        "repositorios_sem_arquivo_runs": sum(row["status_fonte_runs"] == "arquivo_runs_ausente" for row in metadados),
        "repositorios_com_50_runs_observados": len(runs), "runs_observados_exportados": sum(len(lista) for lista in runs.values()),
        "pendencias": ["Verificar metadados atuais e pelo menos cinco releases reais pela API.", "Comprovar população final de pelo menos 300 repositórios.", "Não calcular métricas anuais de CI com a cobertura parcial."],
    }
    saida.mkdir(parents=True)
    paths = {
        "metadata_repositorios.json": metadados,
        "runs_historicos.json": runs,
    }
    hashes = {}
    for nome, dados in paths.items():
        path = saida / nome
        with path.open("x", encoding="utf-8") as stream:
            json.dump(dados, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        hashes[nome] = _hashes(path)[1]
    manifest["saidas_sha256"] = hashes
    with (saida / "proveniencia_historico.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return manifest


def recuperar(arquivo, config, saida):
    """Inspecione exclusivamente a fonte publicada, cujo MD5 é fixo."""
    return _recuperar(arquivo, config, saida, md5_esperado=MD5_FONTE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--saida", type=Path, default=Path("data/historico_2024"))
    args = parser.parse_args(argv)
    try:
        manifesto = recuperar(args.arquivo, args.config, args.saida)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, yaml.YAMLError) as exc:
        print(f"Recuperação interrompida: {exc}", file=sys.stderr)
        return 2
    print(
        f"Fonte verificada: {manifesto['repositorios_metadata']} repositórios; "
        f"{manifesto['repositorios_snapshot_stars_ge1000']} com >=1000 stars no snapshot; "
        f"{manifesto['repositorios_com_50_runs_observados']} com >=50 runs válidos observados."
    )
    print(f"Artefatos em {args.saida}. Cobertura parcial: limite inferior, sem métricas anuais DORA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
