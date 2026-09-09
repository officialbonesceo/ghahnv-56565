#!/usr/bin/env python3
"""Mike + clean studio BG + lips + AI moves."""
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
        print("NO mouth.json cues", file=sys.stderr)
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


def topic_world(topic: str) -> str:
    t = (topic or "").lower()
    if re.search(r"star|sun|moon|planet|space|galaxy|solar|telescope", t):
        return "space"
    if re.search(r"ocean|water|rain|cloud|storm", t):
        return "sky"
    if re.search(r"tree|plant|leaf|forest", t):
        return "nature"
    if re.search(r"atom|chem|electric|sound|wave|ai|model", t):
        return "lab"
    return "stage"


def secondary_world(primary: str) -> str:
    order = ["space", "sky", "nature", "lab", "stage"]
    if primary in order:
        return order[(order.index(primary) + 1) % len(order)]
    return "space"


def draw_classroom(topic: str, definition: str = "", cta: str = "") -> Image.Image:
    """Clean vertical studio — board top-center, wall, floor, Mike stands in open space."""
    # Exact frame size so camera does not crop weirdly
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (18, 32, 58))
    d = ImageDraw.Draw(img)

    # soft vertical gradient
    for i in range(20):
        y0 = int(bh * i / 20)
        y1 = int(bh * (i + 1) / 20)
        shade = 16 + i
        d.rectangle([0, y0, bw, y1], fill=(shade, 28 + i // 2, 52 + i))

    # left accent bar (neon strip)
    d.rectangle([0, 0, 14, bh], fill=ACCENT)
    d.rectangle([14, 0, 18, bh], fill=(255, 220, 100))

    # small SCI/TECH/AI label top-left
    nf = font(22)
    d.text((36, 36), "SCIENCE", font=nf, fill=(140, 220, 255))
    d.text((36, 62), "TECH · AI", font=nf, fill=(140, 220, 255))

    # ===== MAIN BOARD (centered upper third) =====
    bx0, by0 = 90, 100
    bx1, by1 = bw - 90, 480
    # outer frame
    d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 18, fill=(30, 40, 60))
    # board face
    d.rounded_rectangle([bx0, by0, bx1, by1], 14, fill=(16, 70, 62))
    # cyan left edge
    d.rectangle([bx0, by0 + 8, bx0 + 8, by1 - 8], fill=(80, 210, 255))

    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(58)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 60) and tf.size > 28:
        tf = font(tf.size - 3)
    y = by0 + 36
    for line in wrap_text(d, topic, tf, bx1 - bx0 - 60)[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(240, 255, 250))
        y += tf.size + 10

    if definition:
        df = font(28)
        y += 12
        for line in wrap_text(d, definition, df, bx1 - bx0 - 60)[:4]:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=(170, 220, 205))
            y += df.size + 6

    cta = cta or "Comment YES for part 2"
    cf = font(26)
    bar_y0, bar_y1 = by1 - 70, by1 - 18
    d.rounded_rectangle([bx0 + 40, bar_y0, bx1 - 40, bar_y1], 14, fill=ACCENT)
    bb = d.textbbox((0, 0), cta, font=cf)
    tw = bb[2] - bb[0]
    d.text((bx0 + (bx1 - bx0 - tw) // 2, bar_y0 + 12), cta, font=cf, fill=BLACK)

    # wall panel under board (empty stage area for character)
    d.rectangle([0, by1 + 20, bw, int(bh * 0.78)], fill=(14, 26, 48))

    # subtle floor ellipse / stage ring
    d.ellipse(
        [int(bw * 0.12), int(bh * 0.82), int(bw * 0.88), int(bh * 0.98)],
        outline=(255, 190, 50), width=3,
    )
    # floor
    d.rectangle([0, int(bh * 0.88), bw, bh], fill=(10, 16, 30))

    return img


def draw_stage() -> Image.Image:
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (10, 22, 48))
    d = ImageDraw.Draw(img)
    for i in range(16):
        y0 = int(bh * i / 16)
        d.rectangle([0, y0, bw, int(bh * (i + 1) / 16)], fill=(10 + i, 20 + i, 42 + i * 2))
    d.ellipse([int(bw * 0.12), int(bh * 0.82), int(bw * 0.88), int(bh * 0.98)], outline=(255, 200, 60), width=3)
    d.rectangle([0, int(bh * 0.9), bw, bh], fill=(8, 12, 24))
    return img


def draw_space() -> Image.Image:
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (6, 8, 24))
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(320):
        x, y = rng.randint(0, bw - 1), rng.randint(0, int(bh * 0.85))
        r = rng.randint(1, 3)
        d.ellipse([x, y, x + r, y + r], fill=(240, 245, 255))
    d.ellipse([bw - 200, 80, bw - 80, 200], fill=(255, 245, 180))
    d.rectangle([0, int(bh * 0.9), bw, bh], fill=(4, 6, 16))
    return img


def draw_sky() -> Image.Image:
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (120, 175, 230))
    d = ImageDraw.Draw(img)
    d.ellipse([bw - 220, 40, bw - 60, 180], fill=(255, 230, 120))
    d.rectangle([0, int(bh * 0.75), bw, bh], fill=(70, 140, 80))
    return img


def draw_nature() -> Image.Image:
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (140, 190, 150))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.55)], fill=(120, 180, 230))
    d.rectangle([0, int(bh * 0.55), bw, bh], fill=(50, 110, 55))
    return img


def draw_lab() -> Image.Image:
    bw, bh = W + 80, H + 80
    img = Image.new("RGB", (bw, bh), (12, 22, 48))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([bw // 2 - 220, 120, bw // 2 + 220, 380], 16, fill=(10, 20, 40))
    d.text((bw // 2 - 50, 220), "AI", font=font(72), fill=(80, 200, 255))
    d.ellipse([int(bw * 0.12), int(bh * 0.82), int(bw * 0.88), int(bh * 0.98)], outline=ACCENT, width=3)
    return img


def make_bg(kind: str, topic: str = "", definition: str = "", cta: str = "") -> Image.Image:
    if kind == "classroom":
        return draw_classroom(topic, definition, cta)
    return {
        "space": draw_space, "sky": draw_sky, "nature": draw_nature,
        "lab": draw_lab, "stage": draw_stage,
    }.get(kind, draw_stage)()


def camera_crop(full: Image.Image, t: float, duration: float, mode: str) -> Image.Image:
    """Gentle Ken Burns — keep board readable, less aggressive crop."""
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    fw, fh = full.size
    # mild zoom only so board + character stay in frame
    if mode == "close":
        scale, ox, oy = 1.06, 0.5, 0.42
    elif mode == "left":
        scale, ox, oy = 1.04, 0.35 + 0.08 * ease, 0.45
    elif mode == "right":
        scale, ox, oy = 1.04, 0.55 - 0.08 * ease, 0.45
    elif mode == "pan":
        scale, ox, oy = 1.03 + 0.03 * ease, 0.35 + 0.3 * ease, 0.45
    else:
        scale, ox, oy = 1.0 + 0.04 * ease, 0.5, 0.45
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
                moves = sorted(data, key=lambda x: float(x.get("at", 0)))
                print("MOVES FROM", path, moves, file=sys.stderr)
                return moves
        except Exception as e:
            print("moves load err", path, e, file=sys.stderr)
    default = [
        {"at": 0.0, "move": "welcome"},
        {"at": 0.12, "move": "talk"},
        {"at": 0.28, "move": "walk_left"},
        {"at": 0.4, "move": "point"},
        {"at": 0.55, "move": "question"},
        {"at": 0.7, "move": "sit"},
        {"at": 0.85, "move": "present"},
    ]
    print("MOVES DEFAULT", default, file=sys.stderr)
    return default


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
    if p < 0.28:
        return "classroom"
    if p < 0.62:
        return "world"
    return "world2"


def cam_for(move: str, p: float) -> str:
    if move == "walk_left":
        return "left"
    if move == "walk_right":
        return "right"
    if move == "point":
        return "right"
    if move == "sit":
        return "close"
    if move == "present":
        return "wide"
    if p < 0.12:
        return "close"
    if p > 0.82:
        return "wide"
    return "pan"


def body_for(move: str, t: float, blink: bool) -> str:
    if blink and move in ("talk", "welcome", "present", "happy", "question"):
        return "body_blink.png"
    if move in ("walk_left", "walk_right"):
        phase = int(t * 8) % 2
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
    if move in ("walk_left", "walk_right"):
        return body
    mouth = load_rgba(mouth_name(mouth_open))
    if mouth.size != body.size:
        mouth = mouth.resize(body.size, Image.Resampling.NEAREST)
    return Image.alpha_composite(body, mouth)


def draw_chair(frame: Image.Image, cx: int, seat_y: int) -> None:
    d = ImageDraw.Draw(frame)
    wood, wood_d = (50, 55, 70), (35, 40, 55)
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
    # topic chip only if not already big on board (keep light)
    if 0.48 <= p <= 0.66 and dyk:
        df = font(30)
        lines = wrap_text(d, "Did you know? " + dyk, df, W - 100)[:4]
        box_h = 40 + len(lines) * (df.size + 8)
        d.rounded_rectangle([40, 120, W - 40, 120 + box_h], 16, fill=(12, 18, 35))
        y = 140
        for line in lines:
            d.text((60, y), line, font=df, fill=WHITE)
            y += df.size + 8
    if p >= 0.78:
        cf = font(32)
        msg = cta or "Comment YES for part 2"
        bb = d.textbbox((0, 0), msg, font=cf)
        tw = bb[2] - bb[0]
        d.rounded_rectangle([W // 2 - tw // 2 - 28, 100, W // 2 + tw // 2 + 28, 160], 16, fill=ACCENT)
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
            if 0.26 <= pfrac <= 0.30:
                base_full = Image.blend(bg_class, bg_w1, (pfrac - 0.26) / 0.04)
            elif 0.60 <= pfrac <= 0.64:
                base_full = Image.blend(bg_w1, bg_w2, (pfrac - 0.60) / 0.04)

            frame = camera_crop(base_full, t, duration, cam).convert("RGBA")
            mouth = open_at(cues, t)
            char = composite_host(move, mouth, blink, t)
            target_h = int(H * (0.50 if cam == "close" else 0.46))
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)

            bob = int(3 * math.sin(t * 6))
            if move == "walk_left":
                walk_moves = [m for m in moves if m.get("move") == "walk_left"]
                start_p = float(walk_moves[0]["at"]) if walk_moves else 0.28
                local = max(0.0, min(1.0, (pfrac - start_p) / 0.14))
                x = int(W * 0.62 - local * W * 0.35)
                bob = int(10 * abs(math.sin(local * math.pi * 4)))
            elif move == "walk_right":
                walk_moves = [m for m in moves if m.get("move") == "walk_right"]
                start_p = float(walk_moves[0]["at"]) if walk_moves else 0.28
                local = max(0.0, min(1.0, (pfrac - start_p) / 0.14))
                x = int(W * 0.2 + local * W * 0.35)
                bob = int(10 * abs(math.sin(local * math.pi * 4)))
            elif move == "point":
                x = int(W * 0.28)
            elif move == "sit":
                x = (W - nw) // 2
                bob = 0
                draw_chair(frame, W // 2, H - 200 - int(nh * 0.25))
            else:
                x = (W - nw) // 2

            # stand on floor, clear of captions
            y = H - nh - 200 + bob
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
