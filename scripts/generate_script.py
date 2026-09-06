#!/usr/bin/env python3
"""Script + moves + definition + did-you-know + CTA for TikTok retention."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

VALID_MOVES = {
    "talk", "welcome", "walk_left", "walk_right",
    "point", "sit", "present", "question", "happy",
}


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
    words = t.split()
    if len(words) < 55:
        return ""
    if len(words) > 150:
        t = " ".join(words[:140])
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
        if 40 <= len(s) <= 160 and re.match(r"^[A-Z0-9]", s):
            if not re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
                return s[:140]
    return f"{title} is a key idea you can explain in simple words."


def did_you_know_line(extract: str, title: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    for s in sents[1:]:
        s = s.strip()
        if 35 <= len(s) <= 140 and re.match(r"^[A-Z0-9]", s):
            return s[:130]
    return f"Most people hear about {title}, but few can explain it clearly."


def default_moves(topic: str) -> list[dict]:
    t = (topic or "").lower()
    plan = [
        {"at": 0.00, "move": "welcome"},
        {"at": 0.10, "move": "talk"},
        {"at": 0.25, "move": "walk_left"},
        {"at": 0.38, "move": "point"},
        {"at": 0.52, "move": "question"},
        {"at": 0.68, "move": "sit"},
        {"at": 0.82, "move": "present"},
    ]
    if re.search(r"space|star|planet|solar|moon|galaxy", t):
        plan[3] = {"at": 0.38, "move": "point"}
    return plan


def parse_moves(raw: str, topic: str) -> list[dict]:
    if not raw:
        return default_moves(topic)
    out = []
    for part in re.split(r"[,;\n]+", raw):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"([a-z_]+)\s*[@:]\s*(0(?:\.\d+)?|1(?:\.0)?)", part, re.I)
        if m:
            move = m.group(1).lower()
            at = float(m.group(2))
            if move in VALID_MOVES:
                out.append({"at": at, "move": move})
    if len(out) < 2:
        return default_moves(topic)
    out.sort(key=lambda x: x["at"])
    return out


def pick_sentences(extract: str) -> list[str]:
    parts = []
    for s in re.split(r"(?<=[.!?])\s+", extract or ""):
        s = s.strip()
        if len(s) < 40 or not re.match(r"^[A-Z0-9]", s):
            continue
        if re.search(r"\b(crime|unlawful|disambiguation)\b", s, re.I):
            continue
        parts.append(s)
    return parts[:5]


def template_scripts(topic: dict) -> dict:
    short = display_title(topic.get("title") or "this idea")
    extract = topic.get("extract") or ""
    sents = pick_sentences(extract)
    while len(sents) < 4:
        sents.append(f"Everyday examples help you remember {short}.")
    facts = [s if len(s) <= 120 else s[:117].rsplit(" ", 1)[0] + "." for s in sents[:4]]
    definition = short_definition(extract, short)
    dyk = did_you_know_line(extract, short)
    script = (
        f"Hey, I am Mike. Today on the board: {short}. "
        f"Definition: {definition} "
        f"Here is the big idea. {facts[0]} "
        f"Did you know? {dyk} "
        f"Also important. {facts[2]} "
        f"So now you can explain {short} in plain words. "
        f"Comment YES for part 2. Follow mike.the.tutor. See you soon!"
    )
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk,
        "cta": "Comment YES for part 2",
        "script": re.sub(r"\s+", " ", script).strip(),
        "moves": default_moves(short),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": "template",
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
    if short.lower() not in cleaned.lower():
        cleaned = f"Hey, I am Mike. Today we learn about {short}. " + cleaned
    if "comment yes" not in cleaned.lower() and "part 2" not in cleaned.lower():
        cleaned = cleaned.rstrip(".!") + ". Comment YES for part 2."
    if "mike.the.tutor" not in cleaned.lower():
        cleaned = cleaned.rstrip(".!") + " Follow mike.the.tutor!"
    if re.match(r"^(group of|gas that|of space)\b", cleaned, re.I):
        return None
    definition = (definition or short_definition(extract, short))[:140]
    dyk = (dyk or did_you_know_line(extract, short))[:130]
    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk,
        "cta": "Comment YES for part 2",
        "script": cleaned,
        "moves": parse_moves(moves_raw, short),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
    }


def run_openrouter(topic: dict) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:450]
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    prompt = (
        "You are Mike, TikTok science tutor (@mike.the.tutor).\n"
        "Write 110-140 spoken words. Hook in first sentence. Include one Did you know fact.\n"
        "End with: Comment YES for part 2. Follow mike.the.tutor.\n"
        f"Topic: {short}\nFacts: {extract}\n\n"
        "After the script write these lines exactly:\n"
        "DEFINITION: one short plain definition under 20 words\n"
        "DIDYOUKNOW: one surprising fact under 25 words\n"
        "MOVES: welcome@0,talk@0.12,walk_left@0.28,point@0.4,question@0.55,sit@0.7,present@0.85\n"
        "Allowed moves: welcome,talk,walk_left,walk_right,point,sit,present,question,happy"
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
                "max_tokens": 420,
                "temperature": 0.35,
            },
            timeout=90,
        )
        print("openrouter", r.status_code, model, file=sys.stderr)
        if r.status_code != 200:
            print(r.text[:300], file=sys.stderr)
            return None
        full = r.json()["choices"][0]["message"]["content"].strip()
        moves_raw = definition = dyk = ""
        m = re.search(r"MOVES:\s*(.+)$", full, re.I | re.M)
        if m:
            moves_raw = m.group(1)
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
    Path("cta.txt").write_text(result.get("cta") or "Comment YES for part 2", encoding="utf-8")
    Path("bg.txt").write_text("classroom", encoding="utf-8")

    short = result["short_title"]
    slug = re.sub(r"[^a-z0-9]+", "", short.lower())[:24] or "science"
    caption = (
        f"{short} explained simply — Mike the Tutor\n\n"
        f"Comment YES for part 2\nFollow @mike.the.tutor\n\n"
        f"#{slug} #learntok #science #fyp #stem #studytok #didyouknow #mikethetutor"
    )
    Path("tiktok_caption.txt").write_text(caption, encoding="utf-8")
    Path("tiktok_comment.txt").write_text(
        f"Comment YES if you want part 2 on {short}", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
