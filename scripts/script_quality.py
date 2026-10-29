#!/usr/bin/env python3
"""Reject weak or gibberish spoken scripts before they become videos."""
from __future__ import annotations

import re

GIBBERISH = re.compile(
    r"(?i)("
    r"teachers?\s+asks?|topic\s+to\s+\w+|introduce\s+to\s+\w+|"
    r"wire[, ]+jam|jam\s+and\s+nickel|for\s+wire|"
    r"is\s+important\s+for\s+waec\s+jamb|"
    r"share,\s*save\s+and\s+pull|save\s+and\s+pull|"
    r"they:\s*|you:\s*|i:\s*hello,?\s*class|"
    r"important topic in secondary school|"
    r"helps with waec,?\s*neco and jamb style|"
    r"teachers often explain .{1,40} with a short definition"
    r")"
)

DIALOGUE_DUMP = re.compile(
    r"(?is)(THEY:\s*|YOU:\s*|I:\s*|Student:\s*|Teacher:\s*){2,}"
)

EMPTY_HOOK = re.compile(
    r"(?i)^(exam trap on .{1,40}\?\s*fix it in under a minute\.?|"
    r"most students lose marks on .{1,40} — here is the clean version\.?)"
)

EXAMPLE_MARK = re.compile(
    r"(?i)\b("
    r"for example|when you|imagine|think of|like when|in the kitchen|"
    r"on the (road|bus)|your (phone|body|hand)|a (ball|car|bottle|metal)|"
    r"because|means that|is when|called|this happens|in real life|"
    r"rust|iron|oxygen|apple|cut|breath|respir|battery|fuel|burn"
    r")\b"
)

CTA_TAIL = re.compile(
    r"(?is)(tap the bookmark.*|share it with a classmate.*|follow for daily.*)$"
)


def body_without_cta(script: str) -> str:
    s = (script or "").strip()
    s = CTA_TAIL.sub("", s).strip()
    return s


def is_weak_script(script: str, topic: str = "") -> str | None:
    """Return reason string if weak, else None."""
    s = (script or "").strip()
    if not s:
        return "empty"
    if GIBBERISH.search(s):
        return "gibberish_or_synthetic"
    if DIALOGUE_DUMP.search(s):
        return "dialogue_dump"
    body = body_without_cta(s)
    words = body.split()
    if len(words) < 70:
        return f"too_short_body:{len(words)}"
    if not EXAMPLE_MARK.search(body):
        return "no_example_or_explanation"
    head = " ".join(words[:35]).lower()
    if re.search(r"(?i)^(today'?s topic|the topic is|our topic|teachers?|hello,? class)\b", head):
        return "textbook_open"
    if EMPTY_HOOK.search(body[:120]) and len(words) < 90:
        return "empty_exam_trap_hook"
    if re.search(r"(?i)\b(they|you|student|teacher)\s*:\s*\w+", body):
        return "role_labels"
    # pure padding about exams without science content
    if re.search(r"(?i)waec|jamb|neco", body) and not re.search(
        r"(?i)\b(energy|force|cell|heat|light|wave|atom|mass|oxygen|rust|"
        r"acid|base|current|pressure|oxid|reduc|electron|metal)\b",
        body,
    ):
        return "exam_padding_no_science"
    return None


def is_broad_topic_title(title: str) -> bool:
    """Block vague curriculum shells that produce empty lessons."""
    t = (title or "").strip()
    if re.match(
        r"(?i)^(introduction|intro|basics?|overview|summary|revision)\s+(to|of|on)\b",
        t,
    ):
        return True
    if re.match(r"(?i)^(introduction|intro)\s+to\b", t):
        return True
    # Applications of X with no specificity often becomes synthetic fluff
    if re.match(r"(?i)^applications? of\s+\w+$", t):
        return True
    if re.fullmatch(r"(?i)(radiation|energy|force|matter|science|biology|physics|chemistry)", t):
        return True
    return False


def is_synthetic_extract(extract: str = "", source: str = "") -> bool:
    if (source or "").lower() in ("fallback", "fallback-synthetic", "synthetic"):
        return True
    e = (extract or "").lower()
    if "important topic in secondary school" in e:
        return True
    if "helps with waec, neco and jamb style" in e:
        return True
    return False
