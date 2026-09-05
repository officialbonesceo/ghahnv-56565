#!/usr/bin/env python3
"""Phi-2 / GGUF child process."""
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
    # Phi-2 style instruct
    prompt = f"""Instruct: You are Mike, a TikTok science tutor. Write 110 spoken words for teens about {title}. Use only these facts. Complete sentences. No markdown. Greet as Mike, three facts, one example, end with follow mike.the.tutor.
Facts: {ctx}
Output:"""
    out = llm(prompt, max_tokens=260, temperature=0.4, stop=["Instruct:", "Facts:"])
    text = out["choices"][0]["text"].strip()
    out_path.write_text(json.dumps({"intro": "", "body": text}), encoding="utf-8")


if __name__ == "__main__":
    main()
