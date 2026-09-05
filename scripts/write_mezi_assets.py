#!/usr/bin/env python3
"""Build MEZI sprite layers: grounded body, small mouths, side-walk, point."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 400, 700
HOODIE = (255, 196, 40, 255)
HOODIE_S = (255, 220, 100, 255)
HOODIE_D = (230, 165, 25, 255)
SKIN = (210, 155, 115, 255)
SKIN_D = (180, 125, 90, 255)
HAIR = (28, 24, 30, 255)
PANTS = (32, 36, 48, 255)
SHOE = (20, 20, 26, 255)
WHITE = (255, 255, 255, 255)
BLACK = (25, 22, 28, 255)
MOUTH_IN = (95, 35, 45, 255)
TEETH = (250, 245, 240, 255)

# Shared anchor: face center for mouth alignment
CX = W // 2
CY = 400  # body center lower so feet sit near bottom
HY = CY - 95  # head center Y
MOUTH_Y = HY + 28  # mouth on face, not chest


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_body(mode: str = "front") -> Image.Image:
    """mode: front | walk | point"""
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = CX, CY

    # ground shadow so character does not float
    oval(d, [cx - 70, cy + 175, cx + 70, cy + 205], (0, 0, 0, 55))

    if mode == "walk":
        # side-ish walk: body slightly turned, legs striding
        d.rounded_rectangle([cx - 25, cy + 85, cx - 2, cy + 175], 12, fill=PANTS)
        d.rounded_rectangle([cx + 8, cy + 70, cx + 32, cy + 160], 12, fill=PANTS)
        oval(d, [cx - 38, cy + 165, cx + 2, cy + 192], SHOE)
        oval(d, [cx + 5, cy + 150, cx + 48, cy + 178], SHOE)
        # torso
        d.rounded_rectangle([cx - 55, cy - 5, cx + 50, cy + 105], 28, fill=HOODIE)
        d.rounded_rectangle([cx - 38, cy + 20, cx + 35, cy + 90], 20, fill=HOODIE_S)
        # far arm back
        d.line([(cx - 48, cy + 25), (cx - 75, cy + 90)], fill=HOODIE_D, width=16)
        oval(d, [cx - 90, cy + 82, cx - 65, cy + 108], SKIN)
        # near arm forward
        d.line([(cx + 42, cy + 30), (cx + 80, cy + 20)], fill=HOODIE, width=16)
        oval(d, [cx + 72, cy + 8, cx + 98, cy + 34], SKIN)
    elif mode == "point":
        d.rounded_rectangle([cx - 38, cy + 90, cx - 12, cy + 175], 12, fill=PANTS)
        d.rounded_rectangle([cx + 12, cy + 90, cx + 38, cy + 175], 12, fill=PANTS)
        oval(d, [cx - 48, cy + 165, cx - 5, cy + 192], SHOE)
        oval(d, [cx + 5, cy + 165, cx + 48, cy + 192], SHOE)
        d.rounded_rectangle([cx - 58, cy - 5, cx + 58, cy + 110], 28, fill=HOODIE)
        d.rounded_rectangle([cx - 40, cy + 25, cx + 40, cy + 95], 20, fill=HOODIE_S)
        d.line([(cx + 50, cy + 30), (cx + 105, cy - 35)], fill=HOODIE, width=18)
        oval(d, [cx + 95, cy - 52, cx + 122, cy - 25], SKIN)
        d.line([(cx + 115, cy - 40), (cx + 145, cy - 60)], fill=SKIN, width=7)
        d.line([(cx - 50, cy + 35), (cx - 78, cy + 100)], fill=HOODIE, width=16)
        oval(d, [cx - 95, cy + 90, cx - 70, cy + 115], SKIN)
    else:
        # front idle
        d.rounded_rectangle([cx - 38, cy + 90, cx - 12, cy + 175], 12, fill=PANTS)
        d.rounded_rectangle([cx + 12, cy + 90, cx + 38, cy + 175], 12, fill=PANTS)
        oval(d, [cx - 48, cy + 165, cx - 5, cy + 192], SHOE)
        oval(d, [cx + 5, cy + 165, cx + 48, cy + 192], SHOE)
        d.rounded_rectangle([cx - 58, cy - 5, cx + 58, cy + 110], 28, fill=HOODIE)
        d.rounded_rectangle([cx - 40, cy + 25, cx + 40, cy + 95], 20, fill=HOODIE_S)
        d.rounded_rectangle([cx - 32, cy + 55, cx + 32, cy + 95], 14, fill=HOODIE)
        oval(d, [cx - 14, cy + 22, cx + 14, cy + 50], None, BLACK, 3)
        d.line([(cx - 50, cy + 30), (cx - 78, cy + 100)], fill=HOODIE, width=16)
        d.line([(cx + 50, cy + 30), (cx + 78, cy + 100)], fill=HOODIE, width=16)
        oval(d, [cx - 95, cy + 90, cx - 70, cy + 115], SKIN)
        oval(d, [cx + 70, cy + 90, cx + 95, cy + 115], SKIN)

    # neck + head (same for all — mouth layer aligns here)
    d.rectangle([cx - 12, cy - 28, cx + 12, cy + 5], fill=SKIN)
    hy = HY
    oval(d, [cx - 68, hy - 78, cx + 68, hy + 18], HAIR)
    oval(d, [cx - 58, hy - 58, cx + 58, hy + 55], SKIN)
    oval(d, [cx - 66, hy - 88, cx + 66, hy - 12], HAIR)
    oval(d, [cx - 52, hy - 35, cx + 52, hy + 50], SKIN)
    for ox, oy, r in [(-40, -85, 22), (-8, -96, 24), (22, -96, 24), (48, -85, 20)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    oval(d, [cx - 72, hy - 12, cx - 54, hy + 22], SKIN)
    oval(d, [cx + 54, hy - 12, cx + 72, hy + 22], SKIN)

    # eyes
    ey = hy - 8
    oval(d, [cx - 36, ey - 16, cx - 8, ey + 14], WHITE, BLACK, 3)
    oval(d, [cx + 8, ey - 16, cx + 36, ey + 14], WHITE, BLACK, 3)
    oval(d, [cx - 28, ey - 6, cx - 14, ey + 8], BLACK)
    oval(d, [cx + 14, ey - 6, cx + 28, ey + 8], BLACK)
    oval(d, [cx - 26, ey - 4, cx - 20, ey + 2], WHITE)
    oval(d, [cx + 16, ey - 4, cx + 22, ey + 2], WHITE)
    d.arc([cx - 38, ey - 30, cx - 6, ey - 6], 200, 340, fill=BLACK, width=3)
    d.arc([cx + 6, ey - 30, cx + 38, ey - 6], 200, 340, fill=BLACK, width=3)
    return img


def draw_mouth(kind: str) -> Image.Image:
    """Small mouths locked to face position — will not spill over body."""
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    my = MOUTH_Y
    if kind == "closed":
        # small smile only
        d.arc([cx - 14, my - 4, cx + 14, my + 10], 25, 155, fill=BLACK, width=3)
    elif kind == "open":
        # modest open — stays on face
        oval(d, [cx - 12, my - 2, cx + 12, my + 16], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 9, my, cx + 9, my + 5], TEETH)
        oval(d, [cx - 8, my + 6, cx + 8, my + 13], (55, 18, 28, 255))
    else:  # wide but still face-sized
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
