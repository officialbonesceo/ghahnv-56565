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
You are Mike, a TikTok science tutor. Write 140 spoken words for teens.
Complete sentences only. No markdown. No parentheses. No mid-sentence starts.
Topic: {title}
Facts: {ctx}
Say hello as Mike, explain three facts clearly, end with follow mike.the.tutor.
<end_of_turn>
<start_of_turn>model
"""
    out = llm(prompt, max_tokens=300, temperature=0.45, stop=["<end_of_turn>", "<start_of_turn>"])
    text = out["choices"][0]["text"].strip()
    out_path.write_text(json.dumps({"intro": "", "body": text}), encoding="utf-8")


if __name__ == "__main__":
    main()
