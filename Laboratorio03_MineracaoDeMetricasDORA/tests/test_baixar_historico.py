"""Fixtures de bytes, sem download real ou alegação de dados empíricos."""

import hashlib
import json

import pytest
import requests

import baixar_historico as download


BYTES = b"arquivo-publico-ficticio-exclusivo-deste-teste"
MD5 = hashlib.md5(BYTES).hexdigest()
URL = "https://fixture.invalid/archive.zip"


class Resposta:
    def __init__(self, inicio, fim, *, corpo=None, status=206, headers=None):
        self.status_code = status
        self.headers = {
            "Content-Range": f"bytes {inicio}-{fim}/{len(BYTES)}",
            "Content-Length": str(fim - inicio + 1),
        }
        if headers:
            self.headers.update(headers)
        self.corpo = BYTES[inicio:fim + 1] if corpo is None else corpo

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError(f"HTTP {self.status_code}")
    def iter_content(self, chunk_size):
        yield self.corpo


def baixar_fixture(path, **kwargs):
    return download._baixar(path, url=URL, tamanho=len(BYTES), md5_esperado=MD5, **kwargs)


def fake_get(chamadas, modificar=None):
    def get(url, *, headers, stream, timeout):
        assert url == URL and stream is True
        inicio, fim = map(int, headers["Range"].removeprefix("bytes=").split("-"))
        chamadas.append((inicio, fim))
        return modificar(inicio, fim) if modificar else Resposta(inicio, fim)
    return get


def test_baixa_blocos_e_verifica_md5(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    chamadas = []
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas))
    estado = baixar_fixture(path, bloco=10)
    assert path.read_bytes() == BYTES
    assert not path.with_name("fonte.zip.part").exists()
    assert chamadas[0] == (0, 9)
    assert chamadas[-1][1] == len(BYTES) - 1
    assert estado["md5_zip_verificado"] is True
    assert estado["source_doi"] is None  # Fixture nunca recebe DOI empírico.


def test_checkpoint_truncado_preservado_e_parcial_retomado(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    path.with_name("fonte.zip.part").write_bytes(BYTES[:10])
    registro = path.with_name("fonte.zip.download.json")
    corrompido = b'{"status": "interrompido",'
    registro.write_bytes(corrompido)
    chamadas = []
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas))
    estado = baixar_fixture(path, bloco=10)
    assert estado["md5_zip_verificado"] is True and path.read_bytes() == BYTES
    assert chamadas[0][0] == 10
    preservados = list(tmp_path.glob("fonte.zip.download.json.corrompido.*"))
    assert len(preservados) == 1 and preservados[0].read_bytes() == corrompido
    assert json.loads(registro.read_text(encoding="utf-8"))["status"] == "download_verificado"
    assert not registro.with_name(registro.name + ".tmp").exists()


def test_retoma_parcial_no_byte_correto(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    parcial = tmp_path / "fonte.zip.part"
    parcial.write_bytes(BYTES[:7])
    chamadas = []
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas))
    baixar_fixture(path, bloco=10)
    assert chamadas[0] == (7, 16)
    assert path.read_bytes() == BYTES


def test_retoma_destino_menor_como_parcial(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    path.write_bytes(BYTES[:5])
    chamadas = []
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas))
    baixar_fixture(path, bloco=20)
    assert chamadas[0][0] == 5
    assert path.read_bytes() == BYTES


@pytest.mark.parametrize("modificar", [
    lambda a, b: Resposta(a, b, status=200),
    lambda a, b: Resposta(a, b, headers={"Content-Range": "bytes 1-2/999"}),
    lambda a, b: Resposta(a, b, headers={"Content-Length": "999"}),
])
def test_resposta_inconsistente_nao_e_gravada(tmp_path, monkeypatch, modificar):
    path = tmp_path / "fonte.zip"
    parcial = tmp_path / "fonte.zip.part"
    parcial.write_bytes(BYTES[:4])
    chamadas = []
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas, modificar))
    with pytest.raises(RuntimeError, match="MD5 integral pendente"):
        baixar_fixture(path, bloco=10, tentativas=2)
    assert len(chamadas) == 2
    assert parcial.read_bytes() == BYTES[:4]
    assert not path.exists()
    estado = json.loads((tmp_path / "fonte.zip.download.json").read_text())
    assert estado["md5_zip_verificado"] is False
    assert estado["status"] == "download_interrompido"
    assert estado["sha256_parcial"] == hashlib.sha256(BYTES[:4]).hexdigest()


def test_resposta_curta_retoma_em_tentativa_seguinte(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    chamadas = []
    def resposta(a, b):
        return Resposta(a, b, corpo=BYTES[a:a + 3]) if len(chamadas) == 1 else Resposta(a, b)
    monkeypatch.setattr(download.requests, "get", fake_get(chamadas, resposta))
    baixar_fixture(path, bloco=10, tentativas=2)
    assert chamadas[:2] == [(0, 9), (3, 12)]
    assert path.read_bytes() == BYTES


def test_md5_errado_preserva_bytes_sem_promover_zip(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    def resposta(a, b): return Resposta(a, b, corpo=b"x" * (b - a + 1))
    monkeypatch.setattr(download.requests, "get", fake_get([], resposta))
    with pytest.raises(RuntimeError, match="MD5 integral pendente"):
        baixar_fixture(path, bloco=10, tentativas=1)
    assert not path.exists()
    assert (tmp_path / "fonte.zip.part").stat().st_size == len(BYTES)


def test_zip_existente_valido_nao_reconsulta_rede(tmp_path, monkeypatch):
    path = tmp_path / "fonte.zip"
    path.write_bytes(BYTES)
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: pytest.fail("Não deve consultar rede."))
    assert baixar_fixture(path)["md5_zip_verificado"] is True


def test_zip_existente_invalido_preservado(tmp_path):
    path = tmp_path / "fonte.zip"
    anterior = b"outro-arquivo-" * 5
    path.write_bytes(anterior)
    with pytest.raises(ValueError, match="MD5/tamanho"):
        baixar_fixture(path)
    assert path.read_bytes() == anterior


def test_nao_grava_em_csv_humano(tmp_path):
    path = tmp_path / "rotulos_vinicius.csv"
    path.write_text("julgamentos humanos", encoding="utf-8")
    with pytest.raises(ValueError, match="nunca um CSV humano"):
        baixar_fixture(path)
    assert path.read_text(encoding="utf-8") == "julgamentos humanos"


def test_cli_fonte_e_checksum_nao_podem_ser_substituidos(tmp_path):
    with pytest.raises(SystemExit) as exc:
        download.main(["--saida", str(tmp_path / "fonte.zip"), "--url", URL])
    assert exc.value.code == 2


def test_cli_timeout_retorna_erro_e_preserva_parcial(tmp_path, monkeypatch, capsys):
    path = tmp_path / "fonte.zip"
    def indisponivel(*args, **kwargs): raise requests.Timeout("Servidor indisponível.")
    monkeypatch.setattr(download.requests, "get", indisponivel)
    assert download.main(["--saida", str(path), "--tentativas", "1", "--timeout", "1"]) == 2
    assert "MD5 integral pendente" in capsys.readouterr().err
    assert not path.exists()
