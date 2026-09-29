#!/usr/bin/env python3
"""Mike sprite layers — sheet art when possible (fixed-seed fetch), else PIL."""
from __future__ import annotations

import io
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw

W, H = 560, 900

HOODIE = (255, 205, 40, 255)
HOODIE_L = (255, 230, 110, 255)
HOODIE_D = (235, 175, 25, 255)
SKIN = (196, 140, 95, 255)
SKIN_D = (168, 112, 72, 255)
SKIN_L = (220, 170, 125, 255)
HAIR = (32, 22, 18, 255)
PANTS = (28, 40, 70, 255)
SHOE = (30, 30, 35, 255)
SHOE_W = (245, 245, 248, 255)
WHITE = (255, 255, 255, 255)
BLACK = (18, 14, 12, 255)
MOUTH_IN = (150, 55, 60, 255)
TEETH = (252, 250, 248, 255)
BADGE = (40, 55, 90, 255)
CX = W // 2

# Fixed seeds → same Mike every run (brand consistency)
SHEET_PROMPTS = {
    "body.png": (
        "full body front view 2D cartoon animation sprite, young male tutor named Mike, "
        "warm brown skin, short dark hair, friendly smile, bright yellow hoodie with kangaroo pocket, "
        "navy blue pants, white sneakers, clean solid colors, bold outlines, white background, "
        "centered standing, arms relaxed at sides, no text, no watermark",
        4242,
    ),
    "body_happy.png": (
        "full body front view 2D cartoon animation sprite, young male tutor Mike, warm brown skin, "
        "short dark hair, big happy smile, bright yellow hoodie, navy pants, white sneakers, "
        "clean solid colors, bold outlines, white background, standing, no text",
        4243,
    ),
    "body_explain.png": (
        "full body front view 2D cartoon animation sprite, young male tutor Mike, warm brown skin, "
        "short dark hair, teaching pose one hand raised explaining, bright yellow hoodie, navy pants, "
        "white sneakers, clean solid colors, bold outlines, white background, no text",
        4244,
    ),
    "arm_point.png": (
        "full body front view 2D cartoon animation sprite, young male tutor Mike, warm brown skin, "
        "short dark hair, pointing with right hand to the side, bright yellow hoodie, navy pants, "
        "white sneakers, clean solid colors, bold outlines, white background, no text",
        4245,
    ),
    "body_present.png": (
        "full body front view 2D cartoon animation sprite, young male tutor Mike, warm brown skin, "
        "short dark hair, both arms open welcoming present pose, bright yellow hoodie, navy pants, "
        "white sneakers, clean solid colors, bold outlines, white background, no text",
        4246,
    ),
}


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2 - 1, 6)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def hand(d, cx, cy, scale=1.0):
    s = scale
    oval(d, [cx - 17 * s, cy - 15 * s, cx + 17 * s, cy + 18 * s], SKIN)
    for dx in (-9, 0, 9):
        oval(d, [cx + dx * s - 5 * s, cy + 14 * s, cx + dx * s + 5 * s, cy + 32 * s], SKIN)


def draw_head(d, cx, hy, expr="neutral", tilt=0):
    cx = cx + tilt
    oval(d, [cx - 82, hy - 100, cx + 82, hy + 15], HAIR)
    oval(d, [cx - 68, hy - 72, cx + 68, hy + 70], SKIN)
    oval(d, [cx - 78, hy - 108, cx + 78, hy - 8], HAIR)
    d.polygon([(cx - 70, hy - 40), (cx - 95, hy - 55), (cx - 88, hy - 20), (cx - 72, hy - 10)], fill=HAIR)
    d.polygon([(cx + 70, hy - 40), (cx + 95, hy - 55), (cx + 88, hy - 20), (cx + 72, hy - 10)], fill=HAIR)
    d.polygon([(cx - 30, hy - 70), (cx - 15, hy - 125), (cx + 5, hy - 75), (cx + 25, hy - 120), (cx + 45, hy - 70)], fill=HAIR)
    oval(d, [cx - 80, hy - 5, cx - 60, hy + 28], SKIN)
    oval(d, [cx + 60, hy - 5, cx + 80, hy + 28], SKIN)
    ey = hy - 6
    if expr == "blink":
        d.line([(cx - 40, ey), (cx - 12, ey)], fill=BLACK, width=5)
        d.line([(cx + 12, ey), (cx + 40, ey)], fill=BLACK, width=5)
    else:
        oval(d, [cx - 46, ey - 24, cx - 10, ey + 24], WHITE, BLACK, 3)
        oval(d, [cx + 10, ey - 24, cx + 46, ey + 24], WHITE, BLACK, 3)
        oval(d, [cx - 34, ey - 10, cx - 16, ey + 12], (45, 28, 18, 255))
        oval(d, [cx + 16, ey - 10, cx + 34, ey + 12], (45, 28, 18, 255))
        oval(d, [cx - 30, ey - 4, cx - 20, ey + 8], BLACK)
        oval(d, [cx + 20, ey - 4, cx + 30, ey + 8], BLACK)
        oval(d, [cx - 28, ey - 10, cx - 22, ey - 3], WHITE)
        oval(d, [cx + 22, ey - 10, cx + 28, ey - 3], WHITE)
    if expr == "question":
        d.line([(cx - 44, ey - 34), (cx - 12, ey - 26)], fill=BLACK, width=4)
        d.line([(cx + 12, ey - 28), (cx + 44, ey - 36)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 46, ey - 40, cx - 10, ey - 12], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 10, ey - 40, cx + 46, ey - 12], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 42, ey - 32), (cx - 14, ey - 32)], fill=BLACK, width=3)
        d.line([(cx + 14, ey - 32), (cx + 42, ey - 32)], fill=BLACK, width=3)
    oval(d, [cx - 7, hy + 10, cx + 7, hy + 30], SKIN_D)


def draw_mouth_on(d, cx, hy, kind="closed", tilt=0):
    cx = cx + tilt
    my = hy + 44
    if kind == "closed":
        d.arc([cx - 18, my - 2, cx + 18, my + 16], 25, 155, fill=BLACK, width=3)
    elif kind == "smile":
        d.arc([cx - 24, my - 4, cx + 24, my + 22], 15, 165, fill=BLACK, width=4)
    elif kind == "open":
        oval(d, [cx - 16, my, cx + 16, my + 24], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 11, my + 2, cx + 11, my + 10], TEETH)
    else:
        oval(d, [cx - 22, my, cx + 22, my + 30], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 14, my + 2, cx + 14, my + 10], TEETH)


def draw_torso(d, cx, shoulder_y):
    d.rounded_rectangle([cx - 98, shoulder_y, cx + 98, shoulder_y + 235], 48, fill=HOODIE)
    d.rounded_rectangle([cx - 52, shoulder_y + 95, cx + 52, shoulder_y + 175], 22, fill=HOODIE_D)
    d.line([(cx, shoulder_y + 95), (cx, shoulder_y + 175)], fill=HOODIE_L, width=3)
    d.arc([cx - 72, shoulder_y - 12, cx + 72, shoulder_y + 58], 200, 340, fill=HOODIE_D, width=9)
    d.line([(cx - 20, shoulder_y + 38), (cx - 20, shoulder_y + 100)], fill=WHITE, width=4)
    d.line([(cx + 20, shoulder_y + 38), (cx + 20, shoulder_y + 100)], fill=WHITE, width=4)
    oval(d, [cx - 26, shoulder_y + 98, cx - 14, shoulder_y + 112], WHITE)
    oval(d, [cx + 14, shoulder_y + 98, cx + 26, shoulder_y + 112], WHITE)
    d.rounded_rectangle([cx + 40, shoulder_y + 48, cx + 78, shoulder_y + 78], 6, fill=BADGE)
    d.rectangle([cx + 44, shoulder_y + 52, cx + 74, shoulder_y + 74], fill=WHITE)
    d.line([(cx + 59, shoulder_y + 52), (cx + 59, shoulder_y + 74)], fill=BADGE, width=2)


def draw_legs(d, cx, hip_y):
    d.rounded_rectangle([cx - 72, hip_y, cx + 72, hip_y + 38], 18, fill=PANTS)
    d.rounded_rectangle([cx - 70, hip_y + 18, cx - 10, hip_y + 205], 24, fill=PANTS)
    d.rounded_rectangle([cx + 10, hip_y + 18, cx + 70, hip_y + 205], 24, fill=PANTS)
    d.rounded_rectangle([cx - 80, hip_y + 190, cx - 2, hip_y + 232], 14, fill=SHOE)
    d.rounded_rectangle([cx - 80, hip_y + 215, cx - 2, hip_y + 235], 10, fill=SHOE_W)
    d.rounded_rectangle([cx + 2, hip_y + 190, cx + 80, hip_y + 232], 14, fill=SHOE)
    d.rounded_rectangle([cx + 2, hip_y + 215, cx + 80, hip_y + 235], 10, fill=SHOE_W)


def arms_down(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 102, sy + 135, 38, HOODIE)
    limb(d, cx - 102, sy + 135, cx - 96, sy + 205, 34, HOODIE)
    hand(d, cx - 96, sy + 222)
    limb(d, cx + 92, sy + 42, cx + 102, sy + 135, 38, HOODIE)
    limb(d, cx + 102, sy + 135, cx + 96, sy + 205, 34, HOODIE)
    hand(d, cx + 96, sy + 222)


def arms_present(d, cx, sy):
    limb(d, cx - 92, sy + 48, cx - 158, sy + 58, 38, HOODIE)
    limb(d, cx - 158, sy + 58, cx - 188, sy + 72, 32, HOODIE)
    hand(d, cx - 198, sy + 82)
    limb(d, cx + 92, sy + 48, cx + 158, sy + 58, 38, HOODIE)
    limb(d, cx + 158, sy + 58, cx + 188, sy + 72, 32, HOODIE)
    hand(d, cx + 198, sy + 82)


def arms_point(d, cx, sy):
    limb(d, cx - 92, sy + 48, cx - 102, sy + 155, 36, HOODIE)
    hand(d, cx - 102, sy + 178)
    limb(d, cx + 92, sy + 42, cx + 158, sy - 8, 38, HOODIE)
    limb(d, cx + 158, sy - 8, cx + 198, sy - 42, 30, HOODIE)
    hand(d, cx + 208, sy - 52)


def arms_explain(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 102, sy + 145, 36, HOODIE)
    hand(d, cx - 102, sy + 168)
    limb(d, cx + 92, sy + 42, cx + 122, sy - 28, 38, HOODIE)
    limb(d, cx + 122, sy - 28, cx + 132, sy - 92, 32, HOODIE)
    hand(d, cx + 132, sy - 112)


def arms_shrug(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 142, sy + 12, 38, HOODIE)
    limb(d, cx - 142, sy + 12, cx - 162, sy - 22, 30, HOODIE)
    hand(d, cx - 168, sy - 38)
    limb(d, cx + 92, sy + 42, cx + 142, sy + 12, 38, HOODIE)
    limb(d, cx + 142, sy + 12, cx + 162, sy - 22, 30, HOODIE)
    hand(d, cx + 168, sy - 38)


def arms_count(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 98, sy + 155, 36, HOODIE)
    hand(d, cx - 98, sy + 178)
    limb(d, cx + 92, sy + 42, cx + 112, sy - 22, 38, HOODIE)
    limb(d, cx + 112, sy - 22, cx + 118, sy - 82, 32, HOODIE)
    oval(d, [cx + 98, sy - 122, cx + 142, sy - 72], SKIN)


def arms_chin(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 102, sy + 155, 36, HOODIE)
    hand(d, cx - 102, sy + 178)
    limb(d, cx + 92, sy + 42, cx + 72, sy + 22, 36, HOODIE)
    limb(d, cx + 72, sy + 22, cx + 48, sy - 8, 30, HOODIE)
    hand(d, cx + 38, sy - 2, 0.9)


def draw_pose(mode="stand", expr="neutral", mouth=None) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    hy, sy, hip_y = 128, 208, 418
    tilt = 0
    if mode == "sit":
        hip_y, sy, hy = 500, 280, 180
        d.rounded_rectangle([cx - 110, hip_y + 30, cx + 110, hip_y + 55], 8, fill=(50, 55, 70))
        draw_torso(d, cx, sy)
        arms_down(d, cx, sy)
        d.rounded_rectangle([cx - 16, hy + 55, cx + 16, sy + 15], 10, fill=SKIN)
        draw_head(d, cx, hy, expr)
        return img
    cx_body = cx + (10 if mode == "lean" else 0)
    tilt = 16 if mode == "lean" else 0
    draw_legs(d, cx_body, hip_y)
    draw_torso(d, cx_body, sy)
    if mode == "point":
        arms_point(d, cx_body, sy)
    elif mode == "present":
        arms_present(d, cx_body, sy)
    elif mode == "explain":
        arms_explain(d, cx_body, sy)
    elif mode == "shrug":
        arms_shrug(d, cx_body, sy)
        expr = "question"
    elif mode == "count":
        arms_count(d, cx_body, sy)
    elif mode == "think":
        arms_chin(d, cx_body, sy)
        expr = "question"
    elif mode == "lean":
        arms_explain(d, cx_body, sy)
    else:
        arms_down(d, cx_body, sy)
    d.rounded_rectangle([cx_body - 16 + tilt // 2, hy + 55, cx_body + 16 + tilt // 2, sy + 14], 10, fill=SKIN)
    draw_head(d, cx_body, hy, expr, tilt=tilt)
    if mouth:
        draw_mouth_on(d, cx_body, hy, mouth, tilt=tilt)
    return img


def mouth_overlay(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    draw_mouth_on(d, CX, 128, kind)
    return img


def _whiten_to_alpha(im: Image.Image) -> Image.Image:
    """Turn near-white background transparent for sprite paste."""
    im = im.convert("RGBA")
    pixels = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > 240 and g > 240 and b > 240:
                pixels[x, y] = (r, g, b, 0)
            elif r > 220 and g > 220 and b > 220:
                pixels[x, y] = (r, g, b, max(0, 255 - (r + g + b - 660)))
    return im


def fetch_sheet(prompt: str, seed: int) -> Image.Image | None:
    url = (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt)
        + f"?width=512&height=768&seed={seed}&nologo=true&enhance=true"
    )
    try:
        r = requests.get(url, timeout=90)
        if r.status_code != 200 or len(r.content) < 1000:
            print("sheet fetch fail", r.status_code, file=sys.stderr)
            return None
        im = Image.open(io.BytesIO(r.content)).convert("RGBA")
        im = _whiten_to_alpha(im)
        # fit into W x H canvas
        canvas = blank()
        im.thumbnail((W - 20, H - 40), Image.Resampling.LANCZOS)
        x = (W - im.width) // 2
        y = H - im.height - 20
        canvas.paste(im, (x, y), im)
        return canvas
    except Exception as e:
        print("sheet fetch error", e, file=sys.stderr)
        return None


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)

    if (out / "LOCKED").exists():
        print("LOCKED — keeping prebuilt sheet PNGs", file=sys.stderr)
        return

    sheet_ok = 0
    for fname, (prompt, seed) in SHEET_PROMPTS.items():
        img = fetch_sheet(prompt, seed)
        if img is not None:
            img.save(out / fname)
            sheet_ok += 1
            print("SHEET", fname, file=sys.stderr)
        else:
            # PIL fallback for this pose
            if "explain" in fname:
                draw_pose("explain", "happy").save(out / fname)
            elif "point" in fname:
                draw_pose("point", "neutral").save(out / fname)
            elif "present" in fname:
                draw_pose("present", "welcoming").save(out / fname)
            elif "happy" in fname:
                draw_pose("stand", "happy").save(out / fname)
            else:
                draw_pose("stand", "neutral").save(out / fname)
            print("PIL fallback", fname, file=sys.stderr)

    # remaining poses always PIL (gestures)
    draw_pose("stand", "question").save(out / "body_question.png")
    draw_pose("stand", "blink").save(out / "body_blink.png")
    draw_pose("sit", "neutral").save(out / "body_sit.png")
    draw_pose("shrug", "question").save(out / "body_shrug.png")
    draw_pose("count", "neutral").save(out / "body_count.png")
    draw_pose("think", "question").save(out / "body_think.png")
    draw_pose("lean", "happy").save(out / "body_lean.png")
    for name in ("walk_l0.png", "walk_l1.png", "walk_r0.png", "walk_r1.png"):
        draw_pose("stand", "neutral", mouth="closed").save(out / name)
    for kind, fname in [
        ("closed", "mouth_closed.png"),
        ("open", "mouth_open.png"),
        ("wide", "mouth_wide.png"),
        ("smile", "mouth_smile.png"),
    ]:
        mouth_overlay(kind).save(out / fname)

    print(f"OK sheet_ok={sheet_ok}/{len(SHEET_PROMPTS)} + PIL gestures")


if __name__ == "__main__":
    main()
