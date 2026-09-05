#!/usr/bin/env python3
"""Child process: TinyLlama generate intro+body. Exit non-zero on failure."""
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
        n_ctx=1024,
        n_threads=2,
        verbose=False,
    )
    title = inp.get("title") or "science"
    ctx = inp.get("extract") or ""
    prompt = f"""### System:
You write short spoken lines for Mezi, a friendly science explainer for teens.
Only output the spoken words. No labels.

### User:
Topic: {title}
Facts: {ctx}

Write two parts:
INTRO (25-40 words): point to a board and name the topic simply.
BODY (50-80 words): explain simply with 2 facts and a friendly close.

### Assistant:
INTRO:
"""
    out1 = llm(prompt, max_tokens=80, temperature=0.7, stop=["BODY:", "###", "Topic:"])
    intro = out1["choices"][0]["text"].strip()
    prompt2 = prompt + intro + "\nBODY:\n"
    out2 = llm(prompt2, max_tokens=120, temperature=0.7, stop=["###", "INTRO:", "Topic:"])
    body = out2["choices"][0]["text"].strip()
    out_path.write_text(json.dumps({"intro": intro, "body": body}), encoding="utf-8")


if __name__ == "__main__":
    main()
