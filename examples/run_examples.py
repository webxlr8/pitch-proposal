#!/usr/bin/env python3
"""Rebuild the two example proposals end to end.

    python3 examples/run_examples.py [--only wellness|kestrel]

wellness  WebXLR8 (dark) · new platform for a wellness organisation · build preset.
          Fetches its free Unsplash photos listed in wellness-platform/images.txt.
kestrel   Northwind Studio (fictional, light) · refresh of the fictional demo site in demo-site/.
          Serves the demo site locally, crawls it, takes screenshots, crops the evidence.
Both refresh assets/ from the skill templates, then run build.py (render, previews, checks).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

EX = Path(__file__).resolve().parent
SK = EX.parent / "skills" / "pitch-proposal"
S = SK / "scripts"
PY = sys.executable


def run(*args, cwd=EX):
    print("$", " ".join(str(a).replace(str(EX.parent) + "/", "") for a in args), flush=True)
    subprocess.run([PY, *map(str, args)], cwd=cwd, check=True)


def refresh_assets(d):
    for f in ("base.css", "ui.css"):
        shutil.copy(SK / "templates" / f, d / "assets" / f)


def wellness():
    d = EX / "wellness-platform"
    refresh_assets(d)
    for line in (d / "images.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, url = line.split()
            if not (d / "images" / f"{name}.jpg").exists():
                run(S / "stock_photos.py", "get", url, "--out", d / "images", "--name", name, "--width", "1400")
    run(S / "build.py", d)


def kestrel():
    d = EX / "kestrel-refresh"
    refresh_assets(d)
    sys.path.insert(0, str(EX / "demo-site"))
    import serve  # noqa: E402
    srv = serve.start(background=True)
    try:
        url = f"http://127.0.0.1:{serve.PORT}/"
        run(S / "crawl_site.py", url, "--out", d / "site", "--max", "10", "--delay", "0")
        shots = d / "site" / "shots"
        run(S / "screenshots.py", "shoot", url, shots / "home.png", "--height", "2100")
        run(S / "screenshots.py", "shoot", url, shots / "home-mobile.png", "--mobile")
        run(S / "screenshots.py", "shoot", url + "services.html", shots / "services.png", "--height", "900")
        run(S / "screenshots.py", "shoot", url + "contact.html", shots / "contact.png", "--height", "900")
        crops = [("home", "current-site", "0,0,1440,900"), ("home-mobile", "shot-1", "0,560,390,1400"),
                 ("home", "shot-2", "0,150,1440,700"), ("home", "shot-3", "0,690,1440,830"),
                 ("home", "shot-4", "200,1520,1240,1810"), ("services", "shot-5", "300,40,1140,330"),
                 ("contact", "shot-6", "280,60,1240,420")]
        (d / "images").mkdir(exist_ok=True)
        for src, dst, box in crops:
            run(S / "screenshots.py", "crop", shots / f"{src}.png", d / "images" / f"{dst}.jpg", box)
    finally:
        srv.shutdown()
    run(S / "build.py", d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["wellness", "kestrel"])
    a = ap.parse_args()
    if a.only in (None, "kestrel"):
        kestrel()
    if a.only in (None, "wellness"):
        wellness()
