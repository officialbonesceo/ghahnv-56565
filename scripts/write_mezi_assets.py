#!/usr/bin/env python3
"""Mike host layers: front, side walk, point, present (open arms)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 420, 720
HOODIE = (255, 196, 40, 255)
HOODIE_S = (255, 220, 100, 255)
HOODIE_D = (230, 165, 25, 255)
SKIN = (210, 155, 115, 255)
HAIR = (28, 24, 30, 255)
PANTS = (40, 44, 58, 255)
SHOE = (22, 22, 28, 255)
WHITE = (255, 255, 255, 255)
BLACK = (25, 22, 28, 255)
MOUTH_IN = (95, 35, 45, 255)
TEETH = (250, 245, 240, 255)

CX = W // 2
CY = 400
HY = CY - 70
MOUTH_Y = HY + 26


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2, 4)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def draw_head_front(d, cx, hy):
    oval(d, [cx - 58, hy - 66, cx + 58, hy + 10], HAIR)
    oval(d, [cx - 50, hy - 50, cx + 50, hy + 46], SKIN)
    oval(d, [cx - 56, hy - 76, cx + 56, hy - 8], HAIR)
    oval(d, [cx - 46, hy - 28, cx + 46, hy + 40], SKIN)
    for ox, oy, r in [(-34, -74, 18), (-4, -84, 20), (18, -84, 20), (38, -74, 16)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    oval(d, [cx - 62, hy - 6, cx - 46, hy + 20], SKIN)
    oval(d, [cx + 46, hy - 6, cx + 62, hy + 20], SKIN)
    ey = hy - 4
    oval(d, [cx - 30, ey - 12, cx - 8, ey + 10], WHITE, BLACK, 3)
    oval(d, [cx + 8, ey - 12, cx + 30, ey + 10], WHITE, BLACK, 3)
    oval(d, [cx - 24, ey - 4, cx - 14, ey + 6], BLACK)
    oval(d, [cx + 14, ey - 4, cx + 24, ey + 6], BLACK)


def draw_head_side(d, cx, hy, facing: str = "left"):
    """Side profile: one ear, one eye, nose toward direction of travel."""
    # facing left means nose points left (walk toward left of screen)
    sign = -1 if facing == "left" else 1
    # hair
    oval(d, [cx - 48, hy - 70, cx + 48, hy + 8], HAIR)
    oval(d, [cx - 42, hy - 52, cx + 42, hy + 44], SKIN)
    oval(d, [cx - 50, hy - 78, cx + 40, hy - 10], HAIR)
    # ear (visible on side)
    ear_x = cx - sign * 40
    oval(d, [ear_x - 12, hy - 8, ear_x + 12, hy + 22], SKIN, BLACK, 2)
    oval(d, [ear_x - 6, hy - 2, ear_x + 6, hy + 14], (190, 140, 105, 255))
    # eye
    eye_x = cx + sign * 12
    oval(d, [eye_x - 10, hy - 14, eye_x + 10, hy + 8], WHITE, BLACK, 2)
    oval(d, [eye_x - 4, hy - 6, eye_x + 4, hy + 2], BLACK)
    # nose tip
    nx = cx + sign * 38
    oval(d, [nx - 6, hy + 2, nx + 6, hy + 16], SKIN)


def draw_body(mode: str = "front") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy, hy = CX, CY, HY

    oval(d, [cx - 60, cy + 155, cx + 60, cy + 178], (0, 0, 0, 40))

    if mode == "side_left":
        # legs staggered (walk)
        limb(d, cx - 6, cy + 78, cx - 28, cy + 155, 26, PANTS)
        limb(d, cx + 8, cy + 78, cx + 22, cy + 150, 26, PANTS)
        oval(d, [cx - 48, cy + 148, cx - 8, cy + 176], SHOE)
        oval(d, [cx + 4, cy + 142, cx + 44, cy + 172], SHOE)
        d.rounded_rectangle([cx - 36, cy + 2, cx + 36, cy + 92], 22, fill=HOODIE)
        # near arm swing back, far arm forward
        limb(d, cx + 10, cy + 28, cx + 40, cy + 80, 24, HOODIE)
        oval(d, [cx + 32, cy + 72, cx + 56, cy + 96], SKIN)
        limb(d, cx - 8, cy + 30, cx - 45, cy + 20, 24, HOODIE)
        oval(d, [cx - 58, cy + 8, cx - 34, cy + 32], SKIN)
        d.rectangle([cx - 16, cy - 6, cx + 16, cy + 16], fill=SKIN)
        draw_head_side(d, cx, hy, "left")

    elif mode == "side_right":
        limb(d, cx + 6, cy + 78, cx + 28, cy + 155, 26, PANTS)
        limb(d, cx - 8, cy + 78, cx - 22, cy + 150, 26, PANTS)
        oval(d, [cx + 8, cy + 148, cx + 48, cy + 176], SHOE)
        oval(d, [cx - 44, cy + 142, cx - 4, cy + 172], SHOE)
        d.rounded_rectangle([cx - 36, cy + 2, cx + 36, cy + 92], 22, fill=HOODIE)
        limb(d, cx - 10, cy + 28, cx - 40, cy + 80, 24, HOODIE)
        oval(d, [cx - 56, cy + 72, cx - 32, cy + 96], SKIN)
        limb(d, cx + 8, cy + 30, cx + 45, cy + 20, 24, HOODIE)
        oval(d, [cx + 34, cy + 8, cx + 58, cy + 32], SKIN)
        d.rectangle([cx - 16, cy - 6, cx + 16, cy + 16], fill=SKIN)
        draw_head_side(d, cx, hy, "right")

    elif mode == "point":
        limb(d, cx - 16, cy + 78, cx - 16, cy + 155, 26, PANTS)
        limb(d, cx + 16, cy + 78, cx + 16, cy + 155, 26, PANTS)
        oval(d, [cx - 38, cy + 148, cx + 2, cy + 176], SHOE)
        oval(d, [cx - 2, cy + 148, cx + 38, cy + 176], SHOE)
        d.rounded_rectangle([cx - 50, cy + 2, cx + 50, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 34, cy + 28, cx + 34, cy + 82], 16, fill=HOODIE_S)
        # arm up-right pointing
        limb(d, cx + 40, cy + 28, cx + 105, cy - 30, 26, HOODIE)
        oval(d, [cx + 96, cy - 48, cx + 122, cy - 22], SKIN)
        limb(d, cx + 114, cy - 36, cx + 145, cy - 55, 11, SKIN)
        limb(d, cx - 40, cy + 32, cx - 70, cy + 88, 24, HOODIE)
        oval(d, [cx - 88, cy + 78, cx - 64, cy + 102], SKIN)
        d.rectangle([cx - 18, cy - 6, cx + 18, cy + 16], fill=SKIN)
        draw_head_front(d, cx, hy)

    elif mode == "present":
        # open arms, teacher stage pose
        limb(d, cx - 16, cy + 78, cx - 16, cy + 155, 26, PANTS)
        limb(d, cx + 16, cy + 78, cx + 16, cy + 155, 26, PANTS)
        oval(d, [cx - 38, cy + 148, cx + 2, cy + 176], SHOE)
        oval(d, [cx - 2, cy + 148, cx + 38, cy + 176], SHOE)
        d.rounded_rectangle([cx - 50, cy + 2, cx + 50, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 34, cy + 28, cx + 34, cy + 82], 16, fill=HOODIE_S)
        limb(d, cx - 42, cy + 30, cx - 100, cy + 10, 26, HOODIE)
        oval(d, [cx - 118, cy - 2, cx - 92, cy + 24], SKIN)
        limb(d, cx + 42, cy + 30, cx + 100, cy + 10, 26, HOODIE)
        oval(d, [cx + 92, cy - 2, cx + 118, cy + 24], SKIN)
        d.rectangle([cx - 18, cy - 6, cx + 18, cy + 16], fill=SKIN)
        draw_head_front(d, cx, hy)

    else:  # front talk
        limb(d, cx - 16, cy + 78, cx - 16, cy + 155, 26, PANTS)
        limb(d, cx + 16, cy + 78, cx + 16, cy + 155, 26, PANTS)
        oval(d, [cx - 38, cy + 148, cx + 2, cy + 176], SHOE)
        oval(d, [cx - 2, cy + 148, cx + 38, cy + 176], SHOE)
        d.rounded_rectangle([cx - 50, cy + 2, cx + 50, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 34, cy + 28, cx + 34, cy + 82], 16, fill=HOODIE_S)
        oval(d, [cx - 12, cy + 22, cx + 12, cy + 44], None, BLACK, 3)
        limb(d, cx - 40, cy + 30, cx - 70, cy + 88, 24, HOODIE)
        limb(d, cx + 40, cy + 30, cx + 70, cy + 88, 24, HOODIE)
        oval(d, [cx - 88, cy + 78, cx - 64, cy + 102], SKIN)
        oval(d, [cx + 64, cy + 78, cx + 88, cy + 102], SKIN)
        d.rectangle([cx - 18, cy - 6, cx + 18, cy + 16], fill=SKIN)
        draw_head_front(d, cx, hy)

    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, MOUTH_Y
    if kind == "closed":
        d.arc([cx - 12, my - 3, cx + 12, my + 9], 25, 155, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 10, my - 1, cx + 10, my + 13], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 7, my + 1, cx + 7, my + 5], TEETH)
    else:
        oval(d, [cx - 13, my - 1, cx + 13, my + 16], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 9, my + 1, cx + 9, my + 5], TEETH)
    return img


def draw_eyes_laugh() -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, hy = CX, HY
    ey = hy - 4
    d.arc([cx - 30, ey - 2, cx - 8, ey + 10], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 8, ey - 2, cx + 30, ey + 10], 200, 340, fill=BLACK, width=4)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    items = {
        "body.png": draw_body("front"),
        "body_side_left.png": draw_body("side_left"),
        "body_side_right.png": draw_body("side_right"),
        "arm_point.png": draw_body("point"),
        "body_present.png": draw_body("present"),
        "mouth_closed.png": draw_mouth("closed"),
        "mouth_open.png": draw_mouth("open"),
        "mouth_wide.png": draw_mouth("wide"),
        "eyes_laugh.png": draw_eyes_laugh(),
    }
    for name, im in items.items():
        path = out / name
        im.save(path, "PNG")
        print("wrote", path)


if __name__ == "__main__":
    main()
