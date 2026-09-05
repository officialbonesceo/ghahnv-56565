#!/usr/bin/env python3
"""Mike jointed figure: board -> walk side -> world point -> present; blink + expressions."""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
ACCENT = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)
GLOW = (255, 230, 100)
MOUTH = {
    "X": 0.0, "B": 0.0, "A": 1.0, "C": 0.55,
    "D": 0.7, "E": 0.85, "F": 0.45, "G": 0.95, "H": 1.0,
}


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "mezi"


def load_rgba(name: str) -> Image.Image:
    p = asset_dir() / name
    if not p.exists():
        # fallback
        alt = asset_dir() / "body.png"
        return Image.open(alt if alt.exists() else p).convert("RGBA")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.0 if math.sin(t * 16) < 0.2 else 0.55 + 0.35 * abs(math.sin(t * 16))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.5)
    return 0.0


def mouth_name(open_amt: float, pose: str) -> str:
    if pose == "present" and open_amt < 0.3:
        return "mouth_smile.png"
    if open_amt >= 0.75:
        return "mouth_wide.png"
    if open_amt >= 0.2:
        return "mouth_open.png"
    return "mouth_closed.png"


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def topic_world(topic: str) -> str:
    t = (topic or "").lower()
    if re.search(r"star|sun|moon|planet|space|galaxy|black hole|solar|telescope|comet", t):
        return "space"
    if re.search(r"ocean|tide|water|rain|cloud|storm|lightning|rainbow", t):
        return "sky"
    if re.search(r"tree|plant|photo|leaf|forest|oxygen|carbon", t):
        return "nature"
    if re.search(r"atom|molecule|chem|battery|electric|circuit|magnet", t):
        return "lab"
    return "classroom"


def draw_classroom(topic: str) -> Image.Image:
    img = Image.new("RGB", (W, H), (236, 228, 210))
    d = ImageDraw.Draw(img)
    # richer classroom
    d.rectangle([0, 0, W, int(H * 0.68)], fill=(245, 238, 220))
    d.rectangle([0, int(H * 0.68), W, H], fill=(150, 120, 85))
    # windows
    for i in range(2):
        x0 = 60 + i * 200
        d.rectangle([x0, 40, x0 + 140, 180], fill=(180, 210, 235), outline=(120, 100, 70), width=4)
    # big board
    bx0, by0, bx1, by1 = 40, 200, W - 40, int(H * 0.42)
    d.rounded_rectangle([bx0 - 12, by0 - 12, bx1 + 12, by1 + 12], 14, fill=(90, 70, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 10, fill=(32, 82, 52))
    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(64)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 48) and tf.size > 32:
        tf = font(tf.size - 4)
    words = topic.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 48):
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = by0 + 50
    for line in lines[:3]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(245, 250, 240))
        y += tf.size + 14
    d.rectangle([bx0, by1 + 4, bx1, by1 + 18], fill=(120, 95, 60))
    # desk hint
    d.rectangle([W // 2 - 180, int(H * 0.62), W // 2 + 180, int(H * 0.66)], fill=(120, 90, 55))
    return img


def draw_space() -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 10, 28))
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    for _ in range(160):
        x, y = rng.randint(0, W - 1), rng.randint(0, int(H * 0.75))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    sx, sy = int(W * 0.72), int(H * 0.22)
    d.ellipse([sx - 32, sy - 32, sx + 32, sy + 32], fill=(255, 250, 200))
    d.rectangle([0, int(H * 0.78), W, H], fill=(12, 14, 32))
    return img


def draw_sky() -> Image.Image:
    img = Image.new("RGB", (W, H), (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([int(W * 0.7), int(H * 0.08), int(W * 0.9), int(H * 0.2)], fill=(255, 230, 120))
    d.rectangle([0, int(H * 0.72), W, H], fill=(90, 160, 90))
    return img


def draw_nature() -> Image.Image:
    img = Image.new("RGB", (W, H), (160, 210, 160))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.55)], fill=(140, 200, 240))
    d.rectangle([0, int(H * 0.55), W, H], fill=(70, 130, 70))
    return img


def draw_lab() -> Image.Image:
    img = Image.new("RGB", (W, H), (220, 225, 230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H * 0.7), W, H], fill=(90, 95, 105))
    sx, sy = int(W * 0.75), int(H * 0.28)
    d.ellipse([sx - 40, sy - 40, sx + 40, sy + 40], fill=(120, 220, 255))
    return img


def make_bg(kind: str, topic: str) -> Image.Image:
    return {
        "space": draw_space,
        "sky": draw_sky,
        "nature": draw_nature,
        "lab": draw_lab,
    }.get(kind, lambda: draw_classroom(topic))()


def beat(t: float, duration: float) -> str:
    p = t / max(duration, 0.1)
    if p < 0.12:
        return "welcome"
    if p < 0.22:
        return "board_talk"
    if p < 0.34:
        return "walk_left"
    if p < 0.55:
        return "world_point"
    if p < 0.68:
        return "question"
    if p < 0.82:
        return "sit"
    return "present"


def body_for(pose: str, blink: bool) -> str:
    if blink and pose in ("board_talk", "welcome", "question"):
        return "body_blink.png"
    return {
        "welcome": "body_present.png",
        "board_talk": "body.png",
        "walk_left": "body_side_left.png",
        "world_point": "arm_point.png",
        "question": "body_question.png",
        "sit": "body_sit.png",
        "present": "body_happy.png",
    }.get(pose, "body.png")


def composite_host(pose: str, mouth_open: float, blink: bool) -> Image.Image:
    body = load_rgba(body_for(pose, blink))
    # mouth only for front-ish poses
    if pose in ("walk_left",):
        return body
    mouth = load_rgba(mouth_name(mouth_open, pose))
    return Image.alpha_composite(body, mouth)


def word_windows(text: str, duration: float):
    words = [w for w in text.replace("\n", " ").split() if w]
    if not words:
        return [(0, duration, ["..."], 0)]
    n = len(words)
    slot = duration / max(n, 1)
    windows, i = [], 0
    while i < n:
        chunk = words[i : i + 5]
        start = i * slot
        end = min(duration, (i + len(chunk)) * slot)
        for j in range(len(chunk)):
            ws = start + j * (end - start) / len(chunk)
            we = start + (j + 1) * (end - start) / len(chunk)
            windows.append((ws, we, chunk, j))
        i += len(chunk)
    return windows


def active_caption(windows, t):
    for ws, we, chunk, j in windows:
        if ws <= t < we:
            return chunk, j
    if windows:
        return windows[-1][2], windows[-1][3]
    return [""], 0


def draw_karaoke(rgb, text, t, duration, pose):
    d = ImageDraw.Draw(rgb)
    af = font(22)
    label = f"MIKE · {pose.replace('_', ' ').upper()[:14]}"
    d.rounded_rectangle([W - 320, 28, W - 24, 78], 14, fill=ACCENT)
    d.text((W - 305, 40), label, font=af, fill=BLACK)
    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(44)
    max_w = W - 64
    gaps, display, total = [], [], 0
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        if total + ww + 14 > max_w and display:
            break
        display.append(w)
        gaps.append(ww)
        total += ww + 14
    if not display:
        display, gaps, total = ["..."], [40], 40
    active = min(active, len(display) - 1)
    total = max(total - 14, 1)
    x0 = max(32, (W - total) // 2)
    y = H - 180
    d.rounded_rectangle([24, y - 20, W - 24, y + 78], 20, fill=(12, 12, 20))
    x = x0
    for i, w in enumerate(display):
        if i == active:
            for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                d.text((x + ox, y + oy), w, font=cf, fill=GLOW)
            d.text((x, y), w, font=cf, fill=WHITE)
        else:
            d.text((x, y), w, font=cf, fill=(175, 175, 185))
        x += gaps[i] + 14


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Lesson")
    p.add_argument("--bg", default="classroom")
    p.add_argument("--bg-image", default="")
    p.add_argument("--out", default="output.mp4")
    p.add_argument("--actions", default="")
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")

    dur_s = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        text=True,
    ).strip()
    duration = min(max(float(dur_s), 1.0), 90.0)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic

    world = topic_world(topic)
    bg_board = draw_classroom(topic)
    bg_world = make_bg(world, topic)
    print(f"jointed Mike board->{world} duration={duration:.2f}s frames={n}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            pose = beat(t, duration)
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 7 == 0)  # occasional blink

            if pose == "walk_left":
                walk_p = (pfrac - 0.22) / 0.12
                walk_p = max(0.0, min(1.0, walk_p))
                base = Image.blend(bg_board, bg_world, walk_p)
            elif pose in ("world_point", "question", "sit", "present"):
                base = bg_world.copy()
            else:
                base = bg_board.copy()

            frame = base.convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(pose, mouth, blink)
            target_h = int(H * 0.48)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(4 * math.sin(t * 8))
            if pose == "walk_left":
                walk_p = max(0.0, min(1.0, (pfrac - 0.22) / 0.12))
                x = int((W - nw) // 2 - walk_p * (W * 0.38))
                bob = int(10 * abs(math.sin(walk_p * math.pi * 5)))
            elif pose == "world_point":
                x = int(W * 0.26)
            elif pose == "sit":
                x = (W - nw) // 2
                bob = 0
            else:
                x = (W - nw) // 2

            y = H - nh - 200 + bob
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_karaoke(rgb, args.text, t, duration, pose)
            rgb.save(tmp_path / f"frame_{i:05d}.png")

        out_mp4 = Path(args.out).resolve()
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4),
        ])
        sz = out_mp4.stat().st_size
        if sz < 50_000:
            raise SystemExit(f"output too small: {sz}")
        print("OK", out_mp4, sz)


if __name__ == "__main__":
    main()
