#!/usr/bin/env python3
"""AI-only student Shorts scripts. No template fallback — exit 1 if AI fails."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import requests

VALID_MOVES = {
    "talk", "welcome", "point", "sit", "present", "question", "happy",
    "explain", "shrug", "count", "think", "lean",
}

HOOK_TEMPLATES = [
    "Stop scrolling. This is how exams trick you on {topic}.",
    "Most students lose marks on {topic}. Here is why.",
    "If {topic} confuses you, watch this once.",
    "Teachers assume you know {topic}. You might not.",
    "One clear way to explain {topic} in an exam.",
    "Before your test: what {topic} actually means.",
    "{topic} in plain words — no textbook fog.",
    "Can you define {topic} without panic? Start here.",
]

CTA_ENDINGS = [
    "Comment what you understood.",
    "Comment the next topic you want.",
    "Comment your subject if you want this series.",
    "Comment one thing you learned.",
]

# Phrases that mean the model echoed the system prompt into the script
PROMPT_LEAK_RE = re.compile(
    r"(?is)("
    r"tiktok for secondary|before exams\.?\s*\d\."
    r"|first line must|no hey/?hi|definition\s*→|exam-useful fact"
    r"|75-?105 words|never say mike\.the\.tutor|comment yes"
    r"|after script:|moves:\s*question@|moves:\s*talk,"
    r"|instruct:|system:|user:|assistant:"
    r"|you are a helpful|write a script|output only"
    r"|topic:\s*\w+\s*facts:"
    r")"
)


def display_title(title: str) -> str:
    t = title or "Science"
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    return t[:40]


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    # Drop anything after labeled metadata lines
    t = re.split(r"(?im)^\s*(MOVES|DEFINITION|DIDYOUKNOW|INSTRUCT|SYSTEM)\s*:", t)[0]
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"(?im)^#{1,3}\s+.*$", " ", t)
    t = re.sub(r"MOVES:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"DEFINITION:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"DIDYOUKNOW:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"Instruct:.*", " ", t, flags=re.I | re.S)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"SCRIPT:\s*"]:
        t = re.sub(p, " ", t, flags=re.I)
    # If model pasted the whole prompt, reject
    if PROMPT_LEAK_RE.search(t):
        print("PROMPT_LEAK detected — rejecting", file=sys.stderr)
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(hey[, ]+)?(i am|i'm) mike[.!]?\s*", "", t, flags=re.I)
    t = re.sub(r"^today (on the board|we (learn|talk) about)[:\s]+", "", t, flags=re.I)
    t = re.sub(r"comment yes[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"follow\s+mike\.the\.tutor[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    words = t.split()
    if len(words) < 45:
        return ""
    if len(words) > 120:
        t = " ".join(words[:110])
        if "." in t:
            t = t[: t.rfind(".") + 1]
    if t and t[-1] not in ".!?":
        if "." in t:
            t = t[: t.rfind(".") + 1]
        else:
            t += "."
    return t


def short_definition(extract: str, title: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    for s in sents:
        s = s.strip()
        if 35 <= len(s) <= 140 and re.match(r"^[A-Z0-9]", s):
            return s[:120]
    return f"{title} is a simple idea you can explain in everyday words."


def did_you_know_line(extract: str, title: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    for s in sents[1:]:
        s = s.strip()
        if 30 <= len(s) <= 120 and re.match(r"^[A-Z0-9]", s):
            return s[:110]
    return f"Most students have heard of {title}, but few can explain it in an exam."


def default_moves(topic: str) -> list[dict]:
    return [
        {"at": 0.00, "move": "question"},
        {"at": 0.12, "move": "talk"},
        {"at": 0.35, "move": "explain"},
        {"at": 0.55, "move": "point"},
        {"at": 0.78, "move": "present"},
        {"at": 0.92, "move": "happy"},
    ]


def parse_moves(raw: str, topic: str) -> list[dict]:
    if not raw:
        return default_moves(topic)
    out = []
    raw = raw.replace("→", " ").replace("->", " ")
    for part in re.split(r"[,;|\n]+", raw):
        part = part.strip().strip("-•*").strip()
        if not part:
            continue
        move = at = None
        m = re.match(r"([a-z_]+)\s*[@:]\s*(0?\.\d+|1\.0?|0|1)\b", part, re.I)
        if m:
            move, at = m.group(1).lower(), float(m.group(2))
        if move is None:
            m = re.match(r"(0?\.\d+|1\.0?|0|1)\s*[:\s]+\s*([a-z_]+)\b", part, re.I)
            if m:
                at, move = float(m.group(1)), m.group(2).lower()
        if move is None:
            m = re.match(r"([a-z_]+)\s+(\d{1,3})\s*%?\b", part, re.I)
            if m:
                move = m.group(1).lower()
                pct = float(m.group(2))
                at = pct / 100.0 if pct > 1 else pct
        if move and at is not None:
            if move in ("walk_left", "walk_right"):
                move = "talk"
            if move not in VALID_MOVES:
                for v in VALID_MOVES:
                    if v.startswith(move[:4]) or move in v:
                        move = v
                        break
            if move in VALID_MOVES:
                out.append({"at": max(0.0, min(1.0, float(at))), "move": move})
    if len(out) < 2:
        return default_moves(topic)
    out.sort(key=lambda x: x["at"])
    if out[0]["at"] > 0.05:
        out.insert(0, {"at": 0.0, "move": "question"})
    return out


def force_hook(script: str, topic: str) -> str:
    s = script.strip()
    soft = re.match(
        r"^(hey|hi|hello|welcome|i am mike|i'm mike|today we|let's talk|here is)",
        s,
        re.I,
    )
    first = s.split(".")[0] if "." in s else s
    weak = soft or len(first.split()) > 16 or not re.search(
        r"\b(exam|mark|test|student|wrong|confus|trick|before|stop)\b", first, re.I
    )
    if weak:
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)
        rest = s
        if "." in s:
            first_s, _, after = s.partition(".")
            if re.match(r"^(hey|hi|hello|i am|i'm|today|here is|stop)", first_s.strip(), re.I):
                rest = after.strip()
        s = f"{hook} {rest}".strip()
    return re.sub(r"\s+", " ", s)


def ensure_cta(script: str, topic: str) -> str:
    s = script.rstrip(".! ")
    s = re.sub(r"(?i)comment yes[^.]*", "", s)
    s = re.sub(r"(?i)follow\s+(mike\.the\.tutor|@?mike\.the\.tutor)[^.]*", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".! ")
    cta = random.choice(CTA_ENDINGS)
    if "comment" not in s.lower():
        s += f". {cta}"
    if "follow" not in s.lower():
        s += " Follow for more."
    if not s.endswith((".", "!", "?")):
        s += "."
    return s


def pack(topic, text, engine, moves_raw="", definition="", dyk=""):
    short = display_title(topic.get("title") or "Lesson")
    extract = topic.get("extract") or ""
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    cleaned = force_hook(cleaned, short)
    cleaned = ensure_cta(cleaned, short)
    if PROMPT_LEAK_RE.search(cleaned):
        print("PROMPT_LEAK after pack — rejecting", file=sys.stderr)
        return None
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": (definition or short_definition(extract, short))[:120],
        "did_you_know": (dyk or did_you_know_line(extract, short))[:110],
        "cta": random.choice(CTA_ENDINGS),
        "script": cleaned,
        "moves": parse_moves(moves_raw, short),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_openrouter(topic: dict):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("openrouter: no API key", file=sys.stderr)
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:400]
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    # Keep instructions out of a form models love to copy-paste
    system = (
        "You write spoken TikTok voiceover for secondary school exam revision. "
        "Return ONLY the spoken script paragraphs. No headings, no numbered rules, "
        "no MOVES/DEFINITION labels in the main text."
    )
    user = (
        f"Topic: {short}\n"
        f"Facts you may use:\n{extract}\n\n"
        "Write 75-105 words. Open with an exam-style hook (marks/test/confusion). "
        "Then definition, one exam-useful fact, one did-you-know style line, short takeaway. "
        "End with a soft comment CTA and Follow for more. "
        "Do not introduce yourself as Mike. Do not invent religious or political content.\n\n"
        "After the script, on new lines only:\n"
        "DEFINITION: one short sentence\n"
        "DIDYOUKNOW: one short sentence\n"
        "MOVES: question@0,talk@0.12,explain@0.35,point@0.55,present@0.8"
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/officialbonesceo/ghahnv-56565",
                "X-Title": "mike-tutor",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 380,
                "temperature": 0.35,
            },
            timeout=90,
        )
        if r.status_code != 200:
            print("openrouter status", r.status_code, r.text[:300], file=sys.stderr)
            return None
        choice = r.json().get("choices") or []
        if not choice:
            return None
        full = ((choice[0].get("message") or {}).get("content") or "").strip()
        if not full:
            return None
        moves_raw = definition = dyk = ""
        m = re.search(r"MOVES:\s*(.+)$", full, re.I | re.M)
        if m:
            moves_raw, full = m.group(1).strip(), full[: m.start()].strip()
        m = re.search(r"DEFINITION:\s*(.+)$", full, re.I | re.M)
        if m:
            definition, full = m.group(1).strip(), full[: m.start()].strip()
        m = re.search(r"DIDYOUKNOW:\s*(.+)$", full, re.I | re.M)
        if m:
            dyk, full = m.group(1).strip(), full[: m.start()].strip()
        return pack(topic, full, f"openrouter:{model}", moves_raw, definition, dyk)
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
        return None


def run_gguf(model: Path, topic: dict, engine_name: str):
    if not model.exists() or model.stat().st_size < 10_000_000:
        print("gguf missing or tiny", model, file=sys.stderr)
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    if not helper.exists():
        print("missing _llm_once.py", file=sys.stderr)
        return None
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    short = display_title(topic.get("title") or "")
    inp.write_text(
        json.dumps({
            "model": str(model),
            "title": short,
            "extract": (topic.get("extract") or "")[:400],
        }),
        encoding="utf-8",
    )
    if outp.exists():
        outp.unlink()
    try:
        r = subprocess.run(
            [sys.executable, str(helper), str(inp), str(outp)],
            timeout=360,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not outp.exists():
            print("gguf fail", r.stderr[:500] if r.stderr else r.stdout[:500], file=sys.stderr)
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        return pack(topic, data.get("body") or "", engine_name)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def main():
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
            result = run_gguf(Path(args.model), topic, "phi2-gguf")
        if result is None and args.model_fallback:
            result = run_gguf(Path(args.model_fallback), topic, "gguf-fallback")

    # NO template / seed fallback — fail the job
    if result is None:
        print("AI_SCRIPT_FAILED: no usable LLM script (OpenRouter + local)", file=sys.stderr)
        sys.exit(1)

    if result.get("engine", "").startswith("template"):
        print("REFUSING template engine", file=sys.stderr)
        sys.exit(1)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("moves.json").write_text(json.dumps(result.get("moves") or [], indent=2), encoding="utf-8")
    Path("title_short.txt").write_text(result["short_title"], encoding="utf-8")
    Path("definition.txt").write_text(result.get("definition") or "", encoding="utf-8")
    Path("did_you_know.txt").write_text(result.get("did_you_know") or "", encoding="utf-8")
    Path("cta.txt").write_text(result.get("cta") or "Comment what you understood.", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")
    first = result["script"].split(".")[0].strip()
    Path("hook.txt").write_text(first[:90], encoding="utf-8")
    short = result["short_title"]
    slug = re.sub(r"[^a-z0-9]+", "", short.lower())[:20] or "study"
    Path("tiktok_caption.txt").write_text(
        f"{short} — exam plain words\n\n{result.get('cta')}\nFollow for more\n\n"
        f"#{slug} #examtips #study #learntok #fyp #waec #jamb",
        encoding="utf-8",
    )
    print("ENGINE", result.get("engine"), "WORDS", len(result["script"].split()), file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
