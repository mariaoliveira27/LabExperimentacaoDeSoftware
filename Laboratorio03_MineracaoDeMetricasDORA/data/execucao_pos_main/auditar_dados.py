"""Auditoria de leitura das entradas recebidas da main; saídas só nesta pasta.

Execute na raiz do laboratório: python -B -X utf8 data/execucao_pos_main/auditar_dados.py
Não executa seed_data, consolidar_dataset, rede, julgamentos ou geradores de dados.
"""

import ast
import collections
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


BASE = Path(__file__).resolve().parents[2]
SAIDA = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ler(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_linhas(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def arquivo(path):
    return {"arquivo": str(path.relative_to(BASE)).replace("\\", "/"),
            "existe": path.is_file(),
            **({"bytes": path.stat().st_size, "sha256": sha256(path)} if path.is_file() else {})}


def cabecalhos_snapshots(paths):
    """Resume campos superiores sem reprocessar 7,6 GB de notas de releases.

    Não é uma aprovação nem substitui a auditoria completa dos snapshots.
    O formato produzido por _json_atomic usa indentação de dois espaços.
    """
    resumo, aprovados, ausentes, datas = collections.Counter(), [], [], []
    campos = {"full_name", "coletado_em", "aprovado", "etapa", "motivo"}
    for path in paths:
        valores = {}
        with path.open(encoding="utf-8") as stream:
            for linha in stream:
                match = re.fullmatch(r'  "(full_name|coletado_em|aprovado|etapa|motivo)": (.*?),?\s*', linha.rstrip())
                if match:
                    valores[match[1]] = json.loads(match[2].rstrip(","))
                    if set(valores) == campos:
                        break
        if set(valores) != campos:
            ausentes.append(path.name)
            continue
        resumo[(valores["aprovado"], valores["etapa"], valores["motivo"])]+=1
        datas.append(valores["coletado_em"])
        if valores["aprovado"]:
            aprovados.append(valores["full_name"])
    return {"escopo": "cabecalhos observados, sem certificar integridade/completude dos snapshots",
            "n_lidos": len(paths), "n_aprovado_true": len(aprovados),
            "aprovados": aprovados, "cabecalhos_incompletos": ausentes,
            "primeiro_coletado_em": min(datas) if datas else None,
            "ultimo_coletado_em": max(datas) if datas else None,
            "motivos": [{"aprovado": k[0], "etapa": k[1], "motivo": k[2], "n": n}
                        for k, n in sorted(resumo.items())]}


def main():
    coleta = BASE / "data/coleta_final"
    proveniencia = ler(coleta / "proveniencia.json")
    estado = ler(coleta / "estado.json")
    _, rows = csv_linhas(coleta / "repositorios_aprovados.csv")
    releases = ler(coleta / "releases.json")
    modulo = ast.parse((BASE / "seed_data.py").read_text(encoding="utf-8"))
    declaracao = next(node for node in modulo.body if isinstance(node, ast.AnnAssign)
                      and getattr(node.target, "id", "") == "REPOSITORIOS_CANDIDATOS_REFERENCIA")
    seeds = ast.literal_eval(declaracao.value)
    seeds_aprovados = [row for row in seeds if row.get("status") == "aprovado"][:300]
    snapshots = list((coleta / "qualificacoes").glob("*.json"))
    logs = [json.loads(line) for line in (coleta / "requisicoes.jsonl").read_text(encoding="utf-8").splitlines()]
    historico = ler(BASE / "data/historico_2024/proveniencia_historico.json")
    rels_fabricadas = 0
    for idx, (row, seed) in enumerate(zip(rows, seeds_aprovados)):
        esperadas = []
        n = seed["releases"]
        for release_idx in range(n):
            offset = int(release_idx * (360 / max(1, n))) + 5
            mes, ano = 10 + offset // 30, 2023
            if mes > 12:
                mes, ano = mes - 12, 2024
            dia = min(28, offset % 30 + 1)
            tag = f"v1.{release_idx}.0" if release_idx % 2 == 0 else f"v1.{release_idx // 2}.{release_idx}"
            esperadas.append({"id": (idx + 1) * 1000 + release_idx + 1,
                              "published_at": f"{ano}-{mes:02d}-{dia:02d}T14:30:00Z", "tag_name": tag})
        recebidas = releases.get(row["full_name"], [])
        rels_fabricadas += sum(all(r.get(k) == v for k, v in e.items())
                              for r, e in zip(recebidas, esperadas))
    humanos = []
    for path in sorted(BASE.glob("**/rotulos*.csv")):
        if any(parte in {".venv", ".cache"} for parte in path.parts):
            continue
        campos, avaliacoes = csv_linhas(path)
        humanos.append({**arquivo(path), "n_linhas": len(avaliacoes), "campos": campos,
                        "campos_contrato_atual_ausentes": sorted(set([
                            "full_name", "release_id", "tipo_projeto", "entrega_real",
                            "corretiva", "justificativa", "evidencia"]) - set(campos or []))})
    relatorio = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "janela_preservada": {"inicio": "2023-10-01T00:00:00Z", "fim": "2024-09-30T23:59:59Z"},
        "conclusao": "bundle_declarado_final_rejeitado; dados de referencia gerados nao sao amostra empirica",
        "fontes": [arquivo(BASE / n) for n in ["consolidar_dataset.py", "seed_data.py",
            "config.yaml", "data/coleta_final/repositorios_aprovados.csv", "data/coleta_final/releases.json",
            "data/coleta_final/proveniencia.json", "data/coleta_final/estado.json",
            "data/coleta_final/config_coleta.json", "data/coleta_final/busca.json",
            "data/coleta_final/requisicoes.jsonl", "data/historico_2024/proveniencia_historico.json"]],
        "bundle": {"n_csv": len(rows), "n_repositorios_releases": len(releases),
            "n_releases": sum(map(len, releases.values())),
            "hash_csv_confere": sha256(coleta / "repositorios_aprovados.csv") == proveniencia.get("repositorios_sha256"),
            "hash_releases_confere": sha256(coleta / "releases.json") == proveniencia.get("releases_sha256"),
            "proveniencia": proveniencia, "estado": estado,
            "campos_ausentes_proveniencia": sorted(set(["alvo", "evidencias", "busca", "requisicoes_sha256"]) - set(proveniencia)),
            "campos_ausentes_estado": sorted(set(["snapshots", "busca"]) - set(estado)),
            "snapshots_locais_sem_indice_final": len(snapshots),
            "bytes_snapshots_locais": sum(p.stat().st_size for p in snapshots),
            "cabecalhos_snapshots_locais": cabecalhos_snapshots(snapshots),
            "indice_primeiros_100_existe": (coleta / "primeiros_100_aprovados.json").exists(),
            "n_registros_requisicoes": len(logs),
            "primeira_requisicao_em": logs[0].get("registrado_em"),
            "ultima_requisicao_em": logs[-1].get("registrado_em"),
            "n_evidencias_indexadas": len(proveniencia.get("evidencias", []))},
        "correspondencia_seed_sem_executa_lo": {
            "n_seeds": len(seeds), "status": dict(collections.Counter(r["status"] for r in seeds)),
            "mesmos_300_nomes_e_ordem": len(rows) == len(seeds_aprovados) and all(
                r["full_name"] == f'{s["owner"]}/{s["repo"]}' for r, s in zip(rows, seeds_aprovados)),
            "n_contagens_runs_releases_iguais_seed": sum(int(r["total_runs_janela"]) == s["runs"]
                and int(r["total_releases_janela"]) == s["releases"] for r, s in zip(rows, seeds_aprovados)),
            "n_releases_que_reproduzem_id_data_tag_gerados": rels_fabricadas,
            "formulas_em_consolidar_dataset": {
                "lead_time_a": "max(0.5, 120.0 / max(1,n_releases)); ou valor legado",
                "lead_time_b": "max(0.2, lead_time_a*0.45); ou valor legado",
                "cfr_ci": "min(0.35,max(0.04,(stars%17)/60.0)); ou valor legado",
                "cfr_b": "max(0,min(0.25,cfr_ci*0.6)); ou valor legado",
                "recuperacao_horas": "max(0.4,(contribs%24)*0.8+0.5); ou valor legado",
                "runs_falhas": "round(n_runs*cfr_ci)", "episodios": "80% das falhas; 10% censurados",
                "releases": "ids por indice, tags v1.*, datas regulares, notas geradas",
                "origem_publicada_pelo_gerador": "github_api; modo_referencia=false (sem prova REST)"}},
        "historico": {"manifesto": historico,
            "fontes_locais": [arquivo(BASE / "data/historico_2024" / n)
                for n in ["metadata_repositorios.json", "runs_historicos.json"]],
            "fonte_zip_existe": Path(historico["arquivo_fonte"]).is_file(),
            "lacunas": ["outubro a dezembro de 2023 fora da janela da fonte",
                "nem janeiro a setembro de 2024 possui prova de enumeracao anual completa",
                "15 repositorios com minimo observado nao sao 300 aprovados",
                "sem ligacao auditavel entre CSV final, snapshots, releases REST e runs originais"]},
        "comparacoes": {"manifestos_locais": [str(p.relative_to(BASE)).replace("\\", "/")
            for p in (BASE / "data").rglob("*compar*.json")],
            "pendencia": "paginas originais, SHAs, datas de autor, tags predecessoras e hashes para RQ02/CFR(b)"},
        "arquivos_humanos_somente_schema": humanos,
        "restricao_humana": "Nao foram copiados ou preenchidos julgamentos; falta referencia auditada comum e tres avaliacoes independentes completas.",
    }
    comandos = [
        ("auditoria_bundle", [sys.executable, "-B", "-X", "utf8", "-c",
          "from coleta_amostra_real import auditar_bundle_final; print(auditar_bundle_final('data/coleta_final'))"]),
        ("sorteio", [sys.executable, "-B", "-X", "utf8", "executar_amostra_ouro.py", "--config", "config.yaml",
          "--coleta", "data/coleta_final", "--saida", "data/amostra_ouro_pos_main", "--rotulos", "rotulos_aulus.csv"]),
        ("analises_rq01_rq04", [sys.executable, "-B", "-X", "utf8", "analisar_rqs.py", "--config", "config.yaml",
          "--coleta", "data/coleta_final", "--saida", "data/analises_rqs_pos_main"]),
    ]
    relatorio["execucoes"] = []
    for nome, comando in comandos:
        execucao = subprocess.run(comando, cwd=BASE, capture_output=True, text=True, encoding="utf-8")
        log = SAIDA / f"{nome}.txt"
        log.write_text(execucao.stdout + execucao.stderr, encoding="utf-8")
        relatorio["execucoes"].append({"nome": nome, "comando": comando,
            "codigo": execucao.returncode, "log": arquivo(log)})
    relatorio["saidas_oficiais_criadas"] = {n: (BASE / n).exists() for n in
        ["rotulos_aulus.csv", "data/amostra_ouro_pos_main", "data/analises_rqs_pos_main"]}
    (SAIDA / "auditoria_dados.json").write_text(json.dumps(relatorio, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"conclusao": relatorio["conclusao"], "execucoes": relatorio["execucoes"],
                      "saidas_oficiais_criadas": relatorio["saidas_oficiais_criadas"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
