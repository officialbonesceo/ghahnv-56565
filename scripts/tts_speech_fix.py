#!/usr/bin/env python3
"""TTS-safe spoken text: no 'one dot' list markers, no long step dumps."""
from __future__ import annotations
import re

ORD = {
    "1": "Number one", "2": "Number two", "3": "Number three", "4": "Number four",
    "5": "Number five", "6": "Number six", "7": "Number seven", "8": "Number eight",
    "9": "Number nine", "10": "Number ten",
}

def speakable_numbers(text: str) -> str:
    def repl(m):
        n = m.group(2)
        return m.group(1) + ORD.get(n, f"Number {n}") + ","
    t = re.sub(r"(?m)(^|\s)(\d{1,2})[.)]\s+", repl, text or "")
    t = re.sub(
        r"\b(\d{1,2})[.)](?=\s*[A-Za-z])",
        lambda m: ORD.get(m.group(1), f"Number {m.group(1)}") + ",",
        t,
    )
    return re.sub(r"\s+", " ", t).strip()

def is_boring_step_dump(text: str) -> bool:
    head = " ".join((text or "").split()[:45]).lower()
    if re.search(r"\bsteps? to (answer|solv|approach|write|do)\b", head):
        return True
    if re.search(r"\b(here are the steps|follow these steps|the steps are|step by step)\b", head):
        return True
    early = " ".join((text or "").split()[:90])
    if len(re.findall(r"\bNumber (one|two|three|four|five|six|seven|eight)\b", early, re.I)) >= 3:
        return True
    if len(re.findall(r"(?:^|[\s])\d{1,2}[.)]\s+", " " + early)) >= 3:
        return True
    return False

def strip_step_intro(text: str) -> str:
    s = (text or "").strip()
    s = re.sub(r"(?i)^(steps? to (answer|solv|approach|write|do)[^.]*\.\s*)+", "", s).strip()
    s = re.sub(r"(?i)^(here are the steps[^.]*\.\s*)+", "", s).strip()
    return s
