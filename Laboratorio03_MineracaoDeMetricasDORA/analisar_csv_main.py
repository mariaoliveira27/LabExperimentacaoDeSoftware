"""Descreve métricas já calculadas no CSV fornecido pela main.

Este comando não executa coleta, não audita critérios de inclusão e não
reconstitui runs ou commits. A origem empírica dos valores não foi validada.
As análises de bundles com evidência original continuam em analisar_rqs.py.
"""

import argparse
import csv
from datetime import datetime
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import re
import sys

import yaml

from analisar_rqs import resumir


METRICAS = (
    ("RQ01", "deployment_frequency_semana", "releases/semana", "Frequência de entrega"),
    ("RQ02", "lead_time_release_mediana_dias", "dias", "Lead time (a), por release"),
    ("RQ02", "lead_time_commit_mediana_dias", "dias", "Lead time (b), por commit"),
    ("RQ03", "cfr_ci_proxy", "proporção", "CFR: proxy de CI declarado"),
    ("RQ03", "cfr_releases_proxy", "proporção", "CFR: proxy de releases declarado"),
    ("RQ04", "tempo_recuperacao_mediana_horas", "horas", "Mediana de recuperação declarada"),
    ("RQ04", "proporcao_episodios_censurados", "proporção", "Proporção de censura declarada"),
)
CONTAGENS = ("episodios_recuperados", "episodios_censurados")
PROPORCOES = {"cfr_ci_proxy", "cfr_releases_proxy", "proporcao_episodios_censurados"}
AVISO = "Valores fornecidos; origem empírica não validada"
AUDITORIA = "data/execucao_pos_main/auditoria_dados.json"
STATUS = "analise_descritiva_de_valores_fornecidos"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _numero(valor, campo, linha, inteiro=False):
    """Somente célula vazia representa ausência; NaN/Inf são erros."""
    valor = valor.strip()
    if not valor:
        return None
    try:
        numero = float(valor)
    except ValueError as exc:
        raise ValueError(f"Linha {linha}: {campo} deve ser numérico ou vazio.") from exc
    if not math.isfinite(numero) or numero < 0:
        raise ValueError(f"Linha {linha}: {campo} deve ser finito e não negativo.")
    if campo in PROPORCOES and numero > 1:
        raise ValueError(f"Linha {linha}: {campo} deve estar entre 0 e 1.")
    if inteiro:
        if not numero.is_integer():
            raise ValueError(f"Linha {linha}: {campo} deve ser uma contagem inteira.")
        # O limite impede a perda silenciosa de precisão de float em contagens.
        if numero > 2**53 - 1:
            raise ValueError(f"Linha {linha}: {campo} excede a precisão de contagem suportada.")
        return int(numero)
    return numero


def ler_csv(path):
    """Valida a forma e os domínios, sem promover declarações a evidências."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        campos = reader.fieldnames
        exigidos = {"full_name", *(metrica[1] for metrica in METRICAS)}
        if not campos or len(campos) != len(set(campos)) or any(not c for c in campos):
            raise ValueError("Cabeçalho vazio ou com colunas duplicadas/vazias.")
        faltam = exigidos - set(campos)
        if faltam:
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(faltam))}.")
        linhas, nomes = [], set()
        for numero, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Linha {numero}: quantidade de células diverge do cabeçalho.")
            nome = row["full_name"].strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", nome):
                raise ValueError(f"Linha {numero}: full_name inválido.")
            if nome.casefold() in nomes:
                raise ValueError(f"Unidade full_name duplicada: {nome}.")
            nomes.add(nome.casefold())
            row["full_name"] = nome
            for _, campo, _, _ in METRICAS:
                row[campo] = _numero(row[campo], campo, numero)
            for campo in CONTAGENS:
                if campo in row:
                    row[campo] = _numero(row[campo], campo, numero, inteiro=True)
            linhas.append(row)
    if not linhas:
        raise ValueError("O CSV deve conter ao menos um repositório.")
    return campos, linhas


def _config(path):
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or not isinstance(cfg.get("window"), dict):
        raise ValueError("Configuração sem janela declarada.")
    janela = cfg["window"]
    try:
        inicio, fim = (datetime.fromisoformat(str(janela[c]).replace("Z", "+00:00"))
                       for c in ("start_date", "end_date"))
        semanas = float(janela["weeks"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Janela declarada inválida na configuração.") from exc
    if (inicio.tzinfo is None or fim.tzinfo is None or fim <= inicio
            or not math.isfinite(semanas) or semanas <= 0):
        raise ValueError("Datas devem ter fuso e ordem válida; semanas devem ser positivas e finitas.")
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "semanas": semanas}


def _csv(path, rows, campos):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=campos)
        writer.writeheader()
        writer.writerows(rows)


def identificar_origem(auditoria, hash_csv):
    """Vincula o parecer anterior aos mesmos bytes, sem auditar fontes novas."""
    if auditoria.is_file():
        parecer = json.loads(auditoria.read_text(encoding="utf-8"))
        if (isinstance(parecer, dict) and "gerados" in parecer.get("conclusao", "")
                and any(fonte.get("sha256") == hash_csv
                        for fonte in parecer.get("fontes", []) if isinstance(fonte, dict))):
            return "seed_data.py/consolidar_dataset.py; valores gerados por fórmulas"
    return "nao_estabelecida_pelas_evidencias_preservadas"


def graficos(destino, sumarios):
    """Mediana e quartis de unidades do CSV; sem inventar distribuições brutas."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with plt.rc_context({"svg.fonttype": "none", "font.size": 10}):
        for rq in ("RQ01", "RQ02", "RQ03", "RQ04"):
            dados = [s for s in sumarios if s["rq"] == rq]
            fig, axes = plt.subplots(len(dados), 1, figsize=(10, 2 + 1.8 * len(dados)), squeeze=False)
            fig.suptitle(f"{rq} · Mediana e intervalo interquartil por repositório", fontsize=14, y=.98)
            for ax, dado in zip(axes[:, 0], dados):
                titulo = next(m[3] for m in METRICAS if m[1] == dado["metrica"])
                ax.set_title(f"{titulo} — n={dado['n_validos']}/{dado['n_total']}; "
                             f"ausentes={dado['n_ausentes']}", loc="left", fontsize=10)
                ax.set_xlabel(dado["unidade"])
                ax.set_yticks([])
                ax.set_ylim(-1, 1)
                ax.spines[["top", "left", "right"]].set_visible(False)
                ax.grid(axis="x", alpha=.2)
                if dado["n_validos"]:
                    ax.hlines(0, dado["q1"], dado["q3"], color="#245e91", linewidth=12)
                    ax.plot(dado["mediana"], 0, "|", markersize=23, color="#152c41", markeredgewidth=3)
                    ax.set_xlim(0, max(dado["q3"] * 1.2, 1e-6))
                    ax.text(.01, .1, f"Q1={dado['q1']:.5g}; mediana={dado['mediana']:.5g}; "
                            f"Q3={dado['q3']:.5g}; IQR={dado['iqr']:.5g}", transform=ax.transAxes)
                else:
                    ax.text(.02, .5, "Nenhum valor fornecido", transform=ax.transAxes)
            fig.text(.5, .02, AVISO, ha="center", fontsize=10, color="#7a351a")
            fig.tight_layout(rect=(0, .08, 1, .93))
            for extensao in ("svg", "png"):
                fig.savefig(destino / f"{rq.lower()}_mediana_iqr.{extensao}", dpi=160)
            plt.close(fig)


def executar(csv_path, saida, config="config.yaml", commit_origem=None):
    """Cria uma saída exclusiva e mantém as entradas intactas."""
    destino = Path(saida)
    if destino.exists():
        raise FileExistsError(f"Saída preservada: {destino} já existe; use outro diretório.")
    if commit_origem is not None and not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit_origem):
        raise ValueError("Commit de origem deve ser um SHA Git de 7 a 40 caracteres hexadecimais.")
    campos, linhas = ler_csv(csv_path)
    janela = _config(config)
    entradas = {"csv": sha256(csv_path), "config": sha256(config)}
    sumarios = [dict(rq=rq, metrica=campo, unidade_observacao="repositorio", unidade=unidade,
                     **resumir(row[campo] for row in linhas))
                for rq, campo, unidade, _ in METRICAS]
    # resumir também atende episódios auditados; aqui a unidade é projeto e
    # nenhuma contagem de censura pode ser inferida de valores agregados.
    for sumario in sumarios:
        del sumario["n_censurados"]
    contagens = [dict(full_name=row["full_name"], **{campo: row.get(campo) for campo in CONTAGENS})
                for row in linhas]
    auditoria = Path(__file__).resolve().parent / AUDITORIA
    fontes = sorted({row.get("origem_coleta", "").strip() for row in linhas})
    manifesto = {
        "schema_version": 1,
        "status": STATUS,
        "aviso": AVISO,
        "origem_dos_valores": "csv_fornecido_pela_main",
        "origem_identificada": identificar_origem(auditoria, entradas["csv"]),
        "fonte_declarada": fontes[0] if len(fontes) == 1 and fontes[0] else fontes,
        "fonte_declarada_por": "campo origem_coleta do CSV; declaração não verificada",
        "evidencia_coleta_real_verificada": False,
        "criterios_inclusao_verificados": False,
        "cobertura_historica_verificada": False,
        "comparacoes_originais_verificadas": False,
        "janela_declarada_na_config": janela,
        "janela_do_csv_verificada": False,
        "n_unidades_no_csv": len(linhas),
        "commit_origem_declarado": commit_origem,
        "commit_origem_verificado_por_este_comando": False,
        "arquivo_csv": str(Path(csv_path).resolve()),
        "entradas_sha256": entradas,
        "codigo_sha256": {"analisar_csv_main.py": sha256(__file__),
                           "analisar_rqs.py": sha256(Path(__file__).with_name("analisar_rqs.py"))},
        "versoes": {"python": sys.version.split()[0], "PyYAML": version("PyYAML"),
                    "matplotlib": version("matplotlib")},
        "parecer_auditoria_preexistente": {"arquivo": AUDITORIA,
            "sha256": sha256(auditoria) if auditoria.is_file() else None},
        "quantis": "interpolacao_linear_tipo_7",
        "agregacao": "cada full_name tem peso igual; métricas lidas sem recalcular commits ou runs",
        "cfr_releases": "proxy declarado no CSV; versão da heurística não comprovada",
        "rq04": "contagens e medianas declaradas por projeto; sem episódios individuais ou "
                "estimativa de sobrevivência; não se infere mediana de episódios a partir de medianas",
        "contagens_presentes_no_csv": [campo for campo in CONTAGENS if campo in campos],
        "cobertura_por_metrica": [{k: s[k] for k in ("rq", "metrica", "n_total", "n_validos", "n_ausentes")}
                                  for s in sumarios],
    }
    destino.mkdir(parents=True, exist_ok=False)
    _csv(destino / "metricas_lidas.csv", linhas, campos)
    _csv(destino / "sumarios_rq01_rq04.csv", sumarios, list(sumarios[0]))
    _csv(destino / "rq04_contagens_declaradas.csv", contagens, ("full_name", *CONTAGENS))
    graficos(destino, sumarios)
    manifesto["saidas_sha256"] = {p.name: sha256(p) for p in sorted(destino.iterdir()) if p.is_file()}
    with (destino / "analise.json").open("x", encoding="utf-8") as stream:
        json.dump(manifesto, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return manifesto


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="CSV de métricas previamente calculadas")
    parser.add_argument("--saida", required=True, help="Diretório novo, exclusivo desta execução")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--commit-origem", help="SHA declarado da versão do CSV na main")
    args = parser.parse_args(argv)
    try:
        manifesto = executar(args.csv, args.saida, args.config, args.commit_origem)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Análise interrompida: {exc}", file=sys.stderr)
        return 2
    print(f"{manifesto['status']}: {manifesto['n_unidades_no_csv']} unidades. {AVISO}. Saída: {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
