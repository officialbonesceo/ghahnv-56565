#!/usr/bin/env python3
"""Mike — full-body + expressive teacher gestures (no side-walk)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 560, 900
HOODIE = (255, 200, 45, 255)
HOODIE_L = (255, 228, 120, 255)
HOODIE_D = (230, 170, 30, 255)
SKIN = (238, 195, 155, 255)
SKIN_D = (215, 165, 125, 255)
HAIR = (28, 24, 30, 255)
PANTS = (38, 46, 62, 255)
SHOE = (255, 215, 70, 255)
SHOE_W = (250, 250, 252, 255)
WHITE = (255, 255, 255, 255)
BLACK = (18, 16, 20, 255)
MOUTH_IN = (155, 55, 65, 255)
TEETH = (252, 250, 248, 255)
GLASS = (35, 38, 48, 230)
CX = W // 2


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
    oval(d, [cx - 18 * s, cy - 16 * s, cx + 18 * s, cy + 20 * s], SKIN)
    for dx in (-10, 0, 10):
        oval(d, [cx + dx * s - 5 * s, cy + 16 * s, cx + dx * s + 5 * s, cy + 34 * s], SKIN)


def draw_head(d, cx, hy, expr="neutral", tilt=0):
    # slight horizontal shift for lean
    cx = cx + tilt
    oval(d, [cx - 78, hy - 95, cx + 78, hy + 10], HAIR)
    oval(d, [cx - 70, hy - 78, cx + 70, hy + 72], SKIN)
    oval(d, [cx - 75, hy - 105, cx + 75, hy - 5], HAIR)
    d.polygon(
        [(cx - 25, hy - 70), (cx - 8, hy - 125), (cx + 12, hy - 68),
         (cx + 32, hy - 118), (cx + 55, hy - 65)],
        fill=HAIR,
    )
    oval(d, [cx - 82, hy - 8, cx - 62, hy + 28], SKIN)
    oval(d, [cx + 62, hy - 8, cx + 82, hy + 28], SKIN)
    ey = hy - 8
    if expr == "blink":
        d.line([(cx - 42, ey), (cx - 14, ey)], fill=BLACK, width=5)
        d.line([(cx + 14, ey), (cx + 42, ey)], fill=BLACK, width=5)
    else:
        oval(d, [cx - 48, ey - 22, cx - 12, ey + 22], WHITE, BLACK, 3)
        oval(d, [cx + 12, ey - 22, cx + 48, ey + 22], WHITE, BLACK, 3)
        oval(d, [cx - 36, ey - 8, cx - 18, ey + 10], BLACK)
        oval(d, [cx + 18, ey - 8, cx + 36, ey + 10], BLACK)
        oval(d, [cx - 30, ey - 10, cx - 22, ey - 2], WHITE)
        oval(d, [cx + 24, ey - 10, cx + 32, ey - 2], WHITE)
    if expr == "question":
        d.line([(cx - 45, ey - 32), (cx - 15, ey - 26)], fill=BLACK, width=4)
        d.line([(cx + 15, ey - 28), (cx + 45, ey - 34)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 48, ey - 38, cx - 12, ey - 14], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 12, ey - 38, cx + 48, ey - 14], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 45, ey - 30), (cx - 15, ey - 30)], fill=BLACK, width=3)
        d.line([(cx + 15, ey - 30), (cx + 45, ey - 30)], fill=BLACK, width=3)
    oval(d, [cx - 8, hy + 12, cx + 8, hy + 32], SKIN_D)
    d.ellipse([cx - 50, ey - 24, cx - 10, ey + 24], outline=GLASS, width=4)
    d.ellipse([cx + 10, ey - 24, cx + 50, ey + 24], outline=GLASS, width=4)
    d.line([(cx - 10, ey), (cx + 10, ey)], fill=GLASS, width=4)


def draw_mouth_on(d, cx, hy, kind="closed", tilt=0):
    cx = cx + tilt
    my = hy + 42
    if kind == "closed":
        d.arc([cx - 20, my - 2, cx + 20, my + 18], 20, 160, fill=BLACK, width=3)
    elif kind == "smile":
        d.arc([cx - 24, my - 4, cx + 24, my + 20], 15, 165, fill=BLACK, width=4)
    elif kind == "open":
        oval(d, [cx - 18, my, cx + 18, my + 26], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 12, my + 2, cx + 12, my + 10], TEETH)
    else:
        oval(d, [cx - 22, my, cx + 22, my + 32], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 14, my + 2, cx + 14, my + 10], TEETH)


def draw_torso(d, cx, shoulder_y):
    d.rounded_rectangle([cx - 95, shoulder_y, cx + 95, shoulder_y + 230], 45, fill=HOODIE)
    d.rounded_rectangle([cx - 55, shoulder_y + 55, cx + 55, shoulder_y + 190], 30, fill=HOODIE_L)
    d.arc([cx - 70, shoulder_y - 15, cx + 70, shoulder_y + 55], 200, 340, fill=HOODIE_D, width=8)
    d.line([(cx - 22, shoulder_y + 40), (cx - 22, shoulder_y + 110)], fill=WHITE, width=5)
    d.line([(cx + 22, shoulder_y + 40), (cx + 22, shoulder_y + 110)], fill=WHITE, width=5)
    oval(d, [cx - 28, shoulder_y + 105, cx - 16, shoulder_y + 120], WHITE)
    oval(d, [cx + 16, shoulder_y + 105, cx + 28, shoulder_y + 120], WHITE)


def draw_legs(d, cx, hip_y):
    d.rounded_rectangle([cx - 70, hip_y, cx + 70, hip_y + 40], 18, fill=PANTS)
    d.rounded_rectangle([cx - 68, hip_y + 20, cx - 12, hip_y + 200], 22, fill=PANTS)
    d.rounded_rectangle([cx + 12, hip_y + 20, cx + 68, hip_y + 200], 22, fill=PANTS)
    d.rounded_rectangle([cx - 78, hip_y + 185, cx - 5, hip_y + 230], 16, fill=SHOE)
    d.rounded_rectangle([cx - 78, hip_y + 210, cx - 5, hip_y + 232], 10, fill=SHOE_W)
    d.rounded_rectangle([cx + 5, hip_y + 185, cx + 78, hip_y + 230], 16, fill=SHOE)
    d.rounded_rectangle([cx + 5, hip_y + 210, cx + 78, hip_y + 232], 10, fill=SHOE_W)


def arms_down(d, cx, sy):
    limb(d, cx - 90, sy + 40, cx - 100, sy + 130, 36, HOODIE)
    limb(d, cx - 100, sy + 130, cx - 95, sy + 200, 32, HOODIE)
    hand(d, cx - 95, sy + 218)
    limb(d, cx + 90, sy + 40, cx + 100, sy + 130, 36, HOODIE)
    limb(d, cx + 100, sy + 130, cx + 95, sy + 200, 32, HOODIE)
    hand(d, cx + 95, sy + 218)


def arms_present(d, cx, sy):
    limb(d, cx - 90, sy + 45, cx - 155, sy + 55, 36, HOODIE)
    limb(d, cx - 155, sy + 55, cx - 185, sy + 70, 30, HOODIE)
    hand(d, cx - 195, sy + 80)
    limb(d, cx + 90, sy + 45, cx + 155, sy + 55, 36, HOODIE)
    limb(d, cx + 155, sy + 55, cx + 185, sy + 70, 30, HOODIE)
    hand(d, cx + 195, sy + 80)


def arms_point(d, cx, sy):
    limb(d, cx - 90, sy + 45, cx - 100, sy + 150, 34, HOODIE)
    hand(d, cx - 100, sy + 175)
    limb(d, cx + 90, sy + 40, cx + 155, sy - 10, 36, HOODIE)
    limb(d, cx + 155, sy - 10, cx + 195, sy - 40, 28, HOODIE)
    hand(d, cx + 205, sy - 50)
    d.line([(cx + 210, sy - 55), (cx + 245, sy - 75)], fill=SKIN, width=10)


def arms_explain(d, cx, sy):
    """One hand up teaching, one relaxed — classic tutor."""
    limb(d, cx - 90, sy + 40, cx - 100, sy + 140, 34, HOODIE)
    hand(d, cx - 100, sy + 165)
    limb(d, cx + 90, sy + 40, cx + 120, sy - 30, 36, HOODIE)
    limb(d, cx + 120, sy - 30, cx + 130, sy - 90, 30, HOODIE)
    hand(d, cx + 130, sy - 110)


def arms_shrug(d, cx, sy):
    limb(d, cx - 90, sy + 40, cx - 140, sy + 10, 36, HOODIE)
    limb(d, cx - 140, sy + 10, cx - 160, sy - 20, 28, HOODIE)
    hand(d, cx - 165, sy - 35)
    limb(d, cx + 90, sy + 40, cx + 140, sy + 10, 36, HOODIE)
    limb(d, cx + 140, sy + 10, cx + 160, sy - 20, 28, HOODIE)
    hand(d, cx + 165, sy - 35)


def arms_count(d, cx, sy):
    """Hold up three fingers energy — palm forward."""
    limb(d, cx - 90, sy + 40, cx - 95, sy + 150, 34, HOODIE)
    hand(d, cx - 95, sy + 175)
    limb(d, cx + 90, sy + 40, cx + 110, sy - 20, 36, HOODIE)
    limb(d, cx + 110, sy - 20, cx + 115, sy - 80, 30, HOODIE)
    # open palm
    oval(d, [cx + 95, sy - 120, cx + 140, sy - 70], SKIN)
    for i, dx in enumerate((-12, 0, 12)):
        oval(d, [cx + 110 + dx, sy - 145, cx + 122 + dx, sy - 115], SKIN)


def arms_chin(d, cx, sy):
    """Thoughtful — hand near chin."""
    limb(d, cx - 90, sy + 40, cx - 100, sy + 150, 34, HOODIE)
    hand(d, cx - 100, sy + 175)
    limb(d, cx + 90, sy + 40, cx + 70, sy + 20, 34, HOODIE)
    limb(d, cx + 70, sy + 20, cx + 45, sy - 10, 28, HOODIE)
    hand(d, cx + 35, sy - 5, 0.9)


def draw_pose(mode="stand", expr="neutral", mouth=None) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    oval(d, [cx - 90, 820, cx + 90, 860], (0, 0, 0, 50))

    head_y, shoulder_y, hip_y = 130, 210, 420
    tilt = 0

    if mode == "sit":
        hip_y, shoulder_y, head_y = 500, 280, 180
        d.rounded_rectangle([cx - 110, hip_y + 30, cx + 110, hip_y + 55], 8, fill=(55, 60, 75))
        d.rounded_rectangle([cx - 100, hip_y + 20, cx - 20, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx + 20, hip_y + 20, cx + 100, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx - 105, hip_y + 45, cx - 55, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx + 55, hip_y + 45, cx + 105, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx - 120, hip_y + 145, cx - 40, hip_y + 185], 14, fill=SHOE)
        d.rounded_rectangle([cx + 40, hip_y + 145, cx + 120, hip_y + 185], 14, fill=SHOE)
        draw_torso(d, cx, shoulder_y)
        arms_down(d, cx, shoulder_y)
        d.rounded_rectangle([cx - 18, head_y + 55, cx + 18, shoulder_y + 15], 10, fill=SKIN)
        draw_head(d, cx, head_y, expr)
        return img

    if mode == "lean":
        tilt = 18
        cx_body = cx + 12

    else:
        cx_body = cx

    draw_legs(d, cx_body, hip_y)
    draw_torso(d, cx_body, shoulder_y)

    if mode == "point":
        arms_point(d, cx_body, shoulder_y)
    elif mode == "present":
        arms_present(d, cx_body, shoulder_y)
    elif mode == "explain":
        arms_explain(d, cx_body, shoulder_y)
    elif mode == "shrug":
        arms_shrug(d, cx_body, shoulder_y)
        expr = "question"
    elif mode == "count":
        arms_count(d, cx_body, shoulder_y)
    elif mode == "think":
        arms_chin(d, cx_body, shoulder_y)
        expr = "question"
    elif mode == "lean":
        arms_explain(d, cx_body, shoulder_y)
    else:
        arms_down(d, cx_body, shoulder_y)

    d.rounded_rectangle(
        [cx_body - 18 + tilt // 2, head_y + 55, cx_body + 18 + tilt // 2, shoulder_y + 12],
        10, fill=SKIN,
    )
    draw_head(d, cx_body, head_y, expr, tilt=tilt)
    if mouth:
        draw_mouth_on(d, cx_body, head_y, mouth, tilt=tilt)
    return img


def mouth_overlay(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    draw_mouth_on(d, CX, 130, kind)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)

    draw_pose("stand", "neutral").save(out / "body.png")
    draw_pose("stand", "happy").save(out / "body_happy.png")
    draw_pose("stand", "question").save(out / "body_question.png")
    draw_pose("stand", "blink").save(out / "body_blink.png")
    draw_pose("present", "welcoming").save(out / "body_present.png")
    draw_pose("point", "neutral").save(out / "arm_point.png")
    draw_pose("sit", "neutral").save(out / "body_sit.png")
    # new gestures
    draw_pose("explain", "happy").save(out / "body_explain.png")
    draw_pose("shrug", "question").save(out / "body_shrug.png")
    draw_pose("count", "neutral").save(out / "body_count.png")
    draw_pose("think", "question").save(out / "body_think.png")
    draw_pose("lean", "happy").save(out / "body_lean.png")

    # keep walk files as stand fallback so old refs don't break
    draw_pose("stand", "neutral", mouth="closed").save(out / "walk_l0.png")
    draw_pose("stand", "neutral", mouth="closed").save(out / "walk_l1.png")
    draw_pose("stand", "neutral", mouth="closed").save(out / "walk_r0.png")
    draw_pose("stand", "neutral", mouth="closed").save(out / "walk_r1.png")

    for kind, fname in [
        ("closed", "mouth_closed.png"),
        ("open", "mouth_open.png"),
        ("wide", "mouth_wide.png"),
        ("smile", "mouth_smile.png"),
    ]:
        mouth_overlay(kind).save(out / fname)

    print("OK gestures: explain shrug count think lean")


if __name__ == "__main__":
    main()
