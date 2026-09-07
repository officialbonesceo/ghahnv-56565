#!/usr/bin/env python3
"""Mike — polished cartoon teacher (ref-style proportions, yellow hoodie, good hands)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 520, 780
# yellow hoodie (Mike brand)
HOODIE = (255, 196, 40, 255)
HOODIE_L = (255, 220, 100, 255)
HOODIE_D = (230, 165, 25, 255)
PANTS = (40, 44, 58, 255)
SHOE = (35, 35, 40, 255)
SKIN = (232, 185, 145, 255)
SKIN_D = (205, 155, 115, 255)
HAIR = (28, 24, 30, 255)
WHITE = (255, 255, 255, 255)
BLACK = (20, 18, 22, 255)
MOUTH_IN = (140, 55, 65, 255)
TEETH = (250, 248, 245, 255)
CHEEK = (245, 165, 145, 80)

CX = W // 2
# proportions closer to polished cartoon (taller legs, proper head)
HEAD_Y = 118
NECK = 168
SHOULDER = 188
HIP = 390
KNEE = 530
FOOT = 680


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2 - 1, 5)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def hand_open(d, x, y, facing=1):
    """Better hand: palm + fingers."""
    oval(d, [x - 16, y - 12, x + 16, y + 16], SKIN)
    # fingers
    for i, ox in enumerate([-10, -3, 4, 11]):
        fy = y - 18 - (2 if i in (1, 2) else 0)
        limb(d, x + ox, y - 6, x + ox + facing, fy, 6, SKIN)
    # thumb
    limb(d, x - 12 * facing, y + 2, x - 22 * facing, y - 6, 7, SKIN)


def hand_point(d, x, y):
    oval(d, [x - 12, y - 10, x + 12, y + 12], SKIN)
    limb(d, x + 4, y - 6, x + 28, y - 28, 7, SKIN)
    for ox in [-8, -2, 6]:
        limb(d, x + ox, y - 4, x + ox - 2, y - 14, 5, SKIN)


def foot_front(d, x, y):
    oval(d, [x - 22, y - 6, x + 22, y + 16], SHOE)
    oval(d, [x - 8, y - 2, x + 18, y + 10], (50, 50, 55, 255))


def foot_side(d, x, y, left: bool):
    if left:
        oval(d, [x - 30, y - 5, x + 10, y + 16], SHOE)
    else:
        oval(d, [x - 10, y - 5, x + 30, y + 16], SHOE)


def head_front(d, cx, hy, expr="neutral"):
    # rounded head
    oval(d, [cx - 55, hy - 58, cx + 55, hy + 50], SKIN)
    # hair cap + spike
    oval(d, [cx - 58, hy - 68, cx + 58, hy - 8], HAIR)
    d.polygon(
        [(cx - 18, hy - 48), (cx - 2, hy - 92), (cx + 14, hy - 50),
         (cx + 30, hy - 85), (cx + 40, hy - 45)],
        fill=HAIR,
    )
    # ears
    oval(d, [cx - 64, hy - 6, cx - 48, hy + 20], SKIN)
    oval(d, [cx + 48, hy - 6, cx + 64, hy + 20], SKIN)
    # cheeks
    oval(d, [cx - 46, hy + 10, cx - 26, hy + 26], CHEEK)
    oval(d, [cx + 26, hy + 10, cx + 46, hy + 26], CHEEK)

    ey = hy - 8
    if expr == "blink":
        d.line([(cx - 30, ey), (cx - 12, ey)], fill=BLACK, width=4)
        d.line([(cx + 12, ey), (cx + 30, ey)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming", "giggle"):
        d.arc([cx - 32, ey - 2, cx - 10, ey + 14], 200, 340, fill=BLACK, width=4)
        d.arc([cx + 10, ey - 2, cx + 32, ey + 14], 200, 340, fill=BLACK, width=4)
    else:
        # big cartoon eyes
        oval(d, [cx - 34, ey - 16, cx - 8, ey + 12], WHITE, BLACK, 3)
        oval(d, [cx + 8, ey - 16, cx + 34, ey + 12], WHITE, BLACK, 3)
        oval(d, [cx - 26, ey - 6, cx - 14, ey + 6], BLACK)
        oval(d, [cx + 14, ey - 6, cx + 26, ey + 6], BLACK)
        oval(d, [cx - 22, ey - 10, cx - 16, ey - 4], WHITE)
        oval(d, [cx + 18, ey - 10, cx + 24, ey - 4], WHITE)

    # brows
    if expr == "confused":
        d.line([(cx - 32, ey - 24), (cx - 10, ey - 18)], fill=BLACK, width=4)
        d.line([(cx + 10, ey - 20), (cx + 32, ey - 26)], fill=BLACK, width=4)
    elif expr == "question":
        d.line([(cx - 32, ey - 26), (cx - 10, ey - 22)], fill=BLACK, width=4)
        d.line([(cx + 10, ey - 22), (cx + 32, ey - 26)], fill=BLACK, width=4)
    else:
        d.line([(cx - 32, ey - 22), (cx - 10, ey - 22)], fill=BLACK, width=3)
        d.line([(cx + 10, ey - 22), (cx + 32, ey - 22)], fill=BLACK, width=3)

    # nose
    oval(d, [cx - 5, hy + 6, cx + 5, hy + 18], SKIN_D)


def head_side(d, cx, hy, facing="left"):
    """True profile — ear, one eye, nose toward walk, closed mouth baked."""
    sign = -1 if facing == "left" else 1
    oval(d, [cx - 40, hy - 52, cx + 40, hy + 42], SKIN)
    oval(d, [cx - 42, hy - 64, cx + 28, hy - 4], HAIR)
    d.polygon(
        [(cx - 6, hy - 42), (cx + sign * 10, hy - 88), (cx + 16, hy - 38)],
        fill=HAIR,
    )
    # ear on back of head
    ex = cx - sign * 34
    oval(d, [ex - 10, hy - 4, ex + 10, hy + 20], SKIN, BLACK, 2)
    oval(d, [ex - 4, hy + 4, ex + 4, hy + 14], SKIN_D)
    # eye
    eye_x = cx + sign * 10
    oval(d, [eye_x - 11, hy - 14, eye_x + 11, hy + 8], WHITE, BLACK, 2)
    oval(d, [eye_x - 4, hy - 4, eye_x + 4, hy + 4], BLACK)
    # nose
    nx = cx + sign * 38
    oval(d, [nx - 6, hy + 2, nx + 6, hy + 16], SKIN_D)
    # profile mouth
    mx = cx + sign * 16
    d.arc([mx - 9, hy + 20, mx + 9, hy + 32], 20, 160, fill=BLACK, width=3)


def torso_front(d, cx, sy):
    d.rounded_rectangle([cx - 58, sy, cx + 58, sy + 175], 30, fill=HOODIE)
    d.rounded_rectangle([cx - 38, sy + 40, cx + 38, sy + 150], 18, fill=HOODIE_L)
    # pocket hint
    d.rounded_rectangle([cx - 28, sy + 90, cx + 28, sy + 130], 10, fill=HOODIE_D)


def torso_side(d, cx, sy):
    d.rounded_rectangle([cx - 36, sy, cx + 36, sy + 170], 24, fill=HOODIE)
    d.rounded_rectangle([cx - 20, sy + 40, cx + 20, sy + 145], 12, fill=HOODIE_L)


def draw_walk(facing: str, phase: int) -> Image.Image:
    """Human-ish side walk: opposite arm/leg, clear profile."""
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    left = facing == "left"
    sign = -1 if left else 1

    oval(d, [cx - 50, FOOT + 2, cx + 50, FOOT + 22], (0, 0, 0, 35))

    if phase == 0:
        # leading leg (facing dir)
        limb(d, cx + sign * 6, HIP, cx + sign * 40, KNEE - 10, 32, PANTS)
        limb(d, cx + sign * 40, KNEE - 10, cx + sign * 52, FOOT - 12, 28, PANTS)
        foot_side(d, cx + sign * 52, FOOT - 6, left)
        # trailing leg
        limb(d, cx - sign * 6, HIP, cx - sign * 28, KNEE + 15, 32, PANTS)
        limb(d, cx - sign * 28, KNEE + 15, cx - sign * 18, FOOT, 28, PANTS)
        foot_side(d, cx - sign * 18, FOOT + 2, left)
        # opposite arms
        limb(d, cx - sign * 30, SHOULDER + 25, cx - sign * 55, SHOULDER + 110, 28, HOODIE)
        hand_open(d, cx - sign * 58, SHOULDER + 122, -sign)
        limb(d, cx + sign * 30, SHOULDER + 25, cx + sign * 62, SHOULDER + 5, 28, HOODIE)
        hand_open(d, cx + sign * 70, SHOULDER - 2, sign)
    else:
        limb(d, cx - sign * 6, HIP, cx - sign * 40, KNEE - 10, 32, PANTS)
        limb(d, cx - sign * 40, KNEE - 10, cx - sign * 52, FOOT - 12, 28, PANTS)
        foot_side(d, cx - sign * 52, FOOT - 6, left)
        limb(d, cx + sign * 6, HIP, cx + sign * 28, KNEE + 15, 32, PANTS)
        limb(d, cx + sign * 28, KNEE + 15, cx + sign * 18, FOOT, 28, PANTS)
        foot_side(d, cx + sign * 18, FOOT + 2, left)
        limb(d, cx + sign * 30, SHOULDER + 25, cx + sign * 55, SHOULDER + 110, 28, HOODIE)
        hand_open(d, cx + sign * 58, SHOULDER + 122, sign)
        limb(d, cx - sign * 30, SHOULDER + 25, cx - sign * 62, SHOULDER + 5, 28, HOODIE)
        hand_open(d, cx - sign * 70, SHOULDER - 2, -sign)

    torso_side(d, cx, SHOULDER)
    d.rounded_rectangle([cx - 12, NECK, cx + 12, SHOULDER + 8], 8, fill=SKIN)
    head_side(d, cx, HEAD_Y, facing)
    return img


def draw_pose(mode: str = "stand", expr: str = "neutral") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    oval(d, [cx - 60, FOOT + 2, cx + 60, FOOT + 24], (0, 0, 0, 40))

    if mode == "point":
        limb(d, cx - 16, HIP, cx - 16, KNEE, 30, PANTS)
        limb(d, cx - 16, KNEE, cx - 16, FOOT, 26, PANTS)
        limb(d, cx + 16, HIP, cx + 16, KNEE, 30, PANTS)
        limb(d, cx + 16, KNEE, cx + 16, FOOT, 26, PANTS)
        foot_front(d, cx - 16, FOOT)
        foot_front(d, cx + 16, FOOT)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 48, SHOULDER + 30, cx - 62, SHOULDER + 130, 28, HOODIE)
        hand_open(d, cx - 64, SHOULDER + 142, -1)
        limb(d, cx + 48, SHOULDER + 28, cx + 115, SHOULDER - 40, 30, HOODIE)
        hand_point(d, cx + 122, SHOULDER - 52)
        d.rounded_rectangle([cx - 12, NECK, cx + 12, SHOULDER + 10], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    elif mode == "present":
        limb(d, cx - 16, HIP, cx - 16, KNEE, 30, PANTS)
        limb(d, cx - 16, KNEE, cx - 16, FOOT, 26, PANTS)
        limb(d, cx + 16, HIP, cx + 16, KNEE, 30, PANTS)
        limb(d, cx + 16, KNEE, cx + 16, FOOT, 26, PANTS)
        foot_front(d, cx - 16, FOOT)
        foot_front(d, cx + 16, FOOT)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 50, SHOULDER + 32, cx - 120, SHOULDER + 50, 30, HOODIE)
        hand_open(d, cx - 130, SHOULDER + 45, -1)
        limb(d, cx + 50, SHOULDER + 32, cx + 120, SHOULDER + 50, 30, HOODIE)
        hand_open(d, cx + 130, SHOULDER + 45, 1)
        d.rounded_rectangle([cx - 12, NECK, cx + 12, SHOULDER + 10], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr if expr != "neutral" else "welcoming")

    elif mode == "sit":
        sit_hip, sit_knee, sit_foot = 450, 495, 600
        limb(d, cx - 18, sit_hip, cx - 72, sit_knee, 32, PANTS)
        limb(d, cx + 18, sit_hip, cx + 72, sit_knee, 32, PANTS)
        limb(d, cx - 72, sit_knee, cx - 78, sit_foot, 28, PANTS)
        limb(d, cx + 72, sit_knee, cx + 78, sit_foot, 28, PANTS)
        foot_front(d, cx - 78, sit_foot)
        foot_front(d, cx + 78, sit_foot)
        torso_front(d, cx, SHOULDER + 55)
        limb(d, cx - 48, SHOULDER + 90, cx - 55, SHOULDER + 175, 28, HOODIE)
        hand_open(d, cx - 55, SHOULDER + 188, -1)
        limb(d, cx + 48, SHOULDER + 90, cx + 55, SHOULDER + 175, 28, HOODIE)
        hand_open(d, cx + 55, SHOULDER + 188, 1)
        d.rounded_rectangle([cx - 12, NECK + 50, cx + 12, SHOULDER + 65], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y + 48, expr)

    else:
        limb(d, cx - 16, HIP, cx - 16, KNEE, 30, PANTS)
        limb(d, cx - 16, KNEE, cx - 16, FOOT, 26, PANTS)
        limb(d, cx + 16, HIP, cx + 16, KNEE, 30, PANTS)
        limb(d, cx + 16, KNEE, cx + 16, FOOT, 26, PANTS)
        foot_front(d, cx - 16, FOOT)
        foot_front(d, cx + 16, FOOT)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 48, SHOULDER + 32, cx - 60, SHOULDER + 135, 28, HOODIE)
        hand_open(d, cx - 62, SHOULDER + 148, -1)
        limb(d, cx + 48, SHOULDER + 32, cx + 60, SHOULDER + 135, 28, HOODIE)
        hand_open(d, cx + 62, SHOULDER + 148, 1)
        d.rounded_rectangle([cx - 12, NECK, cx + 12, SHOULDER + 10], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, HEAD_Y + 30
    if kind == "closed":
        d.arc([cx - 15, my - 2, cx + 15, my + 12], 20, 160, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 13, my, cx + 13, my + 18], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 9, my + 2, cx + 9, my + 7], TEETH)
    elif kind == "smile":
        d.arc([cx - 17, my - 4, cx + 17, my + 14], 15, 165, fill=BLACK, width=4)
    else:
        oval(d, [cx - 15, my, cx + 15, my + 22], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 10, my + 2, cx + 10, my + 7], TEETH)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    draw_walk("left", 0).save(out / "walk_l0.png")
    draw_walk("left", 1).save(out / "walk_l1.png")
    draw_walk("right", 0).save(out / "walk_r0.png")
    draw_walk("right", 1).save(out / "walk_r1.png")
    draw_walk("left", 0).save(out / "body_side_left.png")
    draw_walk("right", 0).save(out / "body_side_right.png")
    print("wrote walk frames")
    poses = {
        "body.png": ("stand", "neutral"),
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
