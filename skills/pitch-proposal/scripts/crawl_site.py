#!/usr/bin/env python3
"""Map a website's structure and functions: pages, menu, forms, embeds, commerce, payments, contact tools.

Usage:
    python3 crawl_site.py <url> --out clients/<slug>/site [--max 60] [--delay 0.4]

Reads sitemap.xml (and sitemap indexes) first, then follows same-site links if needed.
Polite: one request at a time, a short delay, browser User-Agent, no logins, no forms submitted.

Writes:
  site.json    everything found, per page
  site.md      readable summary: tech, menu, page list, forms, and a function inventory with evidence
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from collections import Counter, OrderedDict, defaultdict
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import domain, fetch, same_site  # noqa: E402

SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4|mp3|css|js|ico|xml|json|woff2?)(\?|$)", re.I)

# function inventory: label -> regexes searched in raw HTML (lower-case)
FUNCTIONS = OrderedDict([
    ("Online shop / cart", [r"add[ -]to[ -]cart", r"/cart\b", r"woocommerce", r"cdn\.shopify", r"data-product", r"/products?/"]),
    ("Checkout / online payment", [r"href=\"[^\"]*/checkout", r"checkout\.razorpay|razorpay\.com", r"js\.stripe\.com", r"paypal\.com/sdk|paypalobjects", r"secure\.payu|payu\.in", r"ccavenue", r"paytm\.(in|com)", r"instamojo", r"cashfree"]),
    ("Wishlist", [r"wishlist"]),
    ("Donations", [r"donat(e|ion)", r"\b80g\b", r"recurring|monthly donation"]),
    ("Booking / registration forms", [r"<form[^>]*(regist|book|enrol|enroll|appointment)", r"name=\"(schedule|slot|centre|center)\""]),
    ("Events / calendar", [r"upcoming events?", r"modern-events-calendar|the-events-calendar|tribe-events", r"event-date|class=\"event"]),
    ("Course / class catalogue", [r"/courses?/", r"curriculum", r"course schedule|class timings|batch"]),
    ("Blog / articles", [r"/blog\b", r"/news\b", r"wp-block-post|post-title|article"]),
    ("Video embeds", [r"youtube\.com/embed|youtube-nocookie|player\.vimeo"]),
    ("Maps", [r"google\.com/maps|maps\.googleapis"]),
    ("WhatsApp chat", [r"wa\.me/|api\.whatsapp\.com|web\.whatsapp\.com"]),
    ("Online meetings (Zoom / Meet)", [r"zoom\.us|meet\.google"]),
    ("External forms (Google Forms / Typeform)", [r"forms\.gle|docs\.google\.com/forms|typeform\.com"]),
    ("Member login / accounts", [r"wp-login|/login\b|/sign-?in\b|/register\b|/my-account"]),
    ("Community / forums", [r"buddypress|buddyboss|bbpress|/forums?\b|discourse"]),
    ("Newsletter signup", [r"newsletter|mailchimp|subscribe"]),
    ("Search", [r"type=\"search\"|name=\"s\""]),
    ("Captcha / spam protection", [r"recaptcha|hcaptcha|turnstile|captcha"]),
    ("Cookie consent", [r"cookie(-| )?(consent|notice|banner|law)|cookieyes|complianz"]),
    ("Analytics / ads tags", [r"googletagmanager|gtag\(|google-analytics|fbq\(|facebook\.net/.*/fbevents"]),
    ("Live chat widget", [r"tawk\.to|crisp\.chat|intercom|zendesk|freshchat|livechat"]),
    ("Multi-language", [r"hreflang=|wpml|polylang|weglot|gtranslate"]),
])
TECH = OrderedDict([
    ("WordPress", r"wp-content|wp-includes"), ("Elementor", r"elementor"), ("WooCommerce", r"woocommerce"),
    ("Shopify", r"cdn\.shopify|shopify\.theme"), ("Wix", r"wixstatic|_wix"), ("Squarespace", r"squarespace"),
    ("Webflow", r"webflow"), ("BuddyBoss / BuddyPress", r"buddyboss|buddypress"), ("Laravel", r"laravel_session|csrf-token\" content"),
    ("Next.js", r"/_next/"), ("Astro", r"astro-island|/_astro/"), ("Bootstrap", r"bootstrap(\.min)?\.(css|js)"),
    ("jQuery", r"jquery"), ("Google Tag Manager", r"googletagmanager"),
])
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SOCIAL = ["facebook.com", "instagram.com", "linkedin.com", "youtube.com", "x.com", "twitter.com", "t.me", "tiktok.com", "pinterest."]


class Page(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.title, self.desc, self.gen = "", "", ""
        self.h = []
        self.links, self.nav = [], []
        self.forms, self.iframes = [], []
        self._in, self._buf, self._nav_depth, self._form = None, [], 0, None
        self._a = None
        self._stack = []  # (tag, counted_as_nav)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag in ("title", "h1", "h2", "h3"):
            self._in, self._buf = tag, []
        if tag == "meta":
            n = (a.get("name") or a.get("property") or "").lower()
            if n in ("description", "og:description") and not self.desc:
                self.desc = a.get("content", "")
            if n == "generator":
                self.gen = a.get("content", "")
        if tag not in VOID:
            is_nav = tag == "nav" or (tag in ("ul", "div", "header") and re.search(r"\b(menu|navbar|nav)\b", cls) is not None)
            self._stack.append((tag, is_nav))
            self._nav_depth += is_nav
        if tag == "a" and a.get("href"):
            href = urllib.parse.urljoin(self.base, a["href"].strip())
            self.links.append(href)
            self._a = [href, []]
        if tag == "form":
            self._form = {"action": a.get("action", ""), "method": a.get("method", "get").lower(), "fields": []}
        if tag in ("input", "select", "textarea") and self._form is not None:
            t = a.get("type", tag)
            if t not in ("hidden", "submit", "button"):
                self._form["fields"].append(a.get("name") or a.get("placeholder") or a.get("id") or t)
        if tag == "iframe" and a.get("src"):
            self.iframes.append(a["src"])

    def handle_endtag(self, tag):
        if tag == self._in:
            txt = " ".join("".join(self._buf).split())
            if tag == "title":
                self.title = txt
            elif txt:
                self.h.append((tag, txt[:120]))
            self._in = None
        if tag == "a" and self._a:
            if self._nav_depth:
                label = " ".join("".join(self._a[1]).split())
                if label and len(label) < 40:
                    self.nav.append((label, self._a[0]))
            self._a = None
        if tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None
        if any(t == tag for t, _ in self._stack):
            while self._stack:
                t, n = self._stack.pop()
                self._nav_depth -= n
                if t == tag:
                    break

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
        if self._a:
            self._a[1].append(data)


def sitemap_urls(root):
    found, queue, seen = [], [urllib.parse.urljoin(root, "/sitemap.xml"), urllib.parse.urljoin(root, "/sitemap_index.xml")], set()
    while queue and len(found) < 2000:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        st, _, body = fetch(u)
        if st != 200 or "<loc>" not in body:
            continue
        locs = [l.strip() for l in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)]
        for l in locs:
            (queue if l.endswith(".xml") else found).append(l)
    return [u for u in dict.fromkeys(found) if same_site(u, root) and not SKIP_EXT.search(u)]


def classify_iframe(src):
    s = src.lower()
    for k, v in (("youtube", "YouTube"), ("vimeo", "Vimeo"), ("google.com/maps", "Google Maps"), ("zoom", "Zoom"),
                 ("forms", "Form"), ("calendly", "Calendly"), ("facebook", "Facebook")):
        if k in s:
            return v
    return "Other"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--delay", type=float, default=0.4)
    a = ap.parse_args()

    root = a.url if "//" in a.url else "https://" + a.url
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    st, root_final, home = fetch(root)
    if st != 200:
        raise SystemExit(f"Could not open {root} (HTTP {st}). Check the URL.")
    from_sitemap = sitemap_urls(root_final)
    queue = [root_final] + [u for u in from_sitemap if u.rstrip("/") != root_final.rstrip("/")]
    print(f"sitemap: {len(from_sitemap)} URLs" if from_sitemap else "no sitemap: following links")

    pages, seen, hosts = [], set(), Counter()
    func_hits, tech_hits = defaultdict(list), Counter()
    socials, emails, phones = set(), set(), set()
    raw_cache = {root_final: home}
    while queue and len(pages) < a.max:
        u = re.sub(r"/index\.(html?|php)$", "/", queue.pop(0).split("#")[0])
        if u in seen or SKIP_EXT.search(u):
            continue
        seen.add(u)
        if u in raw_cache:
            body = raw_cache.pop(u)
        else:
            time.sleep(a.delay)
            st, _, body = fetch(u)
            if st != 200 or not body:
                pages.append({"url": u, "status": st})
                continue
        p = Page(u)
        try:
            p.feed(body)
        except Exception:
            pass
        low = body.lower()
        for label, pats in FUNCTIONS.items():
            if any(re.search(x, low) for x in pats):
                func_hits[label].append(u)
        for t, pat in TECH.items():
            if re.search(pat, low):
                tech_hits[t] += 1
        for l in p.links:
            ll = l.lower()
            host = domain(l) if l.startswith("http") else ""
            if host and not same_site(l, root_final):
                hosts[host] += 1
            if any(s in ll for s in SOCIAL):
                socials.add(l.split("?")[0].rstrip("/"))
            if ll.startswith("mailto:"):
                emails.add(l[7:].split("?")[0])
            if ll.startswith("tel:"):
                phones.add(re.sub(r"\s+", " ", l[4:]).strip())
            if l.startswith("http") and same_site(l, root_final) and not from_sitemap and l not in seen:
                queue.append(l)
        for cf in re.findall(r'data-cfemail="([0-9a-f]+)"', body):  # Cloudflare-obfuscated emails
            k = int(cf[:2], 16)
            emails.add("".join(chr(int(cf[i:i + 2], 16) ^ k) for i in range(2, len(cf), 2)))
        pages.append({"url": u, "status": 200, "title": p.title, "description": p.desc, "generator": p.gen,
                      "headings": p.h[:25], "nav": p.nav[:40], "forms": p.forms,
                      "iframes": [{"type": classify_iframe(s), "src": s} for s in p.iframes]})
        print(f"  {len(pages):>3}  {u}")

    nav, labels = [], set()
    for pg in pages[:3]:
        for lab, href in pg.get("nav", []):
            if lab.lower() in labels or re.search(r"/page/\d+|redirect_to=", href) or re.fullmatch(r"page\s?\d+", lab.lower()):
                continue
            labels.add(lab.lower())
            nav.append((lab, href))
    data = {"site": root_final, "pages": pages, "nav": nav, "tech": dict(tech_hits), "functions": dict(func_hits),
            "external_hosts": hosts.most_common(25), "social": sorted(socials), "emails": sorted(emails),
            "phones": sorted(phones), "sitemap_count": len(from_sitemap)}
    (out / "site.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))

    ok = [p for p in pages if p.get("status") == 200]
    md = [f"# Site map · {domain(root_final)}", "",
          f"- Pages in sitemap: {len(from_sitemap) or 'none'} · crawled: {len(ok)} (max {a.max})",
          f"- Built with: {', '.join(k for k, _ in tech_hits.most_common()) or 'unknown'}"
          + (f" · generator: {ok[0].get('generator')}" if ok and ok[0].get("generator") else ""),
          f"- Subdomains / external hosts: {', '.join(h for h, _ in hosts.most_common(10)) or 'none'}", ""]
    md += ["## Main menu", ""] + [f"- {lab} → {href}" for lab, href in nav[:40]] + [""]
    md += ["## Function inventory (pages where it appears)", "", "| Function | Pages | Example |", "|---|---|---|"]
    for label in FUNCTIONS:
        hits = func_hits.get(label, [])
        if hits:
            md.append(f"| {label} | {len(hits)} | {hits[0]} |")
    md += ["", "_Signals come from page HTML. Open the example page and confirm before you list a function._", ""]
    forms = [(p["url"], f) for p in ok for f in p.get("forms", []) if f["fields"]]
    if forms:
        md += ["## Forms", "", "| Page | Fields |", "|---|---|"]
        for u, f in forms[:30]:
            md.append(f"| {u} | {', '.join(dict.fromkeys(f['fields']))[:160]} |")
        md.append("")
    broken = [p for p in pages if p.get("status") != 200]
    if broken:
        md += ["## Broken or unreachable pages", ""] + [f"- {p['url']} (HTTP {p.get('status')})" for p in broken] + [""]
    md += ["## Contact & social", "", f"- Emails: {', '.join(sorted(emails)) or '—'}", f"- Phones: {', '.join(sorted(phones)) or '—'}",
           f"- Social: {', '.join(sorted(socials)) or '—'}", "", "## Pages", ""]
    for p in ok:
        h1 = next((t for tag, t in p.get("headings", []) if tag == "h1"), "")
        emb = Counter(i["type"] for i in p.get("iframes", []))
        extra = (" · " + ", ".join(f"{v}× {k}" for k, v in emb.items())) if emb else ""
        md.append(f"- **{p.get('title') or '(no title)'}** — {p['url']}" + (f" · H1: {h1}" if h1 else "") + extra)
    (out / "site.md").write_text("\n".join(md) + "\n")
    print(f"✓ {out}/site.md  ({len(ok)} pages, {len(func_hits)} function types)")


if __name__ == "__main__":
    main()
