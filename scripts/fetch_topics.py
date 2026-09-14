#!/usr/bin/env python3
"""Prefer trending study topics, else exam seed list; dedupe via seen_topics.json."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "MikeTutor/1.0 (educational)"}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"

SEED_TITLES = [
    "Photosynthesis",
    "Gravity",
    "Friction",
    "Electricity",
    "Electric current",
    "Voltage",
    "Circuit",
    "Atom",
    "Molecule",
    "DNA",
    "Osmosis",
    "Diffusion",
    "Evaporation",
    "Condensation",
    "Water cycle",
    "Respiration",
    "Enzyme",
    "Catalyst",
    "Acid",
    "Base (chemistry)",
    "pH",
    "Speed",
    "Velocity",
    "Acceleration",
    "Force",
    "Newton's laws of motion",
    "Work (physics)",
    "Energy",
    "Kinetic energy",
    "Potential energy",
    "Heat",
    "Temperature",
    "Sound",
    "Light",
    "Reflection (physics)",
    "Refraction",
    "Magnet",
    "Electromagnet",
    "Cell (biology)",
    "Mitosis",
    "Meiosis",
    "Blood",
    "Heart",
    "Lungs",
    "Brain",
    "Sleep",
    "Memory",
    "Vaccine",
    "Antibiotic",
    "Greenhouse effect",
    "Global warming",
    "Solar system",
    "Eclipse",
    "Moon",
    "Earth",
    "Earthquake",
    "Volcano",
    "Fossil",
    "Evolution",
    "Quadratic equation",
    "Pythagorean theorem",
    "Fraction",
    "Percentage",
    "Ratio",
    "Average",
    "Essay",
    "Paragraph",
]


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(title)
    seen.add(re.sub(r"\s*\([^)]*\)", "", title).strip().lower())
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen)[-800:], indent=2), encoding="utf-8")


def load_trends() -> list[str]:
    if not TREND_PATH.exists():
        return []
    try:
        data = json.loads(TREND_PATH.read_text(encoding="utf-8"))
        titles = data.get("titles") if isinstance(data, dict) else data
        if not isinstance(titles, list):
            return []
        return [str(t).strip() for t in titles if str(t).strip()]
    except Exception:
        return []


def summary(title: str) -> dict:
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
            if re.search(r"\b(crime|unlawful|disambiguation)\b", extract, re.I):
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


def build_pool(seen: set[str], seen_norm: set[str]) -> tuple[list[str], list[str]]:
    """Return (trend_pool, seed_pool) excluding seen."""
    trend_pool, seed_pool = [], []
    for t in load_trends():
        key = re.sub(r"\s*\([^)]*\)", "", t).strip().lower()
        if t in seen or key in seen_norm:
            continue
        trend_pool.append(t)
    for t in SEED_TITLES:
        key = re.sub(r"\s*\([^)]*\)", "", t).strip().lower()
        if t in seen or key in seen_norm:
            continue
        seed_pool.append(t)
    return trend_pool, seed_pool


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()
    seen_norm = {s.lower() for s in seen}

    trend_pool, seed_pool = build_pool(seen, seen_norm)
    # Prefer trends ~70% of the time when available
    if trend_pool and (not seed_pool or random.random() < 0.7):
        primary, source_tag = trend_pool, "trend"
    else:
        primary, source_tag = seed_pool or list(dict.fromkeys(SEED_TITLES)), "seed"

    if not primary:
        kept = sorted(seen)[-50:]
        seen = set(kept)
        primary = list(dict.fromkeys(SEED_TITLES))
        source_tag = "seed-reset"
        print("seen list soft-reset", file=sys.stderr)

    random.shuffle(primary)
    candidates = []
    for title in primary:
        s = summary(title)
        if s:
            s["trend"] = source_tag == "trend"
            s["topic_source"] = source_tag
            candidates.append(s)
        if len(candidates) >= 8:
            break

    # If trends failed to resolve on Wikipedia, fall back to seeds
    if not candidates and source_tag == "trend":
        print("trends unresolved, falling back to seeds", file=sys.stderr)
        random.shuffle(seed_pool or SEED_TITLES)
        for title in (seed_pool or SEED_TITLES):
            s = summary(title)
            if s:
                s["trend"] = False
                s["topic_source"] = "seed-fallback"
                candidates.append(s)
            if len(candidates) >= 8:
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
