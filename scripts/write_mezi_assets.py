#!/usr/bin/env python3
"""Mike sprite layers — PIL only (no external AI stills)."""
from __future__ import annotations

from pathlib import Path

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


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2 - 1, 6)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def hand(d, cx, cy, scale=1.0, angle="down"):
    """Cleaner cartoon hand: palm + thumb + 3-4 fingers."""
    s = scale
    oval(d, [cx - 16 * s, cy - 14 * s, cx + 16 * s, cy + 16 * s], SKIN)
    for i, dx in enumerate((-11, -4, 4, 11)):
        fy0 = cy + 12 * s
        fy1 = cy + (28 + (i % 2) * 3) * s
        oval(d, [cx + dx * s - 4.5 * s, fy0, cx + dx * s + 4.5 * s, fy1], SKIN)
    if angle == "down":
        oval(d, [cx + 14 * s, cy - 4 * s, cx + 26 * s, cy + 12 * s], SKIN)
    else:
        oval(d, [cx - 26 * s, cy - 4 * s, cx - 14 * s, cy + 12 * s], SKIN)


def draw_head(d, cx, hy, expr="neutral", tilt=0):
    cx = cx + tilt
    oval(d, [cx - 82, hy - 100, cx + 82, hy + 15], HAIR)
    oval(d, [cx - 68, hy - 72, cx + 68, hy + 70], SKIN)
    oval(d, [cx - 78, hy - 108, cx + 78, hy - 8], HAIR)
    d.polygon([(cx - 70, hy - 40), (cx - 95, hy - 55), (cx - 88, hy - 20), (cx - 72, hy - 10)], fill=HAIR)
    d.polygon([(cx + 70, hy - 40), (cx + 95, hy - 55), (cx + 88, hy - 20), (cx + 72, hy - 10)], fill=HAIR)
    d.polygon(
        [(cx - 30, hy - 70), (cx - 15, hy - 125), (cx + 5, hy - 75), (cx + 25, hy - 120), (cx + 45, hy - 70)],
        fill=HAIR,
    )
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
    oval(d, [cx - 58, hy + 18, cx - 38, hy + 38], (*SKIN_L[:3], 80))
    oval(d, [cx + 38, hy + 18, cx + 58, hy + 38], (*SKIN_L[:3], 80))


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
    d.rounded_rectangle([cx - 68, hip_y + 12, cx - 8, hip_y + 205], 28, fill=PANTS)
    d.rounded_rectangle([cx + 8, hip_y + 12, cx + 68, hip_y + 205], 28, fill=PANTS)
    d.rounded_rectangle([cx - 78, hip_y + 188, cx - 4, hip_y + 232], 16, fill=SHOE)
    d.rounded_rectangle([cx - 78, hip_y + 214, cx - 4, hip_y + 236], 12, fill=SHOE_W)
    d.rounded_rectangle([cx + 4, hip_y + 188, cx + 78, hip_y + 232], 16, fill=SHOE)
    d.rounded_rectangle([cx + 4, hip_y + 214, cx + 78, hip_y + 236], 12, fill=SHOE_W)


def arms_down(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 100, sy + 130, 36, HOODIE)
    limb(d, cx - 100, sy + 130, cx - 94, sy + 200, 32, HOODIE)
    hand(d, cx - 94, sy + 218, angle="down")
    limb(d, cx + 92, sy + 42, cx + 100, sy + 130, 36, HOODIE)
    limb(d, cx + 100, sy + 130, cx + 94, sy + 200, 32, HOODIE)
    hand(d, cx + 94, sy + 218, angle="down")


def arms_present(d, cx, sy):
    limb(d, cx - 92, sy + 48, cx - 140, sy + 70, 36, HOODIE)
    limb(d, cx - 140, sy + 70, cx - 160, sy + 95, 30, HOODIE)
    hand(d, cx - 168, sy + 108, angle="left")
    limb(d, cx + 92, sy + 48, cx + 140, sy + 70, 36, HOODIE)
    limb(d, cx + 140, sy + 70, cx + 160, sy + 95, 30, HOODIE)
    hand(d, cx + 168, sy + 108, angle="down")


def arms_point(d, cx, sy):
    limb(d, cx - 92, sy + 48, cx - 100, sy + 150, 34, HOODIE)
    hand(d, cx - 100, sy + 172, angle="down")
    limb(d, cx + 92, sy + 42, cx + 145, sy + 5, 36, HOODIE)
    limb(d, cx + 145, sy + 5, cx + 175, sy - 28, 28, HOODIE)
    hand(d, cx + 182, sy - 38, angle="down")
    d.line([(cx + 186, sy - 42), (cx + 215, sy - 58)], fill=SKIN, width=9)


def arms_explain(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 100, sy + 140, 34, HOODIE)
    hand(d, cx - 100, sy + 162, angle="down")
    limb(d, cx + 92, sy + 42, cx + 118, sy - 10, 36, HOODIE)
    limb(d, cx + 118, sy - 10, cx + 125, sy - 70, 30, HOODIE)
    hand(d, cx + 125, sy - 90, angle="down")


def arms_shrug(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 135, sy + 18, 36, HOODIE)
    limb(d, cx - 135, sy + 18, cx - 150, sy - 10, 28, HOODIE)
    hand(d, cx - 155, sy - 24, angle="left")
    limb(d, cx + 92, sy + 42, cx + 135, sy + 18, 36, HOODIE)
    limb(d, cx + 135, sy + 18, cx + 150, sy - 10, 28, HOODIE)
    hand(d, cx + 155, sy - 24, angle="down")


def arms_count(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 98, sy + 150, 34, HOODIE)
    hand(d, cx - 98, sy + 172, angle="down")
    limb(d, cx + 92, sy + 42, cx + 110, sy - 10, 36, HOODIE)
    limb(d, cx + 110, sy - 10, cx + 115, sy - 70, 30, HOODIE)
    oval(d, [cx + 95, sy - 115, cx + 138, sy - 68], SKIN)
    for dx in (-12, 0, 12):
        oval(d, [cx + 110 + dx, sy - 140, cx + 122 + dx, sy - 112], SKIN)


def arms_chin(d, cx, sy):
    limb(d, cx - 92, sy + 42, cx - 100, sy + 150, 34, HOODIE)
    hand(d, cx - 100, sy + 172, angle="down")
    limb(d, cx + 92, sy + 42, cx + 72, sy + 22, 34, HOODIE)
    limb(d, cx + 72, sy + 22, cx + 48, sy - 5, 28, HOODIE)
    hand(d, cx + 38, sy + 2, 0.9, angle="down")


def draw_pose(mode="stand", expr="neutral", mouth=None) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    oval(d, [cx - 90, 820, cx + 90, 860], (0, 0, 0, 45))
    head_y, shoulder_y, hip_y = 128, 208, 418
    tilt = 0

    if mode == "sit":
        hip_y, shoulder_y, head_y = 500, 280, 180
        d.rounded_rectangle([cx - 110, hip_y + 30, cx + 110, hip_y + 55], 8, fill=(50, 55, 70))
        d.rounded_rectangle([cx - 100, hip_y + 20, cx - 20, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx + 20, hip_y + 20, cx + 100, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx - 105, hip_y + 45, cx - 55, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx + 55, hip_y + 45, cx + 105, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx - 120, hip_y + 145, cx - 40, hip_y + 185], 14, fill=SHOE)
        d.rounded_rectangle([cx + 40, hip_y + 145, cx + 120, hip_y + 185], 14, fill=SHOE)
        draw_torso(d, cx, shoulder_y)
        arms_down(d, cx, shoulder_y)
        d.rounded_rectangle([cx - 16, head_y + 55, cx + 16, shoulder_y + 15], 10, fill=SKIN)
        draw_head(d, cx, head_y, expr)
        if mouth:
            draw_mouth_on(d, cx, head_y, mouth)
        return img

    if mode == "lean":
        tilt = 16
        cx_body = cx + 10
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
        [cx_body - 16 + tilt // 2, head_y + 55, cx_body + 16 + tilt // 2, shoulder_y + 14],
        10,
        fill=SKIN,
    )
    draw_head(d, cx_body, head_y, expr, tilt=tilt)
    if mouth:
        draw_mouth_on(d, cx_body, head_y, mouth, tilt=tilt)
    return img


def mouth_overlay(kind: str) -> Image.Image:
    """Mouth drawn at the same head position as the body sprites (paste at 0,0)."""
    img = blank()
    d = ImageDraw.Draw(img)
    draw_mouth_on(d, CX, 128, kind)
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
    draw_pose("point", "neutral").save(out / "body_point.png")
    draw_pose("sit", "neutral").save(out / "body_sit.png")
    draw_pose("explain", "happy").save(out / "body_explain.png")
    draw_pose("shrug", "question").save(out / "body_shrug.png")
    draw_pose("count", "neutral").save(out / "body_count.png")
    draw_pose("think", "question").save(out / "body_think.png")
    draw_pose("lean", "happy").save(out / "body_lean.png")

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

    print("OK PIL Mike — fixed mouth anchor, hands, legs, body_point")


if __name__ == "__main__":
    main()
