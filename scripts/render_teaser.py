#!/usr/bin/env python3
"""Render engaging language teaser: Mike + quiz card + 4s countdown + motion."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
WHITE = (255, 255, 255)
BLACK = (18, 18, 24)
YELLOW = (255, 210, 40)
YELLOW_D = (230, 175, 20)
CARD = (22, 32, 58)
CARD_HI = (32, 48, 85)
GREEN = (34, 160, 90)
GREEN_D = (22, 120, 65)
SOFT = (150, 165, 195)
BG_TOP = (42, 58, 88)
BG_BOT = (18, 26, 42)
RING_BG = (40, 52, 78)

# Sweet-spot countdown: long enough to think, short enough not to bore
COUNTDOWN_SECS = 4


def font(size: int):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap(d, text, tf, max_w):
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


def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def bg_gradient() -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r = int(lerp(BG_TOP[0], BG_BOT[0], t))
        g = int(lerp(BG_TOP[1], BG_BOT[1], t))
        b = int(lerp(BG_TOP[2], BG_BOT[2], t))
        for x in range(W):
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(img)
    for i in range(18):
        x = (i * 173 + 40) % (W - 20)
        y = (i * 291 + 80) % (H - 20)
        d.ellipse([x, y, x + 3, y + 3], fill=(255, 255, 255))
    return img


def load_mike(pose: str = "point") -> Image.Image | None:
    root = Path(__file__).resolve().parents[1]
    mapping = {
        "point": "body_point.png",
        "present": "body_present.png",
        "happy": "body_happy.png",
        "question": "body_question.png",
        "stand": "body.png",
        "explain": "body_explain.png",
    }
    path = root / "assets" / "mezi" / mapping.get(pose, "body_point.png")
    if path.exists():
        return Image.open(path).convert("RGBA")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from write_mezi_assets import draw_pose

        mode = "point" if pose == "point" else ("present" if pose == "present" else "stand")
        expr = "happy" if pose in ("happy", "present") else ("question" if pose == "question" else "neutral")
        return draw_pose(mode, expr)
    except Exception:
        return None


def paste_mike(base: Image.Image, pose: str, bob: float = 0.0, scale: float = 0.95) -> None:
    mike = load_mike(pose)
    if mike is None:
        return
    mw = int(520 * scale)
    mh = int(mw * mike.height / max(1, mike.width))
    mike = mike.resize((mw, mh), Image.Resampling.LANCZOS)
    x = -20
    y = H - mh - 40 + int(bob)
    base.paste(mike, (x, y), mike)


def top_banner(d, text: str, fill=YELLOW, text_fill=BLACK):
    d.rectangle([0, 0, W, 110], fill=fill)
    d.rectangle([0, 110, W, 118], fill=YELLOW_D)
    tf = font(44)
    bb = d.textbbox((0, 0), text, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, 32), text, font=tf, fill=text_fill)


def q_by_index(job: dict, qi: int | None) -> dict | None:
    if not qi:
        return None
    for q in job.get("questions") or []:
        if q.get("index") == qi:
            return q
    return None


def draw_intro(job: dict, t_local: float = 0.0) -> Image.Image:
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    slide = int(lerp(-120, 0, ease_out(min(1.0, t_local * 3))))
    d.rectangle([0, slide, W, slide + 110], fill=YELLOW)
    d.rectangle([0, slide + 110, W, slide + 118], fill=YELLOW_D)
    tf = font(48)
    s = "ENGLISH QUIZ"
    bb = d.textbbox((0, 0), s, font=tf)
    d.text(((W - (bb[2] - bb[0])) // 2, slide + 30), s, font=tf, fill=BLACK)

    total = int(job.get("total_marks") or 60)
    each = int(job.get("marks_each") or 20)
    pop = ease_out(max(0.0, min(1.0, (t_local - 0.15) * 2.5)))
    big = font(int(64 + 16 * pop))
    score_line = f"{total} MARKS"
    bb = d.textbbox((0, 0), score_line, font=big)
    d.text(((W - (bb[2] - bb[0])) // 2, 520), score_line, font=big, fill=YELLOW)

    sub = font(34)
    msg = f"3 questions · {each} marks each"
    bb = d.textbbox((0, 0), msg, font=sub)
    d.text(((W - (bb[2] - bb[0])) // 2, 640), msg, font=sub, fill=WHITE)

    tip = font(30)
    m2 = "Comment A, B or C before time is up"
    bb = d.textbbox((0, 0), m2, font=tip)
    d.text(((W - (bb[2] - bb[0])) // 2, 720), m2, font=tip, fill=SOFT)

    bob = math.sin(t_local * 3.0) * 6
    paste_mike(img, "present", bob=bob, scale=0.92)
    return img


def draw_outro(job: dict, t_local: float = 0.0) -> Image.Image:
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    total = int(job.get("total_marks") or 60)
    top_banner(d, f"YOUR SCORE / {total}?", fill=GREEN, text_fill=WHITE)

    y = 280
    for i, q in enumerate(job.get("questions") or []):
        appear = ease_out(max(0.0, min(1.0, (t_local - i * 0.12) * 3)))
        marks = int(q.get("marks") or job.get("marks_each") or 20)
        line = f"Q{q['index']}: {q['answer']}  (+{marks})"
        tf = font(46)
        bb = d.textbbox((0, 0), line, font=tf)
        x = int(lerp(W, (W - (bb[2] - bb[0])) // 2, appear))
        d.text((x, y), line, font=tf, fill=YELLOW)
        y += 95

    full = font(46)
    msg = f"All correct = {total}"
    bb = d.textbbox((0, 0), msg, font=full)
    d.text(((W - (bb[2] - bb[0])) // 2, y + 30), msg, font=full, fill=WHITE)

    cta = font(30)
    msg2 = "Comment your marks · Follow for more"
    bb = d.textbbox((0, 0), msg2, font=cta)
    d.text(((W - (bb[2] - bb[0])) // 2, H - 220), msg2, font=cta, fill=SOFT)

    bob = math.sin(t_local * 2.5) * 5
    paste_mike(img, "happy", bob=bob, scale=0.9)
    return img


def draw_ask(
    q: dict,
    remaining: float | None = None,
    t_local: float = 0.0,
    total_cd: float = COUNTDOWN_SECS,
) -> Image.Image:
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    marks = int(q.get("marks") or 20)
    top_banner(d, f"QUESTION {q.get('index', '')}  ·  {marks} MARKS")

    card_x0, card_x1 = 380, W - 48
    card_y0 = 160
    qf = font(38)
    q_lines = wrap(d, q.get("question") or "", qf, card_x1 - card_x0 - 48)[:4]
    card_h = 70 + len(q_lines) * 48 + 3 * 118 + 40
    d.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y0 + card_h],
        28,
        fill=WHITE,
        outline=(200, 210, 230),
        width=3,
    )
    d.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y0 + 70 + len(q_lines) * 48],
        28,
        fill=CARD,
    )
    d.rectangle(
        [card_x0, card_y0 + 40, card_x1, card_y0 + 70 + len(q_lines) * 48],
        fill=CARD,
    )

    y = card_y0 + 28
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(
            (card_x0 + (card_x1 - card_x0 - (bb[2] - bb[0])) // 2, y),
            line,
            font=qf,
            fill=WHITE,
        )
        y += 48

    choices_top = y + 24
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        appear = ease_out(max(0.0, min(1.0, (t_local - 0.08 * i) * 4)))
        top = choices_top + i * 118
        inset = int((1 - appear) * 40)
        left = card_x0 + 28 + inset
        right = card_x1 - 28 - inset
        d.rounded_rectangle(
            [left, top, right, top + 96],
            22,
            fill=CARD_HI if appear > 0.5 else CARD,
            outline=(70, 90, 130),
            width=3,
        )
        cf = font(36)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(
            ((left + right - (bb[2] - bb[0])) // 2, top + 28),
            ch,
            font=cf,
            fill=WHITE,
        )

    if remaining is not None:
        n_float = max(0.0, float(remaining))
        n = max(0, int(math.ceil(n_float)))
        frac = n_float / max(0.01, total_cd)
        cx, cy, r = 230, H - 320, 108
        pulse = 1.0 + 0.08 * abs(math.sin(t_local * math.pi * 2))
        rr = int(r * pulse)
        d.ellipse([cx - rr - 8, cy - rr - 8, cx + rr + 8, cy + rr + 8], outline=RING_BG, width=14)
        extent = int(360 * frac)
        if extent > 0:
            d.pieslice(
                [cx - rr, cy - rr, cx + rr, cy + rr],
                start=-90,
                end=-90 + extent,
                fill=YELLOW,
            )
            d.ellipse(
                [cx - rr + 18, cy - rr + 18, cx + rr - 18, cy + rr - 18],
                fill=CARD,
            )
        else:
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=YELLOW, width=12)
            d.ellipse(
                [cx - rr + 18, cy - rr + 18, cx + rr - 18, cy + rr - 18],
                fill=CARD,
            )
        nf = font(100)
        s = str(n) if n > 0 else "!"
        bb = d.textbbox((0, 0), s, font=nf)
        d.text(
            (cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2 - 10),
            s,
            font=nf,
            fill=YELLOW,
        )
        lf = font(26)
        lab = "seconds — comment!" if n > 0 else "time up"
        bb = d.textbbox((0, 0), lab, font=lf)
        d.text((cx - (bb[2] - bb[0]) // 2, cy + rr + 16), lab, font=lf, fill=SOFT)
    else:
        tip = font(30)
        msg = "Get ready…"
        bb = d.textbbox((0, 0), msg, font=tip)
        d.text(((W - (bb[2] - bb[0])) // 2, H - 200), msg, font=tip, fill=YELLOW)

    bob = math.sin(t_local * 3.2) * 5
    paste_mike(img, "point", bob=bob, scale=0.95)
    return img


def draw_reveal(q: dict, t_local: float = 0.0) -> Image.Image:
    img = bg_gradient()
    d = ImageDraw.Draw(img)
    marks = int(q.get("marks") or 20)
    top_banner(d, f"ANSWER · Q{q.get('index', '')}  ·  +{marks}", fill=GREEN, text_fill=WHITE)

    ans = str(q.get("answer") or "").upper()
    card_x0, card_x1 = 380, W - 48
    card_y0 = 160
    qf = font(34)
    q_lines = wrap(d, q.get("question") or "", qf, card_x1 - card_x0 - 48)[:3]
    d.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y0 + 520],
        28,
        fill=WHITE,
        outline=(200, 210, 230),
        width=3,
    )
    y = card_y0 + 28
    for line in q_lines:
        bb = d.textbbox((0, 0), line, font=qf)
        d.text(
            (card_x0 + (card_x1 - card_x0 - (bb[2] - bb[0])) // 2, y),
            line,
            font=qf,
            fill=SOFT,
        )
        y += 44

    flash = ease_out(min(1.0, t_local * 4))
    for i, ch in enumerate((q.get("choices") or [])[:3]):
        top = y + 20 + i * 118
        letter = ch.strip()[0].upper() if ch else "?"
        hit = letter == ans or ch.upper().startswith(ans + ")")
        if hit:
            fill = (
                int(lerp(CARD[0], GREEN[0], flash)),
                int(lerp(CARD[1], GREEN[1], flash)),
                int(lerp(CARD[2], GREEN[2], flash)),
            )
            outline = YELLOW
            width = 5
        else:
            fill = CARD
            outline = (50, 58, 78)
            width = 3
        d.rounded_rectangle(
            [card_x0 + 28, top, card_x1 - 28, top + 96],
            22,
            fill=fill,
            outline=outline,
            width=width,
        )
        cf = font(36)
        bb = d.textbbox((0, 0), ch, font=cf)
        d.text(
            ((card_x0 + card_x1 - (bb[2] - bb[0])) // 2, top + 28),
            ch,
            font=cf,
            fill=WHITE,
        )

    rf = font(32)
    reason = (q.get("reason") or "")[:110]
    ry = y + 20 + 3 * 118 + 16
    for line in wrap(d, reason, rf, card_x1 - card_x0 - 40)[:3]:
        bb = d.textbbox((0, 0), line, font=rf)
        d.text(
            (card_x0 + (card_x1 - card_x0 - (bb[2] - bb[0])) // 2, ry),
            line,
            font=rf,
            fill=YELLOW,
        )
        ry += 42

    bob = math.sin(t_local * 2.8) * 5
    paste_mike(img, "happy", bob=bob, scale=0.95)
    return img


def frame_at(job: dict, timeline: list, t: float) -> Image.Image:
    seg = timeline[-1]
    for s in timeline:
        if s["start"] <= t < s["end"] or (s is timeline[-1] and t >= s["start"]):
            if t < s["end"] or s is timeline[-1]:
                seg = s
                if t < s["end"]:
                    break
    phase = seg.get("phase")
    qi = seg.get("q")
    q = q_by_index(job, qi)
    t_local = max(0.0, t - float(seg["start"]))
    dur = max(0.01, float(seg["end"]) - float(seg["start"]))

    if phase == "intro":
        return draw_intro(job, t_local)
    if phase == "outro":
        return draw_outro(job, t_local)
    if phase == "countdown" and q:
        remaining = max(0.0, float(seg["end"]) - t)
        return draw_ask(q, remaining=remaining, t_local=t_local, total_cd=dur)
    if phase == "ask" and q:
        return draw_ask(q, remaining=None, t_local=t_local)
    if phase == "reveal" and q:
        return draw_reveal(q, t_local)
    return draw_intro(job, t_local)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job", default="teaser_job.json")
    p.add_argument("--timeline", default="teaser_timeline.json")
    p.add_argument("--audio", required=True)
    p.add_argument("--out", default="output.mp4")
    args = p.parse_args()

    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    tl_path = Path(args.timeline)
    if not tl_path.exists():
        sys.exit("missing teaser_timeline.json — run assemble_teaser_audio.py first")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
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
            t = i / float(FPS)
            frame_at(job, timeline, t).save(tmp_path / f"frame_{i:05d}.png")
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
