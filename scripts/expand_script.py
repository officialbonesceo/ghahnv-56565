#!/usr/bin/env python3
"""
Offline script expander — no HuggingFace token, no model download.
Turns a short prompt into 1–3 clear spoken sentences for TTS.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def expand(text: str) -> str:
    t = " ".join(text.split()).strip()
    if not t:
        return "Hello from Talking Clip Factory."

    # Already a full spoken line
    if len(t) > 40 and t[-1] in ".!?":
        return t

    # Light cleanup
    t = re.sub(r"\s+", " ", t)
    if t[-1] not in ".!?":
        t = t + "."

    # If very short, wrap into a natural spoken intro
    if len(t) < 50:
        return (
            f"Here is a quick message from Talking Clip Factory. {t} "
            f"Thanks for listening."
        )

    return t


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--out", default="script.txt")
    args = p.parse_args()

    text = args.text.strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    expanded = expand(text)
    Path(args.out).write_text(expanded + "\n", encoding="utf-8")
    print(expanded)


if __name__ == "__main__":
    main()
