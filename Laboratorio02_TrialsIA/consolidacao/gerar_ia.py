"""Worker encerrável pelo cronômetro; reutiliza exclusivamente o cliente do grupo."""

import argparse

from Laboratorio02_TrialsIA.casos_de_teste.katas_Gemini import gerar_solucao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("enunciado")
    parser.add_argument("saida")
    args = parser.parse_args()
    from pathlib import Path
    gerar_solucao(Path(args.enunciado).read_text(encoding="utf-8-sig"), args.saida)


if __name__ == "__main__":
    main()
