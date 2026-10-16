"""A coleta deve parar cedo quando a fonte histórica não sustenta o trabalho."""

from datetime import datetime, timezone
import json

import pytest

import coleta_amostra_real as coleta
from test_coleta_amostra_real import APIPlanejada, preparar
from viabilidade_coleta import HistoricoIndisponivelError, verificar_viabilidade


@pytest.fixture
def relogio(monkeypatch):
    agora = datetime(2026, 10, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(coleta, "verificar_viabilidade", lambda *a, **kw: verificar_viabilidade(*a, **kw, agora=agora))


def test_bloqueia_ao_observar_cem_zeros_preservando_unidades_concluidas(preparar, relogio):
    config, destino, api = preparar(APIPlanejada(102, runs=0))
    with pytest.raises(HistoricoIndisponivelError):
        coleta.coletar(config, destino, client=api)
    estado = json.loads((destino / "estado.json").read_text(encoding="utf-8"))
    diagnostico = json.loads((destino / "diagnostico_viabilidade.json").read_text(encoding="utf-8"))
    assert estado["status"] == diagnostico["status"] == "historico_indisponivel"
    assert estado["n_processados"] == 100 and estado["n_aprovados"] == 0
    assert len(estado["snapshots"]) == 100
    assert not (destino / "qualificacoes/101.json").exists()
    assert not (destino / "repositorios_aprovados.csv").exists()
    assert not (destino / "releases.json").exists()
    assert not (destino / "proveniencia.json").exists()
    assert diagnostico["n_consultas_historicas_total_zero"] == 100
    assert diagnostico["n_fontes_potenciais"] == 0
    assert diagnostico["estado_apos_bloqueio_sha256"] == coleta.sha256(destino / "estado.json")
    assert not any("projeto-100" in endpoint for endpoint, _ in api.chamadas)


def test_retomada_bloqueia_antes_de_autenticar_ler_snapshots_ou_buscar(preparar, relogio, monkeypatch, capsys):
    config, destino, api = preparar(APIPlanejada(100, runs=0))
    with pytest.raises(HistoricoIndisponivelError):
        coleta.coletar(config, destino, client=api)
    protegidos = [destino / nome for nome in (
        "estado.json", "descartes.csv", "candidatos.json", "busca.json", "config_coleta.json",
    )] + list((destino / "qualificacoes").glob("*.json"))
    antes = {path: path.read_bytes() for path in protegidos}

    def nao_executar(*args, **kwargs):
        pytest.fail("A verificação de disponibilidade deve ocorrer antes deste trabalho")

    monkeypatch.setattr(coleta, "_criar_clientes", nao_executar)
    monkeypatch.setattr(coleta, "_ler_snapshot", nao_executar)
    monkeypatch.setattr(coleta, "buscar_candidatos", nao_executar)
    assert coleta.main([
        "--config", str(config), "--saida", str(destino), "--workers", "4", "--usar-gh-auth",
    ]) == 2
    mensagem = capsys.readouterr().err
    assert "bloqueada por indisponibilidade histórica" in mensagem
    assert "Não repita a coleta com as mesmas fontes" in mensagem
    assert all(path.read_bytes() == conteudo for path, conteudo in antes.items())
