#!/usr/bin/env python3
"""Topic JSON -> clean spoken TikTok script for MEZI.

On GitHub Actions, llama-cpp often crashes (Illegal instruction).
Default path: Wikipedia template (reliable). Optional --model only if it loads.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def clean_spoken(text: str) -> str:
    t = text.strip().strip('"').strip("'")
    bad = [
        r"\(You write.*?\)",
        r"You write the TikTok script.*",
        r"Please note that.*",
        r"The provided text is not.*",
        r"Please use the provided text.*",
        r"Write only the spoken script.*",
        r"Rules:.*",
    ]
    for p in bad:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"Hook:\s*", "", t, flags=re.I)
    t = re.sub(r"\d?\s*Facts?:\s*", " ", t, flags=re.I)
    t = re.sub(r"Fun Closing Line:\s*", " ", t, flags=re.I)
    t = re.sub(r"\d+\.\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    low = t.lower()
    if any(x in low for x in ("you write", "tiktok script for", "please note", "rules:")):
        return ""
    words = t.split()
    if len(words) < 20:
        return ""
    if len(words) > 100:
        t = " ".join(words[:95])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def template_script(topic: dict) -> dict:
    title = topic.get("title") or "this"
    extract = (topic.get("extract") or "").strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", extract)
        if len(s.strip()) > 25
    ][:2]
    if not sentences:
        sentences = [extract[:180] or f"{title} is a fascinating idea worth knowing."]
    fact1 = sentences[0]
    fact2 = sentences[1] if len(sentences) > 1 else "Scientists still study it today."
    if len(fact1) > 120:
        fact1 = fact1[:117] + "..."
    if len(fact2) > 120:
        fact2 = fact2[:117] + "..."
    script = (
        f"Hey! Ever heard of {title}? "
        f"{fact1} "
        f"{fact2} "
        f"Wild, right? Follow Mezi for more simple explainers!"
    )
    script = re.sub(r"\s+", " ", script).strip()
    return {
        "title": title,
        "script": script,
        "bg": topic.get("bg") or "studio",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def try_qwen(model_path: Path, topic: dict) -> dict | None:
    """Optional. May SIGILL on some CI CPUs — caller should prefer template."""
    if not model_path.exists():
        return None
    try:
        from llama_cpp import Llama
    except Exception as e:
        print("llama_cpp not available:", e, file=sys.stderr)
        return None
    title = topic.get("title") or "science"
    ctx = (topic.get("extract") or "")[:350]
    prompt = (
        "Write only spoken TikTok words for Mezi. 55-80 words. "
        "No labels. Simple English.\n"
        f"Topic: {title}\nContext: {ctx}\nScript:"
    )
    try:
        llm = Llama(model_path=str(model_path), n_ctx=1024, n_threads=1, verbose=False)
        out = llm(prompt, max_tokens=140, temperature=0.6, stop=["Topic:", "Context:", "\n\n"])
        raw = out["choices"][0]["text"].strip()
        spoken = clean_spoken(raw)
        if not spoken:
            return None
        return {
            "title": title,
            "script": spoken,
            "bg": topic.get("bg") or "studio",
            "source": topic.get("url") or "",
            "engine": "qwen2-0.5b",
        }
    except Exception as e:
        print("qwen failed:", e, file=sys.stderr)
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--out", default="script_job.json")
    p.add_argument(
        "--try-llm",
        action="store_true",
        help="Attempt GGUF model (may crash on some CPUs). Default: template only.",
    )
    args = p.parse_args()

    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = None
    if args.try_llm and args.model:
        result = try_qwen(Path(args.model), topic)
    if result is None:
        result = template_script(topic)
        print("engine=template", file=sys.stderr)

    result["script"] = clean_spoken(result["script"]) or template_script(topic)["script"]
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("bg.txt").write_text(result.get("bg") or "studio", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
