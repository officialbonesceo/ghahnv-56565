#!/usr/bin/env python3
"""Host layers: continuous limbs (no wrist/ankle gaps), solid neck."""
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
CY = 385
HY = CY - 68
MOUTH_Y = HY + 24


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    """Thick continuous line segment (arm/leg) — no gaps at joints."""
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = width // 2
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def draw_body(mode: str = "front") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = CX, CY
    oval(d, [cx - 65, cy + 155, cx + 65, cy + 180], (0, 0, 0, 45))

    # Legs as continuous thick limbs into shoes
    if mode == "walk":
        limb(d, cx - 18, cy + 78, cx - 22, cy + 155, 28, PANTS)
        limb(d, cx + 16, cy + 70, cx + 28, cy + 148, 28, PANTS)
        oval(d, [cx - 42, cy + 148, cx - 2, cy + 178], SHOE)
        oval(d, [cx + 10, cy + 140, cx + 52, cy + 172], SHOE)
        d.rounded_rectangle([cx - 52, cy + 2, cx + 50, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 36, cy + 28, cx + 36, cy + 82], 16, fill=HOODIE_S)
        limb(d, cx - 42, cy + 30, cx - 72, cy + 88, 26, HOODIE_D)
        oval(d, [cx - 90, cy + 76, cx - 64, cy + 102], SKIN)  # hand attached
        limb(d, cx + 40, cy + 32, cx + 78, cy + 18, 26, HOODIE)
        oval(d, [cx + 70, cy + 4, cx + 96, cy + 30], SKIN)
    elif mode == "point":
        limb(d, cx - 18, cy + 78, cx - 18, cy + 155, 28, PANTS)
        limb(d, cx + 18, cy + 78, cx + 18, cy + 155, 28, PANTS)
        oval(d, [cx - 40, cy + 148, cx + 0, cy + 178], SHOE)
        oval(d, [cx + 0, cy + 148, cx + 40, cy + 178], SHOE)
        d.rounded_rectangle([cx - 52, cy + 2, cx + 52, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 36, cy + 28, cx + 36, cy + 82], 16, fill=HOODIE_S)
        limb(d, cx + 42, cy + 28, cx + 100, cy - 28, 28, HOODIE)
        oval(d, [cx + 90, cy - 44, cx + 116, cy - 18], SKIN)
        limb(d, cx + 108, cy - 32, cx + 135, cy - 50, 12, SKIN)  # finger
        limb(d, cx - 42, cy + 32, cx - 72, cy + 90, 26, HOODIE)
        oval(d, [cx - 90, cy + 78, cx - 64, cy + 104], SKIN)
    else:
        limb(d, cx - 18, cy + 78, cx - 18, cy + 155, 28, PANTS)
        limb(d, cx + 18, cy + 78, cx + 18, cy + 155, 28, PANTS)
        oval(d, [cx - 40, cy + 148, cx + 0, cy + 178], SHOE)
        oval(d, [cx + 0, cy + 148, cx + 40, cy + 178], SHOE)
        d.rounded_rectangle([cx - 52, cy + 2, cx + 52, cy + 92], 24, fill=HOODIE)
        d.rounded_rectangle([cx - 36, cy + 28, cx + 36, cy + 82], 16, fill=HOODIE_S)
        oval(d, [cx - 12, cy + 20, cx + 12, cy + 44], None, BLACK, 3)
        limb(d, cx - 42, cy + 30, cx - 72, cy + 90, 26, HOODIE)
        limb(d, cx + 42, cy + 30, cx + 72, cy + 90, 26, HOODIE)
        oval(d, [cx - 90, cy + 78, cx - 64, cy + 104], SKIN)
        oval(d, [cx + 64, cy + 78, cx + 90, cy + 104], SKIN)

    # Solid neck bridging head and hoodie (no gap)
    d.rectangle([cx - 20, cy - 8, cx + 20, cy + 18], fill=SKIN)
    d.rounded_rectangle([cx - 22, hy + 40, cx + 22, cy + 16], 8, fill=SKIN)

    hy = HY
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
        print("wrote", path)


if __name__ == "__main__":
    main()
