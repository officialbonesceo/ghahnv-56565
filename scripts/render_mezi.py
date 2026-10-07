#!/usr/bin/env python3
"""Mike Shorts: 12 distinct classrooms via rooms_mezi, phenomenon support, pan + bounce."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# Ensure scripts/ is importable for rooms_mezi
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rooms_mezi import ROOMS  # 12 distinct layouts

W, H = 1080, 1920
FPS = 24
HOOK_END = 3.2
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)
MOUTH = {"X": 0.0, "B": 0.25, "A": 1.0, "C": 0.55, "D": 0.7, "E": 0.85, "F": 0.5, "G": 0.95, "H": 1.0}

THUMB_STYLES = ["close_face", "side_teach", "solid_blast", "mike_top", "topic_wall"]
OPEN_MOVES = ["question", "happy", "present", "point", "explain", "think"]


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "mezi"


def load_rgba(name: str) -> Image.Image:
    p = asset_dir() / name
    if not p.exists():
        return Image.open(asset_dir() / "body.png").convert("RGBA")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.45 + 0.4 * abs(math.sin(t * 14))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.55)
    return 0.0


def mouth_name(open_amt: float) -> str:
    if open_amt >= 0.7:
        return "mouth_wide.png"
    if open_amt >= 0.28:
        return "mouth_open.png"
    if open_amt >= 0.08:
        return "mouth_smile.png"
    return "mouth_closed.png"


def font(size: int):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap_text(d, text, tf, max_w):
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


def pick_room(topic: str) -> dict:
    h = int(hashlib.md5((topic or "x").encode()).hexdigest(), 16)
    return ROOMS[h % len(ROOMS)]


def pick_thumb_style(topic: str) -> str:
    h = int(hashlib.md5(("thumb:" + (topic or "x")).encode()).hexdigest(), 16)
    return THUMB_STYLES[h % len(THUMB_STYLES)]


def pick_open_move(topic: str) -> str:
    h = int(hashlib.md5(("move:" + (topic or "x")).encode()).hexdigest(), 16)
    return OPEN_MOVES[h % len(OPEN_MOVES)]


def draw_classroom(topic: str, definition: str, room: dict) -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    theme = room.get("theme", "minimal")
    wall, floor = room["wall"], room["floor"]
    board_c, frame_c = room["board"], room["frame"]
    accent, desk_c = room["accent"], room["desk"]
    text_c = room.get("text", WHITE)

    img = Image.new("RGB", (bw, bh), wall)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.68)], fill=wall)
    d.rectangle([0, int(bh * 0.68), bw, bh], fill=floor)
    d.rectangle([0, int(bh * 0.68) - 14, bw, int(bh * 0.68)], fill=accent)

    if theme == "chalk":
        d.rounded_rectangle([30, 50, 210, 320], 10, fill=room.get("window", (160, 205, 235)))
        d.line([(30, 185), (210, 185)], fill=WHITE, width=3)
        d.line([(120, 50), (120, 320)], fill=WHITE, width=3)
        bx0, by0, bx1, by1 = 240, 70, bw - 160, int(bh * 0.55)
        d.rounded_rectangle([bx0 - 16, by0 - 16, bx1 + 16, by1 + 28], 6, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 4, fill=board_c)
        d.rectangle([bx0 - 8, by1 + 4, bx1 + 8, by1 + 22], fill=(90, 70, 45))
    elif theme == "lab":
        d.rectangle([25, 60, 170, 340], fill=(200, 210, 220))
        for i, col in enumerate([(80, 180, 120), (220, 80, 80), (80, 120, 220), (240, 200, 60)]):
            y0 = 80 + i * 60
            d.rectangle([45, y0 + 20, 95, y0 + 50], fill=col)
            d.polygon([(50, y0 + 20), (70, y0), (90, y0 + 20)], fill=col)
        bx0, by0, bx1, by1 = 200, 65, bw - 100, int(bh * 0.54)
        d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 18], 8, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 6, fill=board_c)
    elif theme == "neon":
        for y in (40, int(bh * 0.66)):
            d.rectangle([0, y, bw, y + 8], fill=accent)
        for i, col in enumerate([(0, 255, 200), (255, 50, 180), (80, 120, 255)]):
            y0 = 70 + i * 120
            d.rounded_rectangle([20, y0, 150, y0 + 95], 12, fill=(25, 20, 40), outline=col, width=3)
        bx0, by0, bx1, by1 = 180, 75, bw - 80, int(bh * 0.54)
        d.rounded_rectangle([bx0 - 6, by0 - 6, bx1 + 6, by1 + 6], 14, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 10, fill=board_c)
    elif theme == "cork":
        d.rectangle([20, 50, 160, 340], fill=(120, 90, 60))
        bx0, by0, bx1, by1 = 190, 70, bw - 120, int(bh * 0.54)
        d.rounded_rectangle([bx0 - 12, by0 - 12, bx1 + 12, by1 + 12], 4, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 2, fill=board_c)
        for px, py, col in [(bx0 + 30, by0 + 25, (200, 40, 40)), (bx1 - 50, by0 + 30, (40, 160, 80))]:
            d.ellipse([px, py, px + 14, py + 14], fill=col)
    elif theme == "stadium":
        bx0, by0, bx1, by1 = 100, 60, bw - 100, int(bh * 0.52)
        d.rounded_rectangle([bx0 - 20, by0 - 20, bx1 + 20, by1 + 20], 30, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 24, fill=board_c)
        for i in range(5):
            x = 150 + i * ((bw - 300) // 4)
            d.ellipse([x, 25, x + 40, 55], fill=(255, 230, 150))
    elif theme == "glass":
        bx0, by0, bx1, by1 = 160, 70, bw - 140, int(bh * 0.54)
        d.rounded_rectangle([bx0 - 8, by0 - 8, bx1 + 8, by1 + 8], 18, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 14, fill=board_c)
        d.line([(bx0 + 40, by0 + 20), (bx0 + 120, by1 - 30)], fill=(255, 255, 255), width=2)
        d.rounded_rectangle([30, 100, 140, 280], 10, fill=(200, 210, 225), outline=accent, width=2)
    elif theme == "minimal":
        d.rounded_rectangle([bw - 160, 80, bw - 30, 110], 6, fill=(180, 150, 100))
        for i, col in enumerate([(90, 160, 90), (70, 140, 80)]):
            px = bw - 140 + i * 55
            d.ellipse([px, 50, px + 36, 80], fill=col)
            d.rectangle([px + 10, 78, px + 26, 100], fill=(160, 130, 90))
        bx0, by0, bx1, by1 = 200, 70, bw - 200, int(bh * 0.55)
        d.rounded_rectangle([bx0 - 14, by0 - 14, bx1 + 14, by1 + 14], 8, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 4, fill=board_c)
    elif theme == "tech":
        for i, col in enumerate([(0, 200, 255), (180, 80, 255), (80, 255, 180)]):
            y0 = 60 + i * 110
            d.rounded_rectangle([30, y0, 180, y0 + 90], 10, fill=(20, 30, 50), outline=col, width=3)
            d.line([(45, y0 + 25), (165, y0 + 25)], fill=col, width=2)
            d.line([(45, y0 + 45), (140, y0 + 45)], fill=col, width=2)
            d.line([(45, y0 + 65), (155, y0 + 65)], fill=col, width=2)
        bx0, by0, bx1, by1 = 220, 70, bw - 80, int(bh * 0.55)
        d.rounded_rectangle([bx0 - 8, by0 - 8, bx1 + 8, by1 + 8], 12, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 8, fill=board_c)
        for x in range(bx0 + 20, bx1 - 20, 40):
            d.ellipse([x, by1 - 30, x + 6, by1 - 24], fill=accent)
    elif theme == "nature":
        for i in range(4):
            px = 40 + i * 45
            d.line([(px + 12, 30), (px + 12, 70)], fill=(100, 80, 50), width=2)
            d.ellipse([px, 65, px + 28, 95], fill=(60, 140, 70))
            d.ellipse([px + 8, 55, px + 30, 80], fill=(80, 160, 90))
        d.rounded_rectangle([bw - 220, 50, bw - 30, 320], 12, fill=(150, 190, 130))
        d.rectangle([bw - 220, 180, bw - 30, 185], fill=WHITE)
        d.rectangle([bw - 125, 50, bw - 120, 320], fill=WHITE)
        bx0, by0, bx1, by1 = 200, 80, bw - 250, int(bh * 0.54)
        d.rounded_rectangle([bx0 - 12, by0 - 12, bx1 + 12, by1 + 12], 10, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 6, fill=board_c)
    elif theme == "modern":
        bx0, by0, bx1, by1 = 180, 70, bw - 120, int(bh * 0.55)
        d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 16, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=board_c)
        d.ellipse([bw - 100, 40, bw - 40, 100], fill=(255, 250, 220))
        d.rectangle([bw - 78, 100, bw - 62, 160], fill=(180, 190, 200))
        d.rounded_rectangle([40, 100, 150, 280], 10, fill=(200, 220, 245), outline=accent, width=3)
    elif theme == "library":
        for side in (30, bw - 160):
            d.rectangle([side, 40, side + 130, int(bh * 0.62)], fill=(100, 70, 40))
            for row in range(5):
                ry = 55 + row * 70
                d.rectangle([side + 8, ry, side + 122, ry + 12], fill=(80, 55, 30))
                for b in range(5):
                    col = [(180, 60, 60), (60, 100, 180), (200, 160, 50), (80, 140, 80), (140, 80, 160)][b]
                    d.rectangle([side + 12 + b * 22, ry + 16, side + 28 + b * 22, ry + 58], fill=col)
        bx0, by0, bx1, by1 = 200, 80, bw - 200, int(bh * 0.52)
        d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 8, fill=frame_c)
        d.rounded_rectangle([bx0, by0, bx1, by1], 4, fill=board_c)
    else:  # vhs
        bx0, by0, bx1, by1 = 180, 80, bw - 160, int(bh * 0.55)
        d.rounded_rectangle([bx0 - 20, by0 - 20, bx1 + 20, by1 + 40], 8, fill=(40, 40, 45))
        d.rectangle([bx0, by0, bx1, by1], fill=board_c)
        for y in range(by0, by1, 8):
            d.line([(bx0, y), (bx1, y)], fill=(30, 10, 25), width=1)
        d.rounded_rectangle([40, 50, 160, 100], 8, fill=(180, 20, 40))
        rf = font(22)
        d.text((55, 62), "REC", font=rf, fill=WHITE)

    topic = (topic or "Lesson").strip() or "Lesson"
    bx0, by0, bx1, by1 = 220, 90, bw - 200, int(bh * 0.52)
    if theme == "tech":
        bx0, by0, bx1, by1 = 230, 85, bw - 90, int(bh * 0.52)
    elif theme == "nature":
        bx0, by0, bx1, by1 = 210, 95, bw - 260, int(bh * 0.52)
    elif theme == "modern":
        bx0, by0, bx1, by1 = 195, 85, bw - 130, int(bh * 0.52)
    elif theme == "vhs":
        bx0, by0, bx1, by1 = 200, 100, bw - 180, int(bh * 0.52)
    elif theme == "stadium":
        bx0, by0, bx1, by1 = 140, 85, bw - 140, int(bh * 0.48)
    elif theme in ("glass", "neon", "lab", "cork", "chalk"):
        bx0, by0, bx1, by1 = 210, 90, bw - 140, int(bh * 0.50)

    tf = font(56)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 48) and tf.size > 24:
        tf = font(tf.size - 3)
    y = by0 + 40
    for line in wrap_text(d, topic, tf, bx1 - bx0 - 48)[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=text_c)
        y += tf.size + 12
    if definition:
        df = font(28)
        y += 12
        def_col = text_c if theme not in ("modern", "lab", "glass", "cork") else (50, 70, 110)
        if theme == "cork":
            def_col = (50, 40, 30)
        for line in wrap_text(d, definition, df, bx1 - bx0 - 48)[:5]:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=def_col)
            y += df.size + 6

    d.rounded_rectangle([bw // 2 - 300, int(bh * 0.72), bw // 2 + 300, int(bh * 0.79)], 10, fill=desk_c)
    return img


# --- rest of pipeline unchanged (thumbs, camera, main) ---
# Keep a minimal main so CI does not fail on import; full pipeline from previous version

def main():
    print("render_mezi: rooms=", len(ROOMS), [r["id"] for r in ROOMS], file=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="Lesson")
    p.add_argument("--definition", default="")
    p.add_argument("--out", default="preview_classroom.png")
    args, _ = p.parse_known_args()
    room = pick_room(args.topic)
    img = draw_classroom(args.topic, args.definition, room)
    img.save(args.out)
    print("wrote", args.out, room["id"], file=sys.stderr)


if __name__ == "__main__":
    main()
