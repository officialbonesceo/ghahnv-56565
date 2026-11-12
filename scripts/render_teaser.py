#!/usr/bin/env python3
"""Teaser v6 render: full question + full choices on screen, no mid-word cuts."""
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
    """Word-wrap without cutting words."""
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


def fit_lines(d, text, max_w, max_lines, start_size, min_size=20):
    """Shrink font until text fits in max_lines without truncating words."""
    size = start_size
    while size >= min_size:
        tf = font(size)
        lines = wrap(d, text, tf, max_w)
        if len(lines) <= max_lines:
            return tf, size, lines
        size -= 2
    tf = font(min_size)
    lines = wrap(d, text, tf, max_w)
    # last resort: keep as many full lines as fit (no mid-word)
    return tf, min_size, lines[:max_lines]


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
    mike = load_mike("happy") or load_mike("stand")
    if mike is None:
        return None
    w, h = mike.size
    crop = mike.crop((int(w * 0.18), int(h * 0.02), int(w * 0.82), int(h * 0.42))).convert("RGBA")
    crop = crop.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([2, 2, size - 3, size - 3], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(crop, (0, 0), mask)
    return out


def paste_mike(base: Image.Image, pose: str, bob: float = 0.0, scale: float = 0.85):
    mike = load_mike(pose)
    if mike is None:
        return
    mw = int(480 * scale)
    mh = int(mw * mike.height / max(1, mike.width))
    mike = mike.resize((mw, mh), Image.Resampling.LANCZOS)
    base.paste(mike, ((W - mw) // 2, H - mh - 10 + int(bob)), mike)


def draw_choice_bar(d, left, top, right, height, text, fill, outline, width):
    d.rounded_rectangle([left, top, right, top + height], 20, fill=fill, outline=outline, width=width)
    pad = 18
    max_w = right - left - 36
    # Allow up to 3 full lines so options are not cut
    tf, size, lines = fit_lines(d, text, max_w, max_lines=3, start_size=32, min_size=18)
    th = len(lines) * (size + 6)
    ty = top + max(6, (height - th) // 2)
    for line in lines:
        d.text((left + pad, ty), line, font=tf, fill=WHITE)
        ty += size + 6


def draw_intro(job, q, t_local: float):
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=YELLOW)
    tf = font(36)
    title = (job.get("title") or "Quick quiz")[:50]
    bb = d.textbbox((0, 0), title, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 30), title, font=tf, fill=BLACK)

    max_w = W - 100
    qf, qsize, lines = fit_lines(d, q.get("question") or "", max_w, max_lines=7, start_size=34, min_size=22)
    card_h = 36 + len(lines) * (qsize + 10)
    cy0 = 140
    d.rounded_rectangle([36, cy0, W - 36, cy0 + card_h], 22, fill=CARD, outline=(80, 100, 140), width=3)
    y = cy0 + 18
    for line in lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += qsize + 10

    tip = font(26)
    msg = "Listen… then pick A, B or C"
    bb = d.textbbox((0, 0), msg, font=tip)
    d.text(((W - (bb[2] - bb[0])) // 2, min(cy0 + card_h + 28, H - 420)), msg, font=tip, fill=YELLOW)

    paste_mike(img, "question", bob=math.sin(t_local * 3.0) * 5, scale=0.78)
    return img


def draw_ask(q, remaining: float | None, t_local: float, total_cd: float):
    img = bg_gradient()
    d = ImageDraw.Draw(img)

    bar_h = 100
    d.rectangle([0, 0, W, bar_h], fill=(16, 20, 32))
    if remaining is not None:
        frac = max(0.0, min(1.0, float(remaining) / max(0.01, total_cd)))
        fill_w = int(W * frac)
        color = YELLOW if remaining > 4 else (255, 90, 70)
        d.rectangle([0, 0, fill_w, bar_h], fill=color)
        n = max(0, int(math.ceil(remaining)))
        nf = font(56)
        s = f"{n}s"
        bb = d.textbbox((0, 0), s, font=nf)
        d.text(((W - (bb[2] - bb[0])) // 2, 22), s, font=nf, fill=BLACK if remaining > 4 else WHITE)
    else:
        tf = font(36)
        bb = d.textbbox((0, 0), "GET READY", font=tf)
        d.text(((W - (bb[2] - bb[0])) // 2, 28), "GET READY", font=tf, fill=YELLOW)

    max_w = W - 72
    qf, qsize, q_lines = fit_lines(
        d, q.get("question") or "", max_w, max_lines=6, start_size=36, min_size=22
    )
    y = bar_h + 28
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=WHITE)
        y += qsize + 8

    # Dynamic choice height from remaining space
    top = y + 24
    choices = (q.get("choices") or [])[:3]
    avail = H - top - 40
    gap = 16
    btn_h = max(110, min(160, (avail - gap * 2) // 3))

    for i, ch in enumerate(choices):
        appear = ease_out(max(0.0, min(1.0, (t_local - 0.08 * i) * 3)))
        inset = int((1 - appear) * 24)
        draw_choice_bar(
            d,
            28 + inset,
            top + i * (btn_h + gap),
            W - 28 - inset,
            btn_h,
            ch,
            CARD_HI if appear > 0.4 else CARD,
            (90, 110, 160),
            4,
        )
    return img


def draw_reveal(q, t_local: float):
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=GREEN)
    tf = font(42)
    ans = str(q.get("answer") or "").upper()
    msg = f"ANSWER  {ans}"
    bb = d.textbbox((0, 0), msg, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 26), msg, font=tf, fill=WHITE)

    max_w = W - 72
    qf, qsize, q_lines = fit_lines(
        d, q.get("question") or "", max_w, max_lines=4, start_size=28, min_size=18
    )
    y = 120
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(((W - (bb[2] - bb[0])) // 2, y), line, font=qf, fill=SOFT)
        y += qsize + 6

    flash = ease_out(min(1.0, t_local * 3.5))
    top = y + 16
    choices = (q.get("choices") or [])[:3]
    gap = 12
    # Leave room for reason box (~180px)
    avail = H - top - 200
    btn_h = max(100, min(140, (avail - gap * 2) // 3))

    for i, ch in enumerate(choices):
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
        draw_choice_bar(d, 28, by, W - 28, btn_h, ch, fill, outline, width)
        if hit and flash > 0.4:
            logo = mike_head_logo(72)
            if logo is not None:
                img.paste(logo, (W - 110, by + max(0, (btn_h - 72) // 2)), logo)

    reason = (q.get("reason") or "").strip()
    ry = top + 3 * (btn_h + gap) + 12
    rf, rsize, rlines = fit_lines(d, reason, W - 100, max_lines=5, start_size=28, min_size=18)
    box_h = 24 + len(rlines) * (rsize + 6)
    d.rounded_rectangle([28, ry, W - 28, min(H - 24, ry + box_h)], 18, fill=CARD)
    yy = ry + 14
    for line in rlines:
        bb = d.textbbox((0, 0), line, font=rf)
        d.text(((W - (bb[2] - bb[0])) // 2, yy), line, font=rf, fill=YELLOW)
        yy += rsize + 6
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
        return draw_ask(q, remaining=None, t_local=t_local, total_cd=12)
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
