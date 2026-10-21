"""Prepare o formulário vazio e confira a prontidão dos três arquivos humanos.

Sem os três arquivos completos, grava somente estado e formulário. Quando os
três contratos forem atendidos, calcula Fleiss pré-consenso e divergências em
um diretório novo. Nenhuma decisão de consenso é preenchida automaticamente.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Sequence

from metricas import concordancia
from rotulagem import JULGAMENTOS, METADADOS, ler_csv, validar_rotulos


AVALIADORES = ("aulus", "maria", "vinicius")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inspecionar(path, amostra):
    """Descreva apenas schema, hashes e contagens; nunca exporte votos."""
    estado = {"arquivo": str(path), "existe": path.is_file(), "completo": False}
    if not path.is_file():
        estado["status"] = "arquivo_ausente"
        return estado
    estado["sha256"] = _sha256(path)
    try:
        rows = ler_csv(path)
        with path.open(encoding="utf-8-sig", newline="") as arquivo:
            campos = csv.DictReader(arquivo).fieldnames or []
        estado.update(
            n_linhas=len(rows),
            colunas=campos,
            faltam_colunas=sorted(set(METADADOS + JULGAMENTOS) - set(campos)),
            campos_vazios={
                campo: sum(not row.get(campo, "").strip() for row in rows)
                for campo in METADADOS + JULGAMENTOS
            },
        )
        validar_rotulos(amostra, rows, permitir_vazios=True)
        if any(estado["campos_vazios"][campo] for campo in JULGAMENTOS):
            estado["status"] = "aguardando_preenchimento_humano"
        else:
            validar_rotulos(amostra, rows)
            estado.update(status="contrato_completo", completo=True)
    except (ValueError, OSError, KeyError, TypeError, csv.Error, UnicodeError):
        # Os erros detalhados do validador podem incluir um voto inválido. O
        # estado público preserva o cegamento e apresenta somente o contrato.
        estado["status"] = "contrato_invalido"
        estado["motivo"] = (
            "Verifique encoding UTF-8, schema, unidades, metadados, categorias "
            "permitidas e coerência dos julgamentos por repositório."
        )
    return estado


def executar(amostra_path, humanos, saida, consenso_formulario=None, manifesto=None):
    """Prepare destinos novos; arquivos de avaliadores nunca são alterados."""
    from gerar_amostra_rotulagem import validar_referencia

    amostra_path, saida = Path(amostra_path), Path(saida)
    humanos = {nome: Path(humanos[nome]) for nome in AVALIADORES}
    manifesto = Path(manifesto) if manifesto else amostra_path.parent / "selecao.json"
    formulario_path = Path(consenso_formulario) if consenso_formulario else saida / "consenso_formulario.csv"
    if saida.exists() or saida.is_symlink():
        raise FileExistsError(f"Diretório já existe e será preservado: {saida}.")
    paths = list(humanos.values())
    if len({path.resolve() for path in paths}) != 3 or any(
        esquerda.exists() and direita.exists() and esquerda.samefile(direita)
        for indice, esquerda in enumerate(paths) for direita in paths[indice + 1:]
    ):
        raise ValueError("Informe três caminhos de arquivos humanos distintos, sem aliases.")
    # Validar referência e todos os caminhos antes de criar qualquer saída.
    origem = validar_referencia(amostra_path, manifesto)
    amostra = ler_csv(amostra_path)
    formulario = concordancia.formulario_consenso(amostra)
    entradas = [amostra_path, manifesto, *paths]
    saidas = [
        saida / "estado.json", formulario_path, saida / "kappas_pre_consenso.json",
        saida / "divergencias.csv", saida / "consenso.csv",
    ]
    concordancia._checar_saidas(saidas, entradas)
    if any(saida.resolve() == path.resolve() or saida.resolve() in path.resolve().parents for path in entradas):
        raise ValueError("O diretório novo de saídas não pode conter arquivos de entrada existentes.")
    inspecoes = {nome: _inspecionar(path, amostra) for nome, path in humanos.items()}
    completos = all(item["completo"] for item in inspecoes.values())
    invalidos = any(item["status"] == "contrato_invalido" for item in inspecoes.values())
    estado = {
        "status": "contrato_invalido" if invalidos else "aguardando_tres_avaliacoes_humanas_completas",
        "origem_referencia": origem,
        "referencia": {"arquivo": str(amostra_path), "sha256": _sha256(amostra_path)},
        "manifesto": {"arquivo": str(manifesto), "sha256": _sha256(manifesto)},
        "avaliacoes": inspecoes,
        "avaliacoes_completas": sum(item["completo"] for item in inspecoes.values()),
        "independencia_humana": (
            "Caminhos distintos e contratos completos não comprovam independência; "
            "cada pessoa deve avaliar sem consultar votos alheios e preservar seu arquivo pré-consenso."
        ),
        "formulario": {
            "arquivo": str(formulario_path), "n_decisoes": len(formulario),
            "unidades": {"tipo_projeto": 60, "entrega_real": 60, "corretiva": 300},
            "decisoes_preenchidas": 0, "consenso_validado": False,
        },
        "kappa_calculado": False,
        "divergencias_geradas": False,
        "decisoes_de_reuniao_registradas": False,
    }
    saida.mkdir(parents=True)
    concordancia._salvar_csv(formulario_path, formulario, concordancia.CAMPOS_CONSENSO)
    if completos:
        concordancia.main([
            "avaliar", "--amostra", str(amostra_path), "--manifesto", str(manifesto),
            *[valor for nome, path in humanos.items() for valor in (f"--{nome}", str(path))],
            "--consenso", str(saida / "consenso.csv"),
            "--divergencias", str(saida / "divergencias.csv"),
            "--saida", str(saida / "kappas_pre_consenso.json"),
        ])
        estado.update(
            status="rotulos_completos_kappa_pre_consenso_calculado_aguardando_reuniao",
            kappa_calculado=True, divergencias_geradas=True,
        )
    with (saida / "estado.json").open("x", encoding="utf-8") as arquivo:
        json.dump(estado, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
        arquivo.write("\n")
    return estado


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amostra", type=Path, required=True)
    parser.add_argument("--manifesto", type=Path)
    for nome in AVALIADORES:
        parser.add_argument(f"--{nome}", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True, help="Diretório novo para preservar cada execução")
    parser.add_argument("--consenso-formulario", type=Path)
    args = parser.parse_args(argv)
    try:
        estado = executar(
            args.amostra, {nome: getattr(args, nome) for nome in AVALIADORES},
            args.saida, args.consenso_formulario, args.manifesto,
        )
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        parser.exit(2, f"Preparação interrompida: {exc}\n")
    print(
        f"Estado: {estado['status']}; {estado['avaliacoes_completas']}/3 contratos humanos completos. "
        f"Formulário: {estado['formulario']['n_decisoes']} decisões vazias. "
        f"Evidência e prontidão em {args.saida / 'estado.json'}."
    )
    return 2 if estado["status"] == "contrato_invalido" else 0


if __name__ == "__main__":
    raise SystemExit(main())
