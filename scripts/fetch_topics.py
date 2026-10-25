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

UA = {
    "User-Agent": "MikeTutor/1.8 (educational; contact: github.com/officialbonesceo)",
    "Accept": "application/json",
}
ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "seen_topics.json"
TREND_PATH = ROOT / "data" / "trending_topics.json"
SEED_TOPIC_PATH = ROOT / "data" / "seed_topic.json"
FALLBACK_PATH = ROOT / "data" / "topic_fallback.json"

_WIKI_RATE_LIMITED = False

HARD_BLOCK = {
    "petroleumrefining", "petroleumref", "fractionaldistillation",
    "fractionaldistil", "dangoterefinery", "oilrefinery", "oilrefining",
    "mithraism", "osmosisjones", "mitsubishi", "kotonemitsuishi",
    "mississippiriver", "royalmedal", "theosmonds", "penilaianmen",
    "penilaianmenengahrendah", "nucleation", "quarticequation", "quarticequat",
}

TREND_SPAM = re.compile(
    r"(?i)("
    r"essay\s*writing\s*service|writing\s*service|cheap\s*college|"
    r"trustworthy\s*essay|safe\s*essay|ai\s*essay|"
    r"what\s+is\s+(a\s+|the\s+)?photosynthesis|"
    r"what\s+is\s+(a\s+|the\s+)?water\s*cycle|"
    r"what\s+is\s+fraction|as\s+a?\s*fraction|in\s+fraction|"
    r"magic\s+school\s+bus|water\s+cycle\s+diagram|"
    r"water\s+cycle\s+(management|intensification)|"
    r"photosynthesis\s+(system|research)|cell\s+signaling|"
    r"fraction\s+in\s+disguise|college\s+essay"
    r")"
)

JUNK_TITLE = re.compile(
    r"(?i)(welding|sintering|weapon|penetrator|interceptor|recovery system|"
    r"inducer protein|kinase|quartic|stir |assisted |density$|"
    r"system$|research$|loss$|service$|recommendation|biography|"
    r"discography|filmography|album|single \(song\))"
)

DISCOVER_QUERIES = [
    "physics secondary school",
    "chemistry secondary school",
    "biology secondary school",
    "mathematics secondary school",
    "English grammar secondary school",
    "WAEC physics topic",
    "WAEC chemistry topic",
    "WAEC biology topic",
    "NECO science topic",
    "forces and motion school",
    "heat transfer school",
    "electricity circuit school",
    "cell biology school",
    "plant physiology school",
    "algebra secondary",
    "geometry secondary school",
    "essay structure school",
    "figures of speech school",
    "environmental science secondary",
    "computer science basics school",
    "simple machines school",
    "periodic table secondary",
    "human body systems school",
    "probability secondary school",
]

WIKI_CATEGORY_SEEDS = [
    "Category:Introductory_physics",
    "Category:Concepts_in_physics",
    "Category:Classical_mechanics",
    "Category:Thermodynamics",
    "Category:Electricity",
    "Category:Optics",
    "Category:Biology",
    "Category:Cell_biology",
    "Category:Botany",
    "Category:Ecology",
    "Category:Chemistry",
    "Category:Chemical_reactions",
    "Category:Mathematics_education",
    "Category:Elementary_geometry",
    "Category:Algebra",
    "Category:English_grammar",
    "Category:Figures_of_speech",
    "Category:Earth_sciences",
    "Category:Atmospheric_sciences",
    "Category:Computer_science",
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
    if TREND_SPAM.search(title or ""):
        return True
    if JUNK_TITLE.search(title or ""):
        return True
    if len((title or "").split()) > 7:
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
    titles = sorted(k for k in seen if k and len(k) > 2)[-1200:]
    SEEN_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def is_seen(seen: set[str], title: str) -> bool:
    if is_hard_blocked(title):
        return True
    k = norm_key(title)
    if not k or len(k) < 3:
        return True
    if k in seen:
        return True
    if k.endswith("s") and k[:-1] in seen:
        return True
    if (k + "s") in seen:
        return True
    for s in seen:
        if not s or len(s) < 8 or len(k) < 8:
            continue
        shorter, longer = (s, k) if len(s) <= len(k) else (k, s)
        if len(shorter) >= 10 and shorter in longer and len(longer) - len(shorter) <= 6:
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
            if not t or is_hard_blocked(t) or TREND_SPAM.search(t):
                continue
            cleaned.append(t)
        return filter_title_list(cleaned)
    except Exception:
        return []


def load_fallback_titles() -> list[str]:
    if not FALLBACK_PATH.exists():
        return []
    try:
        data = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
        titles = data.get("titles") if isinstance(data, dict) else data
        if not isinstance(titles, list):
            return []
        return [str(t).strip() for t in titles if str(t).strip()]
    except Exception as e:
        print("fallback load fail", e, file=sys.stderr)
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
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            print("get_json", e, file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None


def discover_wiki_category(cat: str, limit: int = 40) -> list[str]:
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED:
        return []
    out = []
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmlimit": limit,
                "cmtype": "page",
                "format": "json",
            },
            headers=UA,
            timeout=30,
        )
        if r.status_code == 429:
            _WIKI_RATE_LIMITED = True
            print("wiki category 429", cat, file=sys.stderr)
            return []
        if r.status_code != 200:
            return []
        for m in (r.json().get("query") or {}).get("categorymembers") or []:
            title = (m.get("title") or "").strip()
            if not title or title.startswith("Category:"):
                continue
            if is_hard_blocked(title):
                continue
            out.append(title)
    except Exception as e:
        print("wiki category fail", cat, e, file=sys.stderr)
    return out


def discover_wiki_search(query: str, limit: int = 15) -> list[str]:
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED:
        return []
    out = []
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "srnamespace": 0,
                "format": "json",
            },
            headers=UA,
            timeout=30,
        )
        if r.status_code == 429:
            _WIKI_RATE_LIMITED = True
            return []
        if r.status_code != 200:
            return []
        for hit in (r.json().get("query") or {}).get("search") or []:
            title = (hit.get("title") or "").strip()
            if not title or is_hard_blocked(title):
                continue
            out.append(title)
    except Exception as e:
        print("wiki search fail", query, e, file=sys.stderr)
    return out


def discover_ddg_related(query: str) -> list[str]:
    out = []
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=UA,
            timeout=25,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        heading = (data.get("Heading") or "").strip()
        if heading and not is_hard_blocked(heading):
            out.append(heading)
        for rel in data.get("RelatedTopics") or []:
            if isinstance(rel, dict) and "Topics" not in rel:
                text = (rel.get("Text") or "").strip()
                name = text.split(" - ")[0].split(" — ")[0].strip()
                if name and 2 <= len(name.split()) <= 6 and not is_hard_blocked(name):
                    out.append(name)
            elif isinstance(rel, dict) and "Topics" in rel:
                for item in rel.get("Topics") or []:
                    text = (item.get("Text") or "").strip()
                    name = text.split(" - ")[0].split(" — ")[0].strip()
                    if name and 2 <= len(name.split()) <= 6 and not is_hard_blocked(name):
                        out.append(name)
    except Exception as e:
        print("ddg discover fail", query, e, file=sys.stderr)
    return out


def discover_internet_titles(seen: set[str], want: int = 60) -> list[str]:
    pool: list[str] = []
    for t in load_trends():
        if not is_seen(seen, t):
            pool.append(t)

    qs = list(DISCOVER_QUERIES)
    random.shuffle(qs)
    for q in qs[:8]:
        for t in discover_ddg_related(q):
            if not is_seen(seen, t) and t not in pool:
                pool.append(t)
        if len(pool) >= want:
            break
        time.sleep(0.2)

    if not _WIKI_RATE_LIMITED and len(pool) < want:
        cats = list(WIKI_CATEGORY_SEEDS)
        random.shuffle(cats)
        for cat in cats[:5]:
            for t in discover_wiki_category(cat, limit=25):
                if not is_seen(seen, t) and t not in pool:
                    pool.append(t)
            if len(pool) >= want or _WIKI_RATE_LIMITED:
                break
            time.sleep(0.5)

    if not _WIKI_RATE_LIMITED and len(pool) < want:
        qs = list(DISCOVER_QUERIES)
        random.shuffle(qs)
        for q in qs[:4]:
            for t in discover_wiki_search(q, limit=10):
                if not is_seen(seen, t) and t not in pool:
                    pool.append(t)
            if len(pool) >= want or _WIKI_RATE_LIMITED:
                break
            time.sleep(0.4)

    fb = load_fallback_titles()
    random.shuffle(fb)
    for t in fb:
        if len(pool) >= want * 2:
            break
        if not is_seen(seen, t) and t not in pool and not is_hard_blocked(t):
            pool.append(t)

    pool = [t for t in pool if not is_hard_blocked(t)]
    filtered = []
    for t in pool:
        if is_school_safe(t) or any(
            x in t.lower()
            for x in (
                "force", "energy", "cell", "atom", "equation", "grammar",
                "essay", "math", "physics", "chem", "bio", "circuit", "dna",
                "acid", "base", "wave", "light", "sound", "heat", "plant",
            )
        ):
            filtered.append(t)
    pool = filtered or pool
    random.shuffle(pool)
    print("DISCOVERED_TITLES", len(pool), "wiki_limited=", _WIKI_RATE_LIMITED, file=sys.stderr)
    return pool[: max(want, 40)]


def summary_wikipedia(title: str) -> dict:
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED:
        return {}
    if is_hard_blocked(title):
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
        if is_hard_blocked(got):
            continue
        if not is_school_safe(got, extract) and not is_school_safe(title, extract):
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
    global _WIKI_RATE_LIMITED
    if _WIKI_RATE_LIMITED:
        return {}
    if is_hard_blocked(title):
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
                _WIKI_RATE_LIMITED = True
                time.sleep(5)
                return {}
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
                if is_hard_blocked(got):
                    continue
                if not is_school_safe(got, extract) and not is_school_safe(title, extract):
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
        time.sleep(0.35)
    return {}


def summary_duckduckgo(title: str) -> dict:
    if is_hard_blocked(title):
        return {}
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": f"{title} definition school science", "format": "json", "no_html": 1, "skip_disambig": 1},
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
        if is_hard_blocked(heading):
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


def synthetic_extract(title: str) -> dict:
    t = title.strip()
    extract = (
        f"{t} is an important topic in secondary school science and exam study. "
        f"Students learn what {t} means, how it works in everyday life, and how to "
        f"use simple examples and definitions in class. Understanding {t} helps with "
        f"WAEC, NECO and JAMB style questions. Teachers often explain {t} with a "
        f"short definition, one clear example, and a quick check question so learners "
        f"can remember it and apply it correctly."
    )
    return {
        "title": t,
        "extract": extract[:650],
        "description": "fallback-synthetic",
        "url": "",
        "bg": "classroom",
        "trend": False,
        "extract_source": "fallback",
    }


def summary(title: str) -> dict:
    order = (summary_duckduckgo, summary_wikipedia, summary_mediawiki)
    if _WIKI_RATE_LIMITED:
        order = (summary_duckduckgo,)
    for fn in order:
        s = fn(title)
        if s:
            return s
        time.sleep(0.25)
    return {}


def pick_from_fallback(seen: set[str]) -> dict | None:
    titles = load_fallback_titles()
    if not titles:
        return None
    random.shuffle(titles)
    tried = 0
    for t in titles:
        if tried >= 40:
            break
        if is_seen(seen, t) or is_hard_blocked(t):
            continue
        tried += 1
        s = summary(t)
        if not s:
            s = synthetic_extract(t)
        if s and not is_seen(seen, s["title"]):
            s["topic_source"] = "fallback+" + (s.get("extract_source") or "synthetic")
            return s
        time.sleep(0.15)
    for t in titles:
        if is_seen(seen, t) or is_hard_blocked(t):
            continue
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

    primary = discover_internet_titles(seen, want=50)
    candidates = []
    source_tag = "internet"

    for title in primary:
        if is_seen(seen, title) or is_hard_blocked(title):
            continue
        s = summary(title)
        if s and not is_seen(seen, s["title"]) and not is_hard_blocked(s["title"]):
            s["trend"] = False
            s["topic_source"] = source_tag + "+" + (s.get("extract_source") or "wiki")
            candidates.append(s)
        if len(candidates) >= 6:
            break
        time.sleep(0.2)

    if not candidates:
        print("INTERNET_EMPTY trying fallback bank", file=sys.stderr)
        fb = pick_from_fallback(seen)
        if fb:
            candidates = [fb]

    if not candidates:
        print("TOPIC_FAIL: no topics even from fallback bank", file=sys.stderr)
        sys.exit(1)

    pick = random.choice(candidates)
    save_seen(seen, pick["title"])
    out.write_text(json.dumps(pick, indent=2), encoding="utf-8")
    print("TOPIC_SOURCE", pick.get("topic_source"), pick.get("title"), file=sys.stderr)
    print(json.dumps(pick, indent=2))


if __name__ == "__main__":
    main()
