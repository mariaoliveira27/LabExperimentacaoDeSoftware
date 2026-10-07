"""Regressões de CFR(a) e recuperação baseadas somente nos workflow runs."""

from itertools import permutations
from datetime import datetime, timezone

import pytest

from metricas.calculo_metricas import calcular_cfr_ci, calcular_tempo_recuperacao


@pytest.fixture
def criar_run():
    def criar(run_id, conclusion, inicio, fim=None, workflow_id=1):
        return {
            "id": run_id,
            "workflow_id": workflow_id,
            "conclusion": conclusion,
            "run_started_at": f"2024-05-10T{inicio}:00Z",
            "updated_at": f"2024-05-10T{fim or inicio}:00Z",
        }

    return criar


@pytest.fixture
def runs_diagnostico(criar_run):
    return [
        criar_run(1, "success", "09:00"),
        criar_run(2, "failure", "10:00"),
        criar_run(3, "success", "11:00", "11:12"),
    ]


def test_reproduz_diagnostico_sem_metadados(runs_diagnostico):
    cfr = calcular_cfr_ci(runs_diagnostico)
    recuperacao = calcular_tempo_recuperacao(runs_diagnostico)
    assert cfr.cfr == pytest.approx(1 / 3)
    assert (cfr.sucessos, cfr.falhas, cfr.ignorados) == (2, 1, 0)
    assert recuperacao.mediana_horas == pytest.approx(1.2)
    assert recuperacao.tempos_horas == pytest.approx([1.2])
    assert (recuperacao.recuperados, recuperacao.censurados) == (1, 0)
    assert recuperacao.proporcao_censurada == 0.0


@pytest.mark.parametrize("minute,recovered", [(11, 0), (12, 1)])
def test_corte_inclusivo_usa_fim_do_sucesso(runs_diagnostico, minute, recovered):
    cutoff = datetime(2024, 5, 10, 11, minute, tzinfo=timezone.utc)
    result = calcular_tempo_recuperacao(runs_diagnostico, window_end=cutoff)
    assert result.recuperados == recovered
    assert result.censurados == 1 - recovered
    assert result.proporcao_censurada == 1 - recovered


def test_sucesso_fora_corte_nao_estabelece_baseline(criar_run):
    runs = [criar_run(1, "success", "09:00", "12:00"), criar_run(2, "failure", "10:00")]
    cutoff = datetime(2024, 5, 10, 11, tzinfo=timezone.utc)
    result = calcular_tempo_recuperacao(runs, window_end=cutoff)
    assert result.recuperados == result.censurados == 0
    assert result.proporcao_censurada is None


def test_corte_exige_fuso(runs_diagnostico):
    with pytest.raises(ValueError, match="window_end"):
        calcular_tempo_recuperacao(runs_diagnostico, window_end=datetime(2024, 5, 10))


def test_falha_inicial_sem_sucesso_nao_abre_episodio(criar_run):
    runs = [
        criar_run(1, "failure", "08:00"),
        criar_run(2, "startup_failure", "09:00"),
        criar_run(3, "success", "10:00"),
    ]
    resultado = calcular_tempo_recuperacao(runs)
    assert resultado.mediana_horas is None
    assert resultado.tempos_horas == []
    assert resultado.recuperados == resultado.censurados == 0
    assert resultado.proporcao_censurada is None

    runs.extend([
        criar_run(4, "failure", "11:00"),
        criar_run(5, "success", "12:00", "12:12"),
    ])
    resultado = calcular_tempo_recuperacao(runs)
    assert resultado.tempos_horas == pytest.approx([1.2])
    assert resultado.recuperados == 1


def test_falhas_consecutivas_workflows_distintos_e_censura(criar_run):
    runs = [
        criar_run(1, "success", "09:00"),
        criar_run(2, "failure", "10:00"),
        criar_run(3, "timed_out", "10:30"),
        criar_run(4, "startup_failure", "11:00"),
        criar_run(5, "success", "12:00", "12:15"),
        criar_run(6, "success", "08:00", workflow_id=2),
        criar_run(7, "failure", "09:00", workflow_id=2),
        criar_run(8, "success", "13:00", workflow_id=3),
    ]
    resultado = calcular_tempo_recuperacao(list(reversed(runs)))
    assert resultado.tempos_horas == [2.25]
    assert resultado.mediana_horas == 2.25
    assert resultado.recuperados == 1
    assert resultado.censurados == 1
    assert resultado.proporcao_censurada == 0.5


@pytest.mark.parametrize("conclusion", [None, "", "cancelled", "skipped", "neutral", "stale", "action_required", "unknown"])
def test_ignorado_nao_abre_nem_encerra_episodio(criar_run, conclusion):
    runs = [
        {"conclusion": conclusion},  # Não exige datas/IDs de uma execução ignorada.
        criar_run(1, "failure", "08:00"),
        criar_run(2, "success", "09:00"),
        criar_run(3, "failure", "10:00"),
        criar_run(4, conclusion, "11:00"),
        criar_run(5, "success", "12:00"),
        criar_run(6, conclusion, "13:00"),
    ]
    resultado = calcular_tempo_recuperacao(runs)
    assert resultado.tempos_horas == [2.0]
    assert resultado.recuperados == 1
    assert resultado.censurados == 0


def test_horarios_iguais_desempate_id_numerico_e_entrada_embaralhada(criar_run):
    runs = [
        criar_run(2, "success", "10:00"),
        criar_run(10, "failure", "10:00"),
        criar_run(11, "success", "10:00", "11:12"),
    ]
    esperado = calcular_tempo_recuperacao(runs)
    assert esperado.tempos_horas == pytest.approx([1.2])
    for permutacao in permutations(runs):
        assert calcular_tempo_recuperacao(list(permutacao)) == esperado


def test_mediana_e_ordem_dos_tempos_estaveis_entre_workflows(criar_run):
    runs = [
        criar_run(1, "success", "08:00", workflow_id=2),
        criar_run(2, "failure", "09:00", workflow_id=2),
        criar_run(3, "success", "11:00", workflow_id=2),
        criar_run(4, "success", "08:00", workflow_id=1),
        criar_run(5, "failure", "09:00", workflow_id=1),
        criar_run(6, "success", "13:00", workflow_id=1),
    ]
    resultado = calcular_tempo_recuperacao(runs)
    assert resultado.tempos_horas == [4.0, 2.0]
    assert resultado.mediana_horas == 3.0
    assert calcular_tempo_recuperacao(list(reversed(runs))) == resultado


@pytest.mark.parametrize("runs", [[], [{"conclusion": "cancelled"}]])
def test_recuperacao_sem_episodios_indisponivel(runs):
    resultado = calcular_tempo_recuperacao(runs)
    assert resultado.mediana_horas is None
    assert resultado.tempos_horas == []
    assert resultado.recuperados == resultado.censurados == 0
    assert resultado.proporcao_censurada is None


@pytest.mark.parametrize("campo,valor", [
    ("id", None),
    ("id", "invalido"),
    ("workflow_id", None),
    ("run_started_at", None),
    ("run_started_at", "invalido"),
    ("run_started_at", "2024-05-10T09:00:00"),
    ("updated_at", None),
    ("updated_at", "2024-05-10T08:00:00Z"),
])
def test_recuperacao_rejeita_dados_impossiveis(criar_run, campo, valor):
    run = criar_run(1, "success", "09:00")
    run[campo] = valor
    with pytest.raises(ValueError):
        calcular_tempo_recuperacao([run])


def test_recuperacao_nao_substitui_inicio_por_created_at(criar_run):
    run = criar_run(1, "failure", "10:00")
    run["created_at"] = run.pop("run_started_at")
    with pytest.raises(ValueError, match="run_started_at"):
        calcular_tempo_recuperacao([run])


def test_recuperacao_normaliza_fusos(runs_diagnostico):
    runs_diagnostico[1]["run_started_at"] = "2024-05-10T07:00:00-03:00"
    resultado = calcular_tempo_recuperacao(runs_diagnostico)
    assert resultado.mediana_horas == pytest.approx(1.2)
