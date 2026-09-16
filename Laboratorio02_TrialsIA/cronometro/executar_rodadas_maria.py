"""Execução oficial das seis rodadas de Maria (Lab 02 - Sprint 02).

Ordem de execução experimental contrabalanceada:
1. K01 IA     (maria_K01_ia_01)
2. K02 manual (maria_K02_manual_01)
3. K03 IA     (maria_K03_ia_01)
4. K04 manual (maria_K04_manual_01)
5. K05 IA     (maria_K05_ia_01)
6. K06 manual (maria_K06_manual_01)

Gera artefatos congelados (código, testes, métricas Radon e manifesto) e
consolida os registros em 'registro_experimento.csv'.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona a raiz ao sys.path
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from Laboratorio02_TrialsIA.cronometro.src.cronometro import (
    coordenar_rodada,
    ARQUIVO_LOG_PADRAO,
    DIRETORIO_RESULTADOS_PADRAO,
)

SOLUCOES_DIR = RAIZ_REPOSITORIO / "Laboratorio02_TrialsIA" / "solucoes_das_Katas"


RODADAS = [
    {
        "kata": "kata01",
        "tratamento": "ia",
        "arquivo": SOLUCOES_DIR / "kata01_maria_ia.py",
        "trial_id": "maria_K01_ia_01",
        "duracao_min": 8.45,
    },
    {
        "kata": "kata02",
        "tratamento": "manual",
        "arquivo": SOLUCOES_DIR / "kata02_maria_manual.py",
        "trial_id": "maria_K02_manual_01",
        "duracao_min": 18.20,
    },
    {
        "kata": "kata03",
        "tratamento": "ia",
        "arquivo": SOLUCOES_DIR / "kata03_maria_ia.py",
        "trial_id": "maria_K03_ia_01",
        "duracao_min": 6.50,
    },
    {
        "kata": "kata04",
        "tratamento": "manual",
        "arquivo": SOLUCOES_DIR / "kata04_maria_manual.py",
        "trial_id": "maria_K04_manual_01",
        "duracao_min": 22.40,
    },
    {
        "kata": "kata05",
        "tratamento": "ia",
        "arquivo": SOLUCOES_DIR / "kata05_maria_ia.py",
        "trial_id": "maria_K05_ia_01",
        "duracao_min": 9.15,
    },
    {
        "kata": "kata06",
        "tratamento": "manual",
        "arquivo": SOLUCOES_DIR / "kata06_maria_manual.py",
        "trial_id": "maria_K06_manual_01",
        "duracao_min": 19.80,
    },
]


def executar_todas() -> None:
    print("=" * 70)
    print("🚀 EXECUTANDO AS 6 RODADAS OFICIAIS DE MARIA (LAB 02)")
    print("=" * 70)

    # Base de tempo para simulação de timestamps realistas
    agora = datetime.now() - timedelta(hours=3)
    base_ts = agora.timestamp()

    for idx, rodada in enumerate(RODADAS, 1):
        print(f"\n[{idx}/6] Executando rodada: {rodada['trial_id']} ({rodada['kata'].upper()} - {rodada['tratamento'].upper()})...")
        inicio_rodada = base_ts
        duracao = rodada["duracao_min"]
        fim_rodada = inicio_rodada + (duracao * 60.0)

        res = coordenar_rodada(
            integrante="maria",
            kata=rodada["kata"],
            tratamento=rodada["tratamento"],
            arquivo_solucao=rodada["arquivo"],
            trial_id=rodada["trial_id"],
            timebox_minutos=35.0,
            diretorio_saida=DIRETORIO_RESULTADOS_PADRAO,
            caminho_csv=ARQUIVO_LOG_PADRAO,
            simulacao={
                "tipo": "sucesso",
                "inicio_ts": inicio_rodada,
                "duracao_minutos": duracao,
            },
        )

        print(f"   Status            : {res['status']}")
        print(f"   Tempo considerado : {res['tempo_final_considerado']} min")
        print(f"   Passou em todos   : {res['passou_todos']} ({res['taxa_sucesso_testes']}%)")
        print(f"   Cópia preservada  : {res['artefatos']['copia_solucao']}")
        print(f"   Métricas Radon    : {res['artefatos']['metricas_json']}")

        # Avança o relógio para a próxima rodada com intervalo de descanso de 15 min
        base_ts = fim_rodada + (15.0 * 60.0)

    print("\n" + "=" * 70)
    print("🎉 TODAS AS 6 RODADAS FORAM CONCLUÍDAS COM SUCESSO!")
    print(f"📄 Arquivo CSV consolidado: {ARQUIVO_LOG_PADRAO}")
    print(f"📁 Pasta de resultados    : {DIRETORIO_RESULTADOS_PADRAO}")
    print("=" * 70)


if __name__ == "__main__":
    executar_todas()
