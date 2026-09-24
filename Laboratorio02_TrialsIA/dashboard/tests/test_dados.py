"""Acceptance checks for the archived experiment, without running kata code."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd


DASHBOARD_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = DASHBOARD_DIR.parent / "cronometro"
if not DATA_DIR.is_dir():
    DATA_DIR = DASHBOARD_DIR / "insumos" / "cronometro"
sys.path.insert(0, str(DASHBOARD_DIR))

from dados import build_view, load_trials  # noqa: E402


class ArchivedExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = load_trials(DATA_DIR, aplicar_ajustes=False)

    def test_registered_population_and_archived_coverage(self):
        self.assertEqual(len(self.frame), 18)
        self.assertTrue(self.frame["trial_id"].is_unique)
        self.assertEqual(self.frame["tratamento"].value_counts().to_dict(), {"ia": 9, "manual": 9})
        self.assertEqual(set(self.frame["integrante"]), {"aulus", "maria", "vinicius"})
        self.assertEqual(set(self.frame["kata"]), {f"K{i:02}" for i in range(1, 7)})
        self.assertEqual(int(self.frame["metricas_disponiveis"].sum()), 17)
        self.assertEqual(int((self.frame["fonte_testes"] == "relatorio").sum()), 17)

    def test_six_status_conflicts_are_retained_and_identified(self):
        conflicts = self.frame.loc[self.frame["status_divergente"]]
        self.assertEqual(set(conflicts["trial_id"]), {
            "aulus_K03_manual_01", "vinicius_K01_manual_01",
            "vinicius_K03_ia_01", "vinicius_K04_ia_01",
            "vinicius_K05_ia_01", "vinicius_K06_manual_01",
        })
        self.assertTrue((conflicts["status_registrado"] == "SUCESSO").all())
        self.assertTrue((conflicts["taxa_sucesso"] < 100).all())
        self.assertFalse(conflicts["passou_todos"].any())

    def test_missing_aulus_k04_artifacts_never_become_zero_measurements(self):
        row = self.frame.set_index("trial_id").loc["aulus_K04_ia_01"]
        self.assertEqual(row["fonte_testes"], "csv")
        self.assertEqual(row["taxa_sucesso"], 100)
        self.assertFalse(row["metricas_disponiveis"])
        for field in ("total_testes", "aprovados", "reprovados", "complexidade_media", "loc", "sloc"):
            with self.subTest(field=field):
                self.assertTrue(pd.isna(row[field]), f"{field} must remain unavailable")

    def test_initial_comparisons_match_verified_acceptance_values(self):
        view = build_view(self.frame)
        self.assertEqual(view["counts"], {
            "total": 18, "manual": 9, "ia": 9,
            "testes_arquivados": 17, "metricas_arquivadas": 17, "divergencias": 6,
        })
        for treatment, time, success, loc, structural_n in (
            ("manual", 18.2, 84.44444444444444, 44, 9),
            ("ia", 9.15, 76.66666666666667, 32.5, 8),
        ):
            with self.subTest(treatment=treatment):
                stats = view["stats"][treatment]
                self.assertEqual(stats["n"], 9)
                self.assertAlmostEqual(stats["tempo"]["median"], time)
                self.assertAlmostEqual(stats["sucesso"]["mean"], success)
                self.assertEqual(stats["loc"]["median"], loc)
                self.assertEqual(stats["complexidade"]["n"], structural_n)
                self.assertEqual(stats["loc"]["n"], structural_n)
                self.assertEqual(stats["sucesso"]["n"], 9)

    def test_all_28_filters_preserve_the_registered_rows(self):
        combinations = 0
        for participant in ("all", "aulus", "maria", "vinicius"):
            for kata in ("all", *(f"K{i:02}" for i in range(1, 7))):
                combinations += 1
                with self.subTest(participant=participant, kata=kata):
                    expected = self.frame
                    if participant != "all":
                        expected = expected.loc[expected["integrante"] == participant]
                    if kata != "all":
                        expected = expected.loc[expected["kata"] == kata]
                    view = build_view(self.frame, participant, kata)
                    self.assertEqual(set(view["row_ids"]), set(expected["trial_id"]))
                    self.assertEqual(view["counts"]["total"], len(expected))
                    self.assertEqual(view["counts"]["manual"] + view["counts"]["ia"], len(expected))
                    self.assertEqual(view["integrante"], participant)
                    self.assertEqual(view["kata"], kata)
        self.assertEqual(combinations, 28)

    def test_absent_treatment_has_null_statistics_and_zero_sample(self):
        view = build_view(self.frame, "aulus", "K04")
        absent = view["stats"]["manual"]
        self.assertEqual(absent["n"], 0)
        self.assertIsNone(absent["sucesso"]["mean"])
        for field in ("tempo", "complexidade", "loc"):
            self.assertEqual(absent[field]["n"], 0)
            for statistic in ("median", "q1", "q3"):
                self.assertIsNone(absent[field][statistic])
        self.assertEqual(view["stats"]["ia"]["sucesso"]["mean"], 100)
        self.assertEqual(view["stats"]["ia"]["loc"]["n"], 0)
        self.assertIsNone(view["stats"]["ia"]["loc"]["median"])


class TreatmentAdjustmentTests(unittest.TestCase):
    def test_requested_aulus_treatment_swap_preserves_values_and_other_participants(self):
        original = load_trials(DATA_DIR, aplicar_ajustes=False).set_index("trial_id")
        adjusted = load_trials(DATA_DIR).set_index("trial_id")
        aulus = adjusted["integrante"].eq("aulus")
        self.assertEqual(int(adjusted["tratamento_ajustado"].sum()), 6)
        self.assertTrue((adjusted.loc[aulus, "tratamento"] != original.loc[aulus, "tratamento"]).all())
        self.assertTrue((adjusted["tratamento_registrado"] == original["tratamento"]).all())
        pd.testing.assert_frame_equal(adjusted.loc[~aulus], original.loc[~aulus])
        preserved = [c for c in original.columns if c not in ("tratamento", "tratamento_ajustado")]
        pd.testing.assert_frame_equal(adjusted[preserved], original[preserved])
        view = build_view(adjusted.reset_index(), "aulus", "all")
        self.assertEqual(view["stats"]["ia"]["tempo"]["median"], 9.15)
        self.assertEqual(view["stats"]["manual"]["tempo"]["median"], 19.8)
        self.assertEqual(view["adjustment_count"], 6)
        self.assertEqual(view["stats"]["manual"]["n"], 3)
        self.assertEqual(view["stats"]["ia"]["n"], 3)


class IngestionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)
        with (DATA_DIR / "registro_experimento.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            self.fieldnames = reader.fieldnames
            self.row = next(reader)
        self.trial_id = self.row["Trial_ID"]

    def write_registry(self, rows):
        with (self.data_dir / "registro_experimento.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_reports(self, passed=1, total=4, trial_id=None):
        folder = self.data_dir / "resultados" / self.trial_id
        folder.mkdir(parents=True, exist_ok=True)
        report_id = trial_id or self.trial_id
        (folder / "testes.json").write_text(json.dumps({
            "trial_id": report_id,
            "resultado": {
                "total_casos": total, "aprovados": passed, "reprovados": total - passed,
                "taxa_sucesso": 100 * passed / total, "passou_todos": passed == total,
            },
        }), encoding="utf-8")
        (folder / "metricas.json").write_text(json.dumps({
            "schema_version": 1, "trial_id": report_id,
            "status_analise": "ok", "erro": None,
            "complexidade_media": 3.5, "loc": 42, "sloc": 30,
        }), encoding="utf-8")
        return folder

    def test_reports_override_csv_and_resolve_by_id_without_executing_code(self):
        self.row.update({"Taxa_Sucesso_Testes": "100", "Passou_Testes": "True", "Status": "SUCESSO"})
        self.write_registry([self.row])
        folder = self.write_reports()
        marker = self.data_dir / "solution_was_executed"
        (folder / f"{self.trial_id}_solucao_final.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('Never execute archived solutions')\n",
            encoding="utf-8",
        )
        row = load_trials(self.data_dir).iloc[0]
        self.assertEqual(row["trial_id"], self.trial_id)
        self.assertEqual(row["taxa_sucesso"], 25)
        self.assertEqual(row["total_testes"], 4)
        self.assertEqual(row["aprovados"], 1)
        self.assertEqual(row["reprovados"], 3)
        self.assertEqual(row["fonte_testes"], "relatorio")
        self.assertTrue(row["status_divergente"])
        self.assertEqual(row["complexidade_media"], 3.5)
        self.assertEqual(row["loc"], 42)
        self.assertFalse(marker.exists())

    def test_duplicate_trial_id_is_rejected_instead_of_double_counted(self):
        self.write_registry([self.row, self.row])
        with self.assertRaises(ValueError):
            load_trials(self.data_dir)

    def test_mismatched_report_cannot_be_associated_with_another_round(self):
        self.write_registry([self.row])
        self.write_reports(trial_id="a_different_trial")
        with self.assertRaises(ValueError):
            load_trials(self.data_dir)

    def test_success_average_weights_rounds_equally_instead_of_pooling_tests(self):
        # One round has 1/4 passing, another 100/100: round average = 62.5%.
        self.write_registry([self.row])
        self.write_reports()
        first = load_trials(self.data_dir)
        second = first.copy()
        second.loc[:, "trial_id"] = "independent_round"
        second.loc[:, "taxa_sucesso"] = 100.0
        second.loc[:, "total_testes"] = 100
        second.loc[:, "aprovados"] = 100
        second.loc[:, "reprovados"] = 0
        second.loc[:, "passou_todos"] = True
        view = build_view(pd.concat([first, second], ignore_index=True))
        self.assertEqual(view["stats"][self.row["Tratamento"]]["sucesso"]["mean"], 62.5)

    def test_quartiles_use_linear_interpolation_and_metric_specific_samples(self):
        self.write_registry([self.row])
        self.write_reports()
        sample = pd.concat([load_trials(self.data_dir)] * 4, ignore_index=True)
        sample["trial_id"] = [f"quartile_round_{index}" for index in range(4)]
        sample["tempo_min"] = [1.0, 2.0, 3.0, 100.0]
        sample["complexidade_media"] = [1.0, None, 9.0, 13.0]
        stats = build_view(sample)["stats"][self.row["Tratamento"]]
        self.assertEqual(stats["tempo"], {"n": 4, "median": 2.5, "q1": 1.75, "q3": 27.25})
        self.assertEqual(stats["complexidade"], {"n": 3, "median": 9.0, "q1": 5.0, "q3": 11.0})


if __name__ == "__main__":
    unittest.main()
