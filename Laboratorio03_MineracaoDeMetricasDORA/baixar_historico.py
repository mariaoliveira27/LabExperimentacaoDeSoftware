"""Baixe ou retome o ZIP público de 2024; valide seu MD5 antes de disponibilizá-lo."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import requests

from recuperar_historico import DOI_FONTE, MD5_FONTE, URL_FONTE, _hashes


TAMANHO_FONTE = 952289386
BLOCO_PADRAO = 4 * 1024 * 1024


def _registrar(path, estado):
    temporario = path.with_name(path.name + ".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporario.replace(path)


def _baixar(saida, *, url, tamanho, md5_esperado, timeout=30, tentativas=3, bloco=BLOCO_PADRAO):
    """Helper interno com parâmetros de fonte substituíveis somente por fixtures."""
    saida = Path(saida)
    if saida.suffix.casefold() != ".zip":
        raise ValueError("O destino precisa ser um arquivo .zip, nunca um CSV humano.")
    if timeout <= 0 or tentativas < 1 or bloco < 1:
        raise ValueError("Timeout, tentativas e bloco devem ser positivos.")
    parcial = saida.with_name(saida.name + ".part")
    registro = saida.with_name(saida.name + ".download.json")
    if registro.exists():
        try:
            anterior = json.loads(registro.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeError):
            # Preserve checkpoints antigos truncados, sem perder o .part.
            # A fonte pinada e o MD5 integral continuam obrigatórios.
            sufixo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copy2(registro, registro.with_name(registro.name + f".corrompido.{sufixo}"))
            anterior = {"source_url": url, "expected_md5": md5_esperado}
        if not isinstance(anterior, dict):
            raise ValueError("Schema do registro de download inválido; preservado.")
        if anterior.get("source_url") != url or anterior.get("expected_md5") != md5_esperado:
            raise ValueError("Registro de download existente pertence a outra fonte; preservado.")
    estado = {
        "source_doi": DOI_FONTE if md5_esperado == MD5_FONTE else None,
        "source_url": url, "expected_size": tamanho, "expected_md5": md5_esperado,
        "md5_zip_verificado": False, "status": "download_iniciado",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }

    def salvar(status, erro=None):
        estado.update(status=status, atualizado_em=datetime.now(timezone.utc).isoformat())
        estado["downloaded_bytes"] = parcial.stat().st_size if parcial.exists() else 0
        if erro:
            estado["erro"] = str(erro)
        if parcial.exists():
            estado["sha256_parcial"] = _hashes(parcial)[1]
        _registrar(registro, estado)

    def verificar(path):
        md5, sha256 = _hashes(path)
        if path.stat().st_size != tamanho or md5 != md5_esperado:
            raise ValueError("MD5/tamanho não confere; arquivo preservado e não utilizado como fonte real.")
        estado.update(md5_zip_verificado=True, md5=md5, sha256=sha256, downloaded_bytes=tamanho)

    saida.parent.mkdir(parents=True, exist_ok=True)
    if saida.exists():
        if saida.stat().st_size >= tamanho:
            verificar(saida)
            estado["status"] = "download_verificado"
            _registrar(registro, estado)
            return estado
        if parcial.exists():
            raise FileExistsError("Destino parcial e .part existem simultaneamente; ambos preservados.")
        # Uma saída menor que a fonte é mantida como .part para retomada.
        saida.rename(parcial)
    if parcial.exists() and parcial.stat().st_size > tamanho:
        raise ValueError("Arquivo parcial maior que a fonte; preservado.")
    for tentativa in range(1, tentativas + 1):
        try:
            atual = parcial.stat().st_size if parcial.exists() else 0
            while atual < tamanho:
                fim = min(tamanho - 1, atual + bloco - 1)
                esperado = fim - atual + 1
                print(f"Tentativa {tentativa}/{tentativas}: bytes {atual}-{fim}/{tamanho}.", flush=True)
                with requests.get(
                    url, headers={"Range": f"bytes={atual}-{fim}"},
                    stream=True, timeout=timeout,
                ) as resposta:
                    resposta.raise_for_status()
                    content_range = f"bytes {atual}-{fim}/{tamanho}"
                    if resposta.status_code != 206 or resposta.headers.get("Content-Range") != content_range:
                        raise ValueError("Servidor não confirmou Content-Range exato; resposta não gravada.")
                    if resposta.headers.get("Content-Length") != str(esperado):
                        raise ValueError("Content-Length diverge do intervalo; resposta não gravada.")
                    recebidos = 0
                    with parcial.open("ab") as arquivo:
                        for chunk in resposta.iter_content(chunk_size=min(bloco, 256 * 1024)):
                            if not chunk:
                                continue
                            if recebidos + len(chunk) > esperado:
                                raise ValueError("Resposta excede o intervalo; bytes excedentes não gravados.")
                            arquivo.write(chunk)
                            recebidos += len(chunk)
                    if recebidos != esperado:
                        raise ValueError(f"Resposta incompleta: {recebidos}/{esperado} bytes; retomada preservada.")
                atual = parcial.stat().st_size
            verificar(parcial)
            parcial.rename(saida)
            estado.pop("erro", None)
            estado.pop("sha256_parcial", None)
            estado["status"] = "download_verificado"
            _registrar(registro, estado)
            print(f"Arquivo completo: {saida}; MD5 verificado.", flush=True)
            return estado
        except (requests.RequestException, OSError, ValueError) as exc:
            salvar("download_interrompido", exc)
            print(f"Tentativa {tentativa}/{tentativas} interrompida: {exc}", file=sys.stderr, flush=True)
            if tentativa == tentativas:
                raise RuntimeError(
                    f"Download interrompido com {estado['downloaded_bytes']}/{tamanho} bytes. "
                    f"Parcial preservado em {parcial}; execute novamente para retomar. MD5 integral pendente."
                ) from exc


def baixar(saida, *, timeout=30, tentativas=3, bloco=BLOCO_PADRAO):
    return _baixar(
        saida, url=URL_FONTE, tamanho=TAMANHO_FONTE, md5_esperado=MD5_FONTE,
        timeout=timeout, tentativas=tentativas, bloco=bloco,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path(".cache/arquivos_historicos/2024/cicd_env_results.zip"))
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--tentativas", type=int, default=3)
    parser.add_argument("--bloco", type=int, default=BLOCO_PADRAO, help="Bytes por requisição Range")
    args = parser.parse_args(argv)
    try:
        baixar(args.saida, timeout=args.timeout, tentativas=args.tentativas, bloco=args.bloco)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
