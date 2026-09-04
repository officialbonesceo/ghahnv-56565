#!/usr/bin/env python3
"""Build MEZI RGBA sprite layers into assets/mezi/."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 400, 700
HOODIE = (255, 196, 40, 255)
HOODIE_S = (255, 220, 100, 255)
SKIN = (210, 155, 115, 255)
HAIR = (28, 24, 30, 255)
PANTS = (32, 36, 48, 255)
SHOE = (20, 20, 26, 255)
WHITE = (255, 255, 255, 255)
BLACK = (25, 22, 28, 255)
MOUTH_IN = (95, 35, 45, 255)
TEETH = (250, 245, 240, 255)


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def draw_body(arm_mode="normal"):
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, 380
    d.rounded_rectangle([cx - 42, cy + 90, cx - 12, cy + 175], 14, fill=PANTS)
    d.rounded_rectangle([cx + 12, cy + 90, cx + 42, cy + 175], 14, fill=PANTS)
    oval(d, [cx - 52, cy + 162, cx - 5, cy + 192], SHOE)
    oval(d, [cx + 5, cy + 162, cx + 52, cy + 192], SHOE)
    d.rounded_rectangle([cx - 70, cy - 10, cx + 70, cy + 115], 32, fill=HOODIE)
    d.rounded_rectangle([cx - 48, cy + 15, cx + 48, cy + 95], 24, fill=HOODIE_S)
    d.rounded_rectangle([cx - 40, cy + 55, cx + 40, cy + 100], 18, fill=HOODIE)
    oval(d, [cx - 18, cy + 18, cx + 18, cy + 54], None, BLACK, 3)
    d.line([(cx - 58, cy + 5), (cx - 48, cy + 80)], fill=(45, 45, 55, 255), width=6)
    d.line([(cx + 58, cy + 5), (cx + 48, cy + 80)], fill=(45, 45, 55, 255), width=6)
    if arm_mode == "point":
        d.line([(cx + 62, cy + 25), (cx + 120, cy - 50)], fill=HOODIE, width=22)
        oval(d, [cx + 108, cy - 68, cx + 138, cy - 38], SKIN)
        d.line([(cx + 132, cy - 55), (cx + 165, cy - 80)], fill=SKIN, width=8)
        d.line([(cx - 62, cy + 30), (cx - 90, cy + 100)], fill=HOODIE, width=20)
        oval(d, [cx - 108, cy + 90, cx - 78, cy + 120], SKIN)
    else:
        d.line([(cx - 62, cy + 25), (cx - 95, cy + 105)], fill=HOODIE, width=20)
        d.line([(cx + 62, cy + 25), (cx + 95, cy + 105)], fill=HOODIE, width=20)
        oval(d, [cx - 112, cy + 95, cx - 82, cy + 125], SKIN)
        oval(d, [cx + 82, cy + 95, cx + 112, cy + 125], SKIN)
    d.rectangle([cx - 16, cy - 35, cx + 16, cy], fill=SKIN)
    hy = cy - 110
    oval(d, [cx - 78, hy - 85, cx + 78, hy + 25], HAIR)
    oval(d, [cx - 70, hy - 65, cx + 70, hy + 65], SKIN)
    oval(d, [cx - 76, hy - 95, cx + 76, hy - 10], HAIR)
    oval(d, [cx - 62, hy - 40, cx + 62, hy + 60], SKIN)
    for ox, oy, r in [(-48, -95, 26), (-15, -108, 28), (20, -110, 30), (52, -98, 26)]:
        oval(d, [cx + ox - r, hy + oy - r // 2, cx + ox + r, hy + oy + r], HAIR)
    oval(d, [cx - 85, hy - 15, cx - 62, hy + 25], SKIN)
    oval(d, [cx + 62, hy - 15, cx + 85, hy + 25], SKIN)
    ey = hy - 5
    oval(d, [cx - 42, ey - 20, cx - 8, ey + 18], WHITE, BLACK, 3)
    oval(d, [cx + 8, ey - 20, cx + 42, ey + 18], WHITE, BLACK, 3)
    oval(d, [cx - 32, ey - 8, cx - 16, ey + 10], BLACK)
    oval(d, [cx + 16, ey - 8, cx + 32, ey + 10], BLACK)
    oval(d, [cx - 30, ey - 6, cx - 22, ey + 2], WHITE)
    oval(d, [cx + 18, ey - 6, cx + 26, ey + 2], WHITE)
    d.arc([cx - 44, ey - 36, cx - 6, ey - 8], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 6, ey - 36, cx + 44, ey - 8], 200, 340, fill=BLACK, width=4)
    return img


def draw_mouth(kind: str):
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, 380
    hy = cy - 110
    my = hy + 35
    if kind == "closed":
        d.arc([cx - 22, my - 8, cx + 22, my + 12], 20, 160, fill=BLACK, width=5)
    elif kind == "open":
        oval(d, [cx - 28, my - 5, cx + 28, my + 32], MOUTH_IN, BLACK, 3)
        oval(d, [cx - 22, my - 1, cx + 22, my + 10], TEETH)
        oval(d, [cx - 20, my + 12, cx + 20, my + 28], (55, 18, 28, 255))
    else:
        oval(d, [cx - 36, my - 6, cx + 36, my + 42], MOUTH_IN, BLACK, 3)
        oval(d, [cx - 28, my - 2, cx + 28, my + 12], TEETH)
        oval(d, [cx - 26, my + 14, cx + 26, my + 36], (55, 18, 28, 255))
    return img


def draw_eyes_laugh():
    img = blank()
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, 380
    hy = cy - 110
    ey = hy - 5
    d.arc([cx - 42, ey - 8, cx - 8, ey + 16], 200, 340, fill=BLACK, width=5)
    d.arc([cx + 8, ey - 8, cx + 42, ey + 16], 200, 340, fill=BLACK, width=5)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    items = {
        "body.png": draw_body("normal"),
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
