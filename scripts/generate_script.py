#!/usr/bin/env python3
"""AI scripts: Gemini-first, then OpenRouter. No template fallback."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
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
    r"output only the spoken|write a spoken script|"
    r"STRUCTURE:\s*\d|Rules:\s*no religion)"
)

# OpenRouter free tier is unstable; keep a short list only
FREE_MODELS = [
    "openrouter/free",
    "google/gemma-3-4b-it:free",
    "meta-llama/llama-3.3-8b-instruct:free",
]

# Current Gemini API model ids (as of 2026-11 API messages)
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
]


def gemini_api_key() -> str:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_AI_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
    ):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


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
        (r"heat|temper|conduct|latent", "A metal spoon in hot tea burns your hand first — conduction."),
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


def strip_meta_blocks(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    t = re.split(
        r"(?im)^\s*(MOVES|DEFINITION|DIDYOUKNOW|INSTRUCT|SYSTEM|EXAMPLE|PHENOMENON|STRUCTURE)\s*:",
        t,
    )[0]
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"(?im)^#{1,3}\s+.*$", " ", t)
    for lab in ("MOVES", "DEFINITION", "DIDYOUKNOW", "EXAMPLE", "PHENOMENON"):
        t = re.sub(rf"{lab}:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"Instruct:.*", " ", t, flags=re.I | re.S)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"SCRIPT:\s*"]:
        t = re.sub(p, " ", t, flags=re.I)
    return t


def clean_spoken(text: str) -> str:
    t = strip_meta_blocks(text)
    if PROMPT_LEAK_RE.search(t):
        print("PROMPT_LEAK detected — rejecting", file=sys.stderr)
        print("LEAK_SNIP", t[:180], file=sys.stderr)
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
    if not cleaned:
        print("PACK_FAIL empty after clean", file=sys.stderr)
        return None
    if len(cleaned.split()) < 60:
        print("PACK_FAIL too_short", len(cleaned.split()), cleaned[:120], file=sys.stderr)
        return None
    if is_weak_script(cleaned, topic):
        print("WEAK_SCRIPT reject", is_weak_script(cleaned, topic), file=sys.stderr)
        return None
    cleaned = force_hook(cleaned, topic, phenom, extract)
    if is_weak_script(cleaned, topic):
        print("WEAK after force_hook", is_weak_script(cleaned, topic), file=sys.stderr)
        return None
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
        "engine": "ai",
    }


def build_prompts(short: str, extract: str) -> tuple[str, str, bool]:
    phenom = wants_phenomenon(short)
    multi = is_multipart(short, extract)
    print("PHENOMENON_FIRST", phenom, short, file=sys.stderr)
    print("MULTI_PART", multi, short, file=sys.stderr)
    system = (
        "You are Mike, a secondary-school science tutor for West African exams. "
        "Write ONLY the spoken voiceover paragraphs a student hears. "
        "Short energetic sentences. One everyday example. One clear definition. "
        "Open with a concrete scene or exam trap, never a generic greeting. "
        "No celebrity, religion, politics, or prompt instructions in the speech."
    )
    if multi:
        structure = (
            "Write 120-150 spoken words covering EACH part of the topic. "
            "Scene intro, then each part with definition + example, exam tip, short save/share outro."
        )
    elif phenom:
        structure = (
            "Write 95-125 spoken words. "
            "Everyday scene, why it happens, name + plain definition, link scene to science, exam tip, short outro."
        )
    else:
        structure = (
            "Write 90-120 spoken words. "
            "Scene or exam trap, plain definition, everyday example, quick check, exam tip, short outro."
        )
    user = (
        f"Topic: {short}\nFacts:\n{extract}\n\n{structure}\n"
        "After the spoken paragraphs, add exactly these three lines:\n"
        "DEFINITION: one exam-ready sentence under 16 words\n"
        "DIDYOUKNOW: Wait — one exam tip under 18 words\n"
        "MOVES: question@0,talk@0.12,explain@0.35,point@0.55,present@0.8"
    )
    return system, user, phenom


def _call_gemini(key: str, model: str, system: str, user: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 700,
        },
    }
    r = requests.post(url, json=body, timeout=90)
    if r.status_code >= 400:
        print("gemini HTTP", model, r.status_code, r.text[:320], file=sys.stderr)
        return ""
    data = r.json()
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    content = "".join((p.get("text") or "") for p in parts).strip()
    if not content:
        fr = ((data.get("candidates") or [{}])[0].get("finishReason") or "")
        print("gemini empty", model, "finish", fr, file=sys.stderr)
    return content


def try_gemini(topic: str, extract: str, short: str) -> dict | None:
    key = gemini_api_key()
    if not key:
        print("no GEMINI_API_KEY (also checked GOOGLE_API_KEY)", file=sys.stderr)
        return None
    if is_synthetic_extract(extract):
        print("SYNTHETIC_EXTRACT reject — refusing empty-fact topic", file=sys.stderr)
        return None
    system, user, phenom = build_prompts(short, extract)
    preferred = os.environ.get("GEMINI_MODEL", "").strip()
    models = ([preferred] if preferred else []) + [m for m in GEMINI_MODELS if m != preferred]
    for model in models:
        for attempt in range(2):
            try:
                print("GEMINI_TRY", model, "attempt", attempt + 1, file=sys.stderr)
                content = _call_gemini(key, model, system, user)
                if not content:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                packed = pack_script(content, topic, extract, phenom)
                if packed:
                    packed["engine"] = f"gemini:{model}"
                    print("GEMINI_OK", model, file=sys.stderr)
                    return packed
                print("GEMINI_PACK_FAIL", model, "raw_head", content[:160].replace("\n", " "), file=sys.stderr)
            except Exception as e:
                print("gemini fail", model, e, file=sys.stderr)
            time.sleep(0.5 * (attempt + 1))
    return None


def _call_openrouter(key: str, model: str, system: str, user: str) -> str:
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
            "temperature": 0.7,
            "max_tokens": 700,
        },
        timeout=90,
    )
    if r.status_code >= 400:
        print("openrouter HTTP", model, r.status_code, r.text[:280], file=sys.stderr)
        return ""
    content = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if not content:
        print("openrouter empty", model, file=sys.stderr)
    return content


def try_openrouter(topic: str, extract: str, short: str) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("no OPENROUTER_API_KEY", file=sys.stderr)
        return None
    if is_synthetic_extract(extract):
        print("SYNTHETIC_EXTRACT reject — refusing empty-fact topic", file=sys.stderr)
        return None
    preferred = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    models = [preferred] + [m for m in FREE_MODELS if m != preferred]
    system, user, phenom = build_prompts(short, extract)
    for model in models:
        for attempt in range(2):
            try:
                print("OR_TRY", model, "attempt", attempt + 1, file=sys.stderr)
                content = _call_openrouter(key, model, system, user)
                if not content:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                packed = pack_script(content, topic, extract, phenom)
                if packed:
                    packed["engine"] = f"openrouter:{model}"
                    print("OR_OK", model, file=sys.stderr)
                    return packed
                print("OR_PACK_FAIL", model, "raw_head", content[:160].replace("\n", " "), file=sys.stderr)
            except Exception as e:
                print("openrouter fail", model, e, file=sys.stderr)
            time.sleep(0.6 * (attempt + 1))
    return None


def try_llm(topic: str, extract: str, short: str) -> dict | None:
    result = try_gemini(topic, extract, short)
    if result:
        return result
    return try_openrouter(topic, extract, short)


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
    print("TOPIC", short, "extract_src", topic_data.get("extract_source"), "extract_len", len(extract), file=sys.stderr)
    result = None
    if args.try_llm:
        result = try_llm(title, extract, short)
    if not result:
        print("SCRIPT_FAIL: AI engines failed — refusing template fallback", file=sys.stderr)
        sys.exit(1)
    result["title"] = title
    result["extract"] = extract[:400]
    result["bg"] = topic_data.get("bg") or "classroom"
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text((result.get("script") or "").strip() + "\n", encoding="utf-8")
    print(result.get("engine"), result.get("short_title"), len(result.get("script", "").split()), "words", file=sys.stderr)
    print(result.get("script", "")[:240], file=sys.stderr)
    print("DYK", result.get("did_you_know"), file=sys.stderr)
    print("DEF", result.get("definition"), file=sys.stderr)


if __name__ == "__main__":
    main()
