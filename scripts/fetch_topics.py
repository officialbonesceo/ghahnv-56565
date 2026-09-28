#!/usr/bin/env python3
"""School STEM topics from trends/wiki only — no hardcoded lesson fallback."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import is_school_safe, filter_title_list

UA = {"User-Agent": "MikeTutor/1.0 (educational)"}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"
SEED_TOPIC_PATH = ROOT / "data" / "seed_topic.json"

HARD_BLOCK = {
    "petroleumrefining", "petroleumref", "fractionaldistillation",
    "fractionaldistil", "dangoterefinery", "oilrefinery", "oilrefining",
    "mithraism", "osmosisjones", "mitsubishi", "kotonemitsuishi",
}

SYLLABUS_POOL = [
    "Gravity", "Friction", "Electric current", "Voltage", "Circuit",
    "Osmosis", "Diffusion", "Evaporation", "Condensation", "Respiration",
    "Enzyme", "Catalyst", "Speed", "Velocity", "Acceleration", "Force",
    "Newton's laws of motion", "Kinetic energy", "Potential energy",
    "Heat", "Temperature", "Sound", "Light", "Reflection (physics)",
    "Refraction", "Electromagnet", "Mitosis", "Meiosis", "DNA",
    "Quadratic equation", "Pythagorean theorem", "Fraction", "Percentage",
    "Inertia", "Momentum", "Pressure", "Density", "Ohm's law",
    "Photosynthesis", "Essay", "Paragraph",
]


def norm_key(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)", "", title or "")
    t = re.sub(r"[^a-z0-9]+", "", t.lower())
    return t


def is_hard_blocked(title: str) -> bool:
    k = norm_key(title)
    if k in HARD_BLOCK:
        return True
    for b in HARD_BLOCK:
        if len(b) >= 8 and (b in k or k in b):
            return True
    if "petroleum" in k or "refiner" in k or "dangote" in k:
        return True
    return False


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        raw = data if isinstance(data, list) else data.get("titles", [])
        out = set()
        for x in raw:
            out.add(str(x))
            out.add(norm_key(str(x)))
            nk = norm_key(str(x))
            if len(nk) >= 12:
                out.add(nk[:12])
        return out
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(title)
    seen.add(norm_key(title))
    nk = norm_key(title)
    if len(nk) >= 12:
        seen.add(nk[:12])
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    titles = sorted({s for s in seen if s and len(str(s)) > 2})[-1200:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def is_seen(seen: set[str], title: str) -> bool:
    if is_hard_blocked(title):
        return True
    k = norm_key(title)
    if title in seen or k in seen:
        return True
    if len(k) >= 12 and k[:12] in seen:
        return True
    for s in seen:
        sk = norm_key(s) if any(c.isalpha() for c in str(s)) else str(s)
        if len(k) >= 8 and len(sk) >= 8:
            if k == sk or k.startswith(sk) or sk.startswith(k):
                return True
            if abs(len(k) - len(sk)) <= 4 and (k[:8] == sk[:8]):
                return True
    return False


def load_trends() -> list[str]:
    if not TREND_PATH.exists():
        return []
    try:
        data = json.loads(TREND_PATH.read_text(encoding="utf-8"))
        titles = data.get("titles") if isinstance(data, dict) else data
        if not isinstance(titles, list):
            return []
        return filter_title_list([str(t).strip() for t in titles if str(t).strip()])
    except Exception:
        return []


def try_seed_topic(seen: set[str]) -> dict | None:
    if not SEED_TOPIC_PATH.exists():
        return None
    try:
        data = json.loads(SEED_TOPIC_PATH.read_text(encoding="utf-8"))
        if data.get("disabled"):
            return None
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or len(extract) < 80:
            return None
        if is_hard_blocked(title) or is_seen(seen, title):
            SEED_TOPIC_PATH.write_text(
                json.dumps({"disabled": True, "note": f"blocked/seen: {title}"}, indent=2),
                encoding="utf-8",
            )
            return None
        if not is_school_safe(title, extract):
            return None
        data.setdefault("bg", "classroom")
        data["topic_source"] = "seed"
        SEED_TOPIC_PATH.write_text(
            json.dumps({"disabled": True, "used_title": title, "note": "consumed"}, indent=2),
            encoding="utf-8",
        )
        print("USING_SEED once", title, file=sys.stderr)
        return data
    except Exception as e:
        print("seed load fail", e, file=sys.stderr)
        return None


def summary(title: str) -> dict:
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    slug = title.replace(" ", "_")
    for base in (
        "https://simple.wikipedia.org/api/rest_v1/page/summary/",
        "https://en.wikipedia.org/api/rest_v1/page/summary/",
    ):
        try:
            r = requests.get(base + requests.utils.quote(slug), headers=UA, timeout=25)
            r.raise_for_status()
            data = r.json()
            if data.get("type") == "disambiguation":
                continue
            extract = (data.get("extract") or "").strip()
            if len(extract) < 100:
                continue
            got = data.get("title") or title
            if is_hard_blocked(got) or not is_school_safe(got, extract):
                continue
            return {
                "title": got,
                "extract": extract[:650],
                "description": data.get("description") or "",
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "bg": "classroom",
                "trend": False,
            }
        except Exception:
            continue
    return {}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()

    seeded = try_seed_topic(seen)
    if seeded:
        save_seen(seen, seeded["title"])
        out.write_text(json.dumps(seeded, indent=2), encoding="utf-8")
        print("TOPIC_SOURCE seed", seeded.get("title"), file=sys.stderr)
        print(json.dumps(seeded, indent=2))
        return

    trends = load_trends()
    primary = [t for t in trends if not is_seen(seen, t) and not is_hard_blocked(t)]
    source_tag = "trend"

    if not primary:
        hard_keys = set(HARD_BLOCK)
        kept = [s for s in sorted(seen) if is_hard_blocked(str(s))][:80]
        seen = set(kept) | hard_keys
        primary = [t for t in trends if not is_seen(seen, t)]
        if not primary:
            primary = [t for t in SYLLABUS_POOL if not is_seen(seen, t) and is_school_safe(t)]
            source_tag = "syllabus"
        else:
            source_tag = "trend-reset"
        print("pool rebuild", source_tag, len(primary), file=sys.stderr)

    if not primary:
        print("TOPIC_FAIL: no school topics available after trends+syllabus", file=sys.stderr)
        sys.exit(1)

    random.shuffle(primary)
    candidates = []
    for title in primary:
        if is_seen(seen, title) or is_hard_blocked(title):
            continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]) and not is_hard_blocked(s["title"]):
            if not is_school_safe(s["title"], s.get("extract") or ""):
                continue
            s["trend"] = source_tag.startswith("trend")
            s["topic_source"] = source_tag
            candidates.append(s)
        if len(candidates) >= 8:
            break

    if not candidates:
        print("TOPIC_FAIL: Wikipedia returned no safe school extracts", file=sys.stderr)
        sys.exit(1)

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
