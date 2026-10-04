#!/usr/bin/env python3
"""Daily language teaser: 3–4 easy questions. Answers NEVER in the ask audio."""
from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Easy language / English class — clear words, no hard physics/math
BANK = [
    {
        "question": "What is the opposite of hot?",
        "choices": ["A) Warm", "B) Cold", "C) Soft"],
        "answer": "B",
        "reason": "Cold is the opposite of hot.",
    },
    {
        "question": "Which word means a place where you learn?",
        "choices": ["A) Market", "B) School", "C) River"],
        "answer": "B",
        "reason": "School is where we learn.",
    },
    {
        "question": "Choose the correct plural of child.",
        "choices": ["A) Childs", "B) Children", "C) Childes"],
        "answer": "B",
        "reason": "The plural of child is children.",
    },
    {
        "question": "She ___ to school every day.",
        "choices": ["A) go", "B) goes", "C) going"],
        "answer": "B",
        "reason": "With she, we use goes.",
    },
    {
        "question": "What is a synonym of happy?",
        "choices": ["A) Sad", "B) Glad", "C) Angry"],
        "answer": "B",
        "reason": "Glad means almost the same as happy.",
    },
    {
        "question": "Which word is a noun?",
        "choices": ["A) Run", "B) Quickly", "C) Book"],
        "answer": "C",
        "reason": "Book is a thing — a noun.",
    },
    {
        "question": "I have ___ apple.",
        "choices": ["A) a", "B) an", "C) the two"],
        "answer": "B",
        "reason": "An comes before a vowel sound: an apple.",
    },
    {
        "question": "The past tense of eat is…",
        "choices": ["A) Eated", "B) Ate", "C) Eating"],
        "answer": "B",
        "reason": "Eat → ate → eaten.",
    },
    {
        "question": "Which is a question word?",
        "choices": ["A) Because", "B) Where", "C) And"],
        "answer": "B",
        "reason": "Where asks about place.",
    },
    {
        "question": "Big and large are…",
        "choices": ["A) Opposites", "B) Synonyms", "C) Numbers"],
        "answer": "B",
        "reason": "They mean almost the same — synonyms.",
    },
    {
        "question": "Which sentence is correct?",
        "choices": ["A) He don't know", "B) He doesn't know", "C) He no know"],
        "answer": "B",
        "reason": "He / she / it → doesn't.",
    },
    {
        "question": "A person who teaches is a…",
        "choices": ["A) Teacher", "B) Farmer", "C) Driver"],
        "answer": "A",
        "reason": "A teacher teaches.",
    },
    {
        "question": "Which word starts with a vowel sound?",
        "choices": ["A) Ball", "B) Umbrella", "C) Cat"],
        "answer": "B",
        "reason": "Umbrella starts with a vowel sound.",
    },
    {
        "question": "The opposite of full is…",
        "choices": ["A) Empty", "B) Tall", "C) Loud"],
        "answer": "A",
        "reason": "Empty is the opposite of full.",
    },
    {
        "question": "We ___ football yesterday.",
        "choices": ["A) play", "B) played", "C) playing"],
        "answer": "B",
        "reason": "Yesterday needs past tense: played.",
    },
    {
        "question": "Which is an adjective?",
        "choices": ["A) Beautiful", "B) Run", "C) Quickly"],
        "answer": "A",
        "reason": "Beautiful describes a noun.",
    },
    {
        "question": "Hello is used to…",
        "choices": ["A) Say goodbye", "B) Greet someone", "C) Count numbers"],
        "answer": "B",
        "reason": "Hello is a greeting.",
    },
    {
        "question": "One book, two…",
        "choices": ["A) Book", "B) Books", "C) Bookes"],
        "answer": "B",
        "reason": "Add s for most plurals: books.",
    },
    {
        "question": "Which word means very big?",
        "choices": ["A) Tiny", "B) Huge", "C) Slow"],
        "answer": "B",
        "reason": "Huge means very big.",
    },
    {
        "question": "She is ___ honest girl.",
        "choices": ["A) a", "B) an", "C) the a"],
        "answer": "B",
        "reason": "Honest starts with a vowel sound → an.",
    },
    {
        "question": "The present continuous of write is…",
        "choices": ["A) Writed", "B) Writing", "C) Wrote"],
        "answer": "B",
        "reason": "Write → writing (drop e, add ing).",
    },
    {
        "question": "Which is a pronoun?",
        "choices": ["A) Table", "B) They", "C) Jump"],
        "answer": "B",
        "reason": "They stands in for people — a pronoun.",
    },
    {
        "question": "Good morning is said…",
        "choices": ["A) At night", "B) In the morning", "C) Only in class"],
        "answer": "B",
        "reason": "We say good morning in the morning.",
    },
    {
        "question": "The opposite of start is…",
        "choices": ["A) Begin", "B) Stop", "C) Open"],
        "answer": "B",
        "reason": "Stop is the opposite of start.",
    },
]


def pick_pack(n: int = 4) -> list[dict]:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = int(hashlib.md5(f"teaser-lang-{day}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    pool = BANK[:]
    rng.shuffle(pool)
    n = max(3, min(4, n, len(pool)))
    out = []
    for i, q in enumerate(pool[:n]):
        item = q.copy()
        item["index"] = i + 1
        out.append(item)
    return out


def main() -> None:
    questions = pick_pack(4)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Segments: ask (no answer) → countdown → reveal (answer only here)
    segments: list[dict] = []
    segments.append(
        {
            "phase": "intro",
            "text": "Language quiz time. Easy questions. Comment A, B, or C before time is up.",
        }
    )
    for q in questions:
        choices = ". ".join(q["choices"])
        segments.append(
            {
                "phase": "ask",
                "q": q["index"],
                "text": (
                    f"Question {q['index']}. {q['question']} "
                    f"{choices}. "
                    f"Comment your answer now. You have five seconds."
                ),
            }
        )
        segments.append({"phase": "countdown", "q": q["index"], "secs": 5})
        segments.append(
            {
                "phase": "reveal",
                "q": q["index"],
                "text": (
                    f"The answer is {q['answer']}. {q['reason']}"
                ),
            }
        )
    segments.append(
        {
            "phase": "outro",
            "text": "How many did you get right? Comment your score. Follow for more.",
        }
    )

    # Full scripts for debugging — ask-only must not contain answers
    ask_only = " ".join(
        s["text"] for s in segments if s["phase"] in ("intro", "ask", "outro")
    )
    for letter in ("A", "B", "C"):
        # soft check: answer letter alone may appear in choices text; block reason spoilers
        pass
    for q in questions:
        if q["reason"].lower() in ask_only.lower():
            print("WARN reason leaked into ask", file=sys.stderr)

    job = {
        "id": f"teaser-lang-{day}",
        "picked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "theme": "language",
        "title": "Easy English quiz",
        "short_title": "Easy English quiz",
        "questions": questions,
        "segments": segments,
        "countdown_seconds": 5,
        "cta": "Comment your score. Follow for more.",
    }

    Path("teaser_job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    # Placeholder script.txt for older steps; real audio built segment-wise
    Path("script.txt").write_text(
        " ".join(s.get("text", "") for s in segments if s.get("text")) + "\n",
        encoding="utf-8",
    )
    Path("title_short.txt").write_text(job["short_title"], encoding="utf-8")
    Path("cta.txt").write_text(job["cta"], encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        "Easy English quiz — comment A B or C before the timer ends!\n\n"
        f"{job['cta']}\n\n"
        "#english #learnenglish #quiz #fyp #studytok #vocabulary #grammar",
        encoding="utf-8",
    )
    answers = ", ".join(f"Q{q['index']}={q['answer']}" for q in questions)
    Path("tiktok_comment.txt").write_text(
        f"Answers: {answers}. How many did you get?",
        encoding="utf-8",
    )
    print(json.dumps(job, indent=2))
    print("TEASER language pack", len(questions), "questions", file=sys.stderr)


if __name__ == "__main__":
    main()
