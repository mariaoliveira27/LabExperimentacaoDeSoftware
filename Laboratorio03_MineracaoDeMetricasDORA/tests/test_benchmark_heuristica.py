"""
Testes unitários para o script de benchmarking da heurística (benchmark_heuristica.py).
Garante que as métricas, o carregamento de dados e a execução do benchmark funcionem
conforme o esperado e com cobertura automatizada.
"""

import os
import pytest
from benchmark_heuristica import (
    calcular_metricas_manuais,
    carregar_dados_rotulados,
    executar_benchmark,
)


def test_calcular_metricas_manuais_perfeito():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 1, 0, 0]
    m = calcular_metricas_manuais(y_true, y_pred)
    assert m["tp"] == 2
    assert m["tn"] == 2
    assert m["fp"] == 0
    assert m["fn"] == 0
    assert m["acuracia"] == 1.0
    assert m["precisao"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0


def test_calcular_metricas_manuais_com_erros():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 1, 0]
    m = calcular_metricas_manuais(y_true, y_pred)
    assert m["tp"] == 1
    assert m["fn"] == 1
    assert m["fp"] == 1
    assert m["tn"] == 1
    assert m["acuracia"] == 0.5
    assert m["precisao"] == 0.5
    assert m["recall"] == 0.5
    assert m["f1"] == 0.5


def test_calcular_metricas_manuais_vazio():
    m = calcular_metricas_manuais([], [])
    assert m["f1"] == 0.0
    assert m["acuracia"] == 0.0


def test_carregar_dados_rotulados_arquivo_inexistente():
    with pytest.raises(FileNotFoundError):
        carregar_dados_rotulados("caminho_inexistente_12345.csv")


def test_executar_benchmark_com_amostra():
    registros_teste = [
        {
            "release_tag": "v1.0.1",
            "tag_anterior": "v1.0.0",
            "commits_resumo": "fix: resolve memory leak",
            "corretiva": "sim",
        },
        {
            "release_tag": "v1.1.0",
            "tag_anterior": "v1.0.1",
            "commits_resumo": "feat: new dashboard view",
            "corretiva": "não",
        },
        {
            "release_tag": "v1.1.1",
            "tag_anterior": "v1.1.0",
            "commits_resumo": "hotfix: critical security patch",
            "corretiva": "sim",
        },
    ]

    res = executar_benchmark(registros_teste)
    assert "v1" in res
    assert "v2" in res
    assert "v3" in res
    assert res["v3"]["metricas"]["f1"] >= 0.70
