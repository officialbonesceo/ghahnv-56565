#!/usr/bin/env python3
"""MEZI sprites: wider neck, thicker limbs, grounded, side-walk, point."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 400, 700
HOODIE = (255, 196, 40, 255)
HOODIE_S = (255, 220, 100, 255)
HOODIE_D = (230, 165, 25, 255)
SKIN = (210, 155, 115, 255)
HAIR = (28, 24, 30, 255)
PANTS = (32, 36, 48, 255)
SHOE = (20, 20, 26, 255)
WHITE = (255, 255, 255, 255)
BLACK = (25, 22, 28, 255)
MOUTH_IN = (95, 35, 45, 255)
TEETH = (250, 245, 240, 255)

CX = W // 2
CY = 400
HY = CY - 95
MOUTH_Y = HY + 28


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_body(mode: str = "front") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = CX, CY
    oval(d, [cx - 75, cy + 178, cx + 75, cy + 208], (0, 0, 0, 60))

    if mode == "walk":
        # thicker legs, side stride
        d.rounded_rectangle([cx - 32, cy + 80, cx - 2, cy + 178], 14, fill=PANTS)
        d.rounded_rectangle([cx + 6, cy + 65, cx + 36, cy + 165], 14, fill=PANTS)
        oval(d, [cx - 45, cy + 168, cx + 5, cy + 198], SHOE)
        oval(d, [cx + 2, cy + 155, cx + 55, cy + 188], SHOE)
        d.rounded_rectangle([cx - 58, cy - 8, cx + 55, cy + 108], 30, fill=HOODIE)
        d.rounded_rectangle([cx - 40, cy + 18, cx + 40, cy + 95], 22, fill=HOODIE_S)
        d.line([(cx - 50, cy + 28), (cx - 82, cy + 95)], fill=HOODIE_D, width=22)
        oval(d, [cx - 100, cy + 85, cx - 70, cy + 115], SKIN)
        d.line([(cx + 48, cy + 32), (cx + 88, cy + 18)], fill=HOODIE, width=22)
        oval(d, [cx + 80, cy + 5, cx + 110, cy + 35], SKIN)
    elif mode == "point":
        d.rounded_rectangle([cx - 42, cy + 88, cx - 10, cy + 178], 14, fill=PANTS)
        d.rounded_rectangle([cx + 10, cy + 88, cx + 42, cy + 178], 14, fill=PANTS)
        oval(d, [cx - 52, cy + 168, cx - 2, cy + 198], SHOE)
        oval(d, [cx + 2, cy + 168, cx + 52, cy + 198], SHOE)
        d.rounded_rectangle([cx - 62, cy - 8, cx + 62, cy + 112], 30, fill=HOODIE)
        d.rounded_rectangle([cx - 42, cy + 22, cx + 42, cy + 98], 22, fill=HOODIE_S)
        d.line([(cx + 55, cy + 28), (cx + 115, cy - 40)], fill=HOODIE, width=24)
        oval(d, [cx + 102, cy - 58, cx + 132, cy - 28], SKIN)
        d.line([(cx + 125, cy - 45), (cx + 155, cy - 65)], fill=SKIN, width=9)
        d.line([(cx - 55, cy + 35), (cx - 85, cy + 105)], fill=HOODIE, width=22)
        oval(d, [cx - 105, cy + 92, cx - 75, cy + 122], SKIN)
    else:
        d.rounded_rectangle([cx - 42, cy + 88, cx - 10, cy + 178], 14, fill=PANTS)
        d.rounded_rectangle([cx + 10, cy + 88, cx + 42, cy + 178], 14, fill=PANTS)
        oval(d, [cx - 52, cy + 168, cx - 2, cy + 198], SHOE)
        oval(d, [cx + 2, cy + 168, cx + 52, cy + 198], SHOE)
        d.rounded_rectangle([cx - 62, cy - 8, cx + 62, cy + 112], 30, fill=HOODIE)
        d.rounded_rectangle([cx - 42, cy + 22, cx + 42, cy + 98], 22, fill=HOODIE_S)
        d.rounded_rectangle([cx - 34, cy + 55, cx + 34, cy + 98], 16, fill=HOODIE)
        oval(d, [cx - 14, cy + 20, cx + 14, cy + 48], None, BLACK, 3)
        d.line([(cx - 55, cy + 30), (cx - 88, cy + 105)], fill=HOODIE, width=22)
        d.line([(cx + 55, cy + 30), (cx + 88, cy + 105)], fill=HOODIE, width=22)
        oval(d, [cx - 105, cy + 95, cx - 75, cy + 125], SKIN)
        oval(d, [cx + 75, cy + 95, cx + 105, cy + 125], SKIN)

    # wider neck in sync with head
    d.rounded_rectangle([cx - 20, cy - 32, cx + 20, cy + 8], 8, fill=SKIN)
    hy = HY
    oval(d, [cx - 68, hy - 78, cx + 68, hy + 18], HAIR)
    oval(d, [cx - 58, hy - 58, cx + 58, hy + 55], SKIN)
    oval(d, [cx - 66, hy - 88, cx + 66, hy - 12], HAIR)
    oval(d, [cx - 52, hy - 35, cx + 52, hy + 50], SKIN)
    for ox, oy, r in [(-40, -85, 22), (-8, -96, 24), (22, -96, 24), (48, -85, 20)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    oval(d, [cx - 72, hy - 12, cx - 52, hy + 24], SKIN)
    oval(d, [cx + 52, hy - 12, cx + 72, hy + 24], SKIN)
    ey = hy - 8
    oval(d, [cx - 36, ey - 16, cx - 8, ey + 14], WHITE, BLACK, 3)
    oval(d, [cx + 8, ey - 16, cx + 36, ey + 14], WHITE, BLACK, 3)
    oval(d, [cx - 28, ey - 6, cx - 14, ey + 8], BLACK)
    oval(d, [cx + 14, ey - 6, cx + 28, ey + 8], BLACK)
    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, MOUTH_Y
    if kind == "closed":
        d.arc([cx - 14, my - 4, cx + 14, my + 10], 25, 155, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 12, my - 2, cx + 12, my + 16], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 9, my, cx + 9, my + 5], TEETH)
        oval(d, [cx - 8, my + 6, cx + 8, my + 13], (55, 18, 28, 255))
    else:
        oval(d, [cx - 16, my - 2, cx + 16, my + 20], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 12, my, cx + 12, my + 6], TEETH)
        oval(d, [cx - 11, my + 7, cx + 11, my + 17], (55, 18, 28, 255))
    return img


def draw_eyes_laugh() -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, hy = CX, HY
    ey = hy - 8
    d.arc([cx - 36, ey - 4, cx - 8, ey + 12], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 8, ey - 4, cx + 36, ey + 12], 200, 340, fill=BLACK, width=4)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    items = {
        "body.png": draw_body("front"),
        "body_walk.png": draw_body("walk"),
        "arm_point.png": draw_body("point"),
        "mouth_closed.png": draw_mouth("closed"),
        "mouth_open.png": draw_mouth("open"),
        "mouth_wide.png": draw_mouth("wide"),
        "eyes_laugh.png": draw_eyes_laugh(),
    }
    for name, im in items.items():
        path = out / name
        im.save(path, "PNG")
        print("wrote", path, path.stat().st_size)


if __name__ == "__main__":
    main()
