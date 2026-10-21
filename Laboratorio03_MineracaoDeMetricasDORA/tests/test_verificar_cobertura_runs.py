"""Contrato do diagnóstico CLI; HTTP local simulado nunca é evidência empírica."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import verificar_cobertura_runs as diagnostico
from coleta_amostra_real import ClienteAuditavel
from coletor_runs import ColetaIncompletaError
from gerar_amostra_rotulagem import sha256


@pytest.fixture
def arquivos(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        'window:\n  start_date: "2024-01-01T00:00:00Z"\n'
        '  end_date: "2024-02-01T00:00:00Z"\n', encoding="utf-8",
    )
    return config, tmp_path / "saida/diagnostico.json"


def metadata(**alteracoes):
    return {"id": 1, "full_name": "owner/projeto", "default_branch": "main", "private": False, **alteracoes}


def vazio():
    return {"total_count": 0, "workflow_runs": []}


def client_com_respostas(*respostas):
    return SimpleNamespace(request=Mock(side_effect=respostas), invalidate_cache=Mock())


@pytest.mark.parametrize("repositorio", [None, "", "owner", "owner/repo/extra", "../repo", "owner/repo?token=x"])
def test_identificador_invalido_nao_consulta_api(arquivos, repositorio):
    config, saida = arquivos
    client = client_com_respostas()
    with pytest.raises(ValueError, match="owner/repo"):
        diagnostico.verificar(repositorio, saida, config, client=client)
    client.request.assert_not_called()
    assert not saida.exists()


def test_saida_existente_permanece_intacta_antes_de_ler_config(arquivos):
    _, saida = arquivos
    saida.parent.mkdir()
    saida.write_bytes(b"evidencia existente")
    client = client_com_respostas()
    with pytest.raises(FileExistsError, match="preservada"):
        diagnostico.verificar("owner/projeto", saida, "config-ausente.yaml", client=client)
    assert saida.read_bytes() == b"evidencia existente"
    client.request.assert_not_called()


@pytest.mark.parametrize("conteudo", ["", "[]", "window: []", "window: {}", (
    'window:\n  start_date: "2024-02-01T00:00:00Z"\n  end_date: "2024-01-01T00:00:00Z"\n'
)])
def test_config_invalida_falha_antes_de_criar_saida(arquivos, conteudo):
    config, saida = arquivos
    config.write_text(conteudo, encoding="utf-8")
    client = client_com_respostas()
    with pytest.raises(ValueError):
        diagnostico.verificar("owner/projeto", saida, config, client=client)
    client.request.assert_not_called()
    assert not saida.parent.exists()


@pytest.mark.parametrize("status,dados", [(404, {}), (200, metadata(id=True)), (200, metadata(private=True)),
                                        (200, metadata(default_branch="")), (200, metadata(full_name="incorreto"))])
def test_metadados_invalidos_nao_viram_diagnostico_completo(arquivos, status, dados):
    config, saida = arquivos
    client = client_com_respostas((status, dados, {}))
    with pytest.raises(ValueError, match="Metadados públicos incompletos"):
        diagnostico.verificar("owner/projeto", saida, config, client=client)
    assert client.request.call_count == 1
    assert not saida.exists()


def test_sucesso_persiste_janela_e_nunca_aprova_repositorio(arquivos):
    config, saida = arquivos
    client = client_com_respostas((200, metadata(full_name="owner/renomeado"), {}),
                                  (200, vazio(), {}), (200, vazio(), {}))
    resultado = diagnostico.verificar("owner/projeto", saida, config, client=client)
    assert json.loads(saida.read_text(encoding="utf-8")) == resultado
    assert resultado["config_sha256"] == sha256(config)
    assert resultado["aprovacao"] == "nao_avaliada"
    assert resultado["permite_metricas_dora_anuais"] is False
    cobertura = resultado["cobertura_runs"]
    assert cobertura["enumeration_complete"] is True
    assert cobertura["historical_coverage"] == "unknown"
    assert cobertura["historico_anual_completo"] is False
    assert len(cobertura["completed_intervals"]) == 2
    assert cobertura["repository"] == "owner/renomeado"
    assert client.request.call_args_list[0].kwargs == {"use_cache": False}
    assert client.request.call_args_list[1].args == ("/repos/owner/renomeado/actions/runs",)


def test_falhas_parciais_preservadas_e_retomada_reutiliza_cache(arquivos):
    config, saida = arquivos
    auditoria = saida.parent / "requisicoes.jsonl"
    cache = saida.parent / "cache/github_cache.db"

    def resposta(dados, status=200):
        return SimpleNamespace(status_code=status, headers={}, text="", json=lambda: dados)

    client = ClienteAuditavel(auditoria, token="fixture", cache_db_path=str(cache), max_retries=0)
    client.session.get = Mock(side_effect=[resposta(metadata()), resposta(vazio()), resposta({}, 503)])
    with pytest.raises(ColetaIncompletaError):
        diagnostico.verificar("owner/projeto", saida, config, client=client)
    parcial = saida.with_suffix(".incompleta.json")
    original = parcial.read_bytes()
    cobertura = json.loads(original)["cobertura_runs"]
    assert cobertura["enumeration_complete"] is False
    assert len(cobertura["completed_intervals"]) == 1
    assert not saida.exists()
    client.session.close()

    retomada = ClienteAuditavel(auditoria, token="fixture", cache_db_path=str(cache), max_retries=0)
    retomada.session.get = Mock(side_effect=[resposta(metadata()), resposta({}, 503),
                                            resposta(metadata()), resposta(vazio())])
    with pytest.raises(ColetaIncompletaError):
        diagnostico.verificar("owner/projeto", saida, config, client=retomada)
    assert parcial.read_bytes() == original
    assert saida.with_suffix(".incompleta.1.json").is_file()
    resultado = diagnostico.verificar("owner/projeto", saida, config, client=retomada)
    assert resultado["cobertura_runs"]["enumeration_complete"] is True
    assert retomada.session.get.call_count == 4  # Metadados frescos + fevereiro, janeiro vem do SQLite.
    assert parcial.read_bytes() == original
    registros = [json.loads(linha) for linha in auditoria.read_text(encoding="utf-8").splitlines()]
    assert sum(registro["origem"] == "cache" for registro in registros) == 2
    retomada.session.close()


def test_cli_apresenta_limite_historico_e_codigo_de_falha(arquivos, monkeypatch, capsys):
    config, saida = arquivos
    executar = Mock(return_value={"runs": [], "cobertura_runs": {
        "enumeration_complete": True, "completed_intervals": [{}, {}],
    }})
    monkeypatch.setattr(diagnostico, "verificar", executar)
    argumentos = ["--repositorio", "owner/projeto", "--saida", str(saida), "--config", str(config), "--usar-gh-auth"]
    assert diagnostico.main(argumentos) == 0
    executar.assert_called_once_with("owner/projeto", saida, str(config), True)
    assert "cobertura histórica anual: desconhecida" in capsys.readouterr().out
    executar.side_effect = ColetaIncompletaError("interrompida")
    assert diagnostico.main(argumentos) == 2
    assert "Reexecute para retomar pelo cache" in capsys.readouterr().err
