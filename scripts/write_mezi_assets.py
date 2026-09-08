#!/usr/bin/env python3
"""Mike parts pack — high-quality flat cartoon (PNG per joint), yellow hoodie + glasses."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# High-res parts for cleaner scale-down
S = 2  # internal scale

HOODIE = (255, 196, 40, 255)
HOODIE_L = (255, 230, 130, 255)
HOODIE_D = (235, 170, 25, 255)
SKIN = (235, 190, 150, 255)
SKIN_D = (210, 160, 120, 255)
HAIR = (30, 26, 32, 255)
PANTS = (40, 48, 65, 255)
PANTS_L = (55, 65, 85, 255)
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
    """Slight blur for less jagged edges."""
    return img.filter(ImageFilter.SMOOTH)


def part_head() -> Image.Image:
    w, h = 220 * S, 260 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.55)
    # hair back
    oval(d, [cx - 95 * S, cy - 110 * S, cx + 95 * S, cy + 20 * S], HAIR)
    # face
    oval(d, [cx - 88 * S, cy - 90 * S, cx + 88 * S, cy + 95 * S], SKIN)
    # hair front / volume
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
    # ears
    oval(d, [cx - 100 * S, cy - 10 * S, cx - 75 * S, cy + 35 * S], SKIN)
    oval(d, [cx + 75 * S, cy - 10 * S, cx + 100 * S, cy + 35 * S], SKIN)
    return soft(img)


def part_face(expr: str = "neutral") -> Image.Image:
    w, h = 220 * S, 260 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.55)
    # eyes white
    if expr == "blink":
        d.line([(cx - 50 * S, cy - 5 * S), (cx - 20 * S, cy - 5 * S)], fill=BLACK, width=4 * S)
        d.line([(cx + 20 * S, cy - 5 * S), (cx + 50 * S, cy - 5 * S)], fill=BLACK, width=4 * S)
    else:
        oval(d, [cx - 55 * S, cy - 25 * S, cx - 15 * S, cy + 25 * S], WHITE, BLACK, 3 * S)
        oval(d, [cx + 15 * S, cy - 25 * S, cx + 55 * S, cy + 25 * S], WHITE, BLACK, 3 * S)
        # pupils
        oval(d, [cx - 42 * S, cy - 10 * S, cx - 22 * S, cy + 12 * S], BLACK)
        oval(d, [cx + 22 * S, cy - 10 * S, cx + 42 * S, cy + 12 * S], BLACK)
        # shine
        oval(d, [cx - 36 * S, cy - 12 * S, cx - 28 * S, cy - 4 * S], WHITE)
        oval(d, [cx + 28 * S, cy - 12 * S, cx + 36 * S, cy - 4 * S], WHITE)
    # brows
    if expr == "question":
        d.arc([cx - 55 * S, cy - 45 * S, cx - 15 * S, cy - 20 * S], 200, 340, fill=BLACK, width=3 * S)
        d.arc([cx + 15 * S, cy - 48 * S, cx + 55 * S, cy - 22 * S], 200, 340, fill=BLACK, width=3 * S)
    elif expr in ("happy", "welcoming"):
        d.arc([cx - 55 * S, cy - 42 * S, cx - 15 * S, cy - 18 * S], 200, 340, fill=BLACK, width=3 * S)
        d.arc([cx + 15 * S, cy - 42 * S, cx + 55 * S, cy - 18 * S], 200, 340, fill=BLACK, width=3 * S)
    else:
        d.line([(cx - 52 * S, cy - 32 * S), (cx - 18 * S, cy - 32 * S)], fill=BLACK, width=3 * S)
        d.line([(cx + 18 * S, cy - 32 * S), (cx + 52 * S, cy - 32 * S)], fill=BLACK, width=3 * S)
    # nose
    oval(d, [cx - 10 * S, cy + 15 * S, cx + 10 * S, cy + 38 * S], SKIN_D)
    # glasses
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
    else:  # wide
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
    # hoodie body
    d.rounded_rectangle([30 * S, 20 * S, 250 * S, 300 * S], 40 * S, fill=HOODIE)
    # pocket
    d.rounded_rectangle([70 * S, 140 * S, 210 * S, 260 * S], 28 * S, fill=HOODIE_L)
    # hood rim
    d.arc([50 * S, 5 * S, 230 * S, 100 * S], 200, 340, fill=HOODIE_D, width=8 * S)
    # drawstrings
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
    # palm
    oval(d, [12 * S, 20 * S, 58 * S, 70 * S], SKIN)
    # fingers
    for i, x in enumerate([14, 26, 38, 50]):
        oval(d, [x * S, 5 * S, (x + 12) * S, 32 * S], SKIN)
    # thumb
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
    # sneaker
    d.rounded_rectangle([5 * S, 10 * S, 100 * S, 48 * S], 14 * S, fill=SHOE)
    d.rounded_rectangle([5 * S, 32 * S, 100 * S, 50 * S], 10 * S, fill=SHOE_W)
    # stripe
    d.arc([25 * S, 8 * S, 70 * S, 40 * S], 200, 340, fill=WHITE, width=3 * S)
    return soft(img)


def part_joint() -> Image.Image:
    """Knee / elbow orb."""
    w, h = 40 * S, 40 * S
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    oval(d, [4 * S, 4 * S, 36 * S, 36 * S], SKIN)
    return soft(img)


def assemble_pose(mode: str, expr: str, mouth: str) -> Image.Image:
    """Build a full-body pose from parts (for compatibility + preview)."""
    canvas = blank(520, 780)
    # scale parts down from 2x
    def load_scaled(im):
        return im.resize((im.width // S, im.height // S), Image.Resampling.LANCZOS)

    head = load_scaled(part_head())
    face = load_scaled(part_face(expr))
    mth = load_scaled(part_mouth(mouth))
    neck = load_scaled(part_neck())
    torso = load_scaled(part_torso())
    ua = load_scaled(part_upper_arm())
    fa = load_scaled(part_forearm())
    hand = load_scaled(part_hand())
    hips = load_scaled(part_hips())
    thigh = load_scaled(part_thigh())
    shin = load_scaled(part_shin())
    foot = load_scaled(part_foot())
    joint = load_scaled(part_joint())

    cx = 260

    def paste(im, x, y):
        canvas.paste(im, (int(x - im.width // 2), int(y - im.height // 2)), im)

    def paste_rot(im, x, y, angle):
        r = im.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        canvas.paste(r, (int(x - r.width // 2), int(y - r.height // 2)), r)

    # shadow
    d = ImageDraw.Draw(canvas)
    oval(d, [cx - 80, 720, cx + 80, 755], (0, 0, 0, 45))

    if mode == "side_left":
        # simplified side: legs stride
        paste_rot(thigh, cx - 15, 480, 25)
        paste_rot(shin, cx - 35, 580, 10)
        paste_rot(foot, cx - 50, 660, 0)
        paste_rot(thigh, cx + 15, 490, -20)
        paste_rot(shin, cx + 25, 590, -5)
        paste_rot(foot, cx + 30, 670, 0)
        paste(hips, cx, 400)
        paste(torso, cx, 280)
        paste_rot(ua, cx - 50, 250, 40)
        paste_rot(fa, cx - 80, 320, 20)
        paste(hand, cx - 95, 380)
        paste_rot(ua, cx + 50, 250, -50)
        paste_rot(fa, cx + 70, 200, -30)
        paste(hand, cx + 85, 160)
        paste(neck, cx, 175)
        paste(head, cx, 120)
        paste(face, cx, 120)
        # no mouth overlay on pure side — face has slight smile baked if needed
        return canvas

    # front poses
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
        paste(mth, cx, 145)
        return canvas

    # legs stand
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
    paste(mth, cx, 120)
    return canvas


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "assets" / "mezi"
    out.mkdir(parents=True, exist_ok=True)
    parts_dir = out / "parts"
    parts_dir.mkdir(exist_ok=True)

    # raw parts (2x, saved for future bone animator)
    exports = {
        "head.png": part_head,
        "face_neutral.png": lambda: part_face("neutral"),
        "face_happy.png": lambda: part_face("happy"),
        "face_question.png": lambda: part_face("question"),
        "face_blink.png": lambda: part_face("blink"),
        "mouth_closed.png": lambda: part_mouth("closed"),
        "mouth_open.png": lambda: part_mouth("open"),
        "mouth_wide.png": lambda: part_mouth("wide"),
        "mouth_smile.png": lambda: part_mouth("smile"),
        "neck.png": part_neck,
        "torso.png": part_torso,
        "upper_arm.png": part_upper_arm,
        "forearm.png": part_forearm,
        "hand.png": part_hand,
        "hips.png": part_hips,
        "thigh.png": part_thigh,
        "shin.png": part_shin,
        "foot.png": part_foot,
        "joint.png": part_joint,
    }
    for name, fn in exports.items():
        fn().save(parts_dir / name, "PNG")
        print("part", name)

    # full poses for current renderer
    poses = {
        "body.png": ("stand", "neutral", "closed"),
        "body_happy.png": ("stand", "happy", "smile"),
        "body_question.png": ("stand", "question", "closed"),
        "body_blink.png": ("stand", "blink", "closed"),
        "body_present.png": ("present", "welcoming", "smile"),
        "arm_point.png": ("point", "neutral", "closed"),
        "body_sit.png": ("sit", "neutral", "closed"),
        "body_side_left.png": ("side_left", "neutral", "closed"),
        "body_side_right.png": ("side_left", "neutral", "closed"),
        "walk_l0.png": ("side_left", "neutral", "closed"),
        "walk_l1.png": ("side_left", "neutral", "closed"),
        "walk_r0.png": ("side_left", "neutral", "closed"),
        "walk_r1.png": ("side_left", "neutral", "closed"),
    }
    for name, (mode, expr, mouth) in poses.items():
        assemble_pose(mode, expr, mouth).save(out / name, "PNG")
        print("pose", name)

    # mouth overlays aligned to body canvas (front)
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


if __name__ == "__main__":
    main()
