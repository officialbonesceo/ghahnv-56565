#!/usr/bin/env python3
"""Daily brain-teaser job: pick format + puzzle + spoken script (no LLM required)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# School-flavoured teasers — auto-drawn in render_teaser.py
# Outline shapes must be clear geometry (no blob silhouettes).
BANK = [
    # --- OPTIONS (exam traps) ---
    {
        "format": "options",
        "title": "Series or parallel?",
        "hook": "Quick circuit check. Most students mix these up.",
        "question": "Two bulbs on one path, same current through both. What is it?",
        "choices": ["A) Series", "B) Parallel", "C) Both"],
        "answer": "A",
        "reason": "One path means series — same current through each bulb.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Speed vs velocity",
        "hook": "Exam trap in one line.",
        "question": "Which one needs direction?",
        "choices": ["A) Speed only", "B) Velocity only", "C) Both the same"],
        "answer": "B",
        "reason": "Velocity is speed with direction. Speed is scalar.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Osmosis direction",
        "hook": "Biology paper favourite.",
        "question": "Water moves through a membrane toward the side with…",
        "choices": ["A) Less solute", "B) More solute", "C) Equal solute always"],
        "answer": "B",
        "reason": "Osmosis: water moves to the higher solute concentration side.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Newton first law",
        "hook": "Inertia in plain words.",
        "question": "A book on a table stays still because…",
        "choices": ["A) No force at all", "B) Balanced forces / inertia", "C) Gravity switched off"],
        "answer": "B",
        "reason": "Forces balance. Inertia keeps it at rest until a net force acts.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Fraction of 1/2 of 1/3",
        "hook": "Quick maths. Comment before the reveal.",
        "question": "What is one half of one third?",
        "choices": ["A) 1/5", "B) 1/6", "C) 2/3"],
        "answer": "B",
        "reason": "Half of one third is one sixth. Multiply: 1/2 times 1/3 equals 1/6.",
        "visual": {"kind": "options"},
    },
    # --- OUTLINE match (clear geometry only) ---
    {
        "format": "outline",
        "title": "Triangle outline",
        "hook": "99 percent rush this. Look once.",
        "question": "Which shape matches the red outline?",
        "choices": ["A) Circle", "B) Triangle", "C) Square"],
        "answer": "B",
        "reason": "Three sides — the outline is a triangle.",
        "visual": {
            "kind": "outline",
            "shape": "triangle",
            "correct_index": 1,
            "choices": ["circle", "triangle", "square"],
        },
    },
    {
        "format": "outline",
        "title": "Star outline",
        "hook": "Match the outline. Comment A B or C.",
        "question": "Which shape matches the red outline?",
        "choices": ["A) Square", "B) Circle", "C) Star"],
        "answer": "C",
        "reason": "Five points — the outline is a star.",
        "visual": {
            "kind": "outline",
            "shape": "star",
            "correct_index": 2,
            "choices": ["square", "circle", "star"],
        },
    },
    {
        "format": "outline",
        "title": "House outline",
        "hook": "Simple shape. Easy to mis-click.",
        "question": "Which shape matches the red outline?",
        "choices": ["A) House", "B) Circle", "C) Triangle"],
        "answer": "A",
        "reason": "Square base plus roof — the outline is a house.",
        "visual": {
            "kind": "outline",
            "shape": "house",
            "correct_index": 0,
            "choices": ["house", "circle", "triangle"],
        },
    },
    {
        "format": "outline",
        "title": "Egg count",
        "hook": "Count before you comment.",
        "question": "How many eggs match the outline row?",
        "choices": ["A) 2", "B) 3", "C) 4"],
        "answer": "B",
        "reason": "Three outline eggs — answer is three.",
        "visual": {
            "kind": "outline",
            "shape": "eggs",
            "correct_index": 1,
        },
    },
    # --- TRAFFIC / path logic ---
    {
        "format": "traffic",
        "title": "Which car reverses?",
        "hook": "Test your brain. Road logic.",
        "question": "Which numbered car in reverse clears the jam?",
        "choices": ["3", "5", "7"],
        "answer": "3",
        "reason": "Car 3 can reverse out and free the path in this layout.",
        "visual": {"kind": "traffic", "correct": 3},
    },
    {
        "format": "traffic",
        "title": "Exit lane",
        "hook": "One move solves it.",
        "question": "Which car must move first?",
        "choices": ["1", "4", "6"],
        "answer": "4",
        "reason": "Car 4 blocks the middle path — move it first.",
        "visual": {"kind": "traffic", "correct": 4},
    },
    # --- PATTERN / number ---
    {
        "format": "pattern",
        "title": "Missing number",
        "hook": "Pattern check. Comment the missing number.",
        "question": "2, 4, 8, 16, question mark.",
        "choices": ["A) 24", "B) 32", "C) 20"],
        "answer": "B",
        "reason": "Each term doubles. 16 times 2 is 32.",
        "visual": {"kind": "pattern", "seq": [2, 4, 8, 16, "?"]},
    },
    {
        "format": "pattern",
        "title": "Odd one out",
        "hook": "One does not belong.",
        "question": "Which number breaks the pattern: 3, 6, 9, 15, 12?",
        "choices": ["A) 15", "B) 12", "C) 9"],
        "answer": "A",
        "reason": "Multiples of 3 in order go 3, 6, 9, 12 — 15 is out of place.",
        "visual": {"kind": "pattern", "seq": [3, 6, 9, 15, 12]},
    },
]


def pick() -> dict:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    h = int(hashlib.md5(day.encode()).hexdigest(), 16)
    item = BANK[h % len(BANK)].copy()
    item["id"] = f"teaser-{day}-{item['format']}"
    item["picked_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return item


def build_script(item: dict) -> str:
    choices = " ".join(item["choices"])
    return (
        f"{item['hook']} {item['question']} "
        f"Options: {choices}. "
        f"Pause and comment your answer. "
        f"The correct answer is {item['answer']}. {item['reason']} "
        f"Comment the next topic you want us to treat. Follow for more."
    )


def main() -> None:
    item = pick()
    script = build_script(item)
    out = {
        **item,
        "script": script,
        "cta": "Comment the next topic you want us to treat. Follow for more.",
        "short_title": item["title"][:40],
    }
    Path("teaser_job.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    Path("script.txt").write_text(script + "\n", encoding="utf-8")
    Path("title_short.txt").write_text(out["short_title"], encoding="utf-8")
    Path("cta.txt").write_text(out["cta"], encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        f"{out['short_title']} — comment your answer\n\n"
        f"{out['cta']}\n\n"
        f"#brainteaser #examtips #study #fyp #learntok #waec",
        encoding="utf-8",
    )
    Path("tiktok_comment.txt").write_text(
        f"Answer: {item['answer']} — {item['reason'][:80]}",
        encoding="utf-8",
    )
    print(json.dumps(out, indent=2))
    print("TEASER", item["format"], item["title"], "answer", item["answer"], file=sys.stderr)


if __name__ == "__main__":
    main()
