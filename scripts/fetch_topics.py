#!/usr/bin/env python3
"""Internet-first school topics + large fallback bank. Strict seen_topics; 429-resilient."""
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
from script_quality import is_broad_topic_title

UA = {"User-Agent": "MikeTutor/1.9 (educational; contact: github.com/officialbonesceo)", "Accept": "application/json"}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"
SEED_TOPIC_PATH = ROOT / "data" / "seed_topic.json"
FALLBACK_PATH = ROOT / "data" / "topic_fallback.json"
CORES_PATH = ROOT / "data" / "topic_cores.json"
_WIKI_RATE_LIMITED = False

HARD_BLOCK = {"birkhoffsaxioms", "birkhoff", "hilbertsaxioms", "peanosaxioms", "topology", "differentialgeometry", "complexanalysis", "linearalgebra", "grouptheory", "petroleumrefining", "petroleumref", "fractionaldistillation", "fractionaldistil", "dangoterefinery", "oilrefinery", "oilrefining", "mithraism", "osmosisjones", "mitsubishi", "kotonemitsuishi", "mississippiriver", "royalmedal", "theosmonds", "penilaianmen", "penilaianmenengahrendah", "nucleation", "quarticequation", "quarticequat"}
TREND_SPAM = re.compile(r"(?i)(essay\s*writing\s*service|writing\s*service|cheap\s*college|trustworthy\s*essay|safe\s*essay|ai\s*essay|what\s+is\s+(a\s+|the\s+)?photosynthesis|what\s+is\s+(a\s+|the\s+)?water\s*cycle|what\s+is\s+fraction|as\s+a?\s*fraction|in\s+fraction|magic\s+school\s+bus|water\s+cycle\s+diagram|water\s+cycle\s+(management|intensification)|photosynthesis\s+(system|research)|cell\s+signaling|fraction\s+in\s+disguise|college\s+essay)")

CROSS_SUBJECT = re.compile(
    r"(?i)^(?:physics|chemistry|biology|mathematics|english)\s+"
    r"(?:formal\s+letter|letter\s+writing|essay|comprehension|noun|verb|adjective|tenses|"
    r"active\s+voice|passive\s+voice|simile|metaphor|paragraph|grammar)"
)
JUNK_TITLE = re.compile(r"(?i)(welding|sintering|weapon|penetrator|interceptor|recovery system|inducer protein|kinase|quartic|stir |assisted |density$|system$|research$|loss$|service$|recommendation|biography|discography|filmography|album|single \(song\)|embodied design)")

DISCOVER_QUERIES = ["physics secondary school", "chemistry secondary school", "biology secondary school", "mathematics secondary school", "English grammar secondary school", "WAEC physics topic", "WAEC chemistry topic", "WAEC biology topic", "NECO science topic", "forces and motion school", "heat transfer school", "electricity circuit school", "cell biology school", "plant physiology school", "algebra secondary", "geometry secondary school", "essay structure school", "figures of speech school", "environmental science secondary", "computer science basics school", "simple machines school", "periodic table secondary", "human body systems school", "probability secondary school"]
WIKI_CATEGORY_SEEDS = ["Category:Introductory_physics", "Category:Concepts_in_physics", "Category:Classical_mechanics", "Category:Thermodynamics", "Category:Electricity", "Category:Optics", "Category:Biology", "Category:Cell_biology", "Category:Botany", "Category:Ecology", "Category:Chemistry", "Category:Chemical_reactions", "Category:Mathematics_education", "Category:Elementary_geometry", "Category:Algebra", "Category:English_grammar", "Category:Figures_of_speech", "Category:Earth_sciences", "Category:Atmospheric_sciences", "Category:Computer_science"]

def norm_key(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)", "", title or "")
    return re.sub(r"[^a-z0-9]+", "", t.lower())

def is_hard_blocked(title: str) -> bool:
    if is_broad_topic_title(title or ""):
        return True
    k = norm_key(title)
    if k in HARD_BLOCK: return True
    for b in HARD_BLOCK:
        if len(b) >= 8 and (b in k or k in b): return True
    if "petroleum" in k or "refiner" in k or "dangote" in k: return True
    if "jones" in k and "osmosis" in k: return True
    if TREND_SPAM.search(title or "") or JUNK_TITLE.search(title or "") or CROSS_SUBJECT.search(title or ""): return True
    if len((title or "").split()) > 7: return True
    return False

def load_seen() -> set[str]:
    if not SEEN_PATH.exists(): return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        raw = data if isinstance(data, list) else data.get("titles", [])
        return {norm_key(str(x)) for x in raw}
    except Exception:
        return set()

def save_seen(seen: set[str], title: str) -> None:
    seen.add(norm_key(title))
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    titles = sorted(k for k in seen if k and len(k) > 2)[-1200:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")

def is_seen(seen: set[str], title: str) -> bool:
    if is_hard_blocked(title): return True
    k = norm_key(title)
    if not k or len(k) < 3: return True
    if k in seen: return True
    if k.endswith("s") and k[:-1] in seen: return True
    if (k + "s") in seen: return True
    for s in seen:
        if not s or len(s) < 8 or len(k) < 8: continue
        shorter, longer = (s, k) if len(s) <= len(k) else (k, s)
        if len(shorter) >= 10 and shorter in longer and len(longer) - len(shorter) <= 6:
            return True
    return False

def load_trends() -> list[str]:
    if not TREND_PATH.exists(): return []
    try:
        data = json.loads(TREND_PATH.read_text(encoding="utf-8"))
        titles = data.get("titles") if isinstance(data, dict) else data
        if not isinstance(titles, list): return []
        cleaned = [str(t).strip() for t in titles if str(t).strip() and not is_hard_blocked(str(t)) and not TREND_SPAM.search(str(t))]
        return filter_title_list(cleaned)
    except Exception:
        return []

def _generate_fallback_titles() -> list[str]:
    """Expand cores into tens of thousands of school titles."""
    cores: list[str] = []
    try:
        if CORES_PATH.exists():
            data = json.loads(CORES_PATH.read_text(encoding="utf-8"))
            raw = data.get("cores") if isinstance(data, dict) else data
            if isinstance(raw, list):
                cores = [str(x).strip() for x in raw if str(x).strip()]
        for part in sorted((ROOT / "data").glob("topic_cores_part*.json")):
            try:
                data = json.loads(part.read_text(encoding="utf-8"))
                raw = data.get("cores") if isinstance(data, dict) else data
                if isinstance(raw, list):
                    cores.extend(str(x).strip() for x in raw if str(x).strip())
            except Exception as e:
                print("cores part fail", part.name, e, file=sys.stderr)
        seen_c, uniq = set(), []
        for c in cores:
            k = c.lower()
            if k in seen_c: continue
            seen_c.add(k)
            uniq.append(c)
        cores = uniq
    except Exception as e:
        print("cores load", e, file=sys.stderr)
    if len(cores) < 50:
        cores = [
            "Force", "Motion", "Speed", "Velocity", "Acceleration", "Inertia", "Momentum", "Friction",
            "Gravity", "Mass", "Weight", "Density", "Pressure", "Work", "Power", "Energy",
            "Kinetic energy", "Potential energy", "Heat", "Temperature", "Conduction", "Convection",
            "Radiation", "Latent heat", "Electric current", "Voltage", "Resistance", "Ohm's law",
            "Series circuit", "Parallel circuit", "Magnetism", "Light", "Reflection", "Refraction",
            "Sound", "Waves", "Lever", "Pulley", "Buoyancy", "Atom", "Molecule", "Element",
            "Compound", "Periodic table", "Ionic bond", "Covalent bond", "Acid", "Base", "Salt",
            "Neutralization", "Solution", "Oxygen", "Hydrogen", "Rusting", "Electrolysis", "Catalyst",
            "Mole concept", "Cell", "Cell membrane", "Nucleus", "Diffusion", "Osmosis",
            "Photosynthesis", "Respiration", "Enzyme", "Heart", "Lungs", "Brain", "Blood",
            "Vaccine", "DNA", "Mitosis", "Meiosis", "Food chain", "Ecosystem", "Genetics",
            "Fraction", "Percentage", "Ratio", "Algebra", "Linear equation", "Quadratic equation",
            "Geometry", "Triangle", "Circle", "Area", "Volume", "Pythagoras theorem", "Trigonometry",
            "Probability", "Statistics", "Noun", "Verb", "Adjective", "Tenses", "Active voice",
            "Passive voice", "Simile", "Metaphor", "Essay writing", "Comprehension", "Letter writing",
            "Water cycle", "Climate", "Rock cycle", "Computer", "Algorithm", "Internet",
            "Binary system", "States of matter", "Evaporation", "Condensation", "Current electricity",
            "Static electricity", "Simple machines", "Newton laws", "Digestive system",
            "Circulatory system", "Nervous system", "pH scale", "Rate of reaction",
        ]
    angles = [
        "{t}", "Types of {t}", "{t} explained",
        "{t} definition", "{t} examples", "{t} in everyday life", "{t} for WAEC", "{t} for JAMB",
        "{t} for NECO", "{t} for secondary school", "How {t} works", "Importance of {t}",
        "Applications of {t}", "Properties of {t}", "{t} formula", "{t} process", "{t} experiment",
        "SS1 {t}", "SS2 {t}", "SS3 {t}", "JSS {t}", "Common mistakes in {t}", "Exam tips on {t}",
        "Revision on {t}", "Key points on {t}", "Factors affecting {t}", "Uses of {t}",
    ]
    titles: set[str] = set()
    for t in cores:
        for tmpl in angles:
            title = tmpl.format(t=t)
            if 2 <= len(title.split()) <= 8 and len(title) <= 70:
                titles.add(title)
    pairs = [
        ("Kinetic energy", "Potential energy"), ("Conduction", "Convection"),
        ("Series circuit", "Parallel circuit"), ("Mitosis", "Meiosis"),
        ("Osmosis", "Diffusion"), ("Acid", "Base"), ("Speed", "Velocity"),
        ("Mass", "Weight"), ("Reflection", "Refraction"),
        ("Active voice", "Passive voice"), ("Ionic bond", "Covalent bond"),
    ]
    for a, b in pairs:
        for title in (f"{a} and {b}", f"Difference between {a} and {b}", f"{a} vs {b}"):
            if len(title.split()) <= 8:
                titles.add(title)
    return sorted(titles, key=str.lower)

def load_fallback_titles() -> list[str]:
    titles = []
    try:
        if FALLBACK_PATH.exists():
            data = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
            raw = data.get("titles") if isinstance(data, dict) else data
            if isinstance(raw, list):
                titles.extend(str(t).strip() for t in raw if str(t).strip())
        for part in sorted((ROOT / "data").glob("topic_fallback_part*.json")):
            try:
                data = json.loads(part.read_text(encoding="utf-8"))
                raw = data.get("titles") if isinstance(data, dict) else data
                if isinstance(raw, list):
                    titles.extend(str(t).strip() for t in raw if str(t).strip())
            except Exception as e:
                print("fallback part fail", part.name, e, file=sys.stderr)
    except Exception as e:
        print("fallback file load", e, file=sys.stderr)
    titles.extend(_generate_fallback_titles())
    seen_local, out = set(), []
    for t in titles:
        k = t.lower()
        if k in seen_local: continue
        seen_local.add(k)
        out.append(t)
    print("FALLBACK_TITLES", len(out), file=sys.stderr)
    return out

def try_seed_topic(seen: set[str]) -> dict | None:
    if not SEED_TOPIC_PATH.exists(): return None
    try:
        data = json.loads(SEED_TOPIC_PATH.read_text(encoding="utf-8"))
        if data.get("disabled"): return None
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or len(extract) < 80: return None
        if is_hard_blocked(title) or is_seen(seen, title):
            SEED_TOPIC_PATH.write_text(json.dumps({"disabled": True, "note": f"blocked/seen: {title}"}, indent=2), encoding="utf-8")
            return None
        if not is_school_safe(title, extract): return None
        data.setdefault("bg", "classroom")
        data["topic_source"] = "seed"
        SEED_TOPIC_PATH.write_text(json.dumps({"disabled": True, "used_title": title, "note": "consumed"}, indent=2), encoding="utf-8")
        print("USING_SEED once", title, file=sys.stderr)
        return data
    except Exception as e:
        print("seed load fail", e, file=sys.stderr)
        return None

def _get_json(url: str, retries: int = 5) -> dict | None:
    global _WIKI_RATE_LIMITED
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 429:
                _WIKI_RATE_LIMITED = True
                wait = min(45.0, 5.0 * (2 ** attempt) + random.uniform(0, 2))
                print("wiki 429 backoff", round(wait, 1), file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code >= 400: return None
            return r.json()
        except Exception as e:
            print("get_json", e, file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None

def discover_ddg_related(query: str) -> list[str]:
    out = []
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}, headers=UA, timeout=25)
        if r.status_code != 200: return []
        data = r.json()
        heading = (data.get("Heading") or "").strip()
        if heading and not is_hard_blocked(heading): out.append(heading)
        for rel in data.get("RelatedTopics") or []:
            items = [rel] if isinstance(rel, dict) and "Topics" not in rel else (rel.get("Topics") or [] if isinstance(rel, dict) else [])
            for item in items:
                if not isinstance(item, dict): continue
                text = (item.get("Text") or "").strip()
                name = text.split(" - ")[0].split(" — ")[0].strip()
                if name and 2 <= len(name.split()) <= 6 and not is_hard_blocked(name):
                    out.append(name)
    except Exception as e:
        print("ddg discover fail", query, e, file=sys.stderr)
    return out

def discover_wiki_category(cat: str, limit: int = 25) -> list[str]:
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED: return []
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php", params={"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": limit, "cmtype": "page", "format": "json"}, headers=UA, timeout=30)
        if r.status_code == 429:
            _WIKI_RATE_LIMITED = True
            return []
        if r.status_code != 200: return []
        out = []
        for m in (r.json().get("query") or {}).get("categorymembers") or []:
            title = (m.get("title") or "").strip()
            if title and not title.startswith("Category:") and not is_hard_blocked(title):
                out.append(title)
        return out
    except Exception as e:
        print("wiki category fail", cat, e, file=sys.stderr)
        return []

def discover_internet_titles(seen: set[str], want: int = 60) -> list[str]:
    pool: list[str] = []
    for t in load_trends():
        if not is_seen(seen, t): pool.append(t)
    qs = list(DISCOVER_QUERIES)
    random.shuffle(qs)
    for q in qs[:8]:
        for t in discover_ddg_related(q):
            if not is_seen(seen, t) and t not in pool: pool.append(t)
        if len(pool) >= want: break
        time.sleep(0.2)
    if not _WIKI_RATE_LIMITED and len(pool) < want:
        cats = list(WIKI_CATEGORY_SEEDS)
        random.shuffle(cats)
        for cat in cats[:4]:
            for t in discover_wiki_category(cat):
                if not is_seen(seen, t) and t not in pool: pool.append(t)
            if len(pool) >= want or _WIKI_RATE_LIMITED: break
            time.sleep(0.5)
    fb = load_fallback_titles()
    random.shuffle(fb)
    for t in fb:
        if len(pool) >= want * 2: break
        if not is_seen(seen, t) and t not in pool and not is_hard_blocked(t):
            pool.append(t)
    pool = [t for t in pool if not is_hard_blocked(t)]
    random.shuffle(pool)
    print("DISCOVERED_TITLES", len(pool), "wiki_limited=", _WIKI_RATE_LIMITED, file=sys.stderr)
    return pool[: max(want, 40)]

def summary_duckduckgo(title: str) -> dict:
    if is_hard_blocked(title): return {}
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": f"{title} definition school science", "format": "json", "no_html": 1, "skip_disambig": 1}, headers=UA, timeout=25)
        if r.status_code != 200: return {}
        data = r.json()
        abstract = (data.get("AbstractText") or "").strip()
        if len(abstract) < 80:
            for rel in data.get("RelatedTopics") or []:
                if isinstance(rel, dict):
                    text = (rel.get("Text") or "").strip()
                    if len(text) >= 80:
                        abstract = text
                        break
        if len(abstract) < 80: return {}
        return {"title": title, "extract": abstract[:650], "description": (data.get("AbstractSource") or "DuckDuckGo")[:80], "url": data.get("AbstractURL") or "", "bg": "classroom", "trend": False, "extract_source": "duckduckgo"}
    except Exception as e:
        print("ddg summary fail", title, e, file=sys.stderr)
        return {}

def summary_wikipedia(title: str) -> dict:
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED or is_hard_blocked(title): return {}
    slug = title.replace(" ", "_")
    for base in ("https://simple.wikipedia.org/api/rest_v1/page/summary/", "https://en.wikipedia.org/api/rest_v1/page/summary/"):
        data = _get_json(base + requests.utils.quote(slug), retries=3)
        if not data:
            time.sleep(0.4)
            continue
        if data.get("type") == "disambiguation": continue
        extract = (data.get("extract") or "").strip()
        if len(extract) < 80: continue
        got = data.get("title") or title
        if is_hard_blocked(got): continue
        return {"title": got, "extract": extract[:650], "description": data.get("description") or "", "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""), "bg": "classroom", "trend": False, "extract_source": "wikipedia"}
    return {}

def synthetic_extract(title: str) -> dict:
    t = title.strip()
    extract = (f"{t} is an important topic in secondary school science and exam study. "
               f"Students learn what {t} means, how it works in everyday life, and how to "
               f"use simple examples and definitions in class. Understanding {t} helps with "
               f"WAEC, NECO and JAMB style questions. Teachers often explain {t} with a "
               f"short definition, one clear example, and a quick check question so learners "
               f"can remember it and apply it correctly.")
    return {"title": t, "extract": extract[:650], "description": "fallback-synthetic", "url": "", "bg": "classroom", "trend": False, "extract_source": "fallback"}

def summary(title: str) -> dict:
    order = (summary_duckduckgo, summary_wikipedia) if not _WIKI_RATE_LIMITED else (summary_duckduckgo,)
    for fn in order:
        s = fn(title)
        if s: return s
        time.sleep(0.2)
    return {}

def pick_from_fallback(seen: set[str]) -> dict | None:
    titles = load_fallback_titles()
    if not titles: return None
    random.shuffle(titles)
    tried = 0
    for t in titles:
        if tried >= 40: break
        if is_seen(seen, t) or is_hard_blocked(t): continue
        tried += 1
        s = summary(t) or synthetic_extract(t)
        if s and not is_seen(seen, s["title"]):
            s["topic_source"] = "fallback+" + (s.get("extract_source") or "synthetic")
            return s
        time.sleep(0.1)
    for t in titles:
        if is_seen(seen, t) or is_hard_blocked(t): continue
        s = synthetic_extract(t)
        s["topic_source"] = "fallback+synthetic"
        return s
    return None

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
    _ = load_fallback_titles()
    primary = discover_internet_titles(seen, want=50)
    candidates = []
    for title in primary:
        if is_seen(seen, title) or is_hard_blocked(title): continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]) and not is_hard_blocked(s["title"]):
            s["trend"] = False
            s["topic_source"] = "internet+" + (s.get("extract_source") or "wiki")
            candidates.append(s)
        if len(candidates) >= 6: break
        time.sleep(0.2)
    if not candidates:
        print("INTERNET_EMPTY trying fallback bank", file=sys.stderr)
        fb = pick_from_fallback(seen)
        if fb: candidates = [fb]
    if not candidates:
        print("TOPIC_FAIL: no topics available", file=sys.stderr)
        sys.exit(1)
    random.shuffle(candidates)
    chosen = candidates[0]
    save_seen(seen, chosen["title"])
    out.write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", chosen.get("topic_source"), chosen.get("title"), file=sys.stderr)
    print(json.dumps(chosen, indent=2))

if __name__ == "__main__":
    main()
