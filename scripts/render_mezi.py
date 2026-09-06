#!/usr/bin/env python3
"""Mike: classroom -> walk -> world point -> sit on chair -> present. Topic badge, no pose label."""
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
    if pose in ("present", "welcome") and open_amt < 0.25:
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
    img = Image.new("RGB", (W, H), (230, 220, 200))
    d = ImageDraw.Draw(img)
    # wall + floor
    d.rectangle([0, 0, W, int(H * 0.70)], fill=(242, 234, 218))
    d.rectangle([0, int(H * 0.70), W, H], fill=(140, 110, 75))
    # floor shadow band
    d.rectangle([0, int(H * 0.70), W, int(H * 0.72)], fill=(120, 95, 65))
    # windows with panes + sky
    for i in range(2):
        x0 = 50 + i * 210
        d.rounded_rectangle([x0, 50, x0 + 160, 200], 8, fill=(90, 75, 55))
        d.rectangle([x0 + 10, 60, x0 + 150, 190], fill=(160, 200, 235))
        d.line([x0 + 80, 60, x0 + 80, 190], fill=(90, 75, 55), width=4)
        d.line([x0 + 10, 125, x0 + 150, 125], fill=(90, 75, 55), width=4)
    # bookshelf
    d.rectangle([W - 160, 80, W - 40, 280], fill=(100, 70, 45))
    for row in range(3):
        y = 100 + row * 55
        d.rectangle([W - 150, y, W - 50, y + 8], fill=(80, 55, 35))
        for b in range(3):
            d.rectangle(
                [W - 145 + b * 30, y + 12, W - 125 + b * 30, y + 45],
                fill=(180 + b * 20, 80, 70),
            )
    # big board
    bx0, by0, bx1, by1 = 50, 220, W - 180, int(H * 0.44)
    d.rounded_rectangle([bx0 - 14, by0 - 14, bx1 + 14, by1 + 14], 16, fill=(85, 65, 40))
    d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=(28, 78, 48))
    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(60)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 50) and tf.size > 30:
        tf = font(tf.size - 3)
    words = topic.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 50):
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = by0 + 45
    for line in lines[:3]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2 + 2, y + 2), line, font=tf, fill=(15, 40, 25))
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(245, 250, 240))
        y += tf.size + 12
    d.rectangle([bx0, by1 + 4, bx1, by1 + 18], fill=(115, 90, 55))
    # teacher desk
    d.rounded_rectangle(
        [W // 2 - 200, int(H * 0.62), W // 2 + 200, int(H * 0.68)],
        10,
        fill=(115, 85, 50),
    )
    d.rectangle(
        [W // 2 - 190, int(H * 0.64), W // 2 + 190, int(H * 0.66)],
        fill=(140, 105, 65),
    )
    return img


def draw_space() -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 10, 28))
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    for _ in range(180):
        x, y = rng.randint(0, W - 1), rng.randint(0, int(H * 0.75))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    # planet / sun to point at
    sx, sy = int(W * 0.74), int(H * 0.20)
    d.ellipse([sx - 40, sy - 40, sx + 40, sy + 40], fill=(255, 245, 180))
    d.ellipse([sx - 18, sy - 18, sx + 18, sy + 18], fill=(255, 255, 230))
    d.rectangle([0, int(H * 0.78), W, H], fill=(12, 14, 32))
    return img


def draw_sky() -> Image.Image:
    img = Image.new("RGB", (W, H), (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.ellipse([int(W * 0.68), int(H * 0.06), int(W * 0.92), int(H * 0.2)], fill=(255, 230, 120))
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


def draw_chair(frame: Image.Image, cx: int, seat_y: int, scale: float = 1.0) -> None:
    """Full chair under Mike (not a stick)."""
    d = ImageDraw.Draw(frame)
    wood = (120, 85, 50)
    wood_d = (90, 60, 35)
    w = int(160 * scale)
    h_seat = int(18 * scale)
    leg = int(70 * scale)
    back_h = int(90 * scale)
    # seat
    d.rounded_rectangle([cx - w // 2, seat_y, cx + w // 2, seat_y + h_seat], 6, fill=wood)
    # back
    d.rounded_rectangle(
        [cx - w // 2, seat_y - back_h, cx - w // 2 + int(18 * scale), seat_y + h_seat],
        6,
        fill=wood_d,
    )
    d.rounded_rectangle(
        [cx + w // 2 - int(18 * scale), seat_y - back_h, cx + w // 2, seat_y + h_seat],
        6,
        fill=wood_d,
    )
    d.rectangle(
        [cx - w // 2, seat_y - back_h, cx + w // 2, seat_y - back_h + int(14 * scale)],
        fill=wood,
    )
    # legs
    for lx in (cx - w // 2 + 8, cx + w // 2 - 18):
        d.rectangle([lx, seat_y + h_seat, lx + 10, seat_y + h_seat + leg], fill=wood_d)


def beat(t: float, duration: float) -> str:
    p = t / max(duration, 0.1)
    if p < 0.15:
        return "welcome"
    if p < 0.28:
        return "board_talk"
    if p < 0.40:
        return "walk_left"
    if p < 0.58:
        return "world_point"
    if p < 0.72:
        return "sit"
    return "present"


def body_for(pose: str, blink: bool, t: float) -> str:
    if blink and pose in ("board_talk", "welcome", "present"):
        return "body_blink.png"
    if pose == "walk_left":
        # alternate side frames for less stiff walk
        return "body_side_left.png" if int(t * 6) % 2 == 0 else "body_side_right.png"
    return {
        "welcome": "body_present.png",
        "board_talk": "body.png",
        "world_point": "arm_point.png",
        "sit": "body_sit.png",
        "present": "body_happy.png",
    }.get(pose, "body.png")


def composite_host(pose: str, mouth_open: float, blink: bool, t: float) -> Image.Image:
    body = load_rgba(body_for(pose, blink, t))
    # Never overlay mouth on side / sit (wrong head Y → hole beside face)
    if pose in ("walk_left", "sit"):
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


def draw_ui(rgb, text, t, duration, topic: str):
    d = ImageDraw.Draw(rgb)
    # Topic of the day (not pose label)
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    pad = 18
    d.rounded_rectangle(
        [W - tw - pad * 2 - 24, 24, W - 24, 78],
        14,
        fill=ACCENT,
    )
    d.text((W - tw - pad - 24, 38), label, font=af, fill=BLACK)

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
    print(f"Mike board->{world} duration={duration:.2f}s frames={n}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            pose = beat(t, duration)
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 9 == 0)

            if pose == "walk_left":
                walk_p = max(0.0, min(1.0, (pfrac - 0.28) / 0.12))
                base = Image.blend(bg_board, bg_world, walk_p)
            elif pose in ("world_point", "sit", "present"):
                base = bg_world.copy()
            else:
                base = bg_board.copy()

            frame = base.convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(pose, mouth, blink, t)
            target_h = int(H * 0.46)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(3 * math.sin(t * 7))
            if pose == "walk_left":
                walk_p = max(0.0, min(1.0, (pfrac - 0.28) / 0.12))
                x = int((W - nw) // 2 - walk_p * (W * 0.32))
                bob = int(8 * abs(math.sin(t * 10)))
            elif pose == "world_point":
                x = int(W * 0.22)
                bob = int(2 * math.sin(t * 5))
            elif pose == "sit":
                x = (W - nw) // 2
                bob = 0
                # chair appears under him
                seat_y = H - 210 - int(nh * 0.28)
                draw_chair(frame, W // 2, seat_y, scale=1.15)
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
