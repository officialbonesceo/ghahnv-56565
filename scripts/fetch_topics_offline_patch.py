#!/usr/bin/env python3
"""Inject strong offline fact-bank extracts into fetch_topics.py.

No template scripts. No softening of quality gates. Stronger topics only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "data" / "topic_facts.json"
FETCH = ROOT / "scripts" / "fetch_topics.py"


def main() -> None:
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(facts, dict) and len(facts) >= 40, "topic_facts.json too small"

    t = FETCH.read_text(encoding="utf-8")

    # Always refresh summary_offline body if present
    offline_fn = r'''
def summary_offline(title: str) -> dict:
    """Strong local extract from data/topic_facts.json — exam-grade, not filler."""
    if is_hard_blocked(title):
        return {}
    facts_path = ROOT / "data" / "topic_facts.json"
    facts: dict = {}
    try:
        if facts_path.exists():
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception as e:
        print("topic_facts load", e, file=sys.stderr)
        return {}
    if not isinstance(facts, dict) or not facts:
        return {}

    raw = (title or "").strip()
    # Strip common angle prefixes/suffixes to reach the core concept
    core = re.sub(
        r"(?i)^(types of|how|importance of|applications of|properties of|common mistakes in|exam tips on|revision on|key points on|factors affecting|uses of|ss[123]|jss|difference between|what is)\s+",
        "",
        raw,
    ).strip()
    core = re.sub(
        r"(?i)\s+(explained|definition|examples|formula|process|experiment|for WAEC|for JAMB|for NECO|for secondary school|in everyday life)$",
        "",
        core,
    ).strip() or raw

    extract = ""
    matched = ""
    # Exact / case-insensitive key match first
    for k, v in facts.items():
        if k.lower() == core.lower() or k.lower() == raw.lower():
            extract = (v or "").strip()
            matched = k
            break
    if not extract:
        # Substring match: prefer longest key contained in title/core
        candidates = sorted(facts.keys(), key=lambda x: len(x), reverse=True)
        for k in candidates:
            kl = k.lower()
            if len(kl) >= 4 and (kl in core.lower() or kl in raw.lower()):
                extract = (facts[k] or "").strip()
                matched = k
                break
    if len(extract) < 120:
        return {}
    # Prefer canonical strong title from the bank
    out_title = matched or core or raw
    if is_hard_blocked(out_title):
        return {}
    return {
        "title": out_title,
        "extract": extract[:650],
        "description": "offline fact-bank",
        "url": "",
        "bg": "classroom",
        "trend": False,
        "extract_source": "offline_facts",
    }

'''

    if "def summary_offline" in t:
        # Replace existing function through next top-level def at same indent
        import re as _re

        t2, n = _re.subn(
            r"\ndef summary_offline\(title: str\) -> dict:[\s\S]*?(?=\ndef )",
            "\n" + offline_fn.lstrip("\n"),
            t,
            count=1,
        )
        if n:
            t = t2
            print("replaced summary_offline")
        else:
            print("WARN could not replace summary_offline; injecting before pick_from_fallback")
            t = t.replace("def pick_from_fallback", offline_fn + "def pick_from_fallback", 1)
    else:
        t = t.replace("def pick_from_fallback", offline_fn + "def pick_from_fallback", 1)
        print("inserted summary_offline")

    # Ensure offline is last resort in getter chains (keep wiki/ddg first)
    t = t.replace(
        "for getter in (summary_wikipedia, summary_duckduckgo):",
        "for getter in (summary_wikipedia, summary_duckduckgo, summary_offline):",
    )
    # Prefer fact-bank titles when discovering offline candidates
    prefer_block = r'''
def prefer_factbank_titles(seen: set[str]) -> list[str]:
    """Titles that map to strong offline facts — use when network extracts fail."""
    facts_path = ROOT / "data" / "topic_facts.json"
    try:
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(facts, dict):
        return []
    out = []
    keys = list(facts.keys())
    random.shuffle(keys)
    for k in keys:
        if is_seen(seen, k) or is_hard_blocked(k):
            continue
        if len((facts.get(k) or "").strip()) < 120:
            continue
        out.append(k)
    return out

'''
    if "def prefer_factbank_titles" not in t:
        t = t.replace("def pick_from_fallback", prefer_block + "def pick_from_fallback", 1)

    # Rewrite pick_from_fallback to try fact-bank titles first with offline extract
    new_pick = r'''
def pick_from_fallback(seen: set[str]) -> dict | None:
    # 1) Strong fact-bank titles + offline extract (exam-grade)
    for title in prefer_factbank_titles(seen)[:80]:
        s = summary_offline(title)
        if s and len(s.get("extract") or "") >= 120 and is_school_safe(s["title"], s["extract"]):
            s["topic_source"] = "fallback+" + s.get("extract_source", "offline_facts")
            return s
    # 2) Broader title list with wiki/ddg then offline
    fb = load_fallback_titles()
    random.shuffle(fb)
    for title in fb[:200]:
        if is_seen(seen, title) or is_hard_blocked(title):
            continue
        for getter in (summary_wikipedia, summary_duckduckgo, summary_offline):
            s = getter(title)
            if s and len(s.get("extract") or "") >= 120 and is_school_safe(s["title"], s["extract"]):
                s["topic_source"] = "fallback+" + s.get("extract_source", "")
                return s
        time.sleep(0.1)
    return None
'''

    import re as _re

    t3, n3 = _re.subn(
        r"\ndef pick_from_fallback\(seen: set\[str\]\) -> dict \| None:[\s\S]*?(?=\ndef main\()",
        "\n" + new_pick.lstrip("\n") + "\n",
        t,
        count=1,
    )
    if n3:
        t = t3
        print("replaced pick_from_fallback")
    else:
        print("WARN pick_from_fallback replace failed")

    t = t.replace("headers=UA, timeout=25)", "headers=UA, timeout=6)")

    FETCH.write_text(t, encoding="utf-8")
    src = FETCH.read_text(encoding="utf-8")
    assert "summary_offline" in src
    assert "prefer_factbank_titles" in src
    assert "offline_facts" in src or "topic_facts" in src
    print("OK patched", FETCH)


if __name__ == "__main__":
    main()
