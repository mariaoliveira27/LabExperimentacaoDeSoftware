import time
"""Coordenador de Rodadas e Cronometragem — Laboratório 02 (Issue #30).

Responsável por orquestrar a execução de uma rodada experimental:
- Registrar participante, exercício (kata), tratamento (com/sem IA) e arquivo da solução.
- Gerar identificador único da rodada (trial_id, ex: maria_K01_ia_01).
- Medir tempo completo de resolução (time-to-green), com encerramento automático aos 35 minutos.
- Permitir execução dos testes de aceitação (Vinícius, #34) interativamente durante a rodada.
- Tratar parada antecipada com duração real e motivo como INTERRUPÇÃO (não transformando em 35 min).
- Preservar o código final e coletar métricas de complexidade e LOC do Radon (Áulus, #31).
- Salvar dados unificados em registro_experimento.csv e manifesto JSON por rodada.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ARQUIVO_LOG = "registro_experimento.csv"
TIMEBOX_MINUTOS = 35
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def inicializar_csv():
    """Cria o arquivo CSV com os cabeçalhos se ele não existir."""
    if not os.path.exists(ARQUIVO_LOG):
        with open(ARQUIVO_LOG, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Integrante", "Kata", "Tratamento_IA", "Horario_Inicio", 
                "Horario_Fim", "Tempo_Decorrido_Min", "Passou_Testes", 
                "Tempo_Final_Considerado", "Dado_Censurado"
            ])
# Adiciona a raiz do repositório ao sys.path para importação dos módulos parceiros
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

def executar_trial():
    """Conduz a interface visual e registra os dados do trial."""
    print("="*45)
    print("⏱️  COLETA DE TEMPO - EXPERIMENTO DE IA ⏱️")
    print("="*45)
    
    integrante = input("1. Nome do Integrante: ")
    kata = input("2. Nome do Kata: ")
    com_ia = input("3. Usou IA neste trial? (S/N): ").strip().upper() == 'S'
    
    # Início da medição
    input("\n[ Pressione ENTER para iniciar o cronômetro ]")
    inicio_ts = time.time()
    horario_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n▶️ Iniciado em: {horario_inicio}")
    print(f"⚠️ Lembre-se: O time-box máximo é de {TIMEBOX_MINUTOS} minutos.")
    
    # Fim da medição
    input("\n[ Pressione ENTER quando passar nos testes ou estourar o tempo ]")
    fim_ts = time.time()
    horario_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    tempo_decorrido = (fim_ts - inicio_ts) / 60
    print(f"\n⏹️ Finalizado em: {horario_fim}")
    print(f"⏳ Tempo real decorrido: {tempo_decorrido:.2f} minutos")
    
    passou = input("\nO código passou em TODOS os testes automatizados? (S/N): ").strip().upper() == 'S'
    
    # Lógica de Censura (Regra do Experimento)
    if tempo_decorrido >= TIMEBOX_MINUTOS or not passou:
        tempo_final = TIMEBOX_MINUTOS
from Laboratorio02_TrialsIA.casos_de_teste.executor import avaliar_solucao
from Laboratorio02_TrialsIA.metricas_estruturais.src.coletar_metricas import (
    analisar_arquivo,
    gravar_resultado,
)

TIMEBOX_MINUTOS_PADRAO = 35.0
DIRETORIO_CRONOMETRO = Path(__file__).resolve().parents[1]
ARQUIVO_LOG_PADRAO = DIRETORIO_CRONOMETRO / "registro_experimento.csv"
DIRETORIO_RESULTADOS_PADRAO = DIRETORIO_CRONOMETRO / "resultados"

CABECALHOS_CSV = [
    "Trial_ID",
    "Integrante",
    "Kata",
    "Tratamento",
    "Horario_Inicio",
    "Horario_Fim",
    "Tempo_Decorrido_Min",
    "Tempo_Final_Considerado",
    "Status",
    "Motivo_Interrupcao",
    "Passou_Testes",
    "Taxa_Sucesso_Testes",
    "Dado_Censurado",
    "Arquivo_Solucao_Original",
    "Copia_Solucao",
    "Metricas_JSON",
    "Testes_JSON",
]


def normalizar_kata_codigo(kata: str) -> str:
    """Retorna a sigla K01..K06 para uso em nomes e identificadores."""
    k = kata.strip().upper()
    if k.startswith("KATA"):
        k = k.replace("KATA", "K")
    elif not k.startswith("K"):
        try:
            num = int(k)
            k = f"K{num:02d}"
        except ValueError:
            pass
    if len(k) == 2 and k.startswith("K") and k[1].isdigit():
        k = f"K0{k[1]}"
    return k


def chave_kata_executor(kata: str) -> str:
    """Converte para a chave esperada pelo executor do Vinícius (ex: kata01)."""
    k = kata.strip().lower()
    if not k.startswith("kata"):
        if k.startswith("k"):
            k = "kata" + k[1:]
        else:
            try:
                num = int(k)
                k = f"kata{num:02d}"
            except ValueError:
                pass
    return k


def gerar_trial_id(
    integrante: str,
    kata: str,
    tratamento: str,
    sequencial: int = 1,
) -> str:
    """Gera identificador único da rodada, ex.: maria_K01_ia_01."""
    integrante_limpo = integrante.strip().lower()
    codigo_kata = normalizar_kata_codigo(kata)
    tratamento_limpo = tratamento.strip().lower()
    return f"{integrante_limpo}_{codigo_kata}_{tratamento_limpo}_{sequencial:02d}"


def obter_proximo_trial_id(
    integrante: str,
    kata: str,
    tratamento: str,
    diretorio_resultados: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO,
) -> str:
    """Encontra o próximo sequencial livre para não sobrescrever dados."""
    seq = 1
    dir_res = Path(diretorio_resultados)
    arq_csv = Path(caminho_csv)
    while True:
        tid = gerar_trial_id(integrante, kata, tratamento, seq)
        pasta_destino = dir_res / tid
        no_csv = False
        if arq_csv.is_file():
            try:
                texto = arq_csv.read_text(encoding="utf-8")
                if tid in texto:
                    no_csv = True
            except Exception:
                pass
        if not pasta_destino.exists() and not no_csv:
            return tid
        seq += 1


def inicializar_csv(caminho_csv: Path | str = ARQUIVO_LOG_PADRAO) -> None:
    """Inicializa o arquivo CSV com cabeçalhos se ainda não existir."""
    destino = Path(caminho_csv)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.is_file():
        with destino.open("w", newline="", encoding="utf-8") as fluxo:
            escritor = csv.writer(fluxo)
            escritor.writerow(CABECALHOS_CSV)


def salvar_artefatos_rodada(
    trial_id: str,
    arquivo_solucao: Path,
    resultado_testes: dict | None,
    dados_rodada: dict,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
) -> dict[str, Path]:
    """Preserva a cópia do código final, relatório de testes, métricas do Radon e manifesto."""
    pasta_trial = Path(diretorio_saida) / trial_id
    pasta_trial.mkdir(parents=True, exist_ok=True)

    # 1. Cópia congelada do código da solução
    copia_solucao = pasta_trial / f"{trial_id}_solucao_final.py"
    shutil.copy2(arquivo_solucao, copia_solucao)

    # 2. Relatório de testes executados
    caminho_testes_json = pasta_trial / "testes.json"
    relatorio_testes = {
        "trial_id": trial_id,
        "arquivo_solucao": str(copia_solucao),
        "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resultado": resultado_testes,
    }
    with caminho_testes_json.open("w", encoding="utf-8") as f:
        json.dump(relatorio_testes, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # 3. Coleta de métricas Radon (Áulus - RQ3)
    caminho_metricas_json = pasta_trial / "metricas.json"
    resultado_metricas = analisar_arquivo(copia_solucao, trial_id=trial_id)
    gravar_resultado(resultado_metricas, caminho_metricas_json)

    # 4. Manifesto unificado da rodada
    caminho_manifesto = pasta_trial / "manifesto_rodada.json"
    manifesto = {
        "schema_version": 1,
        "trial_id": trial_id,
        "integrante": dados_rodada["integrante"],
        "kata": dados_rodada["kata"],
        "tratamento": dados_rodada["tratamento"],
        "horario_inicio": dados_rodada["horario_inicio"],
        "horario_fim": dados_rodada["horario_fim"],
        "tempo_decorrido_min": dados_rodada["tempo_decorrido_min"],
        "tempo_final_considerado": dados_rodada["tempo_final_considerado"],
        "status": dados_rodada["status"],
        "motivo_interrupcao": dados_rodada["motivo_interrupcao"],
        "passou_todos": dados_rodada["passou_todos"],
        "taxa_sucesso_testes": dados_rodada["taxa_sucesso_testes"],
        "dado_censurado": dados_rodada["dado_censurado"],
        "artefatos": {
            "copia_solucao": str(copia_solucao),
            "sha256_copia": hashlib.sha256(copia_solucao.read_bytes()).hexdigest(),
            "testes_json": str(caminho_testes_json),
            "metricas_json": str(caminho_metricas_json),
        },
    }
    with caminho_manifesto.open("w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return {
        "copia_solucao": copia_solucao,
        "testes_json": caminho_testes_json,
        "metricas_json": caminho_metricas_json,
        "manifesto": caminho_manifesto,
    }


def finalizar_rodada(
    status: str,
    integrante: str,
    kata: str,
    tratamento: str,
    arquivo_solucao: Path,
    trial_id: str,
    inicio_ts: float,
    fim_ts: float,
    resultado_testes: dict | None,
    motivo_interrupcao: str = "",
    timebox_minutos: float = TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO,
) -> dict:
    """Consolida os dados da rodada, salva artefatos e registra no CSV."""
    horario_inicio = datetime.fromtimestamp(inicio_ts).strftime("%Y-%m-%d %H:%M:%S")
    horario_fim = datetime.fromtimestamp(fim_ts).strftime("%Y-%m-%d %H:%M:%S")
    tempo_real = round(max((fim_ts - inicio_ts) / 60.0, 0.0), 2)

    passou_todos = bool(resultado_testes and resultado_testes.get("passou_todos"))
    taxa_sucesso = float(resultado_testes.get("taxa_sucesso", 0.0)) if resultado_testes else 0.0

    if status == "SUCESSO":
        tempo_considerado = tempo_real
        censurado = False
        motivo = ""
    elif status == "LIMITE_ATINGIDO":
        tempo_considerado = float(timebox_minutos)
        censurado = True
        print(f"\n❌ Status: CENSURADO")
        print(f"Motivo: " + ("Estourou o time-box." if tempo_decorrido >= TIMEBOX_MINUTOS else "Falhou nos testes."))
        print(f"Tempo registrado para análise: {TIMEBOX_MINUTOS}.00 min")
        motivo = motivo_interrupcao or f"Timebox máximo de {timebox_minutos} minutos atingido"
    elif status == "INTERRUPCAO":
        # CORREÇÃO CRÍTICA: Não vira 35 minutos! Registra tempo real e motivo.
        tempo_considerado = tempo_real
        censurado = False
        motivo = motivo_interrupcao or "Interrupção solicitada pelo participante"
    else:
        tempo_final = round(tempo_decorrido, 2)
        censurado = False
        print(f"\n✅ Status: SUCESSO")
        print(f"Tempo registrado para análise: {tempo_final} min")
        
    # Salvar no CSV
    with open(ARQUIVO_LOG, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            integrante, kata, com_ia, horario_inicio, horario_fim, 
            round(tempo_decorrido, 2), passou, tempo_final, censurado
        raise ValueError(f"Status inválido: '{status}'")

    dados_rodada = {
        "trial_id": trial_id,
        "integrante": integrante,
        "kata": normalizar_kata_codigo(kata),
        "tratamento": tratamento.lower(),
        "horario_inicio": horario_inicio,
        "horario_fim": horario_fim,
        "tempo_decorrido_min": tempo_real,
        "tempo_final_considerado": tempo_considerado,
        "status": status,
        "motivo_interrupcao": motivo,
        "passou_todos": passou_todos,
        "taxa_sucesso_testes": taxa_sucesso,
        "dado_censurado": censurado,
    }

    # Salva arquivos da rodada (código congelado, testes, métricas Radon)
    artefatos = salvar_artefatos_rodada(
        trial_id=trial_id,
        arquivo_solucao=arquivo_solucao,
        resultado_testes=resultado_testes,
        dados_rodada=dados_rodada,
        diretorio_saida=diretorio_saida,
    )

    # Gravação no CSV consolidado
    inicializar_csv(caminho_csv)
    with Path(caminho_csv).open("a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow([
            trial_id,
            integrante,
            normalizar_kata_codigo(kata),
            tratamento.lower(),
            horario_inicio,
            horario_fim,
            tempo_real,
            tempo_considerado,
            status,
            motivo,
            passou_todos,
            taxa_sucesso,
            censurado,
            str(arquivo_solucao),
            str(artefatos["copia_solucao"]),
            str(artefatos["metricas_json"]),
            str(artefatos["testes_json"]),
        ])
        
    print(f"\n💾 Dados salvos com sucesso em '{ARQUIVO_LOG}'!\n")

    dados_rodada["artefatos"] = {k: str(v) for k, v in artefatos.items()}
    return dados_rodada


def coordenar_rodada(
    integrante: str,
    kata: str,
    tratamento: str,
    arquivo_solucao: Path | str,
    trial_id: str | None = None,
    timebox_minutos: float = TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO,
    simulacao: dict | None = None,
) -> dict:
    """Executa e coordena a rodada, de forma interativa ou simulada para testes."""
    caminho_solucao = Path(arquivo_solucao).resolve()
    if not caminho_solucao.is_file():
        raise FileNotFoundError(f"Arquivo de solução não encontrado: '{caminho_solucao}'")

    chave_kata = chave_kata_executor(kata)

    if not trial_id:
        trial_id = obter_proximo_trial_id(
            integrante=integrante,
            kata=kata,
            tratamento=tratamento,
            diretorio_resultados=diretorio_saida,
            caminho_csv=caminho_csv,
        )

    # --- MODO SIMULADO (Para testes automatizados e demonstração) ---
    if simulacao is not None:
        tipo_simulacao = simulacao.get("tipo", "sucesso").lower()
        inicio_ts = simulacao.get("inicio_ts", time.time())
        duracao_min = float(simulacao.get("duracao_minutos", 5.0))
        fim_ts = inicio_ts + (duracao_min * 60.0)

        # Executa testes na solução
        resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)

        if tipo_simulacao == "sucesso":
            status = "SUCESSO"
            motivo = ""
        elif tipo_simulacao == "limite":
            status = "LIMITE_ATINGIDO"
            motivo = simulacao.get("motivo", f"Timebox máximo de {timebox_minutos} minutos atingido")
            duracao_min = timebox_minutos
            fim_ts = inicio_ts + (duracao_min * 60.0)
        elif tipo_simulacao == "interrupcao":
            status = "INTERRUPCAO"
            motivo = simulacao.get("motivo", "Desistência informada pelo participante")
        else:
            raise ValueError(f"Tipo de simulação desconhecido: '{tipo_simulacao}'")

        return finalizar_rodada(
            status=status,
            integrante=integrante,
            kata=kata,
            tratamento=tratamento,
            arquivo_solucao=caminho_solucao,
            trial_id=trial_id,
            inicio_ts=inicio_ts,
            fim_ts=fim_ts,
            resultado_testes=resultado_testes,
            motivo_interrupcao=motivo,
            timebox_minutos=timebox_minutos,
            diretorio_saida=diretorio_saida,
            caminho_csv=caminho_csv,
        )

    # --- MODO INTERATIVO (Terminal do Participante) ---
    print("\n" + "=" * 60)
    print("⏱️  COORDENADOR DE RODADA - EXPERIMENTO DE IA (LAB 02) ⏱️")
    print("=" * 60)
    print(f"👤 Integrante : {integrante}")
    print(f"🧩 Kata       : {normalizar_kata_codigo(kata)} ({chave_kata})")
    print(f"🤖 Tratamento : {tratamento.upper()}")
    print(f"🆔 Trial ID   : {trial_id}")
    print(f"📄 Solução    : {caminho_solucao}")
    print(f"⏳ Timebox    : {timebox_minutos} minutos")
    print("=" * 60)

    input("\n[ Pressione ENTER para liberar a rodada e INICIAR o cronômetro ]")
    inicio_ts = time.time()
    horario_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n▶️ Rodada iniciada em: {horario_inicio}")
    print("Você já pode programar na solução. Use o menu abaixo para validar seu código.\n")

    ultimo_resultado_testes = None

    while True:
        agora = time.time()
        tempo_decorrido = (agora - inicio_ts) / 60.0
        tempo_restante = timebox_minutos - tempo_decorrido

        # Verificação automática de estouro de timebox
        if tempo_decorrido >= timebox_minutos:
            print("\n" + "!" * 60)
            print(f"🛑 ATENÇÃO: Timebox de {timebox_minutos} minutos esgotado!")
            print("Executando verificação final dos testes...")
            print("!" * 60)
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            return finalizar_rodada(
                status="LIMITE_ATINGIDO",
                integrante=integrante,
                kata=kata,
                tratamento=tratamento,
                arquivo_solucao=caminho_solucao,
                trial_id=trial_id,
                inicio_ts=inicio_ts,
                fim_ts=agora,
                resultado_testes=ultimo_resultado_testes,
                motivo_interrupcao=f"Tempo esgotado ({timebox_minutos} min)",
                timebox_minutos=timebox_minutos,
                diretorio_saida=diretorio_saida,
                caminho_csv=caminho_csv,
            )

        print(f"\n[Tempo decorrido: {tempo_decorrido:.1f} min | Restante: {max(tempo_restante, 0.0):.1f} min]")
        print("Menu da Rodada:")
        print("  [1] Executar bateria de testes agora")
        print("  [2] Consultar tempo restante")
        print("  [3] Interromper rodada antecipadamente (com justificativa)")
        opcao = input("Escolha uma opção (1/2/3): ").strip()

        if opcao == "1":
            print("\nExecutando testes automatizados...")
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            if ultimo_resultado_testes and ultimo_resultado_testes.get("passou_todos"):
                fim_ts = time.time()
                print("\n" + "🎉" * 25)
                print(f"PARABÉNS! Solução aprovada em 100% dos testes dentro do prazo!")
                print(f"Tempo total (Time-to-green): {((fim_ts - inicio_ts) / 60.0):.2f} minutos.")
                print("🎉" * 25 + "\n")
                return finalizar_rodada(
                    status="SUCESSO",
                    integrante=integrante,
                    kata=kata,
                    tratamento=tratamento,
                    arquivo_solucao=caminho_solucao,
                    trial_id=trial_id,
                    inicio_ts=inicio_ts,
                    fim_ts=fim_ts,
                    resultado_testes=ultimo_resultado_testes,
                    timebox_minutos=timebox_minutos,
                    diretorio_saida=diretorio_saida,
                    caminho_csv=caminho_csv,
                )
            else:
                print("Ainda existem testes reprovados. Continue ajustando sua solução!")

        elif opcao == "2":
            print(f"Tempo restante: {max(timebox_minutos - ((time.time() - inicio_ts) / 60.0), 0.0):.2f} minutos.")

        elif opcao == "3":
            motivo = input("\nInforme o motivo da interrupção (ex: desistência, bloqueio conceitual): ").strip()
            if not motivo:
                motivo = "Interrupção manual sem motivo detalhado"
            fim_ts = time.time()
            print("\nExecutando teste final para registrar o estado no momento da parada...")
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            print(f"Registrando interrupção aos {((fim_ts - inicio_ts) / 60.0):.2f} minutos.")
            return finalizar_rodada(
                status="INTERRUPCAO",
                integrante=integrante,
                kata=kata,
                tratamento=tratamento,
                arquivo_solucao=caminho_solucao,
                trial_id=trial_id,
                inicio_ts=inicio_ts,
                fim_ts=fim_ts,
                resultado_testes=ultimo_resultado_testes,
                motivo_interrupcao=motivo,
                timebox_minutos=timebox_minutos,
                diretorio_saida=diretorio_saida,
                caminho_csv=caminho_csv,
            )
        else:
            print("Opção inválida. Digite 1, 2 ou 3.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coordenador de Rodadas e Cronometragem do Lab 02.")
    parser.add_argument("--integrante", help="Nome do participante (ex: maria, vinicius, aulus).")
    parser.add_argument("--kata", help="Identificador do kata (ex: kata01 a kata06 ou 1 a 6).")
    parser.add_argument("--tratamento", choices=["ia", "manual"], help="Tratamento utilizado ('ia' ou 'manual').")
    parser.add_argument("--solucao", help="Caminho do arquivo Python da solução a ser avaliada.")
    parser.add_argument("--timebox", type=float, default=TIMEBOX_MINUTOS_PADRAO, help="Timebox máximo em minutos (padrão: 35).")
    args = parser.parse_args(argv)

    integrante = args.integrante or input("1. Nome do Integrante (maria/vinicius/aulus): ").strip()
    kata = args.kata or input("2. Nome do Kata (ex: kata01): ").strip()
    tratamento = args.tratamento or input("3. Usou IA neste trial? (ia/manual): ").strip().lower()
    
    caminho_solucao = args.solucao
    if not caminho_solucao:
        caminho_solucao = input("4. Caminho do arquivo da solução (.py): ").strip()

    res = coordenar_rodada(
        integrante=integrante,
        kata=kata,
        tratamento=tratamento,
        arquivo_solucao=caminho_solucao,
        timebox_minutos=args.timebox,
    )

    print("\n" + "=" * 60)
    print("🏁 RODADA CONCLUÍDA E ARTEFATOS PRESERVADOS!")
    print(f"Trial ID            : {res['trial_id']}")
    print(f"Status              : {res['status']}")
    print(f"Tempo Considerado   : {res['tempo_final_considerado']} min")
    print(f"Dado Censurado      : {res['dado_censurado']}")
    print(f"Passou Todos        : {res['passou_todos']}")
    print(f"Taxa de Sucesso     : {res['taxa_sucesso_testes']}%")
    print(f"Cópia da Solução    : {res['artefatos']['copia_solucao']}")
    print(f"Relatório de Testes : {res['artefatos']['testes_json']}")
    print(f"Métricas Radon (RQ3): {res['artefatos']['metricas_json']}")
    print(f"Manifesto da Rodada : {res['artefatos']['manifesto']}")
    print("=" * 60 + "\n")
    return 0



if __name__ == "__main__":
    inicializar_csv()
    executar_trial()
    raise SystemExit(main())