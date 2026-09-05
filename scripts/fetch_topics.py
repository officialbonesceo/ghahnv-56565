#!/usr/bin/env python3
"""Prefer clear science topics; avoid disambiguation / crime pages."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "QxilPipe/1.0 (educational)"}
SEEN_PATH = Path(__file__).resolve().parents[1] / "data" / "seen_topics.json"

SEED_TITLES = [
    "Electric battery",
    "Rainbow",
    "Gravity",
    "Photosynthesis",
    "Lightning",
    "Magnet",
    "Echo",
    "Tide",
    "Cloud",
    "Sound",
    "Heat",
    "Moon",
    "Sun",
    "DNA",
    "Internet",
    "Earthquake",
    "Volcano",
    "Oxygen",
    "Sleep",
    "Photosynthesis",
    "Evaporation",
    "Friction",
    "Reflection (physics)",
    "Static electricity",
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
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen)[-500:], indent=2), encoding="utf-8")


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
                "extract": extract[:700],
                "description": data.get("description") or "",
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "bg": "classroom",
            }
        except Exception:
            continue
    return {}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()
    pool = [t for t in SEED_TITLES if t not in seen] or list(SEED_TITLES)
    random.shuffle(pool)
    candidates = []
    for title in pool:
        s = summary(title)
        if s:
            candidates.append(s)
        if len(candidates) >= 6:
            break
    if not candidates:
        candidates = [{
            "title": "Rainbow",
            "extract": (
                "A rainbow is a colorful arc in the sky made when sunlight hits raindrops. "
                "Each drop bends light and splits it into colors we can see from the ground."
            ),
            "description": "light in the sky",
            "url": "",
            "bg": "classroom",
        }]
    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
