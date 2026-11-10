"""Entrypoint para o Dashboard do Lab 04 (Entrega Final).
Permite executar a geração de dados analíticos e iniciar o servidor web local diretamente.
"""

from __future__ import annotations
import sys
from gerar_dashboard import main

if __name__ == "__main__":
    # Se nenhum argumento for passado, gera os dados analíticos e inicia o servidor HTTP por padrão
    if len(sys.argv) == 1:
        sys.argv.append("--servir")
    main()
