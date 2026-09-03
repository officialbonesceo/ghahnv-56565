#!/usr/bin/env python3
"""MEZI-inspired 2D cartoon frames (yellow hoodie explainer). Offline CI puppet."""
from __future__ import annotations

from PIL import Image, ImageDraw

YELLOW_D = (230, 170, 30)
SKIN = (201, 148, 110)
SKIN_D = (180, 125, 90)
HAIR = (35, 30, 28)
HOODIE = (255, 196, 40)
PANTS = (30, 32, 40)
BG_ROOM = (245, 240, 230)
CYAN = (80, 200, 230)
MOUTH_CLOSED = (120, 60, 55)
MOUTH_OPEN = (90, 40, 45)
WHITE = (255, 255, 255)
BLACK = (25, 25, 25)


def draw_background(w: int, h: int, room: str = "studio") -> Image.Image:
    if room == "tech":
        img = Image.new("RGB", (w, h), (20, 28, 48))
        d = ImageDraw.Draw(img)
        d.rectangle([0, int(h * 0.75), w, h], fill=(30, 40, 60))
        for i in range(8):
            x = 30 + i * 120
            d.ellipse([x, 80, x + 40, 120], outline=CYAN, width=2)
        return img
    if room == "science":
        img = Image.new("RGB", (w, h), (230, 245, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, int(h * 0.7), w, h], fill=(200, 230, 200))
        d.ellipse([w - 180, 40, w - 40, 180], fill=(255, 220, 80))
        return img
    img = Image.new("RGB", (w, h), BG_ROOM)
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(h * 0.72), w, h], fill=(220, 210, 195))
    for i in range(3):
        x0 = 40 + i * (w // 3)
        d.rounded_rectangle([x0, 40, x0 + w // 3 - 60, int(h * 0.65)], 20, outline=(210, 200, 185), width=3)
    return img


def draw_mezi(base: Image.Image, mouth: str = "closed", expression: str = "happy", pose: str = "idle") -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx = w // 2
    foot_y = int(h * 0.92)
    bob, x_off = 0, 0
    arm_up = False
    if pose == "walk1":
        bob, x_off = -8, -12
    elif pose == "walk2":
        bob, x_off = -4, 12
    elif pose == "point":
        arm_up = True
    elif pose == "laugh":
        bob = -6
    cx += x_off
    body_y = foot_y - 280 + bob

    leg_l = (cx - 35, foot_y - 90, cx - 10, foot_y)
    leg_r = (cx + 10, foot_y - 90, cx + 35, foot_y)
    if pose == "walk1":
        leg_l = (cx - 50, foot_y - 85, cx - 20, foot_y)
        leg_r = (cx + 5, foot_y - 95, cx + 30, foot_y - 10)
    elif pose == "walk2":
        leg_l = (cx - 30, foot_y - 95, cx - 5, foot_y - 10)
        leg_r = (cx + 20, foot_y - 85, cx + 50, foot_y)
    d.rectangle(leg_l, fill=PANTS)
    d.rectangle(leg_r, fill=PANTS)
    d.ellipse([leg_l[0] - 5, foot_y - 15, leg_l[2] + 10, foot_y + 5], fill=BLACK)
    d.ellipse([leg_r[0] - 5, foot_y - 15, leg_r[2] + 10, foot_y + 5], fill=BLACK)

    d.rounded_rectangle([cx - 70, body_y + 40, cx + 70, body_y + 200], 30, fill=HOODIE)
    d.rounded_rectangle([cx - 40, body_y + 120, cx + 40, body_y + 170], 12, outline=YELLOW_D, width=3)
    d.ellipse([cx - 18, body_y + 70, cx + 18, body_y + 106], fill=YELLOW_D)

    if arm_up or pose == "point":
        d.line([(cx + 60, body_y + 80), (cx + 110, body_y + 20)], fill=HOODIE, width=28)
        d.ellipse([cx + 95, body_y + 5, cx + 125, body_y + 35], fill=SKIN)
        d.line([(cx + 120, body_y + 10), (cx + 145, body_y - 20)], fill=SKIN, width=8)
        d.line([(cx - 60, body_y + 90), (cx - 85, body_y + 170)], fill=HOODIE, width=26)
        d.ellipse([cx - 100, body_y + 160, cx - 70, body_y + 190], fill=SKIN)
    elif pose == "laugh":
        d.line([(cx - 60, body_y + 90), (cx - 100, body_y + 50)], fill=HOODIE, width=26)
        d.line([(cx + 60, body_y + 90), (cx + 100, body_y + 50)], fill=HOODIE, width=26)
        d.ellipse([cx - 115, body_y + 35, cx - 85, body_y + 65], fill=SKIN)
        d.ellipse([cx + 85, body_y + 35, cx + 115, body_y + 65], fill=SKIN)
    else:
        d.line([(cx - 60, body_y + 90), (cx - 90, body_y + 175)], fill=HOODIE, width=26)
        d.line([(cx + 60, body_y + 90), (cx + 90, body_y + 175)], fill=HOODIE, width=26)
        d.ellipse([cx - 105, body_y + 165, cx - 75, body_y + 195], fill=SKIN)
        d.ellipse([cx + 75, body_y + 165, cx + 105, body_y + 195], fill=SKIN)

    d.rectangle([cx - 18, body_y + 20, cx + 18, body_y + 50], fill=SKIN)
    d.ellipse([cx - 75, body_y - 95, cx + 75, body_y + 45], fill=SKIN, outline=SKIN_D, width=2)
    d.ellipse([cx - 80, body_y - 110, cx + 80, body_y - 20], fill=HAIR)
    d.ellipse([cx - 70, body_y - 50, cx + 70, body_y + 30], fill=SKIN)
    for ox, oy in [(-50, -90), (-20, -105), (15, -108), (45, -95), (60, -70)]:
        d.ellipse([cx + ox - 18, body_y + oy - 15, cx + ox + 18, body_y + oy + 20], fill=HAIR)
    d.ellipse([cx - 88, body_y - 20, cx - 68, body_y + 10], fill=SKIN)
    d.ellipse([cx + 68, body_y - 20, cx + 88, body_y + 10], fill=SKIN)

    eye_y = body_y - 25
    d.ellipse([cx - 40, eye_y - 12, cx - 12, eye_y + 16], fill=WHITE, outline=BLACK, width=2)
    d.ellipse([cx + 12, eye_y - 12, cx + 40, eye_y + 16], fill=WHITE, outline=BLACK, width=2)
    d.ellipse([cx - 32, eye_y - 2, cx - 20, eye_y + 10], fill=BLACK)
    d.ellipse([cx + 20, eye_y - 2, cx + 32, eye_y + 10], fill=BLACK)
    d.ellipse([cx - 30, eye_y - 2, cx - 24, eye_y + 4], fill=WHITE)
    d.ellipse([cx + 22, eye_y - 2, cx + 28, eye_y + 4], fill=WHITE)
    d.arc([cx - 45, eye_y - 28, cx - 10, eye_y - 5], 200, 340, fill=BLACK, width=3)
    d.arc([cx + 10, eye_y - 28, cx + 45, eye_y - 5], 200, 340, fill=BLACK, width=3)

    my = body_y + 15
    if expression == "laugh" or mouth == "wide":
        d.ellipse([cx - 28, my - 5, cx + 28, my + 28], fill=MOUTH_OPEN, outline=BLACK, width=2)
        d.arc([cx - 22, my + 2, cx + 22, my + 22], 0, 180, fill=WHITE, width=4)
    elif mouth == "open":
        d.ellipse([cx - 22, my - 2, cx + 22, my + 22], fill=MOUTH_OPEN, outline=BLACK, width=2)
    elif mouth == "smile" or expression == "happy":
        d.arc([cx - 25, my - 15, cx + 25, my + 15], 20, 160, fill=BLACK, width=4)
    else:
        d.arc([cx - 18, my - 8, cx + 18, my + 8], 20, 160, fill=MOUTH_CLOSED, width=3)
    return img


def mouth_from_cue(value: str) -> str:
    v = (value or "X").upper()
    if v in ("A", "E", "H", "G"):
        return "wide"
    if v in ("C", "D", "F"):
        return "open"
    return "closed"


def expression_from_pose(pose: str) -> str:
    if pose == "laugh":
        return "laugh"
    return "happy"
