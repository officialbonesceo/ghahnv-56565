#!/usr/bin/env python3
"""Mike classroom: big board title, Ken Burns pan, captions."""
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


def action_at(t, duration, actions):
    seg = duration / max(1, len(actions))
    return actions[min(int(t / seg), len(actions) - 1)]


def draw_classroom_large(topic: str) -> Image.Image:
    """Draw larger than frame so Ken Burns can pan/zoom."""
    bw, bh = int(W * 1.15), int(H * 1.12)
    img = Image.new("RGB", (bw, bh), (245, 236, 220))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, int(bh * 0.72)], fill=(232, 222, 205))
    d.rectangle([0, int(bh * 0.72), bw, bh], fill=(166, 140, 105))

    bx0, by0 = 40, 70
    bx1, by1 = bw - 40, int(bh * 0.48)
    d.rounded_rectangle([bx0 - 12, by0 - 12, bx1 + 12, by1 + 12], 16, fill=(90, 70, 45))
    d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=(34, 85, 55))

    # Large chalk title — always visible
    topic = (topic or "Today's lesson").strip() or "Today's lesson"
    tf = font(52)
    # fit title
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
    y = by0 + 36
    for line in lines[:3]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        # chalk-ish shadow
        d.text((bx0 + (bx1 - bx0 - tw) // 2 + 2, y + 2), line, font=tf, fill=(20, 50, 35))
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=(250, 255, 245))
        y += tf.size + 14

    # simple drawn icons instead of broken AI images
    icon_y = y + 20
    if icon_y + 100 < by1:
        d.ellipse([bx0 + 50, icon_y, bx0 + 130, icon_y + 80], outline=(200, 230, 200), width=4)
        d.line([bx0 + 180, icon_y + 40, bx0 + 280, icon_y + 40], fill=(200, 230, 200), width=4)
        d.polygon(
            [(bx0 + 320, icon_y + 70), (bx0 + 360, icon_y + 10), (bx0 + 400, icon_y + 70)],
            outline=(200, 230, 200),
        )

    d.rectangle([bx0, by1 + 4, bx1, by1 + 18], fill=(120, 95, 60))
    return img


def ken_crop(full: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    scale = 1.0 + 0.08 * ease  # subtle zoom
    fw, fh = full.size
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * ease * 0.9)
    y = int(max_y * (1 - ease) * 0.5)
    return full.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def word_windows(text: str, duration: float):
    words = [w for w in text.replace("\n", " ").split() if w]
    if not words:
        return [(0, duration, ["..."], 0)]
    n = len(words)
    slot = duration / max(n, 1)
    windows, i = [], 0
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
    label = f"MIKE · {action.upper()}"
    d.rounded_rectangle([W - 175, 20, W - 16, 52], 10, fill=ACCENT)
    d.text((W - 165, 26), label, font=af, fill=BLACK)

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
    duration = min(max(float(dur_s), 1.0), 70.0)
    actions = [a.strip().lower() for a in args.actions.split(",") if a.strip()]
    actions = [a if a in ALL_ACTIONS else "talk" for a in actions] or list(ALL_ACTIONS)
    cues = load_cues(Path(args.cues)) if args.cues else []
    n = max(FPS, int(math.ceil(duration * FPS)))

    topic = args.title
    if Path("title_short.txt").exists():
        topic = Path("title_short.txt").read_text(encoding="utf-8").strip() or topic

    full_bg = draw_classroom_large(topic)
    print(f"mike board duration={duration:.2f}s frames={n} topic={topic!r}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * 3.0 if action == "walk" else t * 1.2
            frame = ken_crop(full_bg, t, duration).convert("RGBA")
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.8)
            char = composite_host(action, mouth)
            target_h = int(H * 0.40)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)
            bob = int(3 * math.sin(phase * 2))
            x_off = int(-40 + 80 * ((t * 0.25) % 1.0)) if action == "walk" else (30 if action == "point" else 0)
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
