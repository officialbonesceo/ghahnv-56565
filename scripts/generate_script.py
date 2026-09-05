#!/usr/bin/env python3
"""Topic -> longer clear classroom scripts. Reject bad LLM output."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    for p in [
        r"INTRO:\s*", r"BODY:\s*", r"Hook:\s*", r"Facts?:\s*",
        r"Friendly Closure:\s*", r"Closing:\s*", r"Script:\s*",
        r"###.*?\n", r"Focal [Pp]oint.*", r"\(x\d.*?\)",
        r"Please note.*", r"You write.*",
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
    if len(words) < 28:
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


def run_tinyllama(model: Path, topic: dict) -> dict | None:
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    inp.write_text(json.dumps({
        "model": str(model),
        "title": topic.get("title") or "",
        "extract": (topic.get("extract") or "")[:400],
    }), encoding="utf-8")
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run([sys.executable, str(helper), str(inp), str(outp)], timeout=180, capture_output=True, text=True)
        if r.returncode != 0 or not outp.exists():
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        body = clean_spoken(data.get("body") or "")
        intro = clean_spoken(data.get("intro") or "")
        if not body:
            return None
        title = topic.get("title") or "Lesson"
        return {
            "title": title,
            "short_title": short_title(title),
            "intro_script": intro or f"Look at the board. Today we learn about {short_title(title)}."
            ,
            "script": body,
            "bg": "classroom",
            "source": topic.get("url") or "",
            "engine": "tinyllama",
        }
    except Exception:
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--out", default="script_job.json")
    p.add_argument("--try-llm", action="store_true")
    args = p.parse_args()
    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = None
    if args.try_llm and args.model and Path(args.model).exists():
        result = run_tinyllama(Path(args.model), topic)
    if result is None:
        result = template_scripts(topic)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("intro.txt").write_text((result.get("intro_script") or "") + "\n", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")
    Path("title_short.txt").write_text(result.get("short_title") or result["title"], encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
