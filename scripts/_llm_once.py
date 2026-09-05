#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[2])
    from llama_cpp import Llama

    llm = Llama(model_path=inp["model"], n_ctx=2048, n_threads=2, verbose=False)
    title = inp.get("title") or "science"
    ctx = inp.get("extract") or ""
    prompt = f"""<start_of_turn>user
Write a spoken classroom TikTok lesson for teens, about 130 words total.
Simple English only. No markdown. No stage directions like (on a whiteboard).
Topic: {title}
Facts: {ctx}
Start with a short welcome naming the topic, then three clear facts, then invite them back next time.
<end_of_turn>
<start_of_turn>model
"""
    out = llm(prompt, max_tokens=280, temperature=0.5, stop=["<end_of_turn>", "<start_of_turn>"])
    text = out["choices"][0]["text"].strip()
    words = text.split()
    mid = max(28, min(48, len(words) // 4))
    intro = " ".join(words[:mid])
    body = " ".join(words[mid:]) if len(words) > mid else text
    out_path.write_text(json.dumps({"intro": intro, "body": body}), encoding="utf-8")


if __name__ == "__main__":
    main()
