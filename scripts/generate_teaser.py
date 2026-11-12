#!/usr/bin/env python3
"""Teaser v6: full text on screen, longer spoken Q, dedupe recent questions."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ALWAYS_TAGS = [
    "#fyp",
    "#shorts",
    "#viral",
    "#quiz",
    "#mike",
    "#mikethetutor",
    "#learnontiktok",
    "#education",
]

SEEN_PATH = Path("data/teaser_seen.json")
SEEN_MAX = 40

EMERGENCY_POOL = [
    {
        "title": "OTP you didn't request",
        "type": "real",
        "question": "An OTP code arrives on your phone but you did not request any transaction. What is the safest thing to do?",
        "choices": [
            "A) Share the code with the caller who says they are from your bank",
            "B) Ignore the code and never share it with anyone",
            "C) Post the code on your status so friends can advise you",
        ],
        "answer": "B",
        "reason": "OTPs open your account. Banks never ask you to read an OTP to a caller.",
        "spoken_intro": "Quick safety check. An OTP just arrived and you did not request anything. What should you do with that code?",
        "spoken_reveal": "The answer is B. Ignore it and never share it. Anyone with your OTP can empty the account.",
        "topic_hashtags": ["#safety", "#scamalert", "#otp"],
        "youtube_description": "OTP you didn't request — what do you do?",
        "tiktok_caption": "OTP just landed. A, B or C?",
        "instagram_caption": "OTP you didn't request. Safest move?",
        "facebook_caption": "OTP scam check — pick A, B or C.",
    },
    {
        "title": "Public Wi-Fi banking",
        "type": "real",
        "question": "You are on free public Wi-Fi at a bus park. You need to check your bank balance. What should you do?",
        "choices": [
            "A) Open your banking app on the free Wi-Fi immediately",
            "B) Use mobile data or wait until you are on a trusted network",
            "C) Share the Wi-Fi password in the class group first",
        ],
        "answer": "B",
        "reason": "Public Wi-Fi can be faked. Sensitive logins should use mobile data or a trusted network.",
        "spoken_intro": "You are at a bus park on free Wi-Fi and you need your bank balance. What is the smart move?",
        "spoken_reveal": "Answer B. Use your own mobile data or wait. Public Wi-Fi is risky for banking.",
        "topic_hashtags": ["#cybersecurity", "#wifi", "#banking"],
        "youtube_description": "Public Wi-Fi and banking — safe or not?",
        "tiktok_caption": "Free Wi-Fi at the park. Do you bank on it?",
        "instagram_caption": "Public Wi-Fi banking check.",
        "facebook_caption": "Would you check your bank on free Wi-Fi?",
    },
]


def gemini_key() -> str:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_AI_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
    ):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


def fingerprint(question: str) -> str:
    q = re.sub(r"[^a-z0-9]+", "", (question or "").lower())
    return hashlib.sha1(q.encode()).hexdigest()[:16]


def load_seen() -> list[dict]:
    if not SEEN_PATH.exists():
        return []
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_seen(entries: list[dict]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(entries[-SEEN_MAX:], indent=2), encoding="utf-8")


def _call_gemini(key: str, model: str, system: str, user: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.95,
            "maxOutputTokens": 1200,
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(url, json=body, timeout=90)
    if r.status_code >= 400:
        body["generationConfig"].pop("responseMimeType", None)
        r = requests.post(url, json=body, timeout=90)
        if r.status_code >= 400:
            print("gemini HTTP", model, r.status_code, r.text[:300], file=sys.stderr)
            return ""
    data = r.json()
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    content = "".join((p.get("text") or "") for p in parts).strip()
    if not content:
        fr = ((data.get("candidates") or [{}])[0].get("finishReason") or "")
        print("gemini empty", model, "finish", fr, file=sys.stderr)
    return content


def _call_openrouter(key: str, model: str, system: str, user: str) -> str:
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
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.95,
            "max_tokens": 1200,
        },
        timeout=90,
    )
    if r.status_code >= 400:
        print("openrouter HTTP", model, r.status_code, r.text[:280], file=sys.stderr)
        return ""
    return (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def parse_json_obj(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except Exception as e:
        print("json parse fail", e, file=sys.stderr)
        return None


def normalize_payload(data: dict) -> dict | None:
    q = (data.get("question") or "").strip()
    choices = data.get("choices") or []
    ans = str(data.get("answer") or "").strip().upper()[:1]
    reason = (data.get("reason") or "").strip()
    if not q or len(choices) < 3 or ans not in "ABC" or len(reason) < 12:
        print(
            "normalize fail",
            "q_len", len(q),
            "ch", len(choices),
            "ans", ans,
            "reason_len", len(reason),
            file=sys.stderr,
        )
        return None
    if len(q) < 40:
        print("normalize fail question too short", file=sys.stderr)
        return None
    low = q.lower()
    if any(x in low for x in ("what is 2+", "what colour is", "how many days in a week")):
        return None

    norm = []
    for i, c in enumerate(choices[:3]):
        c = str(c).strip()
        letter = "ABC"[i]
        if not re.match(r"^[ABC]\)", c):
            c = f"{letter}) {c}"
        # keep full option text (cap only extreme length)
        if len(c) > 160:
            c = c[:157] + "..."
        if len(c) < 8:
            print("normalize fail choice short", c, file=sys.stderr)
            return None
        norm.append(c)

    topic_tags = data.get("topic_hashtags") or data.get("hashtags") or []
    if isinstance(topic_tags, str):
        topic_tags = [t.strip() for t in topic_tags.replace(",", " ").split() if t.strip()]
    clean_tags = []
    for t in topic_tags:
        t = str(t).strip()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        t = re.sub(r"[^#A-Za-z0-9_]", "", t)[:32]
        if len(t) > 2:
            clean_tags.append(t)
    hashtags = []
    for t in ALWAYS_TAGS + clean_tags:
        if t.lower() not in {h.lower() for h in hashtags}:
            hashtags.append(t)
    if not any("mike" in h.lower() for h in hashtags):
        hashtags.extend(["#mike", "#mikethetutor"])

    def cap(key_a: str, key_b: str, default: str) -> str:
        return (data.get(key_a) or data.get(key_b) or default).strip()[:500]

    title = (data.get("title") or data.get("short_title") or "Quick quiz").strip()[:70]
    # Spoken intro must include the actual question so audio is complete
    spoken_intro = (data.get("spoken_intro") or "").strip()
    if len(spoken_intro) < 30 or q.lower()[:20] not in spoken_intro.lower():
        spoken_intro = f"Listen carefully. {q} Choose A, B, or C."
    spoken_intro = spoken_intro[:320]
    spoken_reveal = (data.get("spoken_reveal") or "").strip()
    if len(spoken_reveal) < 25:
        spoken_reveal = f"The correct answer is {ans}. {reason}"
    spoken_reveal = spoken_reveal[:360]

    return {
        "title": title,
        "question": q[:280],
        "choices": norm,
        "answer": ans,
        "reason": reason[:280],
        "type": str(data.get("type") or "real")[:20],
        "spoken_intro": spoken_intro,
        "spoken_reveal": spoken_reveal,
        "hashtags": hashtags[:18],
        "captions": {
            "youtube": cap("youtube_description", "caption_youtube", f"{title}\n\nComment A, B or C before the timer ends."),
            "tiktok": cap("tiktok_caption", "caption_tiktok", f"{title} Comment A B or C"),
            "instagram": cap("instagram_caption", "caption_instagram", f"{title}\nAnswer in the comments"),
            "facebook": cap("facebook_caption", "caption_facebook", f"{title}\nWhat would you pick?"),
        },
    }


def fetch_ai_question(avoid: list[str]) -> dict | None:
    avoid_block = ""
    if avoid:
        lines = "\n".join(f"- {a}" for a in avoid[:15])
        avoid_block = f"\n\nDo NOT repeat or closely paraphrase any of these recent questions:\n{lines}\n"

    system = (
        "You create ONE hard real-life or exam multiple-choice question for Nigerian secondary students. "
        "Return ONLY a JSON object. No markdown. "
        "Every choice must be a complete sentence or full phrase — never cut off mid-word."
    )
    user = (
        "Create exactly ONE medium-to-hard multiple-choice question.\n"
        "Prefer real-life (money, online safety, transport, shopping, health, exams, everyday decisions) "
        "or applied school reasoning (logic, grammar, science in daily life).\n"
        "Not baby-level. Requires thinking.\n"
        "Question: 1-3 full sentences, clear scenario, 60-180 characters ideal.\n"
        "Each choice: complete text starting with A) B) C) — full option, not truncated.\n"
        "Reason: complete explanation, 1-2 sentences.\n"
        "spoken_intro: Mike reads the FULL question out loud in natural speech (include the question text).\n"
        "spoken_reveal: Mike says the letter, the correct option idea, and why — complete sentences.\n"
        f"{avoid_block}\n"
        "JSON keys required:\n"
        "title, type, question, choices (exactly 3 full strings), answer (A|B|C), reason,\n"
        "spoken_intro, spoken_reveal, topic_hashtags (array),\n"
        "youtube_description, tiktok_caption, instagram_caption, facebook_caption\n"
    )
    key = gemini_key()
    preferred = os.environ.get("GEMINI_MODEL", "").strip()
    models = []
    if preferred:
        models.append(preferred)
    for m in (
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ):
        if m not in models:
            models.append(m)

    for model in models:
        if not key:
            break
        for attempt in range(3):
            print("TEASER_GEMINI", model, "attempt", attempt + 1, file=sys.stderr)
            try:
                content = _call_gemini(key, model, system, user)
                data = parse_json_obj(content)
                if data:
                    packed = normalize_payload(data)
                    if packed:
                        fp = fingerprint(packed["question"])
                        if any(fp == fingerprint(a) for a in avoid):
                            print("TEASER_DUP skip", packed["title"], file=sys.stderr)
                            continue
                        packed["engine"] = f"gemini:{model}"
                        print("TEASER_GEMINI_OK", model, file=sys.stderr)
                        return packed
                    print("TEASER_NORM_FAIL", model, file=sys.stderr)
                else:
                    print("TEASER_PARSE_FAIL", model, "head", (content or "")[:120], file=sys.stderr)
            except Exception as e:
                print("TEASER_GEMINI_EXC", model, e, file=sys.stderr)
            time.sleep(0.7 * (attempt + 1))

    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if or_key:
        model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
        for attempt in range(3):
            print("TEASER_OR", model, "attempt", attempt + 1, file=sys.stderr)
            try:
                content = _call_openrouter(or_key, model, system, user)
                data = parse_json_obj(content)
                if data:
                    packed = normalize_payload(data)
                    if packed:
                        packed["engine"] = f"openrouter:{model}"
                        print("TEASER_OR_OK", model, file=sys.stderr)
                        return packed
            except Exception as e:
                print("TEASER_OR_EXC", e, file=sys.stderr)
            time.sleep(1.0)

    print("TEASER_EMERGENCY fallback", file=sys.stderr)
    seen_fps = {fingerprint(a) for a in avoid}
    for item in EMERGENCY_POOL:
        if fingerprint(item["question"]) not in seen_fps:
            packed = normalize_payload(item)
            if packed:
                packed["engine"] = "emergency"
                return packed
    packed = normalize_payload(EMERGENCY_POOL[0])
    if packed:
        packed["engine"] = "emergency"
    return packed


def write_side_files(job: dict) -> None:
    tags = " ".join(job.get("hashtags") or ALWAYS_TAGS)
    caps = job.get("captions") or {}
    Path("title_short.txt").write_text(job.get("title") or "Quiz", encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        f"{(caps.get('tiktok') or job.get('title') or 'Quiz').strip()}\n\n{tags}\n", encoding="utf-8"
    )
    Path("tiktok_comment.txt").write_text(
        f"Watch the reveal for the answer. Follow Mike · {tags}\n", encoding="utf-8"
    )
    Path("image_caption.txt").write_text(
        f"{(caps.get('instagram') or '').strip()}\n\n{tags}\n", encoding="utf-8"
    )
    Path("youtube_description.txt").write_text(
        f"{(caps.get('youtube') or '').strip()}\n\n{tags}\n", encoding="utf-8"
    )
    Path("facebook_caption.txt").write_text(
        f"{(caps.get('facebook') or '').strip()}\n\n{tags}\n", encoding="utf-8"
    )
    Path("script.txt").write_text(
        f"{job.get('spoken_intro','')}\n{job.get('spoken_reveal','')}\n", encoding="utf-8"
    )


def main() -> None:
    seen = load_seen()
    avoid = [e.get("question", "") for e in seen if e.get("question")]
    packed = fetch_ai_question(avoid)
    if not packed:
        print("TEASER_FAIL: no question", file=sys.stderr)
        sys.exit(1)

    q = {
        "index": 1,
        "marks": 20,
        "type": packed["type"],
        "question": packed["question"],
        "choices": packed["choices"],
        "answer": packed["answer"],
        "reason": packed["reason"],
    }

    # Longer timer so viewers can read full on-screen text
    segments = [
        {"phase": "intro", "q": 1, "text": packed["spoken_intro"]},
        {"phase": "countdown", "q": 1, "secs": 12},
        {"phase": "reveal", "q": 1, "text": packed["spoken_reveal"]},
    ]

    job = {
        "version": 6,
        "engine": packed.get("engine"),
        "title": packed["title"],
        "short_title": packed["title"],
        "total_marks": 20,
        "marks_each": 20,
        "questions": [q],
        "segments": segments,
        "hashtags": packed["hashtags"],
        "captions": packed["captions"],
        "spoken_intro": packed["spoken_intro"],
        "spoken_reveal": packed["spoken_reveal"],
    }
    Path("teaser_job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    write_side_files(job)

    seen.append(
        {
            "fp": fingerprint(packed["question"]),
            "question": packed["question"][:180],
            "title": packed["title"],
            "answer": packed["answer"],
        }
    )
    save_seen(seen)

    print("TEASER_OK", job["engine"], job["title"], "answer", q["answer"], file=sys.stderr)
    print(
        json.dumps(
            {
                "title": job["title"],
                "answer": q["answer"],
                "engine": job["engine"],
                "q_len": len(q["question"]),
                "choice_lens": [len(c) for c in q["choices"]],
                "tags": job["hashtags"][:8],
            }
        )
    )


if __name__ == "__main__":
    main()
