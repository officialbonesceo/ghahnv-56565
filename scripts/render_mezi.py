#!/usr/bin/env python3
"""Mike Shorts: 12 distinct classrooms (rooms_mezi), phenomenon support, pan + bounce."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
FPS = 24
HOOK_END = 3.2
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)
MOUTH = {"X": 0.0, "B": 0.25, "A": 1.0, "C": 0.55, "D": 0.7, "E": 0.85, "F": 0.5, "G": 0.95, "H": 1.0}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rooms_mezi import ROOMS, draw_classroom  # 12 distinct layouts

THUMB_STYLES = ["close_face", "side_teach", "solid_blast", "mike_top", "topic_wall"]
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


def draw_thumb_frame(style: str, topic: str, hook: str, room: dict, char: Image.Image) -> Image.Image:
    accent, board, wall = room["accent"], room["board"], room["wall"]
    if style == "close_face":
        img = Image.new("RGB", (W, H), (12, 10, 18))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 28], fill=accent)
        d.rectangle([0, H - 28, W, H], fill=accent)
        target_h = int(H * 1.05)
        scale = target_h / max(char.height, 1)
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, H - nh + int(nh * 0.22)), c)
        tf = font(48)
        lines = wrap_text(d, topic, tf, W - 64)[:2]
        box_h = 36 + len(lines) * (tf.size + 10)
        d.rounded_rectangle([28, 48, W - 28, 48 + box_h], 28, fill=BLACK)
        y = 64
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 10
        return img
    if style == "side_teach":
        img = Image.new("RGB", (W, H), wall)
        d = ImageDraw.Draw(img)
        d.rectangle([int(W * 0.40), 0, W, H], fill=board)
        d.rectangle([int(W * 0.40) - 8, 0, int(W * 0.40) + 8, H], fill=accent)
        tf = font(52)
        lines = wrap_text(d, topic, tf, int(W * 0.55) - 48)[:4]
        y = H // 2 - 140
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            tw = bb[2] - bb[0]
            d.text((int(W * 0.40) + (int(W * 0.60) - tw) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 14
        target_h = int(H * 0.82)
        scale = target_h / max(char.height, 1)
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, (max(4, int(W * 0.20) - nw // 2), H - nh + 60), c)
        return img
    if style == "solid_blast":
        img = Image.new("RGB", (W, H), board)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 36], fill=accent)
        d.rectangle([0, H - 36, W, H], fill=accent)
        tf = font(80)
        lines = wrap_text(d, topic, tf, W - 40)[:3]
        total_h = len(lines) * (tf.size + 18)
        y = max(100, H // 2 - total_h // 2 - 160)
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 18
        target_h = int(H * 0.28)
        scale = target_h / max(char.height, 1)
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, H - nh - 50), c)
        return img
    if style == "mike_top":
        img = Image.new("RGB", (W, H), (16, 14, 22))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, int(H * 0.62)], fill=wall)
        d.rectangle([0, int(H * 0.62), W, H], fill=board)
        d.rectangle([0, int(H * 0.62) - 12, W, int(H * 0.62) + 12], fill=accent)
        target_h = int(H * 0.70)
        scale = target_h / max(char.height, 1)
        nw, nh = int(char.width * scale), int(char.height * scale)
        c = char.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(c, ((W - nw) // 2, int(H * 0.58) - nh + 40), c)
        tf = font(56)
        lines = wrap_text(d, topic, tf, W - 60)[:3]
        y = int(H * 0.68)
        for line in lines:
            bb = d.textbbox((0, 0), line, font=tf)
            d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=WHITE)
            y += tf.size + 12
        return img
    img = Image.new("RGB", (W, H), accent)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 40], fill=BLACK)
    d.rectangle([0, H - 40, W, H], fill=BLACK)
    tf = font(72)
    lines = wrap_text(d, topic, tf, W - 50)[:3]
    y = 120
    for line in lines:
        bb = d.textbbox((0, 0), line, font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=tf, fill=BLACK)
        y += tf.size + 16
    target_h = int(H * 0.55)
    scale = target_h / max(char.height, 1)
    nw, nh = int(char.width * scale), int(char.height * scale)
    c = char.resize((nw, nh), Image.Resampling.LANCZOS)
    img.paste(c, (W - nw - 20, H - nh - 60), c)
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


def load_moves() -> list:
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
        if m["at"] <= p:
            current = m.get("move", "talk")
    return current


def body_for(move: str) -> str:
    mapping = {
        "question": "body_question.png", "happy": "body_happy.png",
        "present": "body_present.png", "point": "body_point.png",
        "explain": "body_explain.png", "think": "body_think.png",
    }
    name = mapping.get(move, "body.png")
    if not (asset_dir() / name).exists():
        return "body.png"
    return name


def composite_host(move: str, mouth_amt: float) -> Image.Image:
    body = load_rgba(body_for(move))
    mouth = load_rgba(mouth_name(mouth_amt))
    mx, my = int(body.width * 0.38), int(body.height * 0.42)
    out = body.copy()
    out.paste(mouth, (mx, my), mouth)
    return out


def word_windows(text, duration):
    words = (text or "").split()
    if not words:
        return []
    slot = duration / max(len(words), 1)
    windows, i = [], 0
    while i < len(words):
        chunk = words[i:i + 3]
        start = i * slot
        end = min(duration, (i + len(chunk)) * slot)
        windows.append((start, end, chunk, i))
        i += len(chunk)
    return windows


def active_caption(windows, t):
    for ws, we, chunk, j in windows:
        if ws <= t < we:
            return (chunk, j)
    return (windows[-1][2], windows[-1][3]) if windows else ([""], 0)


def draw_fullscreen_dyk(dyk: str) -> Image.Image:
    img = Image.new("RGB", (W, H), (20, 18, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 40], fill=(255, 180, 40))
    d.rectangle([0, H - 40, W, H], fill=(255, 180, 40))
    tf = font(44)
    d.text((60, 120), "Did you know?", font=tf, fill=(255, 220, 100))
    df = font(36)
    y = 220
    for line in wrap_text(d, dyk, df, W - 100)[:8]:
        d.text((60, y), line, font=df, fill=WHITE)
        y += df.size + 12
    return img


def draw_fullscreen_cta() -> Image.Image:
    img = Image.new("RGB", (W, H), (25, 20, 40))
    d = ImageDraw.Draw(img)
    tf = font(52)
    msg = "Follow for more!"
    bb = d.textbbox((0, 0), msg, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, H // 2 - 40), msg, font=tf, fill=WHITE)
    return img


def draw_karaoke(frame: Image.Image, words, active_idx: int) -> Image.Image:
    d = ImageDraw.Draw(frame)
    tf = font(32)
    text = " ".join(words)
    bb = d.textbbox((0, 0), text, font=tf)
    tw = bb[2] - bb[0]
    x0 = (W - tw) // 2
    y = H - 180
    d.rounded_rectangle([x0 - 20, y - 10, x0 + tw + 20, y + tf.size + 16], 12, fill=(0, 0, 0))
    d.text((x0, y), text, font=tf, fill=WHITE)
    return frame


def draw_topic_chip(frame: Image.Image, topic: str) -> Image.Image:
    d = ImageDraw.Draw(frame)
    tf = font(28)
    bb = d.textbbox((0, 0), topic, font=tf)
    tw = bb[2] - bb[0]
    d.rounded_rectangle([30, 40, 50 + tw, 40 + tf.size + 20], 16, fill=(0, 0, 0))
    d.text((40, 48), topic, font=tf, fill=WHITE)
    return frame


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", default="speech.mp3")
    p.add_argument("--cues", default="mouth.json")
    p.add_argument("--script", default="script_job.json")
    p.add_argument("--text", default="", help="voiceover script (CI)")
    p.add_argument("--title", default="", help="topic title (CI)")
    p.add_argument("--bg-image", default="", dest="bg_image")
    p.add_argument("--topic-image", default="topic_image.jpg")
    p.add_argument("--out", default="output.mp4")
    p.add_argument("--bg", default="classroom")
    p.add_argument("--actions", default="")
    p.add_argument("--preview", action="store_true")
    args = p.parse_args()

    topic = (args.title or "").strip() or "Lesson"
    text = (args.text or "").strip()
    definition, hook, dyk = "", "", ""

    script_path = Path(args.script)
    if script_path.exists():
        try:
            data = json.loads(script_path.read_text(encoding="utf-8"))
            if not topic or topic == "Lesson":
                topic = data.get("short_title") or data.get("topic") or data.get("title") or topic
            if not text:
                text = data.get("script") or data.get("voiceover") or data.get("text") or ""
            definition = data.get("definition") or data.get("extract") or ""
            hook = data.get("hook") or ""
            dyk = data.get("dyk") or data.get("did_you_know") or ""
        except Exception as e:
            print("script_job load", e, file=sys.stderr)

    for alt in ("topic.json", "script.json"):
        ap = Path(alt)
        if ap.exists() and not definition:
            try:
                data = json.loads(ap.read_text(encoding="utf-8"))
                definition = data.get("extract") or data.get("definition") or definition
                if topic == "Lesson":
                    topic = data.get("title") or data.get("topic") or topic
            except Exception:
                pass

    room = pick_room(topic)
    print("ROOM", room["id"], room.get("theme"), "topic=", topic, file=sys.stderr)

    if args.preview:
        img = draw_classroom(topic, (definition or "")[:120], room)
        outp = Path(args.out if str(args.out).endswith(".png") else "preview_classroom.png")
        img.save(outp)
        print("preview", outp, file=sys.stderr)
        return

    audio = Path(args.audio)
    cues = load_cues(Path(args.cues) if args.cues else None)
    duration = 12.0
    if audio.exists():
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
                capture_output=True, text=True, check=True,
            )
            duration = float(r.stdout.strip())
        except Exception as e:
            print("ffprobe fail", e, file=sys.stderr)

    classroom = draw_classroom(topic, (definition or "")[:200], room)
    tip = Path(args.topic_image) if args.topic_image else None
    topic_img = prepare_topic_image(tip) if tip and tip.exists() else None
    moves = load_moves()
    img_win = image_window(duration) if topic_img is not None else None
    dyk_win = dyk_window(duration, img_win) if dyk else None
    cta_win = cta_window(duration)
    windows = word_windows(text, duration)

    out_mp4 = Path(args.out)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        n_frames = max(1, int(duration * FPS))
        for i in range(n_frames):
            t = i / FPS
            move = move_at(moves, t, duration)
            mouth = open_at(cues, t)
            host = composite_host(move, mouth)

            if dyk_win and dyk_win[0] <= t < dyk_win[1]:
                frame = draw_fullscreen_dyk(dyk)
            elif cta_win and t >= cta_win[0]:
                frame = draw_fullscreen_cta()
            elif img_win and img_win[0] <= t < img_win[1] and topic_img is not None:
                local = t - img_win[0]
                seg = img_win[1] - img_win[0]
                frame = ken_burns_frame(topic_img, local, seg, "zoom_in")
            else:
                base = camera_crop(classroom, t, duration).convert("RGBA")
                target_h = int(H * 0.72)
                scale = target_h / max(host.height, 1)
                nw, nh = int(host.width * scale), int(host.height * scale)
                h = host.resize((nw, nh), Image.Resampling.LANCZOS)
                bx = (W - nw) // 2
                by = H - nh + 40
                base.paste(h, (bx, by), h)
                frame = base.convert("RGB")
                if t < HOOK_END:
                    style = pick_thumb_style(topic)
                    frame = draw_thumb_frame(style, topic, hook, room, host)
                else:
                    frame = draw_topic_chip(frame, topic)
                    if windows:
                        chunk, j = active_caption(windows, t)
                        frame = draw_karaoke(frame, chunk, j)

            frame.save(td / f"f{i:05d}.png")

        list_path = td / "list.txt"
        with list_path.open("w") as f:
            for i in range(n_frames):
                f.write(f"file 'f{i:05d}.png'\nduration {1 / FPS}\n")
            f.write(f"file 'f{n_frames - 1:05d}.png'\n")

        # absolute paths: ffmpeg cwd is temp dir (frames), audio/out live in repo root
        audio_in = str(audio.resolve()) if audio.exists() else str(td / "f00000.png")
        out_abs = str(out_mp4.resolve())
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
            "-i", audio_in,
            "-r", str(FPS), "-pix_fmt", "yuv420p", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart",
        ]
        if audio.exists():
            cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd.append(out_abs)
        subprocess.run(cmd, cwd=str(td), check=True)
        print("OK", out_mp4, out_mp4.stat().st_size if out_mp4.exists() else 0, file=sys.stderr)


if __name__ == "__main__":
    main()
