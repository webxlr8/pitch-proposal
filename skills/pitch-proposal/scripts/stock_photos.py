#!/usr/bin/env python3
"""Find and download free stock photos (Unsplash, Pexels) and record credits.

Usage:
    python3 stock_photos.py search "group meditation class" --out clients/<slug>/images/_candidates [--n 12]
    python3 stock_photos.py get <unsplash-url | unsplash-id | images.unsplash.com/... | pexels-url> \
                               --out clients/<slug>/images --name img-1 [--width 1600]

search needs UNSPLASH_ACCESS_KEY or PEXELS_API_KEY (free developer keys). Without a key, find photos
with a web search or the browser (unsplash.com/s/photos/<query>, filter "Free"), then pass the photo
page URLs to `get`. Unsplash+ (paid) photos are refused. Every download is written to credits.json.

Licences: Unsplash License and Pexels License allow free commercial use without attribution.
We still keep credits, and the proposal footer can say "Photography: Unsplash".
Never use stock photos to pretend to show the client's own business, staff or premises.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch  # noqa: E402


def api_json(url, headers):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "pitch-proposal", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def unsplash_id(ref):
    m = re.search(r"unsplash\.com/(?:photos|\w+/photos)/(?:[a-z0-9-]*-)?([A-Za-z0-9_-]{11})(?:[/?#]|$)", ref)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", ref):
        return ref
    return None


def resolve(ref, width):
    """-> (image_url, credit dict)"""
    if "images.unsplash.com" in ref:
        base = ref.split("?")[0]
        return f"{base}?w={width}&q=80&fm=jpg&fit=max", {"source": "Unsplash", "url": base}
    uid = unsplash_id(ref)
    if uid:
        key = os.environ.get("UNSPLASH_ACCESS_KEY")
        url = f"https://api.unsplash.com/photos/{uid}" if key else f"https://unsplash.com/napi/photos/{uid}"
        try:
            j = api_json(url, {"Authorization": f"Client-ID {key}"} if key else {"Accept": "application/json"})
        except Exception as e:
            raise SystemExit(f"Could not look up Unsplash photo {uid} ({e}). Open the photo page in a browser, "
                             "copy the image address (images.unsplash.com/...) and pass that instead.")
        if j.get("premium") or j.get("plus"):
            raise SystemExit(f"{uid} is an Unsplash+ (paid) photo. Pick a free one.")
        raw = j["urls"]["raw"].split("?")[0]
        return f"{raw}?w={width}&q=80&fm=jpg&fit=max", {
            "source": "Unsplash", "id": uid, "page": f"https://unsplash.com/photos/{uid}",
            "photographer": j.get("user", {}).get("name"), "alt": j.get("alt_description")}
    m = re.search(r"pexels\.com/photo/(?:[a-z0-9-]*-)?(\d+)", ref)
    if m:
        key = os.environ.get("PEXELS_API_KEY")
        if not key:
            raise SystemExit("Pexels photo pages need PEXELS_API_KEY, or pass the direct images.pexels.com URL.")
        j = api_json(f"https://api.pexels.com/v1/photos/{m.group(1)}", {"Authorization": key})
        return j["src"]["large2x"], {"source": "Pexels", "id": m.group(1), "page": j.get("url"), "photographer": j.get("photographer")}
    if "images.pexels.com" in ref:
        return ref, {"source": "Pexels", "url": ref.split("?")[0]}
    raise SystemExit(f"Not an Unsplash or Pexels reference: {ref}")


def get(ref, out, name, width):
    img_url, credit = resolve(ref, width)
    st, _, data = fetch(img_url, binary=True)
    if st != 200 or not data:
        raise SystemExit(f"Download failed (HTTP {st}) for {img_url}")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{name}.jpg"
    dst.write_bytes(data)
    cred_file = out / "credits.json"
    credits = json.loads(cred_file.read_text()) if cred_file.exists() else {}
    credits[dst.name] = credit
    cred_file.write_text(json.dumps(credits, indent=1, ensure_ascii=False))
    print(f"✓ {dst}  ({credit.get('source')}{' · ' + credit['photographer'] if credit.get('photographer') else ''})")


def search(query, out, n, orientation):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    if os.environ.get("UNSPLASH_ACCESS_KEY"):
        q = urllib.parse.urlencode({"query": query, "per_page": n, "orientation": orientation, "content_filter": "high"})
        j = api_json(f"https://api.unsplash.com/search/photos?{q}", {"Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}"})
        results = [(f"https://unsplash.com/photos/{r['id']}", r["urls"]["small"], r.get("alt_description") or "") for r in j["results"]]
    elif os.environ.get("PEXELS_API_KEY"):
        q = urllib.parse.urlencode({"query": query, "per_page": n, "orientation": orientation})
        j = api_json(f"https://api.pexels.com/v1/search?{q}", {"Authorization": os.environ["PEXELS_API_KEY"]})
        results = [(p["url"], p["src"]["medium"], p.get("alt") or "") for p in j["photos"]]
    else:
        raise SystemExit("search needs UNSPLASH_ACCESS_KEY or PEXELS_API_KEY.\n"
                         f"Without a key: open https://unsplash.com/s/photos/{urllib.parse.quote(query.replace(' ', '-'))}?license=free "
                         "in a browser, pick photos, and run `get` with their page URLs.")
    from PIL import Image, ImageDraw
    import io
    thumbs, lines = [], []
    for i, (page, thumb, alt) in enumerate(results, 1):
        st, _, data = fetch(thumb, binary=True)
        if st == 200:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((320, 220))
            thumbs.append(im)
            lines.append(f"{i:>2}  {page}  {alt[:70]}")
    sheet = Image.new("RGB", (4 * 332 + 12, ((len(thumbs) + 3) // 4) * 250 + 12), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(thumbs):
        x, y = 12 + (i % 4) * 332, 12 + (i // 4) * 250
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 6), str(i + 1), fill=(255, 255, 0))
    sheet.save(out / "sheet.png")
    (out / "candidates.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"✓ {out}/sheet.png — look at it, then: stock_photos.py get <page-url> --out <images> --name <slot>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=12); s.add_argument("--orientation", default="landscape")
    g = sub.add_parser("get"); g.add_argument("ref"); g.add_argument("--out", required=True)
    g.add_argument("--name", required=True); g.add_argument("--width", type=int, default=1600)
    a = ap.parse_args()
    if a.cmd == "search":
        search(a.query, a.out, a.n, a.orientation)
    else:
        get(a.ref, a.out, a.name, a.width)


if __name__ == "__main__":
    main()
