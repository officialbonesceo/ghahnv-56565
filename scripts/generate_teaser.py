#!/usr/bin/env python3
"""Teaser v5: AI-only single question + platform captions/hashtags. No seed bank."""
from __future__ import annotations

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


def gemini_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


def _call_gemini(key: str, model: str, system: str, user: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 900},
    }
    r = requests.post(url, json=body, timeout=90)
    if r.status_code >= 400:
        print("gemini HTTP", model, r.status_code, r.text[:280], file=sys.stderr)
        return ""
    data = r.json()
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    return "".join((p.get("text") or "") for p in parts).strip()


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
            "temperature": 0.85,
            "max_tokens": 900,
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
        print("normalize fail fields", file=sys.stderr)
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
        norm.append(c[:90])
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
    # Always tags first, then topic, always include mike variants
    hashtags = []
    for t in ALWAYS_TAGS + clean_tags:
        if t.lower() not in {h.lower() for h in hashtags}:
            hashtags.append(t)
    if not any("mike" in h.lower() for h in hashtags):
        hashtags.extend(["#mike", "#mikethetutor"])

    def cap(key_a: str, key_b: str, default: str) -> str:
        return (data.get(key_a) or data.get(key_b) or default).strip()[:420]

    title = (data.get("title") or data.get("short_title") or "Quick quiz").strip()[:70]
    spoken_intro = (data.get("spoken_intro") or f"Quick one. {q}").strip()[:220]
    spoken_reveal = (data.get("spoken_reveal") or f"The answer is {ans}. {reason}").strip()[:280]

    return {
        "title": title,
        "question": q[:200],
        "choices": norm,
        "answer": ans,
        "reason": reason[:200],
        "type": str(data.get("type") or "real")[:20],
        "spoken_intro": spoken_intro,
        "spoken_reveal": spoken_reveal,
        "hashtags": hashtags[:18],
        "captions": {
            "youtube": cap("youtube_description", "caption_youtube", f"{title}\n\nComment your answer before the timer ends."),
            "tiktok": cap("tiktok_caption", "caption_tiktok", f"{title} Comment A B or C"),
            "instagram": cap("instagram_caption", "caption_instagram", f"{title}\nAnswer in the comments"),
            "facebook": cap("facebook_caption", "caption_facebook", f"{title}\nWhat would you pick?"),
        },
    }


def fetch_ai_question() -> dict | None:
    system = (
        "You create ONE hard real-life or exam multiple-choice question for Nigerian secondary students. "
        "Output ONLY valid JSON. No markdown."
    )
    user = (
        "Create exactly ONE medium-to-hard multiple-choice question.\n"
        "Prefer real-life (money, online safety, transport, shopping, health, everyday decisions) "
        "or applied school reasoning (logic, grammar, science in daily life).\n"
        "Not baby-level. Requires thinking.\n\n"
        "Return ONE JSON object with keys:\n"
        "title (short, under 60 chars),\n"
        "type (real|logic|grammar|science|vocab),\n"
        "question,\n"
        "choices (array of exactly 3 strings),\n"
        "answer (A or B or C),\n"
        "reason (why correct, under 30 words),\n"
        "spoken_intro (Mike reads the question aloud, natural, under 35 words),\n"
        "spoken_reveal (Mike says the answer and short why, under 40 words),\n"
        "topic_hashtags (array of 3-6 topic tags without forcing fyp),\n"
        "youtube_description,\n"
        "tiktok_caption,\n"
        "instagram_caption,\n"
        "facebook_caption\n"
    )
    key = gemini_key()
    models = [
        os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
    ]
    seen = set()
    for model in models:
        if not key or model in seen:
            continue
        seen.add(model)
        for attempt in range(3):
            print("TEASER_GEMINI", model, "attempt", attempt + 1, file=sys.stderr)
            content = _call_gemini(key, model, system, user)
            data = parse_json_obj(content)
            if data:
                packed = normalize_payload(data)
                if packed:
                    packed["engine"] = f"gemini:{model}"
                    return packed
            time.sleep(0.8 * (attempt + 1))

    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if or_key:
        model = os.environ.get("OPENROUTER_MODEL", "openrouter/free").strip()
        for attempt in range(2):
            print("TEASER_OR", model, "attempt", attempt + 1, file=sys.stderr)
            content = _call_openrouter(or_key, model, system, user)
            data = parse_json_obj(content)
            if data:
                packed = normalize_payload(data)
                if packed:
                    packed["engine"] = f"openrouter:{model}"
                    return packed
            time.sleep(1.0)
    return None


def write_side_files(job: dict) -> None:
    tags = " ".join(job.get("hashtags") or ALWAYS_TAGS)
    caps = job.get("captions") or {}
    Path("title_short.txt").write_text(job.get("title") or "Quiz", encoding="utf-8")
    Path("tiktok_caption.txt").write_text(
        f"{(caps.get('tiktok') or job.get('title') or 'Quiz').strip()}\n\n{tags}\n", encoding="utf-8"
    )
    Path("tiktok_comment.txt").write_text(
        f"Answer: watch the reveal. Follow @mike · {tags}\n", encoding="utf-8"
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
    # script.txt for legacy tools
    Path("script.txt").write_text(
        f"{job.get('spoken_intro','')}\n{job.get('spoken_reveal','')}\n", encoding="utf-8"
    )


def main() -> None:
    packed = fetch_ai_question()
    if not packed:
        print("TEASER_FAIL: AI did not return a valid question (no seed bank)", file=sys.stderr)
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

    # Timeline segments for audio/render: intro (Mike reads) -> countdown (timer) -> reveal
    segments = [
        {"phase": "intro", "q": 1, "text": packed["spoken_intro"]},
        {"phase": "countdown", "q": 1, "secs": 8},
        {"phase": "reveal", "q": 1, "text": packed["spoken_reveal"]},
    ]

    job = {
        "version": 5,
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
    print("TEASER_OK", job["engine"], job["title"], "answer", q["answer"], file=sys.stderr)
    print(json.dumps({"title": job["title"], "answer": q["answer"], "tags": job["hashtags"][:8]}))


if __name__ == "__main__":
    main()
