#!/usr/bin/env python3
"""Offline school facts when wiki/DDG are down."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "data" / "topic_facts.json"


def clean_query_title(title: str) -> str:
    t = (title or "").strip()
    t = re.sub(
        r"(?i)\s+(for\s+(waec|jamb|neco|secondary\s+school)|in\s+everyday\s+life|explained|examples?|formula|process|experiment)$",
        "",
        t,
    )
    t = re.sub(
        r"(?i)^(how\s+|types? of\s+|importance of\s+|uses of\s+|factors affecting\s+|applications of\s+|ss[123]\s+|jss\s+)",
        "",
        t,
    )
    return (t.strip(" -:") or title)[:60]


def fact_bank_extract(title: str) -> dict:
    if not BANK_PATH.exists():
        return {}
    try:
        bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(bank, dict):
        return {}
    key = clean_query_title(title)
    for k, v in bank.items():
        if k.lower() == key.lower() or k.lower() == (title or "").strip().lower():
            text = str(v).strip()
            if len(text) >= 80:
                return {
                    "title": k,
                    "extract": text[:650],
                    "description": "fact-bank",
                    "url": "",
                    "bg": "classroom",
                    "trend": False,
                    "extract_source": "fact-bank",
                }
    kl = key.lower()
    for k, v in bank.items():
        kk = k.lower()
        if len(kk) >= 4 and (kk in kl or kl in kk):
            text = str(v).strip()
            if len(text) >= 80:
                return {
                    "title": k,
                    "extract": text[:650],
                    "description": "fact-bank",
                    "url": "",
                    "bg": "classroom",
                    "trend": False,
                    "extract_source": "fact-bank",
                }
    return {}
