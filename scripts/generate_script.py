#!/usr/bin/env python3
"""Student Shorts: strong hook, one idea, teach-only moves, soft CTAs."""
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

# Teach-only — no walk_left / walk_right
VALID_MOVES = {
    "talk", "welcome", "point", "sit", "present", "question", "happy",
}

HOOK_TEMPLATES = [
    "Stop. Most students get {topic} wrong.",
    "Why does {topic} actually matter in exams?",
    "Can you explain {topic} in one sentence?",
    "Here is {topic} in plain words — no fluff.",
    "You need {topic} more than you think. Here is what it is.",
    "Quick test: what is {topic}?",
    "This is the simplest way to understand {topic}.",
]

CTA_ENDINGS = [
    "Comment what you understood.",
    "Comment the next topic you want.",
    "Comment your subject if you want this series.",
    "Comment one thing you learned.",
]


def display_title(title: str) -> str:
    t = title or "Science"
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    return t[:40]


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"\([^)]{0,80}\)", " ", t)
    t = re.sub(r"Instruct:.*", " ", t, flags=re.I | re.S)
    t = re.sub(r"MOVES:.*", " ", t, flags=re.I | re.S)
    t = re.sub(r"DEFINITION:.*", " ", t, flags=re.I | re.S)
    t = re.sub(r"DIDYOUKNOW:.*", " ", t, flags=re.I | re.S)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"###.*?\n"]:
        t = re.sub(p, " ", t, flags=re.I | re.S)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(
        r"^(group of|gas that|and then|so that|into the)\b[^.]*\.\s*",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(r"^(hey[, ]+)?(i am|i'm) mike[.!]?\s*", "", t, flags=re.I)
    t = re.sub(r"^today (on the board|we (learn|talk) about)[:\s]+", "", t, flags=re.I)
    # strip old CTAs if model still writes them
    t = re.sub(r"comment yes[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"follow\s+mike\.the\.tutor[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"follow\s+@?mike[^.]*\.?", "", t, flags=re.I)
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
            if not re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
                return s[:120]
    return f"{title} is a simple idea you can explain in everyday words."


def did_you_know_line(extract: str, title: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    for s in sents[1:]:
        s = s.strip()
        if 30 <= len(s) <= 120 and re.match(r"^[A-Z0-9]", s):
            return s[:110]
    return f"Most students have heard of {title}, but few can explain it clearly."


def default_moves(topic: str) -> list[dict]:
    """Teach gestures only — no side-walk."""
    return [
        {"at": 0.00, "move": "question"},
        {"at": 0.12, "move": "talk"},
        {"at": 0.28, "move": "point"},
        {"at": 0.45, "move": "talk"},
        {"at": 0.62, "move": "happy"},
        {"at": 0.78, "move": "present"},
        {"at": 0.90, "move": "talk"},
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
            # map old walk to talk
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


def pick_sentences(extract: str) -> list[str]:
    parts = []
    for s in re.split(r"(?<=[.!?])\s+", extract or ""):
        s = s.strip()
        if len(s) < 35 or not re.match(r"^[A-Z0-9]", s):
            continue
        if re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
            continue
        parts.append(s)
    return parts[:4]


def force_hook(script: str, topic: str) -> str:
    s = script.strip()
    soft = re.match(
        r"^(hey|hi|hello|welcome|i am mike|i'm mike|today we|let's talk)",
        s,
        re.I,
    )
    if soft or len(s.split(".")[0].split()) > 18:
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)
        rest = s
        if "." in s:
            first, _, after = s.partition(".")
            if re.match(r"^(hey|hi|hello|i am|i'm|today)", first.strip(), re.I):
                rest = after.strip()
        s = f"{hook} {rest}".strip()
    return re.sub(r"\s+", " ", s)


def ensure_cta(script: str, topic: str) -> str:
    s = script.rstrip(".! ")
    low = s.lower()
    # remove old patterns
    s = re.sub(r"(?i)comment yes[^.]*", "", s)
    s = re.sub(r"(?i)follow\s+(mike\.the\.tutor|@?mike\.the\.tutor)[^.]*", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".! ")
    cta = random.choice(CTA_ENDINGS)
    if "comment" not in low:
        s += f". {cta}"
    if "follow" not in s.lower():
        s += " Follow for more."
    if not s.endswith((".", "!", "?")):
        s += "."
    return s


def template_scripts(topic: dict) -> dict:
    short = display_title(topic.get("title") or "this idea")
    extract = topic.get("extract") or ""
    sents = pick_sentences(extract)
    while len(sents) < 2:
        sents.append(f"You can explain {short} with one clear example.")
    definition = short_definition(extract, short)
    dyk = did_you_know_line(extract, short)
    fact = sents[0]
    if len(fact) > 110:
        fact = fact[:107].rsplit(" ", 1)[0] + "."
    hook = random.choice(HOOK_TEMPLATES).format(topic=short)
    cta = random.choice(CTA_ENDINGS)
    script = (
        f"{hook} "
        f"Here is the definition: {definition} "
        f"Remember this: {fact} "
        f"Did you know? {dyk} "
        f"So now you can explain {short} in plain words. "
        f"{cta} Follow for more."
    )
    script = re.sub(r"\s+", " ", script).strip()
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk,
        "cta": cta,
        "script": script,
        "moves": default_moves(short),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template-student",
    }


def pack(
    topic: dict,
    text: str,
    engine: str,
    moves_raw: str = "",
    definition: str = "",
    dyk: str = "",
) -> dict | None:
    short = display_title(topic.get("title") or "Lesson")
    extract = topic.get("extract") or ""
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    cleaned = force_hook(cleaned, short)
    cleaned = ensure_cta(cleaned, short)
    if re.match(r"^(group of|gas that|of space)\b", cleaned, re.I):
        return None
    definition = (definition or short_definition(extract, short))[:120]
    dyk = (dyk or did_you_know_line(extract, short))[:110]
    cta = random.choice(CTA_ENDINGS)
    moves = parse_moves(moves_raw, short)
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk,
        "cta": cta,
        "script": cleaned,
        "moves": moves,
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
        "You write TikTok student science Shorts.\n"
        "RULES:\n"
        "1. FIRST SENTENCE = strong hook (question or bold claim). "
        "Never start with Hey, Hi, I am Mike, or Today we learn.\n"
        "2. One idea: definition → one fact → Did you know → takeaway.\n"
        "3. 75 to 105 spoken words.\n"
        "4. Simple words for secondary school students.\n"
        "5. End with ONE of: Comment what you understood. "
        "OR Comment the next topic you want. Then: Follow for more.\n"
        "Never say mike.the.tutor. Never say Comment YES or part 2.\n"
        f"Topic: {short}\nFacts: {extract}\n\n"
        "After the script write:\n"
        "DEFINITION: under 18 words\n"
        "DIDYOUKNOW: under 22 words\n"
        "MOVES: question@0,talk@0.15,point@0.32,talk@0.5,happy@0.68,present@0.85\n"
        "Allowed moves only: talk,welcome,point,sit,present,question,happy\n"
        "Do NOT use walk_left or walk_right."
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
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 380,
                "temperature": 0.4,
            },
            timeout=90,
        )
        print("openrouter", r.status_code, model, file=sys.stderr)
        if r.status_code != 200:
            print(r.text[:300], file=sys.stderr)
            return None
        choice = r.json().get("choices") or []
        if not choice:
            return None
        msg = choice[0].get("message") or {}
        full = (msg.get("content") or "").strip()
        if not full:
            return None
        moves_raw = definition = dyk = ""
        m = re.search(r"MOVES:\s*(.+)$", full, re.I | re.M)
        if m:
            moves_raw = m.group(1).strip()
            full = full[: m.start()].strip()
        m = re.search(r"DEFINITION:\s*(.+)$", full, re.I | re.M)
        if m:
            definition = m.group(1).strip()
            full = full[: m.start()].strip()
        m = re.search(r"DIDYOUKNOW:\s*(.+)$", full, re.I | re.M)
        if m:
            dyk = m.group(1).strip()
            full = full[: m.start()].strip()
        return pack(
            topic, full, f"openrouter:{r.json().get('model') or model}",
            moves_raw, definition, dyk,
        )
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
            timeout=360, capture_output=True, text=True,
        )
        if r.returncode != 0 or not outp.exists():
            return None
        data = json.loads(outp.read_text(encoding="utf-8"))
        return pack(topic, data.get("body") or "", engine_name)
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
            result = run_gguf(Path(args.model), topic, "phi2-gguf")
        if result is None and args.model_fallback:
            result = run_gguf(Path(args.model_fallback), topic, "gguf-fallback")
    if result is None:
        result = template_scripts(topic)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("moves.json").write_text(json.dumps(result.get("moves") or [], indent=2), encoding="utf-8")
    Path("title_short.txt").write_text(result["short_title"], encoding="utf-8")
    Path("definition.txt").write_text(result.get("definition") or "", encoding="utf-8")
    Path("did_you_know.txt").write_text(result.get("did_you_know") or "", encoding="utf-8")
    Path("cta.txt").write_text(result.get("cta") or "Comment what you understood.", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")

    short = result["short_title"]
    slug = re.sub(r"[^a-z0-9]+", "", short.lower())[:20] or "science"
    caption = (
        f"{short} explained simply\n\n"
        f"{result.get('cta') or 'Comment what you understood.'}\n"
        f"Follow for more\n\n"
        f"#{slug} #learntok #study #fyp #stem #examtips #didyouknow"
    )
    Path("tiktok_caption.txt").write_text(caption, encoding="utf-8")
    Path("tiktok_comment.txt").write_text(
        f"What should we explain next after {short}?",
        encoding="utf-8",
    )
    print("ENGINE", result.get("engine"), "WORDS", len(result["script"].split()), file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
