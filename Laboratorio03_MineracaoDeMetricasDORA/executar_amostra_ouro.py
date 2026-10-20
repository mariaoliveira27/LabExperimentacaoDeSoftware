"""Prepare a amostra comum e o CSV independente de Áulus a partir da coleta real.

Este fluxo usa um bundle existente, sem consultar a rede, classificar releases
ou registrar consenso. Arquivos e seleções existentes são preservados. Uma
execução interrompida após o sorteio pode ser continuada por rotulagem.py.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import yaml

from gerar_amostra_rotulagem import gerar_amostra
from rotulagem import JULGAMENTOS, gerar_rotulos, ler_csv, validar_rotulos


def _preflight(saida, rotulos):
    """Valide os destinos antes de gerar qualquer seleção ou arquivo humano."""
    if rotulos.name.casefold() in ("rotulos_vinicius.csv", "rotulos_maria.csv"):
        raise ValueError(f"O fluxo de Áulus não pode gravar {rotulos.name.lower()}.")
    for destino in (rotulos, saida):
        if destino.exists() or destino.is_symlink():
            raise FileExistsError(
                f"Destino preservado: {destino} já existe. "
                "Use outro destino ou continue a seleção existente com rotulagem.py."
            )
        for pai in destino.parents:
            if pai.exists() and not pai.is_dir():
                raise NotADirectoryError(f"Diretório de destino inválido: {pai}.")
    pasta = saida.resolve()
    arquivo = rotulos.resolve()
    reservados = {
        pasta / "amostra_comum.csv", pasta / "evidencias_releases.json",
        pasta / "selecao.json",
    }
    if arquivo == pasta or arquivo in pasta.parents or arquivo in reservados:
        raise ValueError("O CSV de Áulus deve ter caminho diferente dos artefatos da seleção.")


def executar(config, coleta, saida, rotulos):
    """Gere a referência e valide o rascunho de Áulus, sem decisões humanas.

    A validação da população e da proveniência é feita pelo gerador do sorteio.
    Em caso de erro posterior ao sorteio, a seleção permanece no disco para que
    seja inspecionada e continuada, sem substituir um CSV humano existente.
    """
    config, coleta, saida, rotulos = map(Path, (config, coleta, saida, rotulos))
    _preflight(saida, rotulos)
    faltantes = [nome for nome in ("repositorios_aprovados.csv", "releases.json", "proveniencia.json")
                 if not (coleta / nome).is_file()]
    if faltantes:
        detalhe = ""
        estado_path = coleta / "estado.json"
        if estado_path.is_file():
            estado = json.loads(estado_path.read_text(encoding="utf-8"))
            detalhe = f" Estado da coleta: {estado.get('n_aprovados', 'não informado')} aprovados."
        raise ValueError(
            "São necessários pelo menos 300 repositórios aprovados por coleta real, "
            "as releases e a proveniência completas antes de preparar a rotulagem. "
            f"Faltam em {coleta}: {', '.join(faltantes)}.{detalhe}"
        )
    manifesto = gerar_amostra(
        coleta / "repositorios_aprovados.csv",
        coleta / "releases.json",
        coleta / "proveniencia.json",
        config,
        saida,
    )
    comum = saida / "amostra_comum.csv"
    referencia = ler_csv(comum)
    if any(row.get(campo, "").strip() for row in referencia for campo in JULGAMENTOS):
        raise ValueError("A referência comum deve conter apenas julgamentos humanos vazios.")
    rotulos.parent.mkdir(parents=True, exist_ok=True)
    gerar_rotulos(comum, rotulos)
    validar_rotulos(referencia, ler_csv(rotulos), permitir_vazios=True)
    return {
        "manifesto": manifesto,
        "amostra": str(comum),
        "rotulos": str(rotulos),
        "status": "aguardando_rotulagem_humana",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--coleta", type=Path, default=Path("data/coleta_final"))
    parser.add_argument("--saida", type=Path, default=Path("data/amostra_ouro"))
    parser.add_argument("--rotulos", type=Path, default=Path("rotulos_aulus.csv"))
    args = parser.parse_args(argv)
    try:
        resultado = executar(args.config, args.coleta, args.saida, args.rotulos)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, yaml.YAMLError) as exc:
        print(f"Preparação interrompida: {exc}", file=sys.stderr)
        return 2
    manifesto = resultado["manifesto"]
    print(
        f"Referência comum: {resultado['amostra']} "
        f"({manifesto['n_repositorios']} repositórios × "
        f"{manifesto['releases_por_repositorio']} releases; "
        f"random_state={manifesto['random_state']})."
    )
    print(
        f"CSV independente: {resultado['rotulos']}; rascunho validado, "
        "todos os julgamentos vazios. Issue #62 pendente de julgamento humano de Áulus."
    )
    print("Os arquivos humanos de Maria e Vinicius e o consenso do grupo continuam pendentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
