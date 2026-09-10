#!/usr/bin/env python3
"""Mike: clean classroom, teach-only moves, lips, dual scene optional."""
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
    "X": 0.0, "B": 0.25, "A": 1.0, "C": 0.55,
    "D": 0.7, "E": 0.85, "F": 0.5, "G": 0.95, "H": 1.0,
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
    data = json.loads(path.read_text(encoding="utf-8"))
    cues = data.get("mouthCues") or []
    print(f"LOADED {len(cues)} mouth cues", file=sys.stderr)
    return cues


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.45 + 0.4 * abs(math.sin(t * 14))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.55)
    return 0.0


def mouth_name(open_amt: float) -> str:
    if open_amt >= 0.7:
        return "mouth_wide.png"
    if open_amt >= 0.28:
        return "mouth_open.png"
    if open_amt >= 0.08:
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


def wrap_text(d, text, tf, max_w):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_classroom(topic: str, definition: str = "", cta: str = "") -> Image.Image:
    """Clean modern classroom — trust, not neon clutter."""
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (232, 236, 242))
    d = ImageDraw.Draw(img)

    # soft wall
    d.rectangle([0, 0, bw, int(bh * 0.7)], fill=(240, 243, 248))
    # floor
    d.rectangle([0, int(bh * 0.7), bw, bh], fill=(58, 64, 78))
    d.rectangle([0, int(bh * 0.7) - 8, bw, int(bh * 0.7)], fill=(255, 196, 40))

    # left windows (simple daylight)
    for i in range(2):
        x0 = 36 + i * 150
        d.rounded_rectangle([x0, 40, x0 + 130, 200], 10, fill=(190, 210, 230))
        d.rectangle([x0 + 8, 48, x0 + 122, 192], fill=(160, 195, 230))

    # BIG board — main teaching surface
    bx0, by0 = 50, 230
    bx1, by1 = bw - 50, int(bh * 0.58)
    d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 12, fill=(40, 48, 58))
    d.rounded_rectangle([bx0, by0, bx1, by1], 8, fill=(28, 95, 78))

    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(58)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 48) and tf.size > 28:
        tf = font(tf.size - 3)
    y = by0 + 36
    for line in wrap_text(d, topic, tf, bx1 - bx0 - 48)[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(245, 255, 248))
        y += tf.size + 10

    if definition:
        df = font(28)
        y += 12
        for line in wrap_text(d, definition, df, bx1 - bx0 - 48)[:4]:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=(190, 230, 210))
            y += df.size + 6

    cta = cta or "Comment what you understood"
    cf = font(24)
    d.rounded_rectangle([bx0 + 24, by1 - 58, bx1 - 24, by1 - 14], 12, fill=ACCENT)
    bb = d.textbbox((0, 0), cta[:42], font=cf)
    tw = bb[2] - bb[0]
    d.text((bx0 + (bx1 - bx0 - tw) // 2, by1 - 48), cta[:42], font=cf, fill=BLACK)

    # thin shelf under board
    d.rectangle([bx0, by1 + 14, bx1, by1 + 28], fill=(70, 78, 92))
    return img


def draw_stage() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (245, 247, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(50, 56, 70))
    d.ellipse([int(bw * 0.2), int(bh * 0.8), int(bw * 0.8), int(bh * 0.95)], outline=ACCENT, width=3)
    return img


def draw_space() -> Image.Image:
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (8, 12, 28))
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(200):
        x, y = rng.randint(0, bw - 1), rng.randint(0, int(bh * 0.75))
        r = rng.randint(1, 2)
        d.ellipse([x, y, x + r, y + r], fill=(230, 235, 255))
    return img


def make_bg(kind: str, topic: str = "", definition: str = "", cta: str = "") -> Image.Image:
    if kind in ("classroom", "stage", ""):
        return draw_classroom(topic, definition, cta)
    if kind == "space":
        return draw_space()
    return draw_classroom(topic, definition, cta)


def camera_crop(full: Image.Image, t: float, duration: float, mode: str) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    fw, fh = full.size
    if mode == "close":
        scale, ox, oy = 1.18, 0.5, 0.28
    elif mode == "pan":
        scale, ox, oy = 1.06 + 0.04 * ease, 0.25 + 0.4 * ease, 0.32
    else:
        scale, ox, oy = 1.0 + 0.04 * ease, 0.5, 0.35
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * max(0.0, min(1.0, ox)))
    y = int(max_y * max(0.0, min(1.0, oy)))
    return full.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def load_moves() -> list[dict]:
    for path in (Path("moves.json"), Path("script_job.json")):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if path.name == "script_job.json":
                data = data.get("moves") or []
            if isinstance(data, list) and len(data) >= 2:
                # strip walks
                cleaned = []
                for m in data:
                    mv = m.get("move", "talk")
                    if mv in ("walk_left", "walk_right"):
                        mv = "talk"
                    cleaned.append({"at": float(m.get("at", 0)), "move": mv})
                return sorted(cleaned, key=lambda x: x["at"])
        except Exception:
            pass
    return [
        {"at": 0.0, "move": "question"},
        {"at": 0.12, "move": "talk"},
        {"at": 0.28, "move": "point"},
        {"at": 0.5, "move": "talk"},
        {"at": 0.72, "move": "present"},
        {"at": 0.88, "move": "happy"},
    ]


def move_at(moves: list[dict], t: float, duration: float) -> str:
    p = t / max(duration, 0.1)
    current = moves[0].get("move", "talk") if moves else "talk"
    for m in moves:
        if float(m.get("at", 0)) <= p:
            current = m.get("move", "talk")
        else:
            break
    if current in ("walk_left", "walk_right"):
        return "talk"
    return current


def cam_for(move: str, p: float) -> str:
    if move == "point":
        return "pan"
    if move == "sit":
        return "close"
    if move == "present":
        return "wide"
    if p < 0.1:
        return "close"
    return "pan"


def body_for(move: str, t: float, blink: bool) -> str:
    if blink and move in ("talk", "welcome", "present", "happy", "question"):
        return "body_blink.png"
    return {
        "welcome": "body_present.png",
        "talk": "body.png",
        "point": "arm_point.png",
        "sit": "body_sit.png",
        "present": "body_present.png",
        "question": "body_question.png",
        "happy": "body_happy.png",
    }.get(move, "body.png")


def composite_host(move: str, mouth_open: float, blink: bool, t: float) -> Image.Image:
    body = load_rgba(body_for(move, t, blink))
    mouth = load_rgba(mouth_name(mouth_open))
    if mouth.size != body.size:
        mouth = mouth.resize(body.size, Image.Resampling.NEAREST)
    return Image.alpha_composite(body, mouth)


def draw_chair(frame: Image.Image, cx: int, seat_y: int) -> None:
    d = ImageDraw.Draw(frame)
    wood, wood_d = (70, 78, 92), (50, 56, 68)
    w, h_seat, leg, back_h = 170, 18, 75, 95
    d.rounded_rectangle([cx - w // 2, seat_y, cx + w // 2, seat_y + h_seat], 6, fill=wood)
    d.rounded_rectangle([cx - w // 2, seat_y - back_h, cx - w // 2 + 16, seat_y + h_seat], 6, fill=wood_d)
    d.rounded_rectangle([cx + w // 2 - 16, seat_y - back_h, cx + w // 2, seat_y + h_seat], 6, fill=wood_d)
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


def draw_ui(rgb, text, t, duration, topic: str, dyk: str, cta: str, p: float):
    d = ImageDraw.Draw(rgb)
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W - tw - 60, 24, W - 24, 78], 14, fill=ACCENT)
    d.text((W - tw - 42, 38), label, font=af, fill=BLACK)

    if 0.45 <= p <= 0.65 and dyk:
        df = font(28)
        lines = wrap_text(d, "Did you know? " + dyk, df, W - 100)[:3]
        box_h = 36 + len(lines) * (df.size + 8)
        d.rounded_rectangle([40, 110, W - 40, 110 + box_h], 16, fill=(20, 28, 40))
        y = 128
        for line in lines:
            d.text((56, y), line, font=df, fill=WHITE)
            y += df.size + 8

    if p >= 0.78:
        cf = font(30)
        msg = (cta or "Comment what you understood")[:40]
        bb = d.textbbox((0, 0), msg, font=cf)
        tw = bb[2] - bb[0]
        d.rounded_rectangle([W // 2 - tw // 2 - 24, 100, W // 2 + tw // 2 + 24, 158], 16, fill=ACCENT)
        d.text((W // 2 - tw // 2, 112), msg, font=cf, fill=BLACK)

    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(44)
    gaps, display, total = [], [], 0
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        if total + ww + 14 > W - 64 and display:
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
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)], text=True,
    ).strip()
    duration = min(max(float(dur_s), 1.0), 90.0)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))
    moves = load_moves()
    print("MOVES", moves, file=sys.stderr)

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic
    definition = Path("definition.txt").read_text(encoding="utf-8").strip() if Path("definition.txt").exists() else ""
    dyk = Path("did_you_know.txt").read_text(encoding="utf-8").strip() if Path("did_you_know.txt").exists() else ""
    cta = Path("cta.txt").read_text(encoding="utf-8").strip() if Path("cta.txt").exists() else "Comment what you understood"

    bg = make_bg("classroom", topic, definition, cta)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            move = move_at(moves, t, duration)
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 10 == 0)
            cam = cam_for(move, pfrac)

            frame = camera_crop(bg, t, duration, cam).convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(move, mouth, blink, t)
            target_h = int(H * (0.5 if cam == "close" else 0.44))
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(2 * math.sin(t * 5))
            x = (W - nw) // 2
            if move == "point":
                x = int(W * 0.28)
            elif move == "sit":
                bob = 0
                draw_chair(frame, W // 2, H - 200 - int(nh * 0.25))

            y = H - nh - (160 if cam == "close" else 200) + bob
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_ui(rgb, args.text, t, duration, topic, dyk, cta, pfrac)
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
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
