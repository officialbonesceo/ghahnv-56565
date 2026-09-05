#!/usr/bin/env python3
"""MEZI compositor: grounded character, small mouths, side-walk, karaoke."""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

W, H = 720, 1280
FPS = 12
HOODIE = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)
GLOW = (255, 220, 80)
# Clearer lip thresholds — closed vs open vs wide
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
        raise SystemExit(f"missing sprite {p}")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        # visible chatter without cues
        return 0.0 if math.sin(t * 16) < 0.15 else (0.5 + 0.4 * abs(math.sin(t * 16)))
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


def make_drawn_bg(kind: str) -> Image.Image:
    bw, bh = int(W * 1.25), int(H * 1.25)
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    k = (kind or "science").lower()
    rnd = random.Random(hash(k) & 0xFFFFFFFF)
    if k == "space":
        for y in range(bh):
            c = 6 + y // 80
            d.line([(0, y), (bw, y)], fill=(c, c + 2, 18 + c))
        for _ in range(250):
            x, y = rnd.randint(0, bw - 1), rnd.randint(0, bh - 1)
            r = rnd.choice([1, 1, 2, 3])
            b = rnd.randint(180, 255)
            d.ellipse([x, y, x + r, y + r], fill=(b, b, 255))
    elif k == "ocean":
        for y in range(bh):
            d.line([(0, y), (bw, y)], fill=(120, 190, 235) if y < bh * 0.4 else (15, 80, 130))
    elif k == "nature":
        for y in range(bh):
            d.line([(0, y), (bw, y)], fill=(255 - y // 20, 180 - y // 40, 120))
    elif k == "tech":
        d.rectangle([0, 0, bw, bh], fill=(12, 18, 32))
        for x in range(0, bw, 36):
            d.line([(x, 0), (x, bh)], fill=(30, 50, 70))
    else:
        for y in range(bh):
            d.line([(0, y), (bw, y)], fill=(220, 235, 250))
        d.ellipse([bw - 280, 40, bw - 40, 280], fill=(255, 210, 80))
    return img


def load_bg(kind: str, bg_path: str) -> Image.Image:
    if bg_path:
        p = Path(bg_path)
        if p.exists() and p.stat().st_size > 2000:
            im = Image.open(p).convert("RGB")
            return im.resize((int(W * 1.25), int(H * 1.25)), Image.Resampling.LANCZOS)
    return make_drawn_bg(kind)


def ken_burns(bg: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    scale = 1.0 + 0.18 * ease
    bw, bh = bg.size
    cw, ch = min(int(W * scale), bw), min(int(H * scale), bh)
    max_x, max_y = max(0, bw - cw), max(0, bh - ch)
    x = int(max_x * ease)
    y = int(max_y * (1.0 - ease) * 0.6)
    frame = bg.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-W // 5, -H // 8, W + W // 5, H + H // 8], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(80))
    dark = ImageEnhance.Brightness(frame).enhance(0.55)
    return Image.composite(frame, dark, mask)


def word_windows(text: str, duration: float):
    words = [w for w in text.replace("\n", " ").split() if w]
    if not words:
        return [(0, duration, ["..."], 0)]
    n = len(words)
    slot = duration / n
    windows = []
    i = 0
    while i < n:
        chunk = words[i : i + 4]
        start = i * slot
        end = min(duration, (i + len(chunk)) * slot)
        for j in range(len(chunk)):
            ws = start + j * (end - start) / len(chunk)
            we = start + (j + 1) * (end - start) / len(chunk)
            windows.append((ws, we, chunk, j))
        i += len(chunk)
    return windows


def active_caption(windows, t: float):
    for ws, we, chunk, j in windows:
        if ws <= t < we:
            return chunk, j
    if windows:
        return windows[-1][2], windows[-1][3]
    return [""], 0


def draw_karaoke(rgb, text, t, duration, title, action):
    d = ImageDraw.Draw(rgb)
    f = font(24)
    ttl = (title or "Mezi")[:34]
    bb = d.textbbox((0, 0), ttl, font=f)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([20, 32, 32 + tw + 16, 78], 14, fill=(0, 0, 0))
    d.text((28, 40), ttl, font=f, fill=WHITE)
    af = font(15)
    label = f"MEZI · {action.upper()}"
    d.rounded_rectangle([W - 185, 40, W - 20, 76], 12, fill=HOODIE)
    d.text((W - 175, 48), label, font=af, fill=BLACK)

    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(36)
    gaps = []
    total = 0
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        gaps.append(ww)
        total += ww + 16
    total = max(total - 16, 1)
    x0 = max(20, (W - total) // 2)
    y = H - 160
    d.rounded_rectangle([16, y - 24, W - 16, y + 70], 18, fill=(12, 12, 20))
    x = x0
    for i, w in enumerate(chunk):
        if i == active:
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                d.text((x + ox, y + oy), w, font=cf, fill=GLOW)
            d.text((x, y), w, font=cf, fill=WHITE)
        else:
            d.text((x, y), w, font=cf, fill=(170, 170, 180))
        x += gaps[i] + 16


def composite_mezi(action: str, mouth_open: float) -> Image.Image:
    if action == "walk":
        body = load_rgba("body_walk.png")
    elif action == "point":
        body = load_rgba("arm_point.png")
    else:
        body = load_rgba("body.png")
    mouth = load_rgba(mouth_sprite(mouth_open))
    char = Image.alpha_composite(body, mouth)
    if action == "laugh":
        char = Image.alpha_composite(char, load_rgba("eyes_laugh.png"))
    return char


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Mezi")
    p.add_argument("--bg", default="science")
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
    duration = min(max(float(dur_s), 1.0), 45.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))

    bg_path = args.bg_image
    if not bg_path and Path("bg_path.txt").exists():
        bg_path = Path("bg_path.txt").read_text(encoding="utf-8").strip()
    bg_full = load_bg(args.bg, bg_path)
    print(f"duration={duration:.2f}s frames={n} bg={args.bg} cues={len(cues)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * 3.0 if action == "walk" else t * 1.2
            frame = ken_burns(bg_full, t, duration).convert("RGBA")
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.8)
            char = composite_mezi(action, mouth)
            # smaller scale + feet near bottom (less floating)
            target_h = int(H * 0.48)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)
            bob = int(4 * math.sin(phase * 2))
            if action == "walk":
                # side walk: move across frame
                x_off = int(-80 + 160 * ((t * 0.35) % 1.0))
            else:
                x_off = 0
            x = (W - nw) // 2 + x_off
            y = H - nh - 180 + bob  # grounded above caption bar
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_karaoke(rgb, args.text, t, duration, args.title, action)
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
