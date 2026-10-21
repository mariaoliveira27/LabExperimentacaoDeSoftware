"""Diagnóstico real mensal da janela; não aprova repositórios nem produz DORA.

Exemplo: python verificar_cobertura_runs.py --repositorio microsoft/vscode
  --saida data/cobertura_s03/microsoft_vscode.json --usar-gh-auth
Em caso de falha, execute novamente para reutilizar as páginas em SQLite.
"""

import argparse
import json
from pathlib import Path
import re
import sys

import yaml

from coleta_amostra_real import ClienteAuditavel, agora, token_gh, _json_atomic
from coletor_runs import ColetorRuns
from gerar_amostra_rotulagem import instante, sha256


def verificar(repositorio, saida, config="config.yaml", usar_gh_auth=False, client=None):
    if not isinstance(repositorio, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repositorio):
        raise ValueError("Identificador deve ser owner/repo.")
    saida = Path(saida)
    if saida.exists():
        raise FileExistsError(f"Evidência preservada: {saida}; use outro destino.")
    configuracao = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    if not isinstance(configuracao, dict) or not isinstance(configuracao.get("window"), dict):
        raise ValueError("Configuração deve conter window.start_date e window.end_date.")
    inicio = instante(configuracao["window"].get("start_date"))
    fim = instante(configuracao["window"].get("end_date"))
    if inicio > fim:
        raise ValueError("Janela invertida.")
    saida.parent.mkdir(parents=True, exist_ok=True)
    auditoria = saida.parent / "requisicoes.jsonl"
    if client is None:
        client = ClienteAuditavel(auditoria, token=token_gh() if usar_gh_auth else None,
                                 cache_db_path=str(saida.parent / "cache/github_cache.db"),
                                 verify_ssl=True)
    status, metadata, _ = client.request(f"/repos/{repositorio}", use_cache=False)
    if (status != 200 or not isinstance(metadata, dict)
            or type(metadata.get("id")) is not int or metadata.get("id", 0) <= 0
            or not isinstance(metadata.get("default_branch"), str) or not metadata["default_branch"]
            or metadata.get("private") is not False
            or not isinstance(metadata.get("full_name"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", metadata["full_name"])):
        raise ValueError(f"Metadados públicos incompletos de {repositorio} (HTTP {status}).")
    coletor = ColetorRuns(client)
    relatorio = {}
    owner, repo = metadata["full_name"].split("/")
    try:
        runs = coletor.coletar_runs_janela(owner, repo, metadata["default_branch"], inicio, fim,
                                          relatorio_cobertura=relatorio)
    except Exception:
        incompleta = saida.with_suffix(".incompleta.json")
        tentativa = 1
        while incompleta.exists():
            incompleta = saida.with_suffix(f".incompleta.{tentativa}.json")
            tentativa += 1
        _json_atomic(incompleta, {
            "origem": "github_api", "coletado_em": agora(), "metadata": metadata,
            "cobertura_runs": relatorio, "aprovacao": "nao_avaliada",
        })
        raise
    resultado = {"schema_version": 1, "origem": "github_api", "modo_referencia": False,
                 "coletado_em": agora(), "config_sha256": sha256(config),
                 "metadata": metadata, "cobertura_runs": relatorio, "runs": runs,
                 "aprovacao": "nao_avaliada", "permite_metricas_dora_anuais": False}
    _json_atomic(saida, resultado)
    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repositorio", required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--usar-gh-auth", action="store_true")
    args = parser.parse_args(argv)
    try:
        resultado = verificar(args.repositorio, args.saida, args.config, args.usar_gh_auth)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Verificação incompleta: {exc}. Reexecute para retomar pelo cache.", file=sys.stderr)
        return 2
    cobertura = resultado["cobertura_runs"]
    print(f"Enumeração: {cobertura['enumeration_complete']}; runs disponíveis: {len(resultado['runs'])}; "
          f"intervalos: {len(cobertura['completed_intervals'])}; cobertura histórica anual: desconhecida. "
          f"Evidência: {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
