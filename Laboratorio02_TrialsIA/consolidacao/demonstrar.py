"""Demonstra a integração da Issue #37 em um exercício fora dos seis oficiais.

Executa código e mede tempo reais; não utiliza o modo legado de simulação.
Cada execução exige uma pasta inédita e preserva seus próprios resultados.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from Laboratorio02_TrialsIA.cronometro.src.cronometro import coordenar_rodada


DIRETORIO_ATUAL = Path(__file__).resolve().parent
EXEMPLOS = DIRETORIO_ATUAL / "exemplos"
CASOS = EXEMPLOS / "casos_demo.json"
CENARIOS = (
    ("sucesso", "dobro_correto.py", "SUCESSO", "ok", 0.5),
    ("reprovacao", "dobro_incorreto.py", "TESTES_REPROVADOS", "ok", 0.5),
    ("limite", "dobro_lento.py", "LIMITE_ATINGIDO", "ok", 0.001),
    ("falha_analise", "erro_sintaxe.txt", "ERRO", "erro_sintaxe", 0.5),
    ("interrupcao", "dobro_incorreto.py", "INTERRUPCAO", "ok", 0.5),
)


def _exigir(condicao: bool, mensagem: str) -> None:
    # Continuam ativas mesmo quando Python é chamado com -O.
    if not condicao:
        raise ValueError(f"Falha na verificação da demonstração: {mensagem}")


def _ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _verificar_rodada(
    resultado: dict,
    solucao: Path,
    pasta_saida: Path,
    status_esperado: str,
    analise_esperada: str,
    timebox: float,
) -> dict:
    tid = resultado["trial_id"]
    pasta_trial = pasta_saida / "rodadas" / tid
    manifesto = _ler_json(pasta_trial / "manifesto_rodada.json")
    copia = Path(manifesto["artefatos"]["copia_solucao"])
    testes_json = Path(manifesto["artefatos"]["testes_json"])
    metricas_json = Path(manifesto["artefatos"]["metricas_json"])
    for artefato in (copia, testes_json, metricas_json):
        _exigir(artefato.is_file(), f"artefato ausente: {artefato}")
        _exigir(artefato.parent == pasta_trial, f"artefato fora da rodada: {artefato}")
    _exigir(copia.name == f"{tid}_solucao_final.py", "nome da cópia sem trial_id")
    _exigir(copia.read_bytes() == solucao.read_bytes(), "cópia diferente da solução enviada")
    sha256 = hashlib.sha256(copia.read_bytes()).hexdigest()
    testes = _ler_json(testes_json)
    metricas = _ler_json(metricas_json)
    inicio = _ler_json(pasta_trial / "inicio_rodada.json")
    _exigir(inicio["trial_id"] == tid, "trial_id divergente no registro inicial")
    _exigir(inicio["simulada"] is False, "demonstração executada no modo simulado")
    arquivo_executado = Path(testes["arquivo_executado"])
    _exigir(arquivo_executado.parent == pasta_trial, "arquivo executado fora da rodada")
    _exigir(arquivo_executado.read_bytes() == copia.read_bytes(), "versão testada difere da preservada")
    casos_preservados = Path(testes["arquivo_testes"])
    _exigir(casos_preservados.parent == pasta_trial, "base de testes fora da rodada")
    _exigir(casos_preservados.read_bytes() == CASOS.read_bytes(), "casos demonstrativos alterados")
    for nome, documento in (("manifesto", manifesto), ("testes", testes), ("métricas", metricas)):
        _exigir(documento["trial_id"] == tid, f"trial_id divergente em {nome}")
    for nome, valor in (
        ("manifesto", manifesto["artefatos"]["sha256_copia"]),
        ("testes", testes["sha256_solucao"]),
        ("métricas", metricas["sha256_solucao"]),
    ):
        _exigir(valor == sha256, f"SHA-256 divergente em {nome}")
    _exigir(Path(testes["arquivo_solucao"]) == copia, "testes não referenciam a cópia final")
    _exigir(Path(metricas["arquivo"]) == copia, "métricas não referenciam a cópia final")
    _exigir(manifesto["status"] == status_esperado, f"status incorreto para {tid}")
    _exigir(resultado["status"] == status_esperado, "status retornado diverge do manifesto")
    _exigir(metricas["status_analise"] == analise_esperada, f"análise incorreta para {tid}")
    _exigir(manifesto["tempo_decorrido_min"] >= 0, "duração negativa")

    if status_esperado == "LIMITE_ATINGIDO":
        _exigir(manifesto["dado_censurado"] is True, "limite sem censura")
        _exigir(manifesto["tempo_final_considerado"] == timebox, "timebox não preservado")
    else:
        _exigir(manifesto["dado_censurado"] is False, "censura indevida fora do limite")
    # O cenário lento aprova na avaliação final após o deadline; isso nunca
    # altera o encerramento LIMITE_ATINGIDO para SUCESSO.
    relatorio = testes["resultado"]
    _exigir(relatorio["total_casos"] == 3, "número incorreto de casos demonstrativos")
    passou = status_esperado in {"SUCESSO", "LIMITE_ATINGIDO"}
    _exigir(relatorio["passou_todos"] is passou, "resultado de aceitação incorreto")
    _exigir(relatorio["aprovados"] == (3 if passou else 0), "contagem de aprovados incorreta")
    if status_esperado == "INTERRUPCAO":
        _exigir("EOFError" in manifesto["motivo_interrupcao"], "EOF não registrado como interrupção")
        _exigir(manifesto["tempo_final_considerado"] < timebox, "interrupção virou timebox")

    if analise_esperada != "ok":
        for campo in ("quantidade_funcoes", "complexidade_media", "loc", "sloc", "funcoes"):
            _exigir(metricas[campo] is None, f"métrica indisponível preenchida em {campo}")
        _exigir(metricas["erro"] is not None, "falha de análise sem descrição")
        _exigir(manifesto["status_encerramento"] == "TESTES_REPROVADOS", "motivo original perdido")
    else:
        _exigir(metricas["loc"] > 0, "LOC válido não coletado")
        _exigir(metricas["quantidade_funcoes"] > 0, "função demonstrativa não analisada")
        _exigir(metricas["complexidade_media"] is not None, "complexidade não coletada")

    return {
        "trial_id": tid,
        "status": manifesto["status"],
        "status_analise": metricas["status_analise"],
        "testes_aprovados": relatorio["aprovados"],
        "total_testes": relatorio["total_casos"],
        "tempo_decorrido_min": manifesto["tempo_decorrido_min"],
        "tempo_final_considerado": manifesto["tempo_final_considerado"],
        "sha256_solucao": sha256,
        "copia_solucao": str(copia),
        "testes_json": str(testes_json),
        "metricas_json": str(metricas_json),
        "manifesto": str(pasta_trial / "manifesto_rodada.json"),
    }


def executar_demonstracao(pasta_saida: Path) -> Path:
    """Cria uma saída nova, executa cinco cenários e verifica seus artefatos."""
    pasta_saida = pasta_saida.resolve()
    pasta_saida.mkdir(parents=True, exist_ok=False)
    entradas = pasta_saida / "entradas"
    entradas.mkdir()
    arquivo_csv = pasta_saida / "registro_experimento_demo.csv"
    resumo = []
    for nome, fixture, status, analise, timebox in CENARIOS:
        print(f"\nDemonstração DEMO_DOBRO: {nome}")
        solucao = entradas / f"{nome}.py"
        with solucao.open("xb") as fluxo:
            fluxo.write((EXEMPLOS / fixture).read_bytes())
        inicio = time.monotonic()
        trial_id = f"demo_DEMO_DOBRO_{nome}"
        if nome == "interrupcao":
            # ENTER inicia a rodada; o fim real do stdin em seguida provoca EOF.
            processo = subprocess.run(
                [sys.executable, str(DIRETORIO_ATUAL.parent / "executar_rodada.py"),
                 "--participante", "demonstracao", "--exercicio", "DEMO_DOBRO",
                 "--tratamento", "manual", "--solucao", str(solucao),
                 "--trial-id", trial_id, "--timebox", str(timebox),
                 "--saida", str(pasta_saida / "rodadas"), "--csv", str(arquivo_csv),
                 "--testes", str(CASOS)],
                input="\n", text=True, capture_output=True, encoding="utf-8", timeout=45,
            )
            with (pasta_saida / "interrupcao_terminal.txt").open("x", encoding="utf-8") as fluxo:
                fluxo.write(processo.stdout + processo.stderr)
            _exigir(processo.returncode == 4, f"CLI de interrupção retornou {processo.returncode}")
            resultado = _ler_json(pasta_saida / "rodadas" / trial_id / "manifesto_rodada.json")
        else:
            resultado = coordenar_rodada(
                integrante="demonstracao",
                kata="DEMO_DOBRO",
                tratamento="manual",
                arquivo_solucao=solucao,
                trial_id=trial_id,
                timebox_minutos=timebox,
                diretorio_saida=pasta_saida / "rodadas",
                caminho_csv=arquivo_csv,
                arquivo_testes=CASOS,
                automatico=True,
            )
        tempo_parede = time.monotonic() - inicio
        registro = _verificar_rodada(resultado, solucao, pasta_saida, status, analise, timebox)
        registro["cenario"] = nome
        registro["tempo_parede_segundos"] = tempo_parede
        resumo.append(registro)
        print(f"Verificado: {registro['trial_id']} -> {status}; análise: {analise}")

    with arquivo_csv.open(encoding="utf-8", newline="") as fluxo:
        linhas = list(csv.DictReader(fluxo))
    _exigir(len(linhas) == len(CENARIOS), "número de rodadas incorreto no CSV")
    _exigir(len({linha["Trial_ID"] for linha in linhas}) == len(CENARIOS), "trial_id duplicado no CSV")
    for linha, registro in zip(linhas, resumo):
        _exigir(linha["Trial_ID"] == registro["trial_id"], "trial_id divergente no CSV")
        _exigir(linha["Status"] == registro["status"], "status divergente no CSV")
        for coluna, campo in (
            ("Copia_Solucao", "copia_solucao"),
            ("Testes_JSON", "testes_json"),
            ("Metricas_JSON", "metricas_json"),
        ):
            _exigir(Path(linha[coluna]) == Path(registro[campo]), f"caminho divergente em {coluna}")
        for coluna, campo in (
            ("Tempo_Decorrido_Min", "tempo_decorrido_min"),
            ("Tempo_Final_Considerado", "tempo_final_considerado"),
        ):
            _exigir(float(linha[coluna]) == registro[campo], f"tempo divergente em {coluna}")

    caminho_resumo = pasta_saida / "resumo_demonstracao.json"
    with caminho_resumo.open("x", encoding="utf-8") as fluxo:
        json.dump({
            "issue": 37,
            "exercicio": "DEMO_DOBRO: ler um inteiro e imprimir seu dobro",
            "dados_demonstrativos": True,
            "simulacao": False,
            "verificado": True,
            "csv": str(arquivo_csv),
            "rodadas": resumo,
        }, fluxo, ensure_ascii=False, indent=2, allow_nan=False)
        fluxo.write("\n")
    print(f"\nCinco cenários e seus identificadores, hashes, arquivos e CSV verificados.\nResumo: {caminho_resumo}")
    return caminho_resumo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, help="Pasta inédita para dados exclusivamente demonstrativos.")
    args = parser.parse_args(argv)
    nome_execucao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    destino = args.saida or DIRETORIO_ATUAL / "resultados_demo" / nome_execucao
    try:
        executar_demonstracao(destino)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Demonstração não concluída: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
