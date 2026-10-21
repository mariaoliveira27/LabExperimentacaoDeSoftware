"""Concordância independente e registro explícito das decisões do grupo.

Os kappas descrevem os três julgamentos anteriores à reunião. Nenhuma decisão
de consenso, inclusive uma unanimidade, é inferida ou preenchida pelo código.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence
import unicodedata

import numpy as np
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from rotulagem import CATEGORIAS, JULGAMENTOS, ler_csv, validar_amostra, validar_rotulos


DIMENSOES = ("tipo_projeto", "entrega_real", "corretiva")
CAMPOS_CONSENSO = (
    "dimensao", "full_name", "release_id", "rotulo_consenso", "justificativa",
    "evidencia", "responsaveis", "data_reuniao", "protocolo", "desempate",
)
CAMPOS_DIVERGENCIAS = (
    "dimensao", "full_name", "release_id", "avaliador", "rotulo",
    "justificativa", "evidencia", "html_url", "release_notes_url", "commits_url",
)
Row = Mapping[str, str]
Avaliacoes = Mapping[str, Sequence[Row]]


def _validar_avaliadores(amostra: Sequence[Row], avaliadores: Avaliacoes) -> None:
    validar_amostra(amostra)
    if any(str(row.get(campo, "")).strip() for row in amostra for campo in JULGAMENTOS):
        raise ValueError("A referência comum deve ter julgamentos vazios para preservar o cegamento.")
    if len(avaliadores) != 3 or any(
        not isinstance(nome, str) or not nome.strip() or nome != nome.strip()
        for nome in avaliadores
    ):
        raise ValueError("São necessários exatamente três avaliadores identificados.")
    nomes_normalizados = {unicodedata.normalize("NFKC", nome).casefold() for nome in avaliadores}
    if len(nomes_normalizados) != 3:
        raise ValueError("Os três avaliadores precisam de identificadores distintos, inclusive na caixa Unicode.")
    if len({id(rows) for rows in avaliadores.values()}) != 3:
        raise ValueError("O mesmo conjunto de rótulos não pode representar mais de um avaliador independente.")
    for nome, rotulos in avaliadores.items():
        try:
            validar_rotulos(amostra, rotulos)
        except ValueError as exc:
            raise ValueError(f"Rotulagem independente de {nome}: {exc}") from exc


def _unidades(amostra: Sequence[Row]) -> list[tuple[str, str, str]]:
    """Uma unidade por repositório nas duas primeiras dimensões."""
    repositorios = sorted({row["full_name"].strip() for row in amostra})
    releases = sorted((row["full_name"].strip(), row["release_id"].strip()) for row in amostra)
    return (
        [(dimensao, repo, "") for dimensao in DIMENSOES[:2] for repo in repositorios]
        + [("corretiva", repo, release) for repo, release in releases]
    )


def _indices(avaliadores: Avaliacoes) -> dict[str, dict[tuple[str, str], Row]]:
    return {
        nome: {(row["full_name"].strip(), row["release_id"].strip()): row for row in rows}
        for nome, rows in sorted(avaliadores.items())
    }


def _row_unidade(indice: Mapping[tuple[str, str], Row], repo: str, release: str) -> Row:
    if release:
        return indice[(repo, release)]
    # validar_rotulos já conferiu a constância dos rótulos entre as cinco releases.
    return indice[min(chave for chave in indice if chave[0] == repo)]


def calcular_kappa(rotulos: Sequence[Sequence[str]], categorias: Sequence[str]) -> float | None:
    """Calcula Fleiss para uma matriz n×3; None indica distribuição degenerada.

    Esta função numérica também pode ser usada com pequenas fixtures. Os fluxos
    de preparação e cálculo validam adicionalmente as 60×5 unidades do estudo.
    """
    if not rotulos or len(set(categorias)) != len(categorias) or len(categorias) < 2:
        raise ValueError("São necessárias unidades e pelo menos duas categorias distintas.")
    codigo = {categoria: indice for indice, categoria in enumerate(categorias)}
    if any(len(row) != 3 for row in rotulos):
        raise ValueError("Cada unidade precisa de exatamente três rótulos independentes.")
    try:
        matriz = np.asarray([[codigo[valor] for valor in row] for row in rotulos], dtype=int)
    except KeyError as exc:
        raise ValueError(f"Categoria inválida: {exc.args[0]!r}.") from exc
    tabela, _ = aggregate_raters(matriz, n_cat=len(categorias))
    # Uma única categoria observada produz P_e=1; reportar indefinido, nunca 1.
    with np.errstate(invalid="ignore", divide="ignore"):
        resultado = float(fleiss_kappa(tabela, method="fleiss"))
    return resultado if math.isfinite(resultado) else None


def calcular_kappas(amostra: Sequence[Row], avaliadores: Avaliacoes) -> dict[str, dict]:
    """Kappas separados, sem multiplicar por cinco as decisões de repositório.

    O comando avaliar emite este resultado antes da reunião de consenso. A
    consolidação final requer também as decisões humanas documentadas.
    """
    _validar_avaliadores(amostra, avaliadores)
    indices = _indices(avaliadores)
    resultado = {}
    for dimensao in DIMENSOES:
        unidades = [unidade for unidade in _unidades(amostra) if unidade[0] == dimensao]
        rotulos = [
            [_row_unidade(indice, repo, release)[dimensao].strip() for indice in indices.values()]
            for _, repo, release in unidades
        ]
        categorias = list(CATEGORIAS[dimensao])
        kappa = calcular_kappa(rotulos, categorias)
        resultado[dimensao] = {
            "n": len(unidades),
            "avaliadores": 3,
            "categorias": categorias,
            "categorias_observadas": sorted({valor for row in rotulos for valor in row}),
            "kappa": kappa,
            "status": "calculado" if kappa is not None else "indefinido",
            "motivo": None if kappa is not None else "Uma única categoria observada (P_e = 1).",
        }
    return resultado


def preparar_consenso(amostra: Sequence[Row], avaliadores: Avaliacoes) -> tuple[list[dict], list[dict]]:
    """Retorna divergências e um formulário de consenso inteiramente vazio."""
    _validar_avaliadores(amostra, avaliadores)
    indices = _indices(avaliadores)
    divergencias = []
    for dimensao, repo, release in _unidades(amostra):
        linhas = {nome: _row_unidade(indice, repo, release) for nome, indice in indices.items()}
        if len({row[dimensao].strip() for row in linhas.values()}) > 1:
            for nome, row in linhas.items():
                divergencias.append({
                    "dimensao": dimensao, "full_name": repo, "release_id": release,
                    "avaliador": nome, "rotulo": row[dimensao].strip(),
                    "justificativa": row["justificativa"], "evidencia": row["evidencia"],
                    "html_url": row["html_url"], "release_notes_url": row["release_notes_url"],
                    "commits_url": row["commits_url"],
                })
    return divergencias, formulario_consenso(amostra)


def formulario_consenso(amostra: Sequence[Row]) -> list[dict]:
    """Prepare as 420 decisões vazias sem exigir ou inferir votos humanos.

    Esta preparação estrutural não é um consenso validado. Os comandos de
    arquivo verificam separadamente o manifesto da referência comum antes de
    disponibilizar o formulário para a reunião futura.
    """
    validar_amostra(amostra)
    return [
        {
            **dict.fromkeys(CAMPOS_CONSENSO, ""),
            "dimensao": dimensao, "full_name": repo, "release_id": release,
        }
        for dimensao, repo, release in _unidades(amostra)
    ]


def validar_consenso(amostra: Sequence[Row], avaliadores: Avaliacoes, consenso: Sequence[Row]) -> None:
    """Exige as 420 decisões do grupo, suas fontes e o registro da reunião."""
    _validar_avaliadores(amostra, avaliadores)
    esperadas = set(_unidades(amostra))
    encontradas = set()
    indices = _indices(avaliadores)
    obrigatorios = (
        "rotulo_consenso", "justificativa", "evidencia", "responsaveis", "data_reuniao", "protocolo",
    )
    for numero, row in enumerate(consenso, start=2):
        if any(campo not in row for campo in CAMPOS_CONSENSO):
            raise ValueError(f"Consenso linha {numero}: colunas obrigatórias ausentes.")
        if any(not isinstance(row[campo], str) for campo in CAMPOS_CONSENSO):
            raise ValueError(f"Consenso linha {numero}: valores devem ser texto.")
        chave = (row["dimensao"], row["full_name"], row["release_id"])
        if chave in encontradas:
            raise ValueError(f"Consenso duplicado ou conflitante para {chave}.")
        if chave not in esperadas:
            raise ValueError(f"Unidade de consenso não corresponde à amostra: {chave}.")
        encontradas.add(chave)
        for campo in obrigatorios:
            if not isinstance(row[campo], str) or not row[campo].strip():
                raise ValueError(f"Consenso incompleto para {chave}: {campo} vazio.")
        dimensao, repo, release = chave
        if row["rotulo_consenso"] not in CATEGORIAS[dimensao]:
            raise ValueError(f"Categoria de consenso inválida para {chave}: {row['rotulo_consenso']!r}.")
        participantes = [nome.strip() for nome in row["responsaveis"].split(";")]
        if len(participantes) != 3 or set(participantes) != set(avaliadores):
            raise ValueError(f"Responsáveis de {chave} devem identificar os três avaliadores, separados por ';'.")
        try:
            data = date.fromisoformat(row["data_reuniao"])
            if data.isoformat() != row["data_reuniao"]:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"Data da reunião inválida para {chave}; use YYYY-MM-DD.") from exc
        votos = {_row_unidade(indice, repo, release)[dimensao].strip() for indice in indices.values()}
        if len(votos) == 3 and not row["desempate"].strip():
            raise ValueError(f"Consenso de {chave} exige o registro do desempate: três rótulos distintos.")
    if encontradas != esperadas:
        faltantes = sorted(esperadas - encontradas)
        raise ValueError(f"Consenso incompleto: faltam {len(faltantes)} unidades; primeira: {faltantes[0]}.")


def finalizar(amostra: Sequence[Row], avaliadores: Avaliacoes, consenso: Sequence[Row]) -> dict:
    """Só disponibiliza resultados finais depois das decisões humanas completas."""
    validar_consenso(amostra, avaliadores, consenso)
    frequencias = {dimensao: dict.fromkeys(CATEGORIAS[dimensao], 0) for dimensao in DIMENSOES}
    for row in consenso:
        frequencias[row["dimensao"]][row["rotulo_consenso"]] += 1
    return {
        "status": "avaliacoes_e_consenso_completos",
        "avaliadores": sorted(avaliadores),
        "unidades_consenso": len(consenso),
        "base_kappa": "rotulos_independentes_anteriores_ao_consenso",
        "kappas": calcular_kappas(amostra, avaliadores),
        "frequencias_consenso": frequencias,
    }


def _checar_saidas(saidas: Sequence[Path], entradas: Sequence[Path]) -> None:
    resolvidas = [path.resolve() for path in saidas]
    if len(set(resolvidas)) != len(resolvidas):
        raise ValueError("As saídas devem usar caminhos diferentes.")
    if set(resolvidas) & {path.resolve() for path in entradas}:
        raise ValueError("Uma saída não pode substituir um arquivo de entrada ou de avaliador.")
    for path in saidas:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Saída já existe e será preservada: {path}.")


def _salvar_csv(path: Path, rows: Sequence[Row], campos: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    for comando in ("preparar", "avaliar", "calcular"):
        subparser = comandos.add_parser(comando)
        subparser.add_argument("--amostra", type=Path, required=True)
        subparser.add_argument("--manifesto", type=Path, help="Padrão: selecao.json ao lado da referência comum")
        for nome in ("aulus", "maria", "vinicius"):
            subparser.add_argument(f"--{nome}", type=Path, required=True)
        subparser.add_argument("--consenso", type=Path, required=True)
        if comando in ("preparar", "avaliar"):
            subparser.add_argument("--divergencias", type=Path, required=True)
        if comando in ("avaliar", "calcular"):
            subparser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        humanos = {nome: getattr(args, nome) for nome in ("aulus", "maria", "vinicius")}
        paths = list(humanos.values())
        if (len({path.resolve() for path in paths}) != 3
                or any(esquerda.samefile(direita) for indice, esquerda in enumerate(paths)
                       for direita in paths[indice + 1:])):
            raise ValueError("Informe três arquivos distintos de rotulagem independente.")
        from gerar_amostra_rotulagem import validar_referencia
        manifesto_path = args.manifesto or args.amostra.parent / "selecao.json"
        origem_referencia = validar_referencia(args.amostra, manifesto_path)
        entradas = [args.amostra, *humanos.values()]
        amostra = ler_csv(args.amostra)
        avaliadores = {nome: ler_csv(path) for nome, path in humanos.items()}
        if args.comando in ("preparar", "avaliar"):
            saidas = [args.divergencias, args.consenso]
            if args.comando == "avaliar":
                saidas.append(args.saida)
            _checar_saidas(saidas, [*entradas, manifesto_path])
            divergencias, consenso = preparar_consenso(amostra, avaliadores)
            resultado = None
            if args.comando == "avaliar":
                resultado = {
                    "status": "rotulos_independentes_completos_aguardando_consenso",
                    "base_kappa": "rotulos_independentes_anteriores_ao_consenso",
                    "avaliadores": sorted(avaliadores),
                    "origem_referencia": origem_referencia,
                    "kappas": calcular_kappas(amostra, avaliadores),
                    "arquivos_fontes": [{"arquivo": str(path), "sha256": _sha256(path)}
                                         for path in [*entradas, manifesto_path]],
                }
            _salvar_csv(args.divergencias, divergencias, CAMPOS_DIVERGENCIAS)
            _salvar_csv(args.consenso, consenso, CAMPOS_CONSENSO)
            if resultado is not None:
                args.saida.parent.mkdir(parents=True, exist_ok=True)
                with args.saida.open("x", encoding="utf-8") as arquivo:
                    json.dump(resultado, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
                    arquivo.write("\n")
            print(f"Relatório de divergências: {args.divergencias}. Consenso: {len(consenso)} decisões vazias em {args.consenso}.")
        else:
            entradas.append(args.consenso)
            _checar_saidas([args.saida], [*entradas, manifesto_path])
            resultado = finalizar(amostra, avaliadores, ler_csv(args.consenso))
            resultado["origem_referencia"] = origem_referencia
            resultado["arquivos_fontes"] = [
                {"arquivo": str(path), "sha256": _sha256(path)} for path in entradas
            ]
            args.saida.parent.mkdir(parents=True, exist_ok=True)
            with args.saida.open("x", encoding="utf-8") as arquivo:
                json.dump(resultado, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
                arquivo.write("\n")
            print(f"Kappas dos rótulos independentes e frequências do consenso: {args.saida}.")
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        parser.exit(2, f"Não foi possível {args.comando}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
