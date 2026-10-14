"""Shared helpers for pitch-proposal scripts: profile loading, HTTP fetch, Chrome lookup."""
import colorsys
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


# ---------------------------------------------------------------- HTTP
def fetch(url, timeout=30, binary=False):
    """GET with browser-like headers (many hosts reject bare clients). Returns (status, final_url, body)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            if binary:
                return r.status, r.geturl(), data
            charset = r.headers.get_content_charset() or "utf-8"
            return r.status, r.geturl(), data.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, url, b"" if binary else ""
    except Exception as e:  # network errors, timeouts
        print(f"  ! fetch failed {url}: {e}", file=sys.stderr)
        return 0, url, b"" if binary else ""


def same_site(a, b):
    ha, hb = urllib.parse.urlparse(a).netloc.lower(), urllib.parse.urlparse(b).netloc.lower()
    strip = lambda h: h[4:] if h.startswith("www.") else h
    return strip(ha) == strip(hb)


def domain(url):
    h = urllib.parse.urlparse(url if "//" in url else "https://" + url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "client"


# ---------------------------------------------------------------- browser
def find_chrome():
    """Chrome/Chromium executable, or None. Override with PROPOSAL_CHROME."""
    env = os.environ.get("PROPOSAL_CHROME")
    if env and Path(env).exists():
        return env
    cands = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def chrome(args, timeout=180):
    """Run headless Chrome once. stdin is closed: Chrome can hang when it inherits a pipe."""
    exe = find_chrome()
    if not exe:
        raise SystemExit("Chrome/Chromium not found. Install Google Chrome or set PROPOSAL_CHROME.")
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           "--no-default-browser-check", *args]
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------- profile
def _yaml(path):
    if not path.exists():
        return {}
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    return yaml.safe_load(path.read_text()) or {}


def find_profile(explicit=None):
    for c in (explicit, os.environ.get("PITCH_PROFILE"), "pitch-profile"):
        if c and (Path(c) / "company.yaml").exists():
            return Path(c).resolve()
    raise SystemExit("No company profile found. Pass --profile <dir>, set PITCH_PROFILE, or create one with:\n"
                     "  python3 scripts/profile_from_site.py https://your-company.com --out pitch-profile")


def load_profile(path):
    path = Path(path)
    company = _yaml(path / "company.yaml")
    proof = _yaml(path / "proof.yaml")
    theme = {}
    if (path / "theme.json").exists():
        theme = json.loads((path / "theme.json").read_text())
    return {"dir": path, "company": company, "proof": proof, "theme": theme}


# ---------------------------------------------------------------- colour
def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    r, g, b = [c / 255 for c in hex_rgb(h)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def saturation(h):
    r, g, b = [c / 255 for c in hex_rgb(h)]
    return colorsys.rgb_to_hls(r, g, b)[2]


def shift(h, light=0.0):
    r, g, b = [c / 255 for c in hex_rgb(h)]
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = max(0, min(1, ll + light))
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))
