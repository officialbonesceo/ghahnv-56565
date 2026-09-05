#!/usr/bin/env python3
"""Topic -> scripts. Order: Gemma GGUF -> OpenRouter -> template."""
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
    for p in [
        r"INTRO:\s*", r"BODY:\s*", r"Hook:\s*", r"Facts?:\s*",
        r"Friendly Closure:\s*", r"Closing:\s*", r"Script:\s*",
        r"###.*?\n", r"Please note.*", r"You write.*",
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
    if len(words) < 25:
        return ""
    if len(words) > 140:
        t = " ".join(words[:130])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def short_title(title: str) -> str:
    t = title or "This idea"
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    return t[:36] + ("..." if len(t) > 36 else "")


def pick_sentences(extract: str) -> list[str]:
    parts = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", extract or "")
        if len(s.strip()) > 45 and "=" not in s
    ]
    return parts[:4]


def template_scripts(topic: dict) -> dict:
    title = topic.get("title") or "this idea"
    short = short_title(title)
    sents = pick_sentences(topic.get("extract") or "")
    while len(sents) < 3:
        sents.append("Researchers still study this idea and share clear examples.")
    f1, f2, f3 = sents[0], sents[1], sents[2]
    for i, f in enumerate((f1, f2, f3)):
        if len(f) > 130:
            sents[i] = f[:127].rsplit(" ", 1)[0] + "."
    f1, f2, f3 = sents[0], sents[1], sents[2]
    intro = (
        f"Look at the board. Today our lesson is {short}. "
        f"We will keep it simple and useful. Stay with the class."
    )
    body = (
        f"What is {short}? {f1} "
        f"Next point. {f2} "
        f"One more thing. {f3} "
        f"That is the core idea in plain words. Come back next time for another classroom lesson!"
    )
    return {
        "title": title,
        "short_title": short,
        "intro_script": re.sub(r"\s+", " ", intro).strip(),
        "script": re.sub(r"\s+", " ", body).strip(),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def pack(topic: dict, intro: str, body: str, engine: str) -> dict | None:
    body = clean_spoken(body)
    if not body:
        return None
    title = topic.get("title") or "Lesson"
    short = short_title(title)
    intro = clean_spoken(intro) or f"Look at the board. Today we learn about {short}. Stay with the class."
    return {
        "title": title,
        "short_title": short,
        "intro_script": intro,
        "script": body,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_gguf(model: Path, topic: dict, engine_name: str) -> dict | None:
    if not model.exists() or model.stat().st_size < 10_000_000:
        print("gguf missing/small", model, file=sys.stderr)
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    inp.write_text(
        json.dumps(
            {
                "model": str(model),
                "title": topic.get("title") or "",
                "extract": (topic.get("extract") or "")[:420],
            }
        ),
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
        print(r.stderr[-300:] if r.stderr else "", file=sys.stderr)
        if r.returncode != 0 or not outp.exists():
            print("gguf child failed", r.returncode, file=sys.stderr)
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        return pack(topic, data.get("intro") or "", data.get("body") or "", engine_name)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def run_openrouter(topic: dict) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("no OPENROUTER_API_KEY", file=sys.stderr)
        return None
    title = topic.get("title") or "science"
    extract = (topic.get("extract") or "")[:400]
    model = os.environ.get("OPENROUTER_MODEL", "google/gemma-2-2b-it:free").strip()
    prompt = (
        "Write spoken TikTok classroom lines for teens. Simple English only. "
        "No math symbols. No labels like INTRO or BODY.\n"
        f"Topic: {title}\nFacts: {extract}\n\n"
        "First 35 words: introduce the topic while pointing at a board.\n"
        "Then 80 words: two simple facts and a friendly ending."
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
                "max_tokens": 220,
                "temperature": 0.6,
            },
            timeout=60,
        )
        print("openrouter status", r.status_code, file=sys.stderr)
        data = r.json()
        if r.status_code != 200:
            print(json.dumps(data)[:400], file=sys.stderr)
            return None
        text = data["choices"][0]["message"]["content"].strip()
        words = text.split()
        mid = max(25, min(45, len(words) // 3))
        intro = " ".join(words[:mid])
        body = " ".join(words[mid:]) if len(words) > mid else text
        return pack(topic, intro, body, f"openrouter:{model}")
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--model", default="", help="Primary GGUF path (Gemma preferred)")
    p.add_argument("--model-fallback", default="", help="Optional second GGUF e.g. TinyLlama")
    p.add_argument("--out", default="script_job.json")
    p.add_argument("--try-llm", action="store_true")
    args = p.parse_args()

    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = None

    if args.try_llm:
        if args.model:
            result = run_gguf(Path(args.model), topic, "gemma-gguf")
            if result:
                print("engine=gemma-gguf", file=sys.stderr)
        if result is None and args.model_fallback:
            result = run_gguf(Path(args.model_fallback), topic, "tinyllama-gguf")
            if result:
                print("engine=tinyllama-gguf", file=sys.stderr)
        if result is None:
            result = run_openrouter(topic)
            if result:
                print("engine=openrouter", file=sys.stderr)

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
