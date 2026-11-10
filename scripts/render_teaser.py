#!/usr/bin/env python3
"""Teaser v5 render: Mike reads -> full-screen Q+timer -> green reveal + Mike head."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 24
WHITE = (255, 255, 255)
BLACK = (12, 14, 20)
YELLOW = (255, 210, 40)
GREEN = (36, 180, 100)
RED_SOFT = (90, 40, 50)
CARD = (18, 24, 40)
CARD_HI = (28, 40, 70)
SOFT = (170, 180, 200)
BG_TOP, BG_BOT = (28, 36, 58), (12, 16, 28)


def font(size: int):
    for n in (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(n).exists():
            return ImageFont.truetype(n, size)
    return ImageFont.load_default()


def wrap(d, text, tf, max_w):
    words, lines, cur = (text or "").split(), [], ""
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


def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def bg_gradient():
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r, g, b = [int(lerp(BG_TOP[i], BG_BOT[i], t)) for i in range(3)]
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def load_mike(pose: str = "point"):
    root = Path(__file__).resolve().parents[1]
    mapping = {
        "point": "body_point.png",
        "present": "body_present.png",
        "happy": "body_happy.png",
        "question": "body_question.png",
        "stand": "body.png",
    }
    p = root / "assets" / "mezi" / mapping.get(pose, "body_point.png")
    if p.exists():
        return Image.open(p).convert("RGBA")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from write_mezi_assets import draw_pose

        mode = "point" if pose == "point" else ("present" if pose == "present" else "stand")
        expr = "happy" if pose in ("happy", "present") else ("question" if pose == "question" else "neutral")
        return draw_pose(mode, expr)
    except Exception:
        return None


def mike_head_logo(size: int = 96) -> Image.Image | None:
    """Crop upper portion of Mike body as a circular logo."""
    mike = load_mike("happy") or load_mike("stand")
    if mike is None:
        return None
    # head-ish crop from top of sprite
    w, h = mike.size
    crop = mike.crop((int(w * 0.18), int(h * 0.02), int(w * 0.82), int(h * 0.42))).convert("RGBA")
    crop = crop.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([2, 2, size - 3, size - 3], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(crop, (0, 0), mask)
    return out


def paste_mike(base: Image.Image, pose: str, bob: float = 0.0, scale: float = 0.92):
    mike = load_mike(pose)
    if mike is None:
        return
    mw = int(520 * scale)
    mh = int(mw * mike.height / max(1, mike.width))
    mike = mike.resize((mw, mh), Image.Resampling.LANCZOS)
    base.paste(mike, ((W - mw) // 2, H - mh - 20 + int(bob)), mike)


def draw_choice_bar(d, left, top, right, height, text, fill, outline, width, fsize=34):
    d.rounded_rectangle([left, top, right, top + height], 22, fill=fill, outline=outline, width=width)
    pad, max_w = 20, right - left - 40
    size = fsize
    lines = []
    while size >= 22:
        cf = font(size)
        lines = wrap(d, text, cf, max_w)[:2]
        if lines and d.textbbox((0, 0), lines[0], font=cf)[2] <= max_w:
            break
        size -= 2
    cf = font(size)
    th = len(lines) * (size + 8)
    ty = top + max(8, (height - th) // 2)
    for line in lines:
        d.text((left + pad, ty), line, font=cf, fill=WHITE)
        ty += size + 8


def draw_intro(job, q, t_local: float):
    """Scene 1: Mike reading the question."""
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=YELLOW)
    tf = font(40)
    title = (job.get("title") or "Quick quiz")[:40]
    bb = d.textbbox((0, 0), title, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 28), title, font=tf, fill=BLACK)

    # question card mid
    qf = font(36)
    lines = wrap(d, q.get("question") or "", qf, W - 120)[:6]
    card_h = 40 + len(lines) * 48
    cy0 = 180
    d.rounded_rectangle([40, cy0, W - 40, cy0 + card_h], 24, fill=CARD, outline=(80, 100, 140), width=3)
    y = cy0 + 24
    for line in lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += 48

    tip = font(28)
    msg = "Listen… then pick A, B or C"
    bb = d.textbbox((0, 0), msg, font=tip)
    d.text(((W - (bb[2] - bb[0])) // 2, cy0 + card_h + 40), msg, font=tip, fill=YELLOW)

    paste_mike(img, "question", bob=math.sin(t_local * 3.0) * 6, scale=0.95)
    return img


def draw_ask(q, remaining: float | None, t_local: float, total_cd: float):
    """Scene 2: full-screen question + options + top timer. No Mike."""
    img = bg_gradient()
    d = ImageDraw.Draw(img)

    # Top timer bar
    bar_h = 120
    d.rectangle([0, 0, W, bar_h], fill=(16, 20, 32))
    if remaining is not None:
        frac = max(0.0, min(1.0, float(remaining) / max(0.01, total_cd)))
        fill_w = int(W * frac)
        color = YELLOW if remaining > 3 else (255, 90, 70)
        d.rectangle([0, 0, fill_w, bar_h], fill=color)
        n = max(0, int(math.ceil(remaining)))
        nf = font(64)
        s = f"{n}s"
        bb = d.textbbox((0, 0), s, font=nf)
        d.text(((W - (bb[2] - bb[0])) // 2, 28), s, font=nf, fill=BLACK if remaining > 3 else WHITE)
    else:
        tf = font(40)
        bb = d.textbbox((0, 0), "GET READY", font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, 36), "GET READY", font=tf, fill=YELLOW)

    # Question
    qf = font(40)
    q_lines = wrap(d, q.get("question") or "", qf, W - 80)[:5]
    y = bar_h + 50
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += 52

    # Choices full width
    top = y + 40
    btn_h, gap = 150, 24
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        appear = ease_out(max(0.0, min(1.0, (t_local - 0.1 * i) * 3)))
        inset = int((1 - appear) * 30)
        draw_choice_bar(
            d,
            36 + inset,
            top + i * (btn_h + gap),
            W - 36 - inset,
            btn_h,
            ch,
            CARD_HI if appear > 0.4 else CARD,
            (90, 110, 160),
            4,
            36,
        )
    return img


def draw_reveal(q, t_local: float):
    """Scene 3: correct option green + Mike head logo + reason."""
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 110], fill=GREEN)
    tf = font(44)
    ans = str(q.get("answer") or "").upper()
    msg = f"ANSWER  {ans}"
    bb = d.textbbox((0, 0), msg, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 30), msg, font=tf, fill=WHITE)

    qf = font(32)
    q_lines = wrap(d, q.get("question") or "", qf, W - 80)[:3]
    y = 150
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=SOFT)
        y += 42

    flash = ease_out(min(1.0, t_local * 3.5))
    top = y + 30
    btn_h, gap = 140, 20
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        letter = ch.strip()[0].upper() if ch else "?"
        hit = letter == ans or ch.upper().startswith(ans + ")")
        by = top + i * (btn_h + gap)
        if hit:
            fill = (
                int(lerp(CARD[0], GREEN[0], flash)),
                int(lerp(CARD[1], GREEN[1], flash)),
                int(lerp(CARD[2], GREEN[2], flash)),
            )
            outline, width = YELLOW, 6
        else:
            fill, outline, width = (30, 34, 48), (50, 55, 70), 3
        draw_choice_bar(d, 36, by, W - 36, btn_h, ch, fill, outline, width, 34)
        if hit and flash > 0.4:
            logo = mike_head_logo(88)
            if logo is not None:
                img.paste(logo, (W - 130, by + (btn_h - 88) // 2), logo)

    # reason
    rf = font(30)
    reason = (q.get("reason") or "")[:160]
    ry = top + 3 * (btn_h + gap) + 20
    d.rounded_rectangle([40, ry, W - 40, min(H - 40, ry + 160)], 20, fill=CARD)
    yy = ry + 24
    for line in wrap(d, reason, rf, W - 100)[:4]:
        bb = d.textbbox((0, 0), line, font=rf)
        d.text(((W - (bb[2] - bb[0])) // 2, yy), line, font=rf, fill=YELLOW)
        yy += 36
    return img


def q_by_index(job, qi):
    for q in job.get("questions") or []:
        if q.get("index") == qi:
            return q
    qs = job.get("questions") or []
    return qs[0] if qs else None


def frame_at(job, timeline, t):
    seg = timeline[-1]
    for s in timeline:
        if s["start"] <= t < s["end"] or (s is timeline[-1] and t >= s["start"]):
            if t < s["end"] or s is timeline[-1]:
                seg = s
                if t < s["end"]:
                    break
    phase, qi = seg.get("phase"), seg.get("q")
    q = q_by_index(job, qi)
    t_local = max(0.0, t - float(seg["start"]))
    dur = max(0.01, float(seg["end"]) - float(seg["start"]))
    if phase == "intro" and q:
        return draw_intro(job, q, t_local)
    if phase == "countdown" and q:
        return draw_ask(q, remaining=max(0.0, float(seg["end"]) - t), t_local=t_local, total_cd=dur)
    if phase == "ask" and q:
        return draw_ask(q, remaining=None, t_local=t_local, total_cd=dur)
    if phase == "reveal" and q:
        return draw_reveal(q, t_local)
    if q:
        return draw_ask(q, remaining=None, t_local=t_local, total_cd=8)
    return bg_gradient()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job", default="teaser_job.json")
    p.add_argument("--timeline", default="teaser_timeline.json")
    p.add_argument("--audio", required=True)
    p.add_argument("--out", default="output.mp4")
    args = p.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    tl = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    timeline = tl["timeline"]
    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")
    dur = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio),
            ],
            text=True,
        ).strip()
    )
    n = max(FPS, int(math.ceil(dur * FPS)))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(n):
            frame_at(job, timeline, i / float(FPS)).save(tmp_path / f"frame_{i:05d}.png")
        out = Path(args.out).resolve()
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(tmp_path / "frame_%05d.png"),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(out),
            ]
        )
        print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
