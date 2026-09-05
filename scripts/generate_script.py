#!/usr/bin/env python3
"""Mike the Tutor scripts — coherent, longer classroom shorts."""
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
    t = re.sub(r"\([^)]*(whiteboard|board|write|camera|physics)[^)]*\)", " ", t, flags=re.I)
    for p in [
        r"INTRO:\s*", r"BODY:\s*", r"Hook:\s*", r"Facts?:\s*",
        r"###.*?\n", r"Please note.*", r"You write.*",
        r"Okay, guys,?\s*", r"Alright, guys,?\s*",
    ]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\s+", " ", t).strip()
    # drop leading fragment sentences (common Gemma bug)
    t = re.sub(r"^(back into|into the|so that the|which is|and then)\b[^.]{0,40}\.\s*", "", t, flags=re.I)
    words = t.split()
    if len(words) < 50:
        return ""
    if len(words) > 200:
        t = " ".join(words[:190])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def pick_sentences(extract: str) -> list[str]:
    parts = []
    for s in re.split(r"(?<=[.!?])\s+", extract or ""):
        s = s.strip()
        if len(s) < 50:
            continue
        if re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
            continue
        # must look like a full sentence
        if not re.match(r"^[A-Z0-9]", s):
            continue
        parts.append(s)
    return parts[:5]


def template_scripts(topic: dict) -> dict:
    raw = topic.get("title") or "this idea"
    short = display_title(raw)
    sents = pick_sentences(topic.get("extract") or "")
    while len(sents) < 4:
        sents.append(f"Scientists use simple everyday examples to explain {short}.")
    facts = []
    for s in sents[:4]:
        if len(s) > 130:
            s = s[:127].rsplit(" ", 1)[0] + "."
        facts.append(s)

    script = (
        f"Hey, I am Mike. Welcome to the board. Today we learn about {short}. "
        f"Here is the big idea. {facts[0]} "
        f"Next point. {facts[1]} "
        f"Another detail. {facts[2]} "
        f"One more thing. {facts[3]} "
        f"So now you can explain {short} in plain words. "
        f"Follow mike.the.tutor for more short classroom lessons. See you next time!"
    )
    script = re.sub(r"\s+", " ", script).strip()
    intro = f"Hey, I am Mike. Welcome to the board. Today we learn about {short}."
    return {
        "title": raw,
        "short_title": short,
        "intro_script": intro,
        "script": script,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def pack(topic: dict, text: str, engine: str) -> dict | None:
    short = display_title(topic.get("title") or "Lesson")
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    # reject scripts that still start mid-thought
    if re.match(r"^(back into|into the|so that|and then)\b", cleaned, re.I):
        return None
    if short.lower() not in cleaned.lower() and "mike" not in cleaned.lower():
        cleaned = f"Hey, I am Mike. Today we learn about {short}. " + cleaned
    if "mike.the.tutor" not in cleaned.lower() and "follow" not in cleaned.lower():
        cleaned = cleaned.rstrip(".!") + ". Follow mike.the.tutor for more lessons!"
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "intro_script": f"Hey, I am Mike. Welcome to the board. Today we learn about {short}.",
        "script": cleaned,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_gguf(model: Path, topic: dict, engine_name: str) -> dict | None:
    if not model.exists() or model.stat().st_size < 10_000_000:
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    short = display_title(topic.get("title") or "")
    inp.write_text(
        json.dumps(
            {
                "model": str(model),
                "title": short,
                "extract": (topic.get("extract") or "")[:450],
            }
        ),
        encoding="utf-8",
    )
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run(
            [sys.executable, str(helper), str(inp), str(outp)],
            timeout=300,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not outp.exists():
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        text = f"{data.get('intro') or ''} {data.get('body') or ''}"
        return pack(topic, text, engine_name)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def run_openrouter(topic: dict) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:420]
    model = os.environ.get("OPENROUTER_MODEL", "google/gemma-2-2b-it:free").strip()
    prompt = (
        "You are Mike, a friendly science tutor for teens on TikTok (mike.the.tutor). "
        "Write 140 to 170 spoken words. Complete sentences only. No markdown. "
        "No parentheses. No stage directions.\n"
        f"Topic name to use: {short}\nFacts: {extract}\n\n"
        "Structure: greet as Mike, name the topic, three clear facts in full sentences, "
        "end with follow mike.the.tutor."
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/qxil-pipe",
                "X-Title": "mike-tutor",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 350,
                "temperature": 0.5,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return None
        text = r.json()["choices"][0]["message"]["content"].strip()
        return pack(topic, text, f"openrouter:{model}")
    except Exception as e:
        print("openrouter", e, file=sys.stderr)
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
        if args.model:
            result = run_gguf(Path(args.model), topic, "gemma-gguf")
        if result is None and args.model_fallback:
            result = run_gguf(Path(args.model_fallback), topic, "tinyllama-gguf")
        if result is None:
            result = run_openrouter(topic)
    if result is None:
        result = template_scripts(topic)
        print("engine=template", file=sys.stderr)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("intro.txt").write_text((result.get("intro_script") or "") + "\n", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")
    Path("title_short.txt").write_text(result["short_title"], encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
