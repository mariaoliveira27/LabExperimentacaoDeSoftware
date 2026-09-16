"""Script de Demonstração e Validação dos 3 Cenários da Rodada (Issue #30).

Gera registros automatizados comprovando o cumprimento dos requisitos:
1. SUCESSO: Solução passa em 100% dos testes dentro do timebox (tempo real registrado).
2. LIMITE ATINGIDO: Tempo estoura 35 minutos sem aprovação (censurado em 35 min).
3. INTERRUPÇÃO: Parada antecipada sem sucesso (tempo real registrado e motivo gravado, SEM virar 35 min).

Valida a integridade dos artefatos salvos: cópias de solução, relatórios do executor do Vinícius (#34),
métricas estruturais do Radon do Áulus (#31) e integridade do CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Adiciona a raiz do repositório ao sys.path
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from Laboratorio02_TrialsIA.cronometro.src.cronometro import (
    coordenar_rodada,
    gerar_trial_id,
)

DIRETORIO_ATUAL = Path(__file__).resolve().parent
EXEMPLOS_DIR = DIRETORIO_ATUAL / "exemplos"
SOLUCAO_SUCESSO = EXEMPLOS_DIR / "solucao_demo_kata01.py"
SOLUCAO_FALHA = EXEMPLOS_DIR / "solucao_demo_incompleta.py"


def executar_demonstracao(pasta_saida: Path, arquivo_csv: Path) -> bool:
    print("=" * 70)
    print("[TESTE] INICIANDO DEMONSTRACAO COMPLETA DO COORDENADOR DE RODADAS (#30)")
    print("=" * 70)

    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    if arquivo_csv.exists():
        arquivo_csv.unlink()

    # -------------------------------------------------------------
    # CENÁRIO 1: SUCESSO (Time-to-green dentro do prazo)
    # -------------------------------------------------------------
    print("\n>> [Cenario 1/3] Executando rodada com SUCESSO funcional...")
    trial_id_1 = "maria_K01_ia_01"
    res1 = coordenar_rodada(
        integrante="maria",
        kata="kata01",
        tratamento="ia",
        arquivo_solucao=SOLUCAO_SUCESSO,
        trial_id=trial_id_1,
        diretorio_saida=pasta_saida,
        caminho_csv=arquivo_csv,
        simulacao={
            "tipo": "sucesso",
            "duracao_minutos": 7.35,
        },
    )

    assert res1["status"] == "SUCESSO", f"Esperado SUCESSO, obtido {res1['status']}"
    assert res1["passou_todos"] is True, "Deveria ter passado em todos os testes"
    assert res1["tempo_final_considerado"] == 7.35, f"Tempo considerado incorreto: {res1['tempo_final_considerado']}"
    assert res1["dado_censurado"] is False, "Dado não deve ser censurado no sucesso"
    print(f"   [OK] Cenario 1 Aprovado: {trial_id_1} finalizou com SUCESSO em {res1['tempo_final_considerado']} min.")

    # -------------------------------------------------------------
    # CENÁRIO 2: LIMITE ATINGIDO (Estouro de 35 minutos)
    # -------------------------------------------------------------
    print("\n>> [Cenario 2/3] Executando rodada com LIMITE ATINGIDO (35 min)...")
    trial_id_2 = "maria_K01_manual_01"
    res2 = coordenar_rodada(
        integrante="maria",
        kata="kata01",
        tratamento="manual",
        arquivo_solucao=SOLUCAO_FALHA,
        trial_id=trial_id_2,
        diretorio_saida=pasta_saida,
        caminho_csv=arquivo_csv,
        simulacao={
            "tipo": "limite",
            "duracao_minutos": 35.0,
            "motivo": "Timebox maximo de 35 minutos atingido sem passar em todos os testes",
        },
    )

    assert res2["status"] == "LIMITE_ATINGIDO", f"Esperado LIMITE_ATINGIDO, obtido {res2['status']}"
    assert res2["passou_todos"] is False, "Não deveria ter passado em todos os testes"
    assert res2["tempo_final_considerado"] == 35.0, f"Tempo considerado incorreto: {res2['tempo_final_considerado']}"
    assert res2["dado_censurado"] is True, "Dado deve ser censurado ao atingir limite"
    print(f"   [OK] Cenario 2 Aprovado: {trial_id_2} finalizou com LIMITE_ATINGIDO (censurado em 35.0 min).")

    # -------------------------------------------------------------
    # CENÁRIO 3: INTERRUPÇÃO (Parada antecipada com duração real e motivo)
    # -------------------------------------------------------------
    print("\n>> [Cenario 3/3] Executando rodada com INTERRUPCAO antecipada...")
    trial_id_3 = "maria_K01_ia_02"
    motivo_teste = "Desistencia antecipada por bloqueio na recursao do numero real"
    res3 = coordenar_rodada(
        integrante="maria",
        kata="kata01",
        tratamento="ia",
        arquivo_solucao=SOLUCAO_FALHA,
        trial_id=trial_id_3,
        diretorio_saida=pasta_saida,
        caminho_csv=arquivo_csv,
        simulacao={
            "tipo": "interrupcao",
            "duracao_minutos": 13.50,
            "motivo": motivo_teste,
        },
    )

    # Verificação da regra crítica: NÃO pode ser 35 minutos!
    assert res3["status"] == "INTERRUPCAO", f"Esperado INTERRUPCAO, obtido {res3['status']}"
    assert res3["tempo_final_considerado"] == 13.50, (
        f"ERRO CRITICO: Parada antecipada NAO pode virar 35 min! Obtido: {res3['tempo_final_considerado']}"
    )
    assert res3["dado_censurado"] is False, "Interrupcao nao e censura de timebox"
    assert res3["motivo_interrupcao"] == motivo_teste, f"Motivo incorreto: {res3['motivo_interrupcao']}"
    print(f"   [OK] Cenario 3 Aprovado: {trial_id_3} interrompido aos {res3['tempo_final_considerado']} min com motivo registrado.")

    # -------------------------------------------------------------
    # VALIDAÇÃO DOS ARTEFATOS GRAVADOS
    # -------------------------------------------------------------
    print("\n[VALIDACAO] Validando artefatos gerados nas pastas dos trials...")
    for tid, res in [(trial_id_1, res1), (trial_id_2, res2), (trial_id_3, res3)]:
        pasta_trial = pasta_saida / tid
        assert pasta_trial.is_dir(), f"Pasta do trial nao encontrada: {pasta_trial}"

        copia_sol = Path(res["artefatos"]["copia_solucao"])
        testes_json = Path(res["artefatos"]["testes_json"])
        metricas_json = Path(res["artefatos"]["metricas_json"])
        manifesto_json = Path(res["artefatos"]["manifesto"])

        assert copia_sol.is_file(), f"Copia da solucao ausente em {tid}"
        assert testes_json.is_file(), f"JSON de testes ausente em {tid}"
        assert metricas_json.is_file(), f"JSON de metricas ausente em {tid}"
        assert manifesto_json.is_file(), f"Manifesto ausente em {tid}"

        # Valida conteúdo do JSON de métricas do Áulus (#31)
        conteudo_met = json.loads(metricas_json.read_text(encoding="utf-8"))
        assert conteudo_met["trial_id"] == tid, f"trial_id divergente em metricas.json para {tid}"
        assert conteudo_met["status_analise"] == "ok", f"Falha na analise de metricas para {tid}"
        assert isinstance(conteudo_met["loc"], int), f"LOC invalido em {tid}"

        # Valida conteúdo do JSON de testes do Vinícius (#34)
        conteudo_testes = json.loads(testes_json.read_text(encoding="utf-8"))
        assert conteudo_testes["trial_id"] == tid, f"trial_id divergente em testes.json para {tid}"
        assert "resultado" in conteudo_testes, f"Resultado de testes ausente em {tid}"

    # -------------------------------------------------------------
    # VALIDAÇÃO DO CSV CONSOLIDADO
    # -------------------------------------------------------------
    print("\n[VALIDACAO] Validando integridade do arquivo CSV...")
    assert arquivo_csv.is_file(), f"Arquivo CSV nao foi criado: {arquivo_csv}"
    with arquivo_csv.open("r", encoding="utf-8") as f:
        leitor = list(csv.reader(f))

    assert len(leitor) == 4, f"Esperado cabecalho + 3 linhas no CSV, obtido {len(leitor)}"
    linhas_trials = [linha[0] for linha in leitor[1:]]
    assert linhas_trials == [trial_id_1, trial_id_2, trial_id_3], "Ordem dos trials no CSV divergente"

    # Confere se a linha de interrupção não virou 35.0
    linha_interrupcao = leitor[3]
    tempo_real_col = float(linha_interrupcao[6])
    tempo_cons_col = float(linha_interrupcao[7])
    status_col = linha_interrupcao[8]
    motivo_col = linha_interrupcao[9]

    assert status_col == "INTERRUPCAO", f"Status no CSV incorreto: {status_col}"
    assert tempo_cons_col == 13.50, f"Tempo considerado no CSV nao pode ser 35: {tempo_cons_col}"
    assert tempo_real_col == 13.50, f"Tempo real no CSV divergente: {tempo_real_col}"
    assert motivo_col == motivo_teste, f"Motivo no CSV incorreto: {motivo_col}"

    print(f"   [OK] CSV validado com sucesso ({len(linhas_trials)} rodadas registradas corretamente).")
    print("\n" + "=" * 70)
    print("[SUCESSO] CONCLUSAO: TODOS OS 3 CENARIOS FORAM VALIDADOS COM SUCESSO!")
    print(f"   -> Artefatos salvos em : {pasta_saida}")
    print(f"   -> CSV consolidado em  : {arquivo_csv}")
    print("=" * 70 + "\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstracao automatizada dos 3 cenarios de rodadas do Lab 02.")
    parser.add_argument(
        "--saida",
        type=Path,
        default=DIRETORIO_ATUAL / "resultados_demo",
        help="Diretorio onde os artefatos da demonstracao serao gerados.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DIRETORIO_ATUAL / "registro_experimento_demo.csv",
        help="Arquivo CSV para registrar as rodadas demonstrativas.",
    )
    args = parser.parse_args()

    sucesso = executar_demonstracao(args.saida, args.csv)
    return 0 if sucesso else 1


if __name__ == "__main__":
    raise SystemExit(main())

