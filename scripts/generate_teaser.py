#!/usr/bin/env python3
"""Daily brain-teaser job: harder exam-style puzzles (no LLM required)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Harder school teasers — designed so a rushed answer fails
BANK = [
    # --- OPTIONS: real exam traps ---
    {
        "format": "options",
        "title": "Current in series",
        "hook": "Most students pick the wrong one under pressure.",
        "question": "Three identical resistors in series on 12 V. Current through the middle one is…",
        "choices": ["A) Same as the others", "B) Half of the first", "C) Zero"],
        "answer": "A",
        "reason": "Series current is the same through every component.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Velocity trap",
        "hook": "Exam favourite. Think before you comment.",
        "question": "A car goes 60 km north then 60 km south in 2 hours. Average velocity is…",
        "choices": ["A) 60 km/h", "B) 0", "C) 120 km/h"],
        "answer": "B",
        "reason": "Displacement is zero, so average velocity is zero. Speed is not zero.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Osmosis vs diffusion",
        "hook": "Biology paper trap.",
        "question": "Movement of water only, through a selectively permeable membrane, is…",
        "choices": ["A) Diffusion", "B) Osmosis", "C) Active transport"],
        "answer": "B",
        "reason": "Osmosis is water through a selectively permeable membrane.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Inertia myth",
        "hook": "Newton question students rush.",
        "question": "A moving object keeps moving at constant velocity when…",
        "choices": ["A) A force pushes it forever", "B) Net force is zero", "C) Gravity is removed"],
        "answer": "B",
        "reason": "First law: constant velocity when net force is zero — including zero force.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Half of a third",
        "hook": "Quick maths. Most pick 2/3 by mistake.",
        "question": "What is one half of one third?",
        "choices": ["A) 2/3", "B) 1/6", "C) 1/5"],
        "answer": "B",
        "reason": "Multiply: 1/2 × 1/3 = 1/6. Not 2/3.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "pH of acid",
        "hook": "Chemistry trap.",
        "question": "A solution with pH 3 compared to pH 5 is…",
        "choices": ["A) 2 times more acidic", "B) 100 times more acidic", "C) Less acidic"],
        "answer": "B",
        "reason": "Each pH step is ×10. Two steps = 100 times more H+.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Work done",
        "hook": "Physics definition check.",
        "question": "You push a wall as hard as you can. The wall does not move. Work done is…",
        "choices": ["A) Maximum", "B) Zero", "C) Equal to your force"],
        "answer": "B",
        "reason": "Work needs displacement. No movement means zero work.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Photosynthesis gas",
        "hook": "Do not confuse with respiration.",
        "question": "Gas released by green plants in light is mainly…",
        "choices": ["A) Carbon dioxide", "B) Oxygen", "C) Nitrogen"],
        "answer": "B",
        "reason": "Photosynthesis releases oxygen. Respiration releases CO2.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Percentage trap",
        "hook": "WAEC-style number trap.",
        "question": "A shirt costs 800. Discount 25%. Sale price is…",
        "choices": ["A) 600", "B) 200", "C) 825"],
        "answer": "A",
        "reason": "25% of 800 is 200. Sale price = 800 − 200 = 600.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Parallel resistors",
        "hook": "Harder circuit question.",
        "question": "Two 4 ohm resistors in parallel. Combined resistance is…",
        "choices": ["A) 8 ohm", "B) 2 ohm", "C) 4 ohm"],
        "answer": "B",
        "reason": "Equal parallels: R/2. So 4/2 = 2 ohm.",
        "visual": {"kind": "options"},
    },
    # --- OUTLINE: only one harder visual count ---
    {
        "format": "outline",
        "title": "Egg count",
        "hook": "Count carefully. Easy to mis-count on a phone.",
        "question": "How many eggs match the outline row?",
        "choices": ["A) 2", "B) 3", "C) 4"],
        "answer": "B",
        "reason": "Three outline eggs — answer is three.",
        "visual": {"kind": "outline", "shape": "eggs", "correct_index": 1},
    },
    {
        "format": "outline",
        "title": "Star outline",
        "hook": "Shape match. Look at the points.",
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
    # --- TRAFFIC ---
    {
        "format": "traffic",
        "title": "Which car reverses?",
        "hook": "Road logic. One number frees the jam.",
        "question": "Which numbered car in reverse clears the jam?",
        "choices": ["3", "5", "7"],
        "answer": "3",
        "reason": "Car 3 can reverse out and free the path in this layout.",
        "visual": {"kind": "traffic", "correct": 3},
    },
    {
        "format": "traffic",
        "title": "Exit lane",
        "hook": "One move first. Which car?",
        "question": "Which car must move first?",
        "choices": ["1", "4", "6"],
        "answer": "4",
        "reason": "Car 4 blocks the middle path — move it first.",
        "visual": {"kind": "traffic", "correct": 4},
    },
    # --- PATTERN: multi-step ---
    {
        "format": "pattern",
        "title": "Missing number",
        "hook": "Not simple doubling. Look twice.",
        "question": "3, 6, 11, 18, question mark.",
        "choices": ["A) 27", "B) 25", "C) 30"],
        "answer": "A",
        "reason": "Add 3, 5, 7, 9… Next add 9 → 18+9=27.",
        "visual": {"kind": "pattern", "seq": [3, 6, 11, 18, "?"]},
    },
    {
        "format": "pattern",
        "title": "Odd one out",
        "hook": "One number breaks the rule.",
        "question": "Which breaks the pattern: 2, 3, 5, 7, 9, 11?",
        "choices": ["A) 9", "B) 11", "C) 7"],
        "answer": "A",
        "reason": "Primes: 2,3,5,7,11. Nine is not prime.",
        "visual": {"kind": "pattern", "seq": [2, 3, 5, 7, 9, 11]},
    },
    {
        "format": "pattern",
        "title": "Square numbers",
        "hook": "Pattern from junior secondary maths.",
        "question": "1, 4, 9, 16, question mark.",
        "choices": ["A) 20", "B) 25", "C) 24"],
        "answer": "B",
        "reason": "Squares: 1² 2² 3² 4² 5² → 25.",
        "visual": {"kind": "pattern", "seq": [1, 4, 9, 16, "?"]},
    },
    {
        "format": "pattern",
        "title": "Ratio step",
        "hook": "Harder sequence.",
        "question": "2, 6, 12, 20, question mark.",
        "choices": ["A) 30", "B) 28", "C) 24"],
        "answer": "A",
        "reason": "Add 4, 6, 8, 10… Next 20+10=30.",
        "visual": {"kind": "pattern", "seq": [2, 6, 12, 20, "?"]},
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
        f"#brainteaser #examtips #study #fyp #learntok #waec #jamb",
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
