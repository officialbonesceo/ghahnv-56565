#!/usr/bin/env python3
"""Fetch/cache photoreal classroom stills with empty boards (Pollinations)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "data" / "environments.json"


def main() -> None:
    if not CFG.exists():
        print("no environments.json", file=sys.stderr)
        return
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    envs = cfg.get("image_environments") or []
    if not envs:
        print("no image_environments", file=sys.stderr)
        return

    for env in envs:
        rel = env.get("file") or ""
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 8000:
            print("REUSE", dest, dest.stat().st_size)
            continue
        prompt = env.get("prompt") or (
            "photorealistic empty classroom front view blank chalkboard vertical 9:16 no people no text"
        )
        # 1080x1920 preferred for Shorts
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt)}"
            f"?width=1080&height=1920&nologo=true&enhance=true"
        )
        print("FETCH", env.get("id"), file=sys.stderr)
        try:
            r = requests.get(url, timeout=150)
            r.raise_for_status()
            if len(r.content) < 4000:
                raise RuntimeError(f"tiny image {len(r.content)}")
            dest.write_bytes(r.content)
            print("SAVED", dest, len(r.content))
        except Exception as e:
            print("classroom image fail", env.get("id"), e, file=sys.stderr)
            # keep going — procedural rooms still work

    ready = sum(
        1
        for e in envs
        if (ROOT / e.get("file", "")).exists()
        and (ROOT / e.get("file", "")).stat().st_size > 8000
    )
    print("CLASSROOMS_READY", ready, "/", len(envs))


if __name__ == "__main__":
    main()
