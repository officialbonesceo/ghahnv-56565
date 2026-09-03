#!/usr/bin/env python3
"""Expand a short prompt into a spoken script using TinyLlama (GGUF via llama-cpp)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MODEL_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"


def download_model(cache_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=str(cache_dir),
        local_dir_use_symlinks=False,
    )
    return Path(path)


def expand(text: str, model_path: Path, max_tokens: int = 120) -> str:
    from llama_cpp import Llama

    llm = Llama(
        model_path=str(model_path),
        n_ctx=1024,
        n_threads=max(1, (os.cpu_count() or 2) - 1),
        verbose=False,
    )
    prompt = (
        "<|system|>\n"
        "You write short spoken lines for a narrator video. "
        "Reply with only the spoken words, 1-3 sentences, no quotes or stage directions.\n"
        "<|user|>\n"
        f"Turn this into a clear spoken script:\n{text}\n"
        "<|assistant|>\n"
    )
    out = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        stop=["<|user|>", "<|system|>", "\n\n"],
    )
    result = out["choices"][0]["text"].strip().strip('"').strip()
    return result or text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--model-dir", default="models")
    p.add_argument("--out", default="script.txt")
    p.add_argument("--skip-llm", action="store_true")
    args = p.parse_args()

    text = args.text.strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    if args.skip_llm:
        expanded = text
        print("LLM skipped")
    else:
        try:
            model_path = download_model(Path(args.model_dir))
            print(f"Model: {model_path}")
            expanded = expand(text, model_path)
            print(f"Expanded ({len(expanded)} chars)")
        except Exception as e:
            print(f"WARNING: LLM failed ({e}); using original text", file=sys.stderr)
            expanded = text

    Path(args.out).write_text(expanded + "\n", encoding="utf-8")
    print(expanded)


if __name__ == "__main__":
    main()
