#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[2])
    from llama_cpp import Llama

    llm = Llama(model_path=inp["model"], n_ctx=1024, n_threads=2, verbose=False)
    title = inp.get("title") or "science"
    ctx = inp.get("extract") or ""
    prompt = f"""### Instruction:
Write spoken TikTok lines for teens. No math symbols. No coordinates. No labels like INTRO or BODY in the output.
Use only simple English sentences.

Topic: {title}
Context: {ctx}

First write 30 words introducing the topic for a classroom board.
Then write 70 words explaining two simple facts and a friendly ending.
### Response:
"""
    out = llm(prompt, max_tokens=200, temperature=0.5, stop=["###", "Topic:", "Context:"])
    text = out["choices"][0]["text"].strip()
    # split roughly in half for intro/body
    words = text.split()
    mid = max(20, min(40, len(words) // 3))
    intro = " ".join(words[:mid])
    body = " ".join(words[mid:]) if len(words) > mid else text
    out_path.write_text(json.dumps({"intro": intro, "body": body}), encoding="utf-8")


if __name__ == "__main__":
    main()
