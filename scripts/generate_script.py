#!/usr/bin/env python3
"""AI scripts: phenomenon-first when possible, real-life examples, fail if AI fails."""
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

PHENOMENON_OK = re.compile(
    r"\b("
    r"condens|evaporat|friction|inertia|gravity|force|pressure|density|"
    r"buoyanc|osmosis|diffusion|static|electric|magnet|circuit|ohm|"
    r"heat|temperat|sound|light|reflect|refract|photosynth|respirat|"
    r"enzyme|catalyst|acid|base|momentum|kinetic|potential|surface tension|"
    r"capillar|latent|specific heat|electromagnet|induction|stomata|"
    r"chlorophyll|weather|climate|atmosphere|volcano|earthquake"
    r")\b",
    re.I,
)

PHENOMENON_SKIP = re.compile(
    r"\b(essay|paragraph|quadratic|fraction|percentage|ratio|average|"
    r"pythagorean|algebra|equation|mitosis|meiosis|dna|genetics|heredity)\b",
    re.I,
)

HOOK_TEMPLATES = [
    "Exam question on {topic}? Most students freeze here.",
    "This is the {topic} mistake that costs easy marks.",
    "If {topic} still confuses you, fix it in under a minute.",
    "Teachers love trapping you on {topic}. Here is the clean version.",
    "Write this definition of {topic} and keep the marks.",
]

CTA_ENDINGS = [
    "Comment what you understood in one line.",
    "Comment the next topic you want.",
    "Comment one exam tip you will use.",
]

PROMPT_LEAK_RE = re.compile(
    r"(?is)("
    r"tiktok for secondary|before exams\.?\s*\d\."
    r"|first line must|no hey/?hi|definition\s*→|exam-useful fact"
    r"|75-?110 words|never say mike\.the\.tutor|comment yes"
    r"|after script:|moves:\s*question@|moves:\s*talk,"
    r"|instruct:|system:|user:|assistant:|you are a helpful"
    r"|write a script|output only|real-life example required"
    r"|topic:\s*\w+\s*facts:|didyouknow must|phenomenon-first"
    r")"
)


def display_title(title: str) -> str:
    t = title or "Science"
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    t = re.sub(r"^\d{4}(-\d{2})?\s*", "", t).strip() or title
    return t[:40]


def wants_phenomenon(title: str) -> bool:
    t = title or ""
    if PHENOMENON_SKIP.search(t):
        return False
    if PHENOMENON_OK.search(t):
        return True
    return bool(re.search(
        r"\b(physics|chemistry|biology|energy|motion|water|cell|blood|heart|lung)\b",
        t, re.I,
    ))


def clean_spoken(text: str) -> str:
    t = (text or "").strip().strip('"').strip("'")
    t = re.split(
        r"(?im)^\s*(MOVES|DEFINITION|DIDYOUKNOW|INSTRUCT|SYSTEM|EXAMPLE|PHENOMENON)\s*:",
        t,
    )[0]
    t = re.sub(r"\*\*[^*]+\*\*", " ", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"(?im)^#{1,3}\s+.*$", " ", t)
    t = re.sub(r"MOVES:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"DEFINITION:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"DIDYOUKNOW:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"EXAMPLE:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"PHENOMENON:\s*.+$", " ", t, flags=re.I | re.M)
    t = re.sub(r"Instruct:.*", " ", t, flags=re.I | re.S)
    for p in [r"INTRO:\s*", r"BODY:\s*", r"SCRIPT:\s*"]:
        t = re.sub(p, " ", t, flags=re.I)
    if PROMPT_LEAK_RE.search(t):
        print("PROMPT_LEAK detected — rejecting", file=sys.stderr)
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(hey[, ]+)?(i am|i'm) mike[.!]?\s*", "", t, flags=re.I)
    t = re.sub(r"comment yes[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"follow\s+mike\.the\.tutor[^.]*\.?", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    words = t.split()
    if len(words) < 50:
        return ""
    if len(words) > 130:
        t = " ".join(words[:115])
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
        words = s.split()
        if 8 <= len(words) <= 22 and re.match(r"^[A-Z0-9]", s):
            return s[:110]
    for s in sents:
        s = s.strip()
        if 30 <= len(s) <= 120 and re.match(r"^[A-Z0-9]", s):
            return s[:110]
    return f"{title} is an exam idea you must define in one clear sentence."


def distinct_dyk(extract: str, title: str, definition: str) -> str:
    def_norm = re.sub(r"[^a-z0-9]", "", (definition or "").lower())
    sents = re.split(r"(?<=[.!?])\s+", extract or "")
    candidates = []
    for s in sents:
        s = s.strip()
        if not (28 <= len(s) <= 115 and re.match(r"^[A-Z0-9]", s)):
            continue
        sn = re.sub(r"[^a-z0-9]", "", s.lower())
        if def_norm and (sn[:40] == def_norm[:40] or def_norm[:30] in sn or sn[:30] in def_norm):
            continue
        if re.search(r"\b(is a|are a|refers to|defined as)\b", s, re.I) and len(s) < 70:
            continue
        candidates.append(s)
    if candidates:
        pick = candidates[1] if len(candidates) > 1 else candidates[0]
        if not re.match(r"(?i)(wait|most|almost|few|students|exam|never|only)", pick):
            pick = f"Wait — {pick[0].lower()}{pick[1:]}"
        return pick[:120]
    return f"Wait — exams often ask for one real example of {title}, not only the definition."


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


def force_hook(script: str, topic: str, phenomenon: bool) -> str:
    s = script.strip()
    if phenomenon:
        storyish = re.match(
            r"^(you |when you |pour |imagine |think of |a cold |cold water|your phone|on a bus|"
            r"the bottle|have you|notice how|watch what)",
            s, re.I,
        )
        if storyish:
            return re.sub(r"\s+", " ", s)
    soft = re.match(
        r"^(hey|hi|hello|welcome|i am mike|i'm mike|today we|let's talk|here is)",
        s, re.I,
    )
    first = s.split(".")[0] if "." in s else s
    weak = soft or len(first.split()) > 18 or not re.search(
        r"\b(exam|mark|test|student|wrong|confus|trick|before|stop|pour|bottle|"
        r"phone|bus|cold|wet|slide|lurch|freeze|mistake)\b",
        first, re.I,
    )
    if weak and not phenomenon:
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
    s = re.sub(r"(?i)follow\s+(mike\.the\.tutor|@?mike\.the\.tutor|for more)[^.]*\.?", "", s)
    s = re.sub(r"(?i)\bfollow for more\b\.?", "", s)
    s = re.sub(r"(?i)\b(subscribe|like and|smash that)\b[^.]*\.?", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".! ")
    cta = random.choice(CTA_ENDINGS)
    s = re.sub(
        r"(?i)(comment what you understood[^.]*|comment the next topic[^.]*|comment one[^.]*\.)\s*$",
        "",
        s,
    ).strip().rstrip(".! ")
    s += f". {cta}"
    if not s.endswith((".", "!", "?")):
        s += "."
    return s


def has_real_life_example(script: str) -> bool:
    return bool(re.search(
        r"\b(for example|in real life|like when|think of|imagine|when you|"
        r"on the road|in the kitchen|your phone|your body|a ball|a car|"
        r"a bottle|cold water|pour |wet |bus |football|walking|cooking)\b",
        script,
        re.I,
    ))


def pack(topic, text, engine, moves_raw="", definition="", dyk="", phenomenon=False):
    short = display_title(topic.get("title") or "Lesson")
    extract = topic.get("extract") or ""
    cleaned = clean_spoken(text)
    if not cleaned:
        return None
    cleaned = force_hook(cleaned, short, phenomenon)
    cleaned = ensure_cta(cleaned, short)
    if PROMPT_LEAK_RE.search(cleaned):
        print("PROMPT_LEAK after pack — reject", file=sys.stderr)
        return None
    if not has_real_life_example(cleaned) and not phenomenon:
        print("WARN no concrete example in script", file=sys.stderr)

    definition = (definition or short_definition(extract, short)).strip()[:120]
    dyk_final = (dyk or "").strip()
    if not dyk_final or len(dyk_final) < 25:
        dyk_final = distinct_dyk(extract, short, definition)
    else:
        dn = re.sub(r"[^a-z0-9]", "", definition.lower())
        yn = re.sub(r"[^a-z0-9]", "", dyk_final.lower())
        if dn and (yn[:35] == dn[:35] or dn[:25] in yn):
            dyk_final = distinct_dyk(extract, short, definition)
        elif not re.match(r"(?i)(wait|most|almost|few|students|never|only)", dyk_final):
            dyk_final = f"Wait — {dyk_final[0].lower()}{dyk_final[1:]}"

    return {
        "title": topic.get("title") or short,
        "short_title": short,
        "definition": definition,
        "did_you_know": dyk_final[:120],
        "cta": "Comment what you understood in one line.",
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
        "Return ONLY the spoken paragraphs — never list rules inside the voiceover."
    )
    if phenom:
        structure = (
            "Write 90-120 words.\n"
            "STRUCTURE:\n"
            "1) INTRO: one concrete everyday SCENE (bottle, bus, phone, kitchen, football). Max 2 short sentences.\n"
            "2) PUZZLE: one question — why did that happen?\n"
            "3) NAME + plain definition of the topic (one sentence students can write in an exam).\n"
            "4) LINK: connect the scene to the definition in one sentence.\n"
            "5) EXAM tip: one line on how to answer it in a test.\n"
            "6) OUTRO: exactly one line — Comment what you understood in one line.\n"
            "Do NOT say Follow, subscribe, like, or any username.\n"
        )
    else:
        structure = (
            "Write 85-115 words.\n"
            "STRUCTURE:\n"
            "1) INTRO: exam-pain hook (marks lost / common confusion). One short sentence.\n"
            "2) DEFINITION: plain words, one clear sentence.\n"
            "3) EXAMPLE: one specific real scene (not generic). If none fits, skip example.\n"
            "4) EXAM tip: how to use this on a paper.\n"
            "5) OUTRO: exactly — Comment what you understood in one line.\n"
            "Do NOT say Follow, subscribe, like, or any username.\n"
        )

    user = (
        f"Topic: {short}\nFacts from reliable source:\n{extract}\n\n"
        f"{structure}"
        "Rules: no religion, no politics, no self-intro, no prompt language in the speech.\n\n"
        "After the spoken script, on separate lines ONLY:\n"
        "DEFINITION: formal exam-ready sentence under 18 words for the board\n"
        "DIDYOUKNOW: one surprising fact NOT the same as the definition, under 20 words, start with Wait —\n"
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
                "max_tokens": 450,
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
        return pack(
            topic, full, f"openrouter:{model}", moves_raw, definition, dyk, phenom
        )
    except Exception as e:
        print("openrouter error", e, file=sys.stderr)
        return None


def run_gguf(model: Path, topic: dict, engine_name: str):
    if not model.exists() or model.stat().st_size < 10_000_000:
        return None
    helper = Path(__file__).resolve().parent / "_llm_once.py"
    if not helper.exists():
        return None
    inp, outp = Path("/tmp/llm_in.json"), Path("/tmp/llm_out.json")
    short = display_title(topic.get("title") or "")
    phenom = wants_phenomenon(short)
    inp.write_text(json.dumps({
        "model": str(model),
        "title": short,
        "extract": (topic.get("extract") or "")[:400],
        "phenomenon": phenom,
    }), encoding="utf-8")
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
        return pack(topic, data.get("body") or "", engine_name, phenomenon=phenom)
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

    if result is None:
        print("AI_SCRIPT_FAILED: no usable LLM script", file=sys.stderr)
        sys.exit(1)
    if result.get("engine", "").startswith("template"):
        print("REFUSING template engine", file=sys.stderr)
        sys.exit(1)
    if PROMPT_LEAK_RE.search(result.get("script") or ""):
        print("PROMPT_LEAK in final script", file=sys.stderr)
        sys.exit(1)

    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path("script.txt").write_text(result["script"] + "\n", encoding="utf-8")
    Path("moves.json").write_text(json.dumps(result.get("moves") or [], indent=2), encoding="utf-8")
    Path("title_short.txt").write_text(result["short_title"], encoding="utf-8")
    Path("definition.txt").write_text(result.get("definition") or "", encoding="utf-8")
    Path("did_you_know.txt").write_text(result.get("did_you_know") or "", encoding="utf-8")
    Path("cta.txt").write_text(
        result.get("cta") or "Comment what you understood in one line.", encoding="utf-8"
    )
    Path("bg.txt").write_text("classroom", encoding="utf-8")
    Path("phenomenon.txt").write_text(
        "1" if result.get("phenomenon_first") else "0", encoding="utf-8"
    )
    first = result["script"].split(".")[0].strip()
    Path("hook.txt").write_text(first[:90], encoding="utf-8")
    short = result["short_title"]
    slug = re.sub(r"[^a-z0-9]+", "", short.lower())[:20] or "study"
    Path("tiktok_caption.txt").write_text(
        f"{short} — exam plain words\n\n{result.get('cta')}\n\n"
        f"#{slug} #examtips #study #learntok #fyp #waec #jamb",
        encoding="utf-8",
    )
    print("ENGINE", result.get("engine"), "WORDS", len(result["script"].split()), file=sys.stderr)
    print("PHENOMENON", result.get("phenomenon_first"), file=sys.stderr)
    print("DYK", result.get("did_you_know"), file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
