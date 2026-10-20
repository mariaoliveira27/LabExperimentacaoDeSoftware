"""Coleta auditável da população elegível para a amostra-ouro (sem simulação).

Este coletor exporta fatos de seleção, releases originais e proveniência.
Não calcula métricas DORA com números simulados nem decisões de avaliadores.
"""

import argparse
import csv
from contextlib import closing
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

import yaml

from api_client import GitHubClient
from busca_candidatos import buscar_candidatos
from coletor_runs import ColetorRuns, VALID_CONCLUSIONS
from funil import FunilSelecao
from gerar_amostra_rotulagem import instante, ler_aprovados, releases_validas, sha256, validar_proveniencia
from metricas.calculo_metricas import calcular_cfr_ci
from recuperar_historico import DOI_FONTE, URL_FONTE, MD5_FONTE, INICIO_FONTE, FIM_FONTE, _hashes, _ler_fonte


logger = logging.getLogger("ColetaAmostraReal")
CAMPOS_APROVADOS = (
    "full_name", "owner", "repo", "stars", "language", "default_branch", "created_at",
    "total_releases_janela", "total_runs_janela", "origem_coleta", "origem_metricas_estabilidade",
    "escopo_contagem_runs",
)
CAMPOS_PARCIAIS = CAMPOS_APROVADOS


class FunilColeta(FunilSelecao):
    """Distingue critérios comprovados de evidência histórica indisponível."""

    def gerar_tabela_funil(self):
        tabela = super().gerar_tabela_funil()
        tabela[0]["etapa"] = "1. Candidatos processados da busca pública (stars >= 1000)"
        tabela[1]["motivo_descarte"] = "evidencia_actions_historicos_insuficiente"
        tabela[3]["etapa"] = "4. Mínimo de 50 workflow runs válidos comprovado por registros disponíveis"
        tabela[3]["motivo_descarte"] = "evidencia_runs_historicos_insuficiente; evidencia_runs_validos_insuficiente"
        return tabela


class HistoricoZenodo:
    """Artefatos verificados; a identidade GitHub permite nomes antigos."""

    def __init__(self, metadados_por_id, runs_por_id, referencia):
        self.metadados_por_id = metadados_por_id
        self.runs_por_id = runs_por_id
        self.referencia = referencia


def _validar_run_historico(run, metadata, inicio, fim):
    nome = metadata["full_name"]
    _validar_run_observado(run, nome, metadata["default_branch"], inicio, fim)
    repo = run.get("repository")
    if (not isinstance(repo, dict) or type(repo.get("id")) is not int
            or repo["id"] != metadata["repository_id"]
            or not isinstance(repo.get("full_name"), str)
            or repo["full_name"].casefold() != nome.casefold()
            or run.get("status") != "completed"
            or not isinstance(run.get("conclusion"), str)
            or run["conclusion"].strip().lower() not in VALID_CONCLUSIONS):
        raise ValueError(f"Identidade, status ou conclusão inválida no run histórico de {nome}.")
    criada = instante(run["created_at"])
    iniciada, atualizada = instante(run.get("run_started_at")), instante(run.get("updated_at"))
    if atualizada < iniciada or atualizada < criada:
        raise ValueError(f"Timestamps inconsistentes no run histórico de {nome}.")


def _carregar_historico_zenodo(diretorio, inicio, fim):
    """Aceita somente exportação empírica do ZIP publicado, íntegro e local."""
    diretorio = Path(diretorio).resolve()
    manifesto_path = diretorio / "proveniencia_historico.json"
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    if (not isinstance(manifesto, dict) or manifesto.get("schema_version") != 1
            or manifesto.get("dados_empiricos") is not True
            or manifesto.get("origem") != "arquivo_publico_zenodo"
            or manifesto.get("source_doi") != DOI_FONTE or manifesto.get("source_url") != URL_FONTE
            or manifesto.get("md5_esperado") != MD5_FONTE or manifesto.get("md5_verificado") != MD5_FONTE):
        raise ValueError("Histórico Zenodo não comprova origem empírica da fonte publicada; fixtures não são aceitas.")
    if (manifesto.get("cobertura") != "limite_inferior_observado"
            or manifesto.get("historico_anual_completo") is not False
            or manifesto.get("permite_metricas_dora_anuais") is not False):
        raise ValueError("Histórico deve declarar somente limite inferior observado, sem métricas DORA anuais.")
    janela = manifesto.get("janela_estudo", {})
    if instante(janela.get("inicio")) != inicio or instante(janela.get("fim")) != fim:
        raise ValueError("Janela do histórico não corresponde à configuração da coleta.")
    fonte = manifesto.get("janela_fonte", {})
    inicio_fonte, fim_fonte = instante(INICIO_FONTE), instante(FIM_FONTE)
    if instante(fonte.get("inicio")) != inicio_fonte or instante(fonte.get("fim")) != fim_fonte:
        raise ValueError("Cobertura da fonte histórica diverge da publicação de 2024.")
    observado = manifesto.get("intervalo_observado", {})
    observado_inicio, observado_fim = max(inicio, inicio_fonte), min(fim, fim_fonte)
    if (observado_inicio > observado_fim or instante(observado.get("inicio")) != observado_inicio
            or instante(observado.get("fim")) != observado_fim):
        raise ValueError("Intervalo histórico observado não corresponde à interseção da janela original.")
    fonte_path = Path(manifesto.get("arquivo_fonte", ""))
    if not fonte_path.is_file() or fonte_path.stat().st_size != manifesto.get("arquivo_tamanho"):
        raise ValueError("ZIP original histórico ausente ou com tamanho alterado.")
    md5, hash_fonte = _hashes(fonte_path)
    if md5 != MD5_FONTE or hash_fonte != manifesto.get("arquivo_sha256"):
        raise ValueError("MD5/SHA-256 do ZIP histórico não confere; arquivo parcial ou alterado.")
    saidas = manifesto.get("saidas_sha256", {})
    for nome in ("metadata_repositorios.json", "runs_historicos.json"):
        path = diretorio / nome
        if not path.is_file() or sha256(path) != saidas.get(nome):
            raise ValueError(f"Hash do artefato histórico não confere: {nome}.")
    metadados = json.loads((diretorio / "metadata_repositorios.json").read_text(encoding="utf-8"))
    runs = json.loads((diretorio / "runs_historicos.json").read_text(encoding="utf-8"))
    if not isinstance(metadados, list) or not isinstance(runs, dict):
        raise ValueError("Schema dos artefatos históricos inválido.")
    # Hashes declarados no próprio manifesto não comprovam a derivação.
    # Releia o ZIP de checksum publicado e compare os objetos originais.
    metadados_originais, runs_originais = _ler_fonte(fonte_path, observado_inicio, observado_fim)
    if metadados != metadados_originais or runs != runs_originais:
        raise ValueError("Artefatos históricos divergem do conteúdo original do ZIP verificado.")
    por_id, por_nome, runs_por_id, ids_runs = {}, {}, {}, set()
    for metadata in metadados:
        nome = metadata.get("full_name", "") if isinstance(metadata, dict) else ""
        identificador = metadata.get("repository_id") if isinstance(metadata, dict) else None
        if (not isinstance(nome, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", nome)
                or type(identificador) is not int or identificador <= 0 or identificador in por_id
                or nome.casefold() in por_nome or not isinstance(metadata.get("default_branch"), str)
                or not metadata["default_branch"] or type(metadata.get("stars")) is not int
                or metadata["stars"] < 0 or type(metadata.get("fork")) is not bool
                or type(metadata.get("archived")) is not bool
                or not isinstance(metadata.get("arquivo_info"), str)
                or not isinstance(metadata.get("arquivo_runs"), str)):
            raise ValueError("Metadados históricos inválidos ou duplicados.")
        por_id[identificador], por_nome[nome.casefold()] = metadata, metadata
    for nome, observadas in runs.items():
        metadata = por_nome.get(nome.casefold())
        if metadata is None or not isinstance(observadas, list):
            raise ValueError("Runs históricos sem metadados correspondentes.")
        for run in observadas:
            _validar_run_historico(run, metadata, observado_inicio, observado_fim)
            if run["id"] in ids_runs:
                raise ValueError("ID de run histórico duplicado entre os artefatos.")
            ids_runs.add(run["id"])
        if len(observadas) < 50 or metadata.get("runs_validos_observados") != len(observadas):
            raise ValueError("Contagem histórica não comprova o mínimo ou diverge dos metadados.")
        runs_por_id[metadata["repository_id"]] = observadas
    if (manifesto.get("repositorios_metadata") != len(por_id)
            or manifesto.get("repositorios_com_50_runs_observados") != len(runs_por_id)
            or manifesto.get("runs_observados_exportados") != len(ids_runs)):
        raise ValueError("Contagens do manifesto histórico divergem dos artefatos.")
    referencia = {
        "diretorio": str(diretorio), "source_doi": DOI_FONTE, "source_url": URL_FONTE,
        "arquivo_fonte": str(fonte_path.resolve()), "arquivo_sha256": hash_fonte, "md5_verificado": md5,
        "proveniencia_sha256": sha256(manifesto_path), "saidas_sha256": saidas,
        "cobertura": "limite_inferior_observado", "dados_empiricos": True,
        "historico_anual_completo": False, "permite_metricas_dora_anuais": False,
        "intervalo_observado": observado,
    }
    return HistoricoZenodo(por_id, runs_por_id, referencia)


def _runs_do_arquivo(historico, metadata, inicio, fim):
    if historico is None or metadata["id"] not in historico.runs_por_id:
        return []
    original = historico.metadados_por_id[metadata["id"]]
    selecionados = []
    for run in historico.runs_por_id[metadata["id"]]:
        _validar_run_historico(run, original, inicio, fim)
        if run["head_branch"] == metadata["default_branch"]:
            selecionados.append(run)  # Preserve inclusive nomes antigos, ligados pelo ID GitHub.
    return selecionados


def _fonte_arquivo(historico, metadata, runs):
    original = historico.metadados_por_id[metadata["id"]]
    return {
        "origem": "arquivo_publico_zenodo", "source_doi": historico.referencia["source_doi"],
        "source_url": historico.referencia["source_url"], "repository_id": metadata["id"],
        "full_name_original": original["full_name"], "full_name_atual": metadata["full_name"],
        "arquivo_runs": original["arquivo_runs"],
        "uri": historico.referencia["source_url"] + "#" + quote(original["arquivo_runs"], safe="/"),
        "arquivo_sha256": historico.referencia["arquivo_sha256"],
        "runs_exportados_sha256": historico.referencia["saidas_sha256"]["runs_historicos.json"],
        "runs_snapshot_sha256": _hash_json(runs), "cobertura": "limite_inferior_observado",
        "historico_anual_completo": False, "permite_metricas_dora_anuais": False,
    }


def agora():
    return datetime.now(timezone.utc).isoformat()


def _hash_json(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _json_atomic(path, valor):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario = path.with_name(path.name + ".tmp")
    with temporario.open("w", encoding="utf-8") as stream:
        json.dump(valor, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    temporario.replace(path)


def _csv_atomic(path, rows, campos):
    path = Path(path)
    temporario = path.with_name(path.name + ".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)
    temporario.replace(path)


def _invalidar_resposta(client, endpoint, params=None):
    invalidar = getattr(client, "invalidate_cache", None)
    if callable(invalidar):
        invalidar(endpoint, params=params)


def _workflows(client, nome):
    # Mesmo pedido usado pelo coletor existente, permitindo reutilizar o cache.
    # A primeira página REST usa per_page=30 quando o parâmetro é omitido.
    endpoint, params = f"/repos/{nome}/actions/workflows", None
    status, data, _ = client.request(endpoint, params=params)
    try:
        if status != 200 or not isinstance(data, dict):
            raise RuntimeError(f"Workflows incompletos de {nome} (HTTP {status}).")
        total, workflows = data.get("total_count"), data.get("workflows")
        if (type(total) is not int or total < 0 or not isinstance(workflows, list)
                or len(workflows) != min(total, 30) or data.get("incomplete_results", False)):
            raise ValueError(f"Schema ou tamanho da página de workflows inválido em {nome}.")
        ids = set()
        for workflow in workflows:
            if (not isinstance(workflow, dict) or type(workflow.get("id")) is not int
                    or workflow["id"] <= 0 or workflow["id"] in ids):
                raise ValueError(f"Workflow sem ID válido ou duplicado em {nome}.")
            ids.add(workflow["id"])
    except (ValueError, RuntimeError):
        _invalidar_resposta(client, endpoint, params)
        raise
    return data, params


def _contar_releases(raw_releases, nome, inicio, fim):
    if not isinstance(raw_releases, list):
        raise ValueError(f"Resposta REST de releases deve ser lista em {nome}.")
    ids, tags = set(), set()
    for rel in raw_releases:
        if not isinstance(rel, dict) or type(rel.get("draft")) is not bool or type(rel.get("prerelease")) is not bool:
            raise ValueError(f"Resposta REST de releases incompleta em {nome}.")
        if rel["draft"] or rel["prerelease"]:
            continue
        if not inicio <= instante(rel.get("published_at")) <= fim:
            continue
        identificador, tag = rel.get("id"), rel.get("tag_name")
        if type(identificador) is not int or identificador <= 0 or not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"ID/tag de release inválido em {nome}.")
        url = urlsplit(rel.get("html_url") or "")
        if url.scheme != "https" or url.netloc != "github.com" or not url.path.startswith(f"/{nome}/releases/"):
            raise ValueError(f"Link direto REST da release inválido em {nome}.")
        if identificador in ids or tag in tags:
            raise ValueError(f"Release duplicada (ID/tag) em {nome}.")
        ids.add(identificador)
        tags.add(tag)
    return len(ids)


def _validar_run_observado(run, nome, branch, inicio, fim):
    if (not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0
            or type(run.get("workflow_id")) is not int or run["workflow_id"] <= 0
            or run.get("head_branch") != branch or run.get("event") != "push"
            or not inicio <= instante(run.get("created_at")) <= fim):
        raise ValueError(f"Run observado inválido ou fora do filtro em {nome}.")


def _importar_cache_historico(destino, cache_path, historico):
    historico = Path(historico).resolve()
    registro_path = destino / "cache_historico_importado.json"
    if cache_path.exists():
        if not registro_path.exists():
            raise FileExistsError("Cache de destino já existe sem registro dessa importação; será preservado.")
        registro = json.loads(registro_path.read_text(encoding="utf-8"))
        if (Path(registro.get("arquivo", "")).resolve() != historico
                or registro.get("sha256") != sha256(historico)):
            raise ValueError("Fonte do cache histórico mudou; preserve a coleta e use outro diretório.")
        return
    temporario = cache_path.with_name(cache_path.name + ".importando")
    # O backup inclui transações no WAL; o hash da cópia vincula a imagem
    # efetivamente importada, além do hash do arquivo-fonte.
    with closing(sqlite3.connect(historico.as_uri() + "?mode=ro", uri=True)) as origem:
        with closing(sqlite3.connect(temporario)) as copia:
            origem.backup(copia)
    temporario.replace(cache_path)
    _json_atomic(registro_path, {
        "arquivo": str(historico), "sha256": sha256(historico),
        "copia_importada_sha256": sha256(cache_path), "importado_em": agora(),
    })


def _ler_snapshot(path, hash_snapshot):
    if not path.is_file() or sha256(path) != hash_snapshot:
        raise ValueError(f"Snapshot de coleta alterado ou ausente: {path.name}; checkpoint não confiável.")
    item = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(item, dict) or item.get("origem") != "github_api" or type(item.get("candidate_id")) is not int
            or str(item["candidate_id"]) + ".json" != path.name
            or type(item.get("aprovado")) is not bool):
        raise ValueError("Snapshot não pertence a uma coleta real ou tem schema inválido.")
    item["_snapshot_sha256"] = hash_snapshot
    return item


def _validar_publicacao_final(destino, arquivos, assinatura, inicio, fim, historico=None, *, gravar_checkpoint=True):
    proveniencia = json.loads(arquivos[2].read_text(encoding="utf-8"))
    if any(proveniencia.get(campo) != valor for campo, valor in assinatura.items()):
        raise ValueError("Contrato final não corresponde à janela, critérios e alvo da coleta.")
    validar_proveniencia(proveniencia, arquivos[0], arquivos[1], inicio, fim)
    aprovados = ler_aprovados(arquivos[0])
    if len(aprovados) < assinatura["alvo"] or proveniencia.get("n_aprovados") != len(aprovados):
        raise ValueError("População final não satisfaz o alvo ou diverge da proveniência.")
    releases = json.loads(arquivos[1].read_text(encoding="utf-8"))
    releases_validas(aprovados, releases, inicio, fim)
    evidencias = proveniencia.get("evidencias")
    if not isinstance(evidencias, list) or not evidencias:
        raise ValueError("Proveniência final sem índice de evidências da coleta.")
    resultados, indices = [], {}
    for evidencia in evidencias:
        arquivo = evidencia.get("arquivo", "") if isinstance(evidencia, dict) else ""
        hash_snapshot = evidencia.get("sha256", "") if isinstance(evidencia, dict) else ""
        if (not isinstance(arquivo, str) or not isinstance(hash_snapshot, str)
                or not re.fullmatch(r"qualificacoes/[1-9][0-9]*\.json", arquivo)
                or not re.fullmatch(r"[0-9a-f]{64}", hash_snapshot) or arquivo in indices):
            raise ValueError("Índice final de evidências inválido ou duplicado.")
        indices[arquivo] = hash_snapshot
        resultados.append(_ler_snapshot(destino / arquivo, hash_snapshot))
    fonte_requisicoes = destino / "requisicoes.jsonl"
    if "requisicoes_sha256" in proveniencia:
        if not fonte_requisicoes.is_file() or sha256(fonte_requisicoes) != proveniencia["requisicoes_sha256"]:
            raise ValueError("Registro de requisições alterado ou ausente na publicação final.")
    elif fonte_requisicoes.exists():
        raise ValueError("Proveniência final não vincula o registro de requisições existente.")
    estado_path = destino / "estado.json"
    if estado_path.exists():
        estado = json.loads(estado_path.read_text(encoding="utf-8"))
        for nome, hash_snapshot in estado.get("snapshots", {}).items():
            if indices.get(f"qualificacoes/{nome}") != hash_snapshot:
                raise ValueError("Índice do checkpoint diverge das evidências finais.")
    registros = {}
    for item in resultados:
        if not item["aprovado"]:
            continue
        nome, registro = item["full_name"], item["registro"]
        if nome in registros or item["metadata"].get("private") is not False:
            raise ValueError("Qualificações finais contêm repositório duplicado ou não público.")
        runs = item.get("runs")
        if not isinstance(runs, list):
            raise ValueError(f"Evidência de runs ausente no aprovado {nome}.")
        if registro.get("origem_metricas_estabilidade") == "workflow_runs_arquivo_historico":
            if historico is None:
                raise ValueError(f"Fonte histórica verificada é necessária para auditar {nome}.")
            esperados = _runs_do_arquivo(historico, item["metadata"], inicio, fim)
            if (runs != esperados or item.get("fonte_runs") != _fonte_arquivo(historico, item["metadata"], esperados)
                    or registro.get("escopo_contagem_runs") != "limite_inferior_arquivo_historico"):
                raise ValueError(f"Evidência final diverge da fonte histórica verificada em {nome}.")
        elif (registro.get("origem_metricas_estabilidade") != "workflow_runs"
              or registro.get("escopo_contagem_runs") != "registros_retidos_api"):
            raise ValueError(f"Origem ou cobertura de runs não comprovada em {nome}.")
        ids = set()
        for run in runs:
            _validar_run_observado(run, nome, registro["default_branch"], inicio, fim)
            if run["id"] in ids:
                raise ValueError(f"Evidência de runs duplicada em {nome}.")
            ids.add(run["id"])
        ci = calcular_cfr_ci(runs)
        if ci.sucessos + ci.falhas != registro["total_runs_janela"]:
            raise ValueError(f"Contagem final de runs diverge da evidência em {nome}.")
        criterios = assinatura["criterios"]
        if (registro["stars"] < criterios["min_stars"]
                or registro["total_releases_janela"] < criterios["min_releases"]
                or registro["total_runs_janela"] < criterios["min_workflow_runs"]):
            raise ValueError(f"Qualificação final não comprova os critérios em {nome}.")
        if item.get("releases") != releases.get(nome):
            raise ValueError(f"Releases finais divergem da evidência em {nome}.")
        registros[nome] = registro
    if set(registros) != {row["full_name"] for row in aprovados}:
        raise ValueError("Aprovados finais não correspondem aos snapshots de evidência.")
    for row in aprovados:
        registro = registros[row["full_name"]]
        if any(str(registro.get(campo, "")) != row.get(campo) for campo in CAMPOS_APROVADOS):
            raise ValueError(f"CSV final diverge do snapshot de {row['full_name']}.")
    if gravar_checkpoint:
        return _checkpoint(destino, resultados, assinatura, proveniencia.get("busca"), "completa")
    return {**assinatura, "status": "completa", "n_aprovados": len(aprovados),
            "n_processados": len(resultados), "somente_leitura": True}


def auditar_bundle_final(destino, config_yaml="config.yaml"):
    """Revalide a população final e suas evidências sem rede ou escrita.

    Aprovação comprova os limiares de seleção observados; não transforma
    registros retidos ou arquivos parciais em cobertura histórica anual.
    """
    destino = Path(destino)
    arquivos = [destino / nome for nome in
                ("repositorios_aprovados.csv", "releases.json", "proveniencia.json")]
    faltantes = [path.name for path in arquivos if not path.is_file()]
    if faltantes:
        raise ValueError(f"Bundle final ausente/incompleto em {destino}: {', '.join(faltantes)}; exige >=300 aprovados reais.")
    proveniencia = json.loads(arquivos[2].read_text(encoding="utf-8"))
    config, inicio, fim, criterios, assinatura = _configuracao(config_yaml, proveniencia.get("alvo", 300))
    referencia = proveniencia.get("historico_zenodo")
    historico = None
    if referencia is not None:
        if not isinstance(referencia, dict) or not referencia.get("diretorio"):
            raise ValueError("Fonte histórica sem diretório verificável; recupere os artefatos originais.")
        historico = _carregar_historico_zenodo(referencia["diretorio"], inicio, fim)
        assinatura["historico_zenodo"] = historico.referencia
    return _validar_publicacao_final(destino, arquivos, assinatura, inicio, fim,
                                     historico, gravar_checkpoint=False)


def _preservar_reavaliacao(destino, snapshots):
    if not any(snapshots.glob("*.json")):
        return
    arquivo = destino / "reavaliacoes" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    arquivo.mkdir(parents=True)
    historico = {}
    for path in sorted(snapshots.glob("*.json")):
        if not re.fullmatch(r"[1-9][0-9]*\.json", path.name):
            raise ValueError("Identificador inválido entre snapshots anteriores.")
        shutil.copy2(path, arquivo / path.name)
        historico[path.name] = sha256(path)
    for nome in ("config_coleta.json", "estado.json", "busca.json", "candidatos.json"):
        path = destino / nome
        if path.is_file():
            shutil.copy2(path, arquivo / nome)
    _json_atomic(arquivo / "preservacao.json", {"preservado_em": agora(), "snapshots": historico})
    logger.info("Qualificações anteriores preservadas em %s antes de reavaliar usando as respostas REST.", arquivo)


class ClienteAuditavel(GitHubClient):
    """Guarda hash das respostas e origem HTTP/cache sem registrar credenciais."""

    def __init__(self, auditoria, **kwargs):
        self.auditoria = Path(auditoria)
        super().__init__(**kwargs)

    def request(self, endpoint, params=None, use_cache=None):
        cache_info = None
        if self.use_cache and use_cache is not False:
            key = self._get_cache_key(self._url(endpoint), params)
            if self._read_from_cache(key) is not None:
                with sqlite3.connect(self.cache_db_path) as conn:
                    cache_info = conn.execute(
                        "SELECT timestamp FROM api_cache WHERE cache_key=? AND state='complete'", (key,),
                    ).fetchone()
        registro = {"registrado_em": agora(), "endpoint": endpoint, "params": params,
                    "origem": "cache" if cache_info else "http",
                    "cache_timestamp": cache_info[0] if cache_info else None}
        try:
            status, data, headers = super().request(endpoint, params=params, use_cache=use_cache)
            registro.update(http_status=status, resposta_sha256=_hash_json(data))
            return status, data, headers
        except Exception as exc:
            registro["erro"] = type(exc).__name__
            raise
        finally:
            self.auditoria.parent.mkdir(parents=True, exist_ok=True)
            with self.auditoria.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(registro, ensure_ascii=False) + "\n")


def token_gh():
    """Lê a autenticação existente do gh; o token nunca é escrito ou impresso."""
    try:
        processo = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise ValueError("GitHub CLI indisponível; configure GITHUB_TOKEN.") from exc
    if processo.returncode or not processo.stdout.strip():
        raise ValueError("Autenticação gh indisponível; configure GITHUB_TOKEN ou gh auth login.")
    return processo.stdout.strip()


def _configuracao(config_path, alvo):
    with Path(config_path).open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    inicio = instante(config["window"]["start_date"])
    fim = instante(config["window"]["end_date"])
    if inicio > fim or type(alvo) is not int or alvo < 300:
        raise ValueError("Janela inválida ou alvo inferior a 300 aprovados reais.")
    criterios = {campo: config["criteria"][campo] for campo in
                 ("min_stars", "min_releases", "min_workflow_runs")}
    for campo, minimo in (("min_stars", 1000), ("min_releases", 5), ("min_workflow_runs", 50)):
        if type(criterios[campo]) is not int or criterios[campo] < minimo:
            raise ValueError(f"{campo} deve ser pelo menos {minimo}.")
    assinatura = {"schema_version": 1, "origem": "github_api", "alvo": alvo,
                  "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()}, "criterios": criterios}
    return config, inicio, fim, criterios, assinatura


def _metadata(client, candidate, fim):
    # Estrelas, identidade e default branch são fatos da qualificação atual;
    # um SQLite histórico não pode substituir essa consulta por metadados antigos.
    status, data, _ = client.request(f"/repos/{candidate['full_name']}", use_cache=False)
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"Metadados incompletos de {candidate['full_name']} (HTTP {status}).")
    nome = data.get("full_name", "")
    if (not isinstance(nome, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", nome)
            or type(data.get("id")) is not int or data["id"] != candidate["id"]
            or type(data.get("stargazers_count")) is not int
            or data["stargazers_count"] < 0
            or data.get("private") is not False
            or not isinstance(data.get("default_branch"), str) or not data["default_branch"]
            or instante(data.get("created_at")) > fim):
        raise ValueError(f"Metadados públicos inválidos de {candidate['full_name']}.")
    return data


def _qualificar(client, candidato, inicio, fim, criterios, historico=None):
    metadata = _metadata(client, candidato, fim)
    nome = metadata["full_name"]
    owner, repo = nome.split("/")
    resultado = {"candidate_id": candidato["id"], "full_name": nome, "coletado_em": agora(),
                 "metadata": metadata, "origem": "github_api", "tem_actions": False,
                 "releases_suficientes": False, "aprovado": False, "etapa": "1. Popularidade", "motivo": ""}
    if metadata["stargazers_count"] < criterios["min_stars"]:
        resultado["motivo"] = "menos_de_min_stars"
        return resultado
    coletor = ColetorRuns(client)
    runs_arquivo = _runs_do_arquivo(historico, metadata, inicio, fim)
    n_runs_arquivo = len(runs_arquivo)
    workflows, workflows_params = _workflows(client, nome)
    resultado.update(workflows=workflows, workflows_atuais=workflows, workflows_params=workflows_params,
                     origem_evidencia_actions="workflow_runs_arquivo_historico" if runs_arquivo else "workflows_api_atuais")
    if workflows["total_count"] == 0 and not runs_arquivo:
        resultado.update(etapa="2. GitHub Actions", motivo="evidencia_actions_historicos_insuficiente")
        return resultado
    resultado["tem_actions"] = True
    raw_releases = client.paginate(f"/repos/{nome}/releases", params={"per_page": 100})
    n_releases = _contar_releases(raw_releases, nome, inicio, fim)
    resultado["releases"] = raw_releases
    resultado["total_releases_janela"] = n_releases
    if n_releases < criterios["min_releases"]:
        resultado.update(etapa="3. Releases na janela", motivo="menos_de_5_releases_na_janela")
        return resultado
    resultado["releases_suficientes"] = True
    if n_runs_arquivo >= criterios["min_workflow_runs"]:
        runs = runs_arquivo
        origem_runs, escopo_runs = "workflow_runs_arquivo_historico", "limite_inferior_arquivo_historico"
        resultado["fonte_runs"] = _fonte_arquivo(historico, metadata, runs)
    else:
        # A API só enumera registros ainda disponíveis. Uma contagem baixa não
        # comprova ausência histórica, pois runs antigos podem ter sido removidos.
        resumo_params = {"branch": metadata["default_branch"], "event": "push", "per_page": 1,
                         "created": f"{inicio:%Y-%m-%dT%H:%M:%SZ}..{fim:%Y-%m-%dT%H:%M:%SZ}"}
        status, resumo, _ = client.request(f"/repos/{nome}/actions/runs", params=resumo_params)
        if (status != 200 or not isinstance(resumo, dict) or type(resumo.get("total_count")) is not int
                or resumo["total_count"] < 0 or not isinstance(resumo.get("workflow_runs"), list)
                or len(resumo["workflow_runs"]) != min(resumo["total_count"], 1)
                or resumo.get("incomplete_results", False)):
            _invalidar_resposta(client, f"/repos/{nome}/actions/runs", resumo_params)
            raise RuntimeError(f"Resumo de runs incompleto para {nome} (HTTP {status}).")
        for run in resumo["workflow_runs"]:
            _validar_run_observado(run, nome, metadata["default_branch"], inicio, fim)
        resultado["runs_resumo"] = resumo
        resultado["runs_resumo_params"] = resumo_params
        if resumo["total_count"] < criterios["min_workflow_runs"]:
            resultado.update(etapa="4. Evidência de workflow runs", motivo="evidencia_runs_historicos_insuficiente",
                             runs_disponiveis_api=resumo["total_count"], escopo_contagem_runs="registros_retidos_api")
            return resultado
        runs = coletor.coletar_runs_janela(owner, repo, metadata["default_branch"], inicio, fim)
        resultado["cobertura_runs"] = getattr(coletor, "ultimo_relatorio_cobertura", None)
        origem_runs, escopo_runs = "workflow_runs", "registros_retidos_api"
    ci = calcular_cfr_ci(runs)
    n_runs = ci.sucessos + ci.falhas
    resultado.update(runs=runs, total_runs_janela=n_runs, escopo_contagem_runs=escopo_runs)
    if n_runs < criterios["min_workflow_runs"]:
        resultado.update(etapa="4. Evidência de workflow runs", motivo="evidencia_runs_validos_insuficiente",
                         escopo_contagem_runs=escopo_runs)
        return resultado
    aprovado = dict(full_name=nome, owner=owner, repo=repo, stars=metadata["stargazers_count"],
                    language=metadata.get("language") or "Outra", default_branch=metadata["default_branch"],
                    created_at=metadata["created_at"], total_releases_janela=n_releases, total_runs_janela=n_runs,
                    origem_coleta="github_api", origem_metricas_estabilidade=origem_runs,
                    escopo_contagem_runs=escopo_runs)
    releases_validas([aprovado], {nome: raw_releases}, inicio, fim)
    resultado.update(aprovado=True, registro=aprovado, etapa="5. Aprovado")
    return resultado


def _checkpoint(destino, resultados, assinatura, busca, status, erro=None):
    aprovados = [item["registro"] for item in resultados if item["aprovado"]]
    _csv_atomic(destino / "repositorios_aprovados_parcial.csv", aprovados, CAMPOS_PARCIAIS)
    funil = FunilColeta(target_approved=assinatura["alvo"])
    for item in resultados:
        repo = {"full_name": item["full_name"]}
        funil.registrar_candidato_inicial(repo)
        if item["tem_actions"]:
            funil.aprovar_actions(repo)
        if item["releases_suficientes"]:
            funil.aprovar_releases(repo)
        if item["aprovado"]:
            funil.aprovar_repositorio(repo)
        else:
            detalhes = {key: item[key] for key in ("total_releases_janela", "total_runs_janela", "runs_disponiveis_api", "escopo_contagem_runs") if key in item}
            funil.registrar_descarte(item["full_name"], item["etapa"], item["motivo"], json.dumps(detalhes))
    funil.salvar_relatorios(str(destino / "funil_selecao.csv"), str(destino / "funil_selecao.md"), str(destino / "descartes.csv"))
    estado = {**assinatura, "status": status, "atualizado_em": agora(), "n_processados": len(resultados),
              "n_aprovados": len(aprovados), "busca": busca, "erro": erro,
              "snapshots": {f"{item['candidate_id']}.json": item.get("_snapshot_sha256") or sha256(destino / "qualificacoes" / f"{item['candidate_id']}.json") for item in resultados},
              "pendencia": None if status == "completa" else "Obter pelo menos 300 aprovados reais na janela; não gerar rotulagem com a coleta parcial."}
    _json_atomic(destino / "estado.json", estado)
    # Ordem de aprovação é a ordem de processamento, nunca a ordem alfabética
    # do CSV final. Uma lista vazia informa a pendência, sem fabricar evidência.
    primeiras = [item for item in resultados if item["aprovado"]][:100]
    _json_atomic(destino / "primeiros_100_aprovados.json", {
        "schema_version": 1, "objetivo": 100, "n_comprovados": len(primeiras),
        "completo": len(primeiras) == 100, "janela": assinatura["janela"],
        "ordem": "ordem de aprovação no processamento auditado de candidatos",
        "repositorios": [{"full_name": item["full_name"], "candidate_id": item["candidate_id"],
                           "snapshot": f"qualificacoes/{item['candidate_id']}.json",
                           "sha256": estado["snapshots"][f"{item['candidate_id']}.json"],
                           "total_runs_janela": item["registro"]["total_runs_janela"],
                           "total_releases_janela": item["registro"]["total_releases_janela"],
                           "escopo_contagem_runs": item["registro"]["escopo_contagem_runs"]}
                          for item in primeiras],
        "pendencia": None if len(primeiras) == 100 else "Ainda não há evidência de 100 repositórios aprovados; candidatos processados não são aprovações.",
    })
    return estado


def coletar(config_path="config.yaml", saida="data/coleta_final", alvo=300, limite_candidatos=5000,
            client=None, usar_gh_auth=False, cache_historico=None, reavaliar=False, historico_zenodo=None):
    config, inicio, fim, criterios, assinatura = _configuracao(config_path, alvo)
    historico = _carregar_historico_zenodo(historico_zenodo, inicio, fim) if historico_zenodo else None
    if historico is not None:
        assinatura["historico_zenodo"] = historico.referencia
    if type(limite_candidatos) is not int or limite_candidatos < 1:
        raise ValueError("limite_candidatos deve ser positivo.")
    destino = Path(saida)
    assinatura_path = destino / "config_coleta.json"
    if destino.exists() and not assinatura_path.exists():
        raise FileExistsError(f"Diretório existente não é uma coleta retomável: {destino}.")
    mudou_fonte = False
    if assinatura_path.exists():
        anterior = json.loads(assinatura_path.read_text(encoding="utf-8"))
        if {k: v for k, v in anterior.items() if k != "historico_zenodo"} != {k: v for k, v in assinatura.items() if k != "historico_zenodo"}:
            raise ValueError("Janela/critério/alvo mudou; preserve a coleta anterior e use outro diretório.")
        mudou_fonte = anterior != assinatura
        if mudou_fonte and not reavaliar:
            raise ValueError("Fonte histórica mudou; use --reavaliar para preservar os checkpoints anteriores ou outro diretório.")
    else:
        destino.mkdir(parents=True)
        _json_atomic(assinatura_path, assinatura)
    arquivos_finais = [destino / nome for nome in ("repositorios_aprovados.csv", "releases.json", "proveniencia.json")]
    if all(path.exists() for path in arquivos_finais):
        if reavaliar:
            raise ValueError("População final já publicada; reavalie em outro diretório para preservar o trio final.")
        return _validar_publicacao_final(destino, arquivos_finais, assinatura, inicio, fim, historico)
    # Uma interrupção durante a publicação final deve ser revisada, nunca sobrescrita.
    if any(path.exists() for path in arquivos_finais):
        raise ValueError("Publicação final incompleta; preserve os arquivos e revise antes de retomar.")
    cache_path = destino / "cache/github_cache.db"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_historico:
        _importar_cache_historico(destino, cache_path, cache_historico)
    if client is None:
        api = config.get("api", {})
        if api.get("base_url", "https://api.github.com").rstrip("/") != "https://api.github.com":
            raise ValueError("Coleta real exige API pública https://api.github.com.")
        client = ClienteAuditavel(
            destino / "requisicoes.jsonl", token=token_gh() if usar_gh_auth else None,
            base_url="https://api.github.com", cache_db_path=str(cache_path), verify_ssl=True,
            max_retries=api.get("max_retries", 5), backoff_base_seconds=api.get("backoff_base_seconds", 1.0),
            safety_margin_seconds=api.get("rate_limit_safety_margin_seconds", 5),
        )
    snapshots = destino / "qualificacoes"
    snapshots.mkdir(exist_ok=True)
    resultados = []
    estado_path = destino / "estado.json"
    estado_anterior = json.loads(estado_path.read_text(encoding="utf-8")) if estado_path.exists() else {}
    if estado_anterior:
        contrato_estado = {k: estado_anterior[k] for k in
                          ("schema_version", "origem", "alvo", "janela", "criterios", "historico_zenodo")
                          if k in estado_anterior}
        if contrato_estado != assinatura and not reavaliar:
            raise ValueError("Assinatura do checkpoint diverge da fonte atual; uma reavaliação pode ter sido interrompida. Use --reavaliar.")
    anteriores = estado_anterior.get("snapshots", {})
    for nome_snapshot, hash_snapshot in sorted(anteriores.items()):
        if not re.fullmatch(r"[1-9][0-9]*\.json", nome_snapshot):
            raise ValueError("Identificador inválido no checkpoint da coleta.")
        path = snapshots / nome_snapshot
        resultados.append(_ler_snapshot(path, hash_snapshot))
    if reavaliar:
        _preservar_reavaliacao(destino, snapshots)
        if mudou_fonte:
            _json_atomic(assinatura_path, assinatura)
        resultados = []
        _checkpoint(destino, resultados, assinatura, None, "reavaliando")
    vistos = {item["candidate_id"] for item in resultados}
    busca_info = None
    try:
        candidatos = buscar_candidatos(client, min_stars=criterios["min_stars"], criado_ate=fim.date().isoformat(), max_candidatos=limite_candidatos)
        busca_info = getattr(candidatos, "relatorio", {"max_candidatos": limite_candidatos, "n_candidatos": len(candidatos)})
        _json_atomic(destino / "candidatos.json", candidatos)
        _json_atomic(destino / "busca.json", busca_info)
        for candidato in candidatos:
            if sum(item["aprovado"] for item in resultados) >= alvo:
                break
            if candidato["id"] in vistos:
                continue
            item = _qualificar(client, candidato, inicio, fim, criterios, historico)
            snapshot_path = snapshots / f"{candidato['id']}.json"
            _json_atomic(snapshot_path, item)
            item["_snapshot_sha256"] = sha256(snapshot_path)
            resultados.append(item)
            vistos.add(candidato["id"])
            estado = _checkpoint(destino, resultados, assinatura, busca_info, "em_andamento")
            logger.info("Progresso: %s/%s candidatos; %s/%s aprovados. %s: %s", len(resultados), len(candidatos), estado["n_aprovados"], alvo, item["full_name"], item["motivo"] or "aprovado")
        aprovados = sorted((item["registro"] for item in resultados if item["aprovado"]), key=lambda row: row["full_name"])
        if len(aprovados) < alvo:
            return _checkpoint(destino, resultados, assinatura, busca_info, "insuficiente")
        releases = {item["full_name"]: item["releases"] for item in resultados if item["aprovado"]}
        releases_validas(aprovados, releases, inicio, fim)
        # Somente a população completa recebe nomes consumíveis pelo sorteio.
        with arquivos_finais[0].open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CAMPOS_APROVADOS)
            writer.writeheader()
            writer.writerows(aprovados)
        with arquivos_finais[1].open("x", encoding="utf-8") as stream:
            json.dump(releases, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        proveniencia = {**assinatura, "modo_referencia": False, "fonte_candidatos": "github_search_api", "coletado_em": agora(),
                        "repositorios_sha256": sha256(arquivos_finais[0]), "releases_sha256": sha256(arquivos_finais[1]),
                        "n_aprovados": len(aprovados), "busca": busca_info,
                        "evidencias": [{"arquivo": f"qualificacoes/{item['candidate_id']}.json", "sha256": item["_snapshot_sha256"]} for item in resultados]}
        if (destino / "requisicoes.jsonl").exists():
            proveniencia["requisicoes_sha256"] = sha256(destino / "requisicoes.jsonl")
        with arquivos_finais[2].open("x", encoding="utf-8") as stream:
            json.dump(proveniencia, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return _checkpoint(destino, resultados, assinatura, busca_info, "completa")
    except (Exception, KeyboardInterrupt) as exc:
        _checkpoint(destino, resultados, assinatura, busca_info, "interrompida", f"{type(exc).__name__}: {exc}")
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--saida", default="data/coleta_final")
    parser.add_argument("--alvo", type=int, default=300)
    parser.add_argument("--limite-candidatos", type=int, default=5000)
    parser.add_argument("--usar-gh-auth", action="store_true")
    parser.add_argument("--cache-historico", help="SQLite real previamente coletado; importa uma cópia consistente sem alterar a fonte")
    parser.add_argument("--historico-zenodo", help="Diretório emitido por recuperar_historico.py; verifica fonte, hashes e janela antes de usar runs reais")
    parser.add_argument("--reavaliar", action="store_true", help="Preservar qualificações parciais anteriores e repetir os filtros usando as respostas REST em cache")
    args = parser.parse_args(argv)
    try:
        estado = coletar(args.config, args.saida, args.alvo, args.limite_candidatos,
                        usar_gh_auth=args.usar_gh_auth, cache_historico=args.cache_historico,
                        reavaliar=args.reavaliar, historico_zenodo=args.historico_zenodo)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Coleta interrompida: {exc}. As respostas completas ficam em cache para retomada.", file=sys.stderr)
        return 2
    if estado["status"] != "completa":
        print(f"Coleta real insuficiente: {estado['n_aprovados']}/{estado['alvo']} aprovados em {estado['n_processados']} candidatos consultados. "
              "Os descartes e o cache estão preservados. É necessário obter registros reais da janela, inclusive runs históricos. "
              "Nenhuma amostra-ouro ou classificação humana foi gerada.", file=sys.stderr)
        return 2
    print(f"Coleta real completa: {estado['n_aprovados']} aprovados em {args.saida}; pronta para executar_amostra_ouro.py.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(main())
