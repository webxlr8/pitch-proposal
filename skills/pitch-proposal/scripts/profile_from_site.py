#!/usr/bin/env python3
"""Draft a company profile (the company that SENDS the proposal) from its website.

Usage:
    python3 profile_from_site.py <https://your-company.com> --out profiles/<name> [--theme dark|light] [--force]

Finds: name, tagline, description, logo(s), brand colours (CSS variables and most-used colours),
fonts (Google Fonts / font-family), emails (incl. Cloudflare-protected), phones, social links, and the
services named in the menu and headings.

Writes (same format as the pitch-audit skill, so one profile serves both):
  company.yaml   filled in, review it
  theme.json     CSS variables for the proposal theme + font URLs
  proof.yaml     skeleton: add ONLY approved, public claims (stats, clients, how you work)
  services.md    services and headings found, to draft the "why us" copy
  brand/         downloaded logo files (+ a white version for dark pages when needed)
  report.md      what was found, what is missing, what to check
"""
import argparse
import io
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import domain, fetch, hex_rgb, luminance, same_site, saturation, slugify  # noqa: E402

ICON_FONTS = re.compile(r"awesome|icon|icomoon|theme|ui-monospace|dashicons|eicons|glyph|fa-|material|swiper|slick|elementor", re.I)
GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "initial", "-apple-system", "arial",
           "helvetica", "helvetica neue", "segoe ui", "roboto", "times new roman", "georgia", "verdana", "var"}


def colours_from_css(css):
    hexes = [h.upper() for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css)]
    norm = []
    for h in hexes:
        h = "#" + (h if len(h) == 6 else "".join(c * 2 for c in h))
        norm.append(h)
    named = {}
    for name, val in re.findall(r"(--[\w-]*(?:accent|primary|brand|main|theme|secondary)[\w-]*)\s*:\s*(#[0-9a-fA-F]{3,6})\b", css, re.I):
        named.setdefault(name, "#" + (val[1:] if len(val) == 7 else "".join(c * 2 for c in val[1:])).upper())
    return Counter(norm), named


def pick_accent(counts, named):
    def good(h):
        return saturation(h) > .35 and .03 < luminance(h) < .75
    for name, h in named.items():
        if good(h) and ("accent" in name or "primary" in name or "brand" in name):
            return h, f"CSS variable {name}"
    for h, n in counts.most_common(60):
        if good(h):
            return h, f"most-used brand-like colour ({n}×)"
    return None, "none found"


def fonts_from(html, css):
    gf = re.findall(r'href="(https://fonts\.googleapis\.com/css2?\?[^"]+)"', html)
    fams = []
    for u in gf:
        fams += [urllib.parse.unquote_plus(f.split(":")[0]) for f in re.findall(r"family=([^&]+)", u.replace("&amp;", "&"))]
    decl = Counter()
    for ff in re.findall(r"font-family\s*:\s*([^;}{]+)", css + html):
        first = ff.split(",")[0].strip().strip("'\"")
        if first and first.lower() not in GENERIC and not ICON_FONTS.search(first) and not first.startswith("var("):
            decl[first] += 1
    for f, _ in decl.most_common(4):
        if f not in fams:
            fams.append(f)
    return fams, [u.replace("&amp;", "&") for u in gf]


def logo_candidates(html, base):
    """Logo <img> tags, header first (later 'logo' images are often client logos), then icons."""
    c = []
    header = re.search(r"<header\b.*?</header>", html, re.S | re.I)
    scopes = ([header.group(0)] if header else []) + [html[:max(len(html) // 4, 20000)]]
    for scope in scopes:
        for m in re.finditer(r"<img\b[^>]*>", scope, re.I):
            tag = m.group(0)
            src = re.search(r'\s(?:data-src|src)="([^"]+)"', tag)
            if src and re.search(r"logo|brand", tag, re.I) and not src.group(1).startswith("data:"):
                c.append(urllib.parse.urljoin(base, src.group(1)))
        if c:
            break
    for m in re.finditer(r"<img\b[^>]*>", "", re.I):
        tag = m.group(0)
        src = re.search(r'\s(?:data-src|src)="([^"]+)"', tag)
        if src and re.search(r"logo", tag, re.I) and not src.group(1).startswith("data:"):
            c.append(urllib.parse.urljoin(base, src.group(1)))
    for m in re.finditer(r'<link[^>]+rel="(?:apple-touch-icon|icon)"[^>]*href="([^"]+)"', html, re.I):
        c.append(urllib.parse.urljoin(base, m.group(1)))
    og = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if og:
        c.append(og.group(1))
    return list(dict.fromkeys(c))


def logo_tone(data):
    """'light' (for dark backgrounds), 'dark' (for light backgrounds) or None if unknown (SVG)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None
    im.thumbnail((200, 200))
    px = [p for p in im.getdata() if p[3] > 128]
    if not px:
        return None
    lum = sum(.2126 * r + .7152 * g + .0722 * b for r, g, b, _ in px) / len(px) / 255
    return "light" if lum > .72 else "dark"


def make_white(src, dst):
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    a = im.split()[3]
    white = Image.new("RGBA", im.size, (255, 255, 255, 0))
    white.putalpha(a)
    Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 0)), white).save(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--theme", choices=["dark", "light"], default="light")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    url = a.url if "//" in a.url else "https://" + a.url
    out = Path(a.out)
    if (out / "company.yaml").exists() and not a.force:
        raise SystemExit(f"{out}/company.yaml exists. Use --force to overwrite.")
    (out / "brand").mkdir(parents=True, exist_ok=True)

    st, final, html = fetch(url)
    if st != 200:
        raise SystemExit(f"Could not open {url} (HTTP {st}).")
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    sheets = [urllib.parse.urljoin(final, h.replace("&amp;", "&")) for h in re.findall(r'<link[^>]+rel="stylesheet"[^>]*href="([^"]+)"', html)]
    sheets += [urllib.parse.urljoin(final, h.replace("&amp;", "&")) for h in re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"[^>]*rel="stylesheet"', html)]
    for s in list(dict.fromkeys(sheets))[:8]:
        if same_site(s, final):
            _, _, txt = fetch(s)
            css += "\n" + (txt or "")

    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    title = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
    site_name = re.search(r'property="og:site_name"\s+content="([^"]+)"', html)
    name = site_name.group(1) if site_name else re.split(r"\s[|–—-]\s", title)[0] or domain(final)
    desc = re.search(r'name="description"\s+content="([^"]*)"', html) or re.search(r'property="og:description"\s+content="([^"]*)"', html)
    desc = desc.group(1).strip() if desc else ""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    h1 = re.sub(r"<[^>]+>|\s+", " ", h1.group(1)).strip() if h1 else ""

    counts, named = colours_from_css(css)
    accent, why = pick_accent(counts, named)
    fams, font_urls = fonts_from(html, css)

    emails = {m for m in re.findall(r'mailto:([^"?]+)', html)}
    for cf in re.findall(r'data-cfemail="([0-9a-f]+)"', html):
        k = int(cf[:2], 16)
        emails.add("".join(chr(int(cf[i:i + 2], 16) ^ k) for i in range(2, len(cf), 2)))
    phones = list(dict.fromkeys(re.sub(r"\s+", " ", p).strip() for p in re.findall(r'tel:([^"]+)', html)))
    social = {}
    for net in ("linkedin", "instagram", "facebook", "youtube", "x.com", "twitter"):
        m = re.search(rf'href="(https?://(?:www\.)?{net}[^"]+)"', html)
        if m:
            social[net.replace(".com", "")] = m.group(1)

    logos, logo_light, logo_dark = logo_candidates(html, final), None, None
    for i, lu in enumerate(logos[:4]):
        st, _, data = fetch(lu, binary=True)
        if st != 200 or not data:
            continue
        ext = ".svg" if (lu.lower().split("?")[0].endswith(".svg") or data[:5] == b"<?xml" or b"<svg" in data[:200]) else ".png"
        tone = logo_tone(data) if ext == ".png" else None
        if ext == ".png":
            from PIL import Image
            im = Image.open(io.BytesIO(data))
            if im.width < 120:
                continue  # favicon-sized
            dst = out / "brand" / f"logo-{i}.png"
            im.convert("RGBA").save(dst)
        else:
            dst = out / "brand" / f"logo-{i}.svg"
            dst.write_bytes(data)
        if tone == "light" and not logo_light:
            logo_light = dst.name
        elif tone in ("dark", None) and not logo_dark:
            logo_dark = dst.name
    if logo_dark and not logo_light and logo_dark.endswith(".png"):
        make_white(out / "brand" / logo_dark, out / "brand" / "logo-on-dark.png")
        logo_light = "logo-on-dark.png"

    nav = list(dict.fromkeys(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()
                             for t in re.findall(r"<nav[^>]*>.*?</nav>", html, re.S) for t in re.findall(r"<a[^>]*>(.*?)</a>", t, re.S)))
    heads = [re.sub(r"<[^>]+>|\s+", " ", h).strip() for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.S)]
    heads = [h for h in dict.fromkeys(heads) if 2 < len(h) < 90]

    company = {
        "id": slugify(name), "name": name, "website": final.rstrip("/"),
        "tagline": h1[:90] or desc[:90], "one_liner": desc[:220],
        "language": (re.search(r'<html[^>]*lang="([a-z]{2})', html) or [None, "en"])[1],
        "contact": {"email": sorted(emails)[0] if emails else None, "phone": phones[0] if phones else None,
                    "address_short": None},
        "social": social,
        "brand": {"logo": f"brand/{logo_dark}" if logo_dark else None,
                  "logo_on_dark": f"brand/{logo_light}" if logo_light else None, "logo_height": 30,
                  "accent": accent, "background": "#0B0B0B" if a.theme == "dark" else "#FAF8F4",
                  "heading_font": fams[0] if fams else "Inter", "body_font": fams[1] if len(fams) > 1 else (fams[0] if fams else "Inter")},
    }
    import yaml
    (out / "company.yaml").write_text("# Drafted by profile_from_site.py — review every field.\n" + yaml.safe_dump(company, sort_keys=False, allow_unicode=True))
    if not (out / "proof.yaml").exists():
        (out / "proof.yaml").write_text(
            "# Only approved, public claims. Proposals never invent numbers or client names.\n"
            "stats: []        # e.g. - { value: \"100+\", label: Brands served }\n"
            "clients: []      # names you are allowed to show\n"
            "how_we_work: []  # e.g. - { title: Full handover, body: You own the code and docs. }\n")
    theme = {"name": company["id"], "mode": a.theme, "source": f"{final} (profile_from_site.py)",
             "fonts": font_urls, "vars": {k: v for k, v in {"--accent": accent}.items() if v}}
    (out / "theme.json").write_text(json.dumps(theme, indent=2))
    (out / "services.md").write_text(f"# {name} · services and headings found\n\n## Menu\n" + "\n".join(f"- {n}" for n in nav[:40])
                                     + "\n\n## Headings (home)\n" + "\n".join(f"- {h}" for h in heads[:60]) + f"\n\n## Description\n{desc}\n")
    top = ", ".join(f"{h} ({n})" for h, n in counts.most_common(8))
    rep = [f"# Profile report · {name}", "", f"- Website: {final}", f"- Accent: {accent or 'not found'} ({why})",
           f"- Named colour variables: {', '.join(f'{k}={v}' for k, v in list(named.items())[:8]) or 'none'}",
           f"- Most-used colours: {top}", f"- Fonts: {', '.join(fams) or 'not found'}",
           f"- Logo (for light pages): {logo_dark or 'missing'} · logo (for dark pages): {logo_light or 'missing'}",
           f"- Emails: {', '.join(sorted(emails)) or 'none'} · phones: {', '.join(phones[:4]) or 'none'}",
           f"- Social: {', '.join(social) or 'none'}", "",
           "## To do", "- Check the logos in brand/ (a white version was generated if only a dark logo existed).",
           "- Fill proof.yaml with approved claims only.", "- Set --theme or theme.json \"mode\" to dark/light, and adjust vars if the accent is wrong.",
           "- Add contact.address_short."]
    (out / "report.md").write_text("\n".join(rep) + "\n")
    print("\n".join(rep[:9]))
    print(f"✓ {out}/company.yaml, theme.json, proof.yaml, services.md, brand/")


if __name__ == "__main__":
    main()
