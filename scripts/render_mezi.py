#!/usr/bin/env python3
"""Tri-scene BGs, board topic+definition+CTA, camera modes, did-you-know overlay."""
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
    return "sky"


def secondary_world(primary: str) -> str:
    order = ["space", "sky", "nature", "lab"]
    if primary in order:
        return order[(order.index(primary) + 1) % len(order)]
    return "nature"


def draw_classroom(topic: str, definition: str = "", cta: str = "") -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), (245, 248, 252))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.72)], fill=(248, 250, 252))
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(55, 65, 80))
    d.rectangle([0, int(bh * 0.72) - 8, bw, int(bh * 0.72)], fill=ACCENT)
    for i in range(3):
        x0 = 40 + i * 170
        d.rounded_rectangle([x0, 36, x0 + 140, 200], 10, fill=(220, 230, 240))
        d.rectangle([x0 + 8, 44, x0 + 132, 192], fill=(170, 210, 245))
    bx0, by0 = 40, 220
    bx1, by1 = bw - 60, int(bh * 0.52)
    d.rounded_rectangle([bx0 - 8, by0 - 8, bx1 + 8, by1 + 8], 14, fill=(30, 35, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 10, fill=(18, 78, 62))

    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(58)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 50) and tf.size > 28:
        tf = font(tf.size - 3)
    lines = wrap_text(d, topic, tf, bx1 - bx0 - 50)[:2]
    y = by0 + 28
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(240, 255, 245))
        y += tf.size + 8

    # definition under topic
    if definition:
        df = font(28)
        dlines = wrap_text(d, definition, df, bx1 - bx0 - 50)[:3]
        y += 10
        for line in dlines:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=(200, 235, 215))
            y += df.size + 6

    # CTA strip on board bottom
    cta = cta or "Comment YES for part 2"
    cf = font(26)
    d.rounded_rectangle([bx0 + 20, by1 - 55, bx1 - 20, by1 - 12], 10, fill=ACCENT)
    bb = d.textbbox((0, 0), cta, font=cf)
    tw = bb[2] - bb[0]
    d.text((bx0 + (bx1 - bx0 - tw) // 2, by1 - 48), cta, font=cf, fill=BLACK)

    d.rounded_rectangle(
        [bw // 2 - 220, int(bh * 0.62), bw // 2 + 220, int(bh * 0.68)],
        12, fill=(70, 80, 95),
    )
    return img


def draw_space() -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), (6, 8, 24))
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(240):
        x, y = rng.randint(0, bw - 1), rng.randint(0, int(bh * 0.78))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    sx, sy = int(bw * 0.72), int(bh * 0.2)
    d.ellipse([sx - 45, sy - 45, sx + 45, sy + 45], fill=(255, 245, 180))
    d.rectangle([0, int(bh * 0.8), bw, bh], fill=(10, 12, 28))
    return img


def draw_sky() -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), (130, 185, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([int(bw * 0.7), int(bh * 0.06), int(bw * 0.9), int(bh * 0.18)], fill=(255, 230, 120))
    d.rectangle([0, int(bh * 0.74), bw, bh], fill=(85, 155, 85))
    return img


def draw_nature() -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), (155, 205, 155))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.55)], fill=(135, 195, 235))
    d.rectangle([0, int(bh * 0.55), bw, bh], fill=(65, 125, 65))
    return img


def draw_lab() -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), (225, 228, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(80, 85, 95))
    sx, sy = int(bw * 0.75), int(bh * 0.26)
    d.ellipse([sx - 45, sy - 45, sx + 45, sy + 45], fill=(120, 220, 255))
    return img


def make_bg(kind: str, topic: str = "", definition: str = "", cta: str = "") -> Image.Image:
    if kind == "classroom":
        return draw_classroom(topic, definition, cta)
    return {
        "space": draw_space,
        "sky": draw_sky,
        "nature": draw_nature,
        "lab": draw_lab,
    }.get(kind, draw_sky)()


def camera_crop(full: Image.Image, t: float, duration: float, mode: str) -> Image.Image:
    """Camera modes: wide, close, left, right, pan."""
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    fw, fh = full.size

    if mode == "close":
        scale = 1.22 + 0.04 * math.sin(progress * math.pi)
        ox, oy = 0.5, 0.35
    elif mode == "left":
        scale = 1.12
        ox, oy = 0.25 + 0.1 * ease, 0.4
    elif mode == "right":
        scale = 1.12
        ox, oy = 0.65 - 0.1 * ease, 0.4
    elif mode == "pan":
        scale = 1.1 + 0.06 * ease
        ox, oy = 0.2 + 0.55 * ease, 0.35 + 0.1 * (1 - ease)
    else:  # wide
        scale = 1.0 + 0.06 * ease
        ox, oy = 0.45 + 0.1 * ease, 0.4

    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * max(0.0, min(1.0, ox)))
    y = int(max_y * max(0.0, min(1.0, oy)))
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
        {"at": 0.12, "move": "talk"},
        {"at": 0.28, "move": "walk_left"},
        {"at": 0.4, "move": "point"},
        {"at": 0.55, "move": "question"},
        {"at": 0.7, "move": "sit"},
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


def scene_at(p: float) -> str:
    """Tri-scene: classroom -> world A -> world B / CTA feel."""
    if p < 0.28:
        return "classroom"
    if p < 0.62:
        return "world"
    return "world2"


def cam_for(move: str, p: float) -> str:
    if move in ("walk_left",):
        return "left"
    if move in ("walk_right",):
        return "right"
    if move == "point":
        return "right"
    if move == "sit":
        return "close"
    if move == "present":
        return "wide"
    if p < 0.15:
        return "close"
    if p > 0.8:
        return "wide"
    return "pan"


def body_for(move: str, t: float, blink: bool) -> str:
    if blink and move in ("talk", "welcome", "present", "happy", "question"):
        return "body_blink.png"
    if move in ("walk_left", "walk_right"):
        phase = int(t * 7) % 2
        return f"walk_l{phase}.png" if move == "walk_left" else f"walk_r{phase}.png"
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
    if move in ("walk_left", "walk_right", "sit"):
        return body
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


def draw_ui(rgb, text, t, duration, topic: str, dyk: str, cta: str, p: float):
    d = ImageDraw.Draw(rgb)
    # topic chip
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W - tw - 60, 24, W - 24, 78], 14, fill=ACCENT)
    d.text((W - tw - 42, 38), label, font=af, fill=BLACK)

    # Did you know card mid-video
    if 0.48 <= p <= 0.66 and dyk:
        df = font(30)
        lines = wrap_text(d, "Did you know? " + dyk, df, W - 100)[:4]
        box_h = 40 + len(lines) * (df.size + 8)
        d.rounded_rectangle([40, 120, W - 40, 120 + box_h], 16, fill=(15, 18, 30))
        d.rounded_rectangle([40, 120, W - 40, 128], 4, fill=ACCENT)
        y = 140
        for line in lines:
            d.text((60, y), line, font=df, fill=WHITE)
            y += df.size + 8

    # CTA bar near end
    if p >= 0.78:
        cf = font(32)
        msg = cta or "Comment YES for part 2"
        bb = d.textbbox((0, 0), msg, font=cf)
        tw = bb[2] - bb[0]
        d.rounded_rectangle([W // 2 - tw // 2 - 28, 100, W // 2 + tw // 2 + 28, 160], 16, fill=ACCENT)
        d.text((W // 2 - tw // 2, 112), msg, font=cf, fill=BLACK)

    # karaoke
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
    definition = Path("definition.txt").read_text(encoding="utf-8").strip() if Path("definition.txt").exists() else ""
    dyk = Path("did_you_know.txt").read_text(encoding="utf-8").strip() if Path("did_you_know.txt").exists() else ""
    cta = Path("cta.txt").read_text(encoding="utf-8").strip() if Path("cta.txt").exists() else "Comment YES for part 2"

    world = topic_world(topic)
    world2 = secondary_world(world)
    bg_class = make_bg("classroom", topic, definition, cta)
    bg_w1 = make_bg(world)
    bg_w2 = make_bg(world2)
    print(f"tri-scene class->{world}->{world2} moves={moves} dur={duration:.2f}s")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            move = move_at(moves, t, duration)
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 10 == 0)
            scene = scene_at(pfrac)
            cam = cam_for(move, pfrac)

            if scene == "classroom":
                base_full = bg_class
            elif scene == "world":
                base_full = bg_w1
            else:
                base_full = bg_w2

            # soft crossfade at scene borders
            if 0.26 <= pfrac <= 0.30:
                a = (pfrac - 0.26) / 0.04
                base_full = Image.blend(bg_class, bg_w1, a)
            elif 0.60 <= pfrac <= 0.64:
                a = (pfrac - 0.60) / 0.04
                base_full = Image.blend(bg_w1, bg_w2, a)

            frame = camera_crop(base_full, t, duration, cam).convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(move, mouth, blink, t)
            target_h = int(H * (0.52 if cam == "close" else 0.46))
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(3 * math.sin(t * 6))
            if move == "walk_left":
                x = int(W * 0.55 - (t * 40) % (W * 0.25))
                bob = int(9 * abs(math.sin(t * 11)))
            elif move == "walk_right":
                x = int(W * 0.25 + (t * 40) % (W * 0.25))
                bob = int(9 * abs(math.sin(t * 11)))
            elif move == "point":
                x = int(W * 0.2)
            elif move == "sit":
                x = (W - nw) // 2
                bob = 0
                draw_chair(frame, W // 2, H - 210 - int(nh * 0.28))
            else:
                x = (W - nw) // 2

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
        sz = out_mp4.stat().st_size
        if sz < 50_000:
            raise SystemExit(f"output too small: {sz}")
        print("OK", out_mp4, sz)


if __name__ == "__main__":
    main()
