#!/usr/bin/env python3
"""Fetch fresh explainer topics from free public APIs (Wikipedia). No seed required."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "MeziClipFactory/1.0 (educational; github-actions)"}

# Categories that fit MEZI curious-explorer niche
CATEGORIES = [
    "Category:Basic_concepts_in_physics",
    "Category:Introductory_astronomy",
    "Category:Human_physiology",
    "Category:Basic_meteorological_concepts",
    "Category:Money",
    "Category:Internet",
    "Category:Oceanography",
    "Category:History_of_science",
]

BG_RULES = [
    (r"space|planet|star|moon|galaxy|nasa|orbit|astronaut|solar|cosmos|universe",
     "space"),
    (r"ocean|sea|fish|wave|marine|water",
     "ocean"),
    (r"money|bank|economy|dollar|currency|finance|trade",
     "money"),
    (r"computer|internet|wifi|wifi|software|code|network|phone",
     "tech"),
    (r"sky|cloud|rain|weather|climate|atmosphere",
     "science"),
    (r"body|brain|heart|blood|human|sleep|yawn",
     "science"),
]


def wiki_get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params or {}, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def members_from_category(cat: str, limit: int = 20) -> list[str]:
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
    return "studio"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    random.shuffle(CATEGORIES)
    candidates: list[dict] = []

    for cat in CATEGORIES[:4]:
        try:
            titles = members_from_category(cat, 15)
        except Exception as e:
            print("category fail", cat, e, file=sys.stderr)
            continue
        random.shuffle(titles)
        for title in titles[:6]:
            if title.startswith("List of") or title.startswith("Index of"):
                continue
            s = summary_for(title)
            if not s:
                continue
            s["category"] = cat
            s["bg"] = guess_bg(s["title"], s["extract"])
            candidates.append(s)
            if len(candidates) >= 8:
                break
        if len(candidates) >= 8:
            break

    if not candidates:
        # hard fallback
        candidates = [{
            "title": "Sky",
            "extract": "The sky is the atmosphere as seen from Earth. Daytime sky appears blue because air scatters blue light more than other colors.",
            "description": "appearance of the atmosphere",
            "url": "",
            "category": "fallback",
            "bg": "science",
        }]

    pick = random.choice(candidates)
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print(json.dumps(pick, indent=2))
    print("WROTE", out)


if __name__ == "__main__":
    main()
