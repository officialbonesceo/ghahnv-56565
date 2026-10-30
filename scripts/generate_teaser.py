#!/usr/bin/env python3
"""Teaser v4: no intro, harder real-life + exam, multi-source questions, quiz image for FB/IG."""
from __future__ import annotations
import hashlib, json, os, random, re, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

MARKS_EACH, NUM_QUESTIONS = 20, 3
TOTAL_MARKS = MARKS_EACH * NUM_QUESTIONS

BANK = [
{"type":"real","question":"You transfer money and the network drops mid-send. Safest next step?","choices":["A) Send again immediately","B) Wait, then check transaction status","C) Restart phone and forget it"],"answer":"B","reason":"Wait and confirm status first — resending can double-charge."},
{"type":"real","question":"A message says you won millions — just pay a small processing fee. This is usually…","choices":["A) A bank promotion","B) A scam","C) A government grant"],"answer":"B","reason":"Legitimate prizes never ask you to pay a fee first."},
{"type":"real","question":"On a bus, a stranger asks you to hold their bag while they step down. You should…","choices":["A) Hold it to be polite","B) Politely refuse","C) Open it to check"],"answer":"B","reason":"Never hold a stranger's bag — it can hide illegal items."},
{"type":"real","question":"Your ATM card is swallowed. First correct action?","choices":["A) Walk away and return tomorrow","B) Call the bank hotline / block the card","C) Give your PIN to the security guard"],"answer":"B","reason":"Block the card immediately so nobody can use it."},
{"type":"real","question":"A 'free data' link asks for your network password. You should…","choices":["A) Enter the password quickly","B) Ignore and delete it","C) Share it with the class group"],"answer":"B","reason":"Phishing links steal accounts — never enter passwords from random links."},
{"type":"real","question":"An OTP arrives that you did not request. What should you do?","choices":["A) Share it with the caller who claims to be the bank","B) Ignore it and never share the code","C) Post it on your status for advice"],"answer":"B","reason":"OTPs are private — sharing them lets scammers empty accounts."},
{"type":"real","question":"A WhatsApp 'job offer' asks you to pay ₦15,000 for a form. Most likely…","choices":["A) Standard recruitment","B) A fraud","C) A bank requirement"],"answer":"B","reason":"Real employers do not charge applicants to apply."},
{"type":"real","question":"Someone offers you a 'loan' with no paperwork if you send your BVN and OTP first. This is…","choices":["A) A helpful fintech shortcut","B) Almost certainly a scam","C) Required by CBN for small loans"],"answer":"B","reason":"No legitimate lender needs your OTP; that hands them your account."},
{"type":"real","question":"You see a public Wi-Fi named 'Free Airport WiFi'. Best practice?","choices":["A) Connect and bank immediately","B) Avoid banking or login on public Wi-Fi","C) Share the password with strangers"],"answer":"B","reason":"Public networks can be spoofed; avoid sensitive logins on them."},
{"type":"real","question":"A rider delivers a package you did not order and asks you to pay 'customs' in cash. You should…","choices":["A) Pay to avoid trouble","B) Refuse and keep the door locked","C) Give them your card details"],"answer":"B","reason":"Unsolicited COD packages are a common delivery scam."},
{"type":"real","question":"Your friend sends a link saying 'I got hacked, click to help me recover'. Safest move?","choices":["A) Click and log in to help","B) Call or message them on another channel first","C) Forward the link to the class"],"answer":"B","reason":"Verify offline; the account may already be compromised."},
{"type":"real","question":"At an ATM, a stranger 'helps' you and stands very close while you type your PIN. You should…","choices":["A) Accept the help quickly","B) Cancel, cover the keypad, or leave","C) Tell them your PIN so they can finish"],"answer":"B","reason":"Shoulder-surfing and card skimming often start with 'helpful' strangers."},
{"type":"real","question":"You ordered food; the rider asks you to transfer to a personal account instead of the app. Best action?","choices":["A) Transfer to finish faster","B) Pay only through the official app method","C) Give cash plus extra for 'data'"],"answer":"B","reason":"Off-app transfers break protection and enable fraud."},
{"type":"real","question":"A site offers 'WAEC results early' for ₦2,000. This is…","choices":["A) Official WAEC service","B) Almost always a scam","C) Required for all candidates"],"answer":"B","reason":"Only the official portal releases results; paid early leaks are fraud."},
{"type":"real","question":"Someone DMs you a job that pays in crypto after you 'verify' by sending a small amount first. This is…","choices":["A) Normal crypto onboarding","B) An advance-fee scam","C) How all remote jobs start"],"answer":"B","reason":"Any job that requires you to send money first is a red flag."},
{"type":"logic","question":"All drivers need a licence. Chinedu is a driver. Therefore…","choices":["A) Chinedu may skip the licence","B) Chinedu needs a licence","C) Only older drivers need licences"],"answer":"B","reason":"If all drivers need a licence and he is a driver, he needs one."},
{"type":"logic","question":"A shop offers 20% off a ₦5,000 shirt. Sale price is…","choices":["A) ₦4,000","B) ₦1,000","C) ₦4,500"],"answer":"A","reason":"20% of 5000 is 1000; 5000 − 1000 = 4000."},
{"type":"logic","question":"A bus leaves at 7:40 and takes 1 hour 35 minutes. Arrival time is…","choices":["A) 8:75","B) 9:15","C) 9:05"],"answer":"B","reason":"7:40 + 1h = 8:40; +35 min = 9:15."},
{"type":"logic","question":"If 3 notebooks cost ₦1,200, how much do 5 cost at the same rate?","choices":["A) ₦1,800","B) ₦2,000","C) ₦2,400"],"answer":"B","reason":"One costs 400; five cost 2,000."},
{"type":"logic","question":"A tank is ¾ full. After using ⅓ of what is in it, how full is it?","choices":["A) ½","B) ¼","C) ⅓"],"answer":"A","reason":"¾ × ⅔ remaining = ½."},
{"type":"logic","question":"Two pipes fill a tank in 6 hours together. One alone takes 10 hours. The other alone takes…","choices":["A) 12 hours","B) 15 hours","C) 8 hours"],"answer":"B","reason":"1/6 − 1/10 = 1/15 → 15 hours."},
{"type":"grammar","question":"Neither the teacher nor the students ___ ready for the inspection.","choices":["A) was","B) were","C) is"],"answer":"B","reason":"With neither…nor, the verb agrees with the nearer subject: students → were."},
{"type":"grammar","question":"She is one of those writers who ___ every draft twice.","choices":["A) revises","B) revise","C) revising"],"answer":"B","reason":"Who refers to writers (plural) → revise."},
{"type":"grammar","question":"If he ___ harder last term, he would have passed Physics.","choices":["A) worked","B) had worked","C) works"],"answer":"B","reason":"Third conditional: If + past perfect → would have + past participle."},
{"type":"grammar","question":"Choose the correct sentence.","choices":["A) Each of the boys have a locker","B) Each of the boys has a locker","C) Each of the boy has a locker"],"answer":"B","reason":"Each takes a singular verb: has."},
{"type":"grammar","question":"The committee ___ decided to postpone the meeting.","choices":["A) have","B) has","C) are"],"answer":"B","reason":"Collective noun as a unit takes singular verb in formal English."},
{"type":"grammar","question":"I look forward to ___ from you soon.","choices":["A) hear","B) hearing","C) heard"],"answer":"B","reason":"Look forward to + gerund."},
{"type":"grammar","question":"Hardly had she finished the exam ___ the bell rang.","choices":["A) when","B) than","C) then"],"answer":"A","reason":"Hardly…when is the fixed inversion pattern."},
{"type":"grammar","question":"Which is correct?","choices":["A) Between you and I, the plan failed","B) Between you and me, the plan failed","C) Between you and myself, the plan failed"],"answer":"B","reason":"Object of preposition → me."},
{"type":"vocab","question":"In 'The rumour spread like wildfire', like wildfire means…","choices":["A) Slowly and carefully","B) Very quickly","C) Only at night"],"answer":"B","reason":"Like wildfire = extremely fast."},
{"type":"vocab","question":"To 'turn a blind eye' means to…","choices":["A) Watch carefully","B) Ignore something on purpose","C) Close a shop early"],"answer":"B","reason":"Turn a blind eye = deliberately ignore."},
{"type":"vocab","question":"If a deal is 'too good to be true', it is probably…","choices":["A) A safe investment","B) Suspicious or fake","C) Guaranteed by government"],"answer":"B","reason":"If it sounds unreal, treat it as a likely scam."},
{"type":"vocab","question":"'Bite the bullet' means to…","choices":["A) Eat quickly","B) Face a difficult situation bravely","C) Start a fight"],"answer":"B","reason":"Bite the bullet = endure something hard without complaint."},
{"type":"figure","question":"'The classroom was a market this morning.' This is a…","choices":["A) Simile","B) Metaphor","C) Irony"],"answer":"B","reason":"Direct comparison without like/as is a metaphor."},
{"type":"figure","question":"'I've told you a thousand times' is an example of…","choices":["A) Irony","B) Hyperbole","C) Pun"],"answer":"B","reason":"Deliberate exaggeration is hyperbole."},
{"type":"figure","question":"'As brave as a lion' is a…","choices":["A) Metaphor","B) Simile","C) Personification"],"answer":"B","reason":"Comparison using as/like is a simile."},
{"type":"error","question":"Which sentence is correct?","choices":["A) The informations were useful","B) The information was useful","C) The information were useful"],"answer":"B","reason":"Information is uncountable → was."},
{"type":"error","question":"Pick the correct option.","choices":["A) He suggested me to apply","B) He suggested that I apply","C) He suggested me applying"],"answer":"B","reason":"Suggest is not followed by object + to-infinitive in standard English."},
{"type":"error","question":"Correct form:","choices":["A) She is more taller than her sister","B) She is taller than her sister","C) She is most taller than her sister"],"answer":"B","reason":"Comparative already ends in -er; do not add more."},
{"type":"tense","question":"By the time we arrived, the lesson ___.","choices":["A) starts","B) had started","C) will start"],"answer":"B","reason":"Past perfect for an action completed before another past action."},
{"type":"tense","question":"She ___ in Lagos since 2019.","choices":["A) lives","B) has lived","C) lived"],"answer":"B","reason":"Since + starting point uses present perfect."},
{"type":"article","question":"He is ___ university student in Owerri.","choices":["A) a","B) an","C) the"],"answer":"A","reason":"University starts with a /j/ consonant sound → a."},
{"type":"article","question":"___ honest person will return the money.","choices":["A) A","B) An","C) The"],"answer":"B","reason":"Honest begins with a vowel sound → an."},
{"type":"science","question":"Why does a metal spoon feel colder than a wooden spoon at the same room temperature?","choices":["A) Metal is always colder","B) Metal conducts heat away from your hand faster","C) Wood produces heat"],"answer":"B","reason":"Metals are good conductors; they draw heat from skin quickly so they feel colder."},
{"type":"science","question":"You open a cold bottle of soft drink and it fizzes. The gas is mainly…","choices":["A) Oxygen released by pressure drop","B) Carbon dioxide coming out of solution","C) Nitrogen from the air"],"answer":"B","reason":"CO₂ is dissolved under pressure; opening reduces pressure so gas escapes."},
{"type":"science","question":"Why should you not put a sealed glass bottle of water in a freezer for a long time?","choices":["A) Water expands when it freezes and can crack the bottle","B) Glass becomes radioactive","C) The water will never freeze"],"answer":"A","reason":"Ice occupies more volume than liquid water; sealed bottles can burst."},
{"type":"science","question":"On a hot day a black car feels hotter than a white car. Main reason?","choices":["A) Black paint produces heat","B) Black surfaces absorb more radiation","C) White paint reflects only sound"],"answer":"B","reason":"Dark surfaces absorb more of the sun’s radiation; light surfaces reflect more."},
]

THEMES = [
    ("Real-life quiz", "reallife"),
    ("Street-smart check", "reallife"),
    ("Exam English", "exam"),
    ("Smart choices", "reallife"),
    ("Grammar check", "grammar"),
    ("Think fast", "mixed"),
    ("Money & safety", "reallife"),
    ("Logic sprint", "logic"),
]

def try_live_questions(n=3):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return []
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
    prompt = (
        "Create exactly 3 medium-to-hard multiple-choice questions for Nigerian secondary-school students (SS1–SS3).\n"
        "REQUIREMENTS:\n"
        "- At least 2 must be real-life scenarios (money, online safety, transport, shopping, exams, health, everyday decisions).\n"
        "- 1 can be harder grammar, vocab, logic, or applied science.\n"
        "- Questions must require thinking, not pure memorisation of a textbook definition.\n"
        "- Avoid baby-level questions.\n"
        "- Nigerian or universal everyday context is good.\n"
        "- Each question: 3 choices labelled A) B) C), one correct answer letter, short reason.\n"
        "Return ONLY a JSON list of objects with keys: type, question, choices (list of 3 strings), answer (A/B/C), reason.\n"
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/officialbonesceo/ghahnv-56565",
                "X-Title": "mike-teaser",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You output only valid JSON arrays. No markdown."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.85,
                "max_tokens": 1100,
            },
            timeout=50,
        )
        if r.status_code >= 400:
            print("live status", r.status_code, file=sys.stderr)
            return []
        content = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        m = re.search(r"\[[\s\S]*\]", content)
        if not m:
            return []
        data = json.loads(m.group(0))
        out = []
        for item in data:
            if not isinstance(item, dict):
                continue
            q = (item.get("question") or "").strip()
            choices = item.get("choices") or []
            ans = str(item.get("answer") or "").strip().upper()[:1]
            reason = (item.get("reason") or "").strip()
            if not q or len(choices) < 3 or ans not in "ABC" or len(reason) < 8:
                continue
            low = q.lower()
            if any(x in low for x in ("what is 2+", "what colour is", "how many days in a week")):
                continue
            norm = []
            for i, c in enumerate(choices[:3]):
                c = str(c).strip()
                letter = "ABC"[i]
                if not re.match(r"^[ABC]\)", c):
                    c = f"{letter}) {c}"
                norm.append(c)
            out.append({
                "type": str(item.get("type") or "live")[:20],
                "question": q[:200],
                "choices": norm,
                "answer": ans,
                "reason": reason[:180],
            })
        print("LIVE_QUESTIONS", len(out), file=sys.stderr)
        return out[:n]
    except Exception as e:
        print("live q fail", e, file=sys.stderr)
        return []


def try_secondary_source(n=2):
    out = []
    queries = [
        "everyday safety tips students",
        "common money scams Nigeria",
        "logical reasoning puzzle easy",
        "English grammar common mistakes SS",
        "physics in everyday life questions",
    ]
    random.shuffle(queries)
    for q in queries[:2]:
        try:
            r = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1},
                timeout=18,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            abstract = (data.get("AbstractText") or "").strip()
            if len(abstract) < 60:
                continue
            print("SECONDARY_SOURCE hit", q[:40], file=sys.stderr)
        except Exception as e:
            print("secondary fail", e, file=sys.stderr)
    return out


def pick_pack(n=NUM_QUESTIONS):
    now = datetime.now(timezone.utc)
    seed = int(hashlib.md5(f"teaser-v4-{now.strftime('%Y-%m-%d-%H')}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    live = try_live_questions(3)
    try_secondary_source(1)
    pool = BANK[:]
    rng.shuffle(pool)
    chosen = []
    used = set()
    for q in live:
        k = re.sub(r"[^a-z0-9]+", "", q["question"].lower())
        if k in used:
            continue
        chosen.append(q)
        used.add(k)
        if len(chosen) >= n:
            break
    by = {}
    for q in pool:
        by.setdefault(q["type"], []).append(q)
    preferred = [t for t in ("real", "science", "logic", "grammar", "vocab", "error", "tense", "figure", "article") if t in by]
    ordered = preferred + [t for t in by if t not in preferred]
    for t in ordered:
        if len(chosen) >= n:
            break
        for q in by[t]:
            k = re.sub(r"[^a-z0-9]+", "", q["question"].lower())
            if k in used:
                continue
            chosen.append(q)
            used.add(k)
            break
    while len(chosen) < n and pool:
        q = pool.pop()
        k = re.sub(r"[^a-z0-9]+", "", q["question"].lower())
        if k in used:
            continue
        chosen.append(q)
        used.add(k)
    out = []
    for i, q in enumerate(chosen[:n]):
        item = dict(q)
        item["index"] = i + 1
        item["marks"] = MARKS_EACH
        out.append(item)
    theme_title, theme_key = THEMES[seed % len(THEMES)]
    if any(q.get("type") in ("real", "live", "science") for q in out):
        theme_title, theme_key = rng.choice([
            ("Real-life quiz", "reallife"),
            ("Street-smart check", "reallife"),
            ("Smart choices", "reallife"),
            ("Money & safety", "reallife"),
        ])
    return out, theme_title, theme_key


def make_quiz_image(job):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print("PIL", e, file=sys.stderr)
        return None
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), (18, 26, 42))
    d = ImageDraw.Draw(img)
    try:
        title_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        q_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        c_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:
        title_f = q_f = c_f = small = ImageFont.load_default()
    d.rectangle([0, 0, W, 100], fill=(255, 210, 40))
    title = (job.get("short_title") or "Quiz")[:40]
    bb = d.textbbox((0, 0), title, font=title_f)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), title, font=title_f, fill=(18, 18, 24))
    qs = job.get("questions") or []
    q1 = qs[0] if qs else None
    y = 140
    if q1:
        d.text((48, y), f"Q{q1.get('index', 1)} · {q1.get('marks', 20)} marks", font=small, fill=(255, 210, 40))
        y += 50
        words = (q1.get("question") or "").split()
        line = ""
        lines = []
        for w in words:
            test = (line + " " + w).strip()
            if d.textbbox((0, 0), test, font=q_f)[2] > W - 96:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        for line in lines[:5]:
            d.text((48, y), line, font=q_f, fill=(255, 255, 255))
            y += 48
        y += 24
        for ch in (q1.get("choices") or [])[:3]:
            d.rounded_rectangle([48, y, W - 48, y + 72], 16, fill=(32, 48, 85), outline=(70, 90, 130), width=2)
            d.text((72, y + 18), ch[:70], font=c_f, fill=(255, 255, 255))
            y += 88
    d.text((48, H - 120), "Comment A, B or C · Answer in the caption", font=small, fill=(150, 165, 195))
    d.text((48, H - 70), "Mike · Daily quiz", font=small, fill=(180, 200, 255))
    root = Path(__file__).resolve().parents[1]
    for name in ("body_point.png", "body_question.png", "body.png"):
        mp = root / "assets" / "mezi" / name
        if mp.exists():
            try:
                mike = Image.open(mp).convert("RGBA")
                mw = 380
                mh = int(mw * mike.height / max(1, mike.width))
                mike = mike.resize((mw, mh), Image.Resampling.LANCZOS)
                img.paste(mike, (-10, H - mh - 20), mike)
            except Exception:
                pass
            break
    img.save("quiz_card.jpg", quality=92)
    img.save("post_card.jpg", quality=92)
    print("QUIZ_CARD quiz_card.jpg", file=sys.stderr)
    return Path("quiz_card.jpg")


def main():
    questions, theme_title, theme_key = pick_pack()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    segments = []
    for q in questions:
        choices = ". ".join(q["choices"])
        segments.append({
            "phase": "ask",
            "q": q["index"],
            "text": f"Question {q['index']}. {q['marks']} marks. {q['question']} {choices}. Comment now.",
        })
        segments.append({"phase": "countdown", "q": q["index"], "secs": 4})
        segments.append({
            "phase": "reveal",
            "q": q["index"],
            "text": f"Answer is {q['answer']}. {q['reason']} {q['marks']} marks.",
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
    Path("script.txt").write_text(
        " ".join(s.get("text", "") for s in segments if s.get("text")) + "\n", encoding="utf-8"
    )
    Path("title_short.txt").write_text(job["short_title"], encoding="utf-8")
    Path("cta.txt").write_text(job["cta"], encoding="utf-8")
    answers = ", ".join(f"Q{q['index']}={q['answer']}" for q in questions)
    reasons = " | ".join(f"Q{q['index']}: {q['reason']}" for q in questions)
    q_block = "\n".join(
        f"Q{q['index']}. {q['question']}\n" + " · ".join(q["choices"]) for q in questions
    )
    Path("tiktok_caption.txt").write_text(
        f"{theme_title} — 3 questions × {MARKS_EACH} = {TOTAL_MARKS}\n\n"
        f"{q_block}\n\n"
        f"Comment A B or C before the timer!\n"
        f"{job['cta']}\n\n"
        f"#quiz #fyp #learnenglish #studytok #examprep #reallife #students #moneysafety",
        encoding="utf-8",
    )
    Path("tiktok_comment.txt").write_text(
        f"Answers: {answers}. {reasons} Full marks = {TOTAL_MARKS}. What did you score?",
        encoding="utf-8",
    )
    Path("image_caption.txt").write_text(
        f"{theme_title}\n\n"
        f"{q_block}\n\n"
        f"Drop A, B or C in the comments before you scroll.\n\n"
        f"———\n"
        f"Answers (after you try):\n{answers}\n"
        f"{reasons}\n\n"
        f"{job['cta']}\n\n"
        f"#quiz #education #students #examprep #learnenglish #reallife #moneysafety",
        encoding="utf-8",
    )
    make_quiz_image(job)
    print(json.dumps(job, indent=2))
    print(
        "TEASER",
        theme_title,
        ",".join(sorted({q.get("type", "?") for q in questions})),
        TOTAL_MARKS,
        "marks",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
