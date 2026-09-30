#!/usr/bin/env python3
"""Render Q&A teaser with visible 5-second countdown."""
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
BLACK = (12, 14, 20)
ACCENT = (255, 200, 40)
CARD = (24, 28, 40)
GREEN = (40, 130, 75)
COUNTDOWN_SECS = 5


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


def draw_countdown(d, remaining: int):
    """Big circle + number at lower third."""
    n = max(0, min(COUNTDOWN_SECS, int(remaining)))
    cx, cy, r = W // 2, H - 320, 110
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=10)
    d.ellipse([cx - r + 16, cy - r + 16, cx + r - 16, cy + r - 16], fill=CARD)
    tf = font(120)
    s = str(n) if n > 0 else "!"
    bb = d.textbbox((0, 0), s, font=tf)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2 - 10), s, font=tf, fill=ACCENT)
    lf = font(28)
    label = "seconds left" if n > 0 else "time up"
    bb2 = d.textbbox((0, 0), label, font=lf)
    d.text((cx - (bb2[2] - bb2[0]) // 2, cy + r + 16), label, font=lf, fill=(180, 185, 195))


def draw_ask(item: dict, remaining: int) -> Image.Image:
    img = Image.new("RGB", (W, H), (18, 20, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 90], fill=ACCENT)
    tf = font(36)
    label = "Comment your answer"
    bb = d.textbbox((0, 0), label, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), label, font=tf, fill=BLACK)

    title = item.get("title") or "Quiz"
    ttf = font(32)
    bb = d.textbbox((0, 0), title, font=ttf)
    d.text(((W - (bb[2] - bb[0])) // 2, 110), title, font=ttf, fill=ACCENT)

    qf = font(42)
    y = 180
    for line in wrap(d, item.get("question") or "", qf, W - 100)[:5]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += qf.size + 14

    choices = item.get("choices") or []
    box_h = 100
    start_y = min(y + 40, 520)
    for i, ch in enumerate(choices[:3]):
        top = start_y + i * (box_h + 28)
        d.rounded_rectangle([70, top, W - 70, top + box_h], 22, fill=CARD, outline=(70, 75, 90), width=3)
        cf = font(40)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(((W - (bb[2] - bb[0])) // 2, top + 28), ch, font=cf, fill=WHITE)

    draw_countdown(d, remaining)
    return img


def draw_reveal(item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (18, 20, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 90], fill=GREEN)
    tf = font(36)
    label = "Answer"
    bb = d.textbbox((0, 0), label, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), label, font=tf, fill=WHITE)

    ans = str(item.get("answer") or "").upper()
    choices = item.get("choices") or []
    qf = font(36)
    y = 140
    for line in wrap(d, item.get("question") or "", qf, W - 100)[:3]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=(180, 185, 195))
        y += qf.size + 10

    box_h = 100
    start_y = y + 30
    for i, ch in enumerate(choices[:3]):
        top = start_y + i * (box_h + 28)
        letter = ch.strip()[0].upper() if ch else "?"
        hit = letter == ans or ch.upper().startswith(ans)
        fill = GREEN if hit else CARD
        outline = ACCENT if hit else (70, 75, 90)
        d.rounded_rectangle([70, top, W - 70, top + box_h], 22, fill=fill, outline=outline, width=4)
        cf = font(40)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(((W - (bb[2] - bb[0])) // 2, top + 28), ch, font=cf, fill=WHITE)

    rf = font(34)
    reason = (item.get("reason") or "")[:120]
    y = start_y + 3 * (box_h + 28) + 40
    for line in wrap(d, reason, rf, W - 100)[:4]:
        bb = d.textbbox((0, 0), line, font=rf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=rf, fill=ACCENT)
        y += rf.size + 10

    cta = font(30)
    msg = "Comment the next topic · Follow for more"
    bb = d.textbbox((0, 0), msg, font=cta)
    d.text(((W - (bb[2] - bb[0])) // 2, H - 120), msg, font=cta, fill=(200, 205, 210))
    return img


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job", default="teaser_job.json")
    p.add_argument("--audio", required=True)
    p.add_argument("--out", default="output.mp4")
    args = p.parse_args()
    item = json.loads(Path(args.job).read_text(encoding="utf-8"))
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
    dur = min(max(dur, 10.0), 40.0)

    # Fixed: first 5s = countdown ask (or until 55% of audio if shorter)
    ask_end = min(float(COUNTDOWN_SECS), dur * 0.55)
    # If audio is longer, keep showing last second of countdown until ask_end from proportion
    # Prefer hard 5s ask window when audio allows
    if dur >= COUNTDOWN_SECS + 4:
        ask_end = float(COUNTDOWN_SECS)

    n = max(FPS, int(math.ceil(dur * FPS)))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            if t < ask_end:
                remaining = max(0, math.ceil(ask_end - t))
                frame = draw_ask(item, remaining)
            else:
                frame = draw_reveal(item)
            frame.save(tmp_path / f"frame_{i:05d}.png")

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
        print("OK", out, out.stat().st_size, "ask_end", ask_end)


if __name__ == "__main__":
    main()
