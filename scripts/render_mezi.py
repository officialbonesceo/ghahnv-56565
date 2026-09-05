#!/usr/bin/env python3
"""Classroom + big board + MEZI + karaoke captions (5-6 words, clipped)."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
FPS = 12
HOODIE = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)
GLOW = (255, 230, 100)
MOUTH = {
    "X": 0.0, "B": 0.0, "A": 1.0, "C": 0.55,
    "D": 0.7, "E": 0.85, "F": 0.45, "G": 0.95, "H": 1.0,
}
ALL_ACTIONS = ["talk", "walk", "point", "laugh"]


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "mezi"


def load_rgba(name: str) -> Image.Image:
    p = asset_dir() / name
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.0 if math.sin(t * 16) < 0.2 else 0.55 + 0.35 * abs(math.sin(t * 16))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.5)
    return 0.0


def mouth_sprite(open_amt: float) -> str:
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


def action_at(t, duration, actions):
    seg = duration / max(1, len(actions))
    return actions[min(int(t / seg), len(actions) - 1)]


def draw_classroom(topic: str) -> Image.Image:
    """Full-frame classroom with a very large chalkboard."""
    img = Image.new("RGB", (W, H), (245, 236, 220))
    d = ImageDraw.Draw(img)
    # walls
    d.rectangle([0, 0, W, int(H * 0.72)], fill=(232, 222, 205))
    # floor
    d.rectangle([0, int(H * 0.72), W, H], fill=(166, 140, 105))
    d.line([(0, int(H * 0.72)), (W, int(H * 0.72))], fill=(140, 115, 85), width=3)
    # BIG board — almost full upper half
    bx0, by0, bx1, by1 = 36, 70, W - 36, int(H * 0.48)
    d.rounded_rectangle([bx0 - 8, by0 - 8, bx1 + 8, by1 + 8], 12, fill=(90, 70, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 8, fill=(34, 85, 55))
    # chalk lines decoration
    d.line([bx0 + 24, by1 - 28, bx1 - 24, by1 - 28], fill=(200, 220, 200), width=2)
    # topic text on board (wrapped)
    tf = font(40)
    words = (topic or "Today's lesson").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 40):
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    lines = lines[:4]
    y = by0 + 36
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(245, 250, 240))
        y += 48
    # chalk tray
    d.rectangle([bx0, by1 + 4, bx1, by1 + 18], fill=(120, 95, 60))
    return img


def word_windows(text: str, duration: float):
    words = [w for w in text.replace("\n", " ").split() if w]
    if not words:
        return [(0, duration, ["..."], 0)]
    n = len(words)
    slot = duration / max(n, 1)
    windows = []
    i = 0
    while i < n:
        chunk = words[i : i + 6]  # 5-6 words
        if len(chunk) > 5 and len(chunk[-1]) > 8:
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


def draw_karaoke(rgb, text, t, duration, action):
    d = ImageDraw.Draw(rgb)
    af = font(15)
    label = f"MEZI · {action.upper()}"
    d.rounded_rectangle([W - 185, 24, W - 16, 58], 10, fill=HOODIE)
    d.text((W - 175, 30), label, font=af, fill=BLACK)

    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(32)
    # fit words inside margins
    max_w = W - 48
    gaps = []
    total = 0
    display = []
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        if total + ww + 12 > max_w and display:
            break
        display.append(w)
        gaps.append(ww)
        total += ww + 12
    if not display:
        display, gaps, total = chunk[:1], [40], 40
    active = min(active, len(display) - 1)
    total = max(total - 12, 1)
    x0 = max(24, (W - total) // 2)
    y = H - 130
    d.rounded_rectangle([20, y - 18, W - 20, y + 58], 16, fill=(12, 12, 20))
    x = x0
    for i, w in enumerate(display):
        if i == active:
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                d.text((x + ox, y + oy), w, font=cf, fill=GLOW)
            d.text((x, y), w, font=cf, fill=WHITE)
        else:
            d.text((x, y), w, font=cf, fill=(175, 175, 185))
        x += gaps[i] + 12


def composite_mezi(action: str, mouth_open: float) -> Image.Image:
    if action == "walk":
        body = load_rgba("body_walk.png")
    elif action == "point":
        body = load_rgba("arm_point.png")
    else:
        body = load_rgba("body.png")
    char = Image.alpha_composite(body, load_rgba(mouth_sprite(mouth_open)))
    if action == "laugh":
        char = Image.alpha_composite(char, load_rgba("eyes_laugh.png"))
    return char


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Today's lesson")
    p.add_argument("--bg", default="classroom")
    p.add_argument("--bg-image", default="")
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
    duration = min(max(float(dur_s), 1.0), 50.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic

    base = draw_classroom(topic)
    print(f"classroom board duration={duration:.2f}s frames={n} cues={len(cues)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * 3.0 if action == "walk" else t * 1.2
            frame = base.copy().convert("RGBA")
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.8)
            char = composite_mezi(action, mouth)
            target_h = int(H * 0.42)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)
            bob = int(3 * math.sin(phase * 2))
            if action == "walk":
                x_off = int(-60 + 120 * ((t * 0.3) % 1.0))
            elif action == "point":
                x_off = 40  # stand more to side, point at board
            else:
                x_off = 0
            x = (W - nw) // 2 + x_off
            y = H - nh - 150 + bob
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_karaoke(rgb, args.text, t, duration, action)
            rgb.save(tmp_path / f"frame_{i:05d}.png")

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
