#!/usr/bin/env python3
"""Fresh topics: Simple English Wikipedia + curated science categories. Skip seen."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "QxilPipe/1.0 (educational)"}
SEEN_PATH = Path(__file__).resolve().parents[1] / "data" / "seen_topics.json"

# Prefer topics that make good short explainers (avoid obscure jargon pages)
CATEGORIES = [
    "Category:Basic_concepts_in_physics",
    "Category:Introductory_astronomy",
    "Category:Human_physiology",
    "Category:Basic_meteorological_concepts",
    "Category:Optics",
    "Category:Water",
    "Category:Energy",
]

# Hard allow-list style seeds mixed in for quality
SEED_TITLES = [
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
    "Vaccine",
    "Internet",
    "Battery",
    "Earthquake",
    "Volcano",
    "Oxygen",
    "Sleep",
]


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else data.get("titles", []))
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(title)
    items = sorted(seen)[-500:]
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def wiki_get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params or {}, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def summary_simple(title: str) -> dict:
    """Prefer Simple English Wikipedia for clearer extracts."""
    slug = title.replace(" ", "_")
    for base in (
        "https://simple.wikipedia.org/api/rest_v1/page/summary/",
        "https://en.wikipedia.org/api/rest_v1/page/summary/",
    ):
        try:
            data = wiki_get(base + requests.utils.quote(slug))
            extract = (data.get("extract") or "").strip()
            if len(extract) < 90:
                continue
            return {
                "title": data.get("title") or title,
                "extract": extract[:700],
                "description": data.get("description") or "",
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
        except Exception:
            continue
    return {}


def members(cat: str, limit: int = 20) -> list[str]:
    data = wiki_get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmtype": "page",
            "cmlimit": limit,
            "format": "json",
        },
    )
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def guess_bg(title: str, extract: str) -> str:
    return "classroom"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()
    candidates: list[dict] = []

    pool = list(SEED_TITLES)
    random.shuffle(CATEGORIES)
    for cat in CATEGORIES[:3]:
        try:
            pool.extend(members(cat, 12))
        except Exception as e:
            print("cat fail", cat, e, file=sys.stderr)

    random.shuffle(pool)
    for title in pool:
        if title in seen or title.startswith("List of"):
            continue
        s = summary_simple(title)
        if not s:
            continue
        # skip very technical dumps
        if re.search(r"\b(theorem|equation|polynomial|manifold)\b", s["extract"], re.I):
            continue
        s["bg"] = "classroom"
        s["category"] = "mixed"
        candidates.append(s)
        if len(candidates) >= 10:
            break

    if not candidates:
        candidates = [{
            "title": "Rainbow",
            "extract": (
                "A rainbow is a colorful arc in the sky made when sunlight hits raindrops. "
                "Each drop bends light and splits it into colors we can see."
            ),
            "description": "light in the sky",
            "url": "",
            "bg": "classroom",
            "category": "fallback",
        }]

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
