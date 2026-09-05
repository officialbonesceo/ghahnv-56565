#!/usr/bin/env python3
"""Mike scripts: OpenRouter free -> Gemma -> tight template (on-topic, not slow)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests


def display_title(title: str) -> str:
    t = title or "Science"
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    return t[:40]


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"\([^)]{0,80}\)", " ", t)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"Hook:\s*", r"###.*?\n"]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(back into|into the|so that the|and then)\b[^.]{0,50}\.\s*", "", t, flags=re.I)
    words = t.split()
    # TikTok attention: keep ~90-140 words (faster delivery with +22% rate)
    if len(words) < 50:
        return ""
    if len(words) > 150:
        t = " ".join(words[:140])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def pick_sentences(extract: str) -> list[str]:
    parts = []
    for s in re.split(r"(?<=[.!?])\s+", extract or ""):
        s = s.strip()
        if len(s) < 45 or not re.match(r"^[A-Z0-9]", s):
            continue
        if re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
            continue
        parts.append(s)
    return parts[:4]


def template_scripts(topic: dict) -> dict:
    short = display_title(topic.get("title") or "this idea")
    sents = pick_sentences(topic.get("extract") or "")
    while len(sents) < 3:
        sents.append(f"Simple examples make {short} easier to remember.")
    facts = []
    for s in sents[:3]:
        if len(s) > 110:
            s = s[:107].rsplit(" ", 1)[0] + "."
        facts.append(s)
    script = (
        f"Hey, I am Mike. Quick board lesson on {short}. "
        f"{facts[0]} "
        f"{facts[1]} "
        f"{facts[2]} "
        f"That is {short} in plain words. Follow mike.the.tutor for the next one!"
    )
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "intro_script": f"Hey, I am Mike. Quick board lesson on {short}.",
        "script": re.sub(r"\s+", " ", script).strip(),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def pack(topic: dict, text: str, engine: str) -> dict | None:
    short = display_title(topic.get("title") or "Lesson")
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    if re.match(r"^(back into|into the|so that|and then)\b", cleaned, re.I):
        return None
    # must stay on topic
    if short.lower() not in cleaned.lower():
        cleaned = f"Hey, I am Mike. Quick lesson on {short}. " + cleaned
    if "mike.the.tutor" not in cleaned.lower():
        cleaned = cleaned.rstrip(".!") + ". Follow mike.the.tutor!"
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "intro_script": f"Hey, I am Mike. Quick board lesson on {short}.",
        "script": cleaned,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_openrouter(topic: dict) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:400]
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    prompt = (
        "You are Mike, a fast TikTok science tutor (@mike.the.tutor). "
        "Write 100 to 130 spoken words ONLY about this topic. "
        "Stay on topic. No tangents. Complete sentences. No markdown.\n"
        f"Topic: {short}\nFacts: {extract}\n\n"
        "Greet as Mike, name the topic once, give three tight facts, one everyday example, "
        "end with follow mike.the.tutor."
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/officialbonesceo/ghahnv-56565",
                "X-Title": "mike-the-tutor",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 280,
                "temperature": 0.35,
            },
            timeout=90,
        )
        print("openrouter", r.status_code, model, file=sys.stderr)
        if r.status_code != 200:
            print(r.text[:300], file=sys.stderr)
            return None
        text = r.json()["choices"][0]["message"]["content"].strip()
        used = r.json().get("model") or model
        return pack(topic, text, f"openrouter:{used}")
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
        return None


def run_gguf(model: Path, topic: dict, engine_name: str) -> dict | None:
    if not model.exists() or model.stat().st_size < 10_000_000:
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    short = display_title(topic.get("title") or "")
    inp.write_text(
        json.dumps({"model": str(model), "title": short, "extract": (topic.get("extract") or "")[:400]}),
        encoding="utf-8",
    )
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run(
            [sys.executable, str(helper), str(inp), str(outp)],
            timeout=240,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not outp.exists():
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        return pack(topic, f"{data.get('intro') or ''} {data.get('body') or ''}", engine_name)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--model-fallback", default="")
    p.add_argument("--out", default="script_job.json")
    p.add_argument("--try-llm", action="store_true")
    args = p.parse_args()

    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = None
    if args.try_llm:
        result = run_openrouter(topic)
        if result is None and args.model:
            result = run_gguf(Path(args.model), topic, "gemma-gguf")
        if result is None and args.model_fallback:
            result = run_gguf(Path(args.model_fallback), topic, "tinyllama-gguf")
    if result is None:
        result = template_scripts(topic)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("intro.txt").write_text((result.get("intro_script") or "") + "\n", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")
    Path("title_short.txt").write_text(result["short_title"], encoding="utf-8")

    short = result["short_title"]
    hashtag_slug = re.sub(r"[^a-z0-9]+", "", short.lower())[:24] or "science"
    caption = (
        f"{short} in plain words — Mike the Tutor\n\n"
        f"Comment YES for part 2\n"
        f"Follow @mike.the.tutor\n\n"
        f"#{hashtag_slug} #learntok #science #fyp #foryou #stem #studytok #mikethetutor"
    )
    Path("tiktok_caption.txt").write_text(caption, encoding="utf-8")
    Path("tiktok_comment.txt").write_text(
        f"Comment YES if you want part 2 on {short} — I reply to every one",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
