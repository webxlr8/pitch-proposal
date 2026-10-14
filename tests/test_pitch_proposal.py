"""Unit tests that need no network and no browser."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "pitch-proposal" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build  # noqa: E402
import crawl_site  # noqa: E402
import new_proposal  # noqa: E402
import stock_photos  # noqa: E402
from common import load_profile  # noqa: E402


class PriceCheck(unittest.TestCase):
    def test_flags_amounts_and_pricing(self):
        for t in ["₹ 450", "Rs. 9000", "USD 5,000", "$1,200", "Pricing on request", "₹25,000 + 18% GST", "AED 3000"]:
            self.assertTrue(build.PRICE_RE.search(t), t)

    def test_allows_ordinary_words(self):
        for t in ["product pages with price and stock", "Fixed price, written scope", "prices and colours are placeholders",
                  "Each batch shows fee and venue"]:
            self.assertFalse(build.PRICE_RE.search(t), t)

    def test_concept_screens_are_not_copy(self):
        p = build.CopyText()
        p.feed('<section class="page"><p>Real copy</p><div class="ui panel"><b>₹ 450</b><img src="x"><span>more</span></div><p>After</p></section>')
        self.assertEqual(p.out, ["Real copy", "After"])


class Scaffold(unittest.TestCase):
    def test_new_proposal_fills_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(SCRIPTS / "new_proposal.py"), "acme", "--client", "Acme Ltd",
                                "--profile", str(ROOT / "examples/profiles/northwind"), "--preset", "refresh", "--out", tmp],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = Path(tmp) / "acme"
            html = (d / "proposal.html").read_text()
            self.assertNotIn("{{", html)
            self.assertIn("Northwind Studio", html)
            self.assertEqual(html.count('<section class="page'), 4)
            self.assertTrue((d / "assets/theme.css").read_text().count("--accent:#0F766E"))
            cfg = json.loads((d / "proposal.json").read_text())
            self.assertTrue(cfg["no_prices"])
            self.assertTrue(json.loads((d / "images/.placeholders.json").read_text()))

    def test_theme_from_profile(self):
        css = new_proposal.theme_css(load_profile(ROOT / "examples/profiles/webxlr8"), "dark")
        self.assertIn("--accent:#FF6A3A", css)
        self.assertIn("--bg:#0B0B0B", css)

    def test_every_preset_page_exists(self):
        pages = {p.stem for p in (ROOT / "skills/pitch-proposal/templates/pages").glob("*.html")}
        for preset, names in new_proposal.PRESETS.items():
            self.assertTrue(set(names) <= pages, preset)


class Crawl(unittest.TestCase):
    def test_menu_forms_iframes(self):
        html = ('<html><head><title>T</title><meta name="description" content="D"></head><body>'
                '<nav><ul class="menu"><li><a href="/about">About</a></li><li><a href="/shop">Shop</a></li></ul></nav>'
                '<h1>Hello</h1><form action="/send"><input name="email"><input type="hidden" name="x"><textarea name="msg"></textarea></form>'
                '<iframe src="https://www.youtube.com/embed/abc"></iframe><a href="/blog">Blog</a></body></html>')
        p = crawl_site.Page("https://example.com/")
        p.feed(html)
        self.assertEqual(p.title, "T")
        self.assertEqual([l for l, _ in p.nav], ["About", "Shop"])
        self.assertEqual(p.forms[0]["fields"], ["email", "msg"])
        self.assertEqual(crawl_site.classify_iframe(p.iframes[0]), "YouTube")


class Photos(unittest.TestCase):
    def test_unsplash_ids(self):
        self.assertEqual(stock_photos.unsplash_id("https://unsplash.com/photos/ZARfCYDaVg0"), "ZARfCYDaVg0")
        self.assertEqual(stock_photos.unsplash_id("https://unsplash.com/photos/group-of-people-doing-yoga-ZARfCYDaVg0"), "ZARfCYDaVg0")
        self.assertIsNone(stock_photos.unsplash_id("https://example.com/x.jpg"))


if __name__ == "__main__":
    unittest.main()
