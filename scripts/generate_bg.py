#!/usr/bin/env python3
"""Generate topic background via Pollinations AI; cache and reuse."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import quote

import requests

PROMPTS = {
    "space": "cinematic deep space nebula stars planet, vertical poster, soft lighting, no text no watermark",
    "ocean": "calm ocean horizon turquoise water sky, vertical poster, soft cinematic light, no text",
    "science": "soft science lab glow blue amber light abstract, vertical poster, no text no watermark",
    "tech": "dark blue digital grid soft neon, vertical poster, cinematic, no text",
    "nature": "mountain range sunset soft clouds, vertical poster, painted look, no text",
    "studio": "warm minimal studio wall soft window light, vertical poster, no text",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bg", default="science")
    p.add_argument("--out-dir", default="assets/bg")
    p.add_argument("--width", type=int, default=864)
    p.add_argument("--height", type=int, default=1536)
    args = p.parse_args()

    tag = (args.bg or "science").lower().strip()
    if tag not in PROMPTS:
        tag = "science"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{tag}.jpg"

    if out_path.exists() and out_path.stat().st_size > 5000:
        print("REUSE", out_path, out_path.stat().st_size)
        Path("bg_path.txt").write_text(str(out_path), encoding="utf-8")
        return

    prompt = PROMPTS[tag]
    # pollinations free image endpoint
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width={args.width}&height={args.height}&nologo=true&enhance=true"
    )
    print("FETCH", tag, file=sys.stderr)
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        if len(r.content) < 2000:
            raise RuntimeError("tiny response")
        out_path.write_bytes(r.content)
        print("SAVED", out_path, len(r.content))
    except Exception as e:
        print("pollinations failed:", e, file=sys.stderr)
        # leave missing — renderer falls back to drawn bg
        if out_path.exists():
            out_path.unlink()
        Path("bg_path.txt").write_text("", encoding="utf-8")
        sys.exit(0)

    Path("bg_path.txt").write_text(str(out_path), encoding="utf-8")


if __name__ == "__main__":
    main()
