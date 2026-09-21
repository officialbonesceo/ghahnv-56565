#!/usr/bin/env python3
"""Mike: modern classroom, karaoke white-on-black curved captions, optional image beat."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1920
FPS = 24
HOOK_END = 2.0
# New palette — warm modern studio, not grey lab
ACCENT = (255, 180, 50)
WALL = (255, 244, 230)
WALL_DEEP = (255, 236, 214)
FLOOR = (62, 48, 40)
BOARD = (18, 72, 92)
BOARD_FRAME = (28, 36, 48)
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)
GLOW = (255, 255, 255)
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
    """Warm modern classroom — cream walls, teal board, wood floor, new layout."""
    bw, bh = int(W * 1.18), int(H * 1.14)
    img = Image.new("RGB", (bw, bh), WALL)
    d = ImageDraw.Draw(img)

    # Upper wall band + lower wall
    d.rectangle([0, 0, bw, int(bh * 0.68)], fill=WALL)
    d.rectangle([0, int(bh * 0.68), bw, bh], fill=FLOOR)
    # Skirting
    d.rectangle([0, int(bh * 0.68) - 14, bw, int(bh * 0.68)], fill=ACCENT)

    # Tall window on the LEFT (new place)
    wx0, wy0, wx1, wy1 = 28, 48, 210, 320
    d.rounded_rectangle([wx0, wy0, wx1, wy1], 14, fill=(160, 200, 230))
    d.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=WHITE, width=4)
    d.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=WHITE, width=4)
    d.rounded_rectangle([wx0 - 4, wy0 - 4, wx1 + 4, wy1 + 4], 16, outline=(90, 70, 55), width=5)

    # Poster strip on the RIGHT
    for i, col in enumerate([(255, 120, 100), (100, 180, 255), (120, 210, 140)]):
        px = bw - 170
        py = 50 + i * 100
        d.rounded_rectangle([px, py, px + 130, py + 85], 12, fill=col)
        d.rounded_rectangle([px + 10, py + 12, px + 120, py + 28], 4, fill=WHITE)

    # Shelf under posters
    d.rectangle([bw - 190, 360, bw - 30, 378], fill=(90, 70, 55))

    # Main board — centered but slightly higher, teal (new color)
    bx0, by0, bx1, by1 = 230, 70, bw - 200, int(bh * 0.58)
    d.rounded_rectangle([bx0 - 14, by0 - 14, bx1 + 14, by1 + 14], 18, fill=BOARD_FRAME)
    d.rounded_rectangle([bx0, by0, bx1, by1], 12, fill=BOARD)

    topic = (topic or "Lesson").strip() or "Lesson"
    tf = font(58)
    while d.textbbox((0, 0), topic, font=tf)[2] > (bx1 - bx0 - 48) and tf.size > 26:
        tf = font(tf.size - 3)
    y = by0 + 36
    for line in wrap_text(d, topic, tf, bx1 - bx0 - 48)[:2]:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=tf, fill=WHITE)
        y += tf.size + 10

    if definition:
        df = font(28)
        y += 16
        for line in wrap_text(d, definition, df, bx1 - bx0 - 48)[:4]:
            bb = d.textbbox((0, 0), line, font=df)
            tw = bb[2] - bb[0]
            d.text((bx0 + (bx1 - bx0 - tw) // 2, y), line, font=df, fill=(200, 230, 240))
            y += df.size + 6

    cta = cta or "Comment what you understood"
    cf = font(26)
    d.rounded_rectangle([bx0 + 28, by1 - 64, bx1 - 28, by1 - 18], 20, fill=ACCENT)
    bb = d.textbbox((0, 0), cta[:42], font=cf)
    tw = bb[2] - bb[0]
    d.text((bx0 + (bx1 - bx0 - tw) // 2, by1 - 54), cta[:42], font=cf, fill=BLACK)

    # Desk silhouette at bottom (new place)
    d.rounded_rectangle([bw // 2 - 280, int(bh * 0.72), bw // 2 + 280, int(bh * 0.78)], 10, fill=(70, 52, 42))
    return img


def draw_hook_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), (22, 18, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 280, W, H], fill=(12, 10, 16))
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    return img


def camera_crop(full: Image.Image, t: float, duration: float, mode: str) -> Image.Image:
    progress = min(1.0, t / max(duration, 0.1))
    ease = 0.5 - 0.5 * math.cos(progress * math.pi)
    fw, fh = full.size
    scale, ox, oy = 1.0 + 0.04 * ease, 0.5, 0.16
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    x = int(max_x * max(0.0, min(1.0, ox)))
    y = int(max_y * max(0.0, min(1.0, oy)))
    return full.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def prepare_topic_image(path: Path) -> Image.Image | None:
    if not path.exists():
        return None
    try:
        im = Image.open(path).convert("RGB")
        im = ImageOps.fit(im, (int(W * 1.35), int(H * 1.35)), method=Image.Resampling.LANCZOS)
        return im
    except Exception as e:
        print("topic image load fail", e, file=sys.stderr)
        return None


def ken_burns_frame(src: Image.Image, local_t: float, seg_dur: float, phase: str) -> Image.Image:
    p = min(1.0, max(0.0, local_t / max(seg_dur, 0.01)))
    ease = 0.5 - 0.5 * math.cos(p * math.pi)
    fw, fh = src.size
    scale = 1.0 + 0.18 * ease
    cw, ch = min(int(W * scale), fw), min(int(H * scale), fh)
    max_x, max_y = max(0, fw - cw), max(0, fh - ch)
    if phase == "left":
        ox = 0.15 + 0.2 * ease
    elif phase == "right":
        ox = 0.85 - 0.2 * ease
    else:
        ox = 0.5
    oy = 0.35 + 0.15 * ease
    x = int(max_x * max(0.0, min(1.0, ox)))
    y = int(max_y * max(0.0, min(1.0, oy)))
    return src.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def image_window(duration: float) -> tuple[float, float] | None:
    if duration < 12:
        return None
    start = duration * 0.28
    end = min(duration * 0.58, start + 10.0)
    if end - start < 3.5:
        return None
    return start, end


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
    return [
        {"at": 0.0, "move": "question"},
        {"at": 0.12, "move": "talk"},
        {"at": 0.35, "move": "explain"},
        {"at": 0.55, "move": "point"},
        {"at": 0.78, "move": "present"},
        {"at": 0.92, "move": "happy"},
    ]


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
    return {
        "welcome": "body_present.png", "talk": "body.png", "point": "arm_point.png",
        "sit": "body_sit.png", "present": "body_present.png", "question": "body_question.png",
        "happy": "body_happy.png", "explain": "body_explain.png", "shrug": "body_shrug.png",
        "count": "body_count.png", "think": "body_think.png", "lean": "body_lean.png",
    }.get(move, "body.png")


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
        chunk = words[i : i + 5]
        start, end = i * slot, min(duration, (i + len(chunk)) * slot)
        for j in range(len(chunk)):
            windows.append((start + j * (end - start) / len(chunk),
                            start + (j + 1) * (end - start) / len(chunk), chunk, j))
        i += len(chunk)
    return windows


def active_caption(windows, t):
    for ws, we, chunk, j in windows:
        if ws <= t < we:
            return chunk, j
    return (windows[-1][2], windows[-1][3]) if windows else ([""], 0)


def draw_hook_text(rgb, hook: str):
    d = ImageDraw.Draw(rgb)
    tf = font(48)
    lines = wrap_text(d, hook, tf, W - 80)[:4]
    box_h = 40 + len(lines) * (tf.size + 10)
    top = 80
    d.rounded_rectangle([32, top, W - 32, top + box_h], 28, fill=BLACK)
    y = top + 24
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        tw = bb[2] - bb[0]
        d.text(((W - tw) // 2, y), line, font=tf, fill=WHITE)
        y += tf.size + 10


def draw_image_caption(rgb, topic: str):
    d = ImageDraw.Draw(rgb)
    label = (topic or "")[:36]
    if not label:
        return
    tf = font(28)
    bb = d.textbbox((0, 0), label, font=tf)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W // 2 - tw // 2 - 24, H - 120, W // 2 + tw // 2 + 24, H - 56], 28, fill=BLACK)
    d.text((W // 2 - tw // 2, H - 106), label, font=tf, fill=WHITE)


def draw_karaoke(rgb, text, t, duration):
    """White text, black highly curved (pill) drop, active word brighter."""
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
    # Curved black capsule
    d.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=box_h // 2, fill=BLACK)
    x = x0 + pad_x
    y = y0 + pad_y - 2
    for i, w in enumerate(display):
        if i == active:
            d.text((x, y), w, font=cf, fill=WHITE)
        else:
            d.text((x, y), w, font=cf, fill=(190, 190, 195))
        x += gaps[i] + 16


def draw_ui(rgb, text, t, duration, topic, dyk, cta, p, hook_phase):
    d = ImageDraw.Draw(rgb)
    if hook_phase:
        return
    af = font(24)
    label = (topic or "Lesson")[:28]
    bb = d.textbbox((0, 0), label, font=af)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([W - tw - 60, 24, W - 24, 78], 20, fill=ACCENT)
    d.text((W - tw - 42, 38), label, font=af, fill=BLACK)
    if 0.62 <= p <= 0.75 and dyk:
        df = font(28)
        lines = wrap_text(d, "Did you know? " + dyk, df, W - 100)[:3]
        box_h = 36 + len(lines) * (df.size + 8)
        d.rounded_rectangle([40, 100, W - 40, 100 + box_h], 24, fill=BLACK)
        y = 118
        for line in lines:
            d.text((56, y), line, font=df, fill=WHITE)
            y += df.size + 8
    if p >= 0.82:
        cf = font(30)
        msg = (cta or "Comment what you understood")[:40]
        bb = d.textbbox((0, 0), msg, font=cf)
        tw = bb[2] - bb[0]
        d.rounded_rectangle([W // 2 - tw // 2 - 28, 90, W // 2 + tw // 2 + 28, 152], 24, fill=ACCENT)
        d.text((W // 2 - tw // 2, 104), msg, font=cf, fill=BLACK)
    draw_karaoke(rgb, text, t, duration)


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

    dur_s = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
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

    classroom = draw_classroom(topic, definition, cta)
    hook_bg = draw_hook_bg()
    topic_img = prepare_topic_image(Path(args.topic_image))
    win = image_window(duration) if topic_img is not None else None
    print(f"IMAGE_BEAT {win[0]:.1f}-{win[1]:.1f}s" if win else "IMAGE_BEAT skip", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            t = i / float(FPS)
            hook_phase = t < HOOK_END
            img_phase = bool(win and win[0] <= t < win[1])
            move = move_at(moves, t, duration)
            if hook_phase:
                move = "question"
            pfrac = t / max(duration, 0.1)
            blink = (int(t * 2) % 10 == 0)

            if hook_phase:
                frame = hook_bg.convert("RGBA")
                char = composite_host(move, open_at(cues, t), blink)
                target_h = int(H * 0.92)
                scale = target_h / char.height
                nw, nh = int(char.width * scale), int(char.height * scale)
                char = char.resize((nw, nh), Image.Resampling.LANCZOS)
                x = (W - nw) // 2
                y = H - nh + int(nh * 0.28)
                frame.paste(char, (x, y), char)
                rgb = frame.convert("RGB")
                draw_hook_text(rgb, hook)
            elif img_phase and topic_img is not None and win:
                local = t - win[0]
                seg = win[1] - win[0]
                third = seg / 3.0
                if local < third:
                    phase, lt, ld = "left", local, third
                elif local < 2 * third:
                    phase, lt, ld = "center", local - third, third
                else:
                    phase, lt, ld = "right", local - 2 * third, third
                rgb = ken_burns_frame(topic_img, lt, ld, phase)
                draw_image_caption(rgb, topic)
            else:
                frame = camera_crop(classroom, t, duration, "board").convert("RGBA")
                char = composite_host(move, open_at(cues, t), blink)
                target_h = int(H * 0.32)
                scale = target_h / char.height
                nw, nh = int(char.width * scale), int(char.height * scale)
                char = char.resize((nw, nh), Image.Resampling.LANCZOS)
                bob = int(2 * math.sin(t * 5))
                x = (W - nw) // 2
                if move == "point":
                    x = int(W * 0.22)
                y = H - nh - 140 + bob
                frame.paste(char, (x, y), char)
                rgb = frame.convert("RGB")
                draw_ui(rgb, args.text, t, duration, topic, dyk, cta, pfrac, False)

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
