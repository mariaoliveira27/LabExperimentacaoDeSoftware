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
- Garantir encerramento automático mesmo enquanto aguarda entrada do usuário (input com timeout).
- Impedir que testes concluídos após o prazo sejam marcados como sucesso dentro do timebox.
- Garantir cópia correta e atômica da solução: testes e métricas rodam sobre o mesmo código preservado.
- Integrar o script de IA do Vinícius (#39): permitir consulta a Gemini somente em rodadas com IA
  e bloquear aplicação de respostas que chegarem após o prazo.
- Registrar interrupções antecipadas com duração real e motivo (sem converter para 35 min).
- Coletar métricas estáticas Radon (Áulus, #31) e salvar CSV unificado e manifestos com SHA-256.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ARQUIVO_LOG = "registro_experimento.csv"
TIMEBOX_MINUTOS = 35
# Suporte a leitura não-bloqueante no Windows
try:
    import msvcrt
except ImportError:
    msvcrt = None

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
KATAS_DIR = RAIZ_REPOSITORIO / "Laboratorio02_TrialsIA" / "Katas"

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
    """Retorna a sigla K01..K06 para uso em identificadores."""
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
    codigo = normalizar_kata_codigo(kata)
    if re.fullmatch(r"K\d+", codigo):
        return f"kata{int(codigo[1:]):02d}"
    return kata.strip().lower()



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


def input_com_timeout(prompt: str, timeout_segundos: float, valor_padrao: str = "") -> tuple[str, bool]:
    """Lê do teclado com limite de tempo. Retorna (texto_digitado, timeout_estourou).
    
    Garante encerramento automático caso o participante fique ocioso no prompt.
    """
    if timeout_segundos <= 0:
        return (valor_padrao, True)

    # 1. Estratégia nativa para Windows Console
    if msvcrt is not None and sys.stdin.isatty():
        sys.stdout.write(prompt)
        sys.stdout.flush()
        buffer = []
        inicio = time.time()
        while (time.time() - inicio) < timeout_segundos:
            if msvcrt.kbhit():
                try:
                    ch = msvcrt.getwche()
                except Exception:
                    ch = chr(msvcrt.getch()[0])
                if ch in ("\r", "\n"):
                    print()
                    return ("".join(buffer).strip(), False)
                elif ch == "\b":
                    if buffer:
                        buffer.pop()
                        sys.stdout.write(" \b")
                        sys.stdout.flush()
                elif ord(ch) >= 32:
                    buffer.append(ch)
            time.sleep(0.05)
        print("\n[TEMPO LIMITE ESGOTADO NO PROMPT]")
        return (valor_padrao, True)

    # 2. Estratégia genérica via Thread daemon (para headless, testes e redirecionamentos)
    resultado = [valor_padrao]
    finalizado = [False]

    def leitor():
        try:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            linha = sys.stdin.readline()
            if linha:
                resultado[0] = linha.rstrip("\r\n").strip()
            finalizado[0] = True
        except Exception:
            pass

    t = threading.Thread(target=leitor, daemon=True)
    t.start()
    t.join(timeout=timeout_segundos)

    if finalizado[0]:
        return (resultado[0], False)
    return (valor_padrao, True)


def inicializar_csv(caminho_csv: Path | str = ARQUIVO_LOG_PADRAO) -> None:
    """Inicializa o arquivo CSV com cabeçalhos se ainda não existir."""
    destino = Path(caminho_csv)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.is_file():
        with destino.open("w", newline="", encoding="utf-8") as fluxo:
            escritor = csv.writer(fluxo)
            escritor.writerow(CABECALHOS_CSV)


def salvar_artefatos_rodada(
def congelar_copia_solucao(
    arquivo_solucao: Path,
    trial_id: str,
    arquivo_solucao: Path,
    resultado_testes: dict | None,
    dados_rodada: dict,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
) -> dict[str, Path]:
    """Preserva a cópia do código final, relatório de testes, métricas do Radon e manifesto."""
) -> tuple[Path, str]:
    """Cria uma cópia congelada da solução e retorna seu caminho e hash SHA-256.
    
    Garante que os testes e as métricas avaliem exatamente o mesmo código preservado.
    """
    pasta_trial = Path(diretorio_saida) / trial_id
    pasta_trial.mkdir(parents=True, exist_ok=True)

    # 1. Cópia congelada do código da solução
    copia_solucao = pasta_trial / f"{trial_id}_solucao_final.py"
    shutil.copy2(arquivo_solucao, copia_solucao)
    sha256_copia = hashlib.sha256(copia_solucao.read_bytes()).hexdigest()
    return copia_solucao, sha256_copia

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
def extrair_codigo_markdown(texto_resposta: str) -> str:
    """Extrai o bloco de código Python retornado pelo Gemini."""
    match = re.search(r"```python\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match:
        return match.group(1).strip()
    match_generico = re.search(r"```\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match_generico:
        return match_generico.group(1).strip()
    return texto_resposta.strip()

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
def consultar_gemini_para_kata(
    chave_kata: str,
    prompt_adicional: str = "",
    api_key: str | None = None,
) -> tuple[str, bool, str]:
    """Integração com o script de Gemini de Vinícius (Issue #39).
    
    Consulta o modelo Gemini com o enunciado do kata correspondente.
    Retorna (codigo_gerado, sucesso, mensagem_status).
    """
    num_kata = chave_kata_executor(chave_kata)
    arquivo_kata = None
    if KATAS_DIR.exists():
        for arq in KATAS_DIR.glob("*.md"):
            if num_kata.lower() in arq.name.lower() or num_kata.replace("kata", "k") in arq.name.lower():
                arquivo_kata = arq
                break

    if not arquivo_kata or not arquivo_kata.is_file():
        enunciado = f"Resolva o problema de programação {num_kata} recursivamente em Python."
    else:
        enunciado = arquivo_kata.read_text(encoding="utf-8")

    prompt = (
        "Resolva o seguinte kata de programação em Python. "
        "A solução DEVE ler a entrada padrão (sys.stdin) e imprimir o resultado esperado na saída padrão (print). "
        "Use recursão conforme exigido pelo enunciado. "
        "Retorne APENAS o código Python funcional dentro de um bloco de código markdown (```python ... ```), "
        "sem explicações adicionais.\n\n"
        f"Enunciado:\n{enunciado}\n"
    )
    if prompt_adicional:
        prompt += f"\nInstruções adicionais do participante:\n{prompt_adicional}\n"

    chave = api_key or os.environ.get("GEMINI_API_KEY")
    if not chave:
        return (
            "",
            False,
            "Chave de API do Gemini não configurada. Defina a variável de ambiente GEMINI_API_KEY.",
        )

    try:
        from google import genai
        client = genai.Client(api_key=chave)
        # Utiliza gemini-2.5-flash ou equivalente recente
        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        codigo = extrair_codigo_markdown(resposta.text or "")
        return (codigo, True, "Código gerado com sucesso pelo Gemini.")
    except Exception as exc:
        return ("", False, f"Falha na comunicação com o Gemini: {exc}")


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
    copia_solucao: Path | None = None,
    sha256_copia: str | None = None,
    motivo_interrupcao: str = "",
    timebox_minutos: float = TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO,
) -> dict:
    """Consolida os dados da rodada, salva artefatos e registra no CSV."""
    """Consolida os dados da rodada, salva artefatos atômicos e registra no CSV."""
    horario_inicio = datetime.fromtimestamp(inicio_ts).strftime("%Y-%m-%d %H:%M:%S")
    horario_fim = datetime.fromtimestamp(fim_ts).strftime("%Y-%m-%d %H:%M:%S")
    tempo_real = round(max((fim_ts - inicio_ts) / 60.0, 0.0), 2)

    pasta_trial = Path(diretorio_saida) / trial_id
    pasta_trial.mkdir(parents=True, exist_ok=True)

    # 1. Garantir cópia atômica congelada
    if copia_solucao is None or not copia_solucao.is_file():
        copia_solucao, sha256_copia = congelar_copia_solucao(arquivo_solucao, trial_id, diretorio_saida)
    elif sha256_copia is None:
        sha256_copia = hashlib.sha256(copia_solucao.read_bytes()).hexdigest()

    # 2. Executar testes diretamente sobre a cópia congelada (se ainda não executados)
    chave_kata = chave_kata_executor(kata)
    if resultado_testes is None:
        resultado_testes = avaliar_solucao(str(copia_solucao), chave_kata)

    passou_todos = bool(resultado_testes and resultado_testes.get("passou_todos"))
    taxa_sucesso = float(resultado_testes.get("taxa_sucesso", 0.0)) if resultado_testes else 0.0

    if status == "SUCESSO":
    # 3. CORREÇÃO CRÍTICA DE PRAZO:
    # Testes concluídos após o prazo NÃO podem ser marcados como SUCESSO dentro dos 35 minutos!
    if status == "SUCESSO" and tempo_real > timebox_minutos:
        status = "LIMITE_ATINGIDO"
        motivo = (
            f"Testes foram concluídos aos {tempo_real:.2f} min, após o prazo limite de {timebox_minutos} min. "
            "Não constitui sucesso dentro do timebox."
        )
        tempo_considerado = float(timebox_minutos)
        censurado = True
    elif status == "SUCESSO":
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
        # Parada antecipada: DURAÇÃO REAL e MOTIVO (sem virar 35 min)
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
    # 4. Salvar relatório de testes em JSON
    caminho_testes_json = pasta_trial / "testes.json"
    relatorio_testes_completo = {
        "trial_id": trial_id,
        "arquivo_solucao": str(copia_solucao),
        "sha256_solucao": sha256_copia,
        "data_execucao": horario_fim,
        "resultado": resultado_testes,
    }
    with caminho_testes_json.open("w", encoding="utf-8") as f:
        json.dump(relatorio_testes_completo, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # 5. Coletar métricas Radon de Áulus (#31) sobre a mesma cópia congelada
    caminho_metricas_json = pasta_trial / "metricas.json"
    resultado_metricas = analisar_arquivo(copia_solucao, trial_id=trial_id)
    gravar_resultado(resultado_metricas, caminho_metricas_json)

    # 6. Salvar manifesto da rodada
    caminho_manifesto = pasta_trial / "manifesto_rodada.json"
    manifesto = {
        "schema_version": 1,
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
        "artefatos": {
            "copia_solucao": str(copia_solucao),
            "sha256_copia": sha256_copia,
            "testes_json": str(caminho_testes_json),
            "metricas_json": str(caminho_metricas_json),
        },
    }
    with caminho_manifesto.open("w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Salva arquivos da rodada (código congelado, testes, métricas Radon)
    artefatos = salvar_artefatos_rodada(
        trial_id=trial_id,
        arquivo_solucao=arquivo_solucao,
        resultado_testes=resultado_testes,
        dados_rodada=dados_rodada,
        diretorio_saida=diretorio_saida,
    )

    # Gravação no CSV consolidado
    # 7. Gravar no CSV consolidado
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
            str(copia_solucao),
            str(caminho_metricas_json),
            str(caminho_testes_json),
        ])
        
    print(f"\n💾 Dados salvos com sucesso em '{ARQUIVO_LOG}'!\n")

    dados_rodada["artefatos"] = {k: str(v) for k, v in artefatos.items()}
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
        "artefatos": {
            "copia_solucao": str(copia_solucao),
            "testes_json": str(caminho_testes_json),
            "metricas_json": str(caminho_metricas_json),
            "manifesto": str(caminho_manifesto),
            "sha256_copia": sha256_copia,
        },
    }
    return dados_rodada


def coordenar_rodada(
    integrante: str, kata: str, tratamento: str, arquivo_solucao: Path | str,
    trial_id: str | None = None, timebox_minutos: float = TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO, simulacao: dict | None = None,
    *, arquivo_testes: Path | str = BASE_TESTES_PADRAO, automatico: bool = False,
    gemini: bool = False, enunciado: Path | str | None = None,
) -> dict:
    """Executa e coordena a rodada, de forma interativa ou simulada para testes."""
    """Executa e coordena a rodada com travas de prazo, timeout no input e controle de IA."""
    caminho_solucao = Path(arquivo_solucao).resolve()
    if not caminho_solucao.is_file():
        raise FileNotFoundError(f"Arquivo de solução não encontrado: '{caminho_solucao}'")

    chave_kata = chave_kata_executor(kata)
    tratamento_norm = tratamento.strip().lower()

    if not trial_id:
        trial_id = obter_proximo_trial_id(
            integrante=integrante,
            kata=kata,
            tratamento=tratamento,
            tratamento=tratamento_norm,
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
        # Cópia atômica para avaliação
        copia_solucao, sha256_copia = congelar_copia_solucao(caminho_solucao, trial_id, diretorio_saida)
        resultado_testes = avaliar_solucao(str(copia_solucao), chave_kata)

        if tipo_simulacao == "sucesso":
            status = "SUCESSO"
            motivo = ""
        elif tipo_simulacao == "sucesso_tardio":
            # Teste de correção: testes concluídos após o limite NÃO podem ser SUCESSO
            status = "SUCESSO"  # Será rebaixado em finalizar_rodada
            motivo = ""
        elif tipo_simulacao == "limite":
            status = "LIMITE_ATINGIDO"
            motivo = simulacao.get("motivo", f"Timebox máximo de {timebox_minutos} minutos atingido")
            duracao_min = timebox_minutos
            fim_ts = inicio_ts + (duracao_min * 60.0)
        elif tipo_simulacao == "interrupcao":
            status = "INTERRUPCAO"
            motivo = simulacao.get("motivo", "Desistência informada pelo participante")
        elif tipo_simulacao == "consulta_gemini_manual":
            if tratamento_norm != "ia":
                raise PermissionError("Consulta ao Gemini bloqueada: rodada em tratamento manual.")
            status = "SUCESSO"
            motivo = ""
        elif tipo_simulacao == "consulta_gemini_tardia":
            if duracao_min > timebox_minutos:
                raise TimeoutError("Aplicação de resposta do Gemini bloqueada: resposta chegou após o prazo.")
            status = "SUCESSO"
            motivo = ""
        else:
            raise ValueError(f"Tipo de simulação desconhecido: '{tipo_simulacao}'")

        return finalizar_rodada(
            status=status,
            integrante=integrante,
            kata=kata,
            tratamento=tratamento,
            tratamento=tratamento_norm,
            arquivo_solucao=caminho_solucao,
            trial_id=trial_id,
            inicio_ts=inicio_ts,
            fim_ts=fim_ts,
            resultado_testes=resultado_testes,
            copia_solucao=copia_solucao,
            sha256_copia=sha256_copia,
            motivo_interrupcao=motivo,
            timebox_minutos=timebox_minutos,
            diretorio_saida=diretorio_saida,
            caminho_csv=caminho_csv,
        )

    # --- MODO INTERATIVO (Terminal do Participante) ---
    print("\n" + "=" * 60)
    print("\n" + "=" * 65)
    print("⏱️  COORDENADOR DE RODADA - EXPERIMENTO DE IA (LAB 02) ⏱️")
    print("=" * 60)
    print("=" * 65)
    print(f"👤 Integrante : {integrante}")
    print(f"🧩 Kata       : {normalizar_kata_codigo(kata)} ({chave_kata})")
    print(f"🤖 Tratamento : {tratamento.upper()}")
    print(f"🤖 Tratamento : {tratamento_norm.upper()}")
    print(f"🆔 Trial ID   : {trial_id}")
    print(f"📄 Solução    : {caminho_solucao}")
    print(f"⏳ Timebox    : {timebox_minutos} minutos")
    print("=" * 60)
    print("=" * 65)

    input("\n[ Pressione ENTER para liberar a rodada e INICIAR o cronômetro ]")
    inicio_ts = time.time()
    horario_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n▶️ Rodada iniciada em: {horario_inicio}")
    print("Você já pode programar na solução. Use o menu abaixo para validar seu código.\n")
    print("Programação liberada. Escolha as opções no menu abaixo.")

    ultimo_resultado_testes = None
    ultima_copia = None
    ultimo_hash = None

    while True:
        agora = time.time()
        tempo_decorrido = (agora - inicio_ts) / 60.0
        tempo_restante = timebox_minutos - tempo_decorrido
        tempo_restante_min = timebox_minutos - tempo_decorrido

        # Verificação automática de estouro de timebox
        # 1. Verificação automática imediata de estouro de timebox
        if tempo_decorrido >= timebox_minutos:
            print("\n" + "!" * 60)
            print("\n" + "!" * 65)
            print(f"🛑 ATENÇÃO: Timebox de {timebox_minutos} minutos esgotado!")
            print("Executando verificação final dos testes...")
            print("!" * 60)
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            print("Preservando snapshot e executando avaliação final dos testes...")
            print("!" * 65)
            ultima_copia, ultimo_hash = congelar_copia_solucao(caminho_solucao, trial_id, diretorio_saida)
            ultimo_resultado_testes = avaliar_solucao(str(ultima_copia), chave_kata)
            return finalizar_rodada(
                status="LIMITE_ATINGIDO",
                integrante=integrante,
                kata=kata,
                tratamento=tratamento,
                tratamento=tratamento_norm,
                arquivo_solucao=caminho_solucao,
                trial_id=trial_id,
                inicio_ts=inicio_ts,
                fim_ts=agora,
                resultado_testes=ultimo_resultado_testes,
                copia_solucao=ultima_copia,
                sha256_copia=ultimo_hash,
                motivo_interrupcao=f"Tempo esgotado ({timebox_minutos} min)",
                timebox_minutos=timebox_minutos,
                diretorio_saida=diretorio_saida,
                caminho_csv=caminho_csv,
            )

        print(f"\n[Tempo decorrido: {tempo_decorrido:.1f} min | Restante: {max(tempo_restante, 0.0):.1f} min]")
        print(f"\n[Decorrido: {tempo_decorrido:.1f} min | Restante: {max(tempo_restante_min, 0.0):.1f} min]")
        print("Menu da Rodada:")
        print("  [1] Executar bateria de testes agora")
        print("  [2] Consultar tempo restante")
        print("  [3] Interromper rodada antecipadamente (com justificativa)")
        opcao = input("Escolha uma opção (1/2/3): ").strip()
        print("  [3] Interromper rodada antecipadamente")
        if tratamento_norm == "ia":
            print("  [4] Consultar Gemini para sugestão de código (Vinícius #39)")

        # Timeout dinâmico no input: calcula quantos segundos faltam para estourar os 35 min
        segundos_restantes = max(tempo_restante_min * 60.0, 1.0)
        opcao, estourou = input_com_timeout("Escolha uma opção: ", timeout_segundos=segundos_restantes)

        if estourou:
            print("\n" + "!" * 65)
            print(f"🛑 Timebox esgotado durante a espera por entrada no terminal!")
            print("!" * 65)
            agora_fim = time.time()
            ultima_copia, ultimo_hash = congelar_copia_solucao(caminho_solucao, trial_id, diretorio_saida)
            ultimo_resultado_testes = avaliar_solucao(str(ultima_copia), chave_kata)
            return finalizar_rodada(
                status="LIMITE_ATINGIDO",
                integrante=integrante,
                kata=kata,
                tratamento=tratamento_norm,
                arquivo_solucao=caminho_solucao,
                trial_id=trial_id,
                inicio_ts=inicio_ts,
                fim_ts=agora_fim,
                resultado_testes=ultimo_resultado_testes,
                copia_solucao=ultima_copia,
                sha256_copia=ultimo_hash,
                motivo_interrupcao=f"Tempo esgotado durante espera por comando ({timebox_minutos} min)",
                timebox_minutos=timebox_minutos,
                diretorio_saida=diretorio_saida,
                caminho_csv=caminho_csv,
            )

        if opcao == "1":
            print("\nExecutando testes automatizados...")
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            print("\nPreservando cópia da solução e executando testes...")
            # Cópia congelada primeiro! Testes rodam estritamente sobre ela.
            ultima_copia, ultimo_hash = congelar_copia_solucao(caminho_solucao, trial_id, diretorio_saida)
            ultimo_resultado_testes = avaliar_solucao(str(ultima_copia), chave_kata)
            fim_ts = time.time()
            tempo_apos_testes = (fim_ts - inicio_ts) / 60.0

            # Verificação de sucesso dentro do prazo:
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
                if tempo_apos_testes <= timebox_minutos:
                    print("\n" + "🎉" * 25)
                    print("PARABÉNS! Solução 100% aprovada nos testes dentro do prazo!")
                    print(f"Tempo total (Time-to-green): {tempo_apos_testes:.2f} minutos.")
                    print("🎉" * 25 + "\n")
                    return finalizar_rodada(
                        status="SUCESSO",
                        integrante=integrante,
                        kata=kata,
                        tratamento=tratamento_norm,
                        arquivo_solucao=caminho_solucao,
                        trial_id=trial_id,
                        inicio_ts=inicio_ts,
                        fim_ts=fim_ts,
                        resultado_testes=ultimo_resultado_testes,
                        copia_solucao=ultima_copia,
                        sha256_copia=ultimo_hash,
                        timebox_minutos=timebox_minutos,
                        diretorio_saida=diretorio_saida,
                        caminho_csv=caminho_csv,
                    )
                else:
                    print("\n⚠️ AVISO: Todos os testes passaram, MAS a execução terminou após os 35 minutos!")
                    print(f"Concluído aos {tempo_apos_testes:.2f} min. Encerrando como LIMITE_ATINGIDO.")
                    return finalizar_rodada(
                        status="LIMITE_ATINGIDO",
                        integrante=integrante,
                        kata=kata,
                        tratamento=tratamento_norm,
                        arquivo_solucao=caminho_solucao,
                        trial_id=trial_id,
                        inicio_ts=inicio_ts,
                        fim_ts=fim_ts,
                        resultado_testes=ultimo_resultado_testes,
                        copia_solucao=ultima_copia,
                        sha256_copia=ultimo_hash,
                        motivo_interrupcao=f"Aprovação nos testes ocorreu aos {tempo_apos_testes:.2f} min (após o prazo).",
                        timebox_minutos=timebox_minutos,
                        diretorio_saida=diretorio_saida,
                        caminho_csv=caminho_csv,
                    )
            else:
                print("Ainda existem testes reprovados. Continue ajustando sua solução!")

        elif opcao == "2":
            print(f"Tempo restante: {max(timebox_minutos - ((time.time() - inicio_ts) / 60.0), 0.0):.2f} minutos.")
            rest = max(timebox_minutos - ((time.time() - inicio_ts) / 60.0), 0.0)
            print(f"Tempo restante: {rest:.2f} minutos.")

        elif opcao == "3":
            motivo = input("\nInforme o motivo da interrupção (ex: desistência, bloqueio conceitual): ").strip()
            motivo = input("\nInforme o motivo da interrupção (ex: desistência, erro conceitual): ").strip()
            if not motivo:
                motivo = "Interrupção manual sem motivo detalhado"
            fim_ts = time.time()
            print("\nExecutando teste final para registrar o estado no momento da parada...")
            ultimo_resultado_testes = avaliar_solucao(str(caminho_solucao), chave_kata)
            print(f"Registrando interrupção aos {((fim_ts - inicio_ts) / 60.0):.2f} minutos.")
            ultima_copia, ultimo_hash = congelar_copia_solucao(caminho_solucao, trial_id, diretorio_saida)
            ultimo_resultado_testes = avaliar_solucao(str(ultima_copia), chave_kata)
            return finalizar_rodada(
                status="INTERRUPCAO",
                integrante=integrante,
                kata=kata,
                tratamento=tratamento,
                tratamento=tratamento_norm,
                arquivo_solucao=caminho_solucao,
                trial_id=trial_id,
                inicio_ts=inicio_ts,
                fim_ts=fim_ts,
                resultado_testes=ultimo_resultado_testes,
                copia_solucao=ultima_copia,
                sha256_copia=ultimo_hash,
                motivo_interrupcao=motivo,
                timebox_minutos=timebox_minutos,
                diretorio_saida=diretorio_saida,
                caminho_csv=caminho_csv,
            )

        elif opcao == "4":
            if tratamento_norm != "ia":
                print("\n⛔ BLOQUEADO: Rodada em tratamento MANUAL. O uso de IA é estritamente proibido!")
                continue

            agora_req = time.time()
            if (agora_req - inicio_ts) / 60.0 >= timebox_minutos:
                print("\n⛔ BLOQUEADO: O prazo de 35 minutos já expirou. Consulta cancelada.")
                continue

            print("\nEnviando requisição ao Gemini com o enunciado do Kata...")
            instrucao_extra = input("Deseja enviar instrução adicional ao Gemini? (ENTER para nenhuma): ").strip()
            codigo_gemini, ok, msg = consultar_gemini_para_kata(chave_kata, instrucao_extra)

            agora_resp = time.time()
            if (agora_resp - inicio_ts) / 60.0 >= timebox_minutos:
                print("\n⛔ BLOQUEADO: A resposta do Gemini chegou após o término do prazo de 35 minutos!")
                print("A resposta foi DESCARTADA e NÃO será aplicada ao seu código.")
                continue

            if not ok:
                print(f"\n❌ Erro ao consultar Gemini: {msg}")
            else:
                print("\n✅ Resposta do Gemini recebida dentro do prazo!")
                print("-" * 40)
                print(codigo_gemini[:400] + ("..." if len(codigo_gemini) > 400 else ""))
                print("-" * 40)
                aplicar = input("Deseja aplicar este código ao seu arquivo de solução? (S/N): ").strip().upper() == "S"
                if aplicar:
                    caminho_solucao.write_text(codigo_gemini, encoding="utf-8")
                    print(f"Código aplicado com sucesso em '{caminho_solucao}'!")
        else:
            print("Opção inválida. Digite 1, 2 ou 3.")
            print("Opção inválida.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coordenador de Rodadas e Cronometragem do Lab 02.")
    parser.add_argument("--integrante", help="Nome do participante (ex: maria, vinicius, aulus).")
    parser.add_argument("--kata", help="Identificador do kata (ex: kata01 a kata06 ou 1 a 6).")
    parser.add_argument("--tratamento", choices=["ia", "manual"], help="Tratamento utilizado ('ia' ou 'manual').")
    parser.add_argument("--tratamento", choices=["ia", "manual"], help="Tratamento ('ia' ou 'manual').")
    parser.add_argument("--solucao", help="Caminho do arquivo Python da solução a ser avaliada.")
    parser.add_argument("--timebox", type=float, default=TIMEBOX_MINUTOS_PADRAO, help="Timebox máximo em minutos (padrão: 35).")
    parser.add_argument("--timebox", type=float, default=TIMEBOX_MINUTOS_PADRAO, help="Timebox máximo em minutos.")
    args = parser.parse_args(argv)

    integrante = args.integrante or input("1. Nome do Integrante (maria/vinicius/aulus): ").strip()
    kata = args.kata or input("2. Nome do Kata (ex: kata01): ").strip()
    tratamento = args.tratamento or input("3. Usou IA neste trial? (ia/manual): ").strip().lower()
    
    tratamento = args.tratamento or input("3. Tratamento (ia/manual): ").strip().lower()

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
    print("\n" + "=" * 65)
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
    print("=" * 65 + "\n")
    return 0



if __name__ == "__main__":
    inicializar_csv()
    executar_trial()
    raise SystemExit(main())
