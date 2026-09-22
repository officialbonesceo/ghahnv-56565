#!/usr/bin/env python3
"""School STEM topics — strong dedupe, one-shot seed, hard topic blocks."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_safety import is_school_safe, filter_title_list

UA = {"User-Agent": "MikeTutor/1.0 (educational)"}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"
SEED_TOPIC_PATH = ROOT / "data" / "seed_topic.json"

# Never pick these again (spam / sticky seeds)
HARD_BLOCK = {
    "petroleumrefining", "petroleumref", "fractionaldistillation",
    "fractionaldistil", "dangoterefinery", "oilrefinery", "oilrefining",
    "mithraism", "osmosisjones", "mitsubishi", "kotonemitsuishi",
}

SEED_TITLES = [
    "Gravity", "Friction", "Electricity", "Electric current", "Voltage",
    "Circuit", "Atom", "Molecule", "DNA", "Osmosis", "Diffusion",
    "Evaporation", "Condensation", "Water cycle", "Respiration", "Enzyme",
    "Catalyst", "Acid", "Base (chemistry)", "pH", "Speed", "Velocity",
    "Acceleration", "Force", "Newton's laws of motion", "Work (physics)",
    "Energy", "Kinetic energy", "Potential energy", "Heat", "Temperature",
    "Sound", "Light", "Reflection (physics)", "Refraction", "Magnet",
    "Electromagnet", "Cell (biology)", "Mitosis", "Meiosis", "Blood",
    "Heart", "Lungs", "Brain", "Sleep", "Memory", "Vaccine", "Antibiotic",
    "Greenhouse effect", "Global warming", "Solar system", "Eclipse",
    "Moon", "Earth", "Earthquake", "Volcano", "Fossil", "Evolution",
    "Quadratic equation", "Pythagorean theorem", "Fraction", "Percentage",
    "Ratio", "Average", "Essay", "Paragraph", "Supply and demand",
    "Inertia", "Momentum", "Pressure", "Density", "Buoyancy",
    "Surface tension", "Capillarity", "Latent heat", "Specific heat",
    "Ohm's law", "Series and parallel circuits", "Electromagnetic induction",
    "Transpiration", "Chlorophyll", "Stomata", "Protein", "Carbohydrate",
    "Lipid", "Vitamins", "Nervous system", "Digestive system",
    "Circulatory system", "Immune system", "Genetics", "Heredity",
    "Natural selection", "Food chain", "Ecosystem", "Atmosphere",
    "Weather", "Climate", "Rock cycle", "Plate tectonics",
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
    """One-shot seed only if file valid, not disabled, not already seen/blocked."""
    if not SEED_TOPIC_PATH.exists():
        return None
    try:
        data = json.loads(SEED_TOPIC_PATH.read_text(encoding="utf-8"))
        if data.get("disabled"):
            print("seed disabled — skip", file=sys.stderr)
            return None
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or len(extract) < 80:
            return None
        if is_hard_blocked(title) or is_seen(seen, title):
            print("seed blocked/seen — skip", title, file=sys.stderr)
            # disable sticky seed in workspace so commit can persist
            SEED_TOPIC_PATH.write_text(
                json.dumps({"disabled": True, "note": f"blocked/seen: {title}"}, indent=2),
                encoding="utf-8",
            )
            return None
        if not is_school_safe(title, extract):
            return None
        data.setdefault("bg", "classroom")
        data["topic_source"] = data.get("topic_source") or "seed"
        data["trend"] = bool(data.get("trend", True))
        # disable permanently after one use
        SEED_TOPIC_PATH.write_text(
            json.dumps({"disabled": True, "used_title": title, "note": "consumed"}, indent=2),
            encoding="utf-8",
        )
        print("USING_SEED once", title, file=sys.stderr)
        return data
    except Exception as e:
        print("seed load fail", e, file=sys.stderr)
        return None


def summary(title: str) -> dict:
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
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
            }
        except Exception:
            continue
    return {}


def build_pool(seen: set[str]) -> tuple[list[str], list[str]]:
    trend_pool, seed_pool = [], []
    for t in load_trends():
        if is_seen(seen, t) or is_hard_blocked(t) or not is_school_safe(t):
            continue
        trend_pool.append(t)
    for t in SEED_TITLES:
        if is_seen(seen, t) or is_hard_blocked(t):
            continue
        seed_pool.append(t)
    return trend_pool, seed_pool


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

    trend_pool, seed_pool = build_pool(seen)
    if trend_pool and (not seed_pool or random.random() < 0.65):
        primary, source_tag = trend_pool, "trend"
    else:
        primary, source_tag = seed_pool or [t for t in SEED_TITLES if not is_hard_blocked(t)], "seed"

    if not primary:
        # Keep hard blocks; only soft-reset other seen titles
        hard_keys = set(HARD_BLOCK)
        kept = []
        for s in sorted(seen):
            if is_hard_blocked(str(s)):
                kept.append(s)
            elif len(str(s)) > 12 and len(kept) < 50:
                kept.append(s)
        seen = set(kept) | hard_keys
        primary = [t for t in SEED_TITLES if not is_seen(seen, t)]
        source_tag = "seed-reset"
        print("seen soft-reset (hard blocks kept)", file=sys.stderr)

    random.shuffle(primary)
    candidates = []
    for title in primary:
        if is_seen(seen, title) or is_hard_blocked(title):
            continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]) and not is_hard_blocked(s["title"]):
            s["trend"] = source_tag == "trend"
            s["topic_source"] = source_tag
            candidates.append(s)
        if len(candidates) >= 8:
            break

    if not candidates:
        for title in SEED_TITLES:
            if is_seen(seen, title) or is_hard_blocked(title):
                continue
            s = summary(title)
            if s and not is_hard_blocked(s["title"]):
                s["topic_source"] = "seed-fallback"
                candidates.append(s)
            if len(candidates) >= 5:
                break

    if not candidates:
        candidates = [{
            "title": "Inertia",
            "extract": (
                "Inertia is the tendency of an object to keep doing what it is already doing. "
                "If it is still, it stays still. If it is moving, it keeps moving until a force acts. "
                "Students meet this idea in Newton's first law questions in almost every physics exam."
            ),
            "description": "physics",
            "url": "",
            "bg": "classroom",
            "trend": False,
            "topic_source": "hardcoded",
        }]

    pick = random.choice(candidates)
    if is_hard_blocked(pick["title"]):
        pick = candidates[0]
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
