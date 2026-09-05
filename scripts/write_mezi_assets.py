#!/usr/bin/env python3
"""Mike: tall geometric figure (wireframe-inspired) with joints, colored, multi-pose."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 440, 780
# Mike colors
HOODIE = (255, 196, 40, 255)
HOODIE_D = (230, 160, 20, 255)
HOODIE_L = (255, 220, 100, 255)
SKIN = (220, 170, 130, 255)
SKIN_D = (190, 140, 105, 255)
HAIR = (35, 30, 40, 255)
PANTS = (45, 50, 65, 255)
SHOE = (25, 25, 30, 255)
JOINT = (255, 240, 200, 255)
JOINT_L = (180, 180, 190, 255)
WHITE = (255, 255, 255, 255)
BLACK = (20, 18, 22, 255)
MOUTH_IN = (120, 45, 55, 255)
TEETH = (250, 245, 240, 255)

CX = W // 2


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def joint(d, x, y, r=9):
    oval(d, [x - r, y - r, x + r, y + r], JOINT, JOINT_L, 2)


def limb_seg(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2, 3)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def head_front(d, cx, hy, expr: str = "neutral"):
    # tall angular head like the sketch
    oval(d, [cx - 42, hy - 58, cx + 42, hy + 38], SKIN)
    # hair spike
    d.polygon(
        [(cx - 30, hy - 40), (cx - 8, hy - 78), (cx + 5, hy - 45),
         (cx + 18, hy - 72), (cx + 32, hy - 42), (cx + 38, hy - 20),
         (cx - 38, hy - 20)],
        fill=HAIR,
    )
    oval(d, [cx - 44, hy - 50, cx + 44, hy - 8], HAIR)
    # ears
    oval(d, [cx - 52, hy - 8, cx - 38, hy + 16], SKIN)
    oval(d, [cx + 38, hy - 8, cx + 52, hy + 16], SKIN)
    # brows / eyes by expression
    ey = hy - 8
    if expr == "confused":
        d.line([(cx - 28, ey - 14), (cx - 10, ey - 8)], fill=BLACK, width=3)
        d.line([(cx + 10, ey - 10), (cx + 28, ey - 16)], fill=BLACK, width=3)
    elif expr == "question":
        d.line([(cx - 28, ey - 16), (cx - 10, ey - 12)], fill=BLACK, width=3)
        d.line([(cx + 10, ey - 12), (cx + 28, ey - 16)], fill=BLACK, width=3)
    elif expr in ("happy", "giggle", "encouraging", "welcoming"):
        d.arc([cx - 30, ey - 18, cx - 8, ey - 4], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 8, ey - 18, cx + 30, ey - 4], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 28, ey - 14), (cx - 10, ey - 14)], fill=BLACK, width=3)
        d.line([(cx + 10, ey - 14), (cx + 28, ey - 14)], fill=BLACK, width=3)

    if expr == "blink":
        d.line([(cx - 26, ey), (cx - 10, ey)], fill=BLACK, width=3)
        d.line([(cx + 10, ey), (cx + 26, ey)], fill=BLACK, width=3)
    elif expr in ("happy", "giggle"):
        d.arc([cx - 28, ey - 2, cx - 8, ey + 12], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 8, ey - 2, cx + 28, ey + 12], 200, 340, fill=BLACK, width=3)
    else:
        oval(d, [cx - 26, ey - 10, cx - 8, ey + 10], WHITE, BLACK, 2)
        oval(d, [cx + 8, ey - 10, cx + 26, ey + 10], WHITE, BLACK, 2)
        # pupils look slightly inward
        oval(d, [cx - 20, ey - 4, cx - 12, ey + 4], BLACK)
        oval(d, [cx + 12, ey - 4, cx + 20, ey + 4], BLACK)

    # nose angular
    d.polygon([(cx, hy + 4), (cx - 6, hy + 18), (cx + 6, hy + 18)], fill=SKIN_D)


def head_side(d, cx, hy, facing: str = "left"):
    sign = -1 if facing == "left" else 1
    oval(d, [cx - 36, hy - 55, cx + 36, hy + 36], SKIN)
    d.polygon(
        [(cx - 20, hy - 40), (cx + sign * 5, hy - 75), (cx + 20, hy - 38)],
        fill=HAIR,
    )
    oval(d, [cx - 38, hy - 48, cx + 30, hy - 5], HAIR)
    # ear
    ex = cx - sign * 32
    oval(d, [ex - 10, hy - 6, ex + 10, hy + 20], SKIN, BLACK, 2)
    # one eye
    eye_x = cx + sign * 10
    oval(d, [eye_x - 9, hy - 12, eye_x + 9, hy + 6], WHITE, BLACK, 2)
    oval(d, [eye_x - 3, hy - 5, eye_x + 3, hy + 1], BLACK)
    # nose
    nx = cx + sign * 34
    oval(d, [nx - 5, hy + 2, nx + 5, hy + 16], SKIN_D)


def torso(d, cx, ty, tw=70, th=110):
    # diamond-ish geometric torso like sketch
    d.polygon(
        [
            (cx, ty),
            (cx + tw // 2 + 8, ty + 28),
            (cx + tw // 2, ty + th),
            (cx - tw // 2, ty + th),
            (cx - tw // 2 - 8, ty + 28),
        ],
        fill=HOODIE,
    )
    d.polygon(
        [
            (cx, ty + 18),
            (cx + 22, ty + 40),
            (cx + 18, ty + th - 10),
            (cx - 18, ty + th - 10),
            (cx - 22, ty + 40),
        ],
        fill=HOODIE_L,
    )


def draw_pose(mode: str = "stand", expr: str = "neutral") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    # vertical layout — tall like sketch
    hy = 175  # head center
    neck_y = 225
    shoulder_y = 250
    hip_y = 380
    knee_y = 520
    foot_y = 650

    # shadow
    oval(d, [cx - 55, foot_y + 8, cx + 55, foot_y + 28], (0, 0, 0, 35))

    if mode == "side_left":
        # walk cycle left-facing
        # back leg
        limb_seg(d, cx + 5, hip_y, cx + 18, knee_y - 10, 16, PANTS)
        limb_seg(d, cx + 18, knee_y - 10, cx + 30, foot_y - 5, 14, PANTS)
        joint(d, cx + 18, knee_y - 10, 7)
        oval(d, [cx + 18, foot_y - 12, cx + 52, foot_y + 8], SHOE)
        # front leg
        limb_seg(d, cx - 5, hip_y, cx - 22, knee_y + 5, 16, PANTS)
        limb_seg(d, cx - 22, knee_y + 5, cx - 35, foot_y, 14, PANTS)
        joint(d, cx - 22, knee_y + 5, 7)
        oval(d, [cx - 55, foot_y - 8, cx - 18, foot_y + 12], SHOE)
        torso(d, cx, shoulder_y, 58, 120)
        joint(d, cx, hip_y, 8)
        # arms swing opposite
        limb_seg(d, cx + 20, shoulder_y + 15, cx + 40, shoulder_y + 90, 14, HOODIE)
        joint(d, cx + 40, shoulder_y + 90, 6)
        limb_seg(d, cx + 40, shoulder_y + 90, cx + 48, shoulder_y + 140, 12, SKIN)
        limb_seg(d, cx - 18, shoulder_y + 15, cx - 50, shoulder_y + 50, 14, HOODIE)
        joint(d, cx - 50, shoulder_y + 50, 6)
        limb_seg(d, cx - 50, shoulder_y + 50, cx - 58, shoulder_y + 20, 12, SKIN)
        joint(d, cx - 20, shoulder_y + 12, 7)
        joint(d, cx + 20, shoulder_y + 12, 7)
        # neck
        d.rectangle([cx - 10, neck_y, cx + 10, shoulder_y + 8], fill=SKIN)
        joint(d, cx, neck_y + 5, 6)
        head_side(d, cx, hy, "left")

    elif mode == "side_right":
        limb_seg(d, cx - 5, hip_y, cx - 18, knee_y - 10, 16, PANTS)
        limb_seg(d, cx - 18, knee_y - 10, cx - 30, foot_y - 5, 14, PANTS)
        joint(d, cx - 18, knee_y - 10, 7)
        oval(d, [cx - 52, foot_y - 12, cx - 18, foot_y + 8], SHOE)
        limb_seg(d, cx + 5, hip_y, cx + 22, knee_y + 5, 16, PANTS)
        limb_seg(d, cx + 22, knee_y + 5, cx + 35, foot_y, 14, PANTS)
        joint(d, cx + 22, knee_y + 5, 7)
        oval(d, [cx + 18, foot_y - 8, cx + 55, foot_y + 12], SHOE)
        torso(d, cx, shoulder_y, 58, 120)
        joint(d, cx, hip_y, 8)
        limb_seg(d, cx - 20, shoulder_y + 15, cx - 40, shoulder_y + 90, 14, HOODIE)
        joint(d, cx - 40, shoulder_y + 90, 6)
        limb_seg(d, cx - 40, shoulder_y + 90, cx - 48, shoulder_y + 140, 12, SKIN)
        limb_seg(d, cx + 18, shoulder_y + 15, cx + 50, shoulder_y + 50, 14, HOODIE)
        joint(d, cx + 50, shoulder_y + 50, 6)
        limb_seg(d, cx + 50, shoulder_y + 50, cx + 58, shoulder_y + 20, 12, SKIN)
        joint(d, cx - 20, shoulder_y + 12, 7)
        joint(d, cx + 20, shoulder_y + 12, 7)
        d.rectangle([cx - 10, neck_y, cx + 10, shoulder_y + 8], fill=SKIN)
        joint(d, cx, neck_y + 5, 6)
        head_side(d, cx, hy, "right")

    elif mode == "point":
        limb_seg(d, cx - 14, hip_y, cx - 14, knee_y, 16, PANTS)
        limb_seg(d, cx - 14, knee_y, cx - 14, foot_y, 14, PANTS)
        limb_seg(d, cx + 14, hip_y, cx + 14, knee_y, 16, PANTS)
        limb_seg(d, cx + 14, knee_y, cx + 14, foot_y, 14, PANTS)
        joint(d, cx - 14, knee_y, 7)
        joint(d, cx + 14, knee_y, 7)
        oval(d, [cx - 36, foot_y - 8, cx + 2, foot_y + 12], SHOE)
        oval(d, [cx - 2, foot_y - 8, cx + 36, foot_y + 12], SHOE)
        torso(d, cx, shoulder_y, 70, 115)
        joint(d, cx, hip_y, 8)
        # left arm rest
        limb_seg(d, cx - 28, shoulder_y + 18, cx - 55, shoulder_y + 100, 14, HOODIE)
        joint(d, cx - 55, shoulder_y + 100, 6)
        limb_seg(d, cx - 55, shoulder_y + 100, cx - 60, shoulder_y + 145, 12, SKIN)
        # right arm point up-right
        limb_seg(d, cx + 28, shoulder_y + 18, cx + 85, shoulder_y - 20, 15, HOODIE)
        joint(d, cx + 85, shoulder_y - 20, 7)
        limb_seg(d, cx + 85, shoulder_y - 20, cx + 130, shoulder_y - 55, 12, SKIN)
        # finger
        limb_seg(d, cx + 130, shoulder_y - 55, cx + 155, shoulder_y - 70, 6, SKIN)
        joint(d, cx - 28, shoulder_y + 14, 7)
        joint(d, cx + 28, shoulder_y + 14, 7)
        d.rectangle([cx - 11, neck_y, cx + 11, shoulder_y + 10], fill=SKIN)
        joint(d, cx, neck_y + 5, 6)
        head_front(d, cx, hy, expr)

    elif mode == "present":
        limb_seg(d, cx - 14, hip_y, cx - 14, knee_y, 16, PANTS)
        limb_seg(d, cx - 14, knee_y, cx - 14, foot_y, 14, PANTS)
        limb_seg(d, cx + 14, hip_y, cx + 14, knee_y, 16, PANTS)
        limb_seg(d, cx + 14, knee_y, cx + 14, foot_y, 14, PANTS)
        joint(d, cx - 14, knee_y, 7)
        joint(d, cx + 14, knee_y, 7)
        oval(d, [cx - 36, foot_y - 8, cx + 2, foot_y + 12], SHOE)
        oval(d, [cx - 2, foot_y - 8, cx + 36, foot_y + 12], SHOE)
        torso(d, cx, shoulder_y, 70, 115)
        joint(d, cx, hip_y, 8)
        limb_seg(d, cx - 30, shoulder_y + 18, cx - 95, shoulder_y + 40, 15, HOODIE)
        joint(d, cx - 95, shoulder_y + 40, 7)
        limb_seg(d, cx - 95, shoulder_y + 40, cx - 115, shoulder_y + 15, 12, SKIN)
        limb_seg(d, cx + 30, shoulder_y + 18, cx + 95, shoulder_y + 40, 15, HOODIE)
        joint(d, cx + 95, shoulder_y + 40, 7)
        limb_seg(d, cx + 95, shoulder_y + 40, cx + 115, shoulder_y + 15, 12, SKIN)
        joint(d, cx - 28, shoulder_y + 14, 7)
        joint(d, cx + 28, shoulder_y + 14, 7)
        d.rectangle([cx - 11, neck_y, cx + 11, shoulder_y + 10], fill=SKIN)
        joint(d, cx, neck_y + 5, 6)
        head_front(d, cx, hy, expr if expr != "neutral" else "welcoming")

    elif mode == "sit":
        # seated on imaginary stool
        sit_hip = 480
        limb_seg(d, cx - 20, sit_hip, cx - 55, sit_hip + 20, 16, PANTS)
        limb_seg(d, cx - 55, sit_hip + 20, cx - 70, sit_hip + 90, 14, PANTS)
        limb_seg(d, cx + 20, sit_hip, cx + 55, sit_hip + 20, 16, PANTS)
        limb_seg(d, cx + 55, sit_hip + 20, cx + 70, sit_hip + 90, 14, PANTS)
        joint(d, cx - 55, sit_hip + 20, 7)
        joint(d, cx + 55, sit_hip + 20, 7)
        oval(d, [cx - 90, sit_hip + 82, cx - 55, sit_hip + 105], SHOE)
        oval(d, [cx + 55, sit_hip + 82, cx + 90, sit_hip + 105], SHOE)
        torso(d, cx, shoulder_y + 40, 72, 110)
        joint(d, cx, sit_hip, 8)
        limb_seg(d, cx - 30, shoulder_y + 55, cx - 50, shoulder_y + 130, 14, HOODIE)
        limb_seg(d, cx + 30, shoulder_y + 55, cx + 50, shoulder_y + 130, 14, HOODIE)
        joint(d, cx - 50, shoulder_y + 130, 6)
        joint(d, cx + 50, shoulder_y + 130, 6)
        limb_seg(d, cx - 50, shoulder_y + 130, cx - 45, shoulder_y + 165, 12, SKIN)
        limb_seg(d, cx + 50, shoulder_y + 130, cx + 45, shoulder_y + 165, 12, SKIN)
        d.rectangle([cx - 11, neck_y + 35, cx + 11, shoulder_y + 50], fill=SKIN)
        head_front(d, cx, hy + 30, expr)

    else:  # stand / talk
        limb_seg(d, cx - 14, hip_y, cx - 14, knee_y, 16, PANTS)
        limb_seg(d, cx - 14, knee_y, cx - 14, foot_y, 14, PANTS)
        limb_seg(d, cx + 14, hip_y, cx + 14, knee_y, 16, PANTS)
        limb_seg(d, cx + 14, knee_y, cx + 14, foot_y, 14, PANTS)
        joint(d, cx - 14, knee_y, 7)
        joint(d, cx + 14, knee_y, 7)
        joint(d, cx, hip_y, 8)
        oval(d, [cx - 36, foot_y - 8, cx + 2, foot_y + 12], SHOE)
        oval(d, [cx - 2, foot_y - 8, cx + 36, foot_y + 12], SHOE)
        torso(d, cx, shoulder_y, 70, 115)
        limb_seg(d, cx - 28, shoulder_y + 18, cx - 48, shoulder_y + 110, 14, HOODIE)
        limb_seg(d, cx + 28, shoulder_y + 18, cx + 48, shoulder_y + 110, 14, HOODIE)
        joint(d, cx - 48, shoulder_y + 110, 6)
        joint(d, cx + 48, shoulder_y + 110, 6)
        limb_seg(d, cx - 48, shoulder_y + 110, cx - 52, shoulder_y + 155, 12, SKIN)
        limb_seg(d, cx + 48, shoulder_y + 110, cx + 52, shoulder_y + 155, 12, SKIN)
        joint(d, cx - 28, shoulder_y + 14, 7)
        joint(d, cx + 28, shoulder_y + 14, 7)
        d.rectangle([cx - 11, neck_y, cx + 11, shoulder_y + 10], fill=SKIN)
        joint(d, cx, neck_y + 5, 6)
        head_front(d, cx, hy, expr)

    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, 200  # aligns under front head
    if kind == "closed":
        d.arc([cx - 14, my - 2, cx + 14, my + 12], 20, 160, fill=BLACK, width=3)
    elif kind == "open":
        oval(d, [cx - 12, my, cx + 12, my + 16], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 8, my + 2, cx + 8, my + 6], TEETH)
    elif kind == "smile":
        d.arc([cx - 16, my - 4, cx + 16, my + 14], 15, 165, fill=BLACK, width=3)
    else:
        oval(d, [cx - 14, my, cx + 14, my + 20], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 10, my + 2, cx + 10, my + 6], TEETH)
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
        im = draw_pose(mode, expr)
        im.save(out / name, "PNG")
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
