#!/usr/bin/env python3
"""
MEZI 2D explainer — procedural cartoon closer to the yellow-hoodie sheet.
Still not hand-illustrated sprites; proportions aimed at the MEZI design.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 960, 540
FPS = 12

# MEZI sheet palette
HOODIE = (255, 196, 40)
HOODIE_D = (235, 170, 25)
HOODIE_S = (255, 215, 90)
SKIN = (210, 155, 115)
SKIN_D = (185, 130, 95)
SKIN_L = (230, 185, 150)
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


def draw_room(img: Image.Image):
    d = ImageDraw.Draw(img)
    # warm gradient-ish wall
    for y in range(0, int(H * 0.64)):
        c = 248 - y // 25
        d.line([(0, y), (W, y)], fill=(c, c - 4, c - 12))
    d.rectangle([0, int(H * 0.64), W, H], fill=(205, 195, 178))
    d.line([(0, int(H * 0.64)), (W, int(H * 0.64))], fill=(175, 165, 150), width=2)
    # window with light
    d.rounded_rectangle([36, 36, 210, 195], 14, fill=(170, 215, 245), outline=(110, 145, 170), width=4)
    d.line([123, 36, 123, 195], fill=(110, 145, 170), width=3)
    d.line([36, 115, 210, 115], fill=(110, 145, 170), width=3)
    # soft light pool
    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.ellipse([20, 20, 260, 240], fill=(255, 250, 220, 40))
    img.paste(Image.alpha_composite(img.convert("RGBA"), light).convert("RGB"))
    d = ImageDraw.Draw(img)
    # shelf + books
    d.rectangle([W - 170, 125, W - 36, 134], fill=(140, 110, 80))
    d.rounded_rectangle([W - 160, 88, W - 138, 125], 4, fill=(70, 150, 210))
    d.rounded_rectangle([W - 132, 95, W - 108, 125], 4, fill=(230, 95, 85))
    d.rounded_rectangle([W - 102, 92, W - 80, 125], 4, fill=(90, 180, 120))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_mezi(img: Image.Image, cx: int, cy: int, mouth_open: float, phase: float, action: str):
    """Bigger head, softer shapes — sheet-like cartoon, not box robot."""
    d = ImageDraw.Draw(img)
    walk = action == "walk"
    swing = int(12 * math.sin(phase * 2.2)) if walk else 0
    bob = int(4 * math.sin(phase * 3))

    # ground shadow
    oval(d, [cx - 78, cy + 168, cx + 78, cy + 198], (190, 180, 165))

    # --- legs (shorter, cartoony) ---
    ly = cy + 100
    d.rounded_rectangle([cx - 38 + swing, ly, cx - 10 + swing, cy + 170], 12, fill=PANTS)
    d.rounded_rectangle([cx + 10 - swing, ly, cx + 38 - swing, cy + 170], 12, fill=PANTS)
    oval(d, [cx - 48 + swing, cy + 158, cx - 2 + swing, cy + 182], SHOE)
    oval(d, [cx + 2 - swing, cy + 158, cx + 48 - swing, cy + 182], SHOE)

    # --- torso hoodie (rounded, not a box) ---
    # main body
    d.rounded_rectangle([cx - 62, cy + 8, cx + 62, cy + 118], 28, fill=HOODIE)
    # belly highlight
    d.rounded_rectangle([cx - 40, cy + 30, cx + 40, cy + 100], 22, fill=HOODIE_S)
    d.rounded_rectangle([cx - 36, cy + 58, cx + 36, cy + 100], 16, fill=HOODIE_D)
    # kangaroo pocket
    d.rounded_rectangle([cx - 34, cy + 62, cx + 34, cy + 98], 14, fill=HOODIE)
    d.arc([cx - 34, cy + 70, cx + 34, cy + 98], 200, 340, fill=HOODIE_D, width=3)
    # chest logo (MEZI-like mark)
    oval(d, [cx - 16, cy + 28, cx + 16, cy + 60], None, BLACK, 3)
    d.arc([cx - 11, cy + 33, cx + 11, cy + 55], 40, 300, fill=BLACK, width=3)

    # backpack straps
    d.line([(cx - 50, cy + 18), (cx - 42, cy + 85)], fill=(45, 45, 55), width=5)
    d.line([(cx + 50, cy + 18), (cx + 42, cy + 85)], fill=(45, 45, 55), width=5)

    # --- arms ---
    if action == "point":
        d.line([(cx + 55, cy + 40), (cx + 105, cy - 25)], fill=HOODIE, width=18)
        oval(d, [cx + 95, cy - 40, cx + 122, cy - 14], SKIN)
        # pointing finger
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

    # neck
    d.rectangle([cx - 14, cy - 8, cx + 14, cy + 20], fill=SKIN)

    # --- HEAD (large, sheet-like) ---
    hy = cy - 78 + bob
    # hair back
    oval(d, [cx - 72, hy - 78, cx + 72, hy + 20], HAIR)
    # face
    oval(d, [cx - 64, hy - 58, cx + 64, hy + 58], SKIN)
    # hair tufts / fringe over forehead
    oval(d, [cx - 70, hy - 85, cx + 70, hy - 15], HAIR)
    # face cutout so eyes show
    oval(d, [cx - 58, hy - 35, cx + 58, hy + 55], SKIN)
    # messy top spikes
    for ox, oy, r in [(-42, -88, 22), (-12, -98, 24), (18, -100, 26), (48, -90, 22), (62, -70, 18)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    # sideburns / sides
    oval(d, [cx - 72, hy - 30, cx - 52, hy + 25], HAIR)
    oval(d, [cx + 52, hy - 30, cx + 72, hy + 25], HAIR)
    # ears
    oval(d, [cx - 78, hy - 8, cx - 58, hy + 22], SKIN, SKIN_D, 1)
    oval(d, [cx + 58, hy - 8, cx + 78, hy + 22], SKIN, SKIN_D, 1)

    # blush
    blush = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    bd.ellipse([cx - 58, hy + 12, cx - 32, hy + 32], fill=(255, 140, 130, 70))
    bd.ellipse([cx + 32, hy + 12, cx + 58, hy + 32], fill=(255, 140, 130, 70))
    img.paste(Image.alpha_composite(img.convert("RGBA"), blush).convert("RGB"))
    d = ImageDraw.Draw(img)

    # eyes — big cartoon
    ey = hy - 8
    if action == "laugh":
        d.arc([cx - 36, ey - 6, cx - 8, ey + 14], 200, 340, fill=BLACK, width=4)
        d.arc([cx + 8, ey - 6, cx + 36, ey + 14], 200, 340, fill=BLACK, width=4)
    else:
        oval(d, [cx - 38, ey - 18, cx - 6, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx + 6, ey - 18, cx + 38, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx - 30, ey - 8, cx - 14, ey + 10], BLACK)
        oval(d, [cx + 14, ey - 8, cx + 30, ey + 10], BLACK)
        oval(d, [cx - 28, ey - 6, cx - 20, ey + 2], WHITE)
        oval(d, [cx + 16, ey - 6, cx + 24, ey + 2], WHITE)

    # brows
    d.arc([cx - 40, ey - 32, cx - 6, ey - 10], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 6, ey - 32, cx + 40, ey - 10], 200, 340, fill=BLACK, width=4)

    # nose hint
    d.arc([cx - 6, hy + 8, cx + 6, hy + 20], 20, 160, fill=SKIN_D, width=2)

    # mouth — lip sync
    my = hy + 28
    mw = 16 + int(14 * mouth_open)
    mh = 4 + int(26 * mouth_open)
    if action == "laugh":
        mw = max(mw, 32)
        mh = max(mh, 22)
    oval(d, [cx - mw, my - mh // 4, cx + mw, my + mh], MOUTH_IN, BLACK, 2)
    if mouth_open > 0.3:
        # tongue / depth
        oval(d, [cx - mw + 6, my + 2, cx + mw - 6, my + mh - 2], (160, 70, 80))
        # upper teeth line
        if mouth_open > 0.45:
            d.arc([cx - mw + 4, my - 2, cx + mw - 4, my + 12], 200, 340, fill=WHITE, width=3)


def draw_ui(d, text: str, action: str):
    t = " ".join(text.split())
    if len(t) > 78:
        t = t[:75] + "..."
    f = font(20)
    bbox = d.textbbox((0, 0), t, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 14
    d.rounded_rectangle(
        [(W - tw) // 2 - pad, H - th - 40, (W + tw) // 2 + pad, H - 14],
        14, fill=(28, 28, 36),
    )
    d.text(((W - tw) // 2, H - th - 32), t, font=f, fill=WHITE)
    af = font(13)
    label = f"MEZI · {action.upper()}"
    ab = d.textbbox((0, 0), label, font=af)
    aw = ab[2] - ab[0]
    d.rounded_rectangle([W - aw - 40, 14, W - 14, 40], 10, fill=HOODIE)
    d.text((W - aw - 30, 18), label, font=af, fill=BLACK)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
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
    duration = min(max(float(dur_s), 1.0), 24.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))
    print(f"duration={duration:.2f}s frames={n} actions={actions} cues={len(cues)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * (2.5 if action == "walk" else 1.2)
            cx = W // 2 + (int(40 * math.sin(t * 1.5)) if action == "walk" else 0)
            cy = 215
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.7)

            img = Image.new("RGB", (W, H), (248, 244, 236))
            draw_room(img)
            draw_mezi(img, cx, cy, mouth, phase, action)
            draw_ui(ImageDraw.Draw(img), args.text, action)
            img.save(tmp_path / f"frame_{i:05d}.png")

        out_mp4 = Path(args.out).resolve()
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_mp4),
        ])
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
