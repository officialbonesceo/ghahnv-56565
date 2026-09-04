#!/usr/bin/env python3
"""MEZI TikTok frame: topic backgrounds + Ken Burns camera + actions."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# TikTok-ish vertical
W, H = 720, 1280
FPS = 12

HOODIE = (255, 196, 40)
HOODIE_D = (235, 170, 25)
HOODIE_S = (255, 215, 90)
SKIN = (210, 155, 115)
SKIN_D = (185, 130, 95)
HAIR = (28, 24, 30)
PANTS = (32, 36, 48)
SHOE = (22, 22, 28)
MOUTH_IN = (90, 35, 45)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)

MOUTH = {
    "X": 0.08, "A": 0.95, "B": 0.12, "C": 0.42,
    "D": 0.55, "E": 0.72, "F": 0.32, "G": 0.82, "H": 0.9,
}
ALL_ACTIONS = ["talk", "walk", "point", "laugh"]


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.08 + 0.5 * abs(math.sin(t * 11))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.3)
    return 0.08


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
    """Full-frame background larger than W×H for Ken Burns crop."""
    bw, bh = int(W * 1.15), int(H * 1.15)
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    k = (kind or "studio").lower().strip()

    if k == "space":
        d.rectangle([0, 0, bw, bh], fill=(8, 10, 28))
        for i in range(120):
            x = (i * 97) % bw
            y = (i * 53) % bh
            r = 1 + (i % 3)
            d.ellipse([x, y, x + r, y + r], fill=(220, 230, 255))
        d.ellipse([bw - 200, 80, bw - 40, 240], fill=(40, 60, 120))
        d.ellipse([bw - 180, 100, bw - 60, 220], fill=(20, 30, 70))
    elif k == "ocean":
        d.rectangle([0, 0, bw, int(bh * 0.45)], fill=(135, 200, 245))
        d.rectangle([0, int(bh * 0.45), bw, bh], fill=(20, 90, 140))
        for i in range(8):
            y = int(bh * 0.45) + i * 30
            d.arc([20, y, bw - 20, y + 40], 0, 180, fill=(40, 130, 180), width=3)
    elif k == "money":
        d.rectangle([0, 0, bw, bh], fill=(230, 245, 230))
        d.rectangle([0, int(bh * 0.7), bw, bh], fill=(40, 120, 70))
        for i in range(6):
            x = 40 + i * 120
            d.ellipse([x, 200, x + 70, 270], outline=(20, 100, 50), width=4)
            d.text((x + 22, 225), "$", fill=(20, 100, 50))
    elif k == "tech":
        d.rectangle([0, 0, bw, bh], fill=(15, 22, 40))
        d.rectangle([0, int(bh * 0.75), bw, bh], fill=(25, 35, 55))
        for i in range(10):
            x = 30 + i * 80
            d.rectangle([x, 100, x + 50, 160], outline=(80, 200, 230), width=2)
            d.line([x + 25, 160, x + 25, 200], fill=(80, 200, 230), width=2)
    elif k == "science":
        d.rectangle([0, 0, bw, bh], fill=(230, 245, 255))
        d.rectangle([0, int(bh * 0.7), bw, bh], fill=(180, 220, 180))
        d.ellipse([bw - 220, 60, bw - 40, 240], fill=(255, 220, 80))
        for i in range(5):
            d.line([80, 120 + i * 25, 200, 100 + i * 30], fill=(100, 160, 200), width=2)
    else:  # studio
        d.rectangle([0, 0, bw, int(bh * 0.62)], fill=(245, 240, 230))
        d.rectangle([0, int(bh * 0.62), bw, bh], fill=(210, 200, 185))
        d.rounded_rectangle([50, 60, 260, 260], 16, fill=(175, 215, 240), outline=(110, 145, 170), width=4)

    return img


def crop_ken_burns(bg: Image.Image, t: float, duration: float) -> Image.Image:
    """Slow zoom + pan over the clip."""
    progress = min(1.0, t / max(duration, 0.1))
    scale = 1.0 + 0.08 * progress
    bw, bh = bg.size
    cw, ch = int(W * scale), int(H * scale)
    cw = min(cw, bw)
    ch = min(ch, bh)
    max_x = max(0, bw - cw)
    max_y = max(0, bh - ch)
    x = int(max_x * progress * 0.7)
    y = int(max_y * (1 - progress) * 0.4)
    frame = bg.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.BILINEAR)
    return frame


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_mezi(img, cx, cy, mouth_open, phase, action):
    d = ImageDraw.Draw(img)
    walk = action == "walk"
    swing = int(12 * math.sin(phase * 2.2)) if walk else 0
    bob = int(4 * math.sin(phase * 3))

    oval(d, [cx - 78, cy + 168, cx + 78, cy + 198], (0, 0, 0, ))  # will use dark
    oval(d, [cx - 78, cy + 168, cx + 78, cy + 198], (30, 30, 40))

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

    my = hy + 28
    mw = 16 + int(14 * mouth_open)
    mh = 4 + int(26 * mouth_open)
    if action == "laugh":
        mw, mh = max(mw, 32), max(mh, 22)
    oval(d, [cx - mw, my - mh // 4, cx + mw, my + mh], MOUTH_IN, BLACK, 2)


def draw_ui(d, text, action, title):
    f = font(28)
    # title pill top
    t = (title or "Mezi")[:40]
    bb = d.textbbox((0, 0), t, font=f)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([24, 40, 24 + tw + 28, 88], 16, fill=(0, 0, 0))
    d.text((38, 50), t, font=f, fill=WHITE)

    # caption bottom
    cap = " ".join(text.split())
    if len(cap) > 90:
        cap = cap[:87] + "..."
    cf = font(26)
    cb = d.textbbox((0, 0), cap, font=cf)
    cw, ch = cb[2] - cb[0], cb[3] - cb[1]
    # wrap naive
    d.rounded_rectangle([30, H - 200, W - 30, H - 40], 20, fill=(20, 20, 28))
    # simple wrap
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
    y = H - 180
    for line in lines[:4]:
        d.text((50, y), line, font=cf, fill=WHITE)
        y += 32

    af = font(18)
    label = f"MEZI · {action.upper()}"
    d.rounded_rectangle([W - 200, 48, W - 24, 88], 12, fill=HOODIE)
    d.text((W - 188, 56), label, font=af, fill=BLACK)


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
    print(f"duration={duration:.2f}s frames={n} bg={args.bg} actions={actions}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * (2.5 if action == "walk" else 1.2)
            frame = crop_ken_burns(bg_full, t, duration)
            cx = W // 2 + (int(30 * math.sin(t * 1.5)) if action == "walk" else 0)
            cy = int(H * 0.42)
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.7)
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
