#!/usr/bin/env python3
"""Mike — solid full-body cartoon (one coherent figure, not floating parts)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 560, 900

HOODIE = (255, 200, 45, 255)
HOODIE_L = (255, 228, 120, 255)
HOODIE_D = (230, 170, 30, 255)
SKIN = (238, 195, 155, 255)
SKIN_D = (215, 165, 125, 255)
HAIR = (28, 24, 30, 255)
PANTS = (38, 46, 62, 255)
SHOE = (255, 215, 70, 255)
SHOE_W = (250, 250, 252, 255)
WHITE = (255, 255, 255, 255)
BLACK = (18, 16, 20, 255)
MOUTH_IN = (155, 55, 65, 255)
TEETH = (252, 250, 248, 255)
GLASS = (35, 38, 48, 230)

CX = W // 2


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def limb_capsule(d, x0, y0, x1, y1, width, color):
    d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    r = max(width // 2 - 1, 6)
    oval(d, [x0 - r, y0 - r, x0 + r, y0 + r], color)
    oval(d, [x1 - r, y1 - r, x1 + r, y1 + r], color)


def draw_head(d, cx, hy, expr="neutral"):
    # hair back
    oval(d, [cx - 78, hy - 95, cx + 78, hy + 10], HAIR)
    # face
    oval(d, [cx - 70, hy - 78, cx + 70, hy + 72], SKIN)
    # hair top / spikes
    oval(d, [cx - 75, hy - 105, cx + 75, hy - 5], HAIR)
    d.polygon(
        [
            (cx - 25, hy - 70),
            (cx - 8, hy - 125),
            (cx + 12, hy - 68),
            (cx + 32, hy - 118),
            (cx + 55, hy - 65),
        ],
        fill=HAIR,
    )
    # ears
    oval(d, [cx - 82, hy - 8, cx - 62, hy + 28], SKIN)
    oval(d, [cx + 62, hy - 8, cx + 82, hy + 28], SKIN)

    ey = hy - 8
    if expr == "blink":
        d.line([(cx - 42, ey), (cx - 14, ey)], fill=BLACK, width=5)
        d.line([(cx + 14, ey), (cx + 42, ey)], fill=BLACK, width=5)
    else:
        oval(d, [cx - 48, ey - 22, cx - 12, ey + 22], WHITE, BLACK, 3)
        oval(d, [cx + 12, ey - 22, cx + 48, ey + 22], WHITE, BLACK, 3)
        oval(d, [cx - 36, ey - 8, cx - 18, ey + 10], BLACK)
        oval(d, [cx + 18, ey - 8, cx + 36, ey + 10], BLACK)
        oval(d, [cx - 30, ey - 10, cx - 22, ey - 2], WHITE)
        oval(d, [cx + 24, ey - 10, cx + 32, ey - 2], WHITE)

    # brows
    if expr == "question":
        d.line([(cx - 45, ey - 32), (cx - 15, ey - 26)], fill=BLACK, width=4)
        d.line([(cx + 15, ey - 28), (cx + 45, ey - 34)], fill=BLACK, width=4)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 48, ey - 38, cx - 12, ey - 14], 200, 340, fill=BLACK, width=3)
        d.arc([cx + 12, ey - 38, cx + 48, ey - 14], 200, 340, fill=BLACK, width=3)
    else:
        d.line([(cx - 45, ey - 30), (cx - 15, ey - 30)], fill=BLACK, width=3)
        d.line([(cx + 15, ey - 30), (cx + 45, ey - 30)], fill=BLACK, width=3)

    # nose
    oval(d, [cx - 8, hy + 12, cx + 8, hy + 32], SKIN_D)
    # glasses
    d.ellipse([cx - 50, ey - 24, cx - 10, ey + 24], outline=GLASS, width=4)
    d.ellipse([cx + 10, ey - 24, cx + 50, ey + 24], outline=GLASS, width=4)
    d.line([(cx - 10, ey), (cx + 10, ey)], fill=GLASS, width=4)


def draw_mouth_on(d, cx, hy, kind="closed"):
    my = hy + 42
    if kind == "closed":
        d.arc([cx - 20, my - 2, cx + 20, my + 18], 20, 160, fill=BLACK, width=3)
    elif kind == "smile":
        d.arc([cx - 24, my - 4, cx + 24, my + 20], 15, 165, fill=BLACK, width=4)
    elif kind == "open":
        oval(d, [cx - 18, my, cx + 18, my + 26], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 12, my + 2, cx + 12, my + 10], TEETH)
    else:
        oval(d, [cx - 22, my, cx + 22, my + 32], MOUTH_IN, BLACK, 2)
        oval(d, [cx - 14, my + 2, cx + 14, my + 10], TEETH)


def draw_body_stand(d, cx, shoulder_y):
    # continuous torso — rounded hoodie
    d.rounded_rectangle([cx - 95, shoulder_y, cx + 95, shoulder_y + 230], 45, fill=HOODIE)
    d.rounded_rectangle([cx - 55, shoulder_y + 55, cx + 55, shoulder_y + 190], 30, fill=HOODIE_L)
    # hood rim
    d.arc([cx - 70, shoulder_y - 15, cx + 70, shoulder_y + 55], 200, 340, fill=HOODIE_D, width=8)
    # drawstrings
    d.line([(cx - 22, shoulder_y + 40), (cx - 22, shoulder_y + 110)], fill=WHITE, width=5)
    d.line([(cx + 22, shoulder_y + 40), (cx + 22, shoulder_y + 110)], fill=WHITE, width=5)
    oval(d, [cx - 28, shoulder_y + 105, cx - 16, shoulder_y + 120], WHITE)
    oval(d, [cx + 16, shoulder_y + 105, cx + 28, shoulder_y + 120], WHITE)


def draw_legs_stand(d, cx, hip_y):
    # pants as solid connected shape — no gaps
    # hips band
    d.rounded_rectangle([cx - 70, hip_y, cx + 70, hip_y + 40], 18, fill=PANTS)
    # left leg continuous
    d.rounded_rectangle([cx - 68, hip_y + 20, cx - 12, hip_y + 200], 22, fill=PANTS)
    # right leg continuous
    d.rounded_rectangle([cx + 12, hip_y + 20, cx + 68, hip_y + 200], 22, fill=PANTS)
    # shoes
    d.rounded_rectangle([cx - 78, hip_y + 185, cx - 5, hip_y + 230], 16, fill=SHOE)
    d.rounded_rectangle([cx - 78, hip_y + 210, cx - 5, hip_y + 232], 10, fill=SHOE_W)
    d.rounded_rectangle([cx + 5, hip_y + 185, cx + 78, hip_y + 230], 16, fill=SHOE)
    d.rounded_rectangle([cx + 5, hip_y + 210, cx + 78, hip_y + 232], 10, fill=SHOE_W)


def draw_arms_down(d, cx, shoulder_y):
    # left arm along body
    limb_capsule(d, cx - 90, shoulder_y + 40, cx - 100, shoulder_y + 130, 36, HOODIE)
    limb_capsule(d, cx - 100, shoulder_y + 130, cx - 95, shoulder_y + 200, 32, HOODIE)
    oval(d, [cx - 112, shoulder_y + 195, cx - 78, shoulder_y + 235], SKIN)  # hand
    # fingers
    for dx in (-8, 0, 8):
        oval(d, [cx - 98 + dx, shoulder_y + 228, cx - 88 + dx, shoulder_y + 248], SKIN)
    # right arm
    limb_capsule(d, cx + 90, shoulder_y + 40, cx + 100, shoulder_y + 130, 36, HOODIE)
    limb_capsule(d, cx + 100, shoulder_y + 130, cx + 95, shoulder_y + 200, 32, HOODIE)
    oval(d, [cx + 78, shoulder_y + 195, cx + 112, shoulder_y + 235], SKIN)
    for dx in (-8, 0, 8):
        oval(d, [cx + 88 + dx, shoulder_y + 228, cx + 98 + dx, shoulder_y + 248], SKIN)


def draw_arms_present(d, cx, shoulder_y):
    limb_capsule(d, cx - 90, shoulder_y + 45, cx - 150, shoulder_y + 70, 36, HOODIE)
    limb_capsule(d, cx - 150, shoulder_y + 70, cx - 175, shoulder_y + 90, 30, HOODIE)
    oval(d, [cx - 195, shoulder_y + 75, cx - 160, shoulder_y + 115], SKIN)
    limb_capsule(d, cx + 90, shoulder_y + 45, cx + 150, shoulder_y + 70, 36, HOODIE)
    limb_capsule(d, cx + 150, shoulder_y + 70, cx + 175, shoulder_y + 90, 30, HOODIE)
    oval(d, [cx + 160, shoulder_y + 75, cx + 195, shoulder_y + 115], SKIN)


def draw_arms_point(d, cx, shoulder_y):
    limb_capsule(d, cx - 90, shoulder_y + 45, cx - 105, shoulder_y + 150, 34, HOODIE)
    oval(d, [cx - 120, shoulder_y + 160, cx - 88, shoulder_y + 200], SKIN)
    limb_capsule(d, cx + 90, shoulder_y + 40, cx + 150, shoulder_y - 20, 36, HOODIE)
    limb_capsule(d, cx + 150, shoulder_y - 20, cx + 185, shoulder_y - 45, 28, HOODIE)
    oval(d, [cx + 175, shoulder_y - 65, cx + 210, shoulder_y - 25], SKIN)
    # pointing finger
    d.line([(cx + 195, shoulder_y - 50), (cx + 230, shoulder_y - 70)], fill=SKIN, width=10)


def draw_pose(mode="stand", expr="neutral", mouth=None) -> Image.Image:
    img = blank()
    d = ImageDraw.Draw(img)
    cx = CX

    # soft shadow under feet
    oval(d, [cx - 90, 820, cx + 90, 860], (0, 0, 0, 50))

    head_y = 130
    shoulder_y = 210
    hip_y = 420

    if mode == "sit":
        hip_y = 500
        shoulder_y = 280
        head_y = 180
        # chair seat
        d.rounded_rectangle([cx - 110, hip_y + 30, cx + 110, hip_y + 55], 8, fill=(55, 60, 75))
        # legs bent
        d.rounded_rectangle([cx - 100, hip_y + 20, cx - 20, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx + 20, hip_y + 20, cx + 100, hip_y + 55], 16, fill=PANTS)
        d.rounded_rectangle([cx - 105, hip_y + 45, cx - 55, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx + 55, hip_y + 45, cx + 105, hip_y + 160], 18, fill=PANTS)
        d.rounded_rectangle([cx - 120, hip_y + 145, cx - 40, hip_y + 185], 14, fill=SHOE)
        d.rounded_rectangle([cx + 40, hip_y + 145, cx + 120, hip_y + 185], 14, fill=SHOE)
        draw_body_stand(d, cx, shoulder_y)
        draw_arms_down(d, cx, shoulder_y)
        # neck
        d.rounded_rectangle([cx - 18, head_y + 55, cx + 18, shoulder_y + 15], 10, fill=SKIN)
        draw_head(d, cx, head_y, expr)
        if mouth:
            draw_mouth_on(d, cx, head_y, mouth)
        return img

    if mode in ("walk0", "walk1"):
        # side-ish walk with solid legs
        phase = 0 if mode == "walk0" else 1
        if phase == 0:
            # left leg forward
            limb_capsule(d, cx - 15, hip_y, cx - 50, hip_y + 100, 40, PANTS)
            limb_capsule(d, cx - 50, hip_y + 100, cx - 70, hip_y + 200, 36, PANTS)
            d.rounded_rectangle([cx - 95, hip_y + 185, cx - 40, hip_y + 230], 14, fill=SHOE)
            limb_capsule(d, cx + 15, hip_y, cx + 40, hip_y + 110, 40, PANTS)
            limb_capsule(d, cx + 40, hip_y + 110, cx + 30, hip_y + 210, 36, PANTS)
            d.rounded_rectangle([cx + 5, hip_y + 195, cx + 60, hip_y + 238], 14, fill=SHOE)
            limb_capsule(d, cx - 85, shoulder_y + 40, cx - 120, shoulder_y + 20, 34, HOODIE)
            oval(d, [cx - 140, shoulder_y + 5, cx - 105, shoulder_y + 45], SKIN)
            limb_capsule(d, cx + 85, shoulder_y + 40, cx + 100, shoulder_y + 140, 34, HOODIE)
            oval(d, [cx + 88, shoulder_y + 150, cx + 122, shoulder_y + 190], SKIN)
        else:
            limb_capsule(d, cx + 15, hip_y, cx + 50, hip_y + 100, 40, PANTS)
            limb_capsule(d, cx + 50, hip_y + 100, cx + 70, hip_y + 200, 36, PANTS)
            d.rounded_rectangle([cx + 40, hip_y + 185, cx + 95, hip_y + 230], 14, fill=SHOE)
            limb_capsule(d, cx - 15, hip_y, cx - 40, hip_y + 110, 40, PANTS)
            limb_capsule(d, cx - 40, hip_y + 110, cx - 30, hip_y + 210, 36, PANTS)
            d.rounded_rectangle([cx - 60, hip_y + 195, cx - 5, hip_y + 238], 14, fill=SHOE)
            limb_capsule(d, cx + 85, shoulder_y + 40, cx + 120, shoulder_y + 20, 34, HOODIE)
            oval(d, [cx + 105, shoulder_y + 5, cx + 140, shoulder_y + 45], SKIN)
            limb_capsule(d, cx - 85, shoulder_y + 40, cx - 100, shoulder_y + 140, 34, HOODIE)
            oval(d, [cx - 122, shoulder_y + 150, cx - 88, shoulder_y + 190], SKIN)

        d.rounded_rectangle([cx - 55, hip_y - 10, cx + 55, hip_y + 35], 16, fill=PANTS)
        # torso slightly narrower side
        d.rounded_rectangle([cx - 70, shoulder_y, cx + 70, shoulder_y + 210], 38, fill=HOODIE)
        d.rounded_rectangle([cx - 40, shoulder_y + 50, cx + 40, shoulder_y + 175], 24, fill=HOODIE_L)
        d.rounded_rectangle([cx - 16, head_y + 55, cx + 16, shoulder_y + 12], 10, fill=SKIN)
        draw_head(d, cx, head_y, expr)
        if mouth:
            draw_mouth_on(d, cx, head_y, mouth)
        return img

    # default stand / point / present
    draw_legs_stand(d, cx, hip_y)
    draw_body_stand(d, cx, shoulder_y)
    if mode == "point":
        draw_arms_point(d, cx, shoulder_y)
    elif mode == "present":
        draw_arms_present(d, cx, shoulder_y)
    else:
        draw_arms_down(d, cx, shoulder_y)

    d.rounded_rectangle([cx - 18, head_y + 55, cx + 18, shoulder_y + 12], 10, fill=SKIN)
    draw_head(d, cx, head_y, expr)
    if mouth:
        draw_mouth_on(d, cx, head_y, mouth)
    return img


def mouth_overlay(kind: str) -> Image.Image:
    """Transparent canvas with only mouth at head position for lip-sync."""
    img = blank()
    d = ImageDraw.Draw(img)
    draw_mouth_on(d, CX, 130, kind)
    return img


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)

    # Front poses WITHOUT mouth (lip-sync overlays)
    draw_pose("stand", "neutral").save(out / "body.png")
    draw_pose("stand", "happy").save(out / "body_happy.png")
    draw_pose("stand", "question").save(out / "body_question.png")
    draw_pose("stand", "blink").save(out / "body_blink.png")
    draw_pose("present", "welcoming").save(out / "body_present.png")
    draw_pose("point", "neutral").save(out / "arm_point.png")
    draw_pose("sit", "neutral").save(out / "body_sit.png")

    # Walk cycle
    draw_pose("walk0", "neutral", mouth="closed").save(out / "walk_l0.png")
    draw_pose("walk1", "neutral", mouth="closed").save(out / "walk_l1.png")
    draw_pose("walk0", "neutral", mouth="closed").save(out / "walk_r0.png")
    draw_pose("walk1", "neutral", mouth="closed").save(out / "walk_r1.png")
    draw_pose("walk0", "neutral", mouth="closed").save(out / "body_side_left.png")
    draw_pose("walk1", "neutral", mouth="closed").save(out / "body_side_right.png")

    for kind, fname in [
        ("closed", "mouth_closed.png"),
        ("open", "mouth_open.png"),
        ("wide", "mouth_wide.png"),
        ("smile", "mouth_smile.png"),
    ]:
        mouth_overlay(kind).save(out / fname)
        print("mouth", fname)

    print("OK solid full-body Mike")


if __name__ == "__main__":
    main()
