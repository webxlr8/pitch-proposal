#!/usr/bin/env python3
"""Screenshot web pages (desktop or mobile) and crop evidence from them.

Usage:
    python3 screenshots.py shoot <url> <out.png> [--mobile] [--height 1600] [--wait 8000]
    python3 screenshots.py shoot-list urls.txt <out-dir> [--mobile]     # lines: "<name> <url>"
    python3 screenshots.py crop <in.png> <out.jpg> <x0,y0,x1,y1>        # pixel box from the screenshot
    python3 screenshots.py sheet <dir> <out.png>                        # contact sheet to pick crops

Uses your installed Chrome in headless mode, one page at a time. Desktop is 1440 px wide;
--mobile is 390 px wide with an iPhone user agent. Screenshots are evidence: crop, never edit them.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MOBILE_UA, UA, chrome  # noqa: E402


def shoot(url, out, mobile=False, height=None, wait=8000):
    w = 390 if mobile else 1440
    h = height or (2400 if mobile else 1600)
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    chrome([f"--user-agent={MOBILE_UA if mobile else UA}", f"--virtual-time-budget={wait}",
            f"--window-size={w},{h}", f"--screenshot={out}", url], timeout=120)
    if not out.exists():
        print(f"  ! no screenshot for {url}", file=sys.stderr)
        return False
    print(f"✓ {out}")
    return True


def crop(src, dst, box):
    from PIL import Image
    x0, y0, x1, y1 = [int(v) for v in box.split(",")]
    Image.open(src).convert("RGB").crop((x0, y0, x1, y1)).save(dst, quality=86)
    print(f"✓ {dst}")


def sheet(folder, out):
    from PIL import Image, ImageDraw
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    tw, th = 360, 400
    cols = 4
    rows = (len(files) + cols - 1) // cols
    s = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 30) + 12), (40, 40, 40))
    d = ImageDraw.Draw(s)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((tw, th))
        x, y = 12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 30)
        s.paste(im, (x, y))
        d.text((x, y + th + 6), f.name, fill=(230, 230, 230))
    s.save(out)
    print(f"✓ {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("shoot"); a1.add_argument("url"); a1.add_argument("out")
    a1.add_argument("--mobile", action="store_true"); a1.add_argument("--height", type=int); a1.add_argument("--wait", type=int, default=8000)
    a2 = sub.add_parser("shoot-list"); a2.add_argument("list"); a2.add_argument("outdir"); a2.add_argument("--mobile", action="store_true")
    a3 = sub.add_parser("crop"); a3.add_argument("src"); a3.add_argument("dst"); a3.add_argument("box")
    a4 = sub.add_parser("sheet"); a4.add_argument("dir"); a4.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "shoot":
        shoot(a.url, a.out, a.mobile, a.height, a.wait)
    elif a.cmd == "shoot-list":
        for line in Path(a.list).read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                name, url = line.split(None, 1)
                shoot(url.strip(), Path(a.outdir) / f"{name}.png", a.mobile)
    elif a.cmd == "crop":
        crop(a.src, a.dst, a.box)
    else:
        sheet(a.dir, a.out)


if __name__ == "__main__":
    main()
