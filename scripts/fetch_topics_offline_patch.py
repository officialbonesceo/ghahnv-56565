#!/usr/bin/env python3
"""One-shot patcher: inject summary_offline into fetch_topics.py if missing."""
from pathlib import Path

p = Path("scripts/fetch_topics.py")
t = p.read_text(encoding="utf-8")
if "def summary_offline" in t:
    print("already has summary_offline")
else:
    offline = '''
def summary_offline(title: str) -> dict:
    """Local extract so pipeline never dies when wiki/ddg are down."""
    if is_hard_blocked(title):
        return {}
    core = re.sub(
        r"(?i)^(types of|how|importance of|applications of|properties of|common mistakes in|exam tips on|revision on|key points on|factors affecting|uses of|ss[123]|jss|difference between)\\s+",
        "",
        title or "",
    ).strip() or (title or "this topic")
    extract = (
        f"{title} is a core secondary-school topic for WAEC, NECO and JAMB. "
        f"Students should understand what {core} means, recognise simple everyday examples, "
        f"and avoid common exam mistakes. Focus on clear definition, one worked idea, and why it matters."
    )
    return {
        "title": title,
        "extract": extract[:650],
        "description": "offline bank",
        "url": "",
        "bg": "classroom",
        "trend": False,
        "extract_source": "offline",
    }

'''
    t = t.replace("def pick_from_fallback", offline + "def pick_from_fallback", 1)
    t = t.replace(
        "for getter in (summary_wikipedia, summary_duckduckgo):",
        "for getter in (summary_wikipedia, summary_duckduckgo, summary_offline):",
    )
    # shorter timeouts
    t = t.replace("headers=UA, timeout=25)", "headers=UA, timeout=6)")
    t = t.replace(
        "wait = min(45.0, 5.0 * (2 ** attempt) + random.uniform(0, 2))",
        "wait = min(6.0, 1.5 * (2 ** attempt)); global _WIKI_RATE_LIMITED; _WIKI_RATE_LIMITED = True",
    )
    p.write_text(t, encoding="utf-8")
    print("patched fetch_topics.py")
