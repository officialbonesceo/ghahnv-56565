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
UA = {"User-Agent": "MikeTutorTrends/1.0 (educational; school STEM)"}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import filter_title_list, is_school_safe  # noqa: E402

# Question-style queries — not "Topic X" pasted into search
SEARCH_SEEDS = [
    "WAEC 2025 physics scheme of work topics",
    "JAMB 2025 chemistry syllabus most tested",
    "NECO SSCE biology topics students fail",
    "secondary school math scheme of work 2024 2025",
    "what topics come out every year in WAEC physics",
    "hardest JAMB biology questions topics",
    "SS1 SS2 SS3 physics scheme of work electricity",
    "WAEC chemistry practical topics common",
    "quadratic equations exam questions students miss",
    "osmosis diffusion exam difference secondary",
    "Newton laws of motion WAEC past questions",
    "photosynthesis exam definition and equation",
    "essay writing structure for secondary exams",
    "electric current series parallel circuits exam",
    "kinetic energy potential energy WAEC",
]

WIKI_SEEDS = [
    "Photosynthesis", "Friction", "Electric current", "Osmosis",
    "Mitosis", "Quadratic equation", "Newton's laws of motion",
    "Kinetic energy", "DNA", "Enzyme", "Inertia", "Pressure",
    "Ohm's law", "Diffusion", "Respiration",
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
    "essay writing": "Essay",
    "essay": "Essay",
    "dna": "DNA",
    "kinetic energy": "Kinetic energy",
    "potential energy": "Potential energy",
    "ohms law": "Ohm's law",
    "ohm's law": "Ohm's law",
    "inertia": "Inertia",
    "momentum": "Momentum",
    "pressure": "Pressure",
    "density": "Density",
    "diffusion": "Diffusion",
    "respiration": "Respiration",
}

HARD_SKIP = re.compile(
    r"petroleum|refiner|dangote|mithraism|mitsubishi|porn|login|pdf download|"
    r"actress|actor|celebrity|singer|netflix|k-pop|idol",
    re.I,
)


def clean_title(q: str) -> str | None:
    q = (q or "").strip()
    if not q or len(q) < 3 or len(q) > 55:
        return None
    if HARD_SKIP.search(q) or re.search(r"https?://|www\.", q, re.I):
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
        pytrends = TrendReq(hl="en-US", tz=60, retries=2, backoff_factor=1.5)
        seeds = [
            "WAEC physics", "JAMB chemistry", "photosynthesis",
            "quadratic equation", "newton laws", "osmosis",
            "electric current", "kinetic energy", "mitosis", "ohms law",
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
                    for q in list(df["query"].head(6)):
                        t = clean_title(str(q))
                        if t:
                            found.append(t)
                time.sleep(1.0)
            except Exception as e:
                print("pytrends seed fail", seed, e, file=sys.stderr)
    except Exception as e:
        print("pytrends fail", e, file=sys.stderr)
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
                elif isinstance(rel, list):
                    for item in rel:
                        if isinstance(item, dict):
                            first = (item.get("Text") or "").split(" - ")[0]
                            t = clean_title(first)
                            if t:
                                found.append(t)
            time.sleep(0.35)
        except Exception as e:
            print("ddg fail", q[:40], e, file=sys.stderr)
    return found


def from_wikipedia() -> list[str]:
    found = []
    for seed in WIKI_SEEDS:
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
                    t = clean_title(title)
                    if t:
                        found.append(t)
            r2 = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{seed} secondary school OR WAEC OR exam syllabus",
                    "srlimit": 6,
                    "format": "json",
                },
                headers=UA,
                timeout=20,
            )
            if r2.status_code == 200:
                for hit in (r2.json().get("query") or {}).get("search") or []:
                    t = clean_title(hit.get("title") or "")
                    if t:
                        found.append(t)
            time.sleep(0.25)
        except Exception as e:
            print("wiki fail", seed, e, file=sys.stderr)
    return found


def dedupe(titles: list[str]) -> list[str]:
    out, seen = [], set()
    for t in titles:
        k = re.sub(r"[^a-z0-9]", "", t.lower())
        if not k or k in seen or HARD_SKIP.search(t):
            continue
        if any(k.startswith(s[:8]) or s.startswith(k[:8]) for s in seen if len(s) >= 8 and len(k) >= 8):
            if any(k == s or abs(len(k) - len(s)) <= 3 for s in seen):
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
    titles = filter_title_list(dedupe(titles))
    cleaned = [t for t in titles if len(t.split()) <= 6]
    titles = cleaned[:50]
    # Minimal recovery: only known syllabus titles if discovery almost empty
    if len(titles) < 3:
        for s in WIKI_SEEDS:
            if is_school_safe(s) and s not in titles:
                titles.append(s)
        titles = titles[:15]

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
