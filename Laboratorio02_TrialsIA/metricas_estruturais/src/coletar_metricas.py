"""Coleta estática de RQ3 por rodada, sem importar ou executar a solução."""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tokenize
from pathlib import Path

from radon.complexity import cc_visit_ast
from radon.raw import analyze


class _FuncoesPorEscopo(ast.NodeVisitor):
    """Enumera cada definição uma vez, inclusive em classes locais e closures."""

    def __init__(self) -> None:
        self.escopos: list[str] = []
        self.funcoes: list[dict] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.escopos.append(node.name)
        self.generic_visit(node)
        self.escopos.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # O Radon calcula o bloco desta definição sem somar a CC das closures.
        # A enumeração pela AST também encontra métodos de classes dentro de
        # funções, que não aparecem na lista de closures fornecida pelo Radon.
        bloco = cc_visit_ast(node)[0]
        self.funcoes.append({
            "nome": ".".join([*self.escopos, node.name]),
            "linha": node.lineno,
            "complexidade": bloco.complexity,
        })
        self.escopos.append(node.name)
        self.generic_visit(node)
        self.escopos.pop()

    visit_AsyncFunctionDef = visit_FunctionDef


def analisar_arquivo(arquivo: str | Path, trial_id: str) -> dict:
    """Retorna o registro schema 1; falhas de leitura/análise viram dados de erro.

    Não escreve arquivos. O caminho é preservado como recebido e nomes de
    funções incluem os escopos lexicais. Nenhuma solução é importada/executada.
    """
    resultado = {
        "schema_version": 1,
        "trial_id": trial_id,
        "arquivo": str(arquivo),
        "status_analise": "ok",
        "erro": None,
        "quantidade_funcoes": None,
        "complexidade_media": None,
        "loc": None,
        "sloc": None,
        "funcoes": None,
    }
    try:
        # utf-8-sig aceita UTF-8 com ou sem BOM, comum em editores Windows.
        fonte = Path(arquivo).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError, ValueError) as exc:
        return _registrar_erro(resultado, "erro_leitura", exc)

    try:
        arvore = ast.parse(fonte, filename=str(arquivo))
        # Valida também erros de contexto (ex.: return fora de função).
        # Compilar não executa o código nem resolve seus imports.
        compile(arvore, str(arquivo), "exec", dont_inherit=True)
        visitante = _FuncoesPorEscopo()
        visitante.visit(arvore)
        brutas = analyze(fonte)
    except SyntaxError as exc:
        return _registrar_erro(resultado, "erro_sintaxe", exc)
    except (ValueError, tokenize.TokenError, RecursionError) as exc:
        return _registrar_erro(resultado, "erro_analise", exc)

    funcoes = sorted(visitante.funcoes, key=lambda funcao: funcao["linha"])
    quantidade = len(funcoes)
    resultado.update({
        "quantidade_funcoes": quantidade,
        "complexidade_media": (
            sum(funcao["complexidade"] for funcao in funcoes) / quantidade
            if quantidade else None
        ),
        "loc": brutas.loc,
        "sloc": brutas.sloc,
        "funcoes": funcoes,
    })
    return resultado


def _registrar_erro(resultado: dict, status: str, erro: Exception) -> dict:
    resultado["status_analise"] = status
    resultado["erro"] = {"tipo": type(erro).__name__, "mensagem": str(erro)}
    return resultado


def gravar_resultado(resultado: dict, saida: str | Path) -> None:
    """Grava JSON UTF-8 sem sobrescrever; OSError deve ser tratado pelo chamador.

    O diretório de destino deve existir. Em falha durante a escrita, tenta
    remover apenas o arquivo recém-criado para não deixar JSON parcial.
    """
    texto = json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    destino = Path(saida)
    # A abertura exclusiva evita sobrescrita inclusive entre processos.
    with destino.open("x", encoding="utf-8", newline="\n") as fluxo:
        try:
            fluxo.write(texto)
            fluxo.flush()
        except OSError:
            fluxo.close()
            try:
                destino.unlink()
            except OSError:
                pass
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", required=True, help="Cópia final da solução Python (UTF-8).")
    parser.add_argument("--trial-id", required=True, help="Identificador compartilhado da rodada.")
    parser.add_argument("--saida", required=True, help="Novo arquivo JSON; o diretório deve existir.")
    args = parser.parse_args(argv)

    resultado = analisar_arquivo(args.arquivo, args.trial_id)
    if resultado["erro"] is not None:
        print(
            f"Falha na análise de '{args.arquivo}': "
            f"{resultado['erro']['tipo']}: {resultado['erro']['mensagem']}",
            file=sys.stderr,
        )
    try:
        gravar_resultado(resultado, args.saida)
    except FileExistsError:
        print(
            f"Resultado já existe em '{args.saida}'; use outro destino. Nenhum arquivo foi sobrescrito.",
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError) as exc:
        print(f"Falha ao gravar JSON em '{args.saida}': {exc}", file=sys.stderr)
        return 2

    print(f"JSON gravado em '{args.saida}' (trial_id={args.trial_id}).")
    return 0 if resultado["status_analise"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
