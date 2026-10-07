#!/usr/bin/env python3
"""Discover exam/scheme-of-work topics: Google Trends + DuckDuckGo + Wikipedia."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trending_topics.json"
UA = {
    "User-Agent": "MikeTutorTrends/1.4 (educational; github.com/officialbonesceo)",
    "Accept": "application/json",
}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import filter_title_list, is_school_safe  # noqa: E402

SEARCH_SEEDS = [
    "WAEC 2025 English language common topics",
    "JAMB English lexis and structure topics",
    "NECO SSCE English essay letter writing topics",
    "secondary school English grammar parts of speech",
    "WAEC English comprehension summary topics",
    "figure of speech metaphor simile idiom exam",
    "WAEC biology cell tissue organ system topics",
    "JAMB chemistry states of matter acid base",
    "SS1 SS2 geography map latitude longitude climate",
    "WAEC physics simple machine lever pulley energy",
    "food chain ecosystem habitat pollution exam",
    "fraction ratio average perimeter area volume math",
    "active passive voice subject predicate English",
    "water cycle weather climate continent exam",
]

WIKI_SEEDS = [
    "Noun", "Verb", "Adjective", "Metaphor", "Simile",
    "Photosynthesis", "Cell", "Ecosystem", "Water cycle",
    "Matter", "Acid", "Simple machine", "Fraction",
    "Probability", "Algorithm", "Internet",
    "Friction", "Osmosis", "Enzyme", "Respiration",
]

NORMALIZE = {
    "photosynthesis": "Photosynthesis",
    "quadratic equation": "Quadratic equation",
    "newton laws": "Newton's laws of motion",
    "newton's laws": "Newton's laws of motion",
    "osmosis": "Osmosis",
    "electric current": "Electric current",
    "mitosis": "Mitosis",
    "meiosis": "Meiosis",
    "friction": "Friction",
    "gravity": "Gravity",
    "essay writing": "Essay writing",
    "essay": "Essay writing",
    "dna": "DNA",
    "kinetic energy": "Kinetic energy",
    "potential energy": "Potential energy",
    "ohms law": "Ohm's law",
    "ohm's law": "Ohm's law",
    "inertia": "Inertia",
    "momentum": "Momentum",
    "pressure": "Pressure",
    "diffusion": "Diffusion",
    "respiration": "Respiration",
    "noun": "Noun",
    "verb": "Verb",
    "adjective": "Adjective",
    "adverb": "Adverb",
    "metaphor": "Metaphor",
    "simile": "Simile",
    "idiom": "Idiom",
    "paragraph": "Paragraph",
    "synonym": "Synonym",
    "antonym": "Antonym",
    "ecosystem": "Ecosystem",
    "water cycle": "Water cycle",
    "simple machine": "Simple machine",
    "fraction": "Fraction",
    "probability": "Probability",
}

HARD_SKIP = re.compile(
    r"petroleum|refiner|dangote|mithraism|mitsubishi|porn|login|pdf download|"
    r"actress|actor|celebrity|singer|netflix|k-pop|idol|osmosis jones|records|"
    r"osmonds|royal medal|mitsuishi|penilaian|quartic|nucleation",
    re.I,
)


def clean_title(q: str) -> str | None:
    q = (q or "").strip()
    if not q or len(q) < 3 or len(q) > 55:
        return None
    if HARD_SKIP.search(q) or re.search(r"https?://|www\.", q, re.I):
        return None
    if re.search(r"(?i)(welding|weapon|penetrator|interceptor|sintering|kinase|quartic|stir )", q):
        return None
    if len(q.split()) > 5:
        return None
    if not is_school_safe(q):
        return None
    key = re.sub(r"\s+", " ", q.lower()).strip()
    if key in NORMALIZE:
        return NORMALIZE[key]
    key2 = re.sub(
        r"\b(20\d{2}|waec|jamb|neco|ssce|exam|past question[s]?|tips?|explained|"
        r"for students|scheme of work|syllabus|most tested|hardest)\b",
        "",
        key,
    )
    key2 = re.sub(r"\s+", " ", key2).strip(" -_:")
    if key2 in NORMALIZE:
        return NORMALIZE[key2]
    if 3 <= len(key2) <= 40 and re.match(r"^[a-z0-9][a-z0-9\s'\-]+$", key2):
        titled = key2.title()
        if is_school_safe(titled) and not HARD_SKIP.search(titled):
            return titled
    return None


def from_pytrends() -> list[str]:
    found: list[str] = []
    try:
        from pytrends.request import TrendReq

        try:
            pytrends = TrendReq(hl="en-US", tz=60)
        except Exception:
            return found
        seeds = [
            "WAEC English", "JAMB biology", "photosynthesis",
            "parts of speech", "metaphor", "ecosystem",
            "simple machine", "water cycle", "fraction", "essay writing",
        ]
        for seed in seeds:
            try:
                pytrends.build_payload([seed], timeframe="now 7-d", geo="")
                related = pytrends.related_queries()
                block = related.get(seed) or {}
                for bucket in ("rising", "top"):
                    df = block.get(bucket)
                    if df is None or getattr(df, "empty", True):
                        continue
                    for q in list(df["query"].head(5)):
                        t = clean_title(str(q))
                        if t:
                            found.append(t)
                time.sleep(1.2)
            except Exception as e:
                print("pytrends seed fail", seed, e, file=sys.stderr)
    except Exception as e:
        print("pytrends fail (skipped)", e, file=sys.stderr)
    return found


def from_duckduckgo() -> list[str]:
    found: list[str] = []
    for q in SEARCH_SEEDS:
        try:
            r = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1},
                headers=UA,
                timeout=20,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            for key in ("Heading", "Answer", "AbstractText"):
                t = clean_title(str(data.get(key) or ""))
                if t:
                    found.append(t)
            for rel in data.get("RelatedTopics") or []:
                if isinstance(rel, dict):
                    text = rel.get("Text") or rel.get("Name") or ""
                    first = text.split(" - ")[0].split(".")[0]
                    t = clean_title(first)
                    if t:
                        found.append(t)
            time.sleep(0.4)
        except Exception as e:
            print("ddg fail", q[:40], e, file=sys.stderr)
    return found


def from_wikipedia() -> list[str]:
    found = []
    for seed in WIKI_SEEDS[:10]:
        try:
            r = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": seed,
                    "limit": 5,
                    "namespace": 0,
                    "format": "json",
                },
                headers=UA,
                timeout=20,
            )
            if r.status_code == 429:
                print("wiki 429 stop early", file=sys.stderr)
                time.sleep(3)
                break
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and len(data) > 1:
                for title in data[1]:
                    t = clean_title(title)
                    if t:
                        found.append(t)
            time.sleep(0.6)
        except Exception as e:
            print("wiki fail", seed, e, file=sys.stderr)
            time.sleep(0.8)
    return found


def dedupe(titles: list[str]) -> list[str]:
    out, seen = [], set()
    for t in titles:
        k = re.sub(r"[^a-z0-9]", "", t.lower())
        if not k or k in seen or HARD_SKIP.search(t):
            continue
        skip = False
        if len(k) >= 8:
            for s in seen:
                if len(s) >= 8 and (k.startswith(s[:8]) or s.startswith(k[:8])) and abs(len(k) - len(s)) <= 5:
                    skip = True
                    break
        if skip:
            continue
        seen.add(k)
        out.append(t)
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    titles: list[str] = []
    titles.extend(from_pytrends())
    titles.extend(from_duckduckgo())
    titles.extend(from_wikipedia())
    for s in WIKI_SEEDS:
        if is_school_safe(s):
            titles.append(s)
    titles = filter_title_list(dedupe(titles))
    cleaned = [t for t in titles if len(t.split()) <= 5]
    titles = cleaned[:40]

    payload = {
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "scheme_queries+google_trends+duckduckgo+wikipedia",
        "titles": titles,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"WROTE {len(titles)} topics → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
