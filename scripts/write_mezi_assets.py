#!/usr/bin/env python3
"""Generate MEZI sprite PNGs into assets/mezi/ (layered puppet parts)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SKIN = (210, 155, 115, 255)
HAIR = (28, 24, 30, 255)
HOODIE = (255, 196, 40, 255)
HOODIE_S = (255, 215, 90, 255)
PANTS = (32, 36, 48, 255)
SHOE = (22, 22, 28, 255)
WHITE = (255, 255, 255, 255)
BLACK = (28, 24, 30, 255)
MOUTH_C = (90, 35, 45, 255)


def new(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, w=2):
    d.ellipse(xy, fill=fill, outline=outline, width=w if outline else 0)


def make_body():
    im = new(400, 700)
    d = ImageDraw.Draw(im)
    cx = 200
    oval(d, [cx - 55, 620, cx - 5, 660], SHOE)
    oval(d, [cx + 5, 620, cx + 55, 660], SHOE)
    d.rounded_rectangle([cx - 42, 520, cx - 12, 630], 14, fill=PANTS)
    d.rounded_rectangle([cx + 12, 520, cx + 42, 630], 14, fill=PANTS)
    d.rounded_rectangle([cx - 75, 300, cx + 75, 530], 36, fill=HOODIE)
    d.rounded_rectangle([cx - 50, 340, cx + 50, 500], 28, fill=HOODIE_S)
    d.rounded_rectangle([cx - 42, 420, cx + 42, 495], 18, fill=HOODIE)
    oval(d, [cx - 20, 350, cx + 20, 390], None, BLACK, 3)
    d.line([(cx - 60, 320), (cx - 50, 470)], fill=(45, 45, 55, 255), width=6)
    d.line([(cx + 60, 320), (cx + 50, 470)], fill=(45, 45, 55, 255), width=6)
    d.line([(cx - 70, 360), (cx - 105, 500)], fill=HOODIE, width=22)
    d.line([(cx + 70, 360), (cx + 105, 500)], fill=HOODIE, width=22)
    oval(d, [cx - 125, 485, cx - 90, 520], SKIN)
    oval(d, [cx + 90, 485, cx + 125, 520], SKIN)
    d.rectangle([cx - 18, 270, cx + 18, 310], fill=SKIN)
    oval(d, [cx - 90, 120, cx + 90, 300], SKIN)
    oval(d, [cx - 95, 90, cx + 95, 200], HAIR)
    oval(d, [cx - 80, 160, cx + 80, 280], SKIN)
    for ox, oy, r in [(-55, -20, 28), (-15, -35, 30), (25, -38, 32), (60, -25, 26), (75, 0, 20)]:
        oval(d, [cx + ox - r, 100 + oy, cx + ox + r, 100 + oy + r * 2], HAIR)
    oval(d, [cx - 100, 190, cx - 78, 230], SKIN)
    oval(d, [cx + 78, 190, cx + 100, 230], SKIN)
    oval(d, [cx - 48, 195, cx - 12, 235], WHITE, BLACK, 3)
    oval(d, [cx + 12, 195, cx + 48, 235], WHITE, BLACK, 3)
    oval(d, [cx - 38, 205, cx - 20, 225], BLACK)
    oval(d, [cx + 20, 205, cx + 38, 225], BLACK)
    oval(d, [cx - 35, 208, cx - 27, 216], WHITE)
    oval(d, [cx + 23, 208, cx + 31, 216], WHITE)
    d.arc([cx - 50, 175, cx - 10, 200], 200, 340, fill=BLACK, width=4)
    d.arc([cx + 10, 175, cx + 50, 200], 200, 340, fill=BLACK, width=4)
    blush = new(400, 700)
    bd = ImageDraw.Draw(blush)
    bd.ellipse([cx - 70, 235, cx - 40, 255], fill=(255, 140, 130, 80))
    bd.ellipse([cx + 40, 235, cx + 70, 255], fill=(255, 140, 130, 80))
    return Image.alpha_composite(im, blush)


def make_mouth(open_amt: float):
    im = new(400, 700)
    d = ImageDraw.Draw(im)
    cx, my = 200, 268
    if open_amt < 0.15:
        d.arc([cx - 22, my - 10, cx + 22, my + 12], 20, 160, fill=BLACK, width=5)
    else:
        mw = 14 + int(22 * open_amt)
        mh = 4 + int(30 * open_amt)
        oval(d, [cx - mw, my - mh // 4, cx + mw, my + mh], MOUTH_C, BLACK, 3)
        if open_amt > 0.3:
            oval(d, [cx - mw + 4, my - 1, cx + mw - 4, my + 6 + int(5 * open_amt)], (245, 240, 235, 255))
        if open_amt > 0.5:
            oval(d, [cx - mw + 6, my + 8, cx + mw - 6, my + mh - 3], (50, 15, 25, 255))
    return im


def make_arm_point():
    im = new(400, 700)
    d = ImageDraw.Draw(im)
    cx = 200
    d.line([(cx + 70, 360), (cx + 130, 220)], fill=HOODIE, width=24)
    oval(d, [cx + 115, 195, cx + 150, 230], SKIN)
    d.line([(cx + 140, 210), (cx + 175, 175)], fill=SKIN, width=8)
    return im


def make_eyes_laugh():
    im = new(400, 700)
    d = ImageDraw.Draw(im)
    cx = 200
    d.arc([cx - 48, 200, cx - 12, 230], 200, 340, fill=BLACK, width=5)
    d.arc([cx + 12, 200, cx + 48, 230], 200, 340, fill=BLACK, width=5)
    return im


def main():
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    make_body().save(out / "body.png")
    make_mouth(0.05).save(out / "mouth_closed.png")
    make_mouth(0.55).save(out / "mouth_open.png")
    make_mouth(0.95).save(out / "mouth_wide.png")
    make_arm_point().save(out / "arm_point.png")
    make_eyes_laugh().save(out / "eyes_laugh.png")
    for p in sorted(out.glob("*.png")):
        print("wrote", p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
