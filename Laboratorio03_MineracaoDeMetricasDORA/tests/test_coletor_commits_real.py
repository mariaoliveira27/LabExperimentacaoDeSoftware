"""
Testes unitários para o ColetorCommits e cálculo empírico real de Lead Time (RQ02).
Atende aos requisitos da Issue #04 (Maria):
- Validação do endpoint compare (/repos/{owner}/{repo}/compare/{base}...{head})
- Tratamento de paginação via cabeçalho Link (rel="next")
- Tratamento de status 404 (tags inexistentes, apagadas ou reescritas)
- Integração ponta a ponta com calcular_lead_time_repositorio (variantes a e b)
"""

from datetime import datetime, timezone
import pytest

from api_client import GitHubClient
from coletor_commits import ColetorCommits
from metricas.calculo_metricas import (
    calcular_lead_time_release,
    calcular_lead_time_commits,
    calcular_lead_time_repositorio,
)


class MockGitHubClient:
    """Mock do GitHubClient para simular respostas HTTP e cabeçalhos de paginação."""

    def __init__(self, responses):
        # responses é um dicionário: endpoint -> (status_code, data, headers)
        self.responses = responses
        self.requested_urls = []

    def request(self, endpoint, params=None, use_cache=None):
        self.requested_urls.append((endpoint, params))
        # Extrai chave de busca
        for url_pattern, resp in self.responses.items():
            if url_pattern in endpoint:
                return resp
        return 404, {"message": "Not Found"}, {}

    @staticmethod
    def _extract_next_url(link_header):
        return GitHubClient._extract_next_url(link_header)


def test_coletor_commits_compare_sucesso_pagina_unica():
    """Valida coleta de commits em página única com campos author_date, sha e message."""
    raw_commits = [
        {
            "sha": "a" * 40,
            "commit": {
                "author": {"date": "2024-03-01T10:00:00Z"},
                "message": "feat: primeira feature",
            },
        },
        {
            "sha": "b" * 40,
            "commit": {
                "author": {"date": "2024-03-05T14:30:00Z"},
                "message": "fix: resolve bug crítico de inicialização",
            },
        },
    ]

    mock_client = MockGitHubClient({
        "/compare/v1.0.0...v1.1.0": (
            200,
            {"total_commits": 2, "commits": raw_commits},
            {},
        )
    })

    coletor = ColetorCommits(mock_client)
    resultado = coletor.coletar_commits_entre_releases("owner", "repo", "v1.0.0", "v1.1.0")

    assert resultado is not None
    assert len(resultado) == 2
    assert resultado[0]["sha"] == "a" * 40
    assert resultado[0]["author_date"] == datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)
    assert resultado[0]["message"] == "feat: primeira feature"
    assert resultado[1]["sha"] == "b" * 40
    assert resultado[1]["author_date"] == datetime(2024, 3, 5, 14, 30, tzinfo=timezone.utc)


def test_coletor_commits_compare_paginacao_com_link_header():
    """Valida a paginação completa do endpoint compare seguindo o cabeçalho Link rel='next'."""
    page_1_commits = [
        {
            "sha": f"{i + 1:040x}",
            "commit": {
                "author": {"date": "2024-02-01T08:00:00Z"},
                "message": f"commit lote 1 - {i}",
            },
        }
        for i in range(100)
    ]

    page_2_commits = [
        {
            "sha": f"{i + 101:040x}",
            "commit": {
                "author": {"date": f"2024-02-{i + 15:02d}T09:00:00Z"},
                "message": f"commit lote 2 - {i}",
            },
        }
        for i in range(5)
    ]

    url_p1 = "/repos/facebook/react/compare/v18.0.0...v18.1.0"
    url_p2 = "https://api.github.com/repositories/10270250/compare/v18.0.0...v18.1.0?page=2&per_page=100"

    link_header = f'<{url_p2}>; rel="next", <https://api.github.com/...>; rel="last"'

    mock_client = MockGitHubClient({
        url_p1: (200, {"total_commits": 105, "commits": page_1_commits}, {"Link": link_header}),
        url_p2: (200, {"total_commits": 105, "commits": page_2_commits}, {}),
    })

    coletor = ColetorCommits(mock_client)
    resultado = coletor.coletar_commits_entre_releases("facebook", "react", "v18.0.0", "v18.1.0")

    assert resultado is not None
    assert len(resultado) == 105
    assert resultado[0]["sha"] == f"{1:040x}"
    assert resultado[99]["sha"] == f"{100:040x}"
    assert resultado[100]["sha"] == f"{101:040x}"
    assert resultado[104]["sha"] == f"{105:040x}"
    # Verifica que ambas as URLs foram requisitadas
    assert len(mock_client.requested_urls) == 2


def test_coletor_commits_compare_404_tag_inexistente_ou_reescrita():
    """Valida que status 404 retorna None conforme especificação operacional."""
    mock_client = MockGitHubClient({
        "/compare/tag_inexistente...v2.0.0": (404, {"message": "Not Found"}, {}),
    })

    coletor = ColetorCommits(mock_client)
    resultado = coletor.coletar_commits_entre_releases("owner", "repo", "tag_inexistente", "v2.0.0")

    assert resultado is None


def test_coletor_commits_recusa_comparacao_com_data_invalida():
    """Ignorar datas corrompidas alteraria o denominador e o Lead Time observado."""
    raw_commits = [
        {"sha": "a" * 40, "commit": {"author": None, "message": "sem autor"}},
        {"sha": "b" * 40, "commit": {"author": {"date": "data_invalida"}, "message": "data corrompida"}},
        {"sha": "c" * 40, "commit": {"author": {"date": "2024-04-10T12:00:00Z"}, "message": "valido"}},
    ]

    mock_client = MockGitHubClient({
        "/compare/v1...v2": (200, {"total_commits": 3, "commits": raw_commits}, {}),
    })

    coletor = ColetorCommits(mock_client)
    resultado = coletor.coletar_commits_entre_releases("o", "r", "v1", "v2")

    assert resultado is None


def test_coletor_commits_falha_de_rede_retorna_none():
    """Valida que falha transitória ou exceção inesperada retorna None com log de aviso."""
    class ClientComFalha:
        def request(self, *args, **kwargs):
            raise ConnectionResetError("Conexão interrompida pelo host")

    coletor = ColetorCommits(ClientComFalha())
    resultado = coletor.coletar_commits_entre_releases("owner", "repo", "v1", "v2")
    assert resultado is None


def test_integracao_coletor_com_calculo_lead_time_real():
    """
    Testa integração ponta a ponta:
    1. Coleta commits paginados via ColetorCommits
    2. Alimenta calcular_lead_time_repositorio
    3. Valida cálculo numérico exato das variantes (a) e (b) da RQ02
    """
    commits_rel1 = [
        {"sha": f"{1:040x}", "commit": {"author": {"date": "2024-01-01T00:00:00Z"}, "message": "c1"}},  # 10 dias antes de rel1
        {"sha": f"{2:040x}", "commit": {"author": {"date": "2024-01-05T00:00:00Z"}, "message": "c2"}},  # 6 dias antes de rel1
        {"sha": f"{3:040x}", "commit": {"author": {"date": "2024-01-09T00:00:00Z"}, "message": "c3"}},  # 2 dias antes de rel1
    ]
    # Release 1: data 2024-01-11T00:00:00Z.
    # LT Variante a: 11 - 1 = 10 dias
    # LT Variante b: [10, 6, 2] dias

    commits_rel2 = [
        {"sha": f"{4:040x}", "commit": {"author": {"date": "2024-01-15T00:00:00Z"}, "message": "c4"}},  # 5 dias antes de rel2
        {"sha": f"{5:040x}", "commit": {"author": {"date": "2024-01-19T00:00:00Z"}, "message": "c5"}},  # 1 dia antes de rel2
    ]
    # Release 2: data 2024-01-20T00:00:00Z.
    # LT Variante a: 20 - 15 = 5 dias
    # LT Variante b: [5, 1] dias

    # Agregado:
    # LT Variante a (mediana de [10, 5]): (10 + 5) / 2 = 7.5 dias
    # LT Variante b (mediana de [10, 6, 2, 5, 1] -> ordenado [1, 2, 5, 6, 10]): 5.0 dias

    mock_client = MockGitHubClient({
        "/compare/v1.0.0...v1.1.0": (200, {"total_commits": 3, "commits": commits_rel1}, {}),
        "/compare/v1.1.0...v1.2.0": (200, {"total_commits": 2, "commits": commits_rel2}, {}),
    })

    coletor = ColetorCommits(mock_client)

    # Simula o pipeline coletando para as releases consecutivas
    c1 = coletor.coletar_commits_entre_releases("org", "proj", "v1.0.0", "v1.1.0")
    c2 = coletor.coletar_commits_entre_releases("org", "proj", "v1.1.0", "v1.2.0")

    releases_data = [
        {
            "release_date": datetime(2024, 1, 11, 0, 0, tzinfo=timezone.utc),
            "commit_dates": [c["author_date"] for c in c1],
        },
        {
            "release_date": datetime(2024, 1, 20, 0, 0, tzinfo=timezone.utc),
            "commit_dates": [c["author_date"] for c in c2],
        },
    ]

    mediana_a, mediana_b, total_comms = calcular_lead_time_repositorio(releases_data)

    assert total_comms == 5
    assert mediana_a == pytest.approx(7.5)
    assert mediana_b == pytest.approx(5.0)


def commit_original(indice):
    return {"sha": f"{indice:040x}", "commit": {
        "author": {"date": "2024-01-01T00:00:00Z"}, "message": "fix: fixture"}}


@pytest.mark.parametrize("status", [403, 404, 422, 500])
def test_erro_apos_primeira_pagina_nunca_retorna_prefixo(status):
    primeiro = "/repos/org/proj/compare/v1...v2"
    segundo = "https://api.github.com/repositories/123/compare/v1...v2?page=2&per_page=100"
    client = MockGitHubClient({
        primeiro: (200, {"total_commits": 101, "commits": [commit_original(i) for i in range(100)]},
                   {"Link": f'<{segundo}>; rel="next"'}),
        segundo: (status, {"message": "indisponível"}, {}),
    })
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "v1", "v2") is None
    assert len(client.requested_urls) == 2


@pytest.mark.parametrize("mutacao", [
    "total_ausente", "total_booleano", "total_negativo", "total_menor", "truncada_sem_link",
    "sha_repetido", "sha_invalido", "sem_fuso", "data_invalida", "sem_mensagem", "sem_lista",
])
def test_recusa_resposta_sem_prova_de_completude(mutacao):
    resposta = {"total_commits": 2, "commits": [commit_original(1), commit_original(2)]}
    if mutacao == "total_ausente":
        resposta.pop("total_commits")
    elif mutacao == "total_booleano":
        resposta["total_commits"] = True
    elif mutacao == "total_negativo":
        resposta["total_commits"] = -1
    elif mutacao == "total_menor":
        resposta["total_commits"] = 1
    elif mutacao == "truncada_sem_link":
        resposta = {"total_commits": 101, "commits": [commit_original(i) for i in range(100)]}
    elif mutacao == "sha_repetido":
        resposta["commits"][1]["sha"] = resposta["commits"][0]["sha"]
    elif mutacao == "sha_invalido":
        resposta["commits"][0]["sha"] = "curto"
    elif mutacao == "sem_fuso":
        resposta["commits"][0]["commit"]["author"]["date"] = "2024-01-01T00:00:00"
    elif mutacao == "data_invalida":
        resposta["commits"][0]["commit"]["author"]["date"] = "inválida"
    elif mutacao == "sem_mensagem":
        resposta["commits"][0]["commit"].pop("message")
    elif mutacao == "sem_lista":
        resposta["commits"] = None
    client = MockGitHubClient({"/compare/v1...v2": (200, resposta, {})})
    client.invalidated = []
    client.invalidate_cache = lambda endpoint, params: client.invalidated.append((endpoint, params))
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "v1", "v2") is None
    assert client.invalidated == [("/repos/org/proj/compare/v1...v2", {"page": 1, "per_page": 100})]


@pytest.mark.parametrize("mutacao", ["total_mutante", "sha_duplicado_entre_paginas", "pagina_vazia"])
def test_segunda_pagina_invalida_invalida_comparacao_inteira(mutacao):
    primeiro = "/repos/org/proj/compare/v1...v2"
    segundo = "https://api.github.com/repositories/123/compare/v1...v2?page=2&per_page=100"
    resposta2 = {"total_commits": 101, "commits": [commit_original(101)]}
    if mutacao == "total_mutante":
        resposta2["total_commits"] = 102
    elif mutacao == "sha_duplicado_entre_paginas":
        resposta2["commits"][0] = commit_original(1)
    else:
        resposta2["commits"] = []
    client = MockGitHubClient({
        primeiro: (200, {"total_commits": 101, "commits": [commit_original(i) for i in range(100)]},
                   {"link": f'<{segundo}>; rel="next"'}),
        segundo: (200, resposta2, {}),
    })
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "v1", "v2") is None


@pytest.mark.parametrize("next_url", [
    "https://api.github.com/repos/org/proj/compare/v1...v2?page=1&per_page=100",
    "https://api.github.com/repos/org/proj/compare/v1...v2?page=3&per_page=100",
    "https://api.github.com/repos/org/proj/compare/v1...v3?page=2&per_page=100",
    "https://outro.example/compare/v1...v2?page=2&per_page=100",
])
def test_recusa_link_ciclico_pagina_pulada_ou_outra_comparacao(next_url):
    client = MockGitHubClient({"/repos/org/proj/compare/v1...v2": (
        200, {"total_commits": 101, "commits": [commit_original(i) for i in range(100)]},
        {"Link": f'<{next_url}>; rel="next"'})})
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "v1", "v2") is None
    assert len(client.requested_urls) == 1


def test_zero_comprovado_e_tags_codificadas():
    client = MockGitHubClient({"/compare/release%2Fv1...release%2Fv2": (
        200, {"total_commits": 0, "commits": []}, {})})
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "release/v1", "release/v2") == []
    assert client.requested_urls == [(
        "/repos/org/proj/compare/release%2Fv1...release%2Fv2", {"page": 1, "per_page": 100})]


def test_link_extra_apos_total_nao_e_aceito():
    client = MockGitHubClient({"/compare/v1...v2": (
        200, {"total_commits": 1, "commits": [commit_original(1)]},
        {"Link": '<https://api.github.com/repos/org/proj/compare/v1...v2?page=2&per_page=100>; rel="next"'})})
    assert ColetorCommits(client).coletar_commits_entre_releases("org", "proj", "v1", "v2") is None
