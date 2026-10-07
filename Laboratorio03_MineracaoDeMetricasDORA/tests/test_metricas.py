"""
Testes unitários para o módulo de cálculo das Métricas DORA (Lab03).
Garante cobertura >= 80% do pacote metricas conforme Seção 7 do README.
Testa:
- Exemplos numéricos da Seção 5 (RQ01, RQ02, RQ03, RQ04 e Classificação DORA)
- Casos de borda obrigatórios:
  * Release sem commits novos
  * Falha nunca recuperada (censurada)
  * Repositório com uma única release
  * Execuções cancelled, skipped, neutral (ignoradas)
  * Censura dos últimos 7 dias no CFR(b)
"""

import pytest
from datetime import datetime, timezone, timedelta
from metricas.calculo_metricas import (
    parse_datetime,
    calcular_deployment_frequency,
    calcular_lead_time_release,
    calcular_lead_time_commits,
    calcular_lead_time_repositorio,
    calcular_cfr_ci,
    eh_release_corretiva,
    calcular_cfr_releases,
    calcular_tempo_recuperacao,
    classificar_dora_metrica,
    classificar_dora_repositorio,
    calcular_rework_rate,
)


# ==============================================================================
# Fixtures com dados baseados nos exemplos numéricos da Seção 5
# ==============================================================================

@pytest.fixture
def exemplo_secao5_rq02():
    """Exemplo numérico da RQ02 no README: Release v1.1 em 15/03 com commits em 02/03, 10/03 e 14/03."""
    rel_date = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
    commits = [
        datetime(2024, 3, 2, 12, 0, tzinfo=timezone.utc),   # 13 dias
        datetime(2024, 3, 10, 12, 0, tzinfo=timezone.utc),  # 5 dias
        datetime(2024, 3, 14, 12, 0, tzinfo=timezone.utc),  # 1 dia
    ]
    return rel_date, commits


@pytest.fixture
def exemplo_secao5_rq04():
    """
    Exemplo numérico da RQ04 no README:
    09:00 - success
    10:00 - failure (início do episódio)
    10:30 - failure (mesmo episódio)
    11:15 - success (terminou às 11:20) -> Duração: 1h20 (1.333 horas)
    """
    runs = [
        {
            "workflow_id": "CI",
            "conclusion": "success",
            "run_started_at": "2024-05-10T09:00:00Z",
            "updated_at": "2024-05-10T09:10:00Z",
        },
        {
            "workflow_id": "CI",
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:00:00Z",
            "updated_at": "2024-05-10T10:10:00Z",
        },
        {
            "workflow_id": "CI",
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:30:00Z",
            "updated_at": "2024-05-10T10:40:00Z",
        },
        {
            "workflow_id": "CI",
            "conclusion": "success",
            "run_started_at": "2024-05-10T11:15:00Z",
            "updated_at": "2024-05-10T11:20:00Z",
        },
    ]
    return runs


# ==============================================================================
# Testes RQ01: Deployment Frequency
# ==============================================================================

def test_deployment_frequency_basico():
    freq = calcular_deployment_frequency(num_releases=52, weeks=52.0)
    assert freq == 1.0


def test_deployment_frequency_divisao_zero():
    with pytest.raises(ValueError):
        calcular_deployment_frequency(num_releases=10, weeks=0)


# ==============================================================================
# Testes RQ02: Lead Time for Changes
# ==============================================================================

def test_lead_time_exemplo_secao5(exemplo_secao5_rq02):
    rel_date, commits = exemplo_secao5_rq02

    # Variante (a): 15/03 - 02/03 = 13 dias
    lt_a = calcular_lead_time_release(rel_date, commits)
    assert pytest.approx(lt_a, 0.01) == 13.0

    # Variante (b): commits com 13, 5 e 1 dias
    lt_b = calcular_lead_time_commits(rel_date, commits)
    assert [round(x, 1) for x in lt_b] == [13.0, 5.0, 1.0]


def test_lead_time_repositorio():
    releases_data = [
        {
            "release_date": datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc),
            "commit_dates": [
                datetime(2024, 3, 2, 12, 0, tzinfo=timezone.utc),
                datetime(2024, 3, 10, 12, 0, tzinfo=timezone.utc),
                datetime(2024, 3, 14, 12, 0, tzinfo=timezone.utc),
            ],
        },
        {
            "release_date": datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc),
            "commit_dates": [
                datetime(2024, 4, 10, 12, 0, tzinfo=timezone.utc), # 5 dias
            ],
        },
    ]
    med_a, med_b, total_c = calcular_lead_time_repositorio(releases_data)
    assert med_a is not None and med_b is not None
    assert total_c == 4


def test_lead_time_caso_borda_sem_commits():
    rel_date = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
    assert calcular_lead_time_release(rel_date, []) is None
    assert calcular_lead_time_commits(rel_date, []) == []


# ==============================================================================
# Testes RQ03: Change Failure Rate (CFR)
# ==============================================================================

def test_cfr_ci_com_conclusoes_e_ignorados():
    runs = [
        {"conclusion": "success"},
        {"conclusion": "success"},
        {"conclusion": "failure"},
        {"conclusion": "timed_out"},
        {"conclusion": "startup_failure"},
        # Devem ser estritamente ignorados:
        {"conclusion": "cancelled"},
        {"conclusion": "skipped"},
        {"conclusion": "neutral"},
        {"conclusion": "action_required"},
        {"conclusion": None},
        {"conclusion": ""},
    ]
    # Total validos: 2 sucessos + 3 falhas = 5. CFR = 3 / 5 = 0.60
    cfr, falhas, sucessos = calcular_cfr_ci(runs)
    assert cfr == 0.60
    assert falhas == 3
    assert sucessos == 2


def test_cfr_ci_vazio():
    cfr, f, s = calcular_cfr_ci([])
    assert cfr is None
    assert f == 0
    assert s == 0


def test_heuristica_release_corretiva():
    # Caso 1 do README: v2.3.0 -> v2.3.1 com fix no commit
    assert eh_release_corretiva("v2.3.1", "v2.3.0", ["fix: crash ao abrir arquivo"]) is True

    # Caso 2 do README: v2.4.0 -> v2.5.0 (mudança de minor) sem commits de fix
    assert eh_release_corretiva("v2.5.0", "v2.4.0", ["feat: nova funcionalidade"]) is False

    # Detecção por palavra-chave hotfix/revert
    assert eh_release_corretiva("v1.0.0", "v1.0.0", ["Revert PR #12"]) is True
    assert eh_release_corretiva("v1.0.0", "v1.0.0", ["Hotfix de seguranca"]) is True


def test_cfr_releases_com_censura():
    janela_fim = datetime(2024, 9, 30, 23, 59, tzinfo=timezone.utc)
    releases = [
        # Release 1: seguida de release corretiva em 2 dias -> falha!
        {
            "published_at": datetime(2024, 5, 10, 12, 0, tzinfo=timezone.utc),
            "tag_name": "v2.3.0",
        },
        # Release 2: release corretiva
        {
            "published_at": datetime(2024, 5, 12, 12, 0, tzinfo=timezone.utc),
            "tag_name": "v2.3.1",
            "commit_messages": ["fix: crash"],
        },
        # Release 3: publicada dentro dos últimos 7 dias da janela -> censurada!
        {
            "published_at": datetime(2024, 9, 28, 12, 0, tzinfo=timezone.utc),
            "tag_name": "v3.0.0",
        },
    ]
    cfr, falhas, avaliadas, censuradas = calcular_cfr_releases(releases, janela_fim)
    assert censuradas == 1
    assert avaliadas == 2
    assert falhas == 1
    assert cfr == 0.5


# ==============================================================================
# Testes RQ04: Tempo de Recuperação e Censura
# ==============================================================================

def test_tempo_recuperacao_exemplo_secao5(exemplo_secao5_rq04):
    mediana, tempos, comp, cens = calcular_tempo_recuperacao(exemplo_secao5_rq04)
    assert comp == 1
    assert cens == 0
    # 10:00 até 11:20 = 80 minutos = 1.333 horas
    assert pytest.approx(mediana, 0.01) == 1.333


def test_tempo_recuperacao_caso_borda_censurado():
    runs = [
        {
            "workflow_id": "build",
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:00:00Z",
            "updated_at": "2024-05-10T10:05:00Z",
        },
        {
            "workflow_id": "build",
            "conclusion": "failure",
            "run_started_at": "2024-05-10T11:00:00Z",
            "updated_at": "2024-05-10T11:05:00Z",
        },
        # Nunca recuperou até o fim da janela
    ]
    mediana, tempos, comp, cens = calcular_tempo_recuperacao(runs)
    assert comp == 0
    assert cens == 1
    assert mediana is None


# ==============================================================================
# Testes Classificação DORA (Seção 5 / RQ07)
# ==============================================================================

def test_classificar_dora_metrica_individuais():
    assert classificar_dora_metrica("deployment_frequency", 8.0) == "Elite"
    assert classificar_dora_metrica("deployment_frequency", 2.5) == "High"
    assert classificar_dora_metrica("deployment_frequency", 0.5) == "Medium"
    assert classificar_dora_metrica("deployment_frequency", 0.1) == "Low"

    assert classificar_dora_metrica("lead_time", 0.5) == "Elite"
    assert classificar_dora_metrica("lead_time", 4.0) == "High"
    assert classificar_dora_metrica("lead_time", 15.0) == "Medium"
    assert classificar_dora_metrica("lead_time", 45.0) == "Low"

    assert classificar_dora_metrica("cfr", 0.10) == "Elite"
    assert classificar_dora_metrica("cfr", 0.25) == "High"
    assert classificar_dora_metrica("cfr", 0.40) == "Medium"
    assert classificar_dora_metrica("cfr", 0.55) == "Low"

    assert classificar_dora_metrica("recovery_time", 0.5) == "Elite"
    assert classificar_dora_metrica("recovery_time", 5.0) == "High"
    assert classificar_dora_metrica("recovery_time", 40.0) == "Medium"
    assert classificar_dora_metrica("recovery_time", 200.0) == "Low"


def test_classificacao_dora_exemplo_secao5():
    """Exemplo do README: notas (4, 3, 3, 1) -> mediana é 3, logo High."""
    tier_geral, tiers = classificar_dora_repositorio(
        dep_freq=10.0,         # Elite (4)
        lead_time_days=3.0,    # High (3)
        cfr=0.20,              # High (3)
        recovery_hours=200.0,  # Low (1)
    )
    assert tier_geral == "High"
    assert tiers["deployment_frequency"] == "Elite"
    assert tiers["lead_time"] == "High"
    assert tiers["change_failure_rate"] == "High"
    assert tiers["recovery_time"] == "Low"
    

# ==============================================================================
# Testes Rework Rate (RQ08)
# ==============================================================================
 
    
def test_rework_rate():
    releases = [
        {"published_at": datetime(2024, 1, 1, tzinfo=timezone.utc), "tag_name": "v1.0.0"},
        {"published_at": datetime(2024, 1, 10, tzinfo=timezone.utc), "tag_name": "v1.0.1", "commit_messages": ["fix: bug corrompido"]},
        {"published_at": datetime(2024, 2, 1, tzinfo=timezone.utc), "tag_name": "v1.1.0", "commit_messages": ["feat: nova tela"]},
    ]
    # 3 releases no total, 1 corretiva (v1.0.1) -> 1/3 = 0.3333...
    taxa = calcular_rework_rate(releases)
    assert pytest.approx(taxa, 0.01) == 0.333
