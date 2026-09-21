#!/usr/bin/env python3
"""School STEM topics with strong dedupe + optional seed."""
from __future__ import annotations

import hashlib
import json
import os
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

SEED_TITLES = [
    "Photosynthesis", "Gravity", "Friction", "Electricity", "Electric current",
    "Voltage", "Circuit", "Atom", "Molecule", "DNA", "Osmosis", "Diffusion",
    "Evaporation", "Condensation", "Water cycle", "Respiration", "Enzyme",
    "Catalyst", "Acid", "Base (chemistry)", "pH", "Speed", "Velocity",
    "Acceleration", "Force", "Newton's laws of motion", "Work (physics)",
    "Energy", "Kinetic energy", "Potential energy", "Heat", "Temperature",
    "Sound", "Light", "Reflection (physics)", "Refraction", "Magnet",
    "Electromagnet", "Cell (biology)", "Mitosis", "Meiosis", "Blood",
    "Heart", "Lungs", "Brain", "Sleep", "Memory", "Vaccine", "Antibiotic",
    "Greenhouse effect", "Global warming", "Solar system", "Eclipse",
    "Moon", "Earth", "Earthquake", "Volcano", "Fossil", "Evolution",
    "Quadratic equation", "Pythagorean theorem", "Fraction", "Percentage",
    "Ratio", "Average", "Essay", "Paragraph", "Petroleum refining",
    "Fractional distillation", "Supply and demand",
]


def norm_key(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)", "", title or "")
    t = re.sub(r"[^a-z0-9]+", "", t.lower())
    return t


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
        return out
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(title)
    seen.add(norm_key(title))
    # also store stemmed-ish short form
    seen.add(norm_key(title)[:12])
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    # keep readable titles + keys, last 1000
    titles = sorted({s for s in seen if s and not s.isalnum() or len(s) > 3})[-1000:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def is_seen(seen: set[str], title: str) -> bool:
    k = norm_key(title)
    if title in seen or k in seen:
        return True
    if k[:12] in seen:
        return True
    # fuzzy: any seen key that shares long prefix
    for s in seen:
        sk = norm_key(s) if not s.isalnum() else s
        if len(k) >= 6 and len(sk) >= 6 and (k.startswith(sk[:6]) or sk.startswith(k[:6])):
            if k == sk or abs(len(k) - len(sk)) <= 3:
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


def try_seed_topic() -> dict | None:
    if not SEED_TOPIC_PATH.exists():
        return None
    try:
        data = json.loads(SEED_TOPIC_PATH.read_text(encoding="utf-8"))
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or len(extract) < 80:
            return None
        if not is_school_safe(title, extract):
            return None
        data.setdefault("bg", "classroom")
        data["topic_source"] = data.get("topic_source") or "seed"
        data["trend"] = bool(data.get("trend", True))
        used = SEED_TOPIC_PATH.with_name("seed_topic.used.json")
        SEED_TOPIC_PATH.replace(used)
        print("USING_SEED", title, file=sys.stderr)
        return data
    except Exception as e:
        print("seed load fail", e, file=sys.stderr)
        return None


def summary(title: str) -> dict:
    if not is_school_safe(title):
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
            if not is_school_safe(data.get("title") or title, extract):
                continue
            return {
                "title": data.get("title") or title,
                "extract": extract[:650],
                "description": data.get("description") or "",
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "bg": "classroom",
                "trend": False,
            }
        except Exception:
            continue
    return {}


def build_pool(seen: set[str]) -> tuple[list[str], list[str]]:
    trend_pool, seed_pool = [], []
    for t in load_trends():
        if is_seen(seen, t) or not is_school_safe(t):
            continue
        trend_pool.append(t)
    for t in SEED_TITLES:
        if is_seen(seen, t):
            continue
        seed_pool.append(t)
    return trend_pool, seed_pool


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")

    seeded = try_seed_topic()
    if seeded:
        seen = load_seen()
        save_seen(seen, seeded["title"])
        out.write_text(json.dumps(seeded, indent=2), encoding="utf-8")
        print("TOPIC_SOURCE seed", seeded.get("title"), file=sys.stderr)
        print(json.dumps(seeded, indent=2))
        return

    seen = load_seen()
    trend_pool, seed_pool = build_pool(seen)
    if trend_pool and (not seed_pool or random.random() < 0.7):
        primary, source_tag = trend_pool, "trend"
    else:
        primary, source_tag = seed_pool or list(dict.fromkeys(SEED_TITLES)), "seed"

    if not primary:
        # soft reset only last 40 kept as block
        kept = [s for s in sorted(seen) if len(s) > 12][-40:]
        seen = set(kept)
        for k in list(kept):
            seen.add(norm_key(k))
        primary = [t for t in SEED_TITLES if not is_seen(seen, t)] or list(SEED_TITLES)
        source_tag = "seed-reset"
        print("seen soft-reset", file=sys.stderr)

    random.shuffle(primary)
    candidates = []
    for title in primary:
        if is_seen(seen, title):
            continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]):
            s["trend"] = source_tag == "trend"
            s["topic_source"] = source_tag
            candidates.append(s)
        if len(candidates) >= 8:
            break

    if not candidates:
        for title in SEED_TITLES:
            if is_seen(seen, title):
                continue
            s = summary(title)
            if s:
                s["topic_source"] = "seed-fallback"
                candidates.append(s)
            if len(candidates) >= 5:
                break

    if not candidates:
        candidates = [{
            "title": "Friction",
            "extract": (
                "Friction is a force that slows things down when two surfaces rub. "
                "Students meet it in almost every motion question in exams."
            ),
            "description": "physics",
            "url": "",
            "bg": "classroom",
            "trend": False,
            "topic_source": "hardcoded",
        }]

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
