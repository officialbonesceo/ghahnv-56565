#!/usr/bin/env python3
"""Shared topic/script filters — school STEM only; TikTok/platform-safe."""
from __future__ import annotations

import re

# Hard block: religion, cults, politics, adult, violence, conspiracy
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
    r"conspiracy|illuminati|flat earth"
    r")\b",
    re.I,
)

# Prefer clear school subjects only when trends are messy
ALLOW_HINT_RE = re.compile(
    r"\b("
    r"math|algebra|geometry|quadratic|fraction|percentage|ratio|average|"
    r"physics|force|energy|motion|electric|circuit|magnet|light|sound|heat|"
    r"chemistry|atom|molecule|acid|base|enzyme|catalyst|"
    r"biology|cell|dna|mitosis|meiosis|photosynthesis|osmosis|diffusion|"
    r"respiration|heart|lung|brain|blood|vaccine|"
    r"earth|volcano|earthquake|moon|solar|climate|water cycle|"
    r"essay|paragraph|exam|study|memory|sleep|friction|gravity|newton"
    r")\b",
    re.I,
)


def is_blocked(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return bool(BLOCK_RE.search(t))


def is_school_safe(title: str, extract: str = "") -> bool:
    """True only if not blocked and looks like school STEM/study content."""
    blob = f"{title} {extract}"
    if is_blocked(blob):
        return False
    # Title alone blocked?
    if is_blocked(title):
        return False
    return True


def filter_title_list(titles: list[str]) -> list[str]:
    out = []
    for t in titles:
        if not is_school_safe(t):
            continue
        out.append(t)
    return out
