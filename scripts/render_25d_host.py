#!/usr/bin/env python3
"""
Full-frame 2.5D Profile-3 cyber host.
Draws a proper portrait (not Blender primitives), animates mouth from Rhubarb cues,
muxes Edge TTS audio. Looks closer to the concept than Workbench spheres.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 960, 540
FPS = 24

# Mouth rect in portrait space (open amount changes height)
MOUTH_CX, MOUTH_CY = 480, 355
MOUTH_W = 90

CUE_OPEN = {
    "X": 0.08,
    "A": 0.95,
    "B": 0.15,
    "C": 0.45,
    "D": 0.65,
    "E": 0.80,
    "F": 0.35,
    "G": 0.75,
    "H": 1.00,
}


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or data.get("mouth_cues") or []


def cue_open_at(cues, t: float) -> float:
    if not cues:
        return 0.15 + 0.25 * abs(math.sin(t * 10))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return CUE_OPEN.get(str(c.get("value", "X")).upper(), 0.2)
    return 0.08


def draw_host(open_amt: float, subtitle: str) -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 12, 22))
    d = ImageDraw.Draw(img)

    # Soft vignette background glow
    for r, col in ((420, (20, 40, 70)), (300, (15, 30, 55)), (180, (10, 20, 40))):
        d.ellipse([W // 2 - r, H // 2 - r + 20, W // 2 + r, H // 2 + r + 20], fill=col)

    # Shoulders / jacket
    d.rounded_rectangle([280, 400, 680, 540], radius=40, fill=(18, 22, 32))
    d.rounded_rectangle([300, 410, 660, 540], radius=30, fill=(12, 16, 26))
    # Cyan collar
    d.rounded_rectangle([340, 400, 620, 425], radius=8, fill=(40, 200, 255))

    # Neck
    d.rectangle([440, 360, 520, 415], fill=(150, 160, 175))

    # Head
    d.ellipse([360, 80, 600, 380], fill=(165, 175, 190))
    # Hair
    d.ellipse([355, 70, 605, 230], fill=(30, 35, 50))
    d.chord([355, 90, 605, 280], 180, 0, fill=(30, 35, 50))

    # Headset band
    d.arc([350, 100, 610, 320], 200, 340, fill=(40, 50, 65), width=14)
    d.ellipse([345, 180, 385, 230], fill=(25, 30, 40))
    d.ellipse([575, 180, 615, 230], fill=(25, 30, 40))
    # Boom
    d.line([(370, 210), (420, 340)], fill=(50, 190, 240), width=5)
    d.ellipse([408, 330, 432, 354], fill=(80, 220, 255))

    # Eyes (cyan glow)
    for cx in (430, 530):
        d.ellipse([cx - 28, 195, cx + 28, 245], fill=(230, 240, 255))
        d.ellipse([cx - 16, 205, cx + 16, 235], fill=(40, 210, 255))
        d.ellipse([cx - 6, 212, cx + 6, 224], fill=(10, 30, 50))

    # Brows
    d.arc([400, 175, 460, 210], 200, 340, fill=(40, 45, 60), width=4)
    d.arc([500, 175, 560, 210], 200, 340, fill=(40, 45, 60), width=4)

    # Nose hint
    d.ellipse([468, 250, 492, 280], fill=(150, 158, 172))

    # Mouth — open amount from Rhubarb
    mh = max(6, int(14 + open_amt * 42))
    mw = MOUTH_W + int(open_amt * 20)
    x0 = MOUTH_CX - mw // 2
    y0 = MOUTH_CY - mh // 2
    x1 = MOUTH_CX + mw // 2
    y1 = MOUTH_CY + mh // 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=min(12, mh // 2), fill=(40, 20, 30))
    if open_amt > 0.35:
        # inner mouth
        d.rounded_rectangle([x0 + 8, y0 + 4, x1 - 8, y1 - 4], radius=6, fill=(90, 30, 50))
    if open_amt < 0.2:
        d.arc([x0, y0 - 4, x1, y1 + 4], 20, 160, fill=(120, 50, 70), width=3)

    # Subtitle bar
    bar = Image.new("RGBA", (W, 56), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    bd.rounded_rectangle([40, 4, W - 40, 52], radius=12, fill=(5, 10, 20, 200))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    label = (subtitle[:70] + "…") if len(subtitle) > 70 else subtitle
    bd.text((60, 16), label, fill=(180, 230, 255, 255), font=font)
    img = Image.alpha_composite(img.convert("RGBA"), bar).convert("RGB")

    # Slight soft focus edge
    return img.filter(ImageFilter.SMOOTH)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
    ).strip()
    return max(1.0, min(float(out), 12.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cues", default="")
    ap.add_argument("--text", default="Talking Clip Factory")
    ap.add_argument("--out", default="output_25d.mp4")
    args = ap.parse_args()

    audio = Path(args.audio)
    cues = load_cues(Path(args.cues) if args.cues else None)
    dur = probe_duration(audio)
    nframes = max(FPS, int(round(dur * FPS)))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(nframes):
            t = i / FPS
            open_amt = cue_open_at(cues, t)
            frame = draw_host(open_amt, args.text)
            frame.save(tmp_path / f"frame_{i:05d}.png")

        # ffmpeg image sequence + audio
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"),
            "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(args.out),
        ]
        subprocess.check_call(cmd)

    print("OK", args.out)


if __name__ == "__main__":
    main()
