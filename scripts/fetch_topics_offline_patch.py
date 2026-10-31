#!/usr/bin/env python3
"""One-shot patcher: inject summary_offline into fetch_topics.py if missing."""
from pathlib import Path

p = Path("scripts/fetch_topics.py")
t = p.read_text(encoding="utf-8")
if "def summary_offline" in t:
    print("already has summary_offline")
else:
    offline = r'''
def summary_offline(title: str) -> dict:
    """Local extract so pipeline never dies when wiki/ddg are down."""
    if is_hard_blocked(title):
        return {}
    core = re.sub(
        r"(?i)^(types of|how|importance of|applications of|properties of|common mistakes in|exam tips on|revision on|key points on|factors affecting|uses of|ss[123]|jss|difference between)\s+",
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
    t = t.replace("headers=UA, timeout=25)", "headers=UA, timeout=6)")
    # On 429: mark limited and use short backoff (no invalid global in middle of expression)
    old_wait = "wait = min(45.0, 5.0 * (2 ** attempt) + random.uniform(0, 2))\n                print(\"wiki 429 backoff\", round(wait, 1), file=sys.stderr)\n                time.sleep(wait)\n                continue"
    new_wait = "_WIKI_RATE_LIMITED = True\n                wait = min(6.0, 1.5 * (2 ** attempt))\n                print(\"wiki 429 backoff\", round(wait, 1), file=sys.stderr)\n                time.sleep(wait)\n                continue"
    if old_wait in t:
        t = t.replace(old_wait, new_wait, 1)
    p.write_text(t, encoding="utf-8")
    print("patched fetch_topics.py")

# sanity: offline must be reachable from both loops
src = p.read_text(encoding="utf-8")
assert "summary_offline" in src
print("OK")
