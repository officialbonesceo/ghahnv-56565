#!/usr/bin/env python3
"""
MEZI 2D: one video with full action timeline (talk, walk, point, laugh).
Rhubarb mouth cues + Edge TTS audio.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 540
FPS = 12

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

ALL_ACTIONS = ["talk", "walk", "point", "laugh"]


def load_cues(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or data.get("mouth_cues") or []


def open_at(cues: list[dict], t: float) -> float:
    if not cues:
        return 0.05 + 0.45 * abs(math.sin(t * 12))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.3)
    return 0.05


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def action_at(t: float, duration: float, actions: list[str]) -> str:
    if not actions:
        actions = list(ALL_ACTIONS)
    seg = duration / len(actions)
    idx = min(int(t / seg), len(actions) - 1)
    return actions[idx]


def draw_room(draw: ImageDraw.ImageDraw):
    draw.rectangle([0, 0, W, H], fill=(245, 240, 230))
    draw.rectangle([0, int(H * 0.62), W, H], fill=(210, 200, 185))
    draw.line([(0, int(H * 0.62)), (W, int(H * 0.62))], fill=(190, 180, 165), width=3)
    wx0, wy0, wx1, wy1 = 40, 40, 220, 200
    draw.rounded_rectangle([wx0, wy0, wx1, wy1], radius=8, fill=(180, 220, 245), outline=(120, 150, 170), width=3)
    draw.line([(wx0 + wx1) // 2, wy0, (wx0 + wx1) // 2, wy1], fill=(120, 150, 170), width=2)
    draw.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=(120, 150, 170), width=2)
    draw.rectangle([W - 160, 120, W - 40, 128], fill=(150, 120, 90))
    draw.rectangle([W - 150, 90, W - 130, 120], fill=(80, 160, 200))
    draw.rectangle([W - 120, 95, W - 95, 120], fill=(220, 100, 90))


def draw_mezi(draw, cx, cy, mouth_open, phase, action):
    draw.ellipse([cx - 70, cy + 150, cx + 70, cy + 175], fill=(200, 190, 175))

    leg_swing = int(10 * math.sin(phase * 2)) if action == "walk" else 0
    draw.rounded_rectangle([cx - 35 + leg_swing, cy + 95, cx - 12 + leg_swing, cy + 155], radius=8, fill=(30, 35, 50))
    draw.rounded_rectangle([cx + 12 - leg_swing, cy + 95, cx + 35 - leg_swing, cy + 155], radius=8, fill=(30, 35, 50))
    draw.ellipse([cx - 42 + leg_swing, cy + 148, cx - 5 + leg_swing, cy + 168], fill=(25, 25, 30))
    draw.ellipse([cx + 5 - leg_swing, cy + 148, cx + 42 - leg_swing, cy + 168], fill=(25, 25, 30))

    draw.rounded_rectangle([cx - 55, cy + 10, cx + 55, cy + 110], radius=20, fill=(255, 200, 40))
    draw.rounded_rectangle([cx - 35, cy + 55, cx + 35, cy + 95], radius=10, fill=(245, 180, 30))
    draw.ellipse([cx - 14, cy + 28, cx + 14, cy + 56], outline=(40, 40, 50), width=3)

    arm_y = int(6 * math.sin(phase * 2 + 0.5))
    if action == "point":
        draw.line([(cx + 50, cy + 40), (cx + 95, cy - 10)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx + 88, cy - 22, cx + 108, cy - 2], fill=(196, 140, 90))
        draw.line([(cx - 50, cy + 40), (cx - 70, cy + 90 + arm_y)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx - 82, cy + 85 + arm_y, cx - 62, cy + 105 + arm_y], fill=(196, 140, 90))
    elif action == "laugh":
        draw.line([(cx - 50, cy + 40), (cx - 95, cy + 20)], fill=(255, 200, 40), width=14)
        draw.line([(cx + 50, cy + 40), (cx + 95, cy + 20)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx - 108, cy + 8, cx - 85, cy + 30], fill=(196, 140, 90))
        draw.ellipse([cx + 85, cy + 8, cx + 108, cy + 30], fill=(196, 140, 90))
    else:
        draw.line([(cx - 50, cy + 35), (cx - 75, cy + 85 + arm_y)], fill=(255, 200, 40), width=14)
        draw.line([(cx + 50, cy + 35), (cx + 75, cy + 85 - arm_y)], fill=(255, 200, 40), width=14)
        draw.ellipse([cx - 88, cy + 78 + arm_y, cx - 65, cy + 100 + arm_y], fill=(196, 140, 90))
        draw.ellipse([cx + 65, cy + 78 - arm_y, cx + 88, cy + 100 - arm_y], fill=(196, 140, 90))

    draw.rectangle([cx - 12, cy - 5, cx + 12, cy + 18], fill=(196, 140, 90))
    bob = int(3 * math.sin(phase * 3))
    hy = cy - 70 + bob
    draw.ellipse([cx - 52, hy - 55, cx + 52, hy + 50], fill=(196, 140, 90))
    draw.ellipse([cx - 55, hy - 70, cx + 55, hy - 5], fill=(25, 22, 30))
    draw.polygon(
        [
            (cx - 50, hy - 35),
            (cx - 65, hy - 55),
            (cx - 40, hy - 60),
            (cx - 20, hy - 75),
            (cx, hy - 70),
            (cx + 25, hy - 78),
            (cx + 50, hy - 55),
            (cx + 58, hy - 30),
        ],
        fill=(25, 22, 30),
    )

    eye_y = hy - 10
    if action == "laugh":
        draw.arc([cx - 28, eye_y - 8, cx - 8, eye_y + 8], 200, 340, fill=(30, 25, 20), width=3)
        draw.arc([cx + 8, eye_y - 8, cx + 28, eye_y + 8], 200, 340, fill=(30, 25, 20), width=3)
    else:
        draw.ellipse([cx - 28, eye_y - 12, cx - 8, eye_y + 10], fill=(255, 255, 255), outline=(30, 25, 20), width=2)
        draw.ellipse([cx + 8, eye_y - 12, cx + 28, eye_y + 10], fill=(255, 255, 255), outline=(30, 25, 20), width=2)
        draw.ellipse([cx - 22, eye_y - 6, cx - 12, eye_y + 6], fill=(30, 25, 20))
        draw.ellipse([cx + 14, eye_y - 6, cx + 24, eye_y + 6], fill=(30, 25, 20))
        draw.ellipse([cx - 20, eye_y - 5, cx - 16, eye_y - 1], fill=(255, 255, 255))
        draw.ellipse([cx + 16, eye_y - 5, cx + 20, eye_y - 1], fill=(255, 255, 255))

    draw.arc([cx - 30, eye_y - 22, cx - 6, eye_y - 8], 200, 340, fill=(30, 25, 20), width=3)
    draw.arc([cx + 6, eye_y - 22, cx + 30, eye_y - 8], 200, 340, fill=(30, 25, 20), width=3)

    my = hy + 22
    mw = 18 + int(10 * mouth_open)
    mh = 3 + int(22 * mouth_open)
    if action == "laugh":
        mh = max(mh, 18)
        mw = max(mw, 28)
    draw.ellipse([cx - mw, my - mh // 3, cx + mw, my + mh], fill=(80, 30, 40), outline=(40, 20, 25), width=2)
    if mouth_open > 0.35:
        draw.ellipse([cx - mw + 4, my - mh // 3 + 4, cx + mw - 4, my + mh - 2], fill=(40, 15, 25))

    draw.line([(cx - 48, cy + 20), (cx - 40, cy + 70)], fill=(40, 40, 50), width=4)


def draw_caption(draw, text: str, action: str):
    t = " ".join(text.split())
    if len(t) > 80:
        t = t[:77] + "..."
    f = font(20)
    bbox = draw.textbbox((0, 0), t, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 12
    draw.rounded_rectangle(
        [(W - tw) // 2 - pad, H - th - 36 - pad, (W + tw) // 2 + pad, H - 16],
        radius=12,
        fill=(30, 30, 40),
    )
    draw.text(((W - tw) // 2, H - th - 32), t, font=f, fill=(255, 255, 255))
    # action badge
    af = font(14)
    label = f"MEZI · {action.upper()}"
    ab = draw.textbbox((0, 0), label, font=af)
    aw = ab[2] - ab[0]
    draw.rounded_rectangle([W - aw - 36, 14, W - 14, 40], radius=8, fill=(255, 200, 40))
    draw.text((W - aw - 28, 18), label, font=af, fill=(30, 30, 40))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--out", default="output_mezi.mp4")
    p.add_argument(
        "--actions",
        default="talk,walk,point,laugh",
        help="Comma list played in order over the full clip",
    )
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")

    dur_s = subprocess.check_output(
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
            phase = t * (2.4 if action == "walk" else 1.2)
            cx = W // 2 + (int(36 * math.sin(t * 1.6)) if action == "walk" else 0)
            cy = 220
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.65)

            img = Image.new("RGB", (W, H), (245, 240, 230))
            draw = ImageDraw.Draw(img)
            draw_room(draw)
            draw_mezi(draw, cx, cy, mouth, phase, action)
            draw_caption(draw, args.text, action)
            img.save(tmp_path / f"frame_{i:05d}.png")

        out_mp4 = Path(args.out).resolve()
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
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
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                str(out_mp4),
            ]
        )
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
