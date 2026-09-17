"""Coordenador de Rodadas — base S01 (#30), consolidação S02 (#37).

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
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Adiciona a raiz do repositório ao sys.path para importação dos módulos parceiros
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from Laboratorio02_TrialsIA.consolidacao.artefatos import (
    avaliar_copia, conferir_csv, erro_registrado, gravar_json, preservar, registrar_csv,
)
from Laboratorio02_TrialsIA.consolidacao.terminal import ler_ate

BASE_TESTES_PADRAO = RAIZ_REPOSITORIO / "Laboratorio02_TrialsIA/casos_de_teste/casos_de_teste_katas.json"

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


def inicializar_csv(caminho_csv: Path | str = ARQUIVO_LOG_PADRAO) -> None:
    """Inicializa o arquivo CSV com cabeçalhos se ainda não existir."""
    destino = Path(caminho_csv)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.is_file():
        with destino.open("w", newline="", encoding="utf-8") as fluxo:
            escritor = csv.writer(fluxo)
            escritor.writerow(CABECALHOS_CSV)


def _validar_id(valor: str) -> None:
    if not re.fullmatch(r"[\w][\w.-]*", valor) or valor.endswith("."):
        raise ValueError("Identificadores devem usar letras, números, ponto, hífen ou sublinhado")


def finalizar_rodada(
    status, integrante, kata, tratamento, arquivo_solucao, trial_id, inicio_ts,
    fim_ts, resultado_testes=None, motivo_interrupcao="", timebox_minutos=TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida=DIRETORIO_RESULTADOS_PADRAO, caminho_csv=ARQUIVO_LOG_PADRAO,
    *, arquivo_testes=BASE_TESTES_PADRAO, fonte=None, arquivo_avaliado=None,
    tempo_decorrido_seg=None, erros=None, pasta_reservada=False, simulada=False,
):
    """Finaliza na cópia congelada. Resultado antigo sem origem verificável é refeito."""
    if status not in {"SUCESSO", "TESTES_REPROVADOS", "LIMITE_ATINGIDO", "INTERRUPCAO", "ERRO"}:
        raise ValueError(f"Status inválido: {status}")
    _validar_id(trial_id)
    pasta = Path(diretorio_saida).resolve() / trial_id
    if not pasta_reservada:
        conferir_csv(Path(caminho_csv), CABECALHOS_CSV, trial_id)
        pasta.mkdir(parents=True, exist_ok=False)
    # Um chamador legado pode ter testado o arquivo mutável. Só reutilizamos
    # resultados acompanhados dos bytes e da cópia realmente avaliada.
    if fonte is None or arquivo_avaliado is None:
        resultado_testes = None
    elif Path(arquivo_avaliado).read_bytes() != fonte:
        raise ValueError("A cópia avaliada não corresponde aos bytes finais")
    duracao = max(0, fim_ts - inicio_ts) if tempo_decorrido_seg is None else tempo_decorrido_seg
    tempo_real = round(duracao / 60, 6)
    dados = {
        "trial_id": trial_id, "integrante": integrante, "kata": normalizar_kata_codigo(kata),
        "tratamento": tratamento.lower(), "simulada": simulada,
        "horario_inicio": datetime.fromtimestamp(inicio_ts).isoformat(timespec="milliseconds"),
        "horario_fim": datetime.fromtimestamp(fim_ts).isoformat(timespec="milliseconds"),
        "tempo_decorrido_min": tempo_real,
        "tempo_final_considerado": float(timebox_minutos) if status == "LIMITE_ATINGIDO" else tempo_real,
        "timebox_minutos": timebox_minutos,
        "status": status, "status_encerramento": status,
        "motivo_interrupcao": motivo_interrupcao, "dado_censurado": status == "LIMITE_ATINGIDO",
        "erros": list(erros or []),
    }
    base = pasta / "casos_testes.json"
    if not base.exists():
        with base.open("xb") as fluxo:
            fluxo.write(Path(arquivo_testes).read_bytes())
    preservar(pasta, Path(arquivo_solucao), dados, chave_kata_executor(kata), base,
              fonte=fonte, avaliacao=resultado_testes, arquivo_avaliado=arquivo_avaliado)
    registrar_csv(Path(caminho_csv), CABECALHOS_CSV, dados, Path(arquivo_solucao))
    return dados


def coordenar_rodada(
    integrante: str, kata: str, tratamento: str, arquivo_solucao: Path | str,
    trial_id: str | None = None, timebox_minutos: float = TIMEBOX_MINUTOS_PADRAO,
    diretorio_saida: Path | str = DIRETORIO_RESULTADOS_PADRAO,
    caminho_csv: Path | str = ARQUIVO_LOG_PADRAO, simulacao: dict | None = None,
    *, arquivo_testes: Path | str = BASE_TESTES_PADRAO, automatico: bool = False,
    gemini: bool = False, enunciado: Path | str | None = None,
) -> dict:
    """Conduz uma rodada; medições usam relógio monotônico e cópias por tentativa."""
    if not math.isfinite(timebox_minutos) or not 0 < timebox_minutos <= 35:
        raise ValueError("O timebox deve ser finito, maior que zero e no máximo 35 minutos")
    integrante = integrante.strip()
    tratamento = tratamento.strip().lower()
    _validar_id(integrante)
    _validar_id(normalizar_kata_codigo(kata))
    if tratamento not in {"manual", "ia"}:
        raise ValueError("Tratamento deve ser manual ou ia")
    if gemini and (tratamento != "ia" or enunciado is None):
        raise ValueError("--gemini exige tratamento ia e --enunciado")
    if gemini and not Path(enunciado).is_file():
        raise FileNotFoundError(f"Enunciado não encontrado: {enunciado}")
    solucao = Path(arquivo_solucao).resolve()
    if solucao.suffix != ".py" or not solucao.is_file():
        raise ValueError("Informe um arquivo .py existente (pode estar vazio ao iniciar)")
    saida = Path(diretorio_saida).resolve()
    csv_path = Path(caminho_csv).resolve()
    conferir_csv(csv_path, CABECALHOS_CSV)
    base_fonte = Path(arquivo_testes).resolve()
    base_bytes = base_fonte.read_bytes()
    casos = json.loads(base_bytes.decode("utf-8-sig"))
    chave = chave_kata_executor(kata)
    if not isinstance(casos, dict) or not casos.get(chave):
        raise ValueError(f"Base de testes sem casos para '{chave}'")
    if simulacao is not None and (saida == DIRETORIO_RESULTADOS_PADRAO.resolve()
                                 or csv_path == ARQUIVO_LOG_PADRAO.resolve()):
        raise ValueError("Simulação exige diretório e CSV separados dos dados oficiais")
    if trial_id:
        _validar_id(trial_id)
        conferir_csv(csv_path, CABECALHOS_CSV, trial_id)
        pasta = saida / trial_id
        pasta.mkdir(parents=True, exist_ok=False)
    else:
        while True:
            trial_id = obter_proximo_trial_id(integrante, kata, tratamento, saida, csv_path)
            pasta = saida / trial_id
            try:
                pasta.mkdir(parents=True, exist_ok=False)
                break
            except FileExistsError:
                continue
    base = pasta / "casos_testes.json"
    base.write_bytes(base_bytes)
    gravar_json(pasta / "inicio_rodada.json", {
        "trial_id": trial_id, "integrante": integrante, "kata": normalizar_kata_codigo(kata),
        "tratamento": tratamento, "arquivo_solucao": str(solucao),
        "arquivo_testes_original": str(base_fonte), "automatico": automatico,
        "gemini": gemini, "simulada": simulacao is not None,
    })
    print(f"Trial {trial_id} | {tratamento} | limite: {timebox_minutos} min")
    inicio_ts = time.time()
    inicio_mono = time.monotonic()
    deadline = inicio_mono + timebox_minutos * 60
    fonte_final = resultado_final = arquivo_avaliado = None
    erros = []
    status, motivo = "INTERRUPCAO", ""
    tentativa = 0
    parada = None
    try:
        if not automatico and simulacao is None:
            input("Pressione ENTER para iniciar a rodada: ")
            inicio_ts = time.time()
            inicio_mono = time.monotonic()
            deadline = inicio_mono + timebox_minutos * 60
        if gemini:
            destino_ia = pasta / "gemini_gerada.py"
            processo = subprocess.run(
                [sys.executable, "-m", "Laboratorio02_TrialsIA.consolidacao.gerar_ia",
                 str(Path(enunciado).resolve()), str(destino_ia)],
                cwd=RAIZ_REPOSITORIO, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=max(0.001, deadline - time.monotonic()),
            )
            if processo.returncode:
                raise RuntimeError(f"Falha no Gemini: {processo.stderr.strip()}")
            if time.monotonic() >= deadline:
                raise TimeoutError("Timebox atingido durante geração Gemini")
            solucao.write_bytes(destino_ia.read_bytes())
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError("Timebox atingido")
            opcao = "1" if automatico or simulacao is not None else ler_ate(
                "[1] Testar [2] Tempo [3] Interromper: ", deadline).strip()
            if opcao == "3":
                status = "INTERRUPCAO"
                parada = (time.monotonic(), time.time())
                fonte_final = solucao.read_bytes()
                try:
                    motivo = ler_ate("Motivo da interrupção: ", deadline).strip() or "Interrupção solicitada"
                except (TimeoutError, EOFError, KeyboardInterrupt):
                    motivo = "Interrupção solicitada; justificativa não informada"
                break
            if opcao == "2":
                print(f"Restam {max(0, deadline - time.monotonic()) / 60:.2f} minutos")
                continue
            if opcao != "1":
                print("Opção inválida")
                continue
            tentativa += 1
            fonte = solucao.read_bytes()
            copia = pasta / f"tentativa_{tentativa:03d}.py"
            with copia.open("xb") as fluxo:
                fluxo.write(fonte)
            resultado = avaliar_copia(copia, chave, base, deadline=deadline)
            if time.monotonic() >= deadline:
                raise TimeoutError("Timebox atingido durante os testes")
            # O arquivo em edição pode ter mudado enquanto a bateria executava.
            # Uma aprovação antiga nunca encerra uma versão nova como aprovada.
            if solucao.read_bytes() != fonte:
                print("Solução alterada durante os testes; avaliando a nova versão")
                continue
            if resultado["passou_todos"] or automatico or simulacao is not None:
                fonte_final, resultado_final, arquivo_avaliado = fonte, resultado, copia
                status = "SUCESSO" if resultado["passou_todos"] else "TESTES_REPROVADOS"
                break
            print("Há testes reprovados. Continue editando a solução.")
    except (TimeoutError, subprocess.TimeoutExpired) as exc:
        status, motivo = "LIMITE_ATINGIDO", str(exc)
    except (KeyboardInterrupt, EOFError) as exc:
        status, motivo = "INTERRUPCAO", f"Interrupção de terminal ({type(exc).__name__})"
    except Exception as exc:
        status, motivo = "ERRO", str(exc)
        erros.append({"etapa": "rodada", **erro_registrado(exc)})
    fim_mono, fim_ts = parada or (time.monotonic(), time.time())
    duracao = fim_mono - inicio_mono
    if status == "LIMITE_ATINGIDO":
        # O fim da medição é o deadline; a avaliação final é pós-rodada.
        duracao = timebox_minutos * 60
        fim_ts = inicio_ts + duracao
    if simulacao is not None:
        tipo = simulacao.get("tipo", "sucesso")
        if tipo not in {"sucesso", "limite", "interrupcao"}:
            raise ValueError(f"Tipo de simulação desconhecido: {tipo}")
        if tipo != "sucesso":
            status = {"limite": "LIMITE_ATINGIDO", "interrupcao": "INTERRUPCAO"}[tipo]
        duracao = (timebox_minutos if tipo == "limite" else float(simulacao.get("duracao_minutos", 5))) * 60
        inicio_ts = simulacao.get("inicio_ts", inicio_ts)
        fim_ts = inicio_ts + duracao
        motivo = simulacao.get("motivo", motivo)
    return finalizar_rodada(
        status, integrante, kata, tratamento, solucao, trial_id, inicio_ts, fim_ts,
        resultado_final, motivo, timebox_minutos, saida, csv_path,
        arquivo_testes=base, fonte=fonte_final, arquivo_avaliado=arquivo_avaliado,
        tempo_decorrido_seg=duracao, erros=erros, pasta_reservada=True,
        simulada=simulacao is not None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rodada consolidada do Lab02 S02 — Issue #37")
    parser.add_argument("--integrante", "--participante", dest="integrante")
    parser.add_argument("--kata", "--exercicio", dest="kata")
    parser.add_argument("--tratamento", choices=["ia", "manual"])
    parser.add_argument("--solucao")
    parser.add_argument("--timebox", type=float, default=TIMEBOX_MINUTOS_PADRAO)
    parser.add_argument("--trial-id")
    parser.add_argument("--saida", type=Path, default=DIRETORIO_RESULTADOS_PADRAO)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--testes", type=Path, default=BASE_TESTES_PADRAO)
    parser.add_argument("--automatico", action="store_true", help="Avalia uma vez, sem tempo de desenvolvimento")
    parser.add_argument("--gemini", action="store_true", help="Gera no início via cliente existente; exige ia/enunciado")
    parser.add_argument("--enunciado", type=Path)
    args = parser.parse_args(argv)
    try:
        integrante = args.integrante or input("Participante: ").strip()
        kata = args.kata or input("Exercício: ").strip()
        tratamento = args.tratamento or input("Tratamento (ia/manual): ").strip()
        solucao = args.solucao or input("Arquivo .py da solução: ").strip()
        csv_path = args.csv or (ARQUIVO_LOG_PADRAO if args.saida == DIRETORIO_RESULTADOS_PADRAO
                               else args.saida / "registro_experimento.csv")
        res = coordenar_rodada(
            integrante, kata, tratamento, solucao, trial_id=args.trial_id,
            timebox_minutos=args.timebox, diretorio_saida=args.saida, caminho_csv=csv_path,
            arquivo_testes=args.testes, automatico=args.automatico,
            gemini=args.gemini, enunciado=args.enunciado,
        )
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Falha: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"Trial: {res['trial_id']} | Status: {res['status']} | Tempo: {res['tempo_final_considerado']} min")
    print(f"Manifesto: {res['artefatos']['manifesto']}")
    return {"SUCESSO": 0, "TESTES_REPROVADOS": 1, "ERRO": 2,
            "LIMITE_ATINGIDO": 3, "INTERRUPCAO": 4}[res["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
