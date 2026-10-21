"""Qualifica apenas os 15 projetos com mínimo de runs observado no ZIP real.

Execute na raiz do laboratório com a autenticação existente do gh:
python -B -X utf8 data/execucao_pos_main/qualificar_historico_15.py
Snapshots/cache ficam em .cache/coleta_historico_pos_main; não publica bundle final.
"""

import json
from pathlib import Path
import shutil
import sys
import zipfile

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from coleta_amostra_real import (ClienteAuditavel, _carregar_historico_zenodo,
    _checkpoint, _configuracao, _contar_releases, _json_atomic, _ler_snapshot,
    _qualificar, agora, token_gh)
from gerar_amostra_rotulagem import sha256


def main():
    local = BASE / ".cache/coleta_historico_pos_main"
    saida = Path(__file__).resolve().parent / "historico_15"
    (local / "qualificacoes").mkdir(parents=True, exist_ok=True)
    saida.mkdir(parents=True, exist_ok=True)
    cfg, inicio, fim, criterios, assinatura = _configuracao(BASE / "config.yaml", 300)
    historico = _carregar_historico_zenodo(BASE / "data/historico_2024", inicio, fim)
    assinatura["historico_zenodo"] = historico.referencia
    report_path = saida / "qualificacao.json"
    anterior = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    anteriores = {r["candidate_id"]: r for r in anterior.get("resultados", [])}
    # Retomada íntegra só precisa dos snapshots e da fonte original.
    client = None
    resultados, resumos, erros = [], [], []
    for identificador in historico.runs_por_id:
        metadata = historico.metadados_por_id[identificador]
        candidato = {"id": identificador, "full_name": metadata["full_name"]}
        novo = local / "qualificacoes" / f"{identificador}.json"
        antigo = BASE / "data/coleta_final/qualificacoes" / novo.name
        origem = "qualificacao_real_atual"
        try:
            if novo.is_file() and identificador in anteriores:
                item = _ler_snapshot(novo, anteriores[identificador]["snapshot_sha256"])
                origem = "retomada_snapshot_verificado"
            else:
                item = None
                if antigo.is_file():
                    previo = json.loads(antigo.read_text(encoding="utf-8"))
                    if (previo.get("candidate_id") == identificador
                        and previo.get("aprovado") is False
                        and previo.get("motivo") == "menos_de_5_releases_na_janela"
                        and _contar_releases(previo.get("releases", []), previo["full_name"], inicio, fim) < criterios["min_releases"]):
                        item = previo
                        origem = "descarte_existente_releases_recontadas_sem_requisicao_nova"
                if item is None:
                    if client is None:
                        client = ClienteAuditavel(local / "requisicoes.jsonl", token=token_gh(),
                            cache_db_path=str(local / "cache/github_cache.db"), verify_ssl=True)
                    item = _qualificar(client, candidato, inicio, fim, criterios, historico)
                    _json_atomic(novo, item)
                else:
                    shutil.copyfile(antigo, novo)
            item["_snapshot_sha256"] = sha256(novo)
            resultados.append(item)
            resumos.append({"candidate_id": identificador, "full_name": item["full_name"],
                "aprovado": item["aprovado"], "motivo": item["motivo"], "etapa": item["etapa"],
                "origem_verificacao": origem, "coletado_em": item["coletado_em"],
                "stars": item["metadata"]["stargazers_count"],
                "total_releases_janela": item.get("total_releases_janela"),
                "runs_observados_fonte": len(historico.runs_por_id[identificador]),
                "runs_validos_qualificacao": item.get("total_runs_janela"),
                "escopo_runs": item.get("escopo_contagem_runs"),
                "snapshot": str(novo.relative_to(BASE)).replace("\\", "/"),
                "snapshot_sha256": item["_snapshot_sha256"]})
            print(json.dumps(resumos[-1], ensure_ascii=False), flush=True)
        except Exception as exc:
            erros.append({**candidato, "erro": f"{type(exc).__name__}: {exc}"})
            print(json.dumps(erros[-1], ensure_ascii=False), flush=True)
        _json_atomic(report_path, {"executado_em": agora(), "fonte": historico.referencia,
            "n_candidatos_fonte": len(historico.runs_por_id), "n_processados": len(resultados),
            "n_aprovados": sum(r["aprovado"] for r in resultados), "resultados": resumos, "erros": erros,
            "limitacao": "subconjunto da fonte historica; nao sao 300 aprovados, nao completa os primeiros 100 e nao comprova ano inteiro"})
    busca = {"fonte": "subconjunto_arquivo_publico_zenodo_verificado", "n_candidatos": 15,
        "criterio_preselecao": "ao menos 50 runs validos observados no default branch do snapshot",
        "nao_substitui_busca_final": True}
    _checkpoint(local, resultados, assinatura, busca, "insuficiente", erros or None)
    for nome in ["estado.json", "primeiros_100_aprovados.json", "repositorios_aprovados_parcial.csv",
                 "funil_selecao.csv", "funil_selecao.md", "descartes.csv"]:
        shutil.copyfile(local / nome, saida / nome)
    if (local / "requisicoes.jsonl").is_file():
        shutil.copyfile(local / "requisicoes.jsonl", saida / "requisicoes.jsonl")
    arquivo_zip = local / "originais_qualificacoes.zip"
    with zipfile.ZipFile(arquivo_zip, "w", compression=zipfile.ZIP_DEFLATED) as zipado:
        for path in sorted((local / "qualificacoes").glob("*.json")):
            zipado.write(path, str(path.relative_to(local)))
        zipado.write(local / "requisicoes.jsonl", "requisicoes.jsonl")
    if arquivo_zip.stat().st_size < 10 * 1024 * 1024:
        destino_zip = saida / arquivo_zip.name
        shutil.copyfile(arquivo_zip, destino_zip)
    else:
        destino_zip = arquivo_zip
    _json_atomic(saida / "arquivo_originais.json", {
        "arquivo": str(destino_zip.relative_to(BASE)).replace("\\", "/"),
        "bytes": destino_zip.stat().st_size, "sha256": sha256(destino_zip),
        "conteudo": "15 snapshots de qualificacao + requisicoes; sem cache DB ou ZIP Zenodo",
        "diretorio_original_do_checkpoint": str(local.relative_to(BASE)).replace("\\", "/"),
        "config_sha256": sha256(BASE / "config.yaml"),
        "fonte_historica_sha256": historico.referencia["arquivo_sha256"],
        "snapshots": {str(p.relative_to(local)).replace("\\", "/"): sha256(p)
                      for p in sorted((local / "qualificacoes").glob("*.json"))},
        "extrair_na_raiz_do_laboratorio": f"python -m zipfile -e {destino_zip.relative_to(BASE).as_posix()} .cache/coleta_historico_pos_main",
        "limitacao": "Os checkpoints espelhados referenciam qualificacoes/ neste diretorio original. Para revalidar derivacao dos runs tambem e necessario o ZIP Zenodo de 952289386 bytes com checksum publicado; a amostra continua parcial."})
    print(f"Qualificacao parcial: {sum(r['aprovado'] for r in resultados)}/{len(resultados)}; erros={len(erros)}; ano completo=False", flush=True)


if __name__ == "__main__":
    main()
