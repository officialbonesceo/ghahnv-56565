#!/usr/bin/env python3
"""Render multi-question language teaser from timeline (ask → 5s → reveal)."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
WHITE = (255, 255, 255)
BLACK = (15, 18, 28)
YELLOW = (255, 210, 50)
CARD = (28, 34, 52)
GREEN = (36, 140, 85)
RED = (220, 60, 70)
SOFT = (160, 170, 190)
BG = (14, 18, 32)


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap(d, text, tf, max_w):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def q_by_index(job: dict, qi: int | None) -> dict | None:
    if not qi:
        return None
    for q in job.get("questions") or []:
        if q.get("index") == qi:
            return q
    return None


def draw_intro() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 120], fill=YELLOW)
    t = font(48)
    s = "ENGLISH QUIZ"
    bb = d.textbbox((0, 0), s, font=t)
    d.text(((W - (bb[2] - bb[0])) // 2, 36), s, font=t, fill=BLACK)
    sub = font(40)
    msg = "Easy questions · Comment A B or C"
    bb = d.textbbox((0, 0), msg, font=sub)
    d.text(((W - (bb[2] - bb[0])) // 2, 900), msg, font=sub, fill=WHITE)
    tip = font(32)
    m2 = "Get ready!"
    bb = d.textbbox((0, 0), m2, font=tip)
    d.text(((W - (bb[2] - bb[0])) // 2, 1000), m2, font=tip, fill=YELLOW)
    return img


def draw_outro(job: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 120], fill=GREEN)
    t = font(44)
    s = "HOW MANY DID YOU GET?"
    bb = d.textbbox((0, 0), s, font=t)
    d.text(((W - (bb[2] - bb[0])) // 2, 38), s, font=t, fill=WHITE)
    y = 400
    for q in job.get("questions") or []:
        line = f"Q{q['index']}: {q['answer']}"
        tf = font(48)
        bb = d.textbbox((0, 0), line, font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=YELLOW)
        y += 90
    cta = font(34)
    msg = "Comment your score · Follow for more"
    bb = d.textbbox((0, 0), msg, font=cta)
    d.text(((W - (bb[2] - bb[0])) // 2, H - 200), msg, font=cta, fill=SOFT)
    return img


def draw_ask(q: dict, remaining: int | None = None) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=YELLOW)
    label = f"Question {q.get('index', '')}"
    tf = font(40)
    bb = d.textbbox((0, 0), label, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), label, font=tf, fill=BLACK)

    qf = font(44)
    y = 160
    for line in wrap(d, q.get("question") or "", qf, W - 100)[:5]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += 58

    start_y = max(y + 40, 480)
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        top = start_y + i * 130
        d.rounded_rectangle([60, top, W - 60, top + 110], 24, fill=CARD, outline=(60, 70, 95), width=3)
        cf = font(42)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(((W - (bb[2] - bb[0])) // 2, top + 32), ch, font=cf, fill=WHITE)

    if remaining is not None:
        n = max(0, int(remaining))
        cx, cy, r = W // 2, H - 280, 100
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=YELLOW, width=10)
        d.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], fill=CARD)
        nf = font(110)
        s = str(n) if n > 0 else "!"
        bb = d.textbbox((0, 0), s, font=nf)
        d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2 - 8), s, font=nf, fill=YELLOW)
        lf = font(28)
        lab = "seconds left — comment now" if n > 0 else "time up"
        bb = d.textbbox((0, 0), lab, font=lf)
        d.text((cx - (bb[2] - bb[0]) // 2, cy + r + 18), lab, font=lf, fill=SOFT)
    else:
        tip = font(32)
        msg = "Get ready to comment…"
        bb = d.textbbox((0, 0), msg, font=tip)
        d.text(((W - (bb[2] - bb[0])) // 2, H - 180), msg, font=tip, fill=YELLOW)
    return img


def draw_reveal(q: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=GREEN)
    tf = font(40)
    label = f"Answer · Question {q.get('index', '')}"
    bb = d.textbbox((0, 0), label, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), label, font=tf, fill=WHITE)

    ans = str(q.get("answer") or "").upper()
    y = 160
    qf = font(36)
    for line in wrap(d, q.get("question") or "", qf, W - 100)[:3]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=SOFT)
        y += 48

    start_y = y + 36
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        top = start_y + i * 130
        letter = ch.strip()[0].upper() if ch else "?"
        hit = letter == ans or ch.upper().startswith(ans)
        fill = GREEN if hit else CARD
        outline = YELLOW if hit else (50, 58, 78)
        d.rounded_rectangle([60, top, W - 60, top + 110], 24, fill=fill, outline=outline, width=4)
        cf = font(42)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(((W - (bb[2] - bb[0])) // 2, top + 32), ch, font=cf, fill=WHITE)

    rf = font(36)
    reason = (q.get("reason") or "")[:100]
    y = start_y + 3 * 130 + 30
    for line in wrap(d, reason, rf, W - 100)[:3]:
        bb = d.textbbox((0, 0), line, font=rf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=rf, fill=YELLOW)
        y += 48
    return img


def frame_at(job: dict, timeline: list, t: float) -> Image.Image:
    # find segment
    seg = timeline[-1]
    for s in timeline:
        if s["start"] <= t < s["end"] or (s is timeline[-1] and t >= s["start"]):
            if t < s["end"] or s is timeline[-1]:
                seg = s
                if t < s["end"]:
                    break
    phase = seg.get("phase")
    qi = seg.get("q")
    q = q_by_index(job, qi)

    if phase == "intro":
        return draw_intro()
    if phase == "outro":
        return draw_outro(job)
    if phase == "countdown" and q:
        remaining = max(0, math.ceil(seg["end"] - t))
        return draw_ask(q, remaining=remaining)
    if phase == "ask" and q:
        return draw_ask(q, remaining=None)
    if phase == "reveal" and q:
        return draw_reveal(q)
    return draw_intro()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job", default="teaser_job.json")
    p.add_argument("--timeline", default="teaser_timeline.json")
    p.add_argument("--audio", required=True)
    p.add_argument("--out", default="output.mp4")
    args = p.parse_args()

    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    tl_path = Path(args.timeline)
    if not tl_path.exists():
        sys.exit("missing teaser_timeline.json — run assemble_teaser_audio.py first")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    timeline = tl["timeline"]
    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")

    dur = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio),
            ],
            text=True,
        ).strip()
    )
    n = max(FPS, int(math.ceil(dur * FPS)))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            frame_at(job, timeline, t).save(tmp_path / f"frame_{i:05d}.png")
        out = Path(args.out).resolve()
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(tmp_path / "frame_%05d.png"),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(out),
            ]
        )
        print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
