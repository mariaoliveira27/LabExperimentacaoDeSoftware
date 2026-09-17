"""Persistência da rodada consolidada (S02, Issue #37)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from Laboratorio02_TrialsIA.casos_de_teste.executor import avaliar_solucao


def erro_registrado(exc: BaseException) -> dict:
    return {"tipo": type(exc).__name__, "mensagem": str(exc)}


def gravar_json(caminho: Path, dados: dict) -> None:
    # Nunca substitui resultados anteriores, mesmo em reexecução acidental.
    with caminho.open("x", encoding="utf-8", newline="\n") as fluxo:
        json.dump(dados, fluxo, ensure_ascii=False, indent=2, allow_nan=False)
        fluxo.write("\n")


def avaliar_copia(copia: Path, chave: str, base: Path, *, deadline=None) -> dict:
    digest = hashlib.sha256(copia.read_bytes()).hexdigest()
    resultado = avaliar_solucao(str(copia), chave, str(base), deadline=deadline)
    if hashlib.sha256(copia.read_bytes()).hexdigest() != digest:
        raise RuntimeError("A solução modificou sua própria cópia durante os testes")
    if resultado is None:
        raise ValueError(f"Não há casos de aceitação para '{chave}'")
    return resultado


def metricas_indisponiveis(copia: Path, trial_id: str, exc: Exception) -> dict:
    return {"schema_version": 1, "trial_id": trial_id, "arquivo": str(copia),
            "status_analise": "erro_analise", "erro": erro_registrado(exc),
            "quantidade_funcoes": None, "complexidade_media": None,
            "loc": None, "sloc": None, "funcoes": None}


def coletar(copia: Path, trial_id: str) -> dict:
    try:
        from Laboratorio02_TrialsIA.metricas_estruturais.src.coletar_metricas import analisar_arquivo
        return analisar_arquivo(copia, trial_id=trial_id)
    except Exception as exc:
        # Dependência ausente ou erro inesperado também são dados indisponíveis.
        return metricas_indisponiveis(copia, trial_id, exc)


def preservar(pasta: Path, arquivo_solucao: Path, dados: dict, chave: str,
              base: Path, *, fonte: bytes | None = None,
              avaliacao: dict | None = None, arquivo_avaliado: Path | None = None) -> dict:
    """Congela uma versão e associa somente resultados obtidos desses bytes."""
    trial_id = dados["trial_id"]
    copia = pasta / f"{trial_id}_solucao_final.py"
    testes_path = pasta / "testes.json"
    metricas_path = pasta / "metricas.json"
    manifesto_path = pasta / "manifesto_rodada.json"
    erros = dados.setdefault("erros", [])
    digest = None
    erro_testes = None
    try:
        if fonte is None:
            fonte = arquivo_solucao.read_bytes()
        with copia.open("xb") as fluxo:
            fluxo.write(fonte)
        digest = hashlib.sha256(fonte).hexdigest()
    except OSError as exc:
        erros.append({"etapa": "preservacao", **erro_registrado(exc)})
        erro_testes = erro_registrado(exc)

    if digest is not None:
        try:
            if avaliacao is None:
                arquivo_avaliado = copia
                avaliacao = avaliar_copia(copia, chave, base)
        except (Exception, KeyboardInterrupt) as exc:
            erro_testes = erro_registrado(exc)
            erros.append({"etapa": "testes", **erro_testes})
        finally:
            # Preserva exatamente os bytes capturados, inclusive se a solução
            # tentou alterar __file__. Nesse caso o resultado é indisponível.
            try:
                alterada = copia.read_bytes() != fonte
            except OSError:
                alterada = True
            if alterada:
                try:
                    copia.write_bytes(fonte)
                except OSError as exc:
                    digest = None
                    erros.append({"etapa": "preservacao", **erro_registrado(exc)})
                avaliacao = None
                erro_testes = {"tipo": "RuntimeError", "mensagem": "Cópia alterada durante os testes"}
                erros.append({"etapa": "testes", **erro_testes})

    metricas = coletar(copia, trial_id) if digest else metricas_indisponiveis(
        copia, trial_id, OSError("Não foi possível preservar a versão final da solução"))
    metricas["sha256_solucao"] = digest
    if metricas["erro"] is not None:
        erros.append({"etapa": "metricas", **metricas["erro"]})
    dados["status_analise"] = metricas["status_analise"]
    dados["passou_todos"] = avaliacao["passou_todos"] if avaliacao else None
    dados["taxa_sucesso_testes"] = avaliacao["taxa_sucesso"] if avaliacao else None
    if dados["status"] == "SUCESSO" and not dados["passou_todos"]:
        dados["status"] = dados["status_encerramento"] = "TESTES_REPROVADOS"
    if erros:
        dados["status"] = "ERRO"
    gravar_json(testes_path, {
        "trial_id": trial_id, "arquivo_solucao": str(copia) if digest else None,
        "arquivo_executado": str(arquivo_avaliado) if arquivo_avaliado else None,
        "sha256_solucao": digest, "arquivo_testes": str(base),
        "sha256_testes": hashlib.sha256(base.read_bytes()).hexdigest(),
        "status_execucao": "erro" if erro_testes else "ok",
        "erro": erro_testes, "resultado": avaliacao,
    })
    gravar_json(metricas_path, metricas)
    artefatos = {"copia_solucao": str(copia) if digest else None,
                "sha256_copia": digest, "testes_json": str(testes_path),
                "metricas_json": str(metricas_path), "manifesto": str(manifesto_path),
                "casos_testes": str(base),
                "sha256_testes": hashlib.sha256(base.read_bytes()).hexdigest()}
    dados["artefatos"] = artefatos
    gravar_json(manifesto_path, {"schema_version": 2, **dados})
    return artefatos


def conferir_csv(caminho: Path, cabecalhos: list[str], trial_id: str | None = None) -> None:
    if not caminho.exists():
        return
    with caminho.open(encoding="utf-8", newline="") as fluxo:
        leitor = csv.DictReader(fluxo)
        if leitor.fieldnames != cabecalhos:
            raise ValueError(f"CSV com cabeçalho incompatível: {caminho}; escolha outro --csv")
        if trial_id and any(linha["Trial_ID"] == trial_id for linha in leitor):
            raise FileExistsError(f"trial_id já registrado no CSV: {trial_id}")


def registrar_csv(caminho: Path, cabecalhos: list[str], dados: dict, original: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conferir_csv(caminho, cabecalhos, dados["trial_id"])
    novo = not caminho.exists()
    a = dados["artefatos"]
    with caminho.open("a", encoding="utf-8", newline="") as fluxo:
        escritor = csv.writer(fluxo)
        if novo:
            escritor.writerow(cabecalhos)
        escritor.writerow([
            dados["trial_id"], dados["integrante"], dados["kata"], dados["tratamento"],
            dados["horario_inicio"], dados["horario_fim"], dados["tempo_decorrido_min"],
            dados["tempo_final_considerado"], dados["status"], dados["motivo_interrupcao"],
            dados["passou_todos"], dados["taxa_sucesso_testes"], dados["dado_censurado"],
            str(original), a["copia_solucao"], a["metricas_json"], a["testes_json"],
        ])
