#!/usr/bin/env python3
"""Render proposal.html to an A4 PDF, make page previews, and check it before it is sent.

Usage:
    python3 build.py clients/<slug> [--no-check] [--dpi 90]

Writes:
  <output>.pdf            name from proposal.json "output"
  previews/page-XX.png    one image per page (look at every one)
  previews/overview.png   contact sheet of all pages
  build/report.md         check results

Checks (errors stop the build with exit code 1, warnings do not):
  E  page count differs from the number of <section class="page"> (content overflowed a page)
  E  unfilled {{TOKENS}}, missing image files, placeholder images still in use
  E  amounts or pricing words in proposal copy when "no_prices" is true (concept screens are skipped)
  E  banned words found anywhere (proposal.json "ban": reference-site names, other brands)
  W  leftover template sample copy, [bracket] placeholders
  W  pages with a large empty area at the bottom
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import chrome  # noqa: E402

PRICE_RE = re.compile(r"(₹\s?\d|\bRs\.?\s?\d|\b(?:INR|USD|AED|SAR|EUR|GBP)\s?\d|[$€£]\s?\d|\d\s?(?:INR|USD|AED|SAR)\b|"
                      r"\bpricing\b|\bquotation\b|\btotal cost\b|\bcost of\b|\binvestment\b|\b\d+\s?%\s?(?:GST|VAT)\b|\+\s?(?:GST|VAT)\b)", re.I)
TEMPLATE_COPY = ["Programme one", "Programme two", "Problem in one line", "What it holds", "Module one",
                 "Product name goes here", "Cause one", "Fix one", "Page one", "A short, real quote",
                 "One warm call to action", "Item one", "Featured item", "Short detail line",
                 '<span class="pill">Function</span>']
SKIP_CLASSES = {"ui", "dash", "win", "phone"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class CopyText(HTMLParser):
    """Visible proposal copy, skipping concept screens (.ui/.dash/.win/.phone), scripts and styles."""

    def __init__(self):
        super().__init__()
        self.stack, self.skip, self.out = [], 0, []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        cls = set((dict(attrs).get("class") or "").split())
        s = bool(cls & SKIP_CLASSES) or tag in ("style", "script", "head")
        self.stack.append(s)
        self.skip += s

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        self.skip -= self.stack.pop()

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.out.append(data.strip())


def pdf_pages_and_text(pdf):
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(pdf))
        text = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
        return len(doc), "\n".join(text)
    except ImportError:
        pass
    try:
        import fitz  # type: ignore
        doc = fitz.open(str(pdf))
        return doc.page_count, "\n".join(p.get_text() for p in doc)
    except ImportError:
        pass
    if shutil.which("pdftotext") and shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        return n, txt
    raise SystemExit("Need pypdfium2 (pip install pypdfium2), PyMuPDF, or poppler (pdftotext) to check the PDF.")


def render_previews(pdf, outdir, dpi):
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("page-*.png"):
        old.unlink()
    scale = dpi / 72
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(pdf))
        for i in range(len(doc)):
            doc[i].render(scale=scale).to_pil().convert("RGB").save(outdir / f"page-{i + 1:02d}.png")
        return sorted(outdir.glob("page-*.png"))
    except ImportError:
        pass
    try:
        import fitz  # type: ignore
        doc = fitz.open(str(pdf))
        for i, p in enumerate(doc):
            p.get_pixmap(matrix=fitz.Matrix(scale, scale)).save(str(outdir / f"page-{i + 1:02d}.png"))
        return sorted(outdir.glob("page-*.png"))
    except ImportError:
        pass
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(outdir / "page")], check=True)
        for p in outdir.glob("page-*.png"):  # pdftoppm pads differently: normalise to page-XX.png
            n = int(re.search(r"-(\d+)\.png$", p.name).group(1))
            p.rename(outdir / f"page-{n:02d}.png")
        return sorted(outdir.glob("page-*.png"))
    raise SystemExit("Need pypdfium2, PyMuPDF or poppler (pdftoppm) to render previews.")


def blank_bottom(png):
    """Share of the page body (between header and footer) left empty at the bottom."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    mm = h / 297
    top, foot = int(18 * mm), int((297 - 14) * mm)
    px = im.load()
    step = max(1, w // 300)
    for y in range(foot - 2, top, -1):
        row = [px[x, y] for x in range(int(15 * mm), int(w - 15 * mm), step)]
        med = sorted(row)[len(row) // 2]
        if sum(1 for v in row if abs(v - med) > 22) > len(row) * 0.01:
            return (foot - y) / (foot - top)
    return 1.0


def overview(pngs, out):
    from PIL import Image
    thumbs = [Image.open(p).convert("RGB") for p in pngs]
    tw = 300
    thumbs = [t.resize((tw, int(t.height * tw / t.width))) for t in thumbs]
    cols = min(5, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    th = thumbs[0].height
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 16) + 16), (60, 60, 60))
    for i, t in enumerate(thumbs):
        sheet.paste(t, (16 + (i % cols) * (tw + 16), 16 + (i // cols) * (th + 16)))
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--dpi", type=int, default=90)
    a = ap.parse_args()

    d = Path(a.dir).resolve()
    src = d / "proposal.html"
    if not src.exists():
        raise SystemExit(f"{src} not found. Create it with new_proposal.py.")
    cfg = json.loads((d / "proposal.json").read_text()) if (d / "proposal.json").exists() else {}
    html_text = src.read_text()
    out_pdf = d / (cfg.get("output") or "proposal.pdf")

    t = time.time()
    tmp = d / "build" / "render.pdf"
    tmp.parent.mkdir(exist_ok=True)
    r = chrome(["--no-pdf-header-footer", "--virtual-time-budget=20000", "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={tmp}", src.as_uri()])
    if not tmp.exists():
        raise SystemExit(f"Chrome did not write the PDF:\n{r.stderr[-800:]}")
    shutil.move(tmp, out_pdf)
    pages, text = pdf_pages_and_text(out_pdf)
    pngs = render_previews(out_pdf, d / "previews", a.dpi)
    overview(pngs, d / "previews" / "overview.png")

    errors, warns = [], []
    if not a.no_check:
        n_sections = len(re.findall(r'<section\s+class="page[\s"]', html_text))
        if pages != n_sections:
            errors.append(f"PDF has {pages} pages but proposal.html has {n_sections} <section class=\"page\">: "
                          "content overflowed a page. Shorten copy or split the page.")
        for tok in sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", html_text))):
            errors.append(f"Unfilled token {tok}")
        refs = sorted(set(re.findall(r'(?:src|href)="((?:images|assets)/[^"]+)"', html_text)))
        for ref in refs:
            p = d / ref
            if not p.exists():
                errors.append(f"Missing file: {ref}")
            elif p.suffix.lower() in (".jpg", ".jpeg") and b"pitch-proposal placeholder" in p.read_bytes()[:4096]:
                errors.append(f"Placeholder image still in use: {ref}")

        parser = CopyText()
        parser.feed(html_text)
        copy = " \n".join(parser.out)
        allow = [s.lower() for s in cfg.get("allow", [])]
        if cfg.get("no_prices", True):
            for m in PRICE_RE.finditer(copy):
                ctx = copy[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
                if not any(al in ctx.lower() for al in allow):
                    errors.append(f"Price wording in copy (no_prices is on): “…{ctx}…”  "
                                  "(rewrite, or add a phrase to proposal.json \"allow\")")
        low = text.lower()
        for term in cfg.get("ban", []):
            if term.lower() in low:
                errors.append(f"Banned term found in PDF: “{term}”")

        for s in TEMPLATE_COPY:
            if s in html_text:
                warns.append(f"Template sample copy still present: {re.sub('<[^>]+>', '', s)}")
        for m in sorted(set(re.findall(r"\[[A-Z][^\]]{2,40}\]", copy))):
            warns.append(f"Bracket placeholder in copy: {m} (fine on purpose, e.g. [Client Brand Name])")
        for i, p in enumerate(pngs, 1):
            b = blank_bottom(p)
            if 0.22 < b < 1.0 and i > 1:
                warns.append(f"Page {i:02d}: bottom {b:.0%} of the page body is empty. Enlarge blocks or add content.")

    rep = [f"# Build report · {cfg.get('client', d.name)}", "", f"- PDF: `{out_pdf.name}` ({pages} pages, "
           f"{out_pdf.stat().st_size / 1e6:.1f} MB, {time.time() - t:.0f}s)", f"- Previews: `previews/` and `previews/overview.png`", ""]
    rep += ["## Errors"] + ([f"- {e}" for e in errors] or ["- none"]) + ["", "## Warnings"] + ([f"- {w}" for w in warns] or ["- none"])
    rep += ["", "Now open every `previews/page-XX.png` yourself: clipped text, overlaps, a word alone on a line, busy photo behind text."]
    (d / "build" / "report.md").write_text("\n".join(rep) + "\n")

    print(f"{'✗' if errors else '✓'} {out_pdf}  ({pages} pages)")
    for e in errors:
        print("  ERROR", e)
    for w in warns:
        print("  warn ", w)
    print(f"  report: {d / 'build' / 'report.md'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
