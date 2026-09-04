#!/usr/bin/env python3
"""MEZI vertical short: stronger bgs, Ken Burns, clearer lip sync."""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 720, 1280
FPS = 12

HOODIE = (255, 196, 40)
HOODIE_D = (235, 170, 25)
HOODIE_S = (255, 215, 90)
SKIN = (210, 155, 115)
HAIR = (28, 24, 30)
PANTS = (32, 36, 48)
SHOE = (22, 22, 28)
MOUTH_IN = (90, 35, 45)
TEETH = (245, 240, 235)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)

# More separation between closed / open for visible lip sync
MOUTH = {
    "X": 0.02,
    "A": 1.0,
    "B": 0.08,
    "C": 0.55,
    "D": 0.7,
    "E": 0.85,
    "F": 0.4,
    "G": 0.9,
    "H": 1.0,
}
ALL_ACTIONS = ["talk", "walk", "point", "laugh"]


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        # strong idle chatter so lips still move without cues
        return 0.05 + 0.75 * max(0.0, math.sin(t * 14))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.45)
    return 0.02


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def action_at(t, duration, actions):
    seg = duration / max(1, len(actions))
    return actions[min(int(t / seg), len(actions) - 1)]


def make_bg(kind: str) -> Image.Image:
    bw, bh = int(W * 1.2), int(H * 1.2)
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    k = (kind or "studio").lower().strip()
    rnd = random.Random(hash(k) & 0xFFFFFFFF)

    if k == "space":
        for y in range(bh):
            c = 6 + y // 80
            d.line([(0, y), (bw, y)], fill=(c, c + 2, 18 + c))
        for _ in range(220):
            x, y = rnd.randint(0, bw - 1), rnd.randint(0, bh - 1)
            r = rnd.choice([1, 1, 1, 2, 2, 3])
            bright = rnd.randint(180, 255)
            d.ellipse([x, y, x + r, y + r], fill=(bright, bright, 255))
        # planet
        d.ellipse([bw - 280, 120, bw - 40, 360], fill=(50, 80, 160))
        d.ellipse([bw - 250, 150, bw - 70, 330], fill=(30, 50, 110))
        d.arc([bw - 300, 180, bw - 20, 320], 200, 340, fill=(180, 200, 255), width=6)
    elif k == "ocean":
        for y in range(int(bh * 0.42)):
            d.line([(0, y), (bw, y)], fill=(120 + y // 30, 190, 235))
        for y in range(int(bh * 0.42), bh):
            depth = y - int(bh * 0.42)
            d.line([(0, y), (bw, y)], fill=(15, 70 + depth // 20, 120 + depth // 25))
        for i in range(12):
            y = int(bh * 0.42) + i * 28
            d.arc([10, y, bw - 10, y + 50], 0, 180, fill=(60, 160, 200), width=4)
    elif k == "money":
        d.rectangle([0, 0, bw, bh], fill=(236, 250, 236))
        d.rectangle([0, int(bh * 0.68), bw, bh], fill=(25, 110, 65))
        for i in range(10):
            x = 30 + (i % 5) * 150
            y = 120 + (i // 5) * 160
            d.ellipse([x, y, x + 90, y + 90], fill=(200, 230, 200), outline=(20, 100, 50), width=5)
            d.text((x + 30, y + 28), "$", fill=(20, 90, 45))
    elif k == "tech":
        for y in range(bh):
            d.line([(0, y), (bw, y)], fill=(12, 18, 32))
        # grid
        for x in range(0, bw, 40):
            d.line([(x, 0), (x, bh)], fill=(25, 40, 60), width=1)
        for y in range(0, bh, 40):
            d.line([(0, y), (bw, y)], fill=(25, 40, 60), width=1)
        for i in range(14):
            x = 40 + i * 55
            h = 40 + (i * 37) % 120
            d.rectangle([x, 180, x + 36, 180 + h], outline=(0, 220, 255), width=2)
            d.ellipse([x + 8, 150, x + 28, 170], outline=(0, 255, 200), width=2)
        d.rectangle([0, int(bh * 0.78), bw, bh], fill=(18, 28, 48))
    elif k == "science":
        for y in range(bh):
            d.line([(0, y), (bw, y)], fill=(220, 238, 255))
        d.ellipse([bw - 260, 40, bw - 40, 260], fill=(255, 210, 70))
        d.ellipse([bw - 230, 70, bw - 70, 230], fill=(255, 230, 120))
        # orbit rings
        d.arc([80, 160, 320, 400], 0, 360, fill=(80, 140, 200), width=3)
        d.ellipse([180, 260, 210, 290], fill=(60, 120, 180))
        d.rectangle([0, int(bh * 0.72), bw, bh], fill=(160, 210, 160))
    else:
        for y in range(int(bh * 0.6)):
            c = 250 - y // 40
            d.line([(0, y), (bw, y)], fill=(c, c - 3, c - 10))
        d.rectangle([0, int(bh * 0.6), bw, bh], fill=(200, 190, 175))
        d.rounded_rectangle([60, 80, 300, 320], 20, fill=(160, 210, 245), outline=(100, 140, 170), width=5)
        d.line([180, 80, 180, 320], fill=(100, 140, 170), width=4)
        d.line([60, 200, 300, 200], fill=(100, 140, 170), width=4)

    return img


def crop_ken_burns(bg: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    scale = 1.0 + 0.12 * progress
    bw, bh = bg.size
    cw, ch = min(int(W * scale), bw), min(int(H * scale), bh)
    max_x, max_y = max(0, bw - cw), max(0, bh - ch)
    x = int(max_x * progress * 0.85)
    y = int(max_y * 0.5 * (0.3 + 0.7 * math.sin(progress * math.pi)))
    return bg.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.BILINEAR)


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_mezi(img, cx, cy, mouth_open, phase, action):
    d = ImageDraw.Draw(img)
    swing = int(12 * math.sin(phase * 2.2)) if action == "walk" else 0
    bob = int(4 * math.sin(phase * 3))

    oval(d, [cx - 78, cy + 168, cx + 78, cy + 198], (20, 20, 30))

    ly = cy + 100
    d.rounded_rectangle([cx - 38 + swing, ly, cx - 10 + swing, cy + 170], 12, fill=PANTS)
    d.rounded_rectangle([cx + 10 - swing, ly, cx + 38 - swing, cy + 170], 12, fill=PANTS)
    oval(d, [cx - 48 + swing, cy + 158, cx - 2 + swing, cy + 182], SHOE)
    oval(d, [cx + 2 - swing, cy + 158, cx + 48 - swing, cy + 182], SHOE)

    d.rounded_rectangle([cx - 62, cy + 8, cx + 62, cy + 118], 28, fill=HOODIE)
    d.rounded_rectangle([cx - 40, cy + 30, cx + 40, cy + 100], 22, fill=HOODIE_S)
    d.rounded_rectangle([cx - 34, cy + 62, cx + 34, cy + 98], 14, fill=HOODIE)
    oval(d, [cx - 16, cy + 28, cx + 16, cy + 60], None, BLACK, 3)

    if action == "point":
        d.line([(cx + 55, cy + 40), (cx + 105, cy - 25)], fill=HOODIE, width=18)
        oval(d, [cx + 95, cy - 40, cx + 122, cy - 14], SKIN)
        d.line([(cx + 118, cy - 28), (cx + 145, cy - 48)], fill=SKIN, width=7)
        d.line([(cx - 55, cy + 42), (cx - 78, cy + 100)], fill=HOODIE, width=16)
        oval(d, [cx - 92, cy + 92, cx - 68, cy + 116], SKIN)
    elif action == "laugh":
        d.line([(cx - 55, cy + 45), (cx - 100, cy + 15)], fill=HOODIE, width=16)
        d.line([(cx + 55, cy + 45), (cx + 100, cy + 15)], fill=HOODIE, width=16)
        oval(d, [cx - 115, cy + 2, cx - 90, cy + 26], SKIN)
        oval(d, [cx + 90, cy + 2, cx + 115, cy + 26], SKIN)
    else:
        ay = int(7 * math.sin(phase * 2 + 0.4))
        d.line([(cx - 55, cy + 40), (cx - 80, cy + 95 + ay)], fill=HOODIE, width=16)
        d.line([(cx + 55, cy + 40), (cx + 80, cy + 95 - ay)], fill=HOODIE, width=16)
        oval(d, [cx - 95, cy + 88 + ay, cx - 70, cy + 112 + ay], SKIN)
        oval(d, [cx + 70, cy + 88 - ay, cx + 95, cy + 112 - ay], SKIN)

    d.rectangle([cx - 14, cy - 8, cx + 14, cy + 20], fill=SKIN)
    hy = cy - 78 + bob
    oval(d, [cx - 72, hy - 78, cx + 72, hy + 20], HAIR)
    oval(d, [cx - 64, hy - 58, cx + 64, hy + 58], SKIN)
    oval(d, [cx - 70, hy - 85, cx + 70, hy - 15], HAIR)
    oval(d, [cx - 58, hy - 35, cx + 58, hy + 55], SKIN)
    for ox, oy, r in [(-42, -88, 22), (-12, -98, 24), (18, -100, 26), (48, -90, 22)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)

    ey = hy - 8
    if action == "laugh":
        d.arc([cx - 36, ey - 6, cx - 8, ey + 14], 200, 340, fill=BLACK, width=4)
        d.arc([cx + 8, ey - 6, cx + 36, ey + 14], 200, 340, fill=BLACK, width=4)
    else:
        oval(d, [cx - 38, ey - 18, cx - 6, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx + 6, ey - 18, cx + 38, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx - 30, ey - 8, cx - 14, ey + 10], BLACK)
        oval(d, [cx + 14, ey - 8, cx + 30, ey + 10], BLACK)

    # BIG mouth for visible lip sync
    my = hy + 30
    mw = 14 + int(20 * mouth_open)
    mh = 2 + int(34 * mouth_open)
    if action == "laugh":
        mw, mh = max(mw, 34), max(mh, 26)
    x0, y0, x1, y1 = cx - mw, my - max(2, mh // 5), cx + mw, my + mh
    oval(d, [x0, y0, x1, y1], MOUTH_IN, BLACK, 3)
    if mouth_open > 0.25:
        # teeth bar
        oval(d, [x0 + 5, y0 + 2, x1 - 5, y0 + 8 + int(6 * mouth_open)], TEETH)
        # inner cavity
        if mouth_open > 0.45:
            oval(d, [x0 + 6, y0 + 10, x1 - 6, y1 - 4], (50, 15, 25))


def draw_ui(d, text, action, title):
    f = font(26)
    t = (title or "Mezi")[:36]
    bb = d.textbbox((0, 0), t, font=f)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([24, 36, 36 + tw + 20, 84], 14, fill=(0, 0, 0))
    d.text((36, 46), t, font=f, fill=WHITE)

    cf = font(24)
    cap = " ".join(text.split())
    words = cap.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=cf)[2] > W - 80:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    lines = lines[:5]
    box_h = 28 + len(lines) * 30
    d.rounded_rectangle([24, H - box_h - 36, W - 24, H - 28], 18, fill=(18, 18, 26))
    y = H - box_h - 20
    for line in lines:
        d.text((40, y), line, font=cf, fill=WHITE)
        y += 30

    af = font(16)
    label = f"MEZI · {action.upper()}"
    d.rounded_rectangle([W - 190, 44, W - 24, 82], 12, fill=HOODIE)
    d.text((W - 178, 52), label, font=af, fill=BLACK)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Mezi")
    p.add_argument("--bg", default="studio")
    p.add_argument("--out", default="output_mezi.mp4")
    p.add_argument("--actions", default="talk,walk,point,laugh")
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")

    dur_s = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        text=True,
    ).strip()
    duration = min(max(float(dur_s), 1.0), 45.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))
    bg_full = make_bg(args.bg)
    print(f"duration={duration:.2f}s frames={n} bg={args.bg} cues={len(cues)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * (2.5 if action == "walk" else 1.2)
            frame = crop_ken_burns(bg_full, t, duration)
            cx = W // 2 + (int(28 * math.sin(t * 1.5)) if action == "walk" else 0)
            cy = int(H * 0.40)
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.75)
            draw_mezi(frame, cx, cy, mouth, phase, action)
            draw_ui(ImageDraw.Draw(frame), args.text, action, args.title)
            frame.save(tmp_path / f"frame_{i:05d}.png")

        out_mp4 = Path(args.out).resolve()
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_mp4),
        ])
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
