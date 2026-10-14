#!/usr/bin/env python3
"""Serve the FICTIONAL demo prospect site on http://127.0.0.1:8765 (deliberately flawed for the demo audit).
Generates its heavy hero image and oversized logo on first run (kept out of git)."""
import functools
import http.server
import os
import random
import socketserver
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("DEMO_PORT", 8765))


def make_assets():
    from PIL import Image, ImageDraw, ImageFont
    hero = os.path.join(HERE, "hero.png")
    if not os.path.exists(hero):  # the night photo blown up to an uncompressed 3200x2133 PNG ≈ 10+ MB: "unoptimised image"
        im = Image.open(os.path.join(HERE, "night.jpg")).convert("RGB").resize((3200, 2133), Image.BICUBIC)
        rnd = random.Random(42)
        px = im.load()
        for _ in range(400000):  # sensor-like noise defeats PNG compression, like a real unoptimised export
            x, y = rnd.randrange(3200), rnd.randrange(2133)
            r, g, b_ = px[x, y]
            n = rnd.randint(-12, 12)
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b_ + n)))
        im.save(hero, optimize=False, compress_level=1)
    logo = os.path.join(HERE, "logo.png")
    if not os.path.exists(logo):
        im = Image.new("RGB", (2400, 420), "white")
        d = ImageDraw.Draw(im)
        d.polygon([(60, 360), (210, 60), (360, 360)], fill=(181, 84, 60))
        try:
            f = ImageFont.truetype("Georgia.ttf", 170)
        except Exception:  # noqa: BLE001
            f = ImageFont.load_default()
        d.text((420, 110), "KESTREL VALLEY", fill=(40, 40, 40), font=f)
        im.save(logo)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start(background=True):
    make_assets()
    handler = functools.partial(Quiet, directory=HERE)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), handler)
    if background:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv
    print(f"demo prospect site: http://127.0.0.1:{PORT}")
    srv.serve_forever()


if __name__ == "__main__":
    start(background=False) if "--background" not in sys.argv else start()
