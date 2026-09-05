#!/usr/bin/env python3
"""Classroom + large board (+ optional ref images on board) + host + captions."""
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
ACCENT = (255, 196, 40)
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


def load_board_refs() -> list[Image.Image]:
    imgs = []
    p = Path("board_refs.txt")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            fp = Path(line.strip())
            if fp.exists():
                try:
                    imgs.append(Image.open(fp).convert("RGB"))
                except Exception:
                    pass
    for fp in sorted(Path("assets/board").glob("ref*.jpg")) if Path("assets/board").exists() else []:
        try:
            imgs.append(Image.open(fp).convert("RGB"))
        except Exception:
            pass
    return imgs[:2]


def draw_classroom(topic: str) -> Image.Image:
    img = Image.new("RGB", (W, H), (245, 236, 220))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.72)], fill=(232, 222, 205))
    d.rectangle([0, int(H * 0.72), W, H], fill=(166, 140, 105))
    d.line([(0, int(H * 0.72)), (W, int(H * 0.72))], fill=(140, 115, 85), width=3)

    bx0, by0, bx1, by1 = 28, 56, W - 28, int(H * 0.50)
    d.rounded_rectangle([bx0 - 10, by0 - 10, bx1 + 10, by1 + 10], 14, fill=(90, 70, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 10, fill=(34, 85, 55))

    # topic title on board
    tf = font(36)
    words = (topic or "Lesson").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > (bx1 - bx0 - 36):
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = by0 + 20
    for line in lines[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(245, 250, 240))
        y += 42

    # reference images pinned on board
    refs = load_board_refs()
    if refs:
        slot_w = (bx1 - bx0 - 48) // max(len(refs), 1)
        slot_h = min(160, by1 - y - 24)
        for i, ref in enumerate(refs):
            rw = slot_w - 12
            rh = slot_h
            thumb = ref.copy()
            thumb.thumbnail((rw, rh))
            px = bx0 + 24 + i * slot_w + (rw - thumb.width) // 2
            py = y + 8
            # white frame
            d.rectangle([px - 4, py - 4, px + thumb.width + 4, py + thumb.height + 4], fill=(240, 240, 235))
            img.paste(thumb, (px, py))
    else:
        d.line([bx0 + 24, by1 - 24, bx1 - 24, by1 - 24], fill=(200, 220, 200), width=2)

    d.rectangle([bx0, by1 + 4, bx1, by1 + 16], fill=(120, 95, 60))
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
        chunk = words[i : i + 6]
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
    af = font(14)
    label = f"QX · {action.upper()}"
    d.rounded_rectangle([W - 160, 20, W - 16, 52], 10, fill=ACCENT)
    d.text((W - 150, 26), label, font=af, fill=BLACK)

    windows = word_windows(text, duration)
    chunk, active = active_caption(windows, t)
    cf = font(30)
    max_w = W - 48
    gaps, display, total = [], [], 0
    for w in chunk:
        bb = d.textbbox((0, 0), w, font=cf)
        ww = bb[2] - bb[0]
        if total + ww + 10 > max_w and display:
            break
        display.append(w)
        gaps.append(ww)
        total += ww + 10
    if not display:
        display, gaps, total = ["..."], [30], 30
    active = min(active, len(display) - 1)
    total = max(total - 10, 1)
    x0 = max(24, (W - total) // 2)
    y = H - 120
    d.rounded_rectangle([18, y - 14, W - 18, y + 52], 14, fill=(12, 12, 20))
    x = x0
    for i, w in enumerate(display):
        if i == active:
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                d.text((x + ox, y + oy), w, font=cf, fill=GLOW)
            d.text((x, y), w, font=cf, fill=WHITE)
        else:
            d.text((x, y), w, font=cf, fill=(175, 175, 185))
        x += gaps[i] + 10


def composite_host(action: str, mouth_open: float) -> Image.Image:
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
    p.add_argument("--title", default="Lesson")
    p.add_argument("--bg", default="classroom")
    p.add_argument("--bg-image", default="")
    p.add_argument("--out", default="output.mp4")
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
    duration = min(max(float(dur_s), 1.0), 55.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic

    base = draw_classroom(topic)
    print(f"board scene duration={duration:.2f}s frames={n}")

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
            char = composite_host(action, mouth)
            target_h = int(H * 0.40)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)
            bob = int(3 * math.sin(phase * 2))
            x_off = int(-50 + 100 * ((t * 0.3) % 1.0)) if action == "walk" else (36 if action == "point" else 0)
            x = (W - nw) // 2 + x_off
            y = H - nh - 140 + bob
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
