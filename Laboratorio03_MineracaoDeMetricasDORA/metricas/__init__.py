"""
Pacote de cálculo das Métricas DORA (DevOps Research and Assessment)
Atende aos requisitos de cálculo e definições operacionais do Lab03:
- RQ 01: Deployment Frequency
- RQ 02: Lead Time for Changes (Variante a: por release; Variante b: por commit)
- RQ 03: Change Failure Rate (Variante a: proxy CI; Variante b: proxy releases corretivas)
- RQ 04: Tempo de Recuperação (Failed Deployment Recovery Time por workflow, com censura)
- Classificação DORA (Elite, High, Medium, Low)
"""

from .calculo_metricas import (
    ResultadoCFR,
    ResultadoRecuperacao,
    calcular_deployment_frequency,
    calcular_lead_time_release,
    calcular_lead_time_commits,
    calcular_lead_time_repositorio,
    calcular_cfr_ci,
    calcular_cfr_releases,
    eh_release_corretiva,
    calcular_tempo_recuperacao,
    classificar_dora_metrica,
    classificar_dora_repositorio,
    calcular_rework_rate,
)

__all__ = [
    "ResultadoCFR",
    "ResultadoRecuperacao",
    "calcular_deployment_frequency",
    "calcular_lead_time_release",
    "calcular_lead_time_commits",
    "calcular_lead_time_repositorio",
    "calcular_cfr_ci",
    "calcular_cfr_releases",
    "eh_release_corretiva",
    "calcular_tempo_recuperacao",
    "classificar_dora_metrica",
    "classificar_dora_repositorio",
    "calcular_rework_rate",
]
