#!/usr/bin/env python3
"""AI scripts: phenomenon-first when possible, real-life examples, fail if AI fails."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

import requests

from script_quality import is_weak_script, is_synthetic_extract

from tts_speech_fix import speakable_numbers, is_boring_step_dump, strip_step_intro

VALID_MOVES = {
    "talk", "welcome", "point", "sit", "present", "question", "happy",
    "explain", "shrug", "count", "think", "lean",
}

PHENOMENON_OK = re.compile(
    r"\b(condens|evaporat|friction|inertia|gravity|force|pressure|density|"
    r"buoyanc|osmosis|diffusion|static|electric|magnet|circuit|ohm|"
    r"heat|temperat|sound|light|reflect|refract|photosynth|respirat|"
    r"enzyme|catalyst|acid|base|momentum|kinetic|potential|surface tension|"
    r"capillar|latent|specific heat|electromagnet|induction|stomata|"
    r"chlorophyll|weather|climate|atmosphere|volcano|earthquake)\b",
    re.I,
)
PHENOMENON_SKIP = re.compile(
    r"\b(essay|paragraph|quadratic|fraction|percentage|ratio|average|"
    r"pythagorean|algebra|equation|mitosis|meiosis|dna|genetics|heredity)\b",
    re.I,
)

EMERGENCY_HOOKS = [
    "Quick challenge: can you explain {topic} in one clear sentence before the board does?",
    "Think about it — what really happens with {topic} when you try it in real life?",
    "Most students lose marks on {topic} — here is the version that sticks.",
    "Stop scrolling: one clean take on {topic} that actually helps in class.",
    "If the exam asked for {topic} right now, would your first sentence land?",
]

PROMPT_LEAK_RE = re.compile(
    r"(?is)(tiktok for secondary|spoken tiktok voiceover|voiceover for secondary|"
    r"west africa style english|sharp tutor,? not a textbook|"
    r"stay strictly on the school topic|return only the spoken|"
    r"never list rules inside|thinking process:\s*\d|"
    r"write a script|output only|write the definition of|write this definition of|"
    r"labelled example|for the board|under \d+ words)"
)
INSTRUCTION_FIELD_RE = re.compile(
    r"(?is)(plain words,? one clear|students can write|under \d+ words|"
    r"exam-ready sentence|for the board|structure:|thinking process|"
    r"write the definition|write this definition|labelled example|return only)"
)

def display_title(title: str) -> str:
    t = title or "Science"
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    t = re.sub(r"(?i)^(how\s+)?", "", t).strip()
    t = re.sub(r"(?i)^(basics?|introduction|types?|importance|applications?|properties|laws?)\s+(of\s+)?", "", t).strip()
    t = re.sub(r"(?i)^(ss[123]|jss)\s+", "", t).strip()
    t = re.sub(r"(?i)^(physics|chemistry|biology|mathematics)\s+", "", t).strip()
    t = re.sub(r"(?i)\s+(for\s+(waec|jamb|secondary\s+school)|in\s+everyday\s+life|formula|process|experiment|calculation|works)$", "", t).strip()
    return (t or title)[:40]

def scene_hook_from_extract(topic: str, extract: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    concrete = re.compile(
        r"\b(when|if|for example|such as|like|because|causes|makes|moves|flows|"
        r"ball|car|bus|phone|water|bottle|kitchen|road|football|body|heart|plant|"
        r"metal|wire|light|sound|heat|cold|rain|sun|earth|moon)\b",
        re.I,
    )
    for s in sents:
        s = s.strip()
        words = s.split()
        if not (8 <= len(words) <= 22):
            continue
        if not concrete.search(s):
            continue
        core = s.rstrip(".! ")
        if re.match(r"(?i)^(when|if|imagine|think|pour|notice)", core):
            return core + "?"
        return f"Ever notice this? {core}."
    t = (topic or "").lower()
    micro = [
        (r"veloc|speed|motion|acceler", "Throw a ball — speed alone is not enough. Direction matters too."),
        (r"force|newton|inertia", "A bus brakes hard and you lurch forward — that is inertia."),
        (r"friction", "Walk on a wet floor and you almost slip — friction just dropped."),
        (r"photosynth", "A green leaf in sunlight is a quiet food factory."),
        (r"osmos|diffus", "Put salt on a cucumber slice and water is pulled out — that is osmosis."),
        (r"circuit|ohm|current|voltage", "One dead bulb can kill a whole string of lights — series circuit."),
        (r"acid|base|ph", "Lemon juice tastes sharp for a reason — acids free hydrogen ions."),
        (r"cell|mitos|meios", "Your body replaces skin cells every day — mitosis at work."),
        (r"grav|weight|mass", "Same mass on the Moon feels lighter — gravity changed, mass did not."),
        (r"heat|temper|conduct", "A metal spoon in hot tea burns your hand first — conduction."),
        (r"reflect|refract|light|lens", "A straw in water looks bent — light changes speed."),
        (r"sound|echo|wave", "Shout at a wall and the sound comes back — that is an echo."),
        (r"essay|paragraph|grammar", "Examiners mark structure first — messy paragraphs lose easy points."),
        (r"fraction|percent|ratio|algebra|equation", "One wrong step in the working can wipe the whole method mark."),
    ]
    for pat, line in micro:
        if re.search(pat, t):
            return line
    return ""

def is_multipart(title: str, extract: str = "") -> bool:
    blob = f"{title or ''} {extract or ''}"
    return bool(re.search(
        r"(?i)\b(newton.?s?\s+laws?|kinetic\s+and\s+potential|conduction|convection|radiation|"
        r"plant\s+cell|animal\s+cell|active\s+voice|passive\s+voice|series\s+circuit|parallel\s+circuit|"
        r"types?\s+of|kinds?\s+of|versus|\bvs\.?\b|two\s+types|three\s+laws)\b",
        blob,
    ))

def wants_phenomenon(title: str) -> bool:
    t = title or ""
    if PHENOMENON_SKIP.search(t):
        return False
    if PHENOMENON_OK.search(t):
        return True
    return bool(re.search(r"\b(physics|chemistry|biology|energy|motion|water|cell|blood|heart|lung)\b", t, re.I))

def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    t = re.split(r"(?im)^\s*(MOVES|DEFINITION|DIDYOUKNOW|INSTRUCT|SYSTEM|EXAMPLE|PHENOMENON)\s*:", t)[0]
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"(?im)^#{1,3}\s+.*$", " ", t)
    for lab in ("MOVES", "DEFINITION", "DIDYOUKNOW", "EXAMPLE", "PHENOMENON"):
        t = re.sub(rf"{lab}:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"Instruct:.*", " ", t, flags=re.I | re.S)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"SCRIPT:\s*"]:
        t = re.sub(p, " ", t, flags=re.I)
    if PROMPT_LEAK_RE.search(t):
        print("PROMPT_LEAK detected — rejecting", file=sys.stderr)
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(hey[, ]+)?(i am|i'm) mike[.!]?\s*", "", t, flags=re.I)
    t = speakable_numbers(t)
    if is_boring_step_dump(t):
        print("STEP_DUMP reject", file=sys.stderr)
        return ""
    return t

def default_moves(topic: str) -> list:
    return [
        {"at": 0.00, "move": "question"}, {"at": 0.12, "move": "talk"},
        {"at": 0.35, "move": "explain"}, {"at": 0.55, "move": "point"},
        {"at": 0.78, "move": "present"}, {"at": 0.92, "move": "happy"},
    ]

def parse_moves(raw: str, topic: str) -> list:
    if not raw:
        return default_moves(topic)
    out = []
    for part in re.split(r"[,;|\n]+", raw.replace("→", " ").replace("->", " ")):
        part = part.strip().strip("-•*").strip()
        m = re.match(r"([a-z_]+)\s*[@:]\s*(0?\.\d+|1\.0?|0|1)\b", part, re.I)
        if m:
            move, at = m.group(1).lower(), float(m.group(2))
            if move in ("walk_left", "walk_right"):
                move = "talk"
            if move in VALID_MOVES:
                out.append({"at": max(0.0, min(1.0, at)), "move": move})
    if len(out) < 2:
        return default_moves(topic)
    out.sort(key=lambda x: x["at"])
    if out[0]["at"] > 0.05:
        out.insert(0, {"at": 0.0, "move": "question"})
    return out

def force_hook(script: str, topic: str, phenomenon: bool, extract: str = "") -> str:
    s = strip_step_intro(script.strip())
    storyish = re.match(
        r"^(you |when you |pour |imagine |think of |a cold |cold water|your phone|on a bus|"
        r"the bottle|have you|notice how|watch what|ever notice|throw |walk |put |shout |"
        r"a bus |a green |lemon |one dead |same mass |a metal |a straw )",
        s, re.I,
    )
    if storyish:
        return re.sub(r"\s+", " ", s)
    soft = re.match(r"^(hey|hi|hello|welcome|i am mike|i'm mike|today we|let's talk|here is|learn |steps? to|here are|follow these|the steps)", s, re.I)
    first = s.split(".")[0] if "." in s else s
    weak = soft or len(first.split()) > 20 or not re.search(
        r"\b(exam|mark|test|student|wrong|confus|trick|pour|bottle|phone|bus|cold|"
        r"notice|throw|ball|light|water|heat|force|cell|circuit)\b", first, re.I,
    )
    if not weak:
        return re.sub(r"\s+", " ", s)
    hook = scene_hook_from_extract(topic, extract) or random.choice(EMERGENCY_HOOKS).format(topic=topic)
    rest = s
    if "." in s:
        first_s, _, after = s.partition(".")
        if re.match(r"^(hey|hi|hello|i am|i'm|today|here is|stop|learn)", first_s.strip(), re.I):
            rest = after.strip()
    return re.sub(r"\s+", " ", f"{hook} {rest}".strip())

def pack_script(raw: str, topic: str, extract: str, phenom: bool) -> dict | None:
    cleaned = clean_spoken(raw)
    if not cleaned or len(cleaned.split()) < 60:
        return None
    if is_weak_script(cleaned, topic):
        print("WEAK_SCRIPT reject", is_weak_script(cleaned, topic), file=sys.stderr)
        return None
    cleaned = force_hook(cleaned, topic, phenom, extract)
    if is_weak_script(cleaned, topic):
        print("WEAK after force_hook", is_weak_script(cleaned, topic), file=sys.stderr)
        return None
    # Extract DEFINITION / DIDYOUKNOW / MOVES if present in raw
    def_match = re.search(r"(?im)^DEFINITION:\s*(.+)$", raw)
    dyk_match = re.search(r"(?im)^DIDYOUKNOW:\s*(.+)$", raw)
    moves_match = re.search(r"(?im)^MOVES:\s*(.+)$", raw)
    definition = (def_match.group(1).strip() if def_match else "")[:120]
    dyk = (dyk_match.group(1).strip() if dyk_match else "")[:130]
    moves = parse_moves(moves_match.group(1) if moves_match else "", topic)
    if not definition or len(definition.split()) < 4:
        definition = f"{display_title(topic)} is a core secondary school concept with clear everyday examples."
    if not dyk or len(dyk) < 20:
        dyk = f"Wait — mastering {display_title(topic)} unlocks related exam questions fast."
    return {
        "script": cleaned,
        "definition": definition,
        "did_you_know": dyk,
        "moves": moves,
        "short_title": display_title(topic),
        "engine": "openrouter",
    }

def try_openrouter(topic: str, extract: str, short: str) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("no OPENROUTER_API_KEY", file=sys.stderr)
        return None
    if is_synthetic_extract(extract):
        print("SYNTHETIC_EXTRACT reject — refusing empty-fact topic", file=sys.stderr)
        return None
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    phenom = wants_phenomenon(short)
    print("PHENOMENON_FIRST", phenom, short, file=sys.stderr)
    system = (
        "You write spoken TikTok voiceover for secondary school exam revision in West Africa style English. "
        "Sound like a sharp, energetic tutor who challenges the student — not a textbook. Short sentences. No filler. "
        "Stay strictly on the school topic. Never celebrity or biography. "
        "Open with a concrete everyday scene, a quick challenge question, or a sharp exam trap from the facts — never a generic template line. "
        "After the main point, insert one short interactive beat: 'Think about it...' or 'Can you say it back?' then give the clean answer. "
        "Never open with Steps to answering. Never dump long numbered checklists. At most two ordered points as Number one, Number two. "
        "Must include one concrete everyday example and a clear plain-language definition. Never pad with only exam-name drops or Save/Share without teaching. "
        "Return ONLY the spoken paragraphs — never list rules inside the voiceover."
    )
    multi = is_multipart(short, extract)
    print("MULTI_PART", multi, short, file=sys.stderr)
    if multi:
        structure = (
            "Write 120-150 words. Cover EACH part of the topic.\nSTRUCTURE:\n"
            "1) INTRO: concrete SCENE or exam trap tied to THIS topic. One short sentence. Never a generic template.\n"
            "2) PART A: name, definition, everyday example.\n"
            "3) PART B: name, definition, everyday example.\n"
            "4) Optional third part briefly.\n"
            "5) EXAM tip.\n"
            "6) OUTRO: tap bookmark to save, share with a classmate, follow for daily lessons.\n"
        )
    elif phenom:
        structure = (
            "Write 95-125 words.\nSTRUCTURE:\n"
            "1) INTRO: concrete everyday SCENE or quick challenge question (bottle, bus, phone, kitchen, football). Max 2 short sentences.\n"
            "2) PUZZLE or 'Think about it' beat: why did that happen? Pause feel.\n"
            "3) NAME + plain definition.\n"
            "4) LINK scene to definition with one clear example.\n"
            "5) EXAM tip or quick check ('Say it back: ...').\n"
            "6) OUTRO: tap bookmark to save, share with a classmate, follow for daily lessons.\n"
        )
    else:
        structure = (
            "Write 90-120 words.\nSTRUCTURE:\n"
            "1) INTRO: concrete SCENE, challenge, or exam trap for THIS topic only. Never generic.\n"
            "2) DEFINITION in plain words.\n"
            "3) EXAMPLE if a real school/home/lab scene fits.\n"
            "4) Quick check: 'Think about it...' or 'Can you explain it in one line?' then clean answer.\n"
            "5) EXAM tip.\n"
            "6) OUTRO: tap bookmark to save, share with a classmate, follow for daily lessons.\n"
        )
    user = (
        f"Topic: {short}\nFacts from reliable source:\n{extract}\n\n{structure}"
        "Rules: no religion, no politics, no self-intro, no prompt language in the speech. "
        "NEVER write 1. 2. 3. lists — TTS says one-dot. Say Number one, Number two, max two points. "
        "NEVER open with Steps to answering. Open with a scene or exam trap.\n\n"
        "After the spoken script, on separate lines ONLY:\n"
        "DEFINITION: formal exam-ready sentence under 16 words for the board\n"
        "DIDYOUKNOW: one exam tip fact NOT the same as the definition, under 18 words, start with Wait —\n"
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
                "temperature": 0.75,
                "max_tokens": 700,
            },
            timeout=90,
        )
        if r.status_code >= 400:
            print("openrouter HTTP", r.status_code, r.text[:300], file=sys.stderr)
            return None
        content = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return None
        return pack_script(content, topic, extract, phenom)
    except Exception as e:
        print("openrouter fail", e, file=sys.stderr)
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--try-llm", action="store_true")
    ap.add_argument("--out", default="script_job.json")
    args = ap.parse_args()
    topic_data = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    title = topic_data.get("title") or "Science"
    extract = topic_data.get("extract") or ""
    short = display_title(title)
    result = None
    if args.try_llm:
        result = try_openrouter(title, extract, short)
    if not result:
        print("SCRIPT_FAIL: AI engines failed — refusing template fallback", file=sys.stderr)
        sys.exit(1)
    result["title"] = title
    result["extract"] = extract[:400]
    result["bg"] = topic_data.get("bg") or "classroom"
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result.get("engine"), result.get("short_title"), len(result.get("script", "").split()), "words", file=sys.stderr)
    print(result.get("script", "")[:240], file=sys.stderr)
    print("DYK", result.get("did_you_know"), file=sys.stderr)
    print("DEF", result.get("definition"), file=sys.stderr)

if __name__ == "__main__":
    main()
