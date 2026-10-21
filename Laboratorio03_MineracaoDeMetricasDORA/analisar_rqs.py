"""Análises reproduzíveis RQ01–RQ04, exclusivamente de um bundle final auditado.

Uso: python analisar_rqs.py --coleta data/coleta_final --saida data/analises_rqs
O CSV legado do pipeline (inclusive seu lead time simulado) nunca é uma entrada.
Sem 300 aprovados reais e snapshots íntegros, nenhuma saída é criada. Dados que
faltam em um bundle final válido são nulos, com motivo, e não zero.

Contrato adicional opcional para RQ02 e CFR(b): --comparacoes comparacoes.json.
JSON schema_version=1, origem=github_api, modo_referencia=false, hashes
repositorios_sha256/releases_sha256, e repositorios={full_name: {release_id:
{status: completa|sem_predecessora|indisponivel, base_tag, head_tag, motivo,
paginas: [{arquivo, sha256}]}}}. Cada arquivo de página é JSON com endpoint
/repos/{full_name}/compare/{base_tag}...{head_tag} (tags codificadas), params
{page: 1..N, per_page: 100}, http_status=200 e resposta original REST contendo
total_commits e commits. Total, páginas, SHAs, author.date e mensagens são
validados; a comparação deve usar a predecessora cronológica, inclusive fora
da janela quando preservada no snapshot de releases. A primeira release sem
predecessora da história é explicitamente sem_predecessora; erro/404 usa
indisponivel, nunca uma lista vazia de commits inventada.

RQ03(CI)/RQ04 exigem cobertura_runs em cada snapshot: schema_version=1,
completa/historico_anual_completo/permite_metricas_dora_anuais=true, janela
{inicio,fim}, event=push, default_branch, fonte=exportacao_anual_original e
evidencias=[{arquivo,sha256}]. Cada evidência deve ser um arquivo original
preservado no bundle, referenciado pelo hash do snapshot. A declaração e a
fonte precisam ser auditadas pelo grupo; uma consulta completa dos registros
retidos pela API não comprova a preservação de todo o histórico anual.

Quartis usam interpolação linear (posição (n-1)*p, tipo 7). Sumários principais
descrevem distribuições de métricas por repositório, sem dar maior peso a
projetos maiores. A distribuição adicional de episódios recuperados é
identificada separadamente; censurados não entram em sua mediana/IQR. Não se
estima mediana de sobrevivência sem duração observável dos censurados.
"""

import argparse
import csv
from dataclasses import dataclass
from html import escape
import json
import math
from pathlib import Path
import sys
from urllib.parse import quote

import yaml

from gerar_amostra_rotulagem import instante, ler_aprovados, releases_validas, sha256
from metricas.calculo_metricas import (
    calcular_cfr_ci, calcular_cfr_releases, calcular_deployment_frequency,
    calcular_lead_time_repositorio, calcular_tempo_recuperacao,
)


METRICAS = (
    ("RQ01", "deployment_frequency_semana", "releases/semana"),
    ("RQ02", "lead_time_release_mediana_dias", "dias"),
    ("RQ02", "lead_time_commit_mediana_dias", "dias"),
    ("RQ03", "cfr_ci_proxy", "proporção"),
    ("RQ03", "cfr_releases_proxy_v3", "proporção"),
    ("RQ04", "tempo_recuperacao_mediana_horas", "horas; somente recuperados"),
    ("RQ04", "proporcao_episodios_censurados", "proporção"),
)


@dataclass
class Dataset:
    """Somente carregar_dataset cria a entrada autorizada para exportação."""

    diretorio: Path
    aprovados: list
    releases: dict
    snapshots: dict
    inicio: object
    fim: object
    semanas: float
    hashes: dict


def _json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _evidencia(base, item):
    if not isinstance(item, dict) or not isinstance(item.get("arquivo"), str):
        raise ValueError("Referência de evidência inválida.")
    base, path = Path(base).resolve(), (Path(base) / item["arquivo"]).resolve()
    if not path.is_relative_to(base) or not path.is_file() or sha256(path) != item.get("sha256"):
        raise ValueError(f"Evidência ausente, externa ou com hash divergente: {item['arquivo']}.")
    return path


def carregar_dataset(coleta, config="config.yaml"):
    """Audita fatos e hashes antes de ler ou calcular qualquer métrica."""
    from coleta_amostra_real import auditar_bundle_final

    base = Path(coleta).resolve()
    auditar_bundle_final(base, config_yaml=config)
    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    inicio, fim = (instante(cfg["window"][campo]) for campo in ("start_date", "end_date"))
    semanas = float(cfg["window"]["weeks"])
    if not math.isfinite(semanas) or semanas <= 0:
        raise ValueError("Semanas da janela devem ser positivas e finitas.")
    paths = {nome: base / nome for nome in (
        "repositorios_aprovados.csv", "releases.json", "proveniencia.json")}
    prov = _json(paths["proveniencia.json"])
    aprovados = ler_aprovados(paths["repositorios_aprovados.csv"])
    releases = releases_validas(aprovados, _json(paths["releases.json"]), inicio, fim)
    snapshots = {}
    for evidencia in prov["evidencias"]:
        item = _json(_evidencia(base, evidencia))
        if item["aprovado"]:
            snapshots[item["full_name"]] = item
    hashes = {nome: sha256(path) for nome, path in paths.items()}
    hashes["config"] = sha256(config)
    return Dataset(base, aprovados, releases, snapshots, inicio, fim, semanas, hashes)


def cobertura_anual(dataset, nome):
    """Completude de paginação e completude histórica são contratos distintos."""
    cobertura = dataset.snapshots[nome].get("cobertura_runs")
    if not isinstance(cobertura, dict):
        return False, "cobertura_anual_de_runs_nao_comprovada"
    for campo in ("completa", "historico_anual_completo", "permite_metricas_dora_anuais"):
        if cobertura.get(campo) is not True:
            return False, "cobertura_anual_de_runs_nao_comprovada"
    registro = dataset.snapshots[nome]["registro"]
    janela = cobertura.get("janela")
    if (cobertura.get("schema_version") != 1 or cobertura.get("event") != "push"
            or cobertura.get("default_branch") != registro["default_branch"]
            or cobertura.get("fonte") != "exportacao_anual_original"
            or not isinstance(janela, dict)
            or instante(janela.get("inicio")) != dataset.inicio
            or instante(janela.get("fim")) != dataset.fim):
        raise ValueError(f"Contrato de cobertura anual inválido: {nome}.")
    evidencias = cobertura.get("evidencias")
    if not isinstance(evidencias, list) or not evidencias:
        raise ValueError(f"Cobertura anual sem fontes originais: {nome}.")
    for evidencia in evidencias:
        _evidencia(dataset.diretorio, evidencia)
    return True, ""


def carregar_comparacoes(path, dataset):
    """Valida comparações REST preservadas, sem chamar o coletor nem a rede."""
    if path is None:
        return {}, {}
    path = Path(path).resolve()
    manifesto = _json(path)
    if (not isinstance(manifesto, dict) or manifesto.get("schema_version") != 1
            or manifesto.get("origem") != "github_api" or manifesto.get("modo_referencia") is not False):
        raise ValueError("Comparações devem comprovar origem github_api, sem modo de referência.")
    for campo, nome in (("repositorios_sha256", "repositorios_aprovados.csv"), ("releases_sha256", "releases.json")):
        if manifesto.get(campo) != dataset.hashes[nome]:
            raise ValueError(f"Hash das entradas de comparações diverge: {campo}.")
    repos = manifesto.get("repositorios")
    if not isinstance(repos, dict) or set(repos) - set(dataset.releases):
        raise ValueError("Repositórios das comparações são inválidos ou externos ao dataset final.")
    resultado, hashes = {}, {str(path): sha256(path)}
    for nome, mapeamento in repos.items():
        if not isinstance(mapeamento, dict):
            raise ValueError(f"Comparações inválidas de {nome}.")
        originais = dataset.snapshots[nome]["releases"]
        historia = sorted((r for r in originais if not r["draft"] and not r["prerelease"]
                           and instante(r["published_at"]) <= dataset.fim),
                          key=lambda r: (instante(r["published_at"]), r["id"]))
        predecessoras = {str(r["id"]): (historia[i - 1]["tag_name"] if i else None)
                         for i, r in enumerate(historia)}
        finais = {str(r["id"]): r for r in dataset.releases[nome]}
        if set(mapeamento) - set(finais):
            raise ValueError(f"Release desconhecida nas comparações de {nome}.")
        for rel_id, entrada in mapeamento.items():
            if not isinstance(entrada, dict) or entrada.get("head_tag") != finais[rel_id]["tag_name"]:
                raise ValueError(f"Tag/registro de comparação inválido: {nome}/{rel_id}.")
            status = entrada.get("status")
            anterior = predecessoras[rel_id]
            if status == "sem_predecessora":
                if anterior is not None or not entrada.get("motivo") or entrada.get("paginas"):
                    raise ValueError(f"Release com predecessora foi ignorada: {nome}/{rel_id}.")
                resultado[nome, rel_id] = {"status": status, "commits": [], "motivo": entrada["motivo"]}
                continue
            if status == "indisponivel":
                if not isinstance(entrada.get("motivo"), str) or not entrada["motivo"].strip() or entrada.get("paginas"):
                    raise ValueError("Comparação indisponível exige motivo explícito e nenhuma página.")
                resultado[nome, rel_id] = {"status": status, "commits": [], "motivo": entrada["motivo"]}
                continue
            if status != "completa" or anterior is None or entrada.get("base_tag") != anterior:
                raise ValueError(f"Base/status da comparação inválido: {nome}/{rel_id}.")
            paginas = entrada.get("paginas")
            if not isinstance(paginas, list) or not paginas:
                raise ValueError("Comparação completa sem páginas REST preservadas.")
            endpoint = f"/repos/{nome}/compare/{quote(anterior, safe='')}...{quote(entrada['head_tag'], safe='')}"
            commits, shas, total = [], set(), None
            for indice, evidencia in enumerate(paginas, 1):
                arquivo = _evidencia(path.parent, evidencia)
                hashes[str(arquivo)] = sha256(arquivo)
                pagina = _json(arquivo)
                if (not isinstance(pagina, dict) or pagina.get("endpoint") != endpoint
                        or pagina.get("http_status") != 200
                        or pagina.get("params") != {"page": indice, "per_page": 100}):
                    raise ValueError("Página REST de comparação com endpoint/filtro/ordem inválidos.")
                resposta = pagina.get("resposta")
                if (not isinstance(resposta, dict) or type(resposta.get("total_commits")) is not int
                        or resposta["total_commits"] < 0 or not isinstance(resposta.get("commits"), list)):
                    raise ValueError("Resposta REST de comparação incompleta.")
                total = resposta["total_commits"] if total is None else total
                esperados = min(100, max(0, total - (indice - 1) * 100))
                if resposta["total_commits"] != total or len(resposta["commits"]) != esperados:
                    raise ValueError("Total ou quantidade da página de commits diverge; coleta incompleta.")
                for commit in resposta["commits"]:
                    sha = commit.get("sha") if isinstance(commit, dict) else None
                    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha) or sha in shas:
                        raise ValueError("SHA de commit inválido ou duplicado.")
                    info = commit.get("commit")
                    if not isinstance(info, dict) or not isinstance(info.get("author"), dict):
                        raise ValueError("Commit original sem objeto commit.author válido.")
                    data = instante(info["author"].get("date"))
                    if data > instante(finais[rel_id]["published_at"]):
                        raise ValueError("Data do autor posterior à release; lead time inválido, sem truncar a zero.")
                    if not isinstance(info.get("message"), str):
                        raise ValueError("Mensagem original do commit ausente.")
                    shas.add(sha)
                    commits.append({"author_date": data, "message": info["message"]})
            if len(commits) != total or len(paginas) != max(1, math.ceil(total / 100)):
                raise ValueError("Paginação de commits incompleta ou com páginas extras.")
            resultado[nome, rel_id] = {"status": status, "commits": commits, "motivo": ""}
    return resultado, hashes


def resumir(valores, *, n_total=None, n_censurados=0):
    """Quartis tipo 7; dados ausentes/censurados não viram observações zero."""
    valores = list(valores)
    validos = sorted(v for v in valores if v is not None)
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in validos):
        raise ValueError("Estatística recebeu valor não finito ou não numérico.")
    def quantil(p):
        if not validos:
            return None
        pos = (len(validos) - 1) * p
        a, b = math.floor(pos), math.ceil(pos)
        return validos[a] + (validos[b] - validos[a]) * (pos - a)
    q1, q3 = quantil(.25), quantil(.75)
    return {"n_total": len(valores) + n_censurados if n_total is None else n_total,
            "n_validos": len(validos), "n_ausentes": len(valores) - len(validos),
            "n_censurados": n_censurados, "mediana": quantil(.5), "q1": q1, "q3": q3,
            "iqr": q3 - q1 if validos else None}


def calcular_dataset(dataset, comparacoes):
    """Função pura; fixtures usadas nos testes jamais são exportadas por ela."""
    linhas, faltas, episodios = [], [], []
    def falta(nome, rq, motivo, release_id=""):
        faltas.append(dict(full_name=nome, rq=rq, release_id=release_id, motivo=motivo))
    for repo in dataset.aprovados:
        nome = repo["full_name"]
        releases = dataset.releases[nome]
        snapshot = dataset.snapshots[nome]
        row = dict(full_name=nome, total_releases_janela=len(releases),
                   deployment_frequency_semana=calcular_deployment_frequency(len(releases), dataset.semanas))
        lead, com_mensagens = [], []
        n_sem_commits = 0
        mensagens_completas = True
        for i, rel in enumerate(releases):
            entrada = comparacoes.get((nome, str(rel["id"])))
            completa = entrada is not None and entrada["status"] == "completa"
            commits = entrada["commits"] if completa else []
            if not commits:
                n_sem_commits += 1
                falta(nome, "RQ02", (entrada.get("motivo") or "comparacao_sem_commits") if entrada else "comparacao_ausente", rel["id"])
            lead.append(dict(release_date=instante(rel["published_at"]),
                             commit_dates=[c["author_date"] for c in commits]))
            # A primeira release não pode ser uma corretiva subsequente nesta janela.
            if i > 0 and not completa:
                mensagens_completas = False
            com_mensagens.append({**rel, "published_at": instante(rel["published_at"]),
                                  "commit_messages": [c["message"] for c in commits]})
        lt_a, lt_b, n_commits = calcular_lead_time_repositorio(lead)
        row.update(lead_time_release_mediana_dias=lt_a, lead_time_commit_mediana_dias=lt_b,
                   releases_lead_time_avaliadas=len(releases) - n_sem_commits,
                   releases_lead_time_ausentes=n_sem_commits, commits_lead_time_avaliados=n_commits)
        if mensagens_completas:
            cfr, falhas, avaliadas, censuradas = calcular_cfr_releases(com_mensagens, dataset.fim)
            row.update(cfr_releases_proxy_v3=cfr, releases_com_falha=falhas,
                       releases_cfr_avaliadas=avaliadas, releases_cfr_censuradas=censuradas)
            if cfr is None:
                falta(nome, "RQ03_releases", "nenhuma_release_com_seguimento_completo_de_7_dias")
        else:
            row.update(cfr_releases_proxy_v3=None, releases_com_falha=None,
                       releases_cfr_avaliadas=None, releases_cfr_censuradas=None)
            falta(nome, "RQ03_releases", "mensagens_de_commits_sem_coleta_completa")
        anual, motivo = cobertura_anual(dataset, nome)
        row["cobertura_runs_anual"] = anual
        row["runs_validos_observados_elegibilidade"] = int(repo["total_runs_janela"])
        if anual:
            runs = snapshot["runs"]
            ci = calcular_cfr_ci(runs)
            rec = calcular_tempo_recuperacao(runs, window_end=dataset.fim)
            row.update(cfr_ci_proxy=ci.cfr, runs_sucessos_anuais=ci.sucessos,
                       runs_falhas_anuais=ci.falhas, runs_ignorados_anuais=ci.ignorados,
                       tempo_recuperacao_mediana_horas=rec.mediana_horas,
                       episodios_recuperados=rec.recuperados, episodios_censurados=rec.censurados,
                       proporcao_episodios_censurados=rec.proporcao_censurada)
            for indice, duracao in enumerate(rec.tempos_horas, 1):
                episodios.append(dict(full_name=nome, indice_resultado=indice, estado="recuperado", duracao_horas=duracao))
            for indice in range(1, rec.censurados + 1):
                episodios.append(dict(full_name=nome, indice_resultado=indice, estado="censurado", duracao_horas=None))
            if rec.mediana_horas is None:
                falta(nome, "RQ04", "sem_episodios_recuperados" if rec.censurados else "sem_episodios_observados")
        else:
            for campo in ("cfr_ci_proxy", "runs_sucessos_anuais", "runs_falhas_anuais", "runs_ignorados_anuais",
                          "tempo_recuperacao_mediana_horas", "episodios_recuperados", "episodios_censurados",
                          "proporcao_episodios_censurados"):
                row[campo] = None
            falta(nome, "RQ03_CI", motivo)
            falta(nome, "RQ04", motivo)
        linhas.append(row)
    sumarios = []
    for rq, coluna, unidade in METRICAS:
        sumarios.append(dict(rq=rq, metrica=coluna, unidade_observacao="repositorio", unidade=unidade,
                             **resumir(row[coluna] for row in linhas)))
    recuperados = [e["duracao_horas"] for e in episodios if e["estado"] == "recuperado"]
    censurados = sum(e["estado"] == "censurado" for e in episodios)
    sumarios.append(dict(rq="RQ04", metrica="duracao_episodios_recuperados_horas",
                         unidade_observacao="episodio; condicionado_a_recuperacao", unidade="horas",
                         **resumir(recuperados, n_censurados=censurados)))
    return linhas, sumarios, faltas, episodios


def _csv(path, rows, campos):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def _grafico(rq, sumarios):
    """SVG vetorial: medianas e IQR, incluindo eixos e contagens de ausências."""
    dados = [s for s in sumarios if s["rq"] == rq and s["unidade_observacao"] == "repositorio"]
    height = 120 + 100 * len(dados)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {height}" role="img">',
           f'<title>{rq}: mediana e intervalo interquartil por repositório</title>',
           '<rect width="1100" height="100%" fill="white"/>',
           f'<text x="20" y="30" font-family="sans-serif" font-size="20">{rq}: mediana e IQR por repositório</text>']
    for indice, dado in enumerate(dados):
        y = 80 + indice * 100
        texto = f"{dado['metrica']} ({dado['unidade']}); n={dado['n_validos']}, ausentes={dado['n_ausentes']}"
        out.append(f'<text x="20" y="{y}" font-family="sans-serif" font-size="13">{escape(texto)}</text>')
        if dado["n_validos"] == 0:
            out.append(f'<text x="20" y="{y + 30}" font-family="sans-serif" font-size="13">Pendente: nenhuma observação válida.</text>')
            continue
        escala = max(dado["q3"] * 1.1, 1e-9)
        x = lambda valor: 60 + 900 * valor / escala
        out.extend([
            f'<line x1="60" y1="{y+40}" x2="960" y2="{y+40}" stroke="#999"/>',
            f'<rect x="{x(dado["q1"]):.3f}" y="{y+22}" width="{x(dado["q3"])-x(dado["q1"]):.3f}" height="20" fill="#b9d7e8" stroke="#164e72"/>',
            f'<line x1="{x(dado["mediana"]):.3f}" x2="{x(dado["mediana"]):.3f}" y1="{y+18}" y2="{y+46}" stroke="#123" stroke-width="2"/>',
            f'<text x="60" y="{y+62}" font-family="sans-serif" font-size="12">0</text>',
            f'<text x="400" y="{y+62}" font-family="sans-serif" font-size="12">Q1={dado["q1"]:.5g}; mediana={dado["mediana"]:.5g}; Q3={dado["q3"]:.5g}</text>',
            f'<text x="920" y="{y+62}" font-family="sans-serif" font-size="12">{escala:.5g}</text>',
        ])
    out.append('</svg>')
    return "\n".join(out) + "\n"


def executar(coleta, saida, config="config.yaml", comparacoes=None):
    dataset = carregar_dataset(coleta, config)
    comparadas, hashes_comp = carregar_comparacoes(comparacoes, dataset)
    linhas, sumarios, faltas, episodios = calcular_dataset(dataset, comparadas)
    destino = Path(saida)
    if destino.exists():
        raise FileExistsError(f"Saída preservada: {destino} já existe; use outro diretório.")
    destino.mkdir(parents=True)
    _csv(destino / "metricas_por_repositorio.csv", linhas, list(linhas[0]))
    _csv(destino / "sumarios_rq01_rq04.csv", sumarios, list(sumarios[0]))
    _csv(destino / "dados_ausentes.csv", faltas, ("full_name", "rq", "release_id", "motivo"))
    _csv(destino / "rq04_episodios.csv", episodios, ("full_name", "indice_resultado", "estado", "duracao_horas"))
    censura_releases = [dict(
        full_name=r["full_name"], n_releases_total=r["total_releases_janela"],
        n_releases_avaliadas=r["releases_cfr_avaliadas"],
        n_releases_censuradas=r["releases_cfr_censuradas"],
        n_releases_com_falha=r["releases_com_falha"],
        n_releases_avaliacao_ausente=r["total_releases_janela"] if r["releases_cfr_avaliadas"] is None else 0,
        status="dados_ausentes" if r["releases_cfr_avaliadas"] is None else "avaliada",
    ) for r in linhas]
    _csv(destino / "rq03_censura_releases.csv", censura_releases, list(censura_releases[0]))
    for rq in ("RQ01", "RQ02", "RQ03", "RQ04"):
        (destino / f"{rq.lower()}_mediana_iqr.svg").write_text(_grafico(rq, sumarios), encoding="utf-8")
    manifesto = {
        "schema_version": 1, "origem": "github_api", "modo_referencia": False,
        "status": "executada_com_ausencias" if faltas else "executada",
        "n_repositorios": len(linhas), "janela": {"inicio": dataset.inicio.isoformat(), "fim": dataset.fim.isoformat()},
        "semanas": dataset.semanas, "quantis": "interpolacao_linear_tipo_7",
        "unidade_principal": "repositorio", "heuristica_cfr_releases": "v3_refinada_existente",
        "validacao_humana_heuristica": "nao_aferida_por_esta_analise; depende_dos_tres_rotuladores_e_consenso",
        "rq04": "medianas condicionadas aos recuperados; censurados separados, sem imputacao e sem estimativa de sobrevivencia",
        "entradas_sha256": {**dataset.hashes, **hashes_comp},
        "codigo_sha256": {nome: sha256(Path(__file__).parent / nome) for nome in (
            "analisar_rqs.py", "metricas/calculo_metricas.py", "coleta_amostra_real.py", "gerar_amostra_rotulagem.py")},
        "python_version": sys.version.split()[0],
        "cobertura_por_metrica": [{k: s[k] for k in ("rq", "metrica", "n_total", "n_validos", "n_ausentes", "n_censurados")} for s in sumarios],
        "n_repositorios_cobertura_anual_runs": sum(r["cobertura_runs_anual"] for r in linhas),
        "contagens": {
            "releases_lead_time_ausentes": sum(r["releases_lead_time_ausentes"] for r in linhas),
            "releases_cfr_censuradas_observadas": sum(r["releases_cfr_censuradas"] or 0 for r in linhas),
            "repositorios_cfr_releases_ausente": sum(r["cfr_releases_proxy_v3"] is None for r in linhas),
            "repositorios_censura_releases_desconhecida": sum(r["releases_cfr_censuradas"] is None for r in linhas),
            "releases_avaliacao_ausente": sum(r["n_releases_avaliacao_ausente"] for r in censura_releases),
            "episodios_recuperados_observados": sum(r["episodios_recuperados"] or 0 for r in linhas),
            "episodios_censurados_observados": sum(r["episodios_censurados"] or 0 for r in linhas),
            "repositorios_sem_episodios_entre_os_cobertos": sum(r["episodios_recuperados"] == 0 and r["episodios_censurados"] == 0 for r in linhas),
        },
        "n_registros_ausencias": len(faltas),
        "saidas_sha256": {p.name: sha256(p) for p in sorted(destino.iterdir()) if p.is_file()},
    }
    (destino / "analise.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifesto


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--coleta", default="data/coleta_final")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--comparacoes")
    parser.add_argument("--saida", default="data/analises_rqs")
    args = parser.parse_args(argv)
    try:
        manifesto = executar(args.coleta, args.saida, args.config, args.comparacoes)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Análise interrompida sem resultados oficiais: {exc}", file=sys.stderr)
        return 2
    print(f"{manifesto['status']}: {manifesto['n_repositorios']} repositórios; "
          f"{manifesto['n_registros_ausencias']} registros de dados ausentes. Resultados em {args.saida}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
