#!/usr/bin/env python3
"""Board reference images — clear educational style, not abstract mush."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import requests

OUT = Path("assets/board")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    title = "science classroom"
    if Path("title_short.txt").exists():
        title = Path("title_short.txt").read_text(encoding="utf-8").strip() or title
    elif Path("topic.json").exists():
        title = json.loads(Path("topic.json").read_text()).get("title") or title

    prompts = [
        f"clear simple educational diagram explaining {title}, textbook illustration, white background, high contrast, no text no watermark",
        f"friendly cartoon classroom poster about {title}, simple icons, bright colors, no text no watermark",
    ]
    paths = []
    for i, prompt in enumerate(prompts):
        dest = OUT / f"ref{i}.jpg"
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt)}"
            f"?width=640&height=400&nologo=true&enhance=true"
        )
        try:
            r = requests.get(url, timeout=100)
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
