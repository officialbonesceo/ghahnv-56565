#!/usr/bin/env python3
"""Fetch Wikipedia topics for curious-science niche. Skip seen titles."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "MeziClipFactory/1.0 (educational; github-actions)"}
SEEN_PATH = Path(__file__).resolve().parents[1] / "data" / "seen_topics.json"

CATEGORIES = [
    "Category:Basic_concepts_in_physics",
    "Category:Introductory_astronomy",
    "Category:Human_physiology",
    "Category:Basic_meteorological_concepts",
    "Category:Oceanography",
    "Category:History_of_science",
    "Category:Optics",
    "Category:Atmospheric_science",
]

BG_RULES = [
    (r"space|planet|star|moon|galaxy|nasa|orbit|astronaut|solar|cosmos|universe|nebula",
     "space"),
    (r"ocean|sea|fish|wave|marine|water|reef",
     "ocean"),
    (r"mountain|expedition|himalaya|climb|glacier",
     "nature"),
    (r"computer|internet|wifi|software|code|network|phone|chip",
     "tech"),
    (r"sky|cloud|rain|weather|climate|atmosphere|rainbow",
     "science"),
    (r"body|brain|heart|blood|human|sleep|yawn|cell",
     "science"),
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
    # keep last 500
    items = sorted(seen)
    if len(items) > 500:
        items = items[-500:]
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def wiki_get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params or {}, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def members_from_category(cat: str, limit: int = 30) -> list[str]:
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


def summary_for(title: str) -> dict:
    slug = title.replace(" ", "_")
    try:
        data = wiki_get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(slug)}"
        )
    except Exception:
        return {}
    extract = (data.get("extract") or "").strip()
    if len(extract) < 80:
        return {}
    return {
        "title": data.get("title") or title,
        "extract": extract[:600],
        "description": data.get("description") or "",
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }


def guess_bg(title: str, extract: str) -> str:
    blob = f"{title} {extract}".lower()
    for pattern, bg in BG_RULES:
        if re.search(pattern, blob):
            return bg
    return "science"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()
    random.shuffle(CATEGORIES)
    candidates: list[dict] = []

    for cat in CATEGORIES:
        try:
            titles = members_from_category(cat, 25)
        except Exception as e:
            print("category fail", cat, e, file=sys.stderr)
            continue
        random.shuffle(titles)
        for title in titles:
            if title in seen:
                continue
            if title.startswith("List of") or title.startswith("Index of"):
                continue
            s = summary_for(title)
            if not s:
                continue
            s["category"] = cat
            s["bg"] = guess_bg(s["title"], s["extract"])
            candidates.append(s)
            if len(candidates) >= 12:
                break
        if len(candidates) >= 12:
            break

    if not candidates:
        # all seen or empty — allow reuse of oldest style fallback
        candidates = [{
            "title": "Rainbow",
            "extract": (
                "A rainbow is a meteorological phenomenon caused by reflection, "
                "refraction and dispersion of light in water droplets. It results "
                "in a spectrum of light appearing in the sky."
            ),
            "description": "optical phenomenon",
            "url": "",
            "category": "fallback",
            "bg": "science",
        }]

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print(json.dumps(pick, indent=2))
    print("WROTE", out, "seen", len(seen) + 1)


if __name__ == "__main__":
    main()
