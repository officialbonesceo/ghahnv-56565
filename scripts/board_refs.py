#!/usr/bin/env python3
"""Fetch 2 small topic reference images for the classroom board (Pollinations)."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import requests

OUT = Path("assets/board")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    title = "science"
    if Path("title_short.txt").exists():
        title = Path("title_short.txt").read_text(encoding="utf-8").strip() or title
    elif Path("topic.json").exists():
        title = json.loads(Path("topic.json").read_text()).get("title") or title

    prompts = [
        f"simple educational illustration of {title}, clean diagram style, no text, no watermark",
        f"classroom friendly icon set related to {title}, flat design, no text",
    ]
    paths = []
    for i, prompt in enumerate(prompts):
        dest = OUT / f"ref{i}.jpg"
        if dest.exists() and dest.stat().st_size > 3000:
            paths.append(str(dest))
            continue
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt)}"
            f"?width=512&height=384&nologo=true"
        )
        try:
            r = requests.get(url, timeout=90)
            r.raise_for_status()
            if len(r.content) > 2000:
                dest.write_bytes(r.content)
                paths.append(str(dest))
                print("saved", dest, len(r.content))
        except Exception as e:
            print("ref fail", i, e)
    Path("board_refs.txt").write_text("\n".join(paths), encoding="utf-8")


if __name__ == "__main__":
    main()
