#!/usr/bin/env python3
"""MEZI: tighter proportions, wider neck, thicker limbs, less toy spacing."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 400, 700
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
# Compact body — less empty gap head-to-torso
CY = 390
HY = CY - 72
MOUTH_Y = HY + 26


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_body(mode: str = "front") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = CX, CY
    oval(d, [cx - 70, cy + 160, cx + 70, cy + 188], (0, 0, 0, 50))

    # Legs thicker, closer to body
    if mode == "walk":
        d.rounded_rectangle([cx - 36, cy + 70, cx - 6, cy + 165], 16, fill=PANTS)
        d.rounded_rectangle([cx + 4, cy + 55, cx + 34, cy + 155], 16, fill=PANTS)
        oval(d, [cx - 48, cy + 155, cx + 0, cy + 185], SHOE)
        oval(d, [cx + 0, cy + 145, cx + 50, cy + 175], SHOE)
        d.rounded_rectangle([cx - 55, cy + 0, cx + 52, cy + 95], 26, fill=HOODIE)
        d.rounded_rectangle([cx - 38, cy + 25, cx + 38, cy + 85], 18, fill=HOODIE_S)
        d.line([(cx - 48, cy + 25), (cx - 78, cy + 85)], fill=HOODIE_D, width=26)
        oval(d, [cx - 95, cy + 75, cx - 68, cy + 102], SKIN)
        d.line([(cx + 45, cy + 28), (cx + 85, cy + 15)], fill=HOODIE, width=26)
        oval(d, [cx + 75, cy + 2, cx + 102, cy + 30], SKIN)
    elif mode == "point":
        d.rounded_rectangle([cx - 36, cy + 75, cx - 6, cy + 165], 16, fill=PANTS)
        d.rounded_rectangle([cx + 6, cy + 75, cx + 36, cy + 165], 16, fill=PANTS)
        oval(d, [cx - 48, cy + 155, cx - 2, cy + 185], SHOE)
        oval(d, [cx + 2, cy + 155, cx + 48, cy + 185], SHOE)
        d.rounded_rectangle([cx - 55, cy + 0, cx + 55, cy + 98], 26, fill=HOODIE)
        d.rounded_rectangle([cx - 38, cy + 25, cx + 38, cy + 88], 18, fill=HOODIE_S)
        d.line([(cx + 48, cy + 22), (cx + 105, cy - 35)], fill=HOODIE, width=28)
        oval(d, [cx + 92, cy - 52, cx + 120, cy - 24], SKIN)
        d.line([(cx + 115, cy - 40), (cx + 142, cy - 58)], fill=SKIN, width=10)
        d.line([(cx - 48, cy + 28), (cx - 80, cy + 90)], fill=HOODIE, width=26)
        oval(d, [cx - 98, cy + 80, cx - 72, cy + 108], SKIN)
    else:
        d.rounded_rectangle([cx - 36, cy + 75, cx - 6, cy + 165], 16, fill=PANTS)
        d.rounded_rectangle([cx + 6, cy + 75, cx + 36, cy + 165], 16, fill=PANTS)
        oval(d, [cx - 48, cy + 155, cx - 2, cy + 185], SHOE)
        oval(d, [cx + 2, cy + 155, cx + 48, cy + 185], SHOE)
        d.rounded_rectangle([cx - 55, cy + 0, cx + 55, cy + 98], 26, fill=HOODIE)
        d.rounded_rectangle([cx - 38, cy + 25, cx + 38, cy + 88], 18, fill=HOODIE_S)
        oval(d, [cx - 12, cy + 18, cx + 12, cy + 42], None, BLACK, 3)
        d.line([(cx - 48, cy + 25), (cx - 80, cy + 92)], fill=HOODIE, width=26)
        d.line([(cx + 48, cy + 25), (cx + 80, cy + 92)], fill=HOODIE, width=26)
        oval(d, [cx - 98, cy + 82, cx - 72, cy + 110], SKIN)
        oval(d, [cx + 72, cy + 82, cx + 98, cy + 110], SKIN)

    # Wide neck connecting head to hoodie (no toy gap)
    d.rounded_rectangle([cx - 22, cy - 18, cx + 22, cy + 12], 10, fill=SKIN)
    hy = HY
    oval(d, [cx - 62, hy - 70, cx + 62, hy + 12], HAIR)
    oval(d, [cx - 52, hy - 52, cx + 52, hy + 48], SKIN)
    oval(d, [cx - 60, hy - 80, cx + 60, hy - 10], HAIR)
    oval(d, [cx - 48, hy - 30, cx + 48, hy + 42], SKIN)
    for ox, oy, r in [(-36, -78, 20), (-6, -88, 22), (20, -88, 22), (42, -78, 18)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    oval(d, [cx - 66, hy - 8, cx - 48, hy + 22], SKIN)
    oval(d, [cx + 48, hy - 8, cx + 66, hy + 22], SKIN)
    ey = hy - 6
    oval(d, [cx - 32, ey - 14, cx - 8, ey + 12], WHITE, BLACK, 3)
    oval(d, [cx + 8, ey - 14, cx + 32, ey + 12], WHITE, BLACK, 3)
    oval(d, [cx - 26, ey - 5, cx - 14, ey + 7], BLACK)
    oval(d, [cx + 14, ey - 5, cx + 26, ey + 7], BLACK)
    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, MOUTH_Y
    if kind == "closed":
        d.arc([cx - 12, my - 3, cx + 12, my + 9], 25, 155, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 11, my - 1, cx + 11, my + 14], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 8, my + 1, cx + 8, my + 5], TEETH)
    else:
        oval(d, [cx - 14, my - 1, cx + 14, my + 17], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 10, my + 1, cx + 10, my + 5], TEETH)
    return img


def draw_eyes_laugh() -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, hy = CX, HY
    ey = hy - 6
    d.arc([cx - 32, ey - 2, cx - 8, ey + 10], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 8, ey - 2, cx + 32, ey + 10], 200, 340, fill=BLACK, width=4)
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
