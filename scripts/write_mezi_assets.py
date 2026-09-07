#!/usr/bin/env python3
"""Mike — polished flat-cartoon style (Archie-like proportions), yellow hoodie."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 520, 780
# Mike palette
HOODIE = (255, 196, 40, 255)
HOODIE_L = (255, 225, 120, 255)
HOODIE_D = (230, 165, 25, 255)
SKIN = (232, 185, 145, 255)
SKIN_D = (205, 155, 115, 255)
HAIR = (28, 24, 30, 255)
PANTS = (42, 48, 62, 255)
SHOE = (24, 24, 28, 255)
WHITE = (255, 255, 255, 255)
BLACK = (18, 16, 20, 255)
MOUTH_IN = (140, 55, 65, 255)
TEETH = (250, 248, 245, 255)
CHEEK = (245, 165, 145, 100)

CX = W // 2
# Proportions closer to polished cartoon (taller legs, larger head, clear joints)
HEAD_Y = 130
NECK_Y = 185
SHOULDER = 210
HIP = 400
KNEE = 520
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


def nice_hand(d, x, y, open_palm=False):
    """Round palm + simple fingers (not stubs)."""
    oval(d, [x - 16, y - 12, x + 16, y + 16], SKIN)
    if open_palm:
        for i, dx in enumerate([-12, -4, 4, 12]):
            oval(d, [x + dx - 5, y - 22, x + dx + 5, y - 6], SKIN)
    else:
        for dx in (-10, -2, 6):
            oval(d, [x + dx - 4, y + 10, x + dx + 4, y + 22], SKIN)


def nice_foot(d, x, y, facing=0):
    if facing <= 0:
        oval(d, [x - 30, y - 8, x + 12, y + 18], SHOE)
        oval(d, [x - 28, y + 6, x + 4, y + 16], (15, 15, 18, 255))
    if facing >= 0:
        oval(d, [x - 12, y - 8, x + 30, y + 18], SHOE)
        oval(d, [x - 4, y + 6, x + 28, y + 16], (15, 15, 18, 255))


def head_front(d, cx, hy, expr="neutral"):
    # larger round head
    oval(d, [cx - 62, hy - 68, cx + 62, hy + 58], SKIN)
    # hair cap + tuft
    oval(d, [cx - 64, hy - 78, cx + 64, hy - 8], HAIR)
    d.polygon(
        [(cx - 18, hy - 55), (cx - 2, hy - 98), (cx + 14, hy - 52),
         (cx + 30, hy - 92), (cx + 46, hy - 48)],
        fill=HAIR,
    )
    # ears
    oval(d, [cx - 72, hy - 6, cx - 54, hy + 26], SKIN)
    oval(d, [cx + 54, hy - 6, cx + 72, hy + 26], SKIN)
    oval(d, [cx - 52, hy + 18, cx - 30, hy + 36], CHEEK)
    oval(d, [cx + 30, hy + 18, cx + 52, hy + 36], CHEEK)

    ey = hy - 4
    if expr == "blink":
        d.line([(cx - 34, ey), (cx - 12, ey)], fill=BLACK, width=5)
        d.line([(cx + 12, ey), (cx + 34, ey)], fill=BLACK, width=5)
    elif expr in ("happy", "welcoming", "giggle"):
        d.arc([cx - 36, ey - 2, cx - 10, ey + 16], 200, 340, fill=BLACK, width=4)
        d.arc([cx + 10, ey - 2, cx + 36, ey + 16], 200, 340, fill=BLACK, width=4)
    else:
        # big cartoon eyes
        oval(d, [cx - 38, ey - 18, cx - 8, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx + 8, ey - 18, cx + 38, ey + 16], WHITE, BLACK, 3)
        oval(d, [cx - 28, ey - 8, cx - 14, ey + 6], BLACK)
        oval(d, [cx + 14, ey - 8, cx + 28, ey + 6], BLACK)
        oval(d, [cx - 24, ey - 10, cx - 18, ey - 4], WHITE)
        oval(d, [cx + 18, ey - 10, cx + 24, ey - 4], WHITE)

    if expr == "confused":
        d.line([(cx - 36, ey - 26), (cx - 12, ey - 18)], fill=BLACK, width=4)
        d.line([(cx + 12, ey - 20), (cx + 36, ey - 28)], fill=BLACK, width=4)
    elif expr == "question":
        d.line([(cx - 36, ey - 28), (cx - 12, ey - 22)], fill=BLACK, width=4)
        d.line([(cx + 12, ey - 22), (cx + 36, ey - 28)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 38, ey - 32, cx - 10, ey - 14], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 10, ey - 32, cx + 38, ey - 14], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 36, ey - 24), (cx - 12, ey - 24)], fill=BLACK, width=3)
        d.line([(cx + 12, ey - 24), (cx + 36, ey - 24)], fill=BLACK, width=3)

    # small nose
    oval(d, [cx - 7, hy + 12, cx + 7, hy + 28], SKIN_D)


def head_side(d, cx, hy, facing="left"):
    """Clean profile — one eye, ear, nose, closed mouth baked in."""
    sign = -1 if facing == "left" else 1
    oval(d, [cx - 48, hy - 62, cx + 48, hy + 52], SKIN)
    oval(d, [cx - 50, hy - 74, cx + 36, hy - 4], HAIR)
    d.polygon(
        [(cx - 6, hy - 50), (cx + sign * 14, hy - 95), (cx + 22, hy - 42)],
        fill=HAIR,
    )
    # ear toward back
    ex = cx - sign * 40
    oval(d, [ex - 12, hy - 2, ex + 12, hy + 28], SKIN, BLACK, 2)
    oval(d, [ex - 5, hy + 6, ex + 5, hy + 18], SKIN_D)
    # eye
    eye_x = cx + sign * 16
    oval(d, [eye_x - 14, hy - 14, eye_x + 14, hy + 12], WHITE, BLACK, 2)
    oval(d, [eye_x - 4, hy - 4, eye_x + 6, hy + 6], BLACK)
    # nose
    nx = cx + sign * 46
    oval(d, [nx - 7, hy + 6, nx + 7, hy + 24], SKIN_D)
    # closed smile line (no separate mouth layer on side)
    mx = cx + sign * 20
    d.arc([mx - 12, hy + 26, mx + 12, hy + 40], 15, 165, fill=BLACK, width=3)


def torso_front(d, cx, sy):
    d.rounded_rectangle([cx - 68, sy, cx + 68, sy + 175], 32, fill=HOODIE)
    d.rounded_rectangle([cx - 44, sy + 40, cx + 44, sy + 150], 22, fill=HOODIE_L)
    d.arc([cx - 55, sy - 6, cx + 55, sy + 45], 200, 340, fill=HOODIE_D, width=7)


def torso_side(d, cx, sy):
    d.rounded_rectangle([cx - 42, sy, cx + 42, sy + 170], 26, fill=HOODIE)
    d.rounded_rectangle([cx - 24, sy + 35, cx + 24, sy + 145], 16, fill=HOODIE_L)


def draw_walk(facing: str, phase: int) -> Image.Image:
    """Human-ish side walk: clear stride, opposite arm swing, profile head."""
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    left = facing == "left"
    s = -1 if left else 1

    oval(d, [cx - 60, FOOT + 2, cx + 60, FOOT + 26], (0, 0, 0, 40))

    if phase == 0:
        # front leg (direction of travel)
        limb(d, cx + s * 6, HIP, cx + s * 42, KNEE - 10, 34, PANTS)
        limb(d, cx + s * 42, KNEE - 10, cx + s * 58, FOOT - 12, 30, PANTS)
        nice_foot(d, cx + s * 58, FOOT - 6, -1 if left else 1)
        # back leg
        limb(d, cx - s * 6, HIP, cx - s * 28, KNEE + 12, 34, PANTS)
        limb(d, cx - s * 28, KNEE + 12, cx - s * 18, FOOT, 30, PANTS)
        nice_foot(d, cx - s * 18, FOOT + 2, -1 if left else 1)
        # arms opposite
        limb(d, cx - s * 32, SHOULDER + 32, cx - s * 58, SHOULDER + 110, 28, HOODIE)
        nice_hand(d, cx - s * 62, SHOULDER + 122)
        limb(d, cx + s * 32, SHOULDER + 32, cx + s * 68, SHOULDER + 8, 28, HOODIE)
        nice_hand(d, cx + s * 76, SHOULDER + 2, open_palm=True)
    else:
        limb(d, cx - s * 6, HIP, cx - s * 42, KNEE - 10, 34, PANTS)
        limb(d, cx - s * 42, KNEE - 10, cx - s * 58, FOOT - 12, 30, PANTS)
        nice_foot(d, cx - s * 58, FOOT - 6, -1 if left else 1)
        limb(d, cx + s * 6, HIP, cx + s * 28, KNEE + 12, 34, PANTS)
        limb(d, cx + s * 28, KNEE + 12, cx + s * 18, FOOT, 30, PANTS)
        nice_foot(d, cx + s * 18, FOOT + 2, -1 if left else 1)
        limb(d, cx + s * 32, SHOULDER + 32, cx + s * 58, SHOULDER + 110, 28, HOODIE)
        nice_hand(d, cx + s * 62, SHOULDER + 122)
        limb(d, cx - s * 32, SHOULDER + 32, cx - s * 68, SHOULDER + 8, 28, HOODIE)
        nice_hand(d, cx - s * 76, SHOULDER + 2, open_palm=True)

    torso_side(d, cx, SHOULDER)
    d.rounded_rectangle([cx - 14, NECK_Y, cx + 14, SHOULDER + 14], 10, fill=SKIN)
    head_side(d, cx, HEAD_Y, facing)
    return img


def draw_pose(mode: str = "stand", expr: str = "neutral") -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX
    oval(d, [cx - 75, FOOT + 2, cx + 75, FOOT + 28], (0, 0, 0, 40))

    if mode == "point":
        limb(d, cx - 22, HIP, cx - 22, KNEE, 32, PANTS)
        limb(d, cx - 22, KNEE, cx - 22, FOOT, 28, PANTS)
        limb(d, cx + 22, HIP, cx + 22, KNEE, 32, PANTS)
        limb(d, cx + 22, KNEE, cx + 22, FOOT, 28, PANTS)
        nice_foot(d, cx - 22, FOOT, -1)
        nice_foot(d, cx + 22, FOOT, 1)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 55, SHOULDER + 40, cx - 75, SHOULDER + 130, 28, HOODIE)
        nice_hand(d, cx - 78, SHOULDER + 142)
        # point arm up-right
        limb(d, cx + 55, SHOULDER + 35, cx + 125, SHOULDER - 40, 30, HOODIE)
        nice_hand(d, cx + 132, SHOULDER - 52, open_palm=True)
        # finger tip
        limb(d, cx + 132, SHOULDER - 52, cx + 165, SHOULDER - 72, 9, SKIN)
        d.rounded_rectangle([cx - 14, NECK_Y, cx + 14, SHOULDER + 14], 10, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    elif mode == "present":
        limb(d, cx - 22, HIP, cx - 22, KNEE, 32, PANTS)
        limb(d, cx - 22, KNEE, cx - 22, FOOT, 28, PANTS)
        limb(d, cx + 22, HIP, cx + 22, KNEE, 32, PANTS)
        limb(d, cx + 22, KNEE, cx + 22, FOOT, 28, PANTS)
        nice_foot(d, cx - 22, FOOT, -1)
        nice_foot(d, cx + 22, FOOT, 1)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 58, SHOULDER + 40, cx - 125, SHOULDER + 55, 30, HOODIE)
        nice_hand(d, cx - 136, SHOULDER + 50, open_palm=True)
        limb(d, cx + 58, SHOULDER + 40, cx + 125, SHOULDER + 55, 30, HOODIE)
        nice_hand(d, cx + 136, SHOULDER + 50, open_palm=True)
        d.rounded_rectangle([cx - 14, NECK_Y, cx + 14, SHOULDER + 14], 10, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr if expr != "neutral" else "welcoming")

    elif mode == "sit":
        sit_hip, sit_knee, sit_foot = 460, 500, 600
        limb(d, cx - 24, sit_hip, cx - 80, sit_knee, 34, PANTS)
        limb(d, cx + 24, sit_hip, cx + 80, sit_knee, 34, PANTS)
        limb(d, cx - 80, sit_knee, cx - 85, sit_foot, 30, PANTS)
        limb(d, cx + 80, sit_knee, cx + 85, sit_foot, 30, PANTS)
        nice_foot(d, cx - 85, sit_foot, -1)
        nice_foot(d, cx + 85, sit_foot, 1)
        torso_front(d, cx, SHOULDER + 55)
        limb(d, cx - 55, SHOULDER + 95, cx - 60, SHOULDER + 175, 28, HOODIE)
        nice_hand(d, cx - 60, SHOULDER + 188)
        limb(d, cx + 55, SHOULDER + 95, cx + 60, SHOULDER + 175, 28, HOODIE)
        nice_hand(d, cx + 60, SHOULDER + 188)
        d.rounded_rectangle([cx - 14, NECK_Y + 50, cx + 14, SHOULDER + 68], 10, fill=SKIN)
        head_front(d, cx, HEAD_Y + 45, expr)

    else:
        limb(d, cx - 22, HIP, cx - 22, KNEE, 32, PANTS)
        limb(d, cx - 22, KNEE, cx - 22, FOOT, 28, PANTS)
        limb(d, cx + 22, HIP, cx + 22, KNEE, 32, PANTS)
        limb(d, cx + 22, KNEE, cx + 22, FOOT, 28, PANTS)
        nice_foot(d, cx - 22, FOOT, -1)
        nice_foot(d, cx + 22, FOOT, 1)
        torso_front(d, cx, SHOULDER)
        limb(d, cx - 55, SHOULDER + 40, cx - 70, SHOULDER + 140, 28, HOODIE)
        nice_hand(d, cx - 72, SHOULDER + 152)
        limb(d, cx + 55, SHOULDER + 40, cx + 70, SHOULDER + 140, 28, HOODIE)
        nice_hand(d, cx + 72, SHOULDER + 152)
        d.rounded_rectangle([cx - 14, NECK_Y, cx + 14, SHOULDER + 14], 10, fill=SKIN)
        head_front(d, cx, HEAD_Y, expr)

    return img


def draw_mouth(kind: str) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx, my = CX, HEAD_Y + 38
    if kind == "closed":
        d.arc([cx - 18, my - 2, cx + 18, my + 16], 20, 160, fill=BLACK, width=4)
    elif kind == "open":
        oval(d, [cx - 16, my, cx + 16, my + 22], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 12, my + 2, cx + 12, my + 9], TEETH)
    elif kind == "smile":
        d.arc([cx - 20, my - 4, cx + 20, my + 18], 15, 165, fill=BLACK, width=5)
    else:
        oval(d, [cx - 18, my, cx + 18, my + 26], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 13, my + 2, cx + 13, my + 9], TEETH)
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
    print("walk frames ok")


if __name__ == "__main__":
    main()
