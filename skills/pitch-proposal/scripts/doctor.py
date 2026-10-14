#!/usr/bin/env python3
"""Check this machine can run pitch-proposal.

Usage: python3 doctor.py [--profile <dir>]
"""
import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import find_chrome, find_profile, load_profile  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile")
    a = ap.parse_args()
    ok = True
    print(f"python   {sys.version.split()[0]}", "✓" if sys.version_info >= (3, 9) else "✗ need 3.9+")
    ok &= sys.version_info >= (3, 9)
    for mod, why in (("PIL", "pillow: images, previews"), ("yaml", "pyyaml: profiles"), ("pypdfium2", "pypdfium2: PDF previews and checks")):
        try:
            importlib.import_module(mod)
            print(f"{mod:<9}✓")
        except ImportError:
            alt = mod == "pypdfium2"
            print(f"{mod:<9}{'!' if alt else '✗'} missing ({why}){' — PyMuPDF or poppler also work' if alt else ''}")
            ok &= alt
    c = find_chrome()
    print(f"chrome   {'✓ ' + c if c else '✗ not found (install Google Chrome or set PROPOSAL_CHROME)'}")
    ok &= bool(c)
    try:
        p = load_profile(find_profile(a.profile))
        co = p["company"]
        logo = any((p["dir"] / (co.get("brand") or {}).get(k, "")).is_file() for k in ("logo", "logo_on_dark") if (co.get("brand") or {}).get(k))
        print(f"profile  ✓ {co.get('name')} ({p['dir']}){'' if logo else '  ! no logo file found'}")
    except SystemExit as e:
        print(f"profile  ! {str(e).splitlines()[0]}")
    print("ready" if ok else "fix the ✗ items above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
