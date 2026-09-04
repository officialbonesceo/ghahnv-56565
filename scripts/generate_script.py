#!/usr/bin/env python3
"""
Qwen2-0.5B (GGUF) -> TikTok script for MEZI.
Falls back to template if model missing/fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def template_script(topic: dict) -> dict:
    title = topic.get("title") or "this idea"
    extract = topic.get("extract") or ""
    # first 2 sentences max
    parts = re.split(r"(?<=[.!?])\s+", extract)
    facts = [p.strip() for p in parts if len(p.strip()) > 20][:2]
    if not facts:
        facts = [extract[:160]]
    body = " ".join(facts)
    if len(body) > 220:
        body = body[:217] + "..."
    script = (
        f"Hey! Quick question about {title}. "
        f"{body} "
        f"Wild, right? Follow Mezi for more simple explainers!"
    )
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
        print("model missing", model_path, file=sys.stderr)
        return None

    prompt = f"""You write TikTok scripts for Mezi, a friendly curious cartoon explorer.
Rules:
- 50 to 85 words only
- Simple spoken English for teens
- Structure: hook question, 2 short facts, fun closing line
- No hashtags, no emojis, no stage directions
- Do not invent dangerous or medical advice

Topic: {topic.get('title')}
Context: {topic.get('extract', '')[:400]}

Write only the spoken script text:"""

    try:
        llm = Llama(
            model_path=str(model_path),
            n_ctx=1024,
            n_threads=2,
            verbose=False,
        )
        out = llm(
            prompt,
            max_tokens=180,
            temperature=0.7,
            stop=["Topic:", "Rules:", "\n\n\n"],
        )
        text = out["choices"][0]["text"].strip()
        text = re.sub(r'^["\']|["\']$', "", text).strip()
        # strip possible labels
        text = re.sub(r"^(Script:|Spoken script:)\s*", "", text, flags=re.I)
        words = text.split()
        if len(words) < 25:
            return None
        if len(words) > 110:
            text = " ".join(words[:100])
        return {
            "title": topic.get("title") or "Mezi tip",
            "script": text,
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
    result = run_qwen(Path(args.model), topic) or template_script(topic)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    # also plain script.txt for TTS
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("bg.txt").write_text(result.get("bg") or "studio", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
