#!/usr/bin/env python3
"""Mike Shorts: 5 classrooms, phenomenon support, pan + bounce."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
FPS = 24
HOOK_END = 2.5
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)
MOUTH = {"X": 0.0, "B": 0.25, "A": 1.0, "C": 0.55, "D": 0.7, "E": 0.85, "F": 0.5, "G": 0.95, "H": 1.0}

ROOMS = [
    {"id": "warm_cream", "wall": (255, 236, 210), "floor": (72, 48, 32), "board": (18, 85, 95),
     "frame": (40, 30, 25), "accent": (255, 170, 40), "window": (140, 200, 230),
     "desk": (80, 55, 40), "posters": [(255, 110, 90), (90, 170, 255), (100, 200, 120)]},
    {"id": "cool_lab", "wall": (210, 225, 245), "floor": (40, 50, 70), "board": (15, 45, 100),
     "frame": (20, 35, 55), "accent": (60, 170, 255), "window": (160, 210, 255),
     "desk": (45, 55, 75), "posters": [(70, 160, 255), (160, 120, 255), (80, 210, 180)]},
    {"id": "green_board", "wall": (235, 245, 220), "floor": (50, 55, 35), "board": (20, 100, 50),
     "frame": (30, 50, 25), "accent": (255, 210, 40), "window": (150, 210, 140),
     "desk": (60, 55, 35), "posters": [(255, 150, 60), (70, 190, 100), (255, 230, 80)]},
    {"id": "night_study", "wall": (28, 32, 48), "floor": (18, 20, 30), "board": (12, 55, 80),
     "frame": (55, 60, 80), "accent": (255, 130, 70), "window": (35, 50, 90),
     "desk": (35, 38, 50), "posters": [(255, 100, 80), (90, 130, 255), (180, 90, 220)]},
    {"id": "purple_studio", "wall": (240, 225, 250), "floor": (55, 35, 65), "board": (70, 30, 110),
     "frame": (50, 25, 70), "accent": (230, 100, 255), "window": (200, 170, 240),
     "desk": (75, 45, 80), "posters": [(255, 120, 190), (130, 100, 255), (255, 190, 100)]},
]
THUMB_STYLES = ["close_face", "board_hero", "side_teach", "split_color", "big_topic"]
OPEN_MOVES = ["question", "happy", "present", "point", "explain", "think"]


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
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
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


def pick_room(topic: str) -> dict:
    h = int(hashlib.md5((topic or "x").encode()).hexdigest(), 16)
    return ROOMS[h % len(ROOMS)]


def pick_thumb_style(topic: str) -> str:
    h = int(hashlib.md5(("thumb:" + (topic or "x")).encode()).hexdigest(), 16)
    return THUMB_STYLES[h % len(THUMB_STYLES)]


def pick_open_move(topic: str) -> str:
    h = int(hashlib.md5(("move:" + (topic or "x")).encode()).hexdigest(), 16)
    return OPEN_MOVES[h % len(OPEN_MOVES)]


def draw_classroom(topic: str, definition: str, room: dict) -> Image.Image:
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), room["wall"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.68)], fill=room["wall"])
    d.rectangle([0, int(bh * 0.68), bw, bh], fill=room["floor"])
    d.rectangle([0, int(bh * 0.68) - 16, bw, int(bh * 0.68)], fill=room["accent"])
    wx0, wy0, wx1, wy1 = 28, 48, 200, 300
    d.rounded_rectangle([wx0, wy0, wx1, wy1], 14, fill=room["window"])
    d.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=WHITE, width=3)
    d.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=WHITE, width=3)
    for i, col in enumerate(room["posters"]):
        px, py = bw - 165, 45 + i * 95
        d.rounded_rectangle([px, py, px + 125, py + 80], 12, fill=col)
    bx0, by0, bx1, by1 = 220, 65, bw - 190, int(bh * 0.58)
    d.rounded_rectangle([bx0 - 12, by0 - 12, bx1 + 12, by1 + 12], 16, fill=room["frame"])
    d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=room["board"])
    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(56)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 48) and tf.size > 26:
        tf = font(tf.size - 3)
    y = by0 + 48
    for line in wrap_text(d, topic, tf, bx1 - bx0 - 48)[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=WHITE)
        y += tf.size + 12
    if definition:
        df = font(28)
        y += 16
        for line in wrap_text(d, definition, df, bx1 - bx0 - 48)[:5]:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=(220, 235, 245))
            y += df.size + 6
    d.rounded_rectangle([bw // 2 - 280, int(bh * 0.72), bw // 2 + 280, int(bh * 0.78)], 10, fill=room["desk"])
    return img


def draw_thumb_frame(style: str, topic: str, hook: str, room: dict, char: Image.Image) -> Image.Image:
    accent, board, wall = room["accent"], room["board"], room["wall"]
    if style == "close_face":
        img = Image.new("RGB", (W, H), (14, 12, 20))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 22], fill=accent)
        d.rectangle([0, H - 22, W, H], fill=accent)
        target_h = int(H * 0.98)
        scale = target_h / char.height
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, H - nh + int(nh * 0.18)), c)
        tf = font(44)
        lines = wrap_text(d, topic, tf, W - 70)[:2]
        box_h = 32 + len(lines) * (tf.size + 10)
        d.rounded_rectangle([36, 48, W - 36, 48 + box_h], 28, fill=BLACK)
        y = 62
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 10
        return img
    if style == "board_hero":
        img = Image.new("RGB", (W, H), board)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 24], fill=accent)
        d.rectangle([0, H - 24, W, H], fill=accent)
        tf = font(76)
        lines = wrap_text(d, topic, tf, W - 50)[:3]
        total_h = len(lines) * (tf.size + 16)
        y = max(80, H // 2 - total_h // 2 - 120)
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 16
        target_h = int(H * 0.32)
        scale = target_h / char.height
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, H - nh - 50), c)
        return img
    if style == "side_teach":
        img = Image.new("RGB", (W, H), wall)
        d = ImageDraw.Draw(img)
        d.rectangle([int(W * 0.42), 0, W, H], fill=board)
        d.rectangle([int(W * 0.42), 0, int(W * 0.42) + 14, H], fill=accent)
        tf = font(50)
        lines = wrap_text(d, topic, tf, int(W * 0.52) - 40)[:4]
        y = H // 2 - 120
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            tw = bb[2] - bb[0]
            d.text((int(W * 0.42) + (int(W * 0.58) - tw) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 14
        target_h = int(H * 0.75)
        scale = target_h / char.height
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, (max(8, int(W * 0.21) - nw // 2), H - nh + 50), c)
        return img
    if style == "split_color":
        img = Image.new("RGB", (W, H), room["floor"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, int(H * 0.52)], fill=board)
        d.rectangle([0, int(H * 0.52) - 14, W, int(H * 0.52) + 14], fill=accent)
        tf = font(58)
        lines = wrap_text(d, topic, tf, W - 70)[:3]
        y = 90
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 14
        target_h = int(H * 0.52)
        scale = target_h / char.height
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, H - nh + 25), c)
        return img
    img = Image.new("RGB", (W, H), (10, 10, 16))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.58)], fill=board)
    d.rectangle([0, int(H * 0.58) - 14, W, int(H * 0.58) + 14], fill=accent)
    tf = font(68)
    lines = wrap_text(d, topic, tf, W - 60)[:3]
    y = 90
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
        y += tf.size + 16
    hf = font(28)
    for line in wrap_text(d, (hook or "")[:65], hf, W - 80)[:2]:
        bb = d.textbbox((0, 0), line, font=hf)
        d.text(((W - (bb[2] - bb[0])) // 2, y + 16), line, font=hf, fill=(210, 210, 220))
        y += hf.size + 8
    target_h = int(H * 0.48)
    scale = target_h / char.height
    nw, nh = int(char.width * scale), int(char.height * scale)
    c = char.resize((nw, nh), Image.Resampling.LANCZOS)
    img.paste(c, ((W - nw) // 2, H - nh + 28), c)
    return img


def camera_crop(full: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    fw, fh = full.size
    scale = 1.0 + 0.06 * ease
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    pan = 0.5 + 0.18 * math.sin(progress * math.pi * 1.2)
    ox = max(0.0, min(1.0, pan))
    oy = 0.14 + 0.06 * ease
    x = int(max_x * ox)
    y = int(max_y * max(0.0, min(1.0, oy)))
    return full.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def prepare_topic_image(path: Path) -> Image.Image | None:
    if not path.exists():
        return None
    try:
        im = Image.open(path).convert("RGB")
        return ImageOps.fit(im, (int(W * 1.45), int(H * 1.45)), method=Image.Resampling.LANCZOS)
    except Exception as e:
        print("topic image load fail", e, file=sys.stderr)
        return None


def ken_burns_frame(src: Image.Image, local_t: float, seg_dur: float, phase: str) -> Image.Image:
    p = min(1.0, max(0.0, local_t / max(seg_dur, 0.01)))
    ease = 0.5 - 0.5 * math.cos(p * math.pi)
    fw, fh = src.size
    if phase == "zoom_in":
        scale, ox, oy = 1.0 + 0.28 * ease, 0.5, 0.4
    elif phase == "zoom_out":
        scale, ox, oy = 1.28 - 0.28 * ease, 0.5, 0.45
    elif phase == "left":
        scale, ox, oy = 1.12 + 0.1 * ease, 0.08 + 0.35 * ease, 0.4
    elif phase == "right":
        scale, ox, oy = 1.12 + 0.1 * ease, 0.92 - 0.35 * ease, 0.4
    else:
        scale, ox, oy = 1.05 + 0.15 * ease, 0.5, 0.35 + 0.15 * ease
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * max(0.0, min(1.0, ox)))
    y = int(max_y * max(0.0, min(1.0, oy)))
    return src.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def image_window(duration: float):
    if duration < 14:
        return None
    start = duration * 0.26
    end = min(duration * 0.55, start + 11.0)
    return (start, end) if end - start >= 4.0 else None


def dyk_window(duration: float, img_win):
    if duration < 16:
        return None
    start = (img_win[1] + 0.15) if img_win else duration * 0.48
    end = min(start + 3.6, duration - 2.8)
    return (start, end) if end - start >= 2.5 else None


def cta_window(duration: float):
    return max(0.0, duration - 2.6), duration


def load_moves() -> list[dict]:
    for path in (Path("moves.json"), Path("script_job.json")):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if path.name == "script_job.json":
                data = data.get("moves") or []
            if isinstance(data, list) and len(data) >= 2:
                cleaned = []
                for m in data:
                    mv = m.get("move", "talk")
                    if mv in ("walk_left", "walk_right"):
                        mv = "talk"
                    cleaned.append({"at": float(m.get("at", 0)), "move": mv})
                return sorted(cleaned, key=lambda x: x["at"])
        except Exception:
            pass
    return [{"at": 0.0, "move": "question"}, {"at": 0.12, "move": "talk"}, {"at": 0.35, "move": "explain"},
            {"at": 0.55, "move": "point"}, {"at": 0.78, "move": "present"}, {"at": 0.92, "move": "happy"}]


def move_at(moves, t, duration):
    p = t / max(duration, 0.1)
    current = moves[0].get("move", "talk") if moves else "talk"
    for m in moves:
        if float(m.get("at", 0)) <= p:
            current = m.get("move", "talk")
        else:
            break
    return "talk" if current in ("walk_left", "walk_right") else current


def body_for(move, blink):
    if blink and move in ("talk", "present", "happy", "question", "explain", "lean"):
        return "body_blink.png"
    return {"welcome": "body_present.png", "talk": "body.png", "point": "arm_point.png", "sit": "body_sit.png",
            "present": "body_present.png", "question": "body_question.png", "happy": "body_happy.png",
            "explain": "body_explain.png", "shrug": "body_shrug.png", "count": "body_count.png",
            "think": "body_think.png", "lean": "body_lean.png"}.get(move, "body.png")


def composite_host(move, mouth_open, blink):
    body = load_rgba(body_for(move, blink))
    mouth = load_rgba(mouth_name(mouth_open))
    if mouth.size != body.size:
        mouth = mouth.resize(body.size, Image.Resampling.NEAREST)
    return Image.alpha_composite(body, mouth)


def word_windows(text, duration):
    words = [w for w in text.replace("\n", " ").split() if w]
    if not words:
        return [(0, duration, ["..."], 0)]
    slot, windows, i = duration / max(len(words), 1), [], 0
    while i < len(words):
        chunk = words[i:i + 5]
        start, end = i * slot, min(duration, (i + len(chunk)) * slot)
        for j in range(len(chunk)):
            windows.append((start + j * (end - start) / len(chunk), start + (j + 1) * (end - start) / len(chunk), chunk, j))
        i += len(chunk)
    return windows


def active_caption(windows, t):
    for ws, we, chunk, j in windows:
        if ws <= t < we:
            return chunk, j
    return (windows[-1][2], windows[-1][3]) if windows else ([""], 0)


def draw_fullscreen_dyk(base_rgb: Image.Image, dyk: str, accent) -> Image.Image:
    blurred = base_rgb.filter(ImageFilter.GaussianBlur(radius=18))
    blurred = Image.blend(blurred, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    d = ImageDraw.Draw(blurred)
    label_f = font(26)
    d.rounded_rectangle([W // 2 - 90, H // 2 - 220, W // 2 + 90, H // 2 - 170], 20, fill=accent)
    bb = d.textbbox((0, 0), "DID YOU KNOW", font=label_f)
    d.text((W // 2 - (bb[2] - bb[0]) // 2, H // 2 - 210), "DID YOU KNOW", font=label_f, fill=BLACK)
    tf = font(40)
    lines = wrap_text(d, dyk, tf, W - 120)[:6]
    box_h = 50 + len(lines) * (tf.size + 12)
    top = H // 2 - box_h // 2
    d.rounded_rectangle([40, top, W - 40, top + box_h], 28, fill=BLACK)
    y = top + 28
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
        y += tf.size + 12
    return blurred


def draw_fullscreen_cta(cta: str, topic: str, accent) -> Image.Image:
    img = Image.new("RGB", (W, H), (12, 10, 18))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 16], fill=accent)
    d.rectangle([0, H - 16, W, H], fill=accent)
    title_f = font(36)
    bb = d.textbbox((0, 0), (topic or "")[:32], font=title_f)
    d.text(((W - (bb[2] - bb[0])) // 2, H // 2 - 180), (topic or "")[:32], font=title_f, fill=(180, 180, 190))
    tf = font(48)
    lines = wrap_text(d, cta or "Comment what you understood", tf, W - 100)[:4]
    box_h = 48 + len(lines) * (tf.size + 14)
    top = H // 2 - box_h // 2
    d.rounded_rectangle([48, top, W - 48, top + box_h], 32, fill=accent)
    y = top + 28
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=BLACK)
        y += tf.size + 14
    sub = font(30)
    bb = d.textbbox((0, 0), "Follow for more", font=sub)
    d.text(((W - (bb[2] - bb[0])) // 2, top + box_h + 40), "Follow for more", font=sub, fill=WHITE)
    return img


def draw_karaoke(rgb, text, t, duration):
    d = ImageDraw.Draw(rgb)
    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(44)
    gaps, display, total = [], [], 0
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        if total + ww + 16 > W - 72 and display:
            break
        display.append(w)
        gaps.append(ww)
        total += ww + 16
    if not display:
        display, gaps, total = ["..."], [40], 40
    active = min(active, len(display) - 1)
    total = max(total - 16, 1)
    pad_x, pad_y = 28, 18
    box_w = total + pad_x * 2
    box_h = cf.size + pad_y * 2
    x0 = max(24, (W - box_w) // 2)
    y0 = H - 170
    d.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=box_h // 2, fill=BLACK)
    x = x0 + pad_x
    y = y0 + pad_y - 2
    for i, w in enumerate(display):
        d.text((x, y), w, font=cf, fill=WHITE if i == active else (175, 175, 180))
        x += gaps[i] + 16


def draw_topic_chip(rgb, topic: str, accent):
    d = ImageDraw.Draw(rgb)
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W - tw - 60, 24, W - 24, 78], 20, fill=accent)
    d.text((W - tw - 42, 38), label, font=af, fill=BLACK)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Lesson")
    p.add_argument("--bg", default="classroom")
    p.add_argument("--bg-image", default="")
    p.add_argument("--topic-image", default="topic_image.jpg")
    p.add_argument("--out", default="output.mp4")
    p.add_argument("--actions", default="")
    args = p.parse_args()
    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")
    dur_s = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio)], text=True).strip()
    duration = min(max(float(dur_s), 1.0), 90.0)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))
    moves = load_moves()
    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic
    definition = Path("definition.txt").read_text(encoding="utf-8").strip() if Path("definition.txt").exists() else ""
    dyk = Path("did_you_know.txt").read_text(encoding="utf-8").strip() if Path("did_you_know.txt").exists() else ""
    cta = Path("cta.txt").read_text(encoding="utf-8").strip() if Path("cta.txt").exists() else "Comment what you understood"
    hook = Path("hook.txt").read_text(encoding="utf-8").strip() if Path("hook.txt").exists() else ""
    if not hook:
        hook = (args.text or "").split(".")[0].strip()[:90]
    room = pick_room(topic)
    thumb = pick_thumb_style(topic)
    open_move = pick_open_move(topic)
    Path("thumb_style.txt").write_text(f"{thumb}|{room['id']}|{open_move}", encoding="utf-8")
    print("THUMB", thumb, "ROOM", room["id"], "OPEN_MOVE", open_move, file=sys.stderr)
    classroom = draw_classroom(topic, definition, room)
    topic_img = prepare_topic_image(Path(args.topic_image))
    img_win = image_window(duration) if topic_img is not None else None
    dyk_win = dyk_window(duration, img_win) if dyk else None
    cta_win = cta_window(duration)
    cta_frame = draw_fullscreen_cta(cta, topic, room["accent"])
    print(f"WINDOWS img={img_win} dyk={dyk_win} cta={cta_win[0]:.1f}-{cta_win[1]:.1f}", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            hook_phase = t < HOOK_END
            img_phase = bool(img_win and img_win[0] <= t < img_win[1])
            dyk_phase = bool(dyk_win and dyk_win[0] <= t < dyk_win[1])
            cta_phase = t >= cta_win[0]
            move = open_move if hook_phase else move_at(moves, t, duration)
            blink = (int(t * 2) % 10 == 0)
            char = composite_host(move, open_at(cues, t), blink)
            if cta_phase:
                rgb = cta_frame.copy()
            elif dyk_phase and dyk:
                base = camera_crop(classroom, t, duration)
                rgb = draw_fullscreen_dyk(base, dyk, room["accent"])
            elif hook_phase:
                rgb = draw_thumb_frame(thumb, topic, hook, room, char)
            elif img_phase and topic_img is not None and img_win:
                local = t - img_win[0]
                seg = img_win[1] - img_win[0]
                q = seg / 4.0
                if local < q:
                    phase, lt, ld = "left", local, q
                elif local < 2 * q:
                    phase, lt, ld = "zoom_in", local - q, q
                elif local < 3 * q:
                    phase, lt, ld = "right", local - 2 * q, q
                else:
                    phase, lt, ld = "zoom_out", local - 3 * q, q
                rgb = ken_burns_frame(topic_img, lt, ld, phase)
                draw_topic_chip(rgb, topic, room["accent"])
            else:
                frame = camera_crop(classroom, t, duration).convert("RGBA")
                target_h = int(H * 0.32)
                scale = target_h / char.height
                nw, nh = int(char.width * scale), int(char.height * scale)
                c = char.resize((nw, nh), Image.Resampling.LANCZOS)
                bob = int(5 * math.sin(t * 4.2))
                x = (W - nw) // 2
                if move == "point":
                    x = int(W * 0.22)
                y = H - nh - 140 + bob
                frame.paste(c, (x, y), c)
                rgb = frame.convert("RGB")
                draw_topic_chip(rgb, topic, room["accent"])
                draw_karaoke(rgb, args.text, t, duration)
            rgb.save(tmp_path / f"frame_{i:05d}.png")
        out_mp4 = Path(args.out).resolve()
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(tmp_path / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4),
        ])
        print("OK", out_mp4, out_mp4.stat().st_size)


if __name__ == "__main__":
    main()
