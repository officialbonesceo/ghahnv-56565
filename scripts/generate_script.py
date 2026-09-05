#!/usr/bin/env python3
"""Longer classroom shorts. Gemma -> OpenRouter -> template."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    # strip markdown / stage directions Gemma sometimes emits
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"\([^)]*(whiteboard|board|write|camera)[^)]*\)", " ", t, flags=re.I)
    for p in [
        r"INTRO:\s*", r"BODY:\s*", r"Hook:\s*", r"Facts?:\s*",
        r"Friendly Closure:\s*", r"Closing:\s*", r"Script:\s*",
        r"###.*?\n", r"Please note.*", r"You write.*",
        r"Okay, guys,?\s*", r"Alright, guys,?\s*",
    ]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\d+\.\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    low = t.lower()
    if any(x in low for x in ("friendly closure", "focal point", "coordinates", "x1", "###")):
        return ""
    if t.count("=") > 1:
        return ""
    words = t.split()
    if len(words) < 40:
        return ""
    if len(words) > 220:
        t = " ".join(words[:200])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def short_title(title: str) -> str:
    t = title or "This idea"
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    # disambiguation pages
    if t.lower() in {"battery", "wave", "cell"}:
        pass
    return t[:36] + ("..." if len(t) > 36 else "")


def pick_sentences(extract: str) -> list[str]:
    parts = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", extract or "")
        if len(s.strip()) > 40 and "crime" not in s.lower() and "unlawful" not in s.lower()
    ]
    return parts[:5]


def template_scripts(topic: dict) -> dict:
    title = topic.get("title") or "this idea"
    short = short_title(title)
    sents = pick_sentences(topic.get("extract") or "")
    while len(sents) < 4:
        sents.append("People still study this idea and use simple examples to explain it.")
    facts = []
    for s in sents[:4]:
        if len(s) > 140:
            s = s[:137].rsplit(" ", 1)[0] + "."
        facts.append(s)

    intro = (
        f"Welcome to the board. Today we are learning about {short}. "
        f"Stay with me for a clear, simple explanation you can actually remember."
    )
    body = (
        f"Let us start with the big idea. {facts[0]} "
        f"Here is the next point. {facts[1]} "
        f"Another useful detail. {facts[2]} "
        f"And one more thing. {facts[3]} "
        f"So when someone asks about {short}, you can explain it in plain words. "
        f"That is our classroom lesson. Follow for more short science explainers!"
    )
    full = re.sub(r"\s+", " ", (intro + " " + body).strip())
    return {
        "title": title,
        "short_title": short,
        "intro_script": re.sub(r"\s+", " ", intro).strip(),
        "script": full,  # full spoken short (intro+body) for longer video
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def pack(topic: dict, intro: str, body: str, engine: str) -> dict | None:
    intro_c = clean_spoken(intro) if intro else ""
    body_c = clean_spoken(body)
    if not body_c:
        return None
    title = topic.get("title") or "Lesson"
    short = short_title(title)
    if not intro_c:
        intro_c = (
            f"Welcome to the board. Today we are learning about {short}. "
            f"Stay with me for a simple explanation."
        )
    full = clean_spoken(intro_c + " " + body_c) or body_c
    # ensure length for a real short
    if len(full.split()) < 70:
        return None
    return {
        "title": title,
        "short_title": short,
        "intro_script": intro_c,
        "script": full,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_gguf(model: Path, topic: dict, engine_name: str) -> dict | None:
    if not model.exists() or model.stat().st_size < 10_000_000:
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    inp.write_text(
        json.dumps(
            {
                "model": str(model),
                "title": topic.get("title") or "",
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
            print("gguf failed", r.returncode, file=sys.stderr)
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        return pack(topic, data.get("intro") or "", data.get("body") or "", engine_name)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def run_openrouter(topic: dict) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    title = topic.get("title") or "science"
    extract = (topic.get("extract") or "")[:420]
    model = os.environ.get("OPENROUTER_MODEL", "google/gemma-2-2b-it:free").strip()
    prompt = (
        "Write a spoken TikTok classroom lesson for teens, 120 to 160 words total. "
        "Simple English. No markdown. No stage directions. No math symbols.\n"
        f"Topic: {title}\nFacts: {extract}\n\n"
        "Start with a warm welcome to the board and name the topic. "
        "Then give three clear facts. End by inviting them back next time."
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/qxil-pipe",
                "X-Title": "qxil-pipe",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 320,
                "temperature": 0.55,
            },
            timeout=60,
        )
        if r.status_code != 200:
            print("openrouter", r.status_code, r.text[:300], file=sys.stderr)
            return None
        text = r.json()["choices"][0]["message"]["content"].strip()
        words = text.split()
        mid = max(30, min(50, len(words) // 4))
        return pack(topic, " ".join(words[:mid]), " ".join(words[mid:]), f"openrouter:{model}")
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
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
    Path("title_short.txt").write_text(result.get("short_title") or result["title"], encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
