#!/usr/bin/env python3
"""MEZI sprite compositor: body + mouth layers + bg + Ken Burns."""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
FPS = 12
HOODIE = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (28, 24, 30)
MOUTH = {
    "X": 0.02, "A": 1.0, "B": 0.08, "C": 0.55,
    "D": 0.7, "E": 0.85, "F": 0.4, "G": 0.9, "H": 1.0,
}
ALL_ACTIONS = ["talk", "walk", "point", "laugh"]


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "mezi"


def load_rgba(name: str) -> Image.Image:
    p = asset_dir() / name
    if not p.exists():
        raise SystemExit(f"missing sprite {p} - run scripts/write_mezi_assets.py")
    return Image.open(p).convert("RGBA")


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def open_at(cues, t: float) -> float:
    if not cues:
        return 0.05 + 0.8 * max(0.0, math.sin(t * 14))
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return MOUTH.get(str(c["value"]).upper(), 0.45)
    return 0.02


def mouth_sprite(open_amt: float) -> str:
    if open_amt >= 0.7:
        return "mouth_wide.png"
    if open_amt >= 0.25:
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


def make_bg(kind: str) -> Image.Image:
    bw, bh = int(W * 1.2), int(H * 1.2)
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    k = (kind or "studio").lower().strip()
    rnd = random.Random(hash(k) & 0xFFFFFFFF)
    if k == "space":
        for y in range(bh):
            c = 6 + y // 80
            d.line([(0, y), (bw, y)], fill=(c, c + 2, 18 + c))
        for _ in range(220):
            x, y = rnd.randint(0, bw - 1), rnd.randint(0, bh - 1)
            r = rnd.choice([1, 1, 2, 2, 3])
            b = rnd.randint(180, 255)
            d.ellipse([x, y, x + r, y + r], fill=(b, b, 255))
        d.ellipse([bw - 280, 120, bw - 40, 360], fill=(50, 80, 160))
    elif k == "ocean":
        for y in range(int(bh * 0.42)):
            d.line([(0, y), (bw, y)], fill=(120 + y // 30, 190, 235))
        for y in range(int(bh * 0.42), bh):
            depth = y - int(bh * 0.42)
            d.line([(0, y), (bw, y)], fill=(15, 70 + depth // 20, 120))
    elif k == "money":
        d.rectangle([0, 0, bw, bh], fill=(236, 250, 236))
        d.rectangle([0, int(bh * 0.68), bw, bh], fill=(25, 110, 65))
    elif k == "tech":
        d.rectangle([0, 0, bw, bh], fill=(12, 18, 32))
        for x in range(0, bw, 40):
            d.line([(x, 0), (x, bh)], fill=(25, 40, 60))
        for i in range(12):
            x = 40 + i * 60
            d.rectangle([x, 160, x + 40, 280], outline=(0, 220, 255), width=2)
    elif k == "science":
        d.rectangle([0, 0, bw, bh], fill=(220, 238, 255))
        d.ellipse([bw - 260, 40, bw - 40, 260], fill=(255, 210, 70))
        d.rectangle([0, int(bh * 0.72), bw, bh], fill=(160, 210, 160))
    else:
        d.rectangle([0, 0, bw, int(bh * 0.6)], fill=(245, 240, 230))
        d.rectangle([0, int(bh * 0.6), bw, bh], fill=(200, 190, 175))
        d.rounded_rectangle([60, 80, 300, 320], 20, fill=(160, 210, 245), outline=(100, 140, 170), width=5)
    return img


def crop_ken_burns(bg: Image.Image, t: float, duration: float) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    scale = 1.0 + 0.12 * progress
    bw, bh = bg.size
    cw, ch = min(int(W * scale), bw), min(int(H * scale), bh)
    max_x, max_y = max(0, bw - cw), max(0, bh - ch)
    x = int(max_x * progress * 0.85)
    y = int(max_y * 0.5 * (0.3 + 0.7 * math.sin(progress * math.pi)))
    return bg.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.BILINEAR)


def composite_mezi(action: str, mouth_open: float) -> Image.Image:
    body = load_rgba("arm_point.png" if action == "point" else "body.png")
    mouth = load_rgba(mouth_sprite(mouth_open))
    char = Image.alpha_composite(body, mouth)
    if action == "laugh":
        char = Image.alpha_composite(char, load_rgba("eyes_laugh.png"))
    return char


def draw_ui(d, text, action, title):
    f = font(26)
    t = (title or "Mezi")[:36]
    bb = d.textbbox((0, 0), t, font=f)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([24, 36, 36 + tw + 20, 84], 14, fill=(0, 0, 0))
    d.text((36, 46), t, font=f, fill=WHITE)
    cf = font(24)
    words = " ".join(text.split()).split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=cf)[2] > W - 80:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    lines = lines[:5]
    box_h = 28 + len(lines) * 30
    d.rounded_rectangle([24, H - box_h - 36, W - 24, H - 28], 18, fill=(18, 18, 26))
    y = H - box_h - 20
    for line in lines:
        d.text((40, y), line, font=cf, fill=WHITE)
        y += 30
    af = font(16)
    label = f"MEZI · {action.upper()}"
    d.rounded_rectangle([W - 190, 44, W - 24, 82], 12, fill=HOODIE)
    d.text((W - 178, 52), label, font=af, fill=BLACK)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default="")
    p.add_argument("--text", required=True)
    p.add_argument("--title", default="Mezi")
    p.add_argument("--bg", default="studio")
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
    bg_full = make_bg(args.bg)
    print(f"SPRITE mode duration={duration:.2f}s frames={n} bg={args.bg} cues={len(cues)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            action = action_at(t, duration, actions)
            phase = t * (2.5 if action == "walk" else 1.2)
            frame = crop_ken_burns(bg_full, t, duration).convert("RGBA")
            mouth = open_at(cues, t)
            if action == "laugh":
                mouth = max(mouth, 0.85)
            char = composite_mezi(action, mouth)
            target_h = int(H * 0.55)
            scale = target_h / char.height
            nw, nh = int(char.width * scale), int(char.height * scale)
            char = char.resize((nw, nh), Image.Resampling.LANCZOS)
            bob = int(6 * math.sin(phase * 3))
            x_off = int(28 * math.sin(t * 1.5)) if action == "walk" else 0
            x = (W - nw) // 2 + x_off
            y = int(H * 0.22) + bob
            frame.paste(char, (x, y), char)
            rgb = frame.convert("RGB")
            draw_ui(ImageDraw.Draw(rgb), args.text, action, args.title)
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
