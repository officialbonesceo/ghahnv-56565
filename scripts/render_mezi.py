#!/usr/bin/env python3
"""
MEZI-style 2D talking clip:
  - cartoon explorer character (yellow hoodie)
  - Rhubarb mouth cues
  - simple idle bob / optional walk
  - soft room background
  - frames -> mp4 via ffmpeg + TTS audio
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 540
FPS = 24

# Mouth scale factors from Rhubarb value (open amount 0..1)
MOUTH = {
    "X": 0.05,
    "A": 0.95,
    "B": 0.15,
    "C": 0.45,
    "D": 0.55,
    "E": 0.7,
    "F": 0.35,
    "G": 0.8,
    "H": 0.9,
}


def load_cues(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or data.get("mouth_cues") or []


def open_at(cues: list[dict], t: float) -> float:
    if not cues:
        return 0.05 + 0.5 * abs(math.sin(t * 12))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.3)
    return 0.05


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def draw_room(draw: ImageDraw.ImageDraw):
    # soft room: floor + wall + window light
    draw.rectangle([0, 0, W, H], fill=(245, 240, 230))
    draw.rectangle([0, int(H * 0.62), W, H], fill=(210, 200, 185))
    # back wall shadow line
    draw.line([(0, int(H * 0.62)), (W, int(H * 0.62))], fill=(190, 180, 165), width=3)
    # window
    wx0, wy0, wx1, wy1 = 40, 40, 220, 200
    draw.rounded_rectangle([wx0, wy0, wx1, wy1], radius=8, fill=(180, 220, 245), outline=(120, 150, 170), width=3)
    draw.line([(wx0 + wx1) // 2, wy0, (wx0 + wx1) // 2, wy1], fill=(120, 150, 170), width=2)
    draw.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=(120, 150, 170), width=2)
    # shelf
    draw.rectangle([W - 160, 120, W - 40, 128], fill=(150, 120, 90))
    draw.rectangle([W - 150, 90, W - 130, 120], fill=(80, 160, 200))
    draw.rectangle([W - 120, 95, W - 95, 120], fill=(220, 100, 90))


def draw_mezi(draw: ImageDraw.ImageDraw, cx: int, cy: int, mouth_open: float, phase: float, expression: str):
    """Stylized MEZI: yellow hoodie, dark hair, brown skin, big eyes."""
    # shadow
    draw.ellipse([cx - 70, cy + 150, cx + 70, cy + 175], fill=(200, 190, 175))

    # legs
    leg_swing = int(8 * math.sin(phase * 2))
    draw.rounded_rectangle([cx - 35 + leg_swing, cy + 95, cx - 12 + leg_swing, cy + 155], radius=8, fill=(30, 35, 50))
    draw.rounded_rectangle([cx + 12 - leg_swing, cy + 95, cx + 35 - leg_swing, cy + 155], radius=8, fill=(30, 35, 50))
    # shoes
    draw.ellipse([cx - 42 + leg_swing, cy + 148, cx - 5 + leg_swing, cy + 168], fill=(25, 25, 30))
    draw.ellipse([cx + 5 - leg_swing, cy + 148, cx + 42 - leg_swing, cy + 168], fill=(25, 25, 30))

    # torso hoodie
    draw.rounded_rectangle([cx - 55, cy + 10, cx + 55, cy + 110], radius=20, fill=(255, 200, 40))
    # hoodie pocket
    draw.rounded_rectangle([cx - 35, cy + 55, cx + 35, cy + 95], radius=10, fill=(245, 180, 30))
    # logo circle
    draw.ellipse([cx - 14, cy + 28, cx + 14, cy + 56], outline=(40, 40, 50), width=3)
    draw.arc([cx - 10, cy + 32, cx + 10, cy + 52], 40, 320, fill=(40, 40, 50), width=2)

    # arms
    arm_y = int(6 * math.sin(phase * 2 + 0.5))
    if expression == "point":
        # point with right arm up
        draw.line([(cx + 50, cy + 40), (cx + 95, cy - 10)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx + 88, cy - 22, cx + 108, cy - 2], fill=(196, 140, 90))
        draw.line([(cx - 50, cy + 40), (cx - 70, cy + 90 + arm_y)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx - 82, cy + 85 + arm_y, cx - 62, cy + 105 + arm_y], fill=(196, 140, 90))
    else:
        draw.line([(cx - 50, cy + 35), (cx - 75, cy + 85 + arm_y)], fill=(255, 200, 40), width=14)
        draw.line([(cx + 50, cy + 35), (cx + 75, cy + 85 - arm_y)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx - 88, cy + 78 + arm_y, cx - 65, cy + 100 + arm_y], fill=(196, 140, 90))
        draw.ellipse([cx + 65, cy + 78 - arm_y, cx + 88, cy + 100 - arm_y], fill=(196, 140, 90))

    # neck
    draw.rectangle([cx - 12, cy - 5, cx + 12, cy + 18], fill=(196, 140, 90))

    # head
    bob = int(3 * math.sin(phase * 3))
    hy = cy - 70 + bob
    draw.ellipse([cx - 52, hy - 55, cx + 52, hy + 50], fill=(196, 140, 90))

    # hair
    draw.ellipse([cx - 55, hy - 70, cx + 55, hy - 5], fill=(25, 22, 30))
    draw.polygon(
        [(cx - 50, hy - 35), (cx - 65, hy - 55), (cx - 40, hy - 60), (cx - 20, hy - 75),
         (cx, hy - 70), (cx + 25, hy - 78), (cx + 50, hy - 55), (cx + 58, hy - 30)],
        fill=(25, 22, 30),
    )

    # eyes
    eye_y = hy - 10
    if expression == "laugh":
        # happy squint
        draw.arc([cx - 28, eye_y - 8, cx - 8, eye_y + 8], 200, 340, fill=(30, 25, 20), width=3)
        draw.arc([cx + 8, eye_y - 8, cx + 28, eye_y + 8], 200, 340, fill=(30, 25, 20), width=3)
    else:
        draw.ellipse([cx - 28, eye_y - 12, cx - 8, eye_y + 10], fill=(255, 255, 255), outline=(30, 25, 20), width=2)
        draw.ellipse([cx + 8, eye_y - 12, cx + 28, eye_y + 10], fill=(255, 255, 255), outline=(30, 25, 20), width=2)
        draw.ellipse([cx - 22, eye_y - 6, cx - 12, eye_y + 6], fill=(30, 25, 20))
        draw.ellipse([cx + 14, eye_y - 6, cx + 24, eye_y + 6], fill=(30, 25, 20))
        # shine
        draw.ellipse([cx - 20, eye_y - 5, cx - 16, eye_y - 1], fill=(255, 255, 255))
        draw.ellipse([cx + 16, eye_y - 5, cx + 20, eye_y - 1], fill=(255, 255, 255))

    # brows
    draw.arc([cx - 30, eye_y - 22, cx - 6, eye_y - 8], 200, 340, fill=(30, 25, 20), width=3)
    draw.arc([cx + 6, eye_y - 22, cx + 30, eye_y - 8], 200, 340, fill=(30, 25, 20), width=3)

    # mouth from lip sync
    my = hy + 22
    mw = 18 + int(10 * mouth_open)
    mh = 3 + int(22 * mouth_open)
    if expression == "laugh":
        mh = max(mh, 18)
        mw = max(mw, 28)
    x0, y0 = cx - mw, my - mh // 3
    x1, y1 = cx + mw, my + mh
    draw.ellipse([x0, y0, x1, y1], fill=(80, 30, 40), outline=(40, 20, 25), width=2)
    if mouth_open > 0.35:
        # inner mouth
        draw.ellipse([x0 + 4, y0 + 4, x1 - 4, y1 - 2], fill=(40, 15, 25))

    # backpack strap hint
    draw.line([(cx - 48, cy + 20), (cx - 40, cy + 70)], fill=(40, 40, 50), width=4)


def draw_caption(draw: ImageDraw.ImageDraw, text: str):
    t = " ".join(text.split())
    if len(t) > 90:
        t = t[:87] + "..."
    f = font(22)
    bbox = draw.textbbox((0, 0), t, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 14
    x0 = (W - tw) // 2 - pad
    y0 = H - th - 28 - pad
    x1 = (W + tw) // 2 + pad
    y1 = H - 18
    draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=(30, 30, 40, 230))
    draw.text(((W - tw) // 2, H - th - 28 - pad // 2), t, font=f, fill=(255, 255, 255))


def render_frames(
    out_dir: Path,
    duration: float,
    cues: list[dict],
    text: str,
    action: str,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(FPS, int(math.ceil(duration * FPS)))
    for i in range(n):
        t = i / float(FPS)
        phase = t * (2.2 if action == "walk" else 1.0)
        # walk: drift slightly
        cx = W // 2 + (int(40 * math.sin(t * 1.5)) if action == "walk" else 0)
        cy = 220

        img = Image.new("RGB", (W, H), (245, 240, 230))
        draw = ImageDraw.Draw(img)
        draw_room(draw)

        expression = "neutral"
        if action == "laugh":
            expression = "laugh"
        elif action == "point":
            expression = "point"

        mouth = open_at(cues, t)
        if action == "laugh":
            mouth = max(mouth, 0.6)

        draw_mezi(draw, cx, cy, mouth, phase, expression)
        draw_caption(draw, text)

        # badge
        f = font(14)
        draw.rounded_rectangle([W - 130, 16, W - 16, 42], radius=8, fill=(255, 200, 40))
        draw.text((W - 118, 20), "MEZI", font=f, fill=(30, 30, 40))

        img.save(out_dir / f"frame_{i:05d}.png")
    return n


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True, help="speech.mp3 or .wav")
    p.add_argument("--cues", default="", help="Rhubarb mouth.json")
    p.add_argument("--text", required=True)
    p.add_argument("--out", default="output_mezi.mp4")
    p.add_argument("--action", default="talk", choices=["talk", "walk", "point", "laugh"])
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        print("missing audio", file=sys.stderr)
        sys.exit(1)

    # duration
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio),
        ],
        text=True,
    ).strip()
    duration = min(max(float(out), 1.0), 20.0)

    cues = load_cues(Path(args.cues)) if args.cues else []
    print(f"duration={duration:.2f}s cues={len(cues)} action={args.action}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        n = render_frames(tmp_path, duration, cues, args.text, args.action)
        print(f"frames={n}")
        out_mp4 = Path(args.out).resolve()
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"),
            "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(out_mp4),
        ]
        subprocess.check_call(cmd)
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
