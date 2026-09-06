#!/usr/bin/env python3
"""Mike poses — improved side walk (profile, leg stride, arm swing)."""
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


def foot_side(d, x, y, facing_left: bool):
    if facing_left:
        oval(d, [x - 32, y - 6, x + 8, y + 16], SHOE)
    else:
        oval(d, [x - 8, y - 6, x + 32, y + 16], SHOE)


def head_front(d, cx, hy, expr="neutral"):
    oval(d, [cx - 58, hy - 62, cx + 58, hy + 52], SKIN)
    oval(d, [cx - 60, hy - 70, cx + 60, hy - 5], HAIR)
    d.polygon(
        [(cx - 20, hy - 50), (cx - 5, hy - 88), (cx + 12, hy - 52),
         (cx + 28, hy - 82), (cx + 42, hy - 48)],
        fill=HAIR,
    )
    oval(d, [cx - 68, hy - 8, cx - 52, hy + 22], SKIN)
    oval(d, [cx + 52, hy - 8, cx + 68, hy + 22], SKIN)
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
    oval(d, [cx - 6, hy + 8, cx + 6, hy + 22], SKIN_D)


def head_side(d, cx, hy, facing="left"):
    """Clear profile: one ear, one eye, nose toward walk direction. No front mouth."""
    sign = -1 if facing == "left" else 1
    # skull
    oval(d, [cx - 42, hy - 55, cx + 42, hy + 45], SKIN)
    # hair mass
    oval(d, [cx - 44, hy - 68, cx + 30, hy - 2], HAIR)
    d.polygon(
        [(cx - 8, hy - 48), (cx + sign * 12, hy - 85), (cx + 18, hy - 40)],
        fill=HAIR,
    )
    # ear (back of head)
    ex = cx - sign * 36
    oval(d, [ex - 11, hy - 4, ex + 11, hy + 22], SKIN, BLACK, 2)
    oval(d, [ex - 5, hy + 4, ex + 5, hy + 14], SKIN_D)
    # eye
    eye_x = cx + sign * 12
    oval(d, [eye_x - 11, hy - 12, eye_x + 11, hy + 8], WHITE, BLACK, 2)
    oval(d, [eye_x - 3, hy - 4, eye_x + 5, hy + 4], BLACK)
    # nose tip toward direction
    nx = cx + sign * 40
    oval(d, [nx - 6, hy + 2, nx + 6, hy + 18], SKIN_D)
    # closed profile mouth line (baked in — no separate mouth layer)
    mx = cx + sign * 18
    d.arc([mx - 10, hy + 22, mx + 10, hy + 34], 20, 160, fill=BLACK, width=3)


def torso_side(d, cx, sy):
    # narrower side torso
    d.rounded_rectangle([cx - 38, sy, cx + 38, sy + 145], 22, fill=HOODIE)
    d.rounded_rectangle([cx - 22, sy + 30, cx + 22, sy + 125], 14, fill=HOODIE_L)


def torso_front(d, cx, sy):
    d.rounded_rectangle([cx - 62, sy, cx + 62, sy + 150], 28, fill=HOODIE)
    d.rounded_rectangle([cx - 40, sy + 35, cx + 40, sy + 130], 20, fill=HOODIE_L)
    d.arc([cx - 50, sy - 8, cx + 50, sy + 40], 200, 340, fill=HOODIE_D, width=6)


def draw_walk(facing: str, phase: int) -> Image.Image:
    """phase 0 = left leg forward, phase 1 = right leg forward."""
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    left = facing == "left"
    sign = -1 if left else 1

    oval(d, [cx - 55, FOOT + 4, cx + 55, FOOT + 24], (0, 0, 0, 35))

    # legs: stride
    if phase == 0:
        # front leg (toward facing)
        limb(d, cx + sign * 4, HIP, cx + sign * 35, KNEE - 5, 30, PANTS)
        limb(d, cx + sign * 35, KNEE - 5, cx + sign * 48, FOOT - 8, 26, PANTS)
        foot_side(d, cx + sign * 48, FOOT - 4, left)
        # back leg
        limb(d, cx - sign * 4, HIP, cx - sign * 20, KNEE + 10, 30, PANTS)
        limb(d, cx - sign * 20, KNEE + 10, cx - sign * 10, FOOT, 26, PANTS)
        foot_side(d, cx - sign * 10, FOOT + 2, left)
        # arms opposite to legs
        limb(d, cx - sign * 28, SHOULDER + 28, cx - sign * 55, SHOULDER + 95, 26, HOODIE)
        hand(d, cx - sign * 58, SHOULDER + 108)
        limb(d, cx + sign * 28, SHOULDER + 28, cx + sign * 60, SHOULDER + 15, 26, HOODIE)
        hand(d, cx + sign * 68, SHOULDER + 10)
    else:
        limb(d, cx - sign * 4, HIP, cx - sign * 35, KNEE - 5, 30, PANTS)
        limb(d, cx - sign * 35, KNEE - 5, cx - sign * 48, FOOT - 8, 26, PANTS)
        foot_side(d, cx - sign * 48, FOOT - 4, left)
        limb(d, cx + sign * 4, HIP, cx + sign * 20, KNEE + 10, 30, PANTS)
        limb(d, cx + sign * 20, KNEE + 10, cx + sign * 10, FOOT, 26, PANTS)
        foot_side(d, cx + sign * 10, FOOT + 2, left)
        limb(d, cx + sign * 28, SHOULDER + 28, cx + sign * 55, SHOULDER + 95, 26, HOODIE)
        hand(d, cx + sign * 58, SHOULDER + 108)
        limb(d, cx - sign * 28, SHOULDER + 28, cx - sign * 60, SHOULDER + 15, 26, HOODIE)
        hand(d, cx - sign * 68, SHOULDER + 10)

    torso_side(d, cx, SHOULDER)
    d.rounded_rectangle([cx - 12, NECK_TOP, cx + 12, SHOULDER + 10], 8, fill=SKIN)
    head_side(d, cx, HEAD_Y, facing)
    return img


def draw_pose(mode: str = "stand", expr: str = "neutral") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    oval(d, [cx - 70, FOOT + 4, cx + 70, FOOT + 28], (0, 0, 0, 40))

    if mode == "point":
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        oval(d, [cx - 40, FOOT - 6, cx + 0, FOOT + 14], SHOE)
        oval(d, [cx + 0, FOOT - 6, cx + 40, FOOT + 14], SHOE)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 50, SHOULDER + 35, cx - 70, SHOULDER + 120, 26, HOODIE)
        hand(d, cx - 72, SHOULDER + 132)
        limb(d, cx + 50, SHOULDER + 30, cx + 115, SHOULDER - 35, 28, HOODIE)
        hand(d, cx + 122, SHOULDER - 48)
        limb(d, cx + 122, SHOULDER - 48, cx + 155, SHOULDER - 68, 8, SKIN)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    elif mode == "present":
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        oval(d, [cx - 40, FOOT - 6, cx + 0, FOOT + 14], SHOE)
        oval(d, [cx + 0, FOOT - 6, cx + 40, FOOT + 14], SHOE)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 52, SHOULDER + 35, cx - 115, SHOULDER + 55, 28, HOODIE)
        hand(d, cx - 125, SHOULDER + 50)
        limb(d, cx + 52, SHOULDER + 35, cx + 115, SHOULDER + 55, 28, HOODIE)
        hand(d, cx + 125, SHOULDER + 50)
        d.rounded_rectangle([cx - 14, NECK_TOP, cx + 14, SHOULDER + 12], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr if expr != "neutral" else "welcoming")

    elif mode == "sit":
        sit_hip, sit_knee, sit_foot = 430, 470, 560
        limb(d, cx - 20, sit_hip, cx - 70, sit_knee, 30, PANTS)
        limb(d, cx + 20, sit_hip, cx + 70, sit_knee, 30, PANTS)
        limb(d, cx - 70, sit_knee, cx - 75, sit_foot, 26, PANTS)
        limb(d, cx + 70, sit_knee, cx + 75, sit_foot, 26, PANTS)
        oval(d, [cx - 95, sit_foot - 6, cx - 55, sit_foot + 14], SHOE)
        oval(d, [cx + 55, sit_foot - 6, cx + 95, sit_foot + 14], SHOE)
        torso_front(d, cx, SHOULDER + 50)
        limb(d, cx - 50, SHOULDER + 85, cx - 55, SHOULDER + 160, 26, HOODIE)
        hand(d, cx - 55, SHOULDER + 172)
        limb(d, cx + 50, SHOULDER + 85, cx + 55, SHOULDER + 160, 26, HOODIE)
        hand(d, cx + 55, SHOULDER + 172)
        d.rounded_rectangle([cx - 14, NECK_TOP + 45, cx + 14, SHOULDER + 62], 8, fill=SKIN)
        head_front(d, cx, HEAD_Y + 40, expr)

    else:
        limb(d, cx - 18, HIP, cx - 18, KNEE, 28, PANTS)
        limb(d, cx - 18, KNEE, cx - 18, FOOT, 24, PANTS)
        limb(d, cx + 18, HIP, cx + 18, KNEE, 28, PANTS)
        limb(d, cx + 18, KNEE, cx + 18, FOOT, 24, PANTS)
        oval(d, [cx - 40, FOOT - 6, cx + 0, FOOT + 14], SHOE)
        oval(d, [cx + 0, FOOT - 6, cx + 40, FOOT + 14], SHOE)
        torso_front(d, cx, SHOULDER)
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
    # walk cycle 2 phases each direction
    draw_walk("left", 0).save(out / "walk_l0.png")
    draw_walk("left", 1).save(out / "walk_l1.png")
    draw_walk("right", 0).save(out / "walk_r0.png")
    draw_walk("right", 1).save(out / "walk_r1.png")
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
        # keep aliases
        "body_side_left.png": None,
        "body_side_right.png": None,
    }
    for name, spec in poses.items():
        if spec is None:
            continue
        draw_pose(*spec).save(out / name, "PNG")
        print("wrote", name)
    # aliases for old code paths
    draw_walk("left", 0).save(out / "body_side_left.png")
    draw_walk("right", 0).save(out / "body_side_right.png")
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
