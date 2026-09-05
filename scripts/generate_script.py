#!/usr/bin/env python3
"""Wikipedia topic -> intro + body scripts. TinyLlama optional (subprocess-safe)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path


def clean_spoken(text: str) -> str:
    t = text.strip().strip('"').strip("'")
    for p in [
        r"\(You write.*?\)",
        r"You write.*",
        r"Please note that.*",
        r"Rules:.*",
        r"Hook:\s*",
        r"Facts?:\s*",
        r"Script:\s*",
        r"Intro:\s*",
        r"Body:\s*",
    ]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\d+\.\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if any(x in t.lower() for x in ("you write", "please note", "tiktok script for")):
        return ""
    words = t.split()
    if len(words) < 12:
        return ""
    if len(words) > 90:
        t = " ".join(words[:85])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def simplify_fact(s: str, max_len: int = 110) -> str:
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return s


def template_scripts(topic: dict) -> dict:
    title = topic.get("title") or "this idea"
    extract = (topic.get("extract") or "").strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", extract)
        if len(s.strip()) > 30
    ]
    fact1 = simplify_fact(sentences[0]) if sentences else f"{title} is something people still talk about."
    fact2 = simplify_fact(sentences[1]) if len(sentences) > 1 else "There is more to discover if we look closer."

    # Avoid awkward "Ever heard of 1960-61 Silver Hut expedition?"
    short = title
    if re.match(r"^\d{4}", title):
        short = re.sub(r"^\d{4}(-\d{2})?\s*", "", title).strip() or title

    intro = (
        f"Today on the board: {short}. "
        f"Stay with Mezi — we will break it into simple pieces."
    )
    body = (
        f"Here is the idea. {fact1} "
        f"Also, {fact2} "
        f"That is why it matters. Follow Mezi for more quick explainers!"
    )
    intro = re.sub(r"\s+", " ", intro).strip()
    body = re.sub(r"\s+", " ", body).strip()
    return {
        "title": title,
        "short_title": short,
        "intro_script": intro,
        "script": body,
        "bg": topic.get("bg") or "science",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def run_tinyllama_subprocess(model: Path, topic: dict) -> dict | None:
    """Run LLM in child process so SIGILL cannot kill the workflow step."""
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    payload = {
        "model": str(model),
        "title": topic.get("title") or "",
        "extract": (topic.get("extract") or "")[:400],
    }
    inp = Path("/tmp/llm_in.json")
    outp = Path("/tmp/llm_out.json")
    inp.write_text(json.dumps(payload), encoding="utf-8")
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run(
            [sys.executable, str(helper), str(inp), str(outp)],
            timeout=180,
            capture_output=True,
            text=True,
        )
        print(r.stdout[-500:] if r.stdout else "", file=sys.stderr)
        print(r.stderr[-500:] if r.stderr else "", file=sys.stderr)
        if r.returncode != 0 or not outp.exists():
            print("llm child failed code", r.returncode, file=sys.stderr)
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        intro = clean_spoken(data.get("intro") or "")
        body = clean_spoken(data.get("body") or "")
        if not body:
            return None
        title = topic.get("title") or "Mezi"
        short = title
        if re.match(r"^\d{4}", title):
            short = re.sub(r"^\d{4}(-\d{2})?\s*", "", title).strip() or title
        return {
            "title": title,
            "short_title": short,
            "intro_script": intro or f"Today on the board: {short}. Stay with Mezi!",
            "script": body,
            "bg": topic.get("bg") or "science",
            "source": topic.get("url") or "",
            "engine": "tinyllama",
        }
    except Exception as e:
        print("llm subprocess error", e, file=sys.stderr)
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
        result = run_tinyllama_subprocess(Path(args.model), topic)
    if result is None:
        result = template_scripts(topic)
        print("engine=template", file=sys.stderr)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    # body is main script.txt for backwards compat; intro separate
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("intro.txt").write_text(result.get("intro_script") or "", encoding="utf-8")
    Path("bg.txt").write_text(result.get("bg") or "science", encoding="utf-8")
    Path("title_short.txt").write_text(result.get("short_title") or result["title"], encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
