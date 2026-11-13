#!/usr/bin/env python3
"""Assemble assets/mike/Mike.glb from committed base64 chunks."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "assets" / "mike" / "b64"
OUT = ROOT / "assets" / "mike" / "Mike.glb"
MANIFEST = PARTS_DIR / "manifest.txt"


def main() -> None:
    if OUT.exists() and OUT.stat().st_size > 1_000_000:
        print("REUSE", OUT, OUT.stat().st_size)
        return
    if not MANIFEST.exists():
        print("NO_MANIFEST", MANIFEST, file=sys.stderr)
        sys.exit(1)
    names = [ln.strip() for ln in MANIFEST.read_text(encoding="ascii").splitlines() if ln.strip()]
    buf = []
    for name in names:
        p = PARTS_DIR / name
        if not p.exists():
            print("MISSING_PART", p, file=sys.stderr)
            sys.exit(1)
        buf.append(p.read_text(encoding="ascii").strip())
    data = base64.b64decode("".join(buf))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    if data[:4] != b"glTF":
        print("BAD_MAGIC", data[:4], file=sys.stderr)
        sys.exit(1)
    print("OK", OUT, len(data))


if __name__ == "__main__":
    main()
