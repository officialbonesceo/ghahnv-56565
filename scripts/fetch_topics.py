#!/usr/bin/env python3
"""School STEM topics from trends/wiki — retry wiki, DDG abstract if wiki 429."""
from __future__ import annotations

import json
import random
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import is_school_safe, filter_title_list

UA = {
    "User-Agent": "MikeTutor/1.2 (educational; contact: github.com/officialbonesceo)",
    "Accept": "application/json",
}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"
SEED_TOPIC_PATH = ROOT / "data" / "seed_topic.json"

HARD_BLOCK = {
    "petroleumrefining", "petroleumref", "fractionaldistillation",
    "fractionaldistil", "dangoterefinery", "oilrefinery", "oilrefining",
    "mithraism", "osmosisjones", "mitsubishi", "kotonemitsuishi",
}

SYLLABUS_POOL = [
    "Gravity", "Friction", "Electric current", "Voltage",
    "Osmosis", "Diffusion", "Evaporation", "Condensation", "Respiration",
    "Enzyme", "Speed", "Velocity", "Acceleration", "Force",
    "Newton's laws of motion", "Kinetic energy", "Potential energy",
    "Heat", "Temperature", "Sound", "Light",
    "Refraction", "Mitosis", "DNA",
    "Quadratic equation", "Percentage",
    "Inertia", "Momentum", "Pressure", "Density", "Ohm's law",
    "Photosynthesis",
]


def norm_key(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)", "", title or "")
    t = re.sub(r"[^a-z0-9]+", "", t.lower())
    return t


def is_hard_blocked(title: str) -> bool:
    k = norm_key(title)
    if k in HARD_BLOCK:
        return True
    for b in HARD_BLOCK:
        if len(b) >= 8 and (b in k or k in b):
            return True
    if "petroleum" in k or "refiner" in k or "dangote" in k:
        return True
    if "jones" in k and "osmosis" in k:
        return True
    return False


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
            nk = norm_key(str(x))
            if len(nk) >= 12:
                out.add(nk[:12])
        return out
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(title)
    seen.add(norm_key(title))
    nk = norm_key(title)
    if len(nk) >= 12:
        seen.add(nk[:12])
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    titles = sorted({s for s in seen if s and len(str(s)) > 2})[-1200:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def is_seen(seen: set[str], title: str) -> bool:
    if is_hard_blocked(title):
        return True
    k = norm_key(title)
    if title in seen or k in seen:
        return True
    if len(k) >= 12 and k[:12] in seen:
        return True
    for s in seen:
        sk = norm_key(s) if any(c.isalpha() for c in str(s)) else str(s)
        if len(k) >= 8 and len(sk) >= 8:
            if k == sk or k.startswith(sk) or sk.startswith(k):
                return True
            if abs(len(k) - len(sk)) <= 4 and (k[:8] == sk[:8]):
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


def try_seed_topic(seen: set[str]) -> dict | None:
    if not SEED_TOPIC_PATH.exists():
        return None
    try:
        data = json.loads(SEED_TOPIC_PATH.read_text(encoding="utf-8"))
        if data.get("disabled"):
            return None
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or len(extract) < 80:
            return None
        if is_hard_blocked(title) or is_seen(seen, title):
            SEED_TOPIC_PATH.write_text(
                json.dumps({"disabled": True, "note": f"blocked/seen: {title}"}, indent=2),
                encoding="utf-8",
            )
            return None
        if not is_school_safe(title, extract):
            return None
        data.setdefault("bg", "classroom")
        data["topic_source"] = "seed"
        SEED_TOPIC_PATH.write_text(
            json.dumps({"disabled": True, "used_title": title, "note": "consumed"}, indent=2),
            encoding="utf-8",
        )
        print("USING_SEED once", title, file=sys.stderr)
        return data
    except Exception as e:
        print("seed load fail", e, file=sys.stderr)
        return None


def _get_json(url: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 429:
                wait = 2.5 * (attempt + 1)
                print("wiki 429 backoff", wait, url[-40:], file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            print("get_json", e, file=sys.stderr)
            time.sleep(1.2 * (attempt + 1))
    return None


def summary_wikipedia(title: str) -> dict:
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    slug = title.replace(" ", "_")
    for base in (
        "https://simple.wikipedia.org/api/rest_v1/page/summary/",
        "https://en.wikipedia.org/api/rest_v1/page/summary/",
    ):
        data = _get_json(base + requests.utils.quote(slug), retries=3)
        if not data:
            time.sleep(0.4)
            continue
        if data.get("type") == "disambiguation":
            continue
        extract = (data.get("extract") or "").strip()
        if len(extract) < 80:
            continue
        got = data.get("title") or title
        if is_hard_blocked(got) or not is_school_safe(got, extract):
            continue
        return {
            "title": got,
            "extract": extract[:650],
            "description": data.get("description") or "",
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "bg": "classroom",
            "trend": False,
            "extract_source": "wikipedia",
        }
    return {}


def summary_duckduckgo(title: str) -> dict:
    """Fallback extract when Wikipedia is rate-limited — still grounded, not invented."""
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": title, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=UA,
            timeout=25,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        abstract = (data.get("AbstractText") or "").strip()
        heading = (data.get("Heading") or title).strip()
        if len(abstract) < 80:
            # try related first paragraph
            for rel in data.get("RelatedTopics") or []:
                if isinstance(rel, dict):
                    text = (rel.get("Text") or "").strip()
                    if len(text) >= 80 and title.lower().split()[0] in text.lower():
                        abstract = text
                        break
        if len(abstract) < 80:
            return {}
        if is_hard_blocked(heading) or not is_school_safe(heading, abstract):
            return {}
        return {
            "title": title if len(title) >= 3 else heading,
            "extract": abstract[:650],
            "description": (data.get("AbstractSource") or "DuckDuckGo")[:80],
            "url": data.get("AbstractURL") or "",
            "bg": "classroom",
            "trend": False,
            "extract_source": "duckduckgo",
        }
    except Exception as e:
        print("ddg summary fail", title, e, file=sys.stderr)
        return {}


def summary(title: str) -> dict:
    s = summary_wikipedia(title)
    if s:
        return s
    time.sleep(0.5)
    return summary_duckduckgo(title)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "topic.json")
    seen = load_seen()

    seeded = try_seed_topic(seen)
    if seeded:
        save_seen(seen, seeded["title"])
        out.write_text(json.dumps(seeded, indent=2), encoding="utf-8")
        print("TOPIC_SOURCE seed", seeded.get("title"), file=sys.stderr)
        print(json.dumps(seeded, indent=2))
        return

    trends = load_trends()
    primary = [t for t in trends if not is_seen(seen, t) and not is_hard_blocked(t)]
    source_tag = "trend"

    if not primary:
        hard_keys = set(HARD_BLOCK)
        kept = [s for s in sorted(seen) if is_hard_blocked(str(s))][:80]
        seen = set(kept) | hard_keys
        primary = [t for t in trends if not is_seen(seen, t)]
        if not primary:
            primary = [t for t in SYLLABUS_POOL if not is_seen(seen, t) and is_school_safe(t)]
            source_tag = "syllabus"
        else:
            source_tag = "trend-reset"
        print("pool rebuild", source_tag, len(primary), file=sys.stderr)

    # Always mix a few syllabus titles so 429 on trendy junk does not empty the pool
    for t in SYLLABUS_POOL:
        if t not in primary and not is_seen(seen, t) and is_school_safe(t):
            primary.append(t)

    if not primary:
        print("TOPIC_FAIL: no school topics available after trends+syllabus", file=sys.stderr)
        sys.exit(1)

    random.shuffle(primary)
    candidates = []
    for title in primary:
        if is_seen(seen, title) or is_hard_blocked(title):
            continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]) and not is_hard_blocked(s["title"]):
            if not is_school_safe(s["title"], s.get("extract") or ""):
                continue
            s["trend"] = source_tag.startswith("trend")
            s["topic_source"] = source_tag + "+" + (s.get("extract_source") or "wiki")
            candidates.append(s)
        if len(candidates) >= 6:
            break
        time.sleep(0.35)

    if not candidates:
        print("TOPIC_FAIL: no safe extracts from Wikipedia or DuckDuckGo", file=sys.stderr)
        sys.exit(1)

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
