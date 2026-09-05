#!/usr/bin/env python3
"""Mike multi-scene: classroom board -> walk sideways -> topic world -> present to camera."""
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

# Performance beat timeline (fractions of total duration)
# 0.00-0.22 board intro (front talk)
# 0.22-0.38 walk off board to the left (side profile)
# 0.38-0.72 topic world + point at subject
# 0.72-1.00 face audience present / talk


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
    return json.loads(path.read_text(encoding="utf-8")).get("mouthCues") or []


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


def draw_classroom(topic: str, size: tuple[int, int] | None = None) -> Image.Image:
    bw, bh = size or (W, H)
    img = Image.new("RGB", (bw, bh), (245, 236, 220))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.72)], fill=(232, 222, 205))
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(166, 140, 105))
    bx0, by0 = int(bw * 0.05), int(bh * 0.05)
    bx1, by1 = int(bw * 0.95), int(bh * 0.42)
    d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 16, fill=(90, 70, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=(34, 85, 55))
    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(max(36, bw // 18))
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 40) and tf.size > 28:
        tf = font(tf.size - 4)
    words = topic.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 40):
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = by0 + 40
    for line in lines[:3]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(250, 255, 245))
        y += tf.size + 12
    d.rectangle([bx0, by1 + 4, bx1, by1 + 16], fill=(120, 95, 60))
    return img


def draw_space(size: tuple[int, int] | None = None) -> Image.Image:
    bw, bh = size or (W, H)
    img = Image.new("RGB", (bw, bh), (8, 10, 28))
    d = ImageDraw.Draw(img)
    rng = random.Random(42)
    for _ in range(120):
        x, y = rng.randint(0, bw - 1), rng.randint(0, int(bh * 0.75))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    # big star to point at
    sx, sy = int(bw * 0.72), int(bh * 0.22)
    d.ellipse([sx - 28, sy - 28, sx + 28, sy + 28], fill=(255, 250, 200))
    d.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], fill=(255, 255, 240))
    d.rectangle([0, int(bh * 0.78), bw, bh], fill=(15, 18, 40))
    return img


def draw_sky(size: tuple[int, int] | None = None) -> Image.Image:
    bw, bh = size or (W, H)
    img = Image.new("RGB", (bw, bh), (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([int(bw * 0.7), int(bh * 0.08), int(bw * 0.88), int(bh * 0.2)], fill=(255, 230, 120))
    for cx, cy, r in [(0.2, 0.18, 80), (0.45, 0.12, 60), (0.65, 0.2, 70)]:
        x, y = int(bw * cx), int(bh * cy)
        d.ellipse([x - r, y - r // 2, x + r, y + r // 2], fill=(250, 250, 255))
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(90, 160, 90))
    return img


def draw_nature(size: tuple[int, int] | None = None) -> Image.Image:
    bw, bh = size or (W, H)
    img = Image.new("RGB", (bw, bh), (160, 210, 160))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.55)], fill=(140, 200, 240))
    d.rectangle([0, int(bh * 0.55), bw, bh], fill=(70, 130, 70))
    # trees
    for tx in (0.15, 0.35, 0.8):
        x = int(bw * tx)
        d.rectangle([x - 12, int(bh * 0.45), x + 12, int(bh * 0.65)], fill=(90, 60, 30))
        d.ellipse([x - 50, int(bh * 0.32), x + 50, int(bh * 0.52)], fill=(40, 120, 50))
    return img


def draw_lab(size: tuple[int, int] | None = None) -> Image.Image:
    bw, bh = size or (W, H)
    img = Image.new("RGB", (bw, bh), (220, 225, 230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(bh * 0.7), bw, bh], fill=(90, 95, 105))
    # shelves
    d.rectangle([40, 80, bw - 40, 200], fill=(180, 185, 195))
    for i in range(4):
        x = 80 + i * (bw // 5)
        d.rectangle([x, 100, x + 40, 180], fill=(100, 180, 220))
    # glowing orb to point at
    sx, sy = int(bw * 0.75), int(bh * 0.28)
    d.ellipse([sx - 40, sy - 40, sx + 40, sy + 40], fill=(120, 220, 255))
    return img


def make_bg(kind: str, topic: str) -> Image.Image:
    if kind == "space":
        return draw_space()
    if kind == "sky":
        return draw_sky()
    if kind == "nature":
        return draw_nature()
    if kind == "lab":
        return draw_lab()
    return draw_classroom(topic)


def beat(t: float, duration: float) -> str:
    p = t / max(duration, 0.1)
    if p < 0.20:
        return "board_talk"
    if p < 0.36:
        return "walk_left"
    if p < 0.70:
        return "world_point"
    return "present"


def composite_host(pose: str, mouth_open: float) -> Image.Image:
    body_map = {
        "board_talk": "body.png",
        "walk_left": "body_side_left.png",
        "walk_right": "body_side_right.png",
        "world_point": "arm_point.png",
        "present": "body_present.png",
    }
    body = load_rgba(body_map.get(pose, "body.png"))
    char = Image.alpha_composite(body, load_rgba(mouth_sprite(mouth_open)))
    return char


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
    label = f"MIKE · {pose.replace('_', ' ').upper()[:12]}"
    d.rounded_rectangle([W - 300, 28, W - 24, 78], 14, fill=ACCENT)
    d.text((W - 285, 40), label, font=af, fill=BLACK)
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
    print(f"scenes board->{world} duration={duration:.2f}s frames={n}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            pose = beat(t, duration)
            pfrac = t / max(duration, 0.1)

            # background crossfade during walk
            if pose == "walk_left":
                # blend board -> world
                walk_p = (pfrac - 0.20) / 0.16
                walk_p = max(0.0, min(1.0, walk_p))
                base = Image.blend(bg_board, bg_world, walk_p)
            elif pose in ("world_point", "present"):
                base = bg_world.copy()
            else:
                base = bg_board.copy()

            frame = base.convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(pose, mouth)
            target_h = int(H * 0.42)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            # human-ish bob + walk path
            bob = int(5 * math.sin(t * 9))
            if pose == "walk_left":
                # move from center toward left, side profile
                walk_p = (pfrac - 0.20) / 0.16
                walk_p = max(0.0, min(1.0, walk_p))
                x = int((W - nw) // 2 - walk_p * (W * 0.35))
                # step bounce
                bob = int(8 * abs(math.sin(walk_p * math.pi * 4)))
            elif pose == "world_point":
                x = int(W * 0.28)
            elif pose == "present":
                x = (W - nw) // 2
                bob = int(3 * math.sin(t * 4))
            else:
                x = (W - nw) // 2

            y = H - nh - 210 + bob
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
