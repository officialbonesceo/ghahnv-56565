#!/usr/bin/env python3
"""Daily brain-teaser: medium exam Q&A only (no hard SVG riddles)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Medium difficulty — imaginable, not baby, not olympiad
BANK = [
    {
        "title": "Series current",
        "hook": "Quick exam check.",
        "question": "Three same resistors in series. Current in the middle one is…",
        "choices": ["A) Same as the others", "B) Half of the first", "C) Zero"],
        "answer": "A",
        "reason": "Series: same current through every part.",
    },
    {
        "title": "Average velocity",
        "hook": "Trap question.",
        "question": "60 km north then 60 km south in 2 hours. Average velocity?",
        "choices": ["A) 60 km/h", "B) 0", "C) 120 km/h"],
        "answer": "B",
        "reason": "Back to start — displacement zero, velocity zero.",
    },
    {
        "title": "Work on a wall",
        "hook": "Physics definition.",
        "question": "You push a wall hard. It does not move. Work done is…",
        "choices": ["A) Maximum", "B) Zero", "C) Equal to force"],
        "answer": "B",
        "reason": "No movement means no work.",
    },
    {
        "title": "Parallel resistors",
        "hook": "Circuit basics.",
        "question": "Two 4 ohm resistors in parallel. Combined resistance?",
        "choices": ["A) 8 ohm", "B) 2 ohm", "C) 4 ohm"],
        "answer": "B",
        "reason": "Equal parallels: half → 2 ohm.",
    },
    {
        "title": "pH step",
        "hook": "Chemistry.",
        "question": "pH 3 compared to pH 5 is…",
        "choices": ["A) 2× more acidic", "B) 100× more acidic", "C) Less acidic"],
        "answer": "B",
        "reason": "Each pH step is ×10. Two steps = 100×.",
    },
    {
        "title": "Osmosis",
        "hook": "Biology trap.",
        "question": "Water only, through a selectively permeable membrane, is…",
        "choices": ["A) Diffusion", "B) Osmosis", "C) Active transport"],
        "answer": "B",
        "reason": "That is the definition of osmosis.",
    },
    {
        "title": "Photosynthesis gas",
        "hook": "Do not mix with respiration.",
        "question": "Gas released by green plants in light is mainly…",
        "choices": ["A) Carbon dioxide", "B) Oxygen", "C) Nitrogen"],
        "answer": "B",
        "reason": "Photosynthesis releases oxygen.",
    },
    {
        "title": "Half of a third",
        "hook": "Quick maths.",
        "question": "What is one half of one third?",
        "choices": ["A) 2/3", "B) 1/6", "C) 1/5"],
        "answer": "B",
        "reason": "1/2 × 1/3 = 1/6.",
    },
    {
        "title": "Discount",
        "hook": "WAEC-style %.",
        "question": "Shirt costs 800. 25% off. Sale price?",
        "choices": ["A) 600", "B) 200", "C) 825"],
        "answer": "A",
        "reason": "25% of 800 is 200. Sale = 600.",
    },
    {
        "title": "Triangle angles",
        "hook": "Geometry.",
        "question": "Angles in a triangle add up to…",
        "choices": ["A) 90°", "B) 180°", "C) 360°"],
        "answer": "B",
        "reason": "Always 180 degrees.",
    },
    {
        "title": "Speed vs velocity",
        "hook": "True or false style.",
        "question": "Speed is a vector quantity.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Speed is scalar. Velocity is vector.",
    },
    {
        "title": "Mass on the moon",
        "hook": "True or false.",
        "question": "Mass changes when you go to the moon.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Mass stays the same. Weight changes.",
    },
    {
        "title": "Plants at night",
        "hook": "Biology.",
        "question": "Plants only respire at night.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Respiration is day and night.",
    },
    {
        "title": "Cold bottle",
        "hook": "Everyday science.",
        "question": "Cold bottle from fridge gets wet outside because…",
        "choices": ["A) Water leaked", "B) Moisture condensed", "C) Plastic melted"],
        "answer": "B",
        "reason": "Warm air moisture condenses on the cold surface.",
    },
    {
        "title": "Power formula",
        "hook": "Electricity.",
        "question": "Electrical power P equals…",
        "choices": ["A) V × I", "B) V ÷ I", "C) V + I"],
        "answer": "A",
        "reason": "P = VI.",
    },
    {
        "title": "Acceleration",
        "hook": "Definition.",
        "question": "Acceleration is rate of change of…",
        "choices": ["A) Distance", "B) Velocity", "C) Mass"],
        "answer": "B",
        "reason": "Acceleration = change of velocity over time.",
    },
    {
        "title": "Neutralisation",
        "hook": "Chemistry.",
        "question": "Acid + base mainly produces…",
        "choices": ["A) Salt and water", "B) Only gas", "C) Only acid"],
        "answer": "A",
        "reason": "Neutralisation → salt + water.",
    },
    {
        "title": "Heart",
        "hook": "Human body.",
        "question": "Which organ pumps blood?",
        "choices": ["A) Lungs", "B) Heart", "C) Liver"],
        "answer": "B",
        "reason": "The heart pumps blood.",
    },
    {
        "title": "Mean",
        "hook": "Maths.",
        "question": "Mean of 2, 4, 6, 8 is…",
        "choices": ["A) 4", "B) 5", "C) 6"],
        "answer": "B",
        "reason": "Sum 20 ÷ 4 = 5.",
    },
    {
        "title": "Square pattern",
        "hook": "Find the next number.",
        "question": "1, 4, 9, 16, ?",
        "choices": ["A) 20", "B) 25", "C) 24"],
        "answer": "B",
        "reason": "1² 2² 3² 4² 5² → 25.",
    },
]


def pick() -> dict:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    h = int(hashlib.md5(day.encode()).hexdigest(), 16)
    item = BANK[h % len(BANK)].copy()
    item["format"] = "options"
    item["visual"] = {"kind": "options"}
    item["id"] = f"teaser-{day}-{h % len(BANK)}"
    item["picked_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return item


def build_script(item: dict) -> str:
    choices = ". ".join(item["choices"])
    # Short script so on-screen 5s countdown can breathe
    return (
        f"{item['hook']} {item['question']} "
        f"{choices}. "
        f"You have five seconds. Comment your answer. "
        f"The answer is {item['answer']}. {item['reason']} "
        f"Comment the next topic. Follow for more."
    )


def main() -> None:
    item = pick()
    script = build_script(item)
    out = {
        **item,
        "script": script,
        "cta": "Comment the next topic. Follow for more.",
        "short_title": item["title"][:40],
        "countdown_seconds": 5,
    }
    Path("teaser_job.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    Path("script.txt").write_text(script + "\n", encoding="utf-8")
    Path("title_short.txt").write_text(out["short_title"], encoding="utf-8")
    Path("cta.txt").write_text(out["cta"], encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        f"{out['short_title']} — comment A B or C\n\n"
        f"{out['cta']}\n\n"
        f"#brainteaser #examtips #study #fyp #learntok #waec #jamb",
        encoding="utf-8",
    )
    Path("tiktok_comment.txt").write_text(
        f"Answer: {item['answer']} — {item['reason'][:80]}",
        encoding="utf-8",
    )
    print(json.dumps(out, indent=2))
    print("TEASER", item["title"], "answer", item["answer"], file=sys.stderr)


if __name__ == "__main__":
    main()
