#!/usr/bin/env python3
"""Render auto-drawn teaser video (options / outline / traffic / pattern)."""
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
RED = (230, 50, 60)
CARD = (24, 28, 40)


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


def header(d, title: str, phase: str):
    d.rectangle([0, 0, W, 90], fill=ACCENT)
    tf = font(36)
    label = "99% pause here" if phase == "ask" else ("Answer" if phase == "reveal" else title)
    bb = d.textbbox((0, 0), label, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), label, font=tf, fill=BLACK)


def draw_options(phase: str, item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (18, 20, 30))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Quiz", phase)
    qf = font(40)
    y = 140
    for line in wrap(d, item.get("question") or "", qf, W - 100)[:4]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += qf.size + 12
    choices = item.get("choices") or []
    ans = str(item.get("answer") or "").upper()
    box_h = 110
    start_y = 420
    for i, ch in enumerate(choices[:3]):
        top = start_y + i * (box_h + 36)
        letter = ch.strip()[0].upper() if ch else "?"
        fill = (40, 120, 70) if phase == "reveal" and (
            letter == ans or ch.upper().startswith(ans)
        ) else CARD
        outline = ACCENT if phase == "reveal" and (letter == ans or ch.upper().startswith(ans)) else (70, 75, 90)
        d.rounded_rectangle([80, top, W - 80, top + box_h], 24, fill=fill, outline=outline, width=4)
        cf = font(42)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(((W - (bb[2] - bb[0])) // 2, top + 32), ch, font=cf, fill=WHITE)
    if phase == "reveal":
        rf = font(32)
        reason = (item.get("reason") or "")[:90]
        y = start_y + 3 * (box_h + 36) + 20
        for line in wrap(d, reason, rf, W - 100)[:3]:
            bb = d.textbbox((0, 0), line, font=rf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=rf, fill=(200, 210, 220))
            y += rf.size + 8
    else:
        hf = font(34)
        msg = "Comment A, B, or C"
        bb = d.textbbox((0, 0), msg, font=hf)
        d.text(((W - (bb[2] - bb[0])) // 2, H - 160), msg, font=hf, fill=ACCENT)
    return img


def draw_outline(phase: str, item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (245, 245, 248))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Match", phase)
    d.text((W // 2 - 80, 120), "Match the outline", font=font(34), fill=BLACK)
    vis = item.get("visual") or {}
    shape = vis.get("shape") or "triangle"
    correct = int(vis.get("correct_index") or 1)

    # main outline area
    cx, cy = W // 2, 480
    if shape == "eggs":
        for i in range(3):
            x = 280 + i * 180
            d.ellipse([x, 360, x + 100, 500], outline=RED, width=6)
            if phase == "reveal":
                d.ellipse([x + 10, 370, x + 90, 490], fill=(180, 120, 60))
    elif shape == "croc":
        # simple side silhouette
        pts = [
            (200, 520), (280, 480), (420, 470), (560, 490), (700, 510),
            (780, 480), (820, 500), (780, 540), (700, 560), (500, 570),
            (350, 560), (250, 540),
        ]
        d.line(pts + [pts[0]], fill=RED, width=7)
        if phase == "reveal":
            d.polygon(pts, fill=(80, 120, 70), outline=RED)
    else:  # triangle
        pts = [(cx, 320), (cx + 200, 580), (cx - 200, 580)]
        d.line(pts + [pts[0]], fill=RED, width=8)
        if phase == "reveal":
            d.polygon(pts, fill=(100, 160, 220), outline=RED)

    # three choice slots
    labels = ["A", "B", "C"]
    for i, lab in enumerate(labels):
        x0 = 120 + i * 300
        y0 = 720
        hit = phase == "reveal" and i == correct
        d.rounded_rectangle([x0, y0, x0 + 240, y0 + 280], 20, fill=(30, 34, 48) if hit else (230, 232, 238),
                            outline=ACCENT if hit else (180, 180, 190), width=4)
        d.text((x0 + 100, y0 + 20), lab, font=font(36), fill=WHITE if hit else BLACK)
        # mini shapes
        mx, my = x0 + 120, y0 + 150
        if shape == "eggs":
            d.ellipse([mx - 30, my - 40, mx + 30, my + 40], fill=(180, 120, 60) if i == correct else (200, 200, 200))
        elif shape == "croc":
            d.ellipse([mx - 50, my - 20, mx + 50, my + 30], fill=(80, 120, 70) if i == correct else (200, 200, 200))
        else:
            if i == 0:
                d.ellipse([mx - 40, my - 40, mx + 40, my + 40], outline=BLACK, width=4)
            elif i == 1:
                d.polygon([(mx, my - 50), (mx + 50, my + 40), (mx - 50, my + 40)], outline=BLACK, width=4)
            else:
                d.rectangle([mx - 40, my - 40, mx + 40, my + 40], outline=BLACK, width=4)

    if phase != "reveal":
        d.text((W // 2 - 160, H - 140), "Comment A, B, or C", font=font(34), fill=RED)
    else:
        reason = (item.get("reason") or "")[:100]
        for j, line in enumerate(wrap(d, reason, font(28), W - 100)[:3]):
            bb = d.textbbox((0, 0), line, font=font(28))
            d.text(((W - (bb[2] - bb[0])) // 2, H - 200 + j * 36), line, font=font(28), fill=BLACK)
    return img


def draw_traffic(phase: str, item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (40, 48, 55))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Traffic", phase)
    d.rectangle([60, 160, W - 60, 900], fill=(55, 62, 70))
    # road grid
    d.rectangle([100, 220, W - 100, 820], fill=(70, 78, 88))
    colors = [
        (30, 60, 120), (180, 40, 40), (40, 140, 60), (220, 220, 220),
        (220, 100, 40), (40, 100, 180), (220, 200, 40),
    ]
    positions = [
        (140, 260), (140, 420), (320, 520), (480, 300), (700, 260),
        (700, 450), (700, 620),
    ]
    correct = int((item.get("visual") or {}).get("correct") or 3)
    for i, (x, y) in enumerate(positions):
        n = i + 1
        col = colors[i % len(colors)]
        if phase == "reveal" and n == correct:
            d.rounded_rectangle([x - 8, y - 8, x + 128, y + 88], 12, outline=ACCENT, width=5)
        d.rounded_rectangle([x, y, x + 120, y + 80], 10, fill=col)
        d.text((x + 45, y + 22), str(n), font=font(36), fill=WHITE)
    qf = font(36)
    y = 940
    for line in wrap(d, item.get("question") or "", qf, W - 100)[:3]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += 44
    if phase == "reveal":
        msg = f"Answer: {item.get('answer')} — {(item.get('reason') or '')[:70]}"
        for j, line in enumerate(wrap(d, msg, font(30), W - 100)[:3]):
            bb = d.textbbox((0, 0), line, font=font(30))
            d.text(((W - (bb[2] - bb[0])) // 2, 1200 + j * 40), line, font=font(30), fill=ACCENT)
    else:
        d.text((W // 2 - 200, H - 150), "Comment the car number", font=font(34), fill=ACCENT)
    return img


def draw_pattern(phase: str, item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (20, 22, 32))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Pattern", phase)
    seq = (item.get("visual") or {}).get("seq") or [2, 4, 8, 16, "?"]
    box = 140
    total_w = len(seq) * (box + 24) - 24
    x0 = (W - total_w) // 2
    y0 = 420
    for i, val in enumerate(seq):
        x = x0 + i * (box + 24)
        d.rounded_rectangle([x, y0, x + box, y0 + box], 20, fill=CARD, outline=ACCENT, width=3)
        s = str(val)
        tf = font(48)
        bb = d.textbbox((0, 0), s, font=tf)
        d.text((x + (box - (bb[2] - bb[0])) // 2, y0 + 45), s, font=tf, fill=WHITE)
    qf = font(38)
    y = 650
    for line in wrap(d, item.get("question") or "", qf, W - 100)[:3]:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += 48
    choices = item.get("choices") or []
    for i, ch in enumerate(choices[:3]):
        top = 900 + i * 100
        hit = phase == "reveal" and str(item.get("answer") or "").upper() in ch.upper()
        d.rounded_rectangle([100, top, W - 100, top + 80], 18,
                            fill=(40, 120, 70) if hit else CARD,
                            outline=ACCENT if hit else (60, 65, 80), width=3)
        bb = d.textbbox((0, 0), ch, font=font(36))
        d.text(((W - (bb[2] - bb[0])) // 2, top + 22), ch, font=font(36), fill=WHITE)
    if phase != "reveal":
        d.text((W // 2 - 160, H - 140), "Comment A, B, or C", font=font(34), fill=ACCENT)
    return img


def frame_for(phase: str, item: dict) -> Image.Image:
    fmt = item.get("format") or "options"
    if fmt == "outline":
        return draw_outline(phase, item)
    if fmt == "traffic":
        return draw_traffic(phase, item)
    if fmt == "pattern":
        return draw_pattern(phase, item)
    return draw_options(phase, item)


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
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio),
    ], text=True).strip())
    dur = min(max(dur, 8.0), 45.0)
    n = max(FPS, int(math.ceil(dur * FPS)))
    # phases: ask 0-55%, reveal rest
    ask_end = dur * 0.55
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            phase = "ask" if t < ask_end else "reveal"
            frame_for(phase, item).save(tmp_path / f"frame_{i:05d}.png")
        out = Path(args.out).resolve()
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out),
        ])
        print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
