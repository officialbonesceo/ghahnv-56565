#!/usr/bin/env python3
"""Discover student-teachable topics: Google Trends + DuckDuckGo + Wikipedia."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trending_topics.json"
UA = {"User-Agent": "MikeTutorTrends/1.0 (educational; school STEM)"}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import filter_title_list, is_school_safe  # noqa: E402

# Student-intent search seeds (exam / WAEC / JAMB style)
SEARCH_SEEDS = [
    "WAEC physics topics students struggle",
    "JAMB chemistry most tested topics",
    "secondary school biology exam concepts",
    "math exam topics students fail",
    "photosynthesis exam tips",
    "newton laws of motion explained for students",
    "osmosis vs diffusion exam",
    "quadratic equation word problems",
    "electric current series parallel circuits",
    "how to write essay for exams",
    "kinetic energy potential energy difference",
    "mitosis meiosis difference exam",
]

WIKI_SEEDS = [
    "Photosynthesis", "Friction", "Electric current", "Osmosis",
    "Mitosis", "Quadratic equation", "Newton's laws of motion",
    "Kinetic energy", "DNA", "Enzyme", "Inertia", "Pressure",
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
}

HARD_SKIP = re.compile(
    r"petroleum|refiner|dangote|mithraism|mitsubishi|porn|login|pdf download",
    re.I,
)


def clean_title(q: str) -> str | None:
    q = (q or "").strip()
    if not q or len(q) < 3 or len(q) > 60:
        return None
    if HARD_SKIP.search(q) or re.search(r"https?://|www\.", q, re.I):
        return None
    if not is_school_safe(q):
        return None
    key = re.sub(r"\s+", " ", q.lower()).strip()
    if key in NORMALIZE:
        return NORMALIZE[key]
    key2 = re.sub(
        r"\b(20\d{2}|waec|jamb|neco|ssce|exam|past question[s]?|tips?|explained|for students)\b",
        "",
        key,
    )
    key2 = re.sub(r"\s+", " ", key2).strip(" -_:")
    if key2 in NORMALIZE:
        return NORMALIZE[key2]
    if 3 <= len(key2) <= 45 and re.match(r"^[a-z0-9][a-z0-9\s'\-]+$", key2):
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
            "photosynthesis", "quadratic equation", "newton laws",
            "osmosis", "electric current", "kinetic energy",
            "mitosis", "friction physics", "essay writing", "ohms law",
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
    """DuckDuckGo related topics via Instant Answer API (no key)."""
    found: list[str] = []
    for q in SEARCH_SEEDS[:8]:
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
                    # first clause often the topic name
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
            time.sleep(0.4)
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
                    "limit": 10,
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
            # also related via search
            r2 = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{seed} secondary school OR exam OR physics OR chemistry OR biology",
                    "srlimit": 8,
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
        # prefix collision
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
    # Prefer school-looking titles; drop junk fragments
    cleaned = []
    for t in titles:
        if len(t.split()) > 6:
            continue
        cleaned.append(t)
    titles = cleaned[:50]
    if len(titles) < 5:
        # minimal safe pool only if discovery almost empty — still real wiki titles
        for s in WIKI_SEEDS:
            if s not in titles:
                titles.append(s)
        titles = titles[:20]

    payload = {
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "google_trends+duckduckgo+wikipedia",
        "titles": titles,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"WROTE {len(titles)} topics → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
