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
    "Most students lose marks on {topic} — here is the clean version.",
    "Exam trap on {topic}? Fix it in under a minute.",
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
    """Build a short hook from a concrete fact/scene in the extract — not a static template."""
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
    words = t.split()
    if len(words) < 50:
        return ""
    if len(words) > 155:
        t = " ".join(words[:140])
        if "." in t:
            t = t[: t.rfind(".") + 1]
    if t and t[-1] not in ".!?":
        t = (t[: t.rfind(".") + 1] if "." in t else t + ".")
    return t


def short_definition(extract: str, title: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    for s in sents:
        s = s.strip()
        if 30 <= len(s) <= 140 and re.match(r"^[A-Z0-9]", s):
            return s[:140]
    return f"{title} is the process you must define clearly in the exam."


def distinct_dyk(extract: str, title: str, definition: str) -> str:
    tips = [
        f"Wait — always define {title} before you give an example in the exam.",
        f"Wait — examiners award marks for a clear definition of {title} first.",
        f"Wait — state what {title} is in one sentence, then support with an example.",
    ]
    def_norm = re.sub(r"[^a-z0-9]", "", (definition or "").lower())
    for s in re.split(r"(?<=[.!?])\s+", extract or ""):
        s = s.strip()
        if not (28 <= len(s) <= 130):
            continue
        sn = re.sub(r"[^a-z0-9]", "", s.lower())
        if def_norm and sn[:30] in def_norm:
            continue
        if not re.match(r"(?i)(wait|most|almost)", s):
            s = f"Wait — {s[0].lower()}{s[1:]}"
        return s[:130]
    return tips[len(title) % len(tips)][:130]


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
    """Keep AI scene hooks; repair weak openings using extract-based scenes."""
    s = script.strip()
    storyish = re.match(
        r"^(you |when you |pour |imagine |think of |a cold |cold water|your phone|on a bus|"
        r"the bottle|have you|notice how|watch what|ever notice|throw |walk |put |shout |"
        r"a bus |a green |lemon |one dead |same mass |a metal |a straw )",
        s, re.I,
    )
    if storyish:
        return re.sub(r"\s+", " ", s)
    soft = re.match(r"^(hey|hi|hello|welcome|i am mike|i'm mike|today we|let's talk|here is|learn )", s, re.I)
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


def ensure_cta(script: str, topic: str) -> str:
    s = script.rstrip(".! ")
    s = re.sub(r"(?i)comment yes[^.]*", "", s)
    s = re.sub(r"(?i)follow\s+mike\.the\.tutor[^.]*\.?", "", s)
    s = re.sub(r"(?i)\b(subscribe|like and|smash that)\b[^.]*\.?", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".! ")
    s = re.sub(
        r"(?i)(comment what you understood[^.]*|comment the next topic[^.]*|"
        r"comment one[^.]*|follow for more|tap the bookmark[^.]*|save this[^.]*|"
        r"share (it |this |with )[^.]*|bookmark[^.]*|share with a classmate[^.]*)[^.]*\.?",
        "", s,
    ).strip().rstrip(".! ")
    s += (
        ". Tap the bookmark to save this for revision. "
        "Share it with a classmate who needs the marks. "
        "Follow for daily lessons."
    )
    if not s.endswith((".", "!", "?")):
        s += "."
    return s


def has_real_life_example(script: str) -> bool:
    return bool(re.search(
        r"\b(for example|in real life|like when|think of|imagine|when you|"
        r"on the road|in the kitchen|your phone|your body|a ball|a car|"
        r"a bottle|cold water|pour |wet |bus |football|walking|cooking)\b",
        script, re.I,
    ))


def pack(topic, text, engine, moves_raw="", definition="", dyk="", phenomenon=False):
    short = display_title(topic.get("title") or "Lesson")
    extract = topic.get("extract") or ""
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    cleaned = force_hook(cleaned, short, phenomenon, extract)
    cleaned = ensure_cta(cleaned, short)
    if PROMPT_LEAK_RE.search(cleaned):
        print("PROMPT_LEAK after pack — reject", file=sys.stderr)
        return None
    if re.search(r"(?i)meet .+ in everyday", cleaned):
        print("VAGUE_EXAMPLE reject", file=sys.stderr)
        return None

    definition = (definition or "").strip()
    if not definition or INSTRUCTION_FIELD_RE.search(definition) or len(definition.split()) < 5:
        definition = short_definition(extract, short)
    definition = definition[:140]
    dyk_final = (dyk or "").strip()
    if not dyk_final or len(dyk_final) < 25 or INSTRUCTION_FIELD_RE.search(dyk_final) or PROMPT_LEAK_RE.search(dyk_final):
        dyk_final = distinct_dyk(extract, short, definition)
    if INSTRUCTION_FIELD_RE.search(dyk_final) or PROMPT_LEAK_RE.search(dyk_final):
        dyk_final = f"Wait — examiners award marks for a clear definition of {short} first."

    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk_final[:130],
        "cta": "Save · Share · Follow for daily lessons.",
        "script": cleaned,
        "moves": parse_moves(moves_raw, short),
        "bg": "classroom",
        "source": topic.get("url") or "",
        "engine": engine,
        "phenomenon_first": bool(phenomenon),
    }


def run_openrouter(topic: dict):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("openrouter: no API key", file=sys.stderr)
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:450]
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    phenom = wants_phenomenon(short)
    print("PHENOMENON_FIRST", phenom, short, file=sys.stderr)
    system = (
        "You write spoken TikTok voiceover for secondary school exam revision in West Africa style English. "
        "Sound like a sharp tutor, not a textbook. Short sentences. No filler. "
        "Stay strictly on the school topic. Never celebrity or biography. "
        "Open with a concrete everyday scene or exam trap from the facts — never a generic template line. "
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
            "Write 90-120 words.\nSTRUCTURE:\n"
            "1) INTRO: concrete everyday SCENE (bottle, bus, phone, kitchen, football). Max 2 short sentences.\n"
            "2) PUZZLE: why did that happen?\n"
            "3) NAME + plain definition.\n"
            "4) LINK scene to definition.\n"
            "5) EXAM tip.\n"
            "6) OUTRO: tap bookmark to save, share with a classmate, follow for daily lessons.\n"
        )
    else:
        structure = (
            "Write 85-115 words.\nSTRUCTURE:\n"
            "1) INTRO: concrete SCENE or exam trap for THIS topic only. Never generic.\n"
            "2) DEFINITION in plain words.\n"
            "3) EXAMPLE if a real school/home/lab scene fits.\n"
            "4) EXAM tip.\n"
            "5) OUTRO: tap bookmark to save, share with a classmate, follow for daily lessons.\n"
        )
    user = (
        f"Topic: {short}\nFacts from reliable source:\n{extract}\n\n{structure}"
        "Rules: no religion, no politics, no self-intro, no prompt language in the speech.\n\n"
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
        definition = dyk = moves_raw = ""
        m_def = re.search(r"(?im)^DEFINITION:\s*(.+)$", content)
        m_dyk = re.search(r"(?im)^DIDYOUKNOW:\s*(.+)$", content)
        m_mov = re.search(r"(?im)^MOVES:\s*(.+)$", content)
        if m_def:
            definition = m_def.group(1).strip()
        if m_dyk:
            dyk = m_dyk.group(1).strip()
        if m_mov:
            moves_raw = m_mov.group(1).strip()
        spoken = re.split(r"(?im)^(?:DEFINITION|DIDYOUKNOW|MOVES):", content)[0].strip()
        return pack(topic, spoken, f"openrouter:{model}", moves_raw, definition, dyk, phenom)
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
        return None


def run_gguf(model_path: Path, topic: dict, engine: str):
    if not model_path.exists():
        print("gguf missing", model_path, file=sys.stderr)
        return None
    short = display_title(topic.get("title") or "science")
    extract = (topic.get("extract") or "")[:400]
    phenom = wants_phenomenon(short)
    prompt = (
        f"Write a spoken secondary-school lesson on {short}. "
        f"Facts: {extract}\n"
        "Start with a concrete everyday scene from the facts. 80-120 words. "
        "End: save bookmark, share with classmate, follow.\n"
        "DEFINITION: one exam sentence\nDIDYOUKNOW: Wait — tip\n"
        "MOVES: question@0,talk@0.12,explain@0.35,point@0.55,present@0.8\n"
    )
    try:
        from llama_cpp import Llama
        llm = Llama(model_path=str(model_path), n_ctx=2048, verbose=False)
        out = llm(prompt, max_tokens=500, temperature=0.75, stop=["User:", "System:"])
        content = ((out.get("choices") or [{}])[0].get("text") or "").strip()
        if not content:
            return None
        definition = dyk = moves_raw = ""
        m_def = re.search(r"(?im)^DEFINITION:\s*(.+)$", content)
        m_dyk = re.search(r"(?im)^DIDYOUKNOW:\s*(.+)$", content)
        m_mov = re.search(r"(?im)^MOVES:\s*(.+)$", content)
        if m_def:
            definition = m_def.group(1).strip()
        if m_dyk:
            dyk = m_dyk.group(1).strip()
        if m_mov:
            moves_raw = m_mov.group(1).strip()
        spoken = re.split(r"(?im)^(?:DEFINITION|DIDYOUKNOW|MOVES):", content)[0].strip()
        return pack(topic, spoken, engine, moves_raw, definition, dyk, phenom)
    except Exception as e:
        print("gguf error", e, file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="topic.json")
    ap.add_argument("--model", default="")
    ap.add_argument("--try-llm", action="store_true")
    ap.add_argument("--out", default="script_job.json")
    args = ap.parse_args()

    topic = json.loads(Path(args.topic).read_text(encoding="utf-8"))
    result = None
    if args.try_llm:
        result = run_openrouter(topic)
        if result is None and args.model:
            result = run_gguf(Path(args.model), topic, "phi2-gguf")
    if result is None:
        print("SCRIPT_FAIL: AI engines failed — refusing template fallback", file=sys.stderr)
        sys.exit(1)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    script = (result.get("script") or "").strip()
    Path("script.txt").write_text(script + ("\n" if script else ""), encoding="utf-8")
    short = result.get("short_title") or result.get("title") or "Lesson"
    Path("title_short.txt").write_text(short + "\n", encoding="utf-8")
    Path("moves.json").write_text(json.dumps(result.get("moves") or [], indent=2), encoding="utf-8")
    hook_line = (script.split(".")[0] + ".") if script else "Lesson."
    Path("hook.txt").write_text(hook_line + "\n", encoding="utf-8")
    caption = (
        f"{short}\n\n"
        f"Save this for revision \U0001f516\n"
        f"Share with a classmate \u2197\ufe0f\n"
        f"Follow for daily lessons\n\n"
        f"#learntok #examprep #fyp #waec #jamb #science"
    )
    Path("tiktok_caption.txt").write_text(caption, encoding="utf-8")
    Path("tiktok_comment.txt").write_text(
        f"Bookmark to revise {short} later. What topic next?",
        encoding="utf-8",
    )
    print("ENGINE", result.get("engine"), file=sys.stderr)
    print("PHENOMENON", result.get("phenomenon_first"), file=sys.stderr)
    print("DYK", result.get("did_you_know"), file=sys.stderr)
    print("WROTE script.txt", len(script.split()), "words", file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
