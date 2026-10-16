"""Guarda offline para fontes históricas que não sustentam a coleta planejada.

A guarda não valida julgamentos nem comprova ausência histórica de CI. Sua
série de zeros vem do checkpoint/CSV ou dos resultados fornecidos, sem reler
os snapshots. A fonte histórica recebida deve ter sido validada pelo chamador.
"""

from __future__ import annotations

from contextlib import closing
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urlsplit


MOTIVO = "evidencia_runs_historicos_insuficiente"
INICIO_GUARDA = datetime(2026, 10, 1, tzinfo=timezone.utc)
NOME_REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+")


class HistoricoIndisponivelError(RuntimeError):
    def __init__(self, diagnostico):
        self.diagnostico = diagnostico
        super().__init__(
            "Coleta histórica inconclusiva: a série de consultas vazias e as fontes locais "
            "conhecidas não sustentam o alvo. Obtenha um cache histórico original ou "
            "autorização do professor para revisar a janela/duração; zero registros "
            "disponíveis não comprova ausência histórica de CI."
        )


def _instante(valor):
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if not isinstance(valor, datetime) or valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError("A guarda exige timestamps ISO 8601 com fuso horário.")
    return valor.astimezone(timezone.utc)


def _inteiro(valor, campo):
    if type(valor) is not int or valor < 0:
        raise ValueError(f"{campo} deve ser um inteiro não negativo.")
    return valor


def _nome(valor):
    if not isinstance(valor, str) or not NOME_REPO.fullmatch(valor):
        raise ValueError("Identidade de repositório inválida na evidência local.")
    return valor.casefold()


def _sha(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def _hashes_ledger(destino):
    return {nome: _sha((destino / nome).read_bytes()) for nome in ("estado.json", "descartes.csv")
            if (destino / nome).is_file()}


def _serie_resultados(resultados):
    zeros = aprovados = processados = 0
    nomes, ids = set(), set()
    for item in resultados:
        if not isinstance(item, dict) or type(item.get("aprovado")) is not bool:
            raise ValueError("Resultado local sem status de aprovação explícito.")
        nome = _nome(item.get("full_name"))
        if nome in nomes:
            raise ValueError("Resultados locais contêm repositórios duplicados.")
        nomes.add(nome)
        if "candidate_id" in item:
            identificador = _inteiro(item["candidate_id"], "candidate_id")
            if identificador == 0 or identificador in ids:
                raise ValueError("Resultados locais contêm IDs inválidos ou duplicados.")
            ids.add(identificador)
        processados += 1
        aprovados += item["aprovado"]
        if item.get("motivo") == MOTIVO:
            n = _inteiro(item.get("runs_disponiveis_api"), "runs_disponiveis_api")
            zeros += n == 0
    return zeros, aprovados, processados, "resultados_fornecidos"


def _serie_ledger(destino, inicio, fim):
    estado_path = destino / "estado.json"
    if not estado_path.is_file():
        return 0, 0, 0, "sem_checkpoint"
    estado = json.loads(estado_path.read_bytes())
    if not isinstance(estado, dict):
        raise ValueError("Checkpoint local deve ser um objeto JSON.")
    if "janela" in estado:
        janela = estado["janela"]
        if (not isinstance(janela, dict) or _instante(janela.get("inicio")) != inicio
                or _instante(janela.get("fim")) != fim):
            raise ValueError("Janela do checkpoint diverge da guarda de viabilidade.")
    processados = _inteiro(estado.get("n_processados"), "n_processados")
    aprovados = _inteiro(estado.get("n_aprovados"), "n_aprovados")
    if aprovados > processados:
        raise ValueError("Checkpoint tem mais aprovados do que processados.")
    if aprovados or processados == 0:
        return 0, aprovados, processados, "checkpoint_descartes"
    conteudo = (destino / "descartes.csv").read_bytes().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(conteudo, newline=""))
    if not reader.fieldnames or not {"full_name", "motivo", "detalhes"}.issubset(reader.fieldnames):
        raise ValueError("CSV de descartes não tem as colunas requeridas.")
    zeros = linhas = 0
    nomes = set()
    for linha in reader:
        nome = _nome(linha.get("full_name"))
        if nome in nomes:
            raise ValueError("CSV de descartes contém repositórios duplicados.")
        nomes.add(nome)
        detalhes = json.loads(linha["detalhes"])
        if not isinstance(detalhes, dict):
            raise ValueError("Detalhes do descarte devem ser objeto JSON.")
        if linha["motivo"] == MOTIVO:
            zeros += _inteiro(detalhes.get("runs_disponiveis_api"), "runs_disponiveis_api") == 0
        linhas += 1
    if linhas != processados - aprovados:
        raise ValueError("Quantidade de descartes diverge do checkpoint; não há série consistente.")
    return zeros, aprovados, processados, "checkpoint_descartes"


def _adicionar_alias(aliases, nome, identificador):
    nome = _nome(nome)
    if nome in aliases and aliases[nome] != identificador:
        raise ValueError("Identidades GitHub conflitantes na evidência local.")
    aliases[nome] = identificador


def _identidade_url(url):
    path = unquote(urlsplit(url).path).rstrip("/")
    if not path.endswith("/actions/runs"):
        return None
    match = re.fullmatch(r"/repos/([^/]+/[^/]+)/actions/runs", path)
    if match:
        return "nome", _nome(match[1])
    match = re.fullmatch(r"/repositories/([1-9][0-9]*)/actions/runs", path)
    if match:
        return "id", int(match[1])
    raise ValueError("URL de workflow runs sem identidade verificável de repositório.")


def _identidade_run(run, identidade_url, aliases):
    repository = run.get("repository")
    if repository is not None and not isinstance(repository, dict):
        raise ValueError("repository inválido no cache de workflow runs.")
    repository = repository or {}
    identificador = repository.get("id")
    nome = repository.get("full_name")
    if identificador is not None:
        _inteiro(identificador, "repository.id")
        if identificador == 0:
            raise ValueError("repository.id deve ser positivo.")
        if nome is not None:
            _adicionar_alias(aliases, nome, identificador)
        if identidade_url[0] == "id" and identidade_url[1] != identificador:
            raise ValueError("ID do run diverge da URL de sua evidência.")
        if identidade_url[0] == "nome":
            _adicionar_alias(aliases, identidade_url[1], identificador)
        return "id", identificador
    if nome is not None:
        return "nome", _nome(nome)
    return identidade_url


def _fontes_potenciais(destino, inicio, fim, historico):
    potenciais, aliases = set(), {}
    n_historico = n_linhas_cache = n_runs_janela_cache = 0
    if historico is not None:
        for identificador, metadata in getattr(historico, "metadados_por_id", {}).items():
            if type(identificador) is not int or identificador <= 0 or not isinstance(metadata, dict):
                raise ValueError("Metadados da fonte histórica inválidos.")
            _adicionar_alias(aliases, metadata.get("full_name"), identificador)
        runs_por_id = historico.runs_por_id
        if not isinstance(runs_por_id, dict):
            raise ValueError("Fonte histórica sem índice de runs por ID.")
        for identificador, runs in runs_por_id.items():
            if type(identificador) is not int or identificador <= 0 or not isinstance(runs, list):
                raise ValueError("Índice de runs históricos inválido.")
            dentro = False
            for run in runs:
                if not isinstance(run, dict):
                    raise ValueError("Run histórico inválido.")
                criada = _instante(run.get("created_at"))
                dentro = dentro or inicio <= criada <= fim
            if dentro:
                potenciais.add(("id", identificador))
                n_historico += 1
    cache_path = destino / "cache/github_cache.db"
    if cache_path.exists():
        with closing(sqlite3.connect(cache_path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            cursor = conn.execute(
                "SELECT url,cache_key,response_json FROM api_cache WHERE status_code=200 AND state='complete' "
                "AND (url LIKE '%/actions/runs%' OR cache_key LIKE '%/actions/runs%')"
            )
            for url, cache_key, raw in cursor:
                identidade = _identidade_url(url) or _identidade_url(cache_key)
                if identidade is None:
                    continue
                payload = json.loads(raw)
                if (not isinstance(payload, dict) or type(payload.get("total_count")) is not int
                        or payload["total_count"] < 0 or not isinstance(payload.get("workflow_runs"), list)
                        or payload.get("incomplete_results") is True):
                    raise ValueError("Schema incompleto no cache de workflow runs.")
                if len(payload["workflow_runs"]) > payload["total_count"]:
                    raise ValueError("Contagem contraditória no cache de workflow runs.")
                n_linhas_cache += 1
                for run in payload["workflow_runs"]:
                    if not isinstance(run, dict):
                        raise ValueError("Run inválido no cache local.")
                    if inicio <= _instante(run.get("created_at")) <= fim:
                        potenciais.add(_identidade_run(run, identidade, aliases))
                        n_runs_janela_cache += 1
    normalizados = {(tipo, valor) if tipo == "id" or valor not in aliases else ("id", aliases[valor])
                    for tipo, valor in potenciais}
    return normalizados, {"repositorios_historico_com_run_na_janela": n_historico,
                          "paginas_runs_cache_examinadas": n_linhas_cache,
                          "runs_na_janela_encontrados_no_cache": n_runs_janela_cache,
                          "cache_acesso": "SQLite mode=ro; páginas individuais; sem hash do banco"}


def verificar_viabilidade(destino, inicio, fim, alvo, historico=None, resultados=None, agora=None):
    """Lance erro apenas na combinação conservadora; caso contrário retorne None.

    Potencial significa existir ao menos um run na janela, de qualquer evento,
    branch ou conclusão. Não comprova cinquenta runs nem elegibilidade. Esta
    guarda não escreve arquivos e nunca devolve status de coleta completa.
    """
    inicio, fim = _instante(inicio), _instante(fim)
    agora = _instante(agora) if agora is not None else datetime.now(timezone.utc)
    if inicio > fim or type(alvo) is not int or alvo <= 0:
        raise ValueError("Janela ou alvo inválido para a guarda de viabilidade.")
    if agora < INICIO_GUARDA or fim >= agora - timedelta(days=90):
        return None
    destino = Path(destino)
    zeros, aprovados, processados, origem = (_serie_resultados(resultados) if resultados is not None
                                           else _serie_ledger(destino, inicio, fim))
    if aprovados or zeros < 100:
        return None
    potenciais, fontes = _fontes_potenciais(destino, inicio, fim, historico)
    if len(potenciais) >= alvo:
        return None
    diagnostico = {
        "status": "historico_indisponivel", "verificado_em": agora.isoformat(),
        "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "n_consultas_historicas_total_zero": zeros, "n_processados": processados,
        "n_aprovados": aprovados, "n_fontes_potenciais": len(potenciais), "alvo": alvo,
        "origem_serie_zero": origem,
        "validacao_empirica_serie_nesta_guarda": False,
        "ressalva_serie": "Contagem do ledger/resultados; esta guarda não revalida respostas nem hashes dos snapshots.",
        "fontes_potenciais": fontes,
        "identidades_potenciais": [{"tipo": tipo, "valor": valor} for tipo, valor in sorted(potenciais)],
        "evidencias_sha256": _hashes_ledger(destino),
        "interpretacao": "A fonte conhecida não sustenta o alvo sob a série de respostas vazias. Não é prova de ausência histórica de CI; potenciais são um teto generoso apenas das fontes locais examinadas, não da população GitHub.",
        "dica": "Obter cache histórico original verificável ou autorização do professor para revisar explicitamente janela/duração; não completar a população com dados de referência.",
    }
    raise HistoricoIndisponivelError(diagnostico)
