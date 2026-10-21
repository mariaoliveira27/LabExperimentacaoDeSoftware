"""Sorteia a referência para avaliação humana; nunca inventa releases ou rótulos.

Entradas e comandos: ROTULAGEM_AULUS.md. A coleta final é uma entrada deste
script; os dados de demonstração da Sprint 01 não são uma amostra empírica.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import pandas as pd
import yaml


SEMENTE = 42
MINIMO_APROVADOS = 300
N_REPOSITORIOS = 60
RELEASES_POR_REPOSITORIO = 5
METADADOS = (
    "full_name", "release_id", "published_at", "tag_name", "html_url",
    "release_notes_url", "commits_url", "previous_tag",
)
JULGAMENTOS = ("tipo_projeto", "entrega_real", "corretiva", "justificativa", "evidencia")


def sha256(arquivo):
    digest = hashlib.sha256()
    with Path(arquivo).open("rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def instante(valor):
    try:
        data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if data.tzinfo is None:
            raise ValueError("sem fuso horário")
        return data.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"Data ISO 8601 com fuso horário necessária: {valor!r}") from exc


def ler_aprovados(caminho):
    with Path(caminho).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Cabeçalho de aprovados ausente ou duplicado.")
        rows = list(reader)
    nomes = [row.get("full_name", "") for row in rows]
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", nome) for nome in nomes):
        raise ValueError("Identificador full_name inválido nos aprovados.")
    if len(set(nome.casefold() for nome in nomes)) != len(nomes):
        raise ValueError("Repositórios duplicados no CSV de aprovados.")
    if len(rows) < MINIMO_APROVADOS:
        raise ValueError(
            f"Amostra final insuficiente: {len(rows)} repositórios; são necessários pelo menos "
            "300 aprovados por coleta real da API do GitHub, com releases e proveniência "
            "preservadas. Nenhuma amostra ou planilha humana foi gerada. Não use "
            "seed_data.py nem --reference-mode para completar os dados."
        )
    for row in rows:
        if row.get("origem_coleta") != "github_api" or row.get("origem_metricas_estabilidade") == "referencia_simulada":
            raise ValueError(f"Origem real não comprovada para {row['full_name']}: exige origem_coleta=github_api.")
        for campo, minimo in (("stars", 1000), ("total_releases_janela", 5), ("total_runs_janela", 50)):
            try:
                valor = int(row[campo])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Contagem real inválida: {row['full_name']} / {campo}.") from exc
            if valor < minimo:
                raise ValueError(f"Repositório não aprovado: {row['full_name']} / {campo} < {minimo}.")
    return sorted(rows, key=lambda row: row["full_name"])


def validar_proveniencia(proveniencia, repos_csv, releases_json, inicio, fim):
    if not isinstance(proveniencia, dict) or proveniencia.get("schema_version") != 1:
        raise ValueError("Proveniência requer schema_version=1.")
    if (proveniencia.get("origem") != "github_api"
            or proveniencia.get("modo_referencia") is not False
            or proveniencia.get("fonte_candidatos") != "github_search_api"):
        raise ValueError("Proveniência deve identificar coleta real e candidatos da API; referência/seed não aceita.")
    instante(proveniencia.get("coletado_em"))
    janela = proveniencia.get("janela", {})
    if not isinstance(janela, dict) or instante(janela.get("inicio")) != inicio or instante(janela.get("fim")) != fim:
        raise ValueError("Janela da coleta não corresponde à configuração do sorteio.")
    for campo, arquivo in (("repositorios_sha256", repos_csv), ("releases_sha256", releases_json)):
        if proveniencia.get(campo) != sha256(arquivo):
            raise ValueError(f"Hash de proveniência não confere: {campo}.")
    criterios = proveniencia.get("criterios", {})
    for campo, minimo in (("min_stars", 1000), ("min_releases", 5), ("min_workflow_runs", 50)):
        valor = criterios.get(campo) if isinstance(criterios, dict) else None
        if not isinstance(valor, int) or isinstance(valor, bool) or valor < minimo:
            raise ValueError(f"Critério da coleta inválido: {campo} deve ser >= {minimo}.")


def releases_validas(aprovados, releases, inicio, fim):
    """Valida toda a população antes do sorteio, sem substituir repos insuficientes."""
    if not isinstance(releases, dict):
        raise ValueError("releases.json deve mapear full_name para listas REST de releases.")
    resultado, ids_globais = {}, set()
    for repo in aprovados:
        nome = repo["full_name"]
        registros = releases.get(nome)
        if not isinstance(registros, list):
            raise ValueError(f"Releases reais ausentes: {nome}.")
        validas, tags = [], set()
        for rel in registros:
            if not isinstance(rel, dict):
                raise ValueError(f"Registro de release inválido em {nome}.")
            if type(rel.get("draft")) is not bool or type(rel.get("prerelease")) is not bool:
                raise ValueError(f"Flags REST draft/prerelease ausentes em {nome}.")
            if rel["draft"] or rel["prerelease"]:
                continue
            data = instante(rel.get("published_at"))
            if not inicio <= data <= fim:
                continue
            release_id, tag = rel.get("id"), rel.get("tag_name")
            if type(release_id) is not int or release_id <= 0 or not isinstance(tag, str) or not tag.strip():
                raise ValueError(f"ID/tag de release inválido em {nome}.")
            if release_id in ids_globais or tag in tags:
                raise ValueError(f"Release duplicada (ID/tag): {nome} / {release_id}.")
            url = urlsplit(rel.get("html_url") or "")
            if url.scheme != "https" or url.netloc != "github.com" or not url.path.startswith(f"/{nome}/releases/"):
                raise ValueError(f"Link direto REST da release ausente ou inválido: {nome} / {release_id}.")
            ids_globais.add(release_id)
            tags.add(tag)
            validas.append(rel)
        validas.sort(key=lambda rel: (instante(rel["published_at"]), rel["id"]))
        if len(validas) < RELEASES_POR_REPOSITORIO:
            raise ValueError(f"Amostra final inválida: {nome} tem {len(validas)} releases válidas; mínimo 5.")
        if len(validas) != int(repo["total_releases_janela"]):
            raise ValueError(f"Contagem de releases difere do CSV de aprovados: {nome}.")
        resultado[nome] = validas
    return resultado


def sortear(aprovados, releases, inicio, fim):
    validas = releases_validas(aprovados, releases, inicio, fim)
    selecionados = pd.DataFrame(aprovados).sort_values("full_name").sample(n=N_REPOSITORIOS, random_state=SEMENTE)
    linhas, evidencias = [], {}
    for nome in sorted(selecionados["full_name"].tolist()):
        populacao = validas[nome]
        indices = sorted(pd.DataFrame(populacao).sample(n=RELEASES_POR_REPOSITORIO, random_state=SEMENTE).index)
        evidencias[nome] = []
        for indice in indices:
            rel = populacao[indice]
            anterior = populacao[indice - 1]["tag_name"] if indice else ""
            base_url = f"https://github.com/{nome}"
            commits_url = (f"{base_url}/compare/{quote(anterior, safe='')}...{quote(rel['tag_name'], safe='')}"
                           if anterior else f"{base_url}/commits/{quote(rel['tag_name'], safe='')}")
            linha = dict(full_name=nome, release_id=str(rel["id"]), published_at=rel["published_at"],
                         tag_name=rel["tag_name"], html_url=rel["html_url"], release_notes_url=rel["html_url"],
                         commits_url=commits_url, previous_tag=anterior)
            linha.update({campo: "" for campo in JULGAMENTOS})
            linhas.append(linha)
            # Somente conteúdo original das releases, sem mensagens resumidas nem heurísticas.
            evidencias[nome].append({campo: rel.get(campo) for campo in
                                    ("id", "tag_name", "name", "published_at", "html_url", "body", "draft", "prerelease")})
    return linhas, evidencias


def validar_coleta_final(repos_csv, releases_json, proveniencia_json, config_yaml):
    """Reaproveite a auditoria dos snapshots finais, sem rede ou escrita.

    Marcadores origem_coleta=github_api e hashes autoconsistentes sozinhos não
    comprovam qualificação. Os três arquivos precisam pertencer ao mesmo bundle
    publicado pelo coletor, com os snapshots correspondentes.
    """
    from coleta_amostra_real import auditar_bundle_final

    repos_csv, releases_json, proveniencia_json = map(
        Path, (repos_csv, releases_json, proveniencia_json),
    )
    pasta = repos_csv.resolve().parent
    esperados = ("repositorios_aprovados.csv", "releases.json", "proveniencia.json")
    for arquivo, nome in zip((repos_csv, releases_json, proveniencia_json), esperados):
        if arquivo.resolve() != pasta / nome:
            raise ValueError("Entradas devem pertencer ao mesmo bundle final publicado pelo coletor.")
    return auditar_bundle_final(pasta, config_yaml)


def validar_referencia(amostra_csv, manifesto_json=None):
    """Vincule a referência ao bundle auditado e reproduza o sorteio original.

    Usado pelas CLIs humanas: um CSV estrutural de exemplo não pode virar uma
    referência oficial. O algoritmo numérico permanece disponível para fixtures.
    """
    from rotulagem import ler_csv, validar_amostra

    amostra_csv = Path(amostra_csv)
    manifesto_json = Path(manifesto_json) if manifesto_json else amostra_csv.parent / "selecao.json"
    manifesto = json.loads(manifesto_json.read_text(encoding="utf-8"))
    if isinstance(manifesto, dict) and manifesto.get("tipo_fonte") == "csv_main_adotado":
        from amostra_csv_main import validar_referencia_fornecida
        return validar_referencia_fornecida(amostra_csv, manifesto_json)
    contrato = {"schema_version": 1, "random_state": SEMENTE,
                "n_repositorios": N_REPOSITORIOS, "n_releases": N_REPOSITORIOS * RELEASES_POR_REPOSITORIO,
                "releases_por_repositorio": RELEASES_POR_REPOSITORIO}
    if not isinstance(manifesto, dict) or any(manifesto.get(campo) != valor for campo, valor in contrato.items()):
        raise ValueError("Manifesto de seleção ausente ou incompatível com o protocolo 60×5.")
    if manifesto.get("amostra_comum_sha256") != sha256(amostra_csv):
        raise ValueError("Referência comum diverge do hash preservado no manifesto.")
    entradas = manifesto.get("entradas")
    if not isinstance(entradas, dict):
        raise ValueError("Manifesto sem as entradas auditáveis da seleção.")
    caminhos = {}
    for nome in ("aprovados", "releases", "proveniencia", "config"):
        registro = entradas.get(nome)
        if not isinstance(registro, dict) or not isinstance(registro.get("arquivo"), str):
            raise ValueError(f"Entrada da seleção ausente ou inválida: {nome}.")
        caminho = Path(registro["arquivo"])
        if registro.get("sha256") != sha256(caminho):
            raise ValueError(f"Entrada original da seleção alterada: {nome}.")
        caminhos[nome] = caminho
    validar_coleta_final(caminhos["aprovados"], caminhos["releases"], caminhos["proveniencia"], caminhos["config"])
    aprovados = ler_aprovados(caminhos["aprovados"])
    if manifesto.get("n_populacao") != len(aprovados):
        raise ValueError("População do manifesto difere da coleta final auditada.")
    config = yaml.safe_load(caminhos["config"].read_text(encoding="utf-8"))
    inicio, fim = (instante(config["window"][campo]) for campo in ("start_date", "end_date"))
    releases = json.loads(caminhos["releases"].read_text(encoding="utf-8"))
    esperadas, evidencias = sortear(aprovados, releases, inicio, fim)
    rows = ler_csv(amostra_csv)
    validar_amostra(rows)
    if rows != esperadas:
        raise ValueError("Referência comum não reproduz a seleção determinística do bundle final.")
    evidencias_path = manifesto_json.parent / "evidencias_releases.json"
    if (manifesto.get("evidencias_releases_sha256") != sha256(evidencias_path)
            or json.loads(evidencias_path.read_text(encoding="utf-8")) != evidencias):
        raise ValueError("Evidências de releases divergentes da seleção original.")
    return manifesto


def gerar_amostra(repos_csv, releases_json, proveniencia_json, config_yaml, saida):
    aprovados = ler_aprovados(repos_csv)  # Falha antes de qualquer geração ou fallback.
    with Path(config_yaml).open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    inicio = instante(config["window"]["start_date"])
    fim = instante(config["window"]["end_date"])
    if inicio > fim:
        raise ValueError("Janela invertida.")
    with Path(proveniencia_json).open(encoding="utf-8") as stream:
        proveniencia = json.load(stream)
    validar_proveniencia(proveniencia, repos_csv, releases_json, inicio, fim)
    validar_coleta_final(repos_csv, releases_json, proveniencia_json, config_yaml)
    with Path(releases_json).open(encoding="utf-8") as stream:
        releases = json.load(stream)
    linhas, evidencias = sortear(aprovados, releases, inicio, fim)
    destino = Path(saida)
    if destino.exists():
        raise FileExistsError(f"Seleção preservada: {destino} já existe. Use outro diretório para uma nova execução.")
    destino.mkdir(parents=True)
    csv_path = destino / "amostra_comum.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=METADADOS + JULGAMENTOS)
        writer.writeheader()
        writer.writerows(linhas)
    evidencias_path = destino / "evidencias_releases.json"
    with evidencias_path.open("x", encoding="utf-8") as stream:
        json.dump(evidencias, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    manifesto = {
        "schema_version": 1, "status": "aguardando_rotulagem_humana", "random_state": SEMENTE,
        "algoritmo": "pandas.DataFrame.sample sem reposição; população ordenada por full_name; releases ordenadas por published_at UTC/id; random_state=42 em cada sorteio",
        "pandas_version": pd.__version__, "python_version": sys.version.split()[0],
        "n_populacao": len(aprovados), "n_repositorios": N_REPOSITORIOS,
        "releases_por_repositorio": RELEASES_POR_REPOSITORIO, "n_releases": len(linhas),
        "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "entradas": {nome: {"arquivo": str(Path(path).resolve()), "sha256": sha256(path)} for nome, path in
                     (("aprovados", repos_csv), ("releases", releases_json), ("proveniencia", proveniencia_json), ("config", config_yaml))},
        "selecao": [{"full_name": row["full_name"], "release_id": row["release_id"], "tag_name": row["tag_name"]} for row in linhas],
        "amostra_comum_sha256": sha256(csv_path), "evidencias_releases_sha256": sha256(evidencias_path),
    }
    with (destino / "selecao.json").open("x", encoding="utf-8") as stream:
        json.dump(manifesto, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return manifesto


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--repos", default="data/output/repositorios_aprovados.csv")
    parser.add_argument("--releases", default="data/coleta/releases.json")
    parser.add_argument("--proveniencia", default="data/coleta/proveniencia.json")
    parser.add_argument("--saida", default="data/amostra_ouro")
    args = parser.parse_args(argv)
    try:
        manifesto = gerar_amostra(args.repos, args.releases, args.proveniencia, args.config, args.saida)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Geração interrompida: {exc}", file=sys.stderr)
        return 2
    print(f"Referência comum: {manifesto['n_repositorios']} repositórios / {manifesto['n_releases']} releases em {args.saida}. Julgamentos vazios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
