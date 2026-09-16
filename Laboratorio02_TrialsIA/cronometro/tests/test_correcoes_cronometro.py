"""Testes automatizados das correções do cronômetro (Issue #30).

Cobre:
1. Encerramento automático quando timeout expira durante espera por entrada.
2. Trava de prazo: testes concluídos após o prazo NÃO podem ser marcados como SUCESSO.
3. Cópia atômica: testes e métricas rodam sobre o mesmo arquivo preservado e compartilham o SHA-256.
4. Regras de IA: bloqueio de consulta ao Gemini em rodadas manuais e bloqueio de aplicação após o prazo.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from Laboratorio02_TrialsIA.cronometro.src.cronometro import (
    congelar_copia_solucao,
    coordenar_rodada,
    finalizar_rodada,
    input_com_timeout,
)

FIXTURE_SUCESSO = Path(__file__).resolve().parents[1] / "exemplos" / "solucao_demo_kata01.py"
FIXTURE_INCOMPLETA = Path(__file__).resolve().parents[1] / "exemplos" / "solucao_demo_incompleta.py"


class TestCorrecoesCronometro(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.csv_path = self.temp_dir / "teste_registro.csv"
        self.resultados_dir = self.temp_dir / "resultados"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_timeout_no_input_encerra_automaticamente(self) -> None:
        """Verifica se o input com timeout expira e retorna estourou=True."""
        # Testa com timeout de 0.2 segundos sem digitar nada
        texto, estourou = input_com_timeout("Aguardando: ", timeout_segundos=0.2, valor_padrao="PADRAO")
        self.assertTrue(estourou)
        self.assertEqual(texto, "PADRAO")

    def test_sucesso_tardio_vira_limite_atingido(self) -> None:
        """Testes que passam mas concluem após 35 min não podem ser SUCESSO dentro do timebox."""
        trial_id = "teste_sucesso_tardio_01"
        res = coordenar_rodada(
            integrante="maria",
            kata="kata01",
            tratamento="ia",
            arquivo_solucao=FIXTURE_SUCESSO,
            trial_id=trial_id,
            timebox_minutos=35.0,
            diretorio_saida=self.resultados_dir,
            caminho_csv=self.csv_path,
            simulacao={
                "tipo": "sucesso_tardio",
                "duracao_minutos": 36.20,  # Concluiu aos 36.2 minutos (> 35)
            },
        )

        # Deve ser rebaixado para LIMITE_ATINGIDO
        self.assertEqual(res["status"], "LIMITE_ATINGIDO")
        self.assertEqual(res["tempo_final_considerado"], 35.0)
        self.assertTrue(res["dado_censurado"])
        self.assertIn("após o prazo", res["motivo_interrupcao"])

        # Confere gravação no CSV
        with open(self.csv_path, "r", encoding="utf-8") as f:
            linhas = list(csv.reader(f))
        self.assertEqual(len(linhas), 2)  # Cabeçalho + 1 linha
        linha_trial = linhas[1]
        self.assertEqual(linha_trial[8], "LIMITE_ATINGIDO")
        self.assertEqual(float(linha_trial[7]), 35.0)
        self.assertEqual(linha_trial[12], "True")

    def test_copia_atomica_compartilha_mesmo_sha256(self) -> None:
        """Testes e métricas devem avaliar o mesmo arquivo preservado com mesmo hash."""
        trial_id = "teste_snapshot_atomico_01"
        res = coordenar_rodada(
            integrante="maria",
            kata="kata01",
            tratamento="ia",
            arquivo_solucao=FIXTURE_SUCESSO,
            trial_id=trial_id,
            timebox_minutos=35.0,
            diretorio_saida=self.resultados_dir,
            caminho_csv=self.csv_path,
            simulacao={
                "tipo": "sucesso",
                "duracao_minutos": 8.0,
            },
        )

        pasta_trial = self.resultados_dir / trial_id
        copia_solucao = pasta_trial / f"{trial_id}_solucao_final.py"
        testes_json = pasta_trial / "testes.json"
        metricas_json = pasta_trial / "metricas.json"
        manifesto_json = pasta_trial / "manifesto_rodada.json"

        self.assertTrue(copia_solucao.is_file())
        self.assertTrue(testes_json.is_file())
        self.assertTrue(metricas_json.is_file())
        self.assertTrue(manifesto_json.is_file())

        hash_real = hashlib.sha256(copia_solucao.read_bytes()).hexdigest()

        # Lê os JSONs gerados
        dados_testes = json.loads(testes_json.read_text(encoding="utf-8"))
        dados_metricas = json.loads(metricas_json.read_text(encoding="utf-8"))
        dados_manifesto = json.loads(manifesto_json.read_text(encoding="utf-8"))

        # Ambos os relatórios apontam para a MESMA cópia congelada
        self.assertEqual(dados_testes["arquivo_solucao"], str(copia_solucao))
        self.assertEqual(dados_metricas["arquivo"], str(copia_solucao))
        self.assertEqual(dados_testes["sha256_solucao"], hash_real)
        self.assertEqual(dados_manifesto["artefatos"]["sha256_copia"], hash_real)

    def test_bloqueio_gemini_em_rodada_manual(self) -> None:
        """Garante que tentativa de consulta ao Gemini é bloqueada em tratamento manual."""
        trial_id = "teste_bloqueio_manual_01"
        with self.assertRaises(PermissionError):
            coordenar_rodada(
                integrante="maria",
                kata="kata01",
                tratamento="manual",
                arquivo_solucao=FIXTURE_SUCESSO,
                trial_id=trial_id,
                timebox_minutos=35.0,
                diretorio_saida=self.resultados_dir,
                caminho_csv=self.csv_path,
                simulacao={"tipo": "consulta_gemini_manual"},
            )

    def test_bloqueio_resposta_gemini_tardia(self) -> None:
        """Garante que respostas do Gemini que chegam após 35 min são bloqueadas/descartadas."""
        trial_id = "teste_gemini_tardio_01"
        with self.assertRaises(TimeoutError):
            coordenar_rodada(
                integrante="maria",
                kata="kata01",
                tratamento="ia",
                arquivo_solucao=FIXTURE_SUCESSO,
                trial_id=trial_id,
                timebox_minutos=35.0,
                diretorio_saida=self.resultados_dir,
                caminho_csv=self.csv_path,
                simulacao={
                    "tipo": "consulta_gemini_tardia",
                    "duracao_minutos": 36.0,  # Resposta chegou com 36 min
                },
            )


if __name__ == "__main__":
    unittest.main()
