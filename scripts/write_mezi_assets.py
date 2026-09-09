#!/usr/bin/env python3
"""Mike parts — body WITHOUT baked mouth (lips from overlay). Real walk phases."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 2

HOODIE = (255, 196, 40, 255)
HOODIE_L = (255, 230, 130, 255)
HOODIE_D = (235, 170, 25, 255)
SKIN = (235, 190, 150, 255)
SKIN_D = (210, 160, 120, 255)
HAIR = (30, 26, 32, 255)
PANTS = (40, 48, 65, 255)
SHOE = (255, 220, 80, 255)
SHOE_W = (250, 250, 252, 255)
WHITE = (255, 255, 255, 255)
BLACK = (20, 18, 22, 255)
MOUTH_IN = (150, 60, 70, 255)
TEETH = (252, 250, 248, 255)
GLASS = (40, 42, 50, 220)


def blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def oval(d, xy, fill, outline=None, width=2):
    d.ellipse(xy, fill=fill, outline=outline, width=width if outline else 0)


def soft(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.SMOOTH)


def part_head() -> Image.Image:
    w, h = 220 * S, 260 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.55)
    oval(d, [cx - 95 * S, cy - 110 * S, cx + 95 * S, cy + 20 * S], HAIR)
    oval(d, [cx - 88 * S, cy - 90 * S, cx + 88 * S, cy + 95 * S], SKIN)
    oval(d, [cx - 92 * S, cy - 120 * S, cx + 92 * S, cy - 10 * S], HAIR)
    d.polygon(
        [
            (cx - 30 * S, cy - 80 * S),
            (cx - 5 * S, cy - 145 * S),
            (cx + 25 * S, cy - 75 * S),
            (cx + 50 * S, cy - 135 * S),
            (cx + 75 * S, cy - 70 * S),
        ],
        fill=HAIR,
    )
    oval(d, [cx - 100 * S, cy - 10 * S, cx - 75 * S, cy + 35 * S], SKIN)
    oval(d, [cx + 75 * S, cy - 10 * S, cx + 100 * S, cy + 35 * S], SKIN)
    return soft(img)


def part_face(expr: str = "neutral") -> Image.Image:
    w, h = 220 * S, 260 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.55)
    if expr == "blink":
        d.line([(cx - 50 * S, cy - 5 * S), (cx - 20 * S, cy - 5 * S)], fill=BLACK, width=4 * S)
        d.line([(cx + 20 * S, cy - 5 * S), (cx + 50 * S, cy - 5 * S)], fill=BLACK, width=4 * S)
    else:
        oval(d, [cx - 55 * S, cy - 25 * S, cx - 15 * S, cy + 25 * S], WHITE, BLACK, 3 * S)
        oval(d, [cx + 15 * S, cy - 25 * S, cx + 55 * S, cy + 25 * S], WHITE, BLACK, 3 * S)
        oval(d, [cx - 42 * S, cy - 10 * S, cx - 22 * S, cy + 12 * S], BLACK)
        oval(d, [cx + 22 * S, cy - 10 * S, cx + 42 * S, cy + 12 * S], BLACK)
        oval(d, [cx - 36 * S, cy - 12 * S, cx - 28 * S, cy - 4 * S], WHITE)
        oval(d, [cx + 28 * S, cy - 12 * S, cx + 36 * S, cy - 4 * S], WHITE)
    if expr == "question":
        d.arc([cx - 55 * S, cy - 45 * S, cx - 15 * S, cy - 20 * S], 200, 340, fill=BLACK, width=3 * S)
        d.arc([cx + 15 * S, cy - 48 * S, cx + 55 * S, cy - 22 * S], 200, 340, fill=BLACK, width=3 * S)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 55 * S, cy - 42 * S, cx - 15 * S, cy - 18 * S], 200, 340, fill=BLACK, width=3 * S)
        d.arc([cx + 15 * S, cy - 42 * S, cx + 55 * S, cy - 18 * S], 200, 340, fill=BLACK, width=3 * S)
    else:
        d.line([(cx - 52 * S, cy - 32 * S), (cx - 18 * S, cy - 32 * S)], fill=BLACK, width=3 * S)
        d.line([(cx + 18 * S, cy - 32 * S), (cx + 52 * S, cy - 32 * S)], fill=BLACK, width=3 * S)
    oval(d, [cx - 10 * S, cy + 15 * S, cx + 10 * S, cy + 38 * S], SKIN_D)
    d.ellipse([cx - 58 * S, cy - 28 * S, cx - 12 * S, cy + 28 * S], outline=GLASS, width=3 * S)
    d.ellipse([cx + 12 * S, cy - 28 * S, cx + 58 * S, cy + 28 * S], outline=GLASS, width=3 * S)
    d.line([(cx - 12 * S, cy), (cx + 12 * S, cy)], fill=GLASS, width=3 * S)
    return soft(img)


def part_mouth(kind: str) -> Image.Image:
    w, h = 220 * S, 260 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.55) + 48 * S
    if kind == "closed":
        d.arc([cx - 22 * S, cy - 4 * S, cx + 22 * S, cy + 20 * S], 20, 160, fill=BLACK, width=3 * S)
    elif kind == "smile":
        d.arc([cx - 26 * S, cy - 6 * S, cx + 26 * S, cy + 22 * S], 15, 165, fill=BLACK, width=4 * S)
    elif kind == "open":
        oval(d, [cx - 20 * S, cy, cx + 20 * S, cy + 28 * S], MOUTH_IN, BLACK, 2 * S)
        oval(d, [cx - 14 * S, cy + 3 * S, cx + 14 * S, cy + 12 * S], TEETH)
    else:
        oval(d, [cx - 24 * S, cy, cx + 24 * S, cy + 34 * S], MOUTH_IN, BLACK, 2 * S)
        oval(d, [cx - 16 * S, cy + 3 * S, cx + 16 * S, cy + 12 * S], TEETH)
    return soft(img)


def part_neck() -> Image.Image:
    w, h = 80 * S, 50 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10 * S, 0, 70 * S, 48 * S], 12 * S, fill=SKIN)
    return soft(img)


def part_torso() -> Image.Image:
    w, h = 280 * S, 320 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx = w // 2
    d.rounded_rectangle([30 * S, 20 * S, 250 * S, 300 * S], 40 * S, fill=HOODIE)
    d.rounded_rectangle([70 * S, 140 * S, 210 * S, 260 * S], 28 * S, fill=HOODIE_L)
    d.arc([50 * S, 5 * S, 230 * S, 100 * S], 200, 340, fill=HOODIE_D, width=8 * S)
    d.line([(cx - 25 * S, 55 * S), (cx - 25 * S, 130 * S)], fill=WHITE, width=5 * S)
    d.line([(cx + 25 * S, 55 * S), (cx + 25 * S, 130 * S)], fill=WHITE, width=5 * S)
    oval(d, [cx - 30 * S, 125 * S, cx - 20 * S, 140 * S], WHITE)
    oval(d, [cx + 20 * S, 125 * S, cx + 30 * S, 140 * S], WHITE)
    return soft(img)


def part_upper_arm() -> Image.Image:
    w, h = 70 * S, 140 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([12 * S, 5 * S, 58 * S, 130 * S], 22 * S, fill=HOODIE)
    return soft(img)


def part_forearm() -> Image.Image:
    w, h = 60 * S, 120 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10 * S, 5 * S, 50 * S, 110 * S], 18 * S, fill=HOODIE)
    return soft(img)


def part_hand() -> Image.Image:
    w, h = 70 * S, 80 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    oval(d, [12 * S, 20 * S, 58 * S, 70 * S], SKIN)
    for x in (14, 26, 38, 50):
        oval(d, [x * S, 5 * S, (x + 12) * S, 32 * S], SKIN)
    oval(d, [2 * S, 30 * S, 22 * S, 55 * S], SKIN)
    return soft(img)


def part_hips() -> Image.Image:
    w, h = 200 * S, 80 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([20 * S, 10 * S, 180 * S, 70 * S], 20 * S, fill=PANTS)
    return soft(img)


def part_thigh() -> Image.Image:
    w, h = 80 * S, 160 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([15 * S, 5 * S, 65 * S, 150 * S], 24 * S, fill=PANTS)
    return soft(img)


def part_shin() -> Image.Image:
    w, h = 70 * S, 150 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([12 * S, 5 * S, 58 * S, 140 * S], 20 * S, fill=PANTS)
    return soft(img)


def part_foot() -> Image.Image:
    w, h = 110 * S, 55 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([5 * S, 10 * S, 100 * S, 48 * S], 14 * S, fill=SHOE)
    d.rounded_rectangle([5 * S, 32 * S, 100 * S, 50 * S], 10 * S, fill=SHOE_W)
    d.arc([25 * S, 8 * S, 70 * S, 40 * S], 200, 340, fill=WHITE, width=3 * S)
    return soft(img)


def part_joint() -> Image.Image:
    w, h = 40 * S, 40 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    oval(d, [4 * S, 4 * S, 36 * S, 36 * S], SKIN)
    return soft(img)


def assemble_pose(mode: str, expr: str, bake_mouth: str | None = None, walk_phase: int = 0) -> Image.Image:
    """Front bodies have NO mouth — render composites mouth for lip-sync."""
    canvas = blank(520, 780)

    def ls(im):
        return im.resize((im.width // S, im.height // S), Image.Resampling.LANCZOS)

    head, face = ls(part_head()), ls(part_face(expr))
    neck, torso = ls(part_neck()), ls(part_torso())
    ua, fa, hand = ls(part_upper_arm()), ls(part_forearm()), ls(part_hand())
    hips = ls(part_hips())
    thigh, shin, foot = ls(part_thigh()), ls(part_shin()), ls(part_foot())
    joint = ls(part_joint())
    cx = 260

    def paste(im, x, y):
        canvas.paste(im, (int(x - im.width // 2), int(y - im.height // 2)), im)

    def paste_rot(im, x, y, angle):
        r = im.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        canvas.paste(r, (int(x - r.width // 2), int(y - r.height // 2)), r)

    d = ImageDraw.Draw(canvas)
    oval(d, [cx - 80, 720, cx + 80, 755], (0, 0, 0, 45))

    if mode in ("side_left", "walk"):
        # two walk phases with opposite leg angles
        if walk_phase == 0:
            paste_rot(thigh, cx - 10, 475, 30)
            paste_rot(shin, cx - 40, 575, 15)
            paste_rot(foot, cx - 55, 655, 5)
            paste_rot(thigh, cx + 20, 485, -25)
            paste_rot(shin, cx + 30, 585, -10)
            paste_rot(foot, cx + 25, 665, -5)
            paste_rot(ua, cx - 55, 255, 45)
            paste_rot(fa, cx - 90, 330, 25)
            paste(hand, cx - 105, 390)
            paste_rot(ua, cx + 55, 245, -55)
            paste_rot(fa, cx + 80, 185, -35)
            paste(hand, cx + 95, 145)
        else:
            paste_rot(thigh, cx + 10, 475, -30)
            paste_rot(shin, cx + 40, 575, -15)
            paste_rot(foot, cx + 55, 655, -5)
            paste_rot(thigh, cx - 20, 485, 25)
            paste_rot(shin, cx - 30, 585, 10)
            paste_rot(foot, cx - 25, 665, 5)
            paste_rot(ua, cx + 55, 255, -45)
            paste_rot(fa, cx + 90, 330, -25)
            paste(hand, cx + 105, 390)
            paste_rot(ua, cx - 55, 245, 55)
            paste_rot(fa, cx - 80, 185, 35)
            paste(hand, cx - 95, 145)
        paste(hips, cx, 400)
        paste(torso, cx, 280)
        paste(neck, cx, 175)
        paste(head, cx, 120)
        paste(face, cx, 120)
        # tiny closed mouth on side only (no rhubarb)
        m = ls(part_mouth("closed"))
        paste(m, cx, 120)
        return canvas

    if mode == "sit":
        paste_rot(thigh, cx - 40, 520, 70)
        paste_rot(shin, cx - 90, 580, 5)
        paste_rot(foot, cx - 100, 650, 0)
        paste_rot(thigh, cx + 40, 520, -70)
        paste_rot(shin, cx + 90, 580, -5)
        paste_rot(foot, cx + 100, 650, 0)
        paste(hips, cx, 460)
        paste(torso, cx, 320)
        paste_rot(ua, cx - 70, 300, 15)
        paste_rot(fa, cx - 80, 380, 10)
        paste(hand, cx - 85, 440)
        paste_rot(ua, cx + 70, 300, -15)
        paste_rot(fa, cx + 80, 380, -10)
        paste(hand, cx + 85, 440)
        paste(neck, cx, 200)
        paste(head, cx, 145)
        paste(face, cx, 145)
        # sit uses overlay too — no bake
        return canvas

    # stand / point / present legs
    paste(thigh, cx - 35, 500)
    paste(joint, cx - 35, 560)
    paste(shin, cx - 35, 620)
    paste(foot, cx - 40, 690)
    paste(thigh, cx + 35, 500)
    paste(joint, cx + 35, 560)
    paste(shin, cx + 35, 620)
    paste(foot, cx + 40, 690)
    paste(hips, cx, 420)
    paste(torso, cx, 280)

    if mode == "point":
        paste_rot(ua, cx - 70, 250, 15)
        paste_rot(fa, cx - 85, 340, 20)
        paste(hand, cx - 95, 400)
        paste_rot(ua, cx + 70, 230, -55)
        paste_rot(fa, cx + 120, 160, -40)
        paste(hand, cx + 150, 110)
    elif mode == "present":
        paste_rot(ua, cx - 75, 250, 50)
        paste_rot(fa, cx - 130, 280, 20)
        paste(hand, cx - 160, 300)
        paste_rot(ua, cx + 75, 250, -50)
        paste_rot(fa, cx + 130, 280, -20)
        paste(hand, cx + 160, 300)
    else:
        paste_rot(ua, cx - 70, 260, 10)
        paste_rot(fa, cx - 80, 350, 5)
        paste(hand, cx - 85, 410)
        paste_rot(ua, cx + 70, 260, -10)
        paste_rot(fa, cx + 80, 350, -5)
        paste(hand, cx + 85, 410)

    paste(neck, cx, 175)
    paste(head, cx, 120)
    paste(face, cx, 120)
    # NO mouth bake — lip-sync overlay only
    return canvas


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    parts_dir = out / "parts"
    parts_dir.mkdir(exist_ok=True)

    for name, fn in {
        "head.png": part_head,
        "face_neutral.png": lambda: part_face("neutral"),
        "mouth_closed.png": lambda: part_mouth("closed"),
        "mouth_open.png": lambda: part_mouth("open"),
        "mouth_wide.png": lambda: part_mouth("wide"),
        "mouth_smile.png": lambda: part_mouth("smile"),
        "torso.png": part_torso,
        "thigh.png": part_thigh,
        "shin.png": part_shin,
        "foot.png": part_foot,
        "hand.png": part_hand,
    }.items():
        fn().save(parts_dir / name, "PNG")

    # front poses — no baked mouth
    assemble_pose("stand", "neutral").save(out / "body.png")
    assemble_pose("stand", "happy").save(out / "body_happy.png")
    assemble_pose("stand", "question").save(out / "body_question.png")
    assemble_pose("stand", "blink").save(out / "body_blink.png")
    assemble_pose("present", "welcoming").save(out / "body_present.png")
    assemble_pose("point", "neutral").save(out / "arm_point.png")
    assemble_pose("sit", "neutral").save(out / "body_sit.png")

    # walk cycle two phases
    assemble_pose("walk", "neutral", walk_phase=0).save(out / "walk_l0.png")
    assemble_pose("walk", "neutral", walk_phase=1).save(out / "walk_l1.png")
    assemble_pose("walk", "neutral", walk_phase=0).save(out / "walk_r0.png")
    assemble_pose("walk", "neutral", walk_phase=1).save(out / "walk_r1.png")
    assemble_pose("walk", "neutral", walk_phase=0).save(out / "body_side_left.png")
    assemble_pose("walk", "neutral", walk_phase=1).save(out / "body_side_right.png")

    # mouth overlays at head position (y=120)
    for kind, fname in [
        ("closed", "mouth_closed.png"),
        ("open", "mouth_open.png"),
        ("wide", "mouth_wide.png"),
        ("smile", "mouth_smile.png"),
    ]:
        canvas = blank(520, 780)
        m = part_mouth(kind).resize(
            (part_mouth(kind).width // S, part_mouth(kind).height // S),
            Image.Resampling.LANCZOS,
        )
        canvas.paste(m, (260 - m.width // 2, 120 - m.height // 2), m)
        canvas.save(out / fname, "PNG")
        print("mouth", fname)

    print("poses ok (no baked mouth on front)")


if __name__ == "__main__":
    main()
