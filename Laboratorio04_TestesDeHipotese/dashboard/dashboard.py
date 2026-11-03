"""Entrypoint para o Dashboard do Lab 04 (Lab04S01).
Permite executar a geração de dados e iniciar o dashboard diretamente.
"""

from __future__ import annotations
import sys
from gerar_dashboard import main

if __name__ == "__main__":
    # Se nenhum argumento for passado, gera os dados e inicia o servidor por padrão
    if len(sys.argv) == 1:
        sys.argv.append("--servir")
    main()
