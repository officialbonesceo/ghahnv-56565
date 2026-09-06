#!/usr/bin/env python3
"""Mike: AI moves timeline, Ken Burns, modern classroom, proper walk cycle + lips."""
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
    "X": 0.0, "B": 0.15, "A": 1.0, "C": 0.55,
    "D": 0.7, "E": 0.85, "F": 0.45, "G": 0.95, "H": 1.0,
}


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "mezi"


def load_rgba(name: str) -> Image.Image:
    p = asset_dir() / name
    if not p.exists():
        return Image.open(asset_dir() / "body.png").convert("RGBA")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.35 + 0.35 * abs(math.sin(t * 14))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.5)
    return 0.0


def mouth_name(open_amt: float) -> str:
    if open_amt >= 0.75:
        return "mouth_wide.png"
    if open_amt >= 0.35:
        return "mouth_open.png"
    if open_amt >= 0.12:
        return "mouth_smile.png"
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
    """Modern classroom — larger canvas for Ken Burns."""
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (245, 248, 252))
    d = ImageDraw.Draw(img)
    # modern wall
    d.rectangle([0, 0, bw, int(bh * 0.72)], fill=(248, 250, 252))
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(55, 65, 80))
    # accent stripe
    d.rectangle([0, int(bh * 0.72) - 8, bw, int(bh * 0.72)], fill=(255, 196, 40))
    # tall windows
    for i in range(3):
        x0 = 40 + i * 170
        d.rounded_rectangle([x0, 40, x0 + 140, 220], 10, fill=(220, 230, 240))
        d.rectangle([x0 + 8, 48, x0 + 132, 212], fill=(170, 210, 245))
        d.line([x0 + 70, 48, x0 + 70, 212], fill=(200, 210, 220), width=3)
    # digital board frame
    bx0, by0 = 50, 250
    bx1, by1 = bw - 80, int(bh * 0.48)
    d.rounded_rectangle([bx0 - 8, by0 - 8, bx1 + 8, by1 + 8], 14, fill=(30, 35, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 10, fill=(20, 90, 70))
    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(70)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 60) and tf.size > 32:
        tf = font(tf.size - 4)
    words = topic.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 60):
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
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(240, 255, 245))
        y += tf.size + 14
    # modern desk
    d.rounded_rectangle(
        [bw // 2 - 220, int(bh * 0.62), bw // 2 + 220, int(bh * 0.68)],
        12,
        fill=(70, 80, 95),
    )
    return img


def draw_space() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (6, 8, 24))
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(220):
        x, y = rng.randint(0, bw - 1), rng.randint(0, int(bh * 0.78))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    sx, sy = int(bw * 0.72), int(bh * 0.2)
    d.ellipse([sx - 45, sy - 45, sx + 45, sy + 45], fill=(255, 245, 180))
    d.rectangle([0, int(bh * 0.8), bw, bh], fill=(10, 12, 28))
    return img


def draw_sky() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (130, 185, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([int(bw * 0.7), int(bh * 0.06), int(bw * 0.9), int(bh * 0.18)], fill=(255, 230, 120))
    d.rectangle([0, int(bh * 0.74), bw, bh], fill=(85, 155, 85))
    return img


def draw_nature() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (155, 205, 155))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.55)], fill=(135, 195, 235))
    d.rectangle([0, int(bh * 0.55), bw, bh], fill=(65, 125, 65))
    return img


def draw_lab() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (225, 228, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(80, 85, 95))
    sx, sy = int(bw * 0.75), int(bh * 0.26)
    d.ellipse([sx - 45, sy - 45, sx + 45, sy + 45], fill=(120, 220, 255))
    return img


def make_bg(kind: str, topic: str) -> Image.Image:
    return {
        "space": draw_space,
        "sky": draw_sky,
        "nature": draw_nature,
        "lab": draw_lab,
    }.get(kind, lambda: draw_classroom(topic))()


def ken_crop(full: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    scale = 1.0 + 0.08 * ease
    fw, fh = full.size
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * ease * 0.9)
    y = int(max_y * (1 - ease) * 0.4)
    return full.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def load_moves() -> list[dict]:
    if Path("moves.json").exists():
        try:
            data = json.loads(Path("moves.json").read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return sorted(data, key=lambda x: float(x.get("at", 0)))
        except Exception:
            pass
    return [
        {"at": 0.0, "move": "welcome"},
        {"at": 0.15, "move": "talk"},
        {"at": 0.3, "move": "walk_left"},
        {"at": 0.45, "move": "point"},
        {"at": 0.65, "move": "sit"},
        {"at": 0.85, "move": "present"},
    ]


def move_at(moves: list[dict], t: float, duration: float) -> str:
    p = t / max(duration, 0.1)
    current = moves[0].get("move", "talk") if moves else "talk"
    for m in moves:
        if float(m.get("at", 0)) <= p:
            current = m.get("move", "talk")
        else:
            break
    return current


def body_for(move: str, t: float, blink: bool) -> str:
    if blink and move in ("talk", "welcome", "present", "happy", "question"):
        return "body_blink.png"
    if move in ("walk_left", "walk_right"):
        phase = int(t * 7) % 2
        if move == "walk_left":
            return f"walk_l{phase}.png"
        return f"walk_r{phase}.png"
    return {
        "welcome": "body_present.png",
        "talk": "body.png",
        "point": "arm_point.png",
        "sit": "body_sit.png",
        "present": "body_present.png",
        "question": "body_question.png",
        "happy": "body_happy.png",
    }.get(move, "body.png")


def is_side(move: str) -> bool:
    return move in ("walk_left", "walk_right")


def composite_host(move: str, mouth_open: float, blink: bool, t: float) -> Image.Image:
    body = load_rgba(body_for(move, t, blink))
    if is_side(move) or move == "sit":
        return body  # mouth baked / wrong Y
    mouth = load_rgba(mouth_name(mouth_open))
    return Image.alpha_composite(body, mouth)


def draw_chair(frame: Image.Image, cx: int, seat_y: int) -> None:
    d = ImageDraw.Draw(frame)
    wood, wood_d = (100, 110, 125), (70, 80, 95)
    w, h_seat, leg, back_h = 170, 18, 75, 95
    d.rounded_rectangle([cx - w // 2, seat_y, cx + w // 2, seat_y + h_seat], 6, fill=wood)
    d.rounded_rectangle([cx - w // 2, seat_y - back_h, cx - w // 2 + 16, seat_y + h_seat], 6, fill=wood_d)
    d.rounded_rectangle([cx + w // 2 - 16, seat_y - back_h, cx + w // 2, seat_y + h_seat], 6, fill=wood_d)
    d.rectangle([cx - w // 2, seat_y - back_h, cx + w // 2, seat_y - back_h + 14], fill=wood)
    for lx in (cx - w // 2 + 10, cx + w // 2 - 20):
        d.rectangle([lx, seat_y + h_seat, lx + 10, seat_y + h_seat + leg], fill=wood_d)


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


def draw_ui(rgb, text, t, duration, topic: str):
    d = ImageDraw.Draw(rgb)
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W - tw - 60, 24, W - 24, 78], 14, fill=ACCENT)
    d.text((W - tw - 42, 38), label, font=af, fill=BLACK)

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
    moves = load_moves()

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic

    world = topic_world(topic)
    bg_board = draw_classroom(topic)
    bg_world = make_bg(world, topic)
    print(f"AI moves={moves} board->{world} dur={duration:.2f}s")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            move = move_at(moves, t, duration)
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 10 == 0)

            # scene: classroom until first walk, then world
            walked = any(
                m.get("move") in ("walk_left", "walk_right") and float(m.get("at", 1)) <= pfrac
                for m in moves
            )
            if move in ("walk_left", "walk_right"):
                # blend during walk
                base_full = Image.blend(bg_board, bg_world, 0.5)
            elif walked:
                base_full = bg_world
            else:
                base_full = bg_board

            frame = ken_crop(base_full, t, duration).convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(move, mouth, blink, t)
            target_h = int(H * 0.46)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(3 * math.sin(t * 6))
            if move == "walk_left":
                # progress within walk segment
                x = int(W * 0.55 - (t * 40) % (W * 0.25))
                bob = int(9 * abs(math.sin(t * 11)))
            elif move == "walk_right":
                x = int(W * 0.25 + (t * 40) % (W * 0.25))
                bob = int(9 * abs(math.sin(t * 11)))
            elif move == "point":
                x = int(W * 0.22)
            elif move == "sit":
                x = (W - nw) // 2
                bob = 0
                draw_chair(frame, W // 2, H - 210 - int(nh * 0.28))
            else:
                x = (W - nw) // 2

            y = H - nh - 200 + bob
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_ui(rgb, args.text, t, duration, topic)
            rgb.save(tmp_path / f"frame_{i:05d}.png")

        out_mp4 = Path(args.out).resolve()
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
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
