"""QA opcional: pip install playwright; DASHBOARD_BROWSER_TESTS=1.

Usa o Edge instalado (headless). PLAYWRIGHT_CHANNEL permite escolher chrome.
Não é dependência do site. Evidências visuais ficam em qa-output/ (ignorado).
"""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENABLED = os.environ.get("DASHBOARD_BROWSER_TESTS") == "1"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(ENABLED, "Defina DASHBOARD_BROWSER_TESTS=1 para validar no navegador.")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright

        cls.manifest = json.loads((ROOT / "public/data/manifest.json").read_text(encoding="utf-8"))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "public")))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch(channel=os.environ.get("PLAYWRIGHT_CHANNEL", "msedge"), headless=True)
        (ROOT / "qa-output").mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1050}, accept_downloads=True)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def ready(self, query=""):
        self.page.goto(self.url + "/" + query)
        self.page.wait_for_function("document.querySelectorAll('img[src*=\"charts/\"]').length === 5")
        self.page.locator("img").evaluate_all("imgs => imgs.forEach(img => img.loading = 'eager')")

    def select_view(self, participant, kata):
        self.page.locator("select").nth(0).select_option(participant)
        self.page.locator("select").nth(1).select_option(kata)
        key = participant + "__" + kata
        self.page.wait_for_function("key => [...document.querySelectorAll('img[src*=\"charts/\"]')].every(img => img.getAttribute('src').includes(key))", arg=key)

    def test_all_28_filters_update_table_charts_and_downloads(self):
        self.ready()
        for key, view in self.manifest["views"].items():
            with self.subTest(view=key):
                self.select_view(view["integrante"], view["kata"])
                self.assertEqual(self.page.locator("tbody tr").count(), view["counts"]["total"])
                images = self.page.locator("img[src*='charts/']")
                self.assertEqual({path.removeprefix('./') for path in images.evaluate_all("imgs => imgs.map(img => img.getAttribute('src'))")}, {chart["display"] for chart in view["charts"].values()})
                links = [path.removeprefix('./') for path in self.page.locator("a[download]").evaluate_all("links => links.map(a => a.getAttribute('href'))")]
                self.assertIn(view["csv"], links)
                for chart in view["charts"].values():
                    self.assertIn(chart["svg"], links)
                    self.assertIn(chart["png"], links)
        self.select_view("all", "all")
        self.page.wait_for_function("[...document.querySelectorAll('.chart-image')].every(img => img.complete && img.naturalWidth > 0)")
        self.page.screenshot(path=str(ROOT / "qa-output/desktop.png"), full_page=True)
        self.page.screenshot(path=str(ROOT / "qa-output/desktop-top.png"))
        for section in ("tempo", "sucesso", "qualidade"):
            self.page.locator(f"#{section}").screenshot(path=str(ROOT / f"qa-output/{section}-desktop.png"))

    def test_responsive_charts_and_keyboard_expansion(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.ready("?integrante=aulus")
        self.page.wait_for_function("[...document.querySelectorAll('.chart-image')].every(img => img.complete && img.naturalWidth > 0 && img.currentSrc.endsWith('-mobile.svg'))")
        for frame in self.page.locator(".chart-frame").all():
            self.assertTrue(frame.evaluate("el => el.scrollWidth <= el.clientWidth"))
        for section in ("tempo", "sucesso", "qualidade"):
            self.page.locator(f"#{section}").screenshot(path=str(ROOT / f"qa-output/{section}-mobile.png"))
        button = self.page.locator('[data-expand="tempo"]')
        button.focus()
        self.page.keyboard.press("Enter")
        self.assertTrue(self.page.locator("#chart-dialog").is_visible())
        self.assertTrue(self.page.locator("#expanded-chart").get_attribute("src").endswith("aulus__all/tempo.svg"))
        self.assertTrue(self.page.locator("#close-chart-dialog").evaluate("el => el === document.activeElement"))
        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.locator("#chart-dialog").is_visible())
        self.assertTrue(button.evaluate("el => el === document.activeElement"))

    def test_downloads_deliver_selected_data_and_images(self):
        self.ready()
        self.select_view("aulus", "K04")
        view = self.manifest["views"]["aulus__K04"]
        for filename in (view["csv"], view["charts"]["tempo"]["png"], view["charts"]["tempo"]["svg"]):
            with self.page.expect_download() as event:
                self.page.locator(f'a[download][href="./{filename}"]').first.click()
            download = event.value
            self.assertIsNone(download.failure())
            content = Path(download.path()).read_bytes()
            self.assertGreater(len(content), 50)
            if filename.endswith(".csv"):
                self.assertIn(b"aulus_K04_ia_01", content)
                self.assertNotIn(b"maria_K04", content)

    def test_aulus_card_has_requested_labels_and_auditable_csv(self):
        self.ready("?integrante=aulus")
        card = self.page.locator(".kpi-card").first
        self.assertIn("19,8", card.locator(".kpi-value.manual").inner_text())
        self.assertIn("9,15", card.locator(".kpi-value.ia").inner_text())
        self.assertTrue(self.page.locator("#adjustment-note").is_visible())
        self.page.screenshot(path=str(ROOT / "qa-output/aulus-adjusted.png"), full_page=False)
        self.select_view("maria", "all")
        self.assertFalse(self.page.locator("#adjustment-note").is_visible())

    def test_mobile_keyboard_and_missing_metrics(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.ready("?integrante=aulus&kata=K04")
        self.assertEqual(self.page.locator("select").nth(0).input_value(), "aulus")
        self.assertEqual(self.page.locator("select").nth(1).input_value(), "K04")
        self.assertIn("Não disponível", self.page.locator("tbody").inner_text())
        self.assertIn("Sem observações", self.page.locator("body").inner_text())
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.page.screenshot(path=str(ROOT / "qa-output/mobile.png"), full_page=True)
        self.page.screenshot(path=str(ROOT / "qa-output/mobile-top.png"))
        control = self.page.locator("select").nth(1)
        control.focus()
        self.page.keyboard.press("Home")
        self.page.keyboard.press("Enter")
        self.assertEqual(control.input_value(), "all")
        self.assertEqual(self.page.locator("tbody tr").count(), 6)
        self.assertTrue(self.page.evaluate("document.activeElement.tagName === 'SELECT'"))

    def test_manifest_error_can_be_retried(self):
        self.page.route("**/data/manifest.json", lambda route: route.abort())
        self.page.goto(self.url)
        retry = self.page.get_by_role("button", name=re.compile("Tentar|Recarregar", re.I))
        retry.wait_for(state="visible")
        self.page.unroute("**/data/manifest.json")
        retry.click()
        self.page.wait_for_function("document.querySelectorAll('img[src*=\"charts/\"]').length === 5")
        self.assertEqual(self.page.locator("tbody tr").count(), 18)


if __name__ == "__main__":
    unittest.main()
