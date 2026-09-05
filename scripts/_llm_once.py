#!/usr/bin/env python3
"""Child process GGUF inference — isolate SIGILL from the main job."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[2])
    from llama_cpp import Llama

    llm = Llama(
        model_path=inp["model"],
        n_ctx=2048,
        n_threads=2,
        verbose=False,
    )
    title = inp.get("title") or "science"
    ctx = inp.get("extract") or ""
    prompt = f"""<start_of_turn>user
Write spoken classroom TikTok lines for teens. Simple English. No math symbols. No labels.
Topic: {title}
Facts: {ctx}
Write about 30 words introducing the topic at a board, then about 80 words with two simple facts and a friendly ending.
<end_of_turn>
<start_of_turn>model
"""
    out = llm(prompt, max_tokens=220, temperature=0.55, stop=["<end_of_turn>", "<start_of_turn>"])
    text = out["choices"][0]["text"].strip()
    words = text.split()
    mid = max(22, min(42, len(words) // 3))
    intro = " ".join(words[:mid])
    body = " ".join(words[mid:]) if len(words) > mid else text
    out_path.write_text(json.dumps({"intro": intro, "body": body}), encoding="utf-8")


if __name__ == "__main__":
    main()
