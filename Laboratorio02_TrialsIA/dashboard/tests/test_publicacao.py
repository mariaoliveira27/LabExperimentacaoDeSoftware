"""Verify that the generated static bundle is complete, portable and current.

Run gerar_dashboard.py before these checks. No browser or server is needed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


DASHBOARD_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = DASHBOARD_DIR.parent / "cronometro"
if not DATA_DIR.is_dir():
    DATA_DIR = DASHBOARD_DIR / "insumos" / "cronometro"
PUBLIC_DIR = DASHBOARD_DIR / "public"
sys.path.insert(0, str(DASHBOARD_DIR))

from dados import build_view, load_trials  # noqa: E402


def reject_nonstandard_json_constant(value):
    raise ValueError(f"JSON must use null, never {value}")


class StaticPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest_path = PUBLIC_DIR / "data" / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError("Generate public/data/manifest.json with gerar_dashboard.py before testing publication.")
        cls.manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
            parse_constant=reject_nonstandard_json_constant,
        )
        cls.frame = load_trials(DATA_DIR)

    def public_file(self, relative):
        self.assertIsInstance(relative, str)
        self.assertFalse(urlsplit(relative).scheme, relative)
        self.assertFalse(PurePosixPath(relative).is_absolute(), relative)
        self.assertNotIn("..", PurePosixPath(relative).parts, relative)
        self.assertNotIn("\\", relative, relative)
        path = (PUBLIC_DIR / relative).resolve()
        self.assertTrue(path.is_relative_to(PUBLIC_DIR.resolve()), relative)
        self.assertTrue(path.is_file(), relative)
        self.assertGreater(path.stat().st_size, 0, relative)
        return path

    def test_manifest_contains_exact_population_and_all_28_views(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        participants = {item["value"] for item in self.manifest["participants"]}
        katas = {item["value"] for item in self.manifest["katas"]}
        self.assertEqual(participants, {"all", "aulus", "maria", "vinicius"})
        self.assertEqual(katas, {"all", *(f"K{i:02}" for i in range(1, 7))})
        self.assertEqual(set(self.manifest["views"]), {f"{p}__{k}" for p in participants for k in katas})
        rows = self.manifest["rows"]
        self.assertEqual(len(rows), 18)
        self.assertEqual({row["trial_id"] for row in rows}, set(self.frame["trial_id"]))
        missing = next(row for row in rows if row["trial_id"] == "aulus_K04_ia_01")
        for field in ("complexidade_media", "loc", "sloc", "total_testes", "aprovados", "reprovados"):
            with self.subTest(field=field):
                self.assertIsNone(missing[field])

    def test_every_view_matches_current_data_and_csv_download(self):
        for key, view in self.manifest["views"].items():
            with self.subTest(view=key):
                participant, kata = key.split("__")
                expected = build_view(self.frame, participant, kata)
                for field in ("integrante", "kata", "row_ids", "counts", "stats"):
                    self.assertEqual(view[field], expected[field], f"{key}/{field}")
                with self.public_file(view["csv"]).open(encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream)
                    rows = list(reader)
                self.assertEqual(len(rows), view["counts"]["total"])
                self.assertEqual([row["trial_id"] for row in rows], view["row_ids"])
                if participant != "all":
                    self.assertEqual({row["integrante"] for row in rows}, {participant})
                if kata != "all":
                    self.assertEqual({row["kata"] for row in rows}, {kata})
                for row in rows:
                    if row["trial_id"] == "aulus_K04_ia_01":
                        self.assertEqual(row["loc"], "")
                        self.assertEqual(row["complexidade_media"], "")

    def test_all_280_chart_downloads_are_valid_portable_images(self):
        checked = 0
        for key, view in self.manifest["views"].items():
            self.assertEqual(set(view["charts"]), {"tempo", "sucesso", "complexidade", "loc", "relacao"})
            for chart, paths in view["charts"].items():
                with self.subTest(view=key, chart=chart):
                    svg = self.public_file(paths["svg"])
                    self.assertEqual(svg.suffix, ".svg")
                    self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")
                    png = self.public_file(paths["png"])
                    self.assertEqual(png.suffix, ".png")
                    with png.open("rb") as stream:
                        header = stream.read(24)
                    self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                    self.assertEqual(header[12:16], b"IHDR")
                    width, height = struct.unpack(">II", header[16:24])
                    self.assertGreaterEqual(width, 200)
                    self.assertGreaterEqual(height, 200)
                    checked += 2
        self.assertEqual(checked, 280)

    def test_responsive_versions_exist_for_every_chart(self):
        for key, view in self.manifest["views"].items():
            for chart, paths in view["charts"].items():
                with self.subTest(view=key, chart=chart):
                    desktop = ET.parse(self.public_file(paths["display"])).getroot()
                    mobile = ET.parse(self.public_file(paths["mobile"])).getroot()
                    self.assertEqual(mobile.tag, "{http://www.w3.org/2000/svg}svg")
                    self.assertLess(float(mobile.attrib["width"].removesuffix("pt")),
                                    float(desktop.attrib["width"].removesuffix("pt")))

    def test_public_text_has_no_machine_specific_windows_paths(self):
        files = [path for path in PUBLIC_DIR.rglob("*") if path.suffix.lower() in {
            ".html", ".css", ".js", ".json", ".csv", ".svg", ".md", ".txt",
        }]
        self.assertGreater(len(files), 100)
        windows_path = re.compile(r"\b[A-Za-z]:[\\/]")
        for path in files:
            with self.subTest(file=path.relative_to(PUBLIC_DIR).as_posix()):
                self.assertIsNone(windows_path.search(path.read_text(encoding="utf-8-sig")))


if __name__ == "__main__":
    unittest.main()
