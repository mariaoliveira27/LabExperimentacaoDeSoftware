"""Busca real de candidatos, sem truncar silenciosamente o teto do GitHub.

Cada fatia deve conter menos de 1.000 resultados. Faixas de estrelas são
particionadas sem sobreposição; uma estrela única é particionada pela data
real de criação. Respostas incompletas ou mutáveis interrompem a busca.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re


TETO_BUSCA = 1000
POR_PAGINA = 100
ENDPOINT = "/search/repositories"


class CandidatosBusca(list):
    """Lista de objetos REST com relatório explícito sobre o limite da busca."""

    def __init__(self, items, relatorio):
        super().__init__(items)
        self.relatorio = relatorio


def _data_criacao(valor):
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if instante.tzinfo is None:
            raise ValueError("sem fuso horário")
        return instante.astimezone(timezone.utc).date()
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"created_at inválido na busca: {valor!r}.") from exc


def _invalidar(client, params):
    invalidar = getattr(client, "invalidate_cache", None)
    if callable(invalidar):
        invalidar(ENDPOINT, params=params)


def _consulta(client, q, estrelas, datas, consultas, *, page=1, per_page=POR_PAGINA, sort="stars", order="desc"):
    params = {"q": q, "sort": sort, "order": order, "per_page": per_page, "page": page}
    try:
        status, payload, _ = client.request(ENDPOINT, params=params)
        if status != 200:
            raise RuntimeError(f"Busca interrompida: HTTP {status} em {q!r}, página {page}.")
        if not isinstance(payload, dict):
            raise ValueError("Busca deve retornar um objeto JSON.")
        total = payload.get("total_count")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise ValueError("total_count ausente ou inválido na busca.")
        if payload.get("incomplete_results") is not False:
            raise ValueError("Busca incompleta: incomplete_results deve ser false; não há população verificável.")
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("items deve ser uma lista na busca.")
        quantidade = min(per_page, max(0, min(total, TETO_BUSCA) - (page - 1) * per_page))
        if len(items) != quantidade:
            raise ValueError(
                f"Página de busca incompleta ou inconsistente: {len(items)} itens, "
                f"esperados {quantidade}; total_count={total}."
            )
        ids, nomes = set(), set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Repositório da busca deve ser objeto REST.")
            identificador, nome, stars = item.get("id"), item.get("full_name"), item.get("stargazers_count")
            if isinstance(identificador, bool) or not isinstance(identificador, int) or identificador <= 0:
                raise ValueError("id de repositório ausente ou inválido na busca.")
            if not isinstance(nome, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", nome):
                raise ValueError("full_name ausente ou inválido na busca.")
            if item.get("private") is not False:
                raise ValueError(f"Busca de projetos públicos retornou private inválido: {nome}.")
            if isinstance(stars, bool) or not isinstance(stars, int) or stars < estrelas[0] or (estrelas[1] is not None and stars > estrelas[1]):
                raise ValueError(f"Repositório fora da faixa de estrelas consultada: {nome}.")
            criada = _data_criacao(item.get("created_at"))
            if criada > datas[1] or (datas[0] is not None and criada < datas[0]):
                raise ValueError(f"Repositório fora da faixa de criação consultada: {nome}.")
            if identificador in ids or nome.casefold() in nomes:
                raise ValueError("Busca contém ids ou full_name duplicados na página.")
            ids.add(identificador)
            nomes.add(nome.casefold())
    except (ValueError, RuntimeError):
        _invalidar(client, params)
        raise
    consultas.append({**params, "total_count": total, "items_recebidos": len(items)})
    return payload


def _query(estrelas, datas):
    minimo, maximo = estrelas
    stars = f"stars:>={minimo}" if maximo is None else f"stars:{minimo}..{maximo}"
    inicio, fim = datas
    created = f"created:<={fim.isoformat()}" if inicio is None else f"created:{inicio.isoformat()}..{fim.isoformat()}"
    return f"{stars} {created} is:public"


def buscar_candidatos(client, min_stars=1000, criado_ate="2024-09-30", max_candidatos=5000):
    """Retorna candidatos reais ordenados por estrelas, nome e id.

    O resultado é uma subclasse de ``list``; ``resultado.relatorio`` registra
    as consultas e distingue quota de candidatos de uma busca completa. Essa
    lista ainda não é a amostra aprovada: releases e runs requerem coleta e
    validação posteriores. ``max_candidatos=None`` solicita busca completa.
    """
    if isinstance(min_stars, bool) or not isinstance(min_stars, int) or min_stars < 0:
        raise ValueError("min_stars deve ser inteiro não negativo.")
    if max_candidatos is not None and (
        isinstance(max_candidatos, bool) or not isinstance(max_candidatos, int) or max_candidatos <= 0
    ):
        raise ValueError("max_candidatos deve ser inteiro positivo ou None.")
    try:
        fim = date.fromisoformat(criado_ate)
        if fim.isoformat() != criado_ate:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ValueError("criado_ate deve ser uma data YYYY-MM-DD.") from exc

    consultas, coletados = [], []
    ids, nomes = set(), set()

    def consultar(estrelas, datas, **kwargs):
        return _consulta(client, _query(estrelas, datas), estrelas, datas, consultas, **kwargs)

    def quota_atingida():
        return max_candidatos is not None and len(coletados) >= max_candidatos

    def adicionar(items, estrelas, datas, page):
        for item in items:
            identificador, nome = item["id"], item["full_name"].casefold()
            if identificador in ids or nome in nomes:
                params = {"q": _query(estrelas, datas), "sort": "stars", "order": "desc", "per_page": POR_PAGINA, "page": page}
                _invalidar(client, params)
                raise ValueError("Busca contém ids ou full_name duplicados entre páginas/fatias; população mudou ou há sobreposição.")
            ids.add(identificador)
            nomes.add(nome)
            coletados.append(item)

    def visitar(estrelas, datas, primeira):
        total = primeira["total_count"]
        if total < TETO_BUSCA:
            adicionar(primeira["items"], estrelas, datas, 1)
            for page in range(2, (total + POR_PAGINA - 1) // POR_PAGINA + 1):
                payload = consultar(estrelas, datas, page=page)
                if payload["total_count"] != total:
                    params = {key: value for key, value in consultas[-1].items() if key not in ("total_count", "items_recebidos")}
                    _invalidar(client, params)
                    raise ValueError("total_count mudou entre páginas; a busca não é uma população consistente.")
                adicionar(payload["items"], estrelas, datas, page)
            return

        minimo, maximo = estrelas
        if maximo is None:
            # A consulta ordenada por estrelas fornece seu máximo real, não um
            # limite fixo que excluiria projetos mais populares.
            maximo = primeira["items"][0]["stargazers_count"]
            if any(item["stargazers_count"] > maximo for item in primeira["items"]):
                raise ValueError("Busca ordenada por estrelas não informa o maior valor na primeira posição.")
        if minimo < maximo:
            meio = (minimo + maximo) // 2
            esquerda, direita = (minimo, meio), (meio + 1, maximo)
            primeira_direita = consultar(direita, datas)
            primeira_esquerda = consultar(esquerda, datas)
            if primeira_direita["total_count"] + primeira_esquerda["total_count"] != total:
                raise ValueError("total_count das faixas de estrelas não soma a população anterior; busca mudou.")
            visitar(direita, datas, primeira_direita)
            if not quota_atingida():
                visitar(esquerda, datas, primeira_esquerda)
            return

        estrelas = (minimo, maximo)
        inicio, fim_data = datas
        if inicio is None:
            # Search Repositories não permite sort=created. Descubra o menor
            # dia observado e sonde datas anteriores até uma resposta vazia
            # comprovar que ele é o mínimo real da faixa, sem um ano inicial
            # fixo que excluiria repositórios antigos.
            inicio = min(_data_criacao(item["created_at"]) for item in primeira["items"])
            total_anterior = total
            while inicio > date.min:
                anteriores = consultar(estrelas, (None, inicio - timedelta(days=1)))
                if anteriores["total_count"] >= total_anterior:
                    raise ValueError("total_count não diminuiu ao excluir datas observadas; busca mudou.")
                if anteriores["total_count"] == 0:
                    break
                inicio = min(_data_criacao(item["created_at"]) for item in anteriores["items"])
                total_anterior = anteriores["total_count"]
        if inicio == fim_data:
            raise ValueError(
                f"Faixa inseparável: {total} repositórios com {minimo} estrelas criados "
                f"em {inicio.isoformat()}; teto de 1.000 da busca. Refine os critérios "
                "com um particionamento adicional; nenhum resultado completo foi produzido."
            )
        meio_data = inicio + timedelta(days=(fim_data - inicio).days // 2)
        esquerda, direita = (inicio, meio_data), (meio_data + timedelta(days=1), fim_data)
        primeira_direita = consultar(estrelas, direita)
        primeira_esquerda = consultar(estrelas, esquerda)
        if primeira_direita["total_count"] + primeira_esquerda["total_count"] != total:
            raise ValueError("total_count das faixas de criação não soma a população anterior; busca mudou.")
        visitar(estrelas, direita, primeira_direita)
        if not quota_atingida():
            visitar(estrelas, esquerda, primeira_esquerda)

    estrelas_raiz, datas_raiz = (min_stars, None), (None, fim)
    raiz = consultar(estrelas_raiz, datas_raiz)
    visitar(estrelas_raiz, datas_raiz, raiz)
    ordenados = sorted(coletados, key=lambda item: (-item["stargazers_count"], item["full_name"].casefold(), item["id"]))
    resultado = ordenados if max_candidatos is None else ordenados[:max_candidatos]
    limitado = max_candidatos is not None and raiz["total_count"] > max_candidatos
    if not limitado and len(resultado) != raiz["total_count"]:
        raise ValueError("Quantidade coletada difere de total_count da população inicial.")
    return CandidatosBusca(resultado, {
        "fonte": "github_search_api", "endpoint": ENDPOINT,
        "min_stars": min_stars, "criado_ate": criado_ate,
        "max_candidatos": max_candidatos, "total_count_raiz": raiz["total_count"],
        "candidatos_coletados": len(coletados), "candidatos_retornados": len(resultado),
        "limitado_por_max_candidatos": limitado, "busca_completa": not limitado,
        "ordenacao": "stargazers_count desc, full_name casefold asc, id asc",
        "consultas": consultas,
        "observacao": "Candidatos de busca; a aprovação por releases e runs ainda não foi realizada.",
    })
