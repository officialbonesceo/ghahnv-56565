#!/usr/bin/env python3
"""Topic JSON -> clean spoken TikTok script for MEZI."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def clean_spoken(text: str) -> str:
    """Strip model meta, labels, quotes — keep only words MEZI should say."""
    t = text.strip()
    # drop fenced / quoted wrappers
    t = re.sub(r"^```.*?```", "", t, flags=re.S)
    t = t.strip().strip('"').strip("'")

    # remove prompt echo / instruction leakage
    bad_patterns = [
        r"\(You write.*?\)",
        r"You write the TikTok script.*?\n",
        r"Rules:.*?(?=Hook:|What's|Hey|Did you)",
        r"Please note that.*",
        r"The provided text is not.*",
        r"Please use the provided text.*",
        r"original TikTok script is provided.*",
        r"Write only the spoken script.*",
        r"spoken version of the text.*",
    ]
    for p in bad_patterns:
        t = re.sub(p, " ", t, flags=re.I | re.S)

    # unwrap labeled sections into one spoken paragraph
    t = re.sub(r"Hook:\s*", "", t, flags=re.I)
    t = re.sub(r"\d?\s*Facts?:\s*", " ", t, flags=re.I)
    t = re.sub(r"Fun Closing Line:\s*", " ", t, flags=re.I)
    t = re.sub(r"Closing:\s*", " ", t, flags=re.I)
    t = re.sub(r"Script:\s*", " ", t, flags=re.I)
    t = re.sub(r"\d+\.\s*", "", t)  # numbered lists

    t = re.sub(r"[\"\']{2,}", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip(' "\'')

    # if still looks like instructions, reject
    low = t.lower()
    if any(
        x in low
        for x in (
            "you write",
            "tiktok script for",
            "please note",
            "provided text",
            "spoken version",
            "rules:",
        )
    ):
        return ""

    words = t.split()
    if len(words) < 20:
        return ""
    if len(words) > 100:
        t = " ".join(words[:95])
    # ensure ends with sentence punct
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

    # keep facts short for speech
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


def run_qwen(model_path: Path, topic: dict) -> dict | None:
    try:
        from llama_cpp import Llama
    except Exception as e:
        print("llama_cpp import failed", e, file=sys.stderr)
        return None
    if not model_path.exists():
        return None

    title = topic.get("title") or "science"
    ctx = (topic.get("extract") or "")[:350]

    # Few-shot style: model sees exact output format
    prompt = f"""<|im_start|>system
You are Mezi writing ONLY the words you will speak on TikTok. No labels. No Hook/Facts headers. No notes. 55-80 words. Simple teen English.<|im_end|>
<|im_start|>user
Topic: Rainbow
Context: A rainbow is caused by reflection, refraction and dispersion of light in water droplets.
Speak now.<|im_end|>
<|im_start|>assistant
Hey! Why do we see rainbows? Sunlight bends inside raindrops and splits into colors. Red bends least and violet bends most. That is why a rainbow is a full curve of color after rain. Follow Mezi for more quick science!<|im_end|>
<|im_start|>user
Topic: {title}
Context: {ctx}
Speak now.<|im_end|>
<|im_start|>assistant
"""

    try:
        llm = Llama(model_path=str(model_path), n_ctx=2048, n_threads=2, verbose=False)
        out = llm(
            prompt,
            max_tokens=160,
            temperature=0.6,
            stop=["<|im_end|>", "<|im_start|>", "Topic:", "Context:", "Speak now"],
        )
        raw = out["choices"][0]["text"].strip()
        print("RAW_MODEL:", raw[:300], file=sys.stderr)
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
        print("qwen failed", e, file=sys.stderr)
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--model", default="models/qwen2-0_5b-instruct-q4_k_m.gguf")
    p.add_argument("--out", default="script_job.json")
    args = p.parse_args()

    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = run_qwen(Path(args.model), topic)
    if result is None:
        result = template_script(topic)
        print("Using template fallback", file=sys.stderr)

    # final safety clean
    result["script"] = clean_spoken(result["script"]) or template_script(topic)["script"]

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("bg.txt").write_text(result.get("bg") or "studio", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
