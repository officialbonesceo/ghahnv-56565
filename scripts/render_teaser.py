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
LIGHT = (236, 238, 242)


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


def star_pts(cx, cy, r_out, r_in, n=5):
    pts = []
    for i in range(n * 2):
        ang = -math.pi / 2 + i * math.pi / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def house_pts(cx, cy, s):
    return [
        (cx - s, cy + s),
        (cx - s, cy - s // 3),
        (cx, cy - s),
        (cx + s, cy - s // 3),
        (cx + s, cy + s),
    ]


def draw_shape(d, kind: str, cx: int, cy: int, size: int, *, outline=None, fill=None, width=6):
    if kind == "circle":
        box = [cx - size, cy - size, cx + size, cy + size]
        if fill:
            d.ellipse(box, fill=fill, outline=outline or fill, width=width)
        else:
            d.ellipse(box, outline=outline or RED, width=width)
    elif kind == "square":
        box = [cx - size, cy - size, cx + size, cy + size]
        if fill:
            d.rectangle(box, fill=fill, outline=outline or fill, width=width)
        else:
            d.rectangle(box, outline=outline or RED, width=width)
    elif kind == "triangle":
        pts = [(cx, cy - size), (cx + size, cy + size), (cx - size, cy + size)]
        if fill:
            d.polygon(pts, fill=fill, outline=outline or fill)
            if outline:
                d.line(pts + [pts[0]], fill=outline, width=width)
        else:
            d.line(pts + [pts[0]], fill=outline or RED, width=width)
    elif kind == "star":
        pts = star_pts(cx, cy, size, size * 0.42)
        if fill:
            d.polygon(pts, fill=fill, outline=outline or fill)
            if outline:
                d.line(pts + [pts[0]], fill=outline, width=width)
        else:
            d.line(pts + [pts[0]], fill=outline or RED, width=width)
    elif kind == "house":
        pts = house_pts(cx, cy, size)
        if fill:
            d.polygon(pts, fill=fill, outline=outline or fill)
            if outline:
                d.line(pts + [pts[0]], fill=outline, width=width)
        else:
            d.line(pts + [pts[0]], fill=outline or RED, width=width)
    elif kind == "egg":
        box = [cx - size * 0.7, cy - size, cx + size * 0.7, cy + size]
        if fill:
            d.ellipse(box, fill=fill, outline=outline or fill, width=width)
        else:
            d.ellipse(box, outline=outline or RED, width=width)
    else:
        box = [cx - size, cy - size, cx + size, cy + size]
        d.ellipse(box, outline=outline or RED, width=width)


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
    img = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Match", phase)

    title_f = font(38)
    t = "Match the outline"
    bb = d.textbbox((0, 0), t, font=title_f)
    d.text(((W - (bb[2] - bb[0])) // 2, 120), t, font=title_f, fill=BLACK)

    vis = item.get("visual") or {}
    shape = vis.get("shape") or "triangle"
    correct = int(vis.get("correct_index") or 1)
    choice_shapes = vis.get("choices") or ["circle", "triangle", "square"]

    cx, cy = W // 2, 420
    if shape == "eggs":
        for i in range(3):
            x = 280 + i * 180
            draw_shape(d, "egg", x + 50, 400, 70, outline=RED, width=7)
            if phase == "reveal":
                draw_shape(d, "egg", x + 50, 400, 55, fill=(210, 150, 80), outline=RED, width=3)
    else:
        draw_shape(d, shape, cx, cy, 140, outline=RED, width=8)
        if phase == "reveal":
            fill_map = {
                "triangle": (90, 150, 220),
                "star": (240, 190, 50),
                "house": (100, 160, 100),
                "circle": (120, 120, 200),
                "square": (180, 100, 100),
            }
            draw_shape(d, shape, cx, cy, 120, fill=fill_map.get(shape, (100, 160, 200)), outline=RED, width=4)

    labels = ["A", "B", "C"]
    for i, lab in enumerate(labels):
        x0 = 90 + i * 310
        y0 = 700
        hit = phase == "reveal" and i == correct
        d.rounded_rectangle(
            [x0, y0, x0 + 280, y0 + 320],
            24,
            fill=(40, 120, 70) if hit else LIGHT,
            outline=ACCENT if hit else (190, 192, 200),
            width=5 if hit else 3,
        )
        d.text((x0 + 120, y0 + 18), lab, font=font(40), fill=WHITE if hit else BLACK)

        mx, my = x0 + 140, y0 + 180
        if shape == "eggs":
            n_eggs = [2, 3, 4][i]
            for e in range(n_eggs):
                ex = mx - (n_eggs - 1) * 28 + e * 56
                draw_shape(
                    d, "egg", ex, my, 36,
                    fill=(210, 150, 80) if hit else (160, 160, 165),
                    outline=BLACK if not hit else RED,
                    width=3,
                )
        else:
            cs = choice_shapes[i] if i < len(choice_shapes) else "circle"
            draw_shape(
                d, cs, mx, my, 70,
                fill=(40, 120, 70) if hit else None,
                outline=WHITE if hit else BLACK,
                width=5,
            )

    if phase != "reveal":
        msg = "Comment A, B, or C"
        mf = font(36)
        bb = d.textbbox((0, 0), msg, font=mf)
        d.text(((W - (bb[2] - bb[0])) // 2, H - 160), msg, font=mf, fill=RED)
    else:
        reason = (item.get("reason") or "")[:110]
        rf = font(30)
        for j, line in enumerate(wrap(d, reason, rf, W - 100)[:3]):
            bb = d.textbbox((0, 0), line, font=rf)
            d.text(((W - (bb[2] - bb[0])) // 2, H - 220 + j * 38), line, font=rf, fill=BLACK)
    return img


def draw_traffic(phase: str, item: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), (40, 48, 55))
    d = ImageDraw.Draw(img)
    header(d, item.get("title") or "Traffic", phase)
    d.rectangle([60, 160, W - 60, 900], fill=(55, 62, 70))
    d.rectangle([100, 220, W - 100, 820], fill=(70, 78, 88))
    for lx in (360, 620):
        for ly in range(240, 800, 40):
            d.rectangle([lx, ly, lx + 8, ly + 22], fill=(200, 200, 120))
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
            d.rounded_rectangle([x - 10, y - 10, x + 130, y + 90], 14, outline=ACCENT, width=6)
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
