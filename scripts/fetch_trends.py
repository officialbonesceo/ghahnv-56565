#!/usr/bin/env python3
"""Pull study/exam trend signals → data/trending_topics.json

Sources (in order):
1) Google Trends related/rising queries (pytrends) for education seeds
2) Wikipedia most-read style related pages via search API
3) Static high-intent exam fallback list

Never fails the pipeline — always writes a usable JSON list.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trending_topics.json"
UA = {"User-Agent": "MikeTutorTrends/1.0 (educational)"}

# Seeds that map to student/exam intent (NG + global study)
SEED_QUERIES = [
    "WAEC",
    "JAMB",
    "photosynthesis",
    "quadratic equation",
    "newton laws",
    "osmosis",
    "electric current",
    "how to study for exams",
    "essay writing",
    "mitosis",
]

# Map noisy trend strings → Wikipedia-friendly titles
NORMALIZE = {
    "waec": "West African Examinations Council",
    "jamb": "Joint Admissions and Matriculation Board",
    "photosynthesis": "Photosynthesis",
    "quadratic equation": "Quadratic equation",
    "quadratic equations": "Quadratic equation",
    "newton laws": "Newton's laws of motion",
    "newton's laws": "Newton's laws of motion",
    "newtons laws": "Newton's laws of motion",
    "osmosis": "Osmosis",
    "electric current": "Electric current",
    "electricity": "Electricity",
    "mitosis": "Mitosis",
    "meiosis": "Meiosis",
    "friction": "Friction",
    "gravity": "Gravity",
    "essay writing": "Essay",
    "essay": "Essay",
    "dna": "DNA",
    "atom": "Atom",
    "velocity": "Velocity",
    "acceleration": "Acceleration",
    "kinetic energy": "Kinetic energy",
    "potential energy": "Potential energy",
    "refraction": "Refraction",
    "reflection": "Reflection (physics)",
    "greenhouse effect": "Greenhouse effect",
    "global warming": "Global warming",
    "how to study for exams": "Memory",
    "study tips": "Memory",
    "past questions": "Examination",
}

FALLBACK = [
    "Photosynthesis",
    "Friction",
    "Electric current",
    "Osmosis",
    "Quadratic equation",
    "Newton's laws of motion",
    "Mitosis",
    "Essay",
    "DNA",
    "Kinetic energy",
]


def clean_title(q: str) -> str | None:
    q = (q or "").strip()
    if not q or len(q) < 3:
        return None
    # drop pure navigation / junk
    if re.search(r"https?://|www\.|@\w+", q, re.I):
        return None
    if re.search(r"\b(login|download|pdf|answers only)\b", q, re.I):
        return None
    key = re.sub(r"\s+", " ", q.lower()).strip()
    if key in NORMALIZE:
        return NORMALIZE[key]
    # strip year / exam noise but keep concept
    key2 = re.sub(r"\b(20\d{2}|waec|jamb|neco|ssce|exam|past question[s]?)\b", "", key)
    key2 = re.sub(r"\s+", " ", key2).strip(" -_:")
    if key2 in NORMALIZE:
        return NORMALIZE[key2]
    # Title-case short concept phrases
    if 3 <= len(key2) <= 40 and not re.search(r"[^a-z0-9\s'\-]", key2):
        return key2.title()
    return None


def from_pytrends() -> list[str]:
    try:
        from pytrends.request import TrendReq
    except Exception as e:
        print("pytrends import fail", e, file=sys.stderr)
        return []

    found: list[str] = []
    try:
        pytrends = TrendReq(hl="en-US", tz=60, retries=2, backoff_factor=1.5)
        for seed in SEED_QUERIES[:6]:
            try:
                pytrends.build_payload([seed], timeframe="now 7-d", geo="")
                # related queries
                related = pytrends.related_queries()
                block = related.get(seed) or {}
                for bucket in ("rising", "top"):
                    df = block.get(bucket)
                    if df is None or getattr(df, "empty", True):
                        continue
                    for q in list(df["query"].head(8)):
                        t = clean_title(str(q))
                        if t:
                            found.append(t)
                time.sleep(1.2)
            except Exception as e:
                print("pytrends seed fail", seed, e, file=sys.stderr)
                continue
        # daily trends (US) as extra signal — filter hard
        try:
            daily = pytrends.trending_searches(pn="united_states")
            for q in list(daily[0].head(15)):
                t = clean_title(str(q))
                if t and t in NORMALIZE.values() or (t and len(t.split()) <= 4):
                    # only keep if maps to study concept
                    if t in FALLBACK or t in NORMALIZE.values():
                        found.append(t)
        except Exception as e:
            print("daily trends fail", e, file=sys.stderr)
    except Exception as e:
        print("pytrends session fail", e, file=sys.stderr)
    return found


def from_wikipedia_related() -> list[str]:
    """Lightweight related titles via Wikipedia opensearch."""
    found = []
    for seed in ["Photosynthesis", "Electric current", "Quadratic equation", "Osmosis", "Mitosis"]:
        try:
            r = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": seed,
                    "limit": 8,
                    "namespace": 0,
                    "format": "json",
                },
                headers=UA,
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and len(data) > 1:
                for title in data[1]:
                    t = clean_title(title) or title
                    if t:
                        found.append(t)
            time.sleep(0.3)
        except Exception as e:
            print("wiki related fail", seed, e, file=sys.stderr)
    return found


def dedupe(titles: list[str]) -> list[str]:
    out, seen = [], set()
    for t in titles:
        k = re.sub(r"\s*\([^)]*\)", "", t).strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    titles = []
    titles.extend(from_pytrends())
    if len(titles) < 5:
        titles.extend(from_wikipedia_related())
    titles.extend(FALLBACK)
    titles = dedupe(titles)[:40]

    payload = {
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "google_trends+wikipedia+fallback",
        "titles": titles,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"WROTE {len(titles)} trends → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
