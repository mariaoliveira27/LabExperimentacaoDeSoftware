"""
Módulo de cálculo das Métricas DORA para o Lab03.
Implementa as definições operacionais e regras de negócio:
- RQ01: Deployment frequency (releases por semana)
- RQ02: Lead time for changes (variante a e b)
- RQ03: Change failure rate (variante a CI e b releases)
- RQ04: Tempo de recuperação (em horas, com censura)
- Classificação DORA (tabela de referência e mediana arredondada para baixo)
"""

import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Converte string ISO 8601 em objeto datetime UTC ciente de fuso horário."""
    if not dt_str:
        return None
    # Trata formato ISO padrão do GitHub (terminado em Z ou com offset)
    clean_str = dt_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


# ==============================================================================
# RQ 01: Deployment Frequency
# ==============================================================================

def calcular_deployment_frequency(num_releases: int, weeks: float = 52.14) -> float:
    """
    Calcula a Deployment Frequency em releases por semana.
    Fórmula: número de releases publicadas válidas / semanas na janela.
    """
    if weeks <= 0:
        raise ValueError("O número de semanas na janela deve ser maior que zero.")
    return max(0.0, float(num_releases) / float(weeks))


# ==============================================================================
# RQ 02: Lead Time for Changes
# ==============================================================================

def calcular_lead_time_release(release_date: datetime, commit_dates: List[datetime]) -> Optional[float]:
    """
    Variante (a): Lead time de uma release R.
    Fórmula: (data de R - data do commit mais antigo incluído em R) em dias.
    Se não houver commits associados, retorna None.
    """
    if not commit_dates:
        return None
    oldest_commit = min(commit_dates)
    diff_seconds = (release_date - oldest_commit).total_seconds()
    return max(0.0, diff_seconds / 86400.0)


def calcular_lead_time_commits(release_date: datetime, commit_dates: List[datetime]) -> List[float]:
    """
    Variante (b): Lead time para cada commit individual incluído em R.
    Fórmula: (data de R - data do commit) em dias para cada commit.
    """
    lead_times = []
    for c_date in commit_dates:
        diff_seconds = (release_date - c_date).total_seconds()
        lead_times.append(max(0.0, diff_seconds / 86400.0))
    return lead_times


def calcular_lead_time_repositorio(
    releases_data: List[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float], int]:
    """
    Calcula o lead time for changes para o repositório em ambas as variantes:
    - Variante (a): Mediana do lead time entre as releases.
    - Variante (b): Mediana do lead time entre todos os commits de todas as releases.
    Retorna (mediana_a_dias, mediana_b_dias, total_commits_avaliados).
    """
    lead_times_por_release = []
    todos_lead_times_commits = []

    for item in releases_data:
        # releases_data contêm: {'release_date': datetime, 'commit_dates': [datetime, ...]}
        r_date = item.get("release_date")
        c_dates = item.get("commit_dates", [])
        if not r_date or not c_dates:
            continue

        lt_rel = calcular_lead_time_release(r_date, c_dates)
        if lt_rel is not None:
            lead_times_por_release.append(lt_rel)

        lt_comms = calcular_lead_time_commits(r_date, c_dates)
        todos_lead_times_commits.extend(lt_comms)

    mediana_a = statistics.median(lead_times_por_release) if lead_times_por_release else None
    mediana_b = statistics.median(todos_lead_times_commits) if todos_lead_times_commits else None

    return mediana_a, mediana_b, len(todos_lead_times_commits)


# ==============================================================================
# RQ 03: Change Failure Rate (CFR)
# ==============================================================================

@dataclass(frozen=True)
class ResultadoCFR:
    """CFR(a) e as contagens que explicam seu denominador."""

    cfr: Optional[float]
    falhas: int
    sucessos: int
    ignorados: int


def calcular_cfr_ci(workflow_runs: List[Dict[str, Any]]) -> ResultadoCFR:
    """
    Variante (a): Proxy de CI.
    Fórmula: nº de runs com falha / (nº de falhas + nº de sucessos).
    Conclusions consideradas:
      - Sucesso: 'success'
      - Falha: 'failure', 'timed_out', 'startup_failure'
      - Ignorar: 'cancelled', 'skipped', 'neutral', 'action_required', 'stale', vazio/None.
    Retorna ResultadoCFR com cfr, falhas, sucessos e ignorados.
    Sem sucessos ou falhas, cfr é None (indisponível), e não zero.
    """
    falhas = 0
    sucessos = 0
    ignorados = 0

    conclusoes_falha = {"failure", "timed_out", "startup_failure"}
    conclusoes_sucesso = {"success"}

    for run in workflow_runs:
        conclusion = run.get("conclusion")
        conclusion = conclusion.strip().lower() if isinstance(conclusion, str) else ""
        if conclusion in conclusoes_sucesso:
            sucessos += 1
        elif conclusion in conclusoes_falha:
            falhas += 1
        else:
            ignorados += 1

    total_validos = falhas + sucessos
    if total_validos == 0:
        return ResultadoCFR(None, 0, 0, ignorados)

    cfr = float(falhas) / float(total_validos)
    return ResultadoCFR(cfr, falhas, sucessos, ignorados)


def eh_release_corretiva(
    tag_atual: str,
    tag_anterior: str,
    commit_messages: Optional[List[str]] = None,
) -> bool:
    """
    Heurística automática para identificar se uma release é corretiva (patch/hotfix):
    1. SemVer: apenas o dígito de patch é incrementado (ex.: v2.3.0 -> v2.3.1).
    2. Mensagens de commit contendo termos como 'fix', 'hotfix', 'revert'.
    """
    # 1. Verificação de palavras-chave nas mensagens dos commits
    if commit_messages:
        palavras_chave = [r"\bfix\b", r"\bhotfix\b", r"\brevert\b", r"\bbugfix\b", r"\bpatch\b"]
        for msg in commit_messages:
            msg_lower = msg.lower()
            if any(re.search(padrao, msg_lower) for padrao in palavras_chave):
                return True

    # 2. Verificação de versão SemVer
    semver_pattern = r"v?(\d+)\.(\d+)\.(\d+)"
    m_atual = re.search(semver_pattern, tag_atual)
    m_ant = re.search(semver_pattern, tag_anterior)

    if m_atual and m_ant:
        major_curr, minor_curr, patch_curr = map(int, m_atual.groups())
        major_prev, minor_prev, patch_prev = map(int, m_ant.groups())

        # Se Major e Minor são idênticos e o Patch aumentou
        if major_curr == major_prev and minor_curr == minor_prev and patch_curr > patch_prev:
            return True

    return False


def calcular_cfr_releases(
    releases: List[Dict[str, Any]],
    window_end: datetime,
) -> Tuple[Optional[float], int, int, int]:
    """
    Variante (b): Proxy de entrega.
    Uma release R é considerada FALHA se for seguida, em até 7 dias, por uma release corretiva.
    Releases publicadas nos últimos 7 dias da janela são censuradas (excluídas do denominador).
    Releases devem estar ordenadas por data de publicação crescente.
    Retorna (cfr, releases_com_falha, releases_avaliadas, releases_censuradas).
    """
    if not releases:
        return None, 0, 0, 0

    # Ordena cronologicamente por published_at
    ordenadas = sorted(releases, key=lambda r: r["published_at"])

    releases_avaliadas = 0
    releases_com_falha = 0
    releases_censuradas = 0

    limite_censura_segundos = 7 * 86400.0

    for i, rel in enumerate(ordenadas):
        rel_date = rel["published_at"]
        tempo_ate_fim_janela = (window_end - rel_date).total_seconds()

        # Censura: publicadas nos últimos 7 dias da janela
        if tempo_ate_fim_janela < limite_censura_segundos:
            releases_censuradas += 1
            continue

        releases_avaliadas += 1
        falhou = False

        # Verifica se alguma release subsequente em até 7 dias é corretiva
        for j in range(i + 1, len(ordenadas)):
            prox_rel = ordenadas[j]
            prox_date = prox_rel["published_at"]
            delta_dias = (prox_date - rel_date).total_seconds() / 86400.0

            if delta_dias > 7.0:
                break

            # Avalia se a próxima release é corretiva
            tag_atual = prox_rel.get("tag_name", "")
            tag_anterior = rel.get("tag_name", "")
            commit_msgs = prox_rel.get("commit_messages", [])

            if eh_release_corretiva(tag_atual, tag_anterior, commit_msgs):
                falhou = True
                break

        if falhou:
            releases_com_falha += 1

    if releases_avaliadas == 0:
        return None, 0, 0, releases_censuradas

    cfr = float(releases_com_falha) / float(releases_avaliadas)
    return cfr, releases_com_falha, releases_avaliadas, releases_censuradas


# ==============================================================================
# RQ 04: Tempo de Recuperação (Failed Deployment Recovery Time)
# ==============================================================================

@dataclass(frozen=True)
class ResultadoRecuperacao:
    """Episódios observados e censurados de falha por workflow."""

    mediana_horas: Optional[float]
    tempos_horas: List[float]
    recuperados: int
    censurados: int
    proporcao_censurada: Optional[float]


def _data_run(run: Dict[str, Any], campo: str) -> datetime:
    """Exige a data usada pela definição operacional, sem fabricar substitutos."""
    valor = run.get(campo)
    data = parse_datetime(valor) if isinstance(valor, str) else None
    if data is None or data.tzinfo is None or data.utcoffset() is None:
        raise ValueError(f"Run {run.get('id')}: {campo} deve ser uma data ISO 8601 com fuso.")
    return data.astimezone(timezone.utc)


def _id_run(run: Dict[str, Any]) -> int:
    valor = run.get("id")
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        raise ValueError("Run válido sem ID inteiro para desempate cronológico.")
    try:
        return int(valor)
    except ValueError as exc:
        raise ValueError("Run válido sem ID inteiro para desempate cronológico.") from exc


def calcular_tempo_recuperacao(
    workflow_runs: List[Dict[str, Any]],
    window_end: Optional[datetime] = None,
) -> ResultadoRecuperacao:
    """
    Calcula o tempo de recuperação (em horas) após uma execução de CI/CD com falha.
    Para cada workflow individual:
      - Ordena cronologicamente por run_started_at e ID numérico como desempate.
      - Um episódio de falha começa na primeira falha após um sucesso e termina
        na próxima execução bem-sucedida desse mesmo workflow.
      - Tempo do episódio: fim da execução bem-sucedida (updated_at) - início da primeira falha (run_started_at).
      - Episódio que nunca termina com sucesso até o fim da janela é censurado.
    Falhas anteriores ao primeiro sucesso observado não abrem episódios.
    Conclusões ignoradas não abrem nem encerram episódios.
    Retorna ResultadoRecuperacao. Sem recuperados, mediana_horas é None;
    sem episódios, proporcao_censurada é None. Dados válidos sem os campos
    necessários ou com datas impossíveis geram ValueError.
    Se window_end for informado, sucessos concluídos depois do corte não
    encerram episódios nem estabelecem um sucesso observado dentro da janela.
    """
    if window_end is not None:
        if window_end.tzinfo is None or window_end.utcoffset() is None:
            raise ValueError("window_end deve conter fuso horário.")
        window_end = window_end.astimezone(timezone.utc)
    conclusoes_falha = {"failure", "timed_out", "startup_failure"}
    conclusoes_sucesso = {"success"}

    # Agrupa por workflow_id
    runs_por_workflow: Dict[str, List[Tuple[datetime, int, str, Optional[datetime]]]] = {}
    for run in workflow_runs:
        conclusion = run.get("conclusion")
        conclusion = conclusion.strip().lower() if isinstance(conclusion, str) else ""
        if conclusion not in conclusoes_falha and conclusion not in conclusoes_sucesso:
            continue
        if run.get("workflow_id") is None:
            raise ValueError(f"Run {run.get('id')}: workflow_id ausente.")
        wf_id = str(run["workflow_id"])
        run_id = _id_run(run)
        inicio = _data_run(run, "run_started_at")
        fim = _data_run(run, "updated_at") if conclusion in conclusoes_sucesso else None
        if fim is not None and fim < inicio:
            raise ValueError(f"Run {run_id}: updated_at anterior a run_started_at.")
        if window_end is not None and (inicio > window_end or (fim is not None and fim > window_end)):
            continue
        runs_por_workflow.setdefault(wf_id, []).append((inicio, run_id, conclusion, fim))

    todos_tempos_recuperacao_horas: List[float] = []
    total_episodios_completados = 0
    total_episodios_censurados = 0

    for wf_id in sorted(runs_por_workflow):
        # A lista de tempos também é determinística entre workflows.
        runs_ordenados = sorted(runs_por_workflow[wf_id], key=lambda run: (run[0], run[1]))

        sucesso_observado = False
        inicio_episodio_falha: Optional[datetime] = None

        for t_inicio, _, conc, t_fim in runs_ordenados:
            if conc in conclusoes_falha:
                if sucesso_observado and inicio_episodio_falha is None:
                    inicio_episodio_falha = t_inicio
                # Falhas consecutivas pertencem ao episódio já aberto.
            elif conc in conclusoes_sucesso:
                if inicio_episodio_falha is not None:
                    duracao_segundos = (t_fim - inicio_episodio_falha).total_seconds()
                    duracao_horas = duracao_segundos / 3600.0
                    todos_tempos_recuperacao_horas.append(duracao_horas)
                    total_episodios_completados += 1
                    inicio_episodio_falha = None
                sucesso_observado = True

        if inicio_episodio_falha is not None:
            # Terminou a janela sem sucesso -> Censurado
            total_episodios_censurados += 1

    mediana_horas = (
        statistics.median(todos_tempos_recuperacao_horas)
        if todos_tempos_recuperacao_horas
        else None
    )

    total_episodios = total_episodios_completados + total_episodios_censurados
    proporcao_censurada = total_episodios_censurados / total_episodios if total_episodios else None
    return ResultadoRecuperacao(
        mediana_horas,
        todos_tempos_recuperacao_horas,
        total_episodios_completados,
        total_episodios_censurados,
        proporcao_censurada,
    )


# ==============================================================================
# Classificação DORA (Seção 5 / RQ 07)
# ==============================================================================

TIER_SCORES = {
    "Elite": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

SCORE_TO_TIER = {
    4: "Elite",
    3: "High",
    2: "Medium",
    1: "Low",
}


def classificar_dora_metrica(metrica: str, valor: Optional[float]) -> str:
    """
    Classifica um valor de métrica individual segundo os cortes da tabela DORA (Seção 5):
    - Deployment frequency (por semana):
        Elite: >= 7 (diária ou mais)
        High: >= 1 e < 7
        Medium: >= 0.23 (aprox 1 por mês) e < 1
        Low: < 0.23
    - Lead time (mediana em dias):
        Elite: < 1 dia
        High: 1 a < 7 dias
        Medium: 7 a < 30 dias
        Low: >= 30 dias
    - Change failure rate (percentual/fração 0..1):
        Elite: <= 0.15 (15%)
        High: > 0.15 e <= 0.30 (30%)
        Medium: > 0.30 e <= 0.45 (45%)
        Low: > 0.45
    - Tempo de recuperação (mediana em horas):
        Elite: < 1 hora
        High: 1 hora a < 24 horas (1 dia)
        Medium: 24 horas a < 168 horas (1 semana)
        Low: >= 168 horas
    """
    if valor is None:
        return "Low"

    metrica_clean = metrica.lower()

    if "deployment_frequency" in metrica_clean:
        if valor >= 7.0:
            return "Elite"
        elif valor >= 1.0:
            return "High"
        elif valor >= (1.0 / 4.345):  # aprox 1 por mês = 0.2301
            return "Medium"
        else:
            return "Low"

    elif "lead_time" in metrica_clean:
        if valor < 1.0:
            return "Elite"
        elif valor < 7.0:
            return "High"
        elif valor < 30.0:
            return "Medium"
        else:
            return "Low"

    elif "change_failure_rate" in metrica_clean or "cfr" in metrica_clean:
        if valor <= 0.15:
            return "Elite"
        elif valor <= 0.30:
            return "High"
        elif valor <= 0.45:
            return "Medium"
        else:
            return "Low"

    elif "tempo_recuperacao" in metrica_clean or "recovery_time" in metrica_clean:
        if valor < 1.0:
            return "Elite"
        elif valor < 24.0:
            return "High"
        elif valor < 168.0:
            return "Medium"
        else:
            return "Low"

    return "Low"


def classificar_dora_repositorio(
    dep_freq: Optional[float],
    lead_time_days: Optional[float],
    cfr: Optional[float],
    recovery_hours: Optional[float],
) -> Tuple[str, Dict[str, str]]:
    """
    Atribui 4 pontos a Elite, 3 a High, 2 a Medium e 1 a Low em cada métrica.
    A classificação geral é a mediana desses quatro valores arredondada para baixo (math.floor).
    """
    tiers_individuais = {
        "deployment_frequency": classificar_dora_metrica("deployment_frequency", dep_freq),
        "lead_time": classificar_dora_metrica("lead_time", lead_time_days),
        "change_failure_rate": classificar_dora_metrica("change_failure_rate", cfr),
        "recovery_time": classificar_dora_metrica("tempo_recuperacao", recovery_hours),
    }

    scores = [TIER_SCORES[tiers_individuais[m]] for m in tiers_individuais]
    mediana_score = statistics.median(scores)
    score_geral = int(math.floor(mediana_score))
    score_geral = max(1, min(4, score_geral))

    return SCORE_TO_TIER[score_geral], tiers_individuais



# ==============================================================================
# RQ 08 (Bônus): Rework Rate
# ==============================================================================

def calcular_rework_rate(releases: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calcula o Rework Rate (RQ 08 bônus): proporção de releases corretivas sobre o total de releases.
    """
    if not releases or len(releases) <= 1:
        return 0.0
    
    total_releases = len(releases)
    releases_corretivas = 0
    
    # Ordena cronologicamente por data de publicação
    ordenadas = sorted(releases, key=lambda r: r["published_at"])
    
    for i in range(1, len(ordenadas)):
        tag_atual = ordenadas[i].get("tag_name", "")
        tag_anterior = ordenadas[i-1].get("tag_name", "")
        commit_msgs = ordenadas[i].get("commit_messages", [])
        
        if eh_release_corretiva(tag_atual, tag_anterior, commit_msgs):
            releases_corretivas += 1
            
    return float(releases_corretivas) / float(total_releases)
