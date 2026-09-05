#!/usr/bin/env python3
"""Topic -> clear TikTok scripts. Prefer solid template; LLM only if clean."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    # strip labels and junk TinyLlama loves to emit
    for p in [
        r"INTRO:\s*",
        r"BODY:\s*",
        r"Hook:\s*",
        r"Facts?:\s*",
        r"Friendly Closure:\s*",
        r"Closing:\s*",
        r"Script:\s*",
        r"###.*?\n",
        r"Focal [Pp]oint.*?\n",
        r"\(x\d.*?\)",
        r"x\d\s*=\s*x\d",
        r"y\d\s*=\s*y\d",
        r"-\s*Focal.*",
        r"Please note.*",
        r"You write.*",
    ]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\d+\.\s*", "", t)
    t = re.sub(r"[-=]{2,}", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    low = t.lower()
    if any(
        x in low
        for x in (
            "friendly closure",
            "focal point",
            "you write",
            "coordinates",
            "x1",
            "y1",
            "###",
        )
    ):
        return ""
    # reject equation-heavy nonsense
    if t.count("=") > 1 or t.count("(") > 2:
        return ""
    words = t.split()
    if len(words) < 18:
        return ""
    if len(words) > 100:
        t = " ".join(words[:90])
    if t and t[-1] not in ".!?":
        t += "!"
    return t


def short_title(title: str) -> str:
    t = title or "This idea"
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    if len(t) > 36:
        t = t[:33] + "..."
    return t


def pick_sentences(extract: str) -> list[str]:
    parts = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", extract or "")
        if len(s.strip()) > 40 and "=" not in s and "(" not in s[:20]
    ]
    return parts[:3]


def template_scripts(topic: dict) -> dict:
    title = topic.get("title") or "this idea"
    short = short_title(title)
    sents = pick_sentences(topic.get("extract") or "")
    if not sents:
        sents = [
            f"{short} is a real idea people study and talk about.",
            "The simple version still helps us understand the world a little better.",
        ]
    f1 = sents[0]
    if len(f1) > 120:
        f1 = f1[:117].rsplit(" ", 1)[0] + "."
    f2 = sents[1] if len(sents) > 1 else "Scientists keep learning more about it every year."
    if len(f2) > 120:
        f2 = f2[:117].rsplit(" ", 1)[0] + "."

    intro = (
        f"Look at the board. Today we learn about {short}. "
        f"Stay with Mezi for a simple explanation."
    )
    body = (
        f"So what is {short}? {f1} "
        f"Here is another point. {f2} "
        f"That is the idea in plain words. Follow Mezi for more classroom explainers!"
    )
    intro = re.sub(r"\s+", " ", intro).strip()
    body = re.sub(r"\s+", " ", body).strip()
    return {
        "title": title,
        "short_title": short,
        "intro_script": intro,
        "script": body,
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
    }


def run_tinyllama(model: Path, topic: dict) -> dict | None:
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    inp = Path("/tmp/llm_in.json")
    outp = Path("/tmp/llm_out.json")
    inp.write_text(
        json.dumps(
            {
                "model": str(model),
                "title": topic.get("title") or "",
                "extract": (topic.get("extract") or "")[:380],
            }
        ),
        encoding="utf-8",
    )
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run(
            [sys.executable, str(helper), str(inp), str(outp)],
            timeout=180,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not outp.exists():
            print("llm failed", r.returncode, r.stderr[-400:], file=sys.stderr)
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        intro = clean_spoken(data.get("intro") or "")
        body = clean_spoken(data.get("body") or "")
        if not body or len(body.split()) < 25:
            return None
        title = topic.get("title") or "Mezi"
        return {
            "title": title,
            "short_title": short_title(title),
            "intro_script": intro
            or f"Look at the board. Today we learn about {short_title(title)}. Stay with Mezi!",
            "script": body,
            "bg": "classroom",
            "source": topic.get("url") or "",
            "engine": "tinyllama",
        }
    except Exception as e:
        print("llm error", e, file=sys.stderr)
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
        if result:
            print("engine=tinyllama accepted", file=sys.stderr)
        else:
            print("engine=tinyllama rejected -> template", file=sys.stderr)
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
