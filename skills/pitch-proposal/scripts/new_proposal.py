#!/usr/bin/env python3
"""Scaffold a proposal folder from page templates and a company profile.

Usage:
    python3 new_proposal.py <client-slug> --client "Client Name" [--preset build|refresh|plan]
                            [--pages cover-concept,understanding,...] [--profile pitch-profile]
                            [--theme dark|light] [--client-domain client.com] [--out clients]

Creates clients/<slug>/ with:
  proposal.html   assembled pages, brand tokens filled in from the profile (edit the copy here)
  proposal.json   settings read by build.py (no_prices, ban list, output name)
  assets/         base.css, ui.css, theme defaults, theme.css (your brand), logo
  images/         placeholder JPGs for every image slot (replace them; build.py fails while any remain)
  notes.md        assumptions and open questions to confirm before sending
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TEMPLATES, domain, find_profile, hex_rgb, load_profile, luminance, shift, slugify  # noqa: E402

PRESETS = {
    # new build (from a brief, a profile or a reference site)
    "build": ["cover-concept", "understanding", "features-pair", "features-shop-give", "feature-grid",
              "homepage-concept", "sitemap", "scope-modules", "delivery", "why-us"],
    # existing site: clone + fix + refresh, nothing else
    "refresh": ["cover-screenshot", "site-structure", "site-review", "scope-steps"],
    # page-by-page website plan for a company profile
    "plan": ["cover-concept", "understanding", "sitemap", "page-plan", "homepage-concept",
             "feature-grid", "delivery", "why-us"],
}

FONT_URL = "https://fonts.googleapis.com/css2?family={}&display=swap"


def theme_css(profile, mode):
    """Turn the profile (theme.json or company.yaml brand) into CSS variable overrides."""
    vars_ = dict(profile["theme"].get("vars", {}))
    brand = profile["company"].get("brand", {}) or {}
    out = {}
    accent = vars_.get("--accent") or brand.get("accent")
    if accent:
        out["--accent"] = accent
        out["--accent-rgb"] = ",".join(map(str, hex_rgb(accent)))
        out["--glow-rgb"] = out["--accent-rgb"]
        out["--hl"] = vars_.get("--num-solid") or (accent if mode == "dark" else shift(accent, -0.06))
        out["--accent-2"] = vars_.get("--accent-2") or brand.get("accent_2") or shift(accent, 0.12)
        out["--on-accent"] = vars_.get("--accent-ink") or ("#0B0B0B" if luminance(accent) > .35 else "#FFFFFF")
    if mode == "dark":
        bg = vars_.get("--bg") or (brand.get("background") if brand.get("background") and luminance(brand["background"]) < .2 else None)
        if bg:
            out["--bg"] = bg
            out["--bg-rgb"] = ",".join(map(str, hex_rgb(bg)))
            out["--bg-2"] = vars_.get("--bg-2") or shift(bg, .03)
        for k in ("--text", "--body", "--muted", "--line"):
            if vars_.get(k):
                out[k] = vars_[k]
    head = vars_.get("--head") or (f'"{brand["heading_font"]}",system-ui,sans-serif' if brand.get("heading_font") else None)
    sans = vars_.get("--sans") or (f'"{brand["body_font"]}",system-ui,sans-serif' if brand.get("body_font") else None)
    if head:
        out["--head"] = head
    if sans:
        out["--sans"] = sans
    for k in ("--head-weight", "--head-track"):
        if vars_.get(k):
            out[k] = vars_[k]
    body = "\n".join(f"  {k}:{v};" for k, v in out.items())
    return f"/* generated from the company profile by new_proposal.py · edit freely */\n:root{{\n{body}\n}}\n"


def font_links(profile):
    fonts = list(profile["theme"].get("fonts", []))
    brand = profile["company"].get("brand", {}) or {}
    names = {brand.get("heading_font"), brand.get("body_font"), "Inter"} - {None}
    if not fonts:
        fams = "&family=".join(f"{n.replace(' ', '+')}:wght@400;500;600;700;800" for n in sorted(names))
        fonts.append(FONT_URL.format(fams))
    fonts.append(FONT_URL.format("Cormorant+Garamond:wght@500;600;700"))  # concept-screen serif
    return "\n".join(f'<link href="{html.escape(u)}" rel="stylesheet">' for u in fonts)


def pick_logo(profile, mode, assets):
    brand = profile["company"].get("brand", {}) or {}
    order = ["logo_on_dark", "logo"] if mode == "dark" else ["logo", "logo_on_dark"]
    for key in order:
        rel = brand.get(key)
        if rel and (profile["dir"] / rel).exists():
            src = profile["dir"] / rel
            dst = assets / f"logo{src.suffix}"
            shutil.copy(src, dst)
            return f"assets/{dst.name}"
    print("  ! no logo in profile brand/ — header shows alt text only", file=sys.stderr)
    return "assets/logo.png"


def proof_blocks(profile):
    proof = profile["proof"] or {}
    stats = "".join(f'<div class="card stat"><b>{html.escape(str(s["value"]))}</b><span>{html.escape(str(s["label"]))}</span></div>'
                    for s in (proof.get("stats") or [])[:4])
    how = "".join(f'<div class="card tile"><b style="margin-top:0">{html.escape(h["title"])}</b><span>{html.escape(h["body"])}</span></div>'
                  for h in (proof.get("how_we_work") or [])[:3])
    clients = proof.get("clients") or []
    cl = ""
    if clients:
        cl = ('<div class="card mt-4" style="padding:4mm 5mm;font-size:8pt;line-height:1.7"><div class="k" style="margin-bottom:1.4mm">Trusted by</div>'
              f'<b style="color:var(--text);font-weight:600">{" · ".join(html.escape(c) for c in clients[:12])}</b></div>')
    return stats, how, cl


def contact_row(company):
    c = company.get("contact", {}) or {}
    items = [("Email", c.get("email")), ("Phone", c.get("phone")), ("Web", domain(company.get("website", "")) if company.get("website") else None)]
    return "".join(f"<div><span>{k}</span><b>{html.escape(v)}</b></div>" for k, v in items if v)


def placeholder(path, label):
    """Neutral gradient JPG with the slot name, so drafts render. build.py refuses to ship these."""
    from PIL import Image, ImageDraw
    w, h = 1400, 900
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(0, w, 4):
            v = int(70 + 60 * (x / w) + 40 * (y / h))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = (v, v - 6, v - 14)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, w - 40, h - 40], outline=(200, 190, 175), width=4)
    d.text((70, 70), f"PLACEHOLDER  {label}", fill=(245, 240, 232))
    im.save(path, quality=80, comment=b"pitch-proposal placeholder")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--client", required=True, help='Client name, or "[Client Brand Name]" when unknown')
    ap.add_argument("--preset", choices=PRESETS, default="build")
    ap.add_argument("--pages", help="comma-separated page templates (overrides --preset)")
    ap.add_argument("--profile")
    ap.add_argument("--theme", choices=["dark", "light"])
    ap.add_argument("--client-domain", default="")
    ap.add_argument("--doc-type", default="Website Proposal")
    ap.add_argument("--out", default="clients")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    profile = load_profile(find_profile(a.profile))
    company = profile["company"]
    mode = a.theme or profile["theme"].get("mode") or (
        "dark" if luminance((company.get("brand") or {}).get("background") or "#0B0B0B") < .2 else "light")

    out = Path(a.out) / slugify(a.slug)
    if out.exists() and (out / "proposal.html").exists() and not a.force:
        raise SystemExit(f"{out}/proposal.html exists. Use --force to overwrite.")
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(exist_ok=True)

    for f in ("base.css", "ui.css"):
        shutil.copy(TEMPLATES / f, out / "assets" / f)
    shutil.copy(TEMPLATES / "themes" / f"{mode}.css", out / "assets" / "theme-defaults.css")
    (out / "assets" / "theme.css").write_text(theme_css(profile, mode))
    logo = pick_logo(profile, mode, out / "assets")

    pages = a.pages.split(",") if a.pages else PRESETS[a.preset]
    body = []
    for p in pages:
        f = TEMPLATES / "pages" / f"{p.strip()}.html"
        if not f.exists():
            raise SystemExit(f"Unknown page template: {p}. Available: {', '.join(sorted(x.stem for x in (TEMPLATES / 'pages').glob('*.html')))}")
        body.append(f.read_text())

    stats, how, clients = proof_blocks(profile)
    cdomain = a.client_domain or "yourbrand.com"
    city = (company.get("contact") or {}).get("address_short")
    tokens = {
        "LOGO": logo,
        "COMPANY": html.escape(company.get("name", "Your Company")),
        "WEBSITE": html.escape(domain(company.get("website", "")) if company.get("website") else ""),
        "ONE_LINER": html.escape(company.get("one_liner", "")),
        "WHY_HEADLINE": "We build it, then we <em>stay responsible for it</em>",
        "CLIENT": html.escape(a.client),
        "CLIENT_DOMAIN": html.escape(cdomain),
        "CLIENT_MARK": "YOUR BRAND" if a.client.startswith("[") else html.escape(a.client.upper()),
        "DOC_TYPE": html.escape(a.doc_type),
        "DATE": dt.date.today().strftime("%B %Y"),
        "YEAR": str(dt.date.today().year),
        "PROOF_STATS": stats, "HOW_WE_WORK": how, "CLIENT_LIST": clients,
        "CONTACT_ROW": contact_row(company),
        "CLOSING_NOTE": "Commercials shared separately",
        "CITY_SUFFIX": f" · {html.escape(city)}" if city else "",
    }
    doc = "\n\n".join(body)
    for k, v in tokens.items():
        doc = doc.replace("{{" + k + "}}", v)

    page = f"""<!doctype html>
<html lang="{company.get('language', 'en')}">
<head>
<meta charset="utf-8">
<title>{html.escape(a.doc_type)} · {html.escape(a.client)}</title>
{font_links(profile)}
<link rel="stylesheet" href="assets/theme-defaults.css">
<link rel="stylesheet" href="assets/theme.css">
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" href="assets/ui.css">
<style>
/* proposal-specific tweaks go here */
</style>
</head>
<body>
{doc}
</body>
</html>
"""
    (out / "proposal.html").write_text(page)

    slots = sorted(set(re.findall(r'src="images/([^"]+)"', doc)))
    made = []
    for s in slots:
        p = out / "images" / s
        if not p.exists():
            placeholder(p, s)
            made.append(s)
    (out / "images" / ".placeholders.json").write_text(json.dumps(made, indent=1))

    cfg = {
        "client": a.client, "company": company.get("name"), "preset": a.preset if not a.pages else "custom",
        "theme": mode, "no_prices": True, "ban": [], "output": f"{a.client.strip('[]')} {a.doc_type} - {company.get('name', '')}.pdf",
    }
    if not (out / "proposal.json").exists() or a.force:
        (out / "proposal.json").write_text(json.dumps(cfg, indent=2))
    if not (out / "notes.md").exists():
        (out / "notes.md").write_text(f"# {a.client} · notes\n\n## Assumptions to confirm\n- \n\n## Sources\n- \n\n## Image credits\nSee images/credits.json\n")

    print(f"✓ {out}/proposal.html  ({len(pages)} pages, {mode} theme, profile: {company.get('name')})")
    print(f"  {len(made)} placeholder images in {out}/images/ — replace them (stock_photos.py / screenshots.py)")
    print(f"  next: edit copy in proposal.html, then  python3 {Path(__file__).parent}/build.py {out}")


if __name__ == "__main__":
    main()
