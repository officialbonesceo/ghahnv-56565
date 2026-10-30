#!/usr/bin/env python3
"""Daily language teaser: straight into questions, varied types, no long intro."""
from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKS_EACH = 20
NUM_QUESTIONS = 3
TOTAL_MARKS = MARKS_EACH * NUM_QUESTIONS

BANK = [
    {"type": "antonym", "question": "What is the opposite of expensive?", "choices": ["A) Cheap", "B) Heavy", "C) Soft"], "answer": "A", "reason": "Cheap is the opposite of expensive."},
    {"type": "antonym", "question": "The opposite of ancient is…", "choices": ["A) Old", "B) Modern", "C) Broken"], "answer": "B", "reason": "Modern means new or recent — opposite of ancient."},
    {"type": "antonym", "question": "What is the opposite of generous?", "choices": ["A) Kind", "B) Selfish", "C) Quiet"], "answer": "B", "reason": "Selfish is the opposite of generous."},
    {"type": "antonym", "question": "The opposite of permanent is…", "choices": ["A) Temporary", "B) Strong", "C) Useful"], "answer": "A", "reason": "Temporary means not lasting forever."},
    {"type": "antonym", "question": "What is the opposite of increase?", "choices": ["A) Grow", "B) Decrease", "C) Expand"], "answer": "B", "reason": "Decrease means to become smaller."},
    {"type": "synonym", "question": "Which word means almost the same as begin?", "choices": ["A) End", "B) Start", "C) Stop"], "answer": "B", "reason": "Start and begin are synonyms."},
    {"type": "synonym", "question": "A synonym of difficult is…", "choices": ["A) Easy", "B) Hard", "C) Soft"], "answer": "B", "reason": "Hard means almost the same as difficult."},
    {"type": "synonym", "question": "Which word is a synonym of assist?", "choices": ["A) Help", "B) Hurt", "C) Hide"], "answer": "A", "reason": "Assist means to help."},
    {"type": "synonym", "question": "Brave and courageous are…", "choices": ["A) Opposites", "B) Synonyms", "C) Numbers"], "answer": "B", "reason": "They mean nearly the same thing."},
    {"type": "synonym", "question": "Which word means almost the same as purchase?", "choices": ["A) Sell", "B) Buy", "C) Borrow"], "answer": "B", "reason": "Purchase means to buy."},
    {"type": "grammar", "question": "She ___ her homework every evening.", "choices": ["A) do", "B) does", "C) doing"], "answer": "B", "reason": "With she / he / it we use does."},
    {"type": "grammar", "question": "There ___ three books on the table.", "choices": ["A) is", "B) are", "C) was"], "answer": "B", "reason": "Books is plural → are."},
    {"type": "grammar", "question": "Neither of the boys ___ ready.", "choices": ["A) is", "B) are", "C) were"], "answer": "A", "reason": "Neither takes a singular verb: is."},
    {"type": "grammar", "question": "The news ___ surprising today.", "choices": ["A) are", "B) is", "C) were"], "answer": "B", "reason": "News is treated as singular."},
    {"type": "grammar", "question": "My brother and I ___ going to the market.", "choices": ["A) is", "B) am", "C) are"], "answer": "C", "reason": "Two people → are."},
    {"type": "article", "question": "She bought ___ umbrella yesterday.", "choices": ["A) a", "B) an", "C) the a"], "answer": "B", "reason": "Umbrella starts with a vowel sound → an."},
    {"type": "article", "question": "He is ___ honest man.", "choices": ["A) a", "B) an", "C) the"], "answer": "B", "reason": "Honest starts with a vowel sound → an."},
    {"type": "article", "question": "I saw ___ European tourist.", "choices": ["A) a", "B) an", "C) the an"], "answer": "A", "reason": "European starts with a /j/ consonant sound → a."},
    {"type": "tense", "question": "They ___ football when it started raining.", "choices": ["A) play", "B) were playing", "C) played"], "answer": "B", "reason": "Past continuous for an action in progress."},
    {"type": "tense", "question": "By next year she ___ her degree.", "choices": ["A) finishes", "B) will have finished", "C) finished"], "answer": "B", "reason": "Future perfect: will have finished."},
    {"type": "tense", "question": "I ___ this book three times already.", "choices": ["A) read", "B) have read", "C) am reading"], "answer": "B", "reason": "Present perfect for experience up to now."},
    {"type": "tense", "question": "While I was cooking, the phone ___.", "choices": ["A) rings", "B) rang", "C) is ringing"], "answer": "B", "reason": "Simple past interrupted the continuous action."},
    {"type": "pos", "question": "In 'She runs fast', the word fast is…", "choices": ["A) a noun", "B) an adverb", "C) a verb"], "answer": "B", "reason": "Fast describes how she runs — an adverb."},
    {"type": "pos", "question": "Which word is a preposition?", "choices": ["A) Quickly", "B) Under", "C) Beautiful"], "answer": "B", "reason": "Under shows position — a preposition."},
    {"type": "pos", "question": "In 'The red car stopped', red is…", "choices": ["A) a verb", "B) an adjective", "C) an adverb"], "answer": "B", "reason": "Red describes the car — an adjective."},
    {"type": "pos", "question": "Which word is a conjunction?", "choices": ["A) Because", "B) Quickly", "C) Table"], "answer": "A", "reason": "Because joins ideas — a conjunction."},
    {"type": "error", "question": "Which sentence is correct?", "choices": ["A) He don't know", "B) He doesn't know", "C) He no know"], "answer": "B", "reason": "He / she / it → doesn't."},
    {"type": "error", "question": "Choose the correct sentence.", "choices": ["A) She has went home", "B) She has gone home", "C) She have gone home"], "answer": "B", "reason": "Has + past participle: has gone."},
    {"type": "error", "question": "Which is correct?", "choices": ["A) Informations are useful", "B) Information is useful", "C) Information are useful"], "answer": "B", "reason": "Information is uncountable → is."},
    {"type": "error", "question": "Pick the correct one.", "choices": ["A) One of the boys are late", "B) One of the boys is late", "C) One of the boy is late"], "answer": "B", "reason": "One of + plural noun + singular verb."},
    {"type": "vocab", "question": "Someone who writes books is an…", "choices": ["A) Actor", "B) Author", "C) Artist"], "answer": "B", "reason": "An author writes books."},
    {"type": "vocab", "question": "A place where books are kept for reading is a…", "choices": ["A) Library", "B) Kitchen", "C) Stadium"], "answer": "A", "reason": "A library holds books for reading."},
    {"type": "vocab", "question": "If something is scarce, it is…", "choices": ["A) Plenty", "B) Rare", "C) Heavy"], "answer": "B", "reason": "Scarce means not enough / rare."},
    {"type": "vocab", "question": "To postpone means to…", "choices": ["A) Cancel forever", "B) Put off to later", "C) Finish early"], "answer": "B", "reason": "Postpone = delay to a later time."},
    {"type": "vocab", "question": "A person who treats sick people is a…", "choices": ["A) Teacher", "B) Doctor", "C) Farmer"], "answer": "B", "reason": "A doctor treats the sick."},
    {"type": "figure", "question": "He is as brave as a lion. This is a…", "choices": ["A) Metaphor", "B) Simile", "C) Hyperbole"], "answer": "B", "reason": "As…as comparison is a simile."},
    {"type": "figure", "question": "The classroom was a zoo. This is a…", "choices": ["A) Simile", "B) Metaphor", "C) Irony"], "answer": "B", "reason": "Direct comparison without like/as is a metaphor."},
    {"type": "figure", "question": "I've told you a million times! This is…", "choices": ["A) Irony", "B) Hyperbole", "C) Simile"], "answer": "B", "reason": "Obvious exaggeration is hyperbole."},
    {"type": "figure", "question": "The wind whispered through the trees. This is…", "choices": ["A) Personification", "B) Simile", "C) Pun"], "answer": "A", "reason": "Giving human action to wind is personification."},
    {"type": "form", "question": "The plural of crisis is…", "choices": ["A) Crisises", "B) Crises", "C) Crisis"], "answer": "B", "reason": "Crisis → crises."},
    {"type": "form", "question": "The past participle of write is…", "choices": ["A) Wrote", "B) Written", "C) Writing"], "answer": "B", "reason": "Write → wrote → written."},
    {"type": "form", "question": "Choose the correct comparative.", "choices": ["A) More better", "B) Better", "C) Bestest"], "answer": "B", "reason": "Good → better → best."},
    {"type": "form", "question": "The plural of tooth is…", "choices": ["A) Tooths", "B) Teeth", "C) Toothes"], "answer": "B", "reason": "Tooth → teeth."},
    {"type": "logic", "question": "If all roses are flowers and this is a rose, then it is…", "choices": ["A) A tree", "B) A flower", "C) An animal"], "answer": "B", "reason": "A rose is a flower by the given rule."},
    {"type": "logic", "question": "Which does not belong?", "choices": ["A) Apple", "B) Mango", "C) Chair"], "answer": "C", "reason": "Chair is not a fruit."},
    {"type": "logic", "question": "Book is to read as food is to…", "choices": ["A) Sleep", "B) Eat", "C) Walk"], "answer": "B", "reason": "You read a book; you eat food."},
]

THEMES = [
    ("English quiz", "language"),
    ("Grammar check", "grammar"),
    ("Vocab round", "vocab"),
    ("Quick English test", "language"),
    ("Exam English", "exam"),
    ("Word power", "vocab"),
]


def pick_pack(n: int = NUM_QUESTIONS):
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H")
    seed = int(hashlib.md5(f"teaser-v2-{day}-{hour}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    by_type = {}
    for q in BANK:
        by_type.setdefault(q["type"], []).append(q)
    types = list(by_type.keys())
    rng.shuffle(types)
    chosen = []
    for t in types:
        if len(chosen) >= n:
            break
        pool = by_type[t][:]
        rng.shuffle(pool)
        for q in pool:
            chosen.append(q)
            break
    if len(chosen) < n:
        rest = [q for q in BANK if q not in chosen]
        rng.shuffle(rest)
        for q in rest:
            if len(chosen) >= n:
                break
            chosen.append(q)
    out = []
    for i, q in enumerate(chosen[:n]):
        item = dict(q)
        item["index"] = i + 1
        item["marks"] = MARKS_EACH
        out.append(item)
    theme_title, theme_key = THEMES[seed % len(THEMES)]
    return out, theme_title, theme_key


def main() -> None:
    questions, theme_title, theme_key = pick_pack()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    segments = []
    for q in questions:
        choices = ". ".join(q["choices"])
        marks = q["marks"]
        segments.append({
            "phase": "ask",
            "q": q["index"],
            "text": f"Question {q['index']}. {marks} marks. {q['question']} {choices}. Comment now.",
        })
        segments.append({"phase": "countdown", "q": q["index"], "secs": 4})
        segments.append({
            "phase": "reveal",
            "q": q["index"],
            "text": f"Answer is {q['answer']}. {q['reason']} {marks} marks.",
        })
    segments.append({
        "phase": "outro",
        "text": f"Total {TOTAL_MARKS} marks. How many did you get? Comment your score. Follow for more.",
    })
    job = {
        "id": f"teaser-{theme_key}-{day}",
        "picked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "theme": theme_key,
        "title": theme_title,
        "short_title": theme_title,
        "questions": questions,
        "segments": segments,
        "marks_each": MARKS_EACH,
        "total_marks": TOTAL_MARKS,
        "countdown_seconds": 4,
        "cta": f"Comment your score out of {TOTAL_MARKS}. Follow for more.",
    }
    Path("teaser_job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    Path("script.txt").write_text(" ".join(s.get("text", "") for s in segments if s.get("text")) + "\n", encoding="utf-8")
    Path("title_short.txt").write_text(job["short_title"], encoding="utf-8")
    Path("cta.txt").write_text(job["cta"], encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        f"{theme_title} — 3 questions × {MARKS_EACH} = {TOTAL_MARKS}\n"
        "Comment A B or C before the timer!\n\n"
        f"{job['cta']}\n\n"
        "#english #learnenglish #quiz #fyp #studytok #grammar #vocabulary #examprep",
        encoding="utf-8",
    )
    answers = ", ".join(f"Q{q['index']}={q['answer']} ({q['marks']})" for q in questions)
    Path("tiktok_comment.txt").write_text(
        f"Answers: {answers}. Full marks = {TOTAL_MARKS}. What did you score?",
        encoding="utf-8",
    )
    print(json.dumps(job, indent=2))
    types_used = ", ".join(sorted({q.get("type", "?") for q in questions}))
    print("TEASER", theme_title, types_used, TOTAL_MARKS, "marks", file=sys.stderr)


if __name__ == "__main__":
    main()
