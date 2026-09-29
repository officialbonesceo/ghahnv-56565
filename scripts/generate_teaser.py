#!/usr/bin/env python3
"""Daily brain-teaser job: expanded exam traps, T/F, what-happens-next (no LLM)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Expanded bank — rushed answers fail; school-aligned
BANK = [
    # ========== OPTIONS: physics ==========
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
        "reason": "Displacement is zero, so average velocity is zero.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Inertia myth",
        "hook": "Newton question students rush.",
        "question": "A moving object keeps moving at constant velocity when…",
        "choices": ["A) A force pushes it forever", "B) Net force is zero", "C) Gravity is removed"],
        "answer": "B",
        "reason": "First law: constant velocity when net force is zero.",
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
        "title": "Parallel resistors",
        "hook": "Harder circuit question.",
        "question": "Two 4 ohm resistors in parallel. Combined resistance is…",
        "choices": ["A) 8 ohm", "B) 2 ohm", "C) 4 ohm"],
        "answer": "B",
        "reason": "Equal parallels: R/2. So 4/2 = 2 ohm.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Power formula",
        "hook": "Which formula is correct?",
        "question": "Electrical power P equals…",
        "choices": ["A) V times I", "B) V divided by I", "C) V plus I"],
        "answer": "A",
        "reason": "Power P = VI. Also P = I²R and P = V²/R.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Acceleration",
        "hook": "Definition trap.",
        "question": "Acceleration is rate of change of…",
        "choices": ["A) Distance", "B) Velocity", "C) Mass"],
        "answer": "B",
        "reason": "Acceleration is rate of change of velocity.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Mirror image",
        "hook": "Optics quick check.",
        "question": "A plane mirror produces an image that is…",
        "choices": ["A) Real and inverted", "B) Virtual and upright", "C) Real and upright"],
        "answer": "B",
        "reason": "Plane mirror: virtual, upright, same size.",
        "visual": {"kind": "options"},
    },
    # ========== OPTIONS: chemistry ==========
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
        "title": "Neutralisation",
        "hook": "Acid plus base.",
        "question": "Acid + base mainly produces…",
        "choices": ["A) Salt and water", "B) Only gas", "C) Only acid"],
        "answer": "A",
        "reason": "Neutralisation: salt and water.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Atomic number",
        "hook": "Periodic table basics.",
        "question": "Atomic number equals number of…",
        "choices": ["A) Neutrons", "B) Protons", "C) Nuclei only"],
        "answer": "B",
        "reason": "Atomic number = protons (and electrons in a neutral atom).",
        "visual": {"kind": "options"},
    },
    # ========== OPTIONS: biology ==========
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
        "title": "Photosynthesis gas",
        "hook": "Do not confuse with respiration.",
        "question": "Gas released by green plants in light is mainly…",
        "choices": ["A) Carbon dioxide", "B) Oxygen", "C) Nitrogen"],
        "answer": "B",
        "reason": "Photosynthesis releases oxygen.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Blood pump",
        "hook": "Human biology.",
        "question": "Which organ pumps blood around the body?",
        "choices": ["A) Lungs", "B) Heart", "C) Liver"],
        "answer": "B",
        "reason": "The heart pumps blood. Lungs exchange gases.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Cell control",
        "hook": "Cell structure.",
        "question": "Which part controls the cell’s activities?",
        "choices": ["A) Cytoplasm", "B) Nucleus", "C) Cell wall"],
        "answer": "B",
        "reason": "Nucleus contains genetic material and controls the cell.",
        "visual": {"kind": "options"},
    },
    # ========== OPTIONS: maths ==========
    {
        "format": "options",
        "title": "Half of a third",
        "hook": "Quick maths. Most pick 2/3 by mistake.",
        "question": "What is one half of one third?",
        "choices": ["A) 2/3", "B) 1/6", "C) 1/5"],
        "answer": "B",
        "reason": "1/2 × 1/3 = 1/6.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Percentage trap",
        "hook": "WAEC-style number trap.",
        "question": "A shirt costs 800. Discount 25%. Sale price is…",
        "choices": ["A) 600", "B) 200", "C) 825"],
        "answer": "A",
        "reason": "25% of 800 is 200. Sale = 800 − 200 = 600.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Mean average",
        "hook": "Statistics basic.",
        "question": "Mean of 2, 4, 6, 8 is…",
        "choices": ["A) 4", "B) 5", "C) 6"],
        "answer": "B",
        "reason": "Sum 20, four numbers, mean = 5.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Angle in triangle",
        "hook": "Geometry trap.",
        "question": "Angles in a triangle add up to…",
        "choices": ["A) 90 degrees", "B) 180 degrees", "C) 360 degrees"],
        "answer": "B",
        "reason": "Interior angles of a triangle sum to 180 degrees.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Simple interest",
        "hook": "Commerce / maths.",
        "question": "Simple interest formula is…",
        "choices": ["A) PRT/100", "B) P+R+T", "C) PR times 100"],
        "answer": "A",
        "reason": "I = PRT/100.",
        "visual": {"kind": "options"},
    },
    # ========== TRUE / FALSE ==========
    {
        "format": "options",
        "title": "True or false speed",
        "hook": "True or false. Comment T or F.",
        "question": "Speed is a vector quantity.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Speed is scalar. Velocity is the vector.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "True or false mass",
        "hook": "True or false.",
        "question": "Mass of an object changes when it goes to the moon.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Mass stays the same. Weight changes with gravity.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "True or false boiling",
        "hook": "True or false chemistry.",
        "question": "Pure water boils at 100 degrees Celsius at standard pressure.",
        "choices": ["A) True", "B) False"],
        "answer": "A",
        "reason": "At 1 atm, pure water boils at 100°C.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "True or false plants",
        "hook": "True or false biology.",
        "question": "Plants only respire at night.",
        "choices": ["A) True", "B) False"],
        "answer": "B",
        "reason": "Plants respire day and night. Photosynthesis needs light.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "True or false zero",
        "hook": "True or false maths.",
        "question": "Any number multiplied by zero equals zero.",
        "choices": ["A) True", "B) False"],
        "answer": "A",
        "reason": "Product with zero is always zero.",
        "visual": {"kind": "options"},
    },
    # ========== WHAT HAPPENS NEXT ==========
    {
        "format": "options",
        "title": "Cold bottle",
        "hook": "What happens next? Everyday science.",
        "question": "You take a cold bottle from the fridge. Outside it goes wet. Why?",
        "choices": ["A) Water leaked out", "B) Air moisture condensed", "C) Plastic melted"],
        "answer": "B",
        "reason": "Warm moist air hits cold surface — water vapour condenses.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Ice in drink",
        "hook": "What happens next?",
        "question": "Ice melts in a drink. The drink level will…",
        "choices": ["A) Rise a lot from melting", "B) Stay about the same if ice was floating", "C) Always fall"],
        "answer": "B",
        "reason": "Floating ice already displaces its weight in water — level barely changes.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Metal in fire",
        "hook": "What happens next?",
        "question": "A metal rod is heated at one end. The other end becomes hot because of…",
        "choices": ["A) Conduction", "B) Photosynthesis", "C) Evaporation only"],
        "answer": "A",
        "reason": "Heat travels through the metal by conduction.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Balloon in sun",
        "hook": "What happens next?",
        "question": "A sealed balloon left in hot sun gets bigger mainly because…",
        "choices": ["A) Air particles move faster and push more", "B) Rubber grows new material", "C) Gravity increased"],
        "answer": "A",
        "reason": "Heating gas increases pressure / volume as particles move faster.",
        "visual": {"kind": "options"},
    },
    {
        "format": "options",
        "title": "Salt on ice",
        "hook": "What happens next?",
        "question": "Salt is spread on icy roads. Ice melts because salt…",
        "choices": ["A) Adds heat like fire", "B) Lowers the freezing point", "C) Makes ice heavier"],
        "answer": "B",
        "reason": "Salt lowers freezing point so ice can melt at colder temps.",
        "visual": {"kind": "options"},
    },
    # ========== PATTERN ==========
    {
        "format": "pattern",
        "title": "Missing number",
        "hook": "Not simple doubling. Look twice.",
        "question": "3, 6, 11, 18, question mark.",
        "choices": ["A) 27", "B) 25", "C) 30"],
        "answer": "A",
        "reason": "Add 3, 5, 7, 9… Next 18+9=27.",
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
    {
        "format": "pattern",
        "title": "Multiply chain",
        "hook": "Find the rule.",
        "question": "2, 4, 12, 48, question mark.",
        "choices": ["A) 96", "B) 240", "C) 144"],
        "answer": "B",
        "reason": "×2, ×3, ×4, ×5 → 48×5=240.",
        "visual": {"kind": "pattern", "seq": [2, 4, 12, 48, "?"]},
    },
    # ========== LIGHT VISUAL ==========
    {
        "format": "outline",
        "title": "Egg count",
        "hook": "Count carefully on a small screen.",
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
    {
        "format": "traffic",
        "title": "Which car reverses?",
        "hook": "Road logic. One number frees the jam.",
        "question": "Which numbered car in reverse clears the jam?",
        "choices": ["3", "5", "7"],
        "answer": "3",
        "reason": "Car 3 can reverse out and free the path.",
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
]


def pick() -> dict:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # rotate by day hash so consecutive days differ
    h = int(hashlib.md5(day.encode()).hexdigest(), 16)
    item = BANK[h % len(BANK)].copy()
    item["id"] = f"teaser-{day}-{item['format']}-{h % len(BANK)}"
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
    print("TEASER", item["format"], item["title"], "answer", item["answer"], "bank", len(BANK), file=sys.stderr)


if __name__ == "__main__":
    main()
