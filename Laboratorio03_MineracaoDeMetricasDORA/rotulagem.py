"""Preparação e validação da rotulagem humana independente da amostra-ouro.

O módulo não classifica projetos ou releases. Seus arquivos de saída contêm
somente a referência comum e campos de julgamento vazios. A validação completa
é pré-requisito para o cálculo de concordância, mas não substitui a avaliação
humana das notas e dos commits.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


METADADOS = (
    "full_name", "release_id", "published_at", "tag_name", "html_url",
    "release_notes_url", "commits_url", "previous_tag",
)
JULGAMENTOS = (
    "tipo_projeto", "entrega_real", "corretiva", "justificativa", "evidencia",
)
CATEGORIAS = {
    "tipo_projeto": (
        "biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro",
    ),
    "entrega_real": ("sim", "não", "incerto"),
    "corretiva": ("sim", "não"),
}
NUM_REPOSITORIOS = 60
RELEASES_POR_REPOSITORIO = 5
NUM_RELEASES = NUM_REPOSITORIOS * RELEASES_POR_REPOSITORIO


def ler_csv(path):
    """Leia UTF-8 (com ou sem BOM), rejeitando linhas e cabeçalhos ambíguos."""
    with Path(path).open(encoding="utf-8-sig", newline="") as arquivo:
        reader = csv.DictReader(arquivo)
        campos = reader.fieldnames
        if not campos:
            raise ValueError(f"CSV sem cabeçalho: {path}.")
        if len(campos) != len(set(campos)) or any(not campo for campo in campos):
            raise ValueError(f"CSV com colunas vazias ou duplicadas: {path}.")
        rows = []
        for numero, row in enumerate(reader, start=2):
            if None in row or any(valor is None for valor in row.values()):
                raise ValueError(f"CSV malformado na linha {numero}: {path}.")
            rows.append(row)
    return rows


def _texto(row, campo):
    valor = row.get(campo)
    return valor.strip() if isinstance(valor, str) else ""


def _validar_colunas(rows, campos, origem):
    for numero, row in enumerate(rows, start=2):
        faltam = [campo for campo in campos if campo not in row]
        if faltam:
            raise ValueError(
                f"{origem}, linha {numero}: colunas ausentes: {', '.join(faltam)}."
            )


def _chave(row):
    return _texto(row, "full_name"), _texto(row, "release_id")


def validar_amostra(rows):
    """Exija uma referência de 60 repositórios e cinco releases por repositório.

    A origem empírica e o sorteio são verificados pelo gerador da amostra. Este
    validador verifica seu contrato estrutural, seus identificadores e links.
    """
    if len(rows) != NUM_RELEASES:
        raise ValueError(
            f"Amostra requer {NUM_RELEASES} releases; recebidas {len(rows)}."
        )
    _validar_colunas(rows, METADADOS, "Amostra")
    chaves = set()
    releases = set()
    nomes_repositorios = {}
    contagens = Counter()
    for numero, row in enumerate(rows, start=2):
        repo, release_id = _chave(row)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repo):
            raise ValueError(f"Amostra, linha {numero}: full_name inválido: {repo!r}.")
        repo_canonico = repo.casefold()
        if repo_canonico in nomes_repositorios and nomes_repositorios[repo_canonico] != repo:
            raise ValueError(
                f"Amostra contém variantes de caixa do mesmo full_name: "
                f"{nomes_repositorios[repo_canonico]!r} e {repo!r}. "
                "Preserve um único identificador de repositório na referência comum."
            )
        nomes_repositorios[repo_canonico] = repo
        if not re.fullmatch(r"[1-9][0-9]*", release_id):
            raise ValueError(
                f"Amostra, linha {numero}: release_id deve ser inteiro positivo: "
                f"{release_id!r}."
            )
        if (repo, release_id) in chaves or release_id in releases:
            raise ValueError(
                f"Amostra contém release duplicada: {repo}, {release_id}."
            )
        chaves.add((repo, release_id))
        releases.add(release_id)
        # O GitHub identifica o mesmo repositório independentemente da caixa.
        contagens[repo_canonico] += 1
        data = _texto(row, "published_at")
        try:
            instante = datetime.fromisoformat(data.replace("Z", "+00:00"))
            if instante.tzinfo is None:
                raise ValueError("Fuso horário ausente.")
        except ValueError as exc:
            raise ValueError(
                f"Amostra, linha {numero}: published_at inválido: {data!r}."
            ) from exc
        if not _texto(row, "tag_name"):
            raise ValueError(f"Amostra, linha {numero}: tag_name ausente.")
        for campo in ("html_url", "release_notes_url", "commits_url"):
            link = urlparse(_texto(row, campo))
            prefixos = (
                (f"/{repo}/compare/", f"/{repo}/commits/")
                if campo == "commits_url" else (f"/{repo}/releases/",)
            )
            if (
                link.scheme != "https" or link.netloc != "github.com"
                or not any(link.path.startswith(prefixo) for prefixo in prefixos)
            ):
                raise ValueError(f"Amostra, linha {numero}: {campo} inválido.")
    if len(contagens) != NUM_REPOSITORIOS:
        raise ValueError(
            f"Amostra requer {NUM_REPOSITORIOS} repositórios; "
            f"recebidos {len(contagens)}."
        )
    incorretos = sorted(
        repo for repo, quantidade in contagens.items()
        if quantidade != RELEASES_POR_REPOSITORIO
    )
    if incorretos:
        raise ValueError(
            f"Amostra requer {RELEASES_POR_REPOSITORIO} releases por repositório; "
            f"contagem incorreta: {', '.join(incorretos)}."
        )


def validar_rotulos(amostra_rows, rotulos_rows, permitir_vazios=False):
    """Valide as unidades, metadados e decisões de um único avaliador.

    No rascunho, campos vazios são permitidos; valores já preenchidos continuam
    sujeitos às mesmas categorias e à consistência por repositório. Na versão
    completa, justificativa e evidência são exigidas em cada release.
    """
    validar_amostra(amostra_rows)
    _validar_colunas(rotulos_rows, METADADOS + JULGAMENTOS, "Rótulos")
    referencia = {_chave(row): row for row in amostra_rows}
    avaliados = {}
    for row in rotulos_rows:
        chave = _chave(row)
        if chave in avaliados:
            raise ValueError(f"Rótulos contêm unidade duplicada: {chave}.")
        avaliados[chave] = row
    ausentes = set(referencia) - set(avaliados)
    extras = set(avaliados) - set(referencia)
    if ausentes or extras:
        raise ValueError(
            f"Rótulos não correspondem à amostra: {len(ausentes)} unidades "
            f"ausentes e {len(extras)} unidades extras."
        )
    decisoes_repo = defaultdict(lambda: defaultdict(set))
    for chave, row in avaliados.items():
        for campo in METADADOS:
            if row[campo] != referencia[chave][campo]:
                raise ValueError(
                    f"Metadado {campo} alterado na unidade {chave}. "
                    "Preserve a referência comum."
                )
        for campo in JULGAMENTOS:
            valor = _texto(row, campo)
            if not valor:
                if permitir_vazios:
                    continue
                raise ValueError(f"Rótulo ausente: {campo}, unidade {chave}.")
            if campo in CATEGORIAS and valor not in CATEGORIAS[campo]:
                permitidas = ", ".join(CATEGORIAS[campo])
                raise ValueError(
                    f"Categoria inválida em {campo}, unidade {chave}: {valor!r}. "
                    f"Permitidas: {permitidas}."
                )
            if campo in ("tipo_projeto", "entrega_real"):
                decisoes_repo[chave[0]][campo].add(valor)
    for repo, decisoes in decisoes_repo.items():
        for campo, valores in decisoes.items():
            if len(valores) > 1:
                raise ValueError(
                    f"Decisões inconsistentes de {campo} no repositório {repo}; "
                    "repita uma única decisão nas cinco releases."
                )


def gerar_rotulos(amostra_path, saida_path):
    """Crie um arquivo independente vazio, sem copiar julgamentos ou heurísticas."""
    rows = ler_csv(amostra_path)
    validar_amostra(rows)
    saida = Path(saida_path)
    if saida.name.casefold() == "rotulos_vinicius.csv":
        raise ValueError("A geração de Áulus não pode gravar rotulos_vinicius.csv.")
    # Modo exclusivo: impede qualquer substituição de julgamentos existentes,
    # inclusive quando o arquivo foi criado entre a leitura e esta abertura.
    with saida.open("x", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=METADADOS + JULGAMENTOS)
        writer.writeheader()
        for row in rows:
            independente = {campo: row[campo] for campo in METADADOS}
            independente.update({campo: "" for campo in JULGAMENTOS})
            writer.writerow(independente)
    return saida


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    gerar = comandos.add_parser("gerar", help="Gerar CSV independente sem julgamentos")
    gerar.add_argument("--amostra", required=True, type=Path)
    gerar.add_argument("--saida", type=Path, default=Path("rotulos_aulus.csv"))
    validar = comandos.add_parser("validar", help="Validar decisões contra a amostra")
    validar.add_argument("--amostra", required=True, type=Path)
    validar.add_argument("--rotulos", required=True, type=Path)
    validar.add_argument("--rascunho", action="store_true", help="Permitir campos vazios")
    args = parser.parse_args(argv)
    try:
        if args.comando == "gerar":
            saida = gerar_rotulos(args.amostra, args.saida)
            print(
                f"Criado {saida}: 300 releases, 60 repositórios, julgamentos vazios. "
                "Issue 02 pendente de julgamento humano independente de Áulus."
            )
        else:
            validar_rotulos(
                ler_csv(args.amostra), ler_csv(args.rotulos), args.rascunho,
            )
            if args.rascunho:
                print("Rascunho válido. Julgamentos humanos ainda podem estar pendentes.")
            else:
                print("Rotulagem completa e válida: 60 repositórios e 300 releases.")
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
