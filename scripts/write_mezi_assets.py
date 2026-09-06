#!/usr/bin/env python3
"""Mike — rounded cartoon teacher (human proportions, not stick-figure)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 480, 720
HOODIE = (255, 196, 40, 255)
HOODIE_L = (255, 220, 110, 255)
HOODIE_D = (235, 170, 30, 255)
SKIN = (225, 175, 135, 255)
SKIN_D = (200, 150, 110, 255)
HAIR = (32, 28, 35, 255)
PANTS = (48, 52, 68, 255)
SHOE = (28, 28, 32, 255)
WHITE = (255, 255, 255, 255)
BLACK = (22, 20, 24, 255)
MOUTH_IN = (130, 50, 60, 255)
TEETH = (250, 245, 240, 255)
CHEEK = (240, 160, 140, 90)

CX = W // 2
# Human-ish layout
HEAD_Y = 145
NECK_TOP = 195
SHOULDER = 215
HIP = 360
KNEE = 480
FOOT = 620


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2 - 1, 4)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def hand(d, x, y):
    oval(d, [x - 14, y - 12, x + 14, y + 14], SKIN)


def foot(d, x, y, facing=0):
    # facing: -1 left shoe, 1 right, 0 both-ish
    if facing <= 0:
        oval(d, [x - 28, y - 8, x + 10, y + 16], SHOE)
    if facing >= 0:
        oval(d, [x - 10, y - 8, x + 28, y + 16], SHOE)


def head_front(d, cx, hy, expr="neutral"):
    # round head
    oval(d, [cx - 58, hy - 62, cx + 58, hy + 52], SKIN)
    # hair
    oval(d, [cx - 60, hy - 70, cx + 60, hy - 5], HAIR)
    d.polygon(
        [(cx - 20, hy - 50), (cx - 5, hy - 88), (cx + 12, hy - 52),
         (cx + 28, hy - 82), (cx + 42, hy - 48)],
        fill=HAIR,
    )
    # ears
    oval(d, [cx - 68, hy - 8, cx - 52, hy + 22], SKIN)
    oval(d, [cx + 52, hy - 8, cx + 68, hy + 22], SKIN)
    # cheeks
    oval(d, [cx - 48, hy + 12, cx - 28, hy + 28], CHEEK)
    oval(d, [cx + 28, hy + 12, cx + 48, hy + 28], CHEEK)

    ey = hy - 6
    if expr == "blink":
        d.line([(cx - 32, ey), (cx - 12, ey)], fill=BLACK, width=4)
        d.line([(cx + 12, ey), (cx + 32, ey)], fill=BLACK, width=4)
    elif expr in ("happy", "giggle", "welcoming"):
        d.arc([cx - 34, ey - 4, cx - 10, ey + 14], 200, 340, fill=BLACK, width=4)
        d.arc([cx + 10, ey - 4, cx + 34, ey + 14], 200, 340, fill=BLACK, width=4)
    else:
        oval(d, [cx - 34, ey - 14, cx - 10, ey + 12], WHITE, BLACK, 3)
        oval(d, [cx + 10, ey - 14, cx + 34, ey + 12], WHITE, BLACK, 3)
        oval(d, [cx - 26, ey - 6, cx - 16, ey + 4], BLACK)
        oval(d, [cx + 16, ey - 6, cx + 26, ey + 4], BLACK)
        # shine
        oval(d, [cx - 22, ey - 8, cx - 18, ey - 4], WHITE)
        oval(d, [cx + 20, ey - 8, cx + 24, ey - 4], WHITE)

    # brows
    if expr == "confused":
        d.line([(cx - 34, ey - 22), (cx - 12, ey - 16)], fill=BLACK, width=4)
        d.line([(cx + 12, ey - 18), (cx + 34, ey - 24)], fill=BLACK, width=4)
    elif expr == "question":
        d.line([(cx - 34, ey - 24), (cx - 12, ey - 20)], fill=BLACK, width=4)
        d.line([(cx + 12, ey - 20), (cx + 34, ey - 24)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming", "encouraging"):
        d.arc([cx - 36, ey - 28, cx - 10, ey - 12], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 10, ey - 28, cx + 36, ey - 12], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 34, ey - 22), (cx - 12, ey - 22)], fill=BLACK, width=3)
        d.line([(cx + 12, ey - 22), (cx + 34, ey - 22)], fill=BLACK, width=3)

    # small nose
    oval(d, [cx - 6, hy + 8, cx + 6, hy + 22], SKIN_D)


def head_side(d, cx, hy, facing="left"):
    sign = -1 if facing == "left" else 1
    oval(d, [cx - 48, hy - 58, cx + 48, hy + 48], SKIN)
    oval(d, [cx - 50, hy - 68, cx + 40, hy - 2], HAIR)
    d.polygon(
        [(cx - 10, hy - 45), (cx + sign * 8, hy - 82), (cx + 20, hy - 42)],
        fill=HAIR,
    )
    # ear
    ex = cx - sign * 40
    oval(d, [ex - 12, hy - 6, ex + 12, hy + 24], SKIN, BLACK, 2)
    oval(d, [ex - 6, hy + 2, ex + 6, hy + 16], SKIN_D)
    # eye
    eye_x = cx + sign * 14
    oval(d, [eye_x - 12, hy - 12, eye_x + 12, hy + 10], WHITE, BLACK, 2)
    oval(d, [eye_x - 4, hy - 4, eye_x + 4, hy + 4], BLACK)
    # nose
    nx = cx + sign * 42
    oval(d, [nx - 7, hy + 4, nx + 7, hy + 20], SKIN_D)


def torso(d, cx, sy):
    # rounded hoodie body
    d.rounded_rectangle([cx - 62, sy, cx + 62, sy + 150], 28, fill=HOODIE)
    d.rounded_rectangle([cx - 40, sy + 35, cx + 40, sy + 130], 20, fill=HOODIE_L)
    # hood rim
    d.arc([cx - 50, sy - 8, cx + 50, sy + 40], 200, 340, fill=HOODIE_D, width=6)


def draw_pose(mode: str = "stand", expr: str = "neutral") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX

    # soft shadow
    oval(d, [cx - 70, FOOT + 4, cx + 70, FOOT + 28], (0, 0, 0, 40))

    if mode == "side_left":
        # legs alternating
        limb(d, cx + 6, HIP, cx + 22, KNEE - 15, 28, PANTS)
        limb(d, cx + 22, KNEE - 15, cx + 28, FOOT - 10, 24, PANTS)
        foot(d, cx + 28, FOOT - 6, 1)
        limb(d, cx - 6, HIP, cx - 24, KNEE + 5, 28, PANTS)
        limb(d, cx - 24, KNEE + 5, cx - 32, FOOT, 24, PANTS)
        foot(d, cx - 32, FOOT + 2, -1)
        torso(d, cx, SHOULDER)
        # far arm forward
        limb(d, cx - 40, SHOULDER + 30, cx - 70, SHOULDER + 20, 26, HOODIE)
        hand(d, cx - 78, SHOULDER + 16)
        # near arm back
        limb(d, cx + 40, SHOULDER + 30, cx + 55, SHOULDER + 100, 26, HOODIE)
        hand(d, cx + 55, SHOULDER + 112)
        # short neck
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_side(d, cx, HEAD_Y, "left")

    elif mode == "side_right":
        limb(d, cx - 6, HIP, cx - 22, KNEE - 15, 28, PANTS)
        limb(d, cx - 22, KNEE - 15, cx - 28, FOOT - 10, 24, PANTS)
        foot(d, cx - 28, FOOT - 6, -1)
        limb(d, cx + 6, HIP, cx + 24, KNEE + 5, 28, PANTS)
        limb(d, cx + 24, KNEE + 5, cx + 32, FOOT, 24, PANTS)
        foot(d, cx + 32, FOOT + 2, 1)
        torso(d, cx, SHOULDER)
        limb(d, cx + 40, SHOULDER + 30, cx + 70, SHOULDER + 20, 26, HOODIE)
        hand(d, cx + 78, SHOULDER + 16)
        limb(d, cx - 40, SHOULDER + 30, cx - 55, SHOULDER + 100, 26, HOODIE)
        hand(d, cx - 55, SHOULDER + 112)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_side(d, cx, HEAD_Y, "right")

    elif mode == "point":
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        foot(d, cx - 18, FOOT, -1)
        foot(d, cx + 18, FOOT, 1)
        torso(d, cx, SHOULDER)
        # left arm down
        limb(d, cx - 50, SHOULDER + 35, cx - 70, SHOULDER + 120, 26, HOODIE)
        hand(d, cx - 72, SHOULDER + 132)
        # right arm point up
        limb(d, cx + 50, SHOULDER + 30, cx + 110, SHOULDER - 30, 28, HOODIE)
        hand(d, cx + 118, SHOULDER - 42)
        # pointing finger
        limb(d, cx + 118, SHOULDER - 42, cx + 145, SHOULDER - 60, 8, SKIN)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    elif mode == "present":
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        foot(d, cx - 18, FOOT, -1)
        foot(d, cx + 18, FOOT, 1)
        torso(d, cx, SHOULDER)
        limb(d, cx - 52, SHOULDER + 35, cx - 115, SHOULDER + 55, 28, HOODIE)
        hand(d, cx - 125, SHOULDER + 50)
        limb(d, cx + 52, SHOULDER + 35, cx + 115, SHOULDER + 55, 28, HOODIE)
        hand(d, cx + 125, SHOULDER + 50)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr if expr != "neutral" else "welcoming")

    elif mode == "sit":
        # proper sit: hips lower, thighs forward, shins down
        sit_hip = 430
        sit_knee = 470
        sit_foot = 560
        # thighs
        limb(d, cx - 20, sit_hip, cx - 70, sit_knee, 30, PANTS)
        limb(d, cx + 20, sit_hip, cx + 70, sit_knee, 30, PANTS)
        # shins
        limb(d, cx - 70, sit_knee, cx - 75, sit_foot, 26, PANTS)
        limb(d, cx + 70, sit_knee, cx + 75, sit_foot, 26, PANTS)
        foot(d, cx - 75, sit_foot, -1)
        foot(d, cx + 75, sit_foot, 1)
        # torso higher above hips
        torso(d, cx, SHOULDER + 50)
        # arms on lap
        limb(d, cx - 50, SHOULDER + 85, cx - 55, SHOULDER + 160, 26, HOODIE)
        hand(d, cx - 55, SHOULDER + 172)
        limb(d, cx + 50, SHOULDER + 85, cx + 55, SHOULDER + 160, 26, HOODIE)
        hand(d, cx + 55, SHOULDER + 172)
        d.rounded_rectangle([cx - 14, NECK_TOP + 45, cx + 14, SHOULDER + 62], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y + 40, expr)
        # simple stool
        d.rectangle([cx - 90, sit_hip + 8, cx + 90, sit_hip + 22], fill=(110, 85, 55, 220))

    else:  # stand talk
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        foot(d, cx - 18, FOOT, -1)
        foot(d, cx + 18, FOOT, 1)
        torso(d, cx, SHOULDER)
        limb(d, cx - 50, SHOULDER + 35, cx - 65, SHOULDER + 125, 26, HOODIE)
        hand(d, cx - 68, SHOULDER + 138)
        limb(d, cx + 50, SHOULDER + 35, cx + 65, SHOULDER + 125, 26, HOODIE)
        hand(d, cx + 68, SHOULDER + 138)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, HEAD_Y + 32
    if kind == "closed":
        d.arc([cx - 16, my - 2, cx + 16, my + 14], 20, 160, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 14, my, cx + 14, my + 18], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 10, my + 2, cx + 10, my + 7], TEETH)
    elif kind == "smile":
        d.arc([cx - 18, my - 4, cx + 18, my + 16], 15, 165, fill=BLACK, width=4)
    else:
        oval(d, [cx - 16, my, cx + 16, my + 22], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 11, my + 2, cx + 11, my + 7], TEETH)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    poses = {
        "body.png": ("stand", "neutral"),
        "body_side_left.png": ("side_left", "neutral"),
        "body_side_right.png": ("side_right", "neutral"),
        "arm_point.png": ("point", "encouraging"),
        "body_present.png": ("present", "welcoming"),
        "body_sit.png": ("sit", "neutral"),
        "body_happy.png": ("stand", "happy"),
        "body_question.png": ("stand", "question"),
        "body_confused.png": ("stand", "confused"),
        "body_blink.png": ("stand", "blink"),
    }
    for name, (mode, expr) in poses.items():
        draw_pose(mode, expr).save(out / name, "PNG")
        print("wrote", name)
    for kind, fname in [
        ("closed", "mouth_closed.png"),
        ("open", "mouth_open.png"),
        ("wide", "mouth_wide.png"),
        ("smile", "mouth_smile.png"),
    ]:
        draw_mouth(kind).save(out / fname, "PNG")
        print("wrote", fname)


if __name__ == "__main__":
    main()
