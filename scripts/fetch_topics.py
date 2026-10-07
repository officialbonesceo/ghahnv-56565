#!/usr/bin/env python3
"""School STEM topics — wiki + DDG + local syllabus bank; strict dedupe."""
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
    "User-Agent": "MikeTutor/1.4 (educational; contact: github.com/officialbonesceo)",
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

# Junk trend titles that look technical but are not SSCE syllabus
JUNK_TITLE = re.compile(
    r"(?i)(welding|sintering|weapon|penetrator|interceptor|recovery system|"
    r"inducer protein|kinase|quartic|stir |assisted |density$|"
    r"system$|research$|loss$)"
)

# Local grounded extracts — used ONLY when live wiki/DDG both fail
SYLLABUS_BANK: dict[str, str] = {
    "Gravity": (
        "Gravity is the force that pulls objects toward each other. "
        "On Earth, gravity pulls everything toward the centre of the Earth. "
        "Weight is the force of gravity on an object. Mass stays the same; weight can change."
    ),
    "Friction": (
        "Friction is a force that opposes motion when two surfaces rub. "
        "It can slow moving objects and also helps us walk without slipping. "
        "Rough surfaces usually give more friction than smooth ones."
    ),
    "Electric current": (
        "Electric current is the flow of electric charge through a conductor. "
        "It is measured in amperes. In a simple circuit, current needs a closed path and a source of voltage."
    ),
    "Voltage": (
        "Voltage is the electric potential difference between two points. "
        "It is measured in volts and can be thought of as the push that drives current around a circuit."
    ),
    "Osmosis": (
        "Osmosis is the movement of water through a selectively permeable membrane "
        "from a region of higher water concentration to lower water concentration. "
        "It is important in living cells."
    ),
    "Diffusion": (
        "Diffusion is the net movement of particles from a region of higher concentration "
        "to a region of lower concentration. It does not need a living membrane."
    ),
    "Evaporation": (
        "Evaporation is the change of liquid into vapour at temperatures below boiling point. "
        "It happens at the surface of the liquid and cools the surroundings."
    ),
    "Condensation": (
        "Condensation is the change of vapour into liquid when it cools. "
        "Water droplets on a cold bottle come from water vapour in the air."
    ),
    "Respiration": (
        "Respiration is the process by which living cells release energy from food. "
        "In aerobic respiration, glucose reacts with oxygen to produce carbon dioxide, water and energy."
    ),
    "Enzyme": (
        "Enzymes are biological catalysts that speed up chemical reactions in living things. "
        "They are mostly proteins and work best at specific temperatures and pH values."
    ),
    "Speed": (
        "Speed is the distance travelled per unit time. "
        "It is a scalar quantity. Average speed equals total distance divided by total time."
    ),
    "Velocity": (
        "Velocity is speed in a given direction. "
        "It is a vector. Changing direction changes velocity even if speed stays the same."
    ),
    "Acceleration": (
        "Acceleration is the rate of change of velocity with time. "
        "It is measured in metres per second squared. Speeding up, slowing down, or changing direction all involve acceleration."
    ),
    "Force": (
        "A force is a push or a pull. "
        "Forces can change the shape, speed, or direction of an object. Force is measured in newtons."
    ),
    "Newton's laws of motion": (
        "Newton's first law says an object stays at rest or moves at constant velocity unless a net force acts. "
        "The second law links force, mass and acceleration. The third law says forces come in equal and opposite pairs."
    ),
    "Kinetic energy": (
        "Kinetic energy is the energy an object has because it is moving. "
        "It increases with mass and with the square of speed."
    ),
    "Potential energy": (
        "Potential energy is stored energy due to position or state. "
        "Gravitational potential energy is greater when an object is higher above the ground."
    ),
    "Heat": (
        "Heat is energy transferred from a hotter body to a colder one because of temperature difference. "
        "It can move by conduction, convection or radiation."
    ),
    "Temperature": (
        "Temperature measures how hot or cold something is. "
        "It relates to the average kinetic energy of particles. Common units include Celsius."
    ),
    "Sound": (
        "Sound is a form of energy produced by vibrating objects and travels as waves through a medium. "
        "It cannot travel through a vacuum."
    ),
    "Light": (
        "Light is a form of energy that can travel through a vacuum. "
        "It travels in straight lines in a uniform medium and can be reflected or refracted."
    ),
    "Refraction": (
        "Refraction is the bending of light when it passes from one medium into another of different density. "
        "A straw in water can look bent because of refraction."
    ),
    "Mitosis": (
        "Mitosis is cell division that produces two daughter cells with the same number of chromosomes as the parent. "
        "It is used for growth and repair in the body."
    ),
    "DNA": (
        "DNA is the molecule that carries genetic information in living organisms. "
        "It is found in the nucleus of cells and has a double-helix structure."
    ),
    "Quadratic equation": (
        "A quadratic equation is a polynomial equation of degree two, often written as ax² + bx + c = 0. "
        "It can be solved by factorisation, completing the square, or the quadratic formula."
    ),
    "Percentage": (
        "A percentage is a fraction expressed out of one hundred. "
        "To find x percent of a number, multiply the number by x and divide by 100."
    ),
    "Inertia": (
        "Inertia is the tendency of an object to resist changes in its state of motion. "
        "Objects with greater mass have greater inertia."
    ),
    "Momentum": (
        "Momentum is the product of mass and velocity. "
        "In a closed system, total momentum is conserved when no external force acts."
    ),
    "Pressure": (
        "Pressure is force per unit area. "
        "The same force on a smaller area produces higher pressure. It is measured in pascals."
    ),
    "Density": (
        "Density is mass per unit volume. "
        "Objects denser than water usually sink; less dense ones can float."
    ),
    "Ohm's law": (
        "Ohm's law states that current through a conductor is proportional to voltage across it, "
        "if temperature is constant. In symbols, V = IR."
    ),
    "Photosynthesis": (
        "Photosynthesis is the process by which green plants make food using light energy. "
        "Carbon dioxide and water form glucose and oxygen in the presence of chlorophyll."
    ),
}

SYLLABUS_POOL = list(SYLLABUS_BANK.keys())


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
    if JUNK_TITLE.search(title or ""):
        return True
    # too many words → often wiki disambiguation junk
    if len((title or "").split()) > 5:
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
            out.add(norm_key(str(x)))
        return out
    except Exception:
        return set()


def save_seen(seen: set[str], title: str) -> None:
    seen.add(norm_key(title))
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    # keep last ~400 normalised keys only
    titles = sorted(k for k in seen if k and len(k) > 2)[-400:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def is_seen(seen: set[str], title: str) -> bool:
    """Strict dedupe: exact normalised key only (no fuzzy prefix matching)."""
    if is_hard_blocked(title):
        return True
    k = norm_key(title)
    if not k:
        return True
    if k in seen:
        return True
    # near-exact: same key ignoring trailing 's'
    if k.endswith("s") and k[:-1] in seen:
        return True
    if (k + "s") in seen:
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
        cleaned = []
        for t in titles:
            t = str(t).strip()
            if not t or is_hard_blocked(t):
                continue
            cleaned.append(t)
        return filter_title_list(cleaned)
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


def _get_json(url: str, retries: int = 4) -> dict | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 429:
                wait = 3.0 * (attempt + 1)
                print("wiki 429 backoff", wait, file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            print("get_json", e, file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None


def summary_wikipedia(title: str) -> dict:
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    slug = title.replace(" ", "_")
    for base in (
        "https://simple.wikipedia.org/api/rest_v1/page/summary/",
        "https://en.wikipedia.org/api/rest_v1/page/summary/",
    ):
        data = _get_json(base + requests.utils.quote(slug), retries=4)
        if not data:
            time.sleep(0.5)
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


def summary_mediawiki(title: str) -> dict:
    """Alternative extract via MediaWiki action API (often survives REST 429)."""
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    for api in (
        "https://simple.wikipedia.org/w/api.php",
        "https://en.wikipedia.org/w/api.php",
    ):
        try:
            r = requests.get(
                api,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "titles": title,
                    "format": "json",
                    "redirects": 1,
                },
                headers=UA,
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code >= 400:
                continue
            pages = (r.json().get("query") or {}).get("pages") or {}
            for page in pages.values():
                if page.get("missing") is not None:
                    continue
                extract = (page.get("extract") or "").strip()
                got = page.get("title") or title
                if len(extract) < 80:
                    continue
                if is_hard_blocked(got) or not is_school_safe(got, extract):
                    continue
                return {
                    "title": got,
                    "extract": extract[:650],
                    "description": "mediawiki",
                    "url": f"https://en.wikipedia.org/wiki/{got.replace(' ', '_')}",
                    "bg": "classroom",
                    "trend": False,
                    "extract_source": "mediawiki",
                }
        except Exception as e:
            print("mediawiki fail", title, e, file=sys.stderr)
        time.sleep(0.4)
    return {}


def summary_duckduckgo(title: str) -> dict:
    if is_hard_blocked(title) or not is_school_safe(title):
        return {}
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": f"{title} science definition", "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=UA,
            timeout=25,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        abstract = (data.get("AbstractText") or "").strip()
        heading = (data.get("Heading") or title).strip()
        if len(abstract) < 80:
            for rel in data.get("RelatedTopics") or []:
                if isinstance(rel, dict):
                    text = (rel.get("Text") or "").strip()
                    if len(text) >= 80:
                        abstract = text
                        break
        if len(abstract) < 80:
            return {}
        if is_hard_blocked(heading) or not is_school_safe(title, abstract):
            return {}
        return {
            "title": title,
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


def summary_local(title: str) -> dict:
    """Syllabus bank — real exam definitions, not AI invention."""
    # exact then fuzzy key match
    if title in SYLLABUS_BANK:
        key = title
    else:
        key = None
        nk = norm_key(title)
        for k in SYLLABUS_BANK:
            if norm_key(k) == nk:
                key = k
                break
    if not key:
        return {}
    extract = SYLLABUS_BANK[key]
    if not is_school_safe(key, extract):
        return {}
    return {
        "title": key,
        "extract": extract,
        "description": "syllabus bank",
        "url": "",
        "bg": "classroom",
        "trend": False,
        "extract_source": "syllabus_bank",
    }


def summary(title: str) -> dict:
    for fn in (summary_wikipedia, summary_mediawiki, summary_duckduckgo, summary_local):
        s = fn(title)
        if s:
            return s
        time.sleep(0.35)
    return {}


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

    # Always mix unused syllabus titles
    for t in SYLLABUS_POOL:
        if t not in primary and not is_seen(seen, t) and is_school_safe(t):
            primary.append(t)

    if not primary:
        # soft reset: keep only last 30 seen keys so pool can rotate
        kept = sorted(seen)[-30:]
        seen = set(kept)
        primary = [t for t in SYLLABUS_POOL if not is_seen(seen, t) and is_school_safe(t)]
        source_tag = "syllabus-reset"
        print("pool rebuild", source_tag, len(primary), file=sys.stderr)

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
        if len(candidates) >= 8:
            break
        time.sleep(0.25)

    if not candidates:
        # last resort: any unseen bank entry
        for title in SYLLABUS_POOL:
            if is_seen(seen, title):
                continue
            s = summary_local(title)
            if s:
                s["topic_source"] = "syllabus_bank_fallback"
                candidates.append(s)
            if len(candidates) >= 3:
                break

    if not candidates:
        print("TOPIC_FAIL: no safe extracts from Wikipedia, DuckDuckGo, or syllabus bank", file=sys.stderr)
        sys.exit(1)

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
