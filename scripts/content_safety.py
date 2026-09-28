#!/usr/bin/env python3
"""Shared topic/script filters — school STEM/exam only; TikTok-safe."""
from __future__ import annotations

import re

BLOCK_RE = re.compile(
    r"\b("
    r"religion|religious|god|gods|jesus|christ|christian|christianity|bible|church|"
    r"islam|muslim|quran|koran|allah|hindu|hinduism|buddhist|buddhism|"
    r"jew|jewish|judaism|torah|sikh|sikhism|"
    r"cult|sect|occult|witchcraft|satan|devil|demon|hell|heaven|prayer|pray|"
    r"pastor|priest|imam|mosque|temple|synagogue|faith|worship|miracle|"
    r"prophet|apostle|gospel|sermon|theology|atheism|atheist|"
    r"politic|election|president|senator|party politics|"
    r"porn|sex|nude|nsfw|drug deal|cocaine|heroin|"
    r"terror|bomb|shooting|massacre|genocide|holocaust denial|"
    r"conspiracy|illuminati|flat earth|"
    # celebrities / entertainment noise (not exam syllabus)
    r"actress|actor|celebrity|singer|rapper|footballer|nba|netflix|"
    r"k-pop|kpop|idol|hollywood|idol|hollywood drama|hollywood"
    r")\b",
    re.I,
)

# Must look like school syllabus content
ALLOW_HINT_RE = re.compile(
    r"\b("
    r"math|algebra|geometry|trigonometry|calculus|quadratic|fraction|percentage|"
    r"ratio|average|pythagorean|equation|statistics|probability|"
    r"physics|force|energy|motion|electric|circuit|magnet|light|sound|heat|"
    r"inertia|momentum|pressure|density|friction|gravity|newton|ohm|"
    r"chemistry|atom|molecule|acid|base|enzyme|catalyst|bond|reaction|"
    r"biology|cell|dna|mitosis|meiosis|photosynthesis|osmosis|diffusion|"
    r"respiration|heart|lung|brain|blood|vaccine|genetics|heredity|"
    r"earth|volcano|earthquake|moon|solar|climate|water cycle|rock cycle|"
    r"essay|paragraph|grammar|comprehension|literature|"
    r"exam|study|memory|sleep|waec|jamb|neco|ssce|scheme of work|syllabus"
    r")\b",
    re.I,
)


def is_blocked(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return bool(BLOCK_RE.search(t))


def is_school_safe(title: str, extract: str = "") -> bool:
    """True only if not blocked AND looks like school STEM/exam content."""
    blob = f"{title} {extract}"
    if is_blocked(blob) or is_blocked(title):
        return False
    # Title must carry a syllabus-ish hint (blocks random people/pages)
    if not ALLOW_HINT_RE.search(title) and not ALLOW_HINT_RE.search(extract[:200]):
        return False
    return True


def filter_title_list(titles: list[str]) -> list[str]:
    out = []
    for t in titles:
        if not is_school_safe(t):
            continue
        out.append(t)
    return out
