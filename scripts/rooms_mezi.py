#!/usr/bin/env python3
"""Mike classroom layouts — 12 distinct rooms (boards, props, not just recolors)."""
from __future__ import annotations

import random
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1080, 1920
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)

def font(size: int):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()

def wrap_text(d, text, tf, max_w):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=tf)[2] > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines

ROOMS = [
    {"id": "chalk_classic", "wall": (245, 238, 220), "floor": (92, 68, 42), "board": (28, 92, 48),
     "frame": (70, 50, 30), "accent": (210, 160, 60), "window": (160, 205, 235),
     "desk": (110, 78, 48), "theme": "chalk", "text": (255, 255, 240)},
    {"id": "lab_science", "wall": (230, 240, 248), "floor": (70, 85, 100), "board": (245, 248, 252),
     "frame": (90, 110, 130), "accent": (40, 150, 180), "window": (190, 220, 245),
     "desk": (95, 105, 120), "theme": "lab", "text": (25, 40, 60)},
    {"id": "neon_night", "wall": (18, 16, 32), "floor": (12, 12, 22), "board": (8, 10, 22),
     "frame": (0, 200, 180), "accent": (255, 60, 160), "window": (40, 30, 70),
     "desk": (30, 28, 45), "theme": "neon", "text": (180, 255, 240)},
    {"id": "cork_workshop", "wall": (210, 185, 150), "floor": (100, 75, 50), "board": (175, 140, 95),
     "frame": (90, 65, 40), "accent": (200, 90, 40), "window": (200, 210, 180),
     "desk": (130, 95, 60), "theme": "cork", "text": (40, 30, 20)},
    {"id": "stadium_lecture", "wall": (40, 55, 75), "floor": (30, 35, 45), "board": (20, 35, 55),
     "frame": (200, 180, 120), "accent": (255, 200, 50), "window": (60, 90, 130),
     "desk": (50, 55, 70), "theme": "stadium", "text": (255, 250, 220)},
    {"id": "glass_board", "wall": (235, 240, 245), "floor": (180, 185, 195), "board": (220, 230, 240),
     "frame": (140, 150, 165), "accent": (70, 130, 220), "window": (210, 225, 245),
     "desk": (160, 165, 175), "theme": "glass", "text": (30, 40, 55)},
    {"id": "purple_minimal", "wall": (210, 185, 235), "floor": (90, 75, 110), "board": (35, 40, 55),
     "frame": (120, 95, 70), "accent": (160, 100, 220), "window": (230, 220, 245),
     "desk": (140, 110, 80), "theme": "minimal", "text": (245, 245, 250)},
    {"id": "dark_tech", "wall": (18, 22, 40), "floor": (12, 14, 28), "board": (10, 15, 35),
     "frame": (40, 80, 140), "accent": (0, 220, 255), "window": (30, 50, 90),
     "desk": (25, 35, 55), "theme": "tech", "text": (180, 255, 255)},
    {"id": "green_nature", "wall": (210, 230, 200), "floor": (90, 110, 70), "board": (55, 100, 60),
     "frame": (100, 80, 50), "accent": (80, 170, 90), "window": (160, 200, 140),
     "desk": (120, 90, 55), "theme": "nature", "text": (245, 255, 240)},
    {"id": "blue_modern", "wall": (175, 205, 235), "floor": (70, 95, 130), "board": (240, 245, 255),
     "frame": (90, 130, 180), "accent": (50, 120, 210), "window": (200, 220, 245),
     "desk": (80, 110, 150), "theme": "modern", "text": (30, 50, 90)},
    {"id": "cozy_library", "wall": (250, 230, 180), "floor": (120, 85, 50), "board": (60, 45, 30),
     "frame": (100, 70, 40), "accent": (230, 170, 50), "window": (255, 240, 200),
     "desk": (140, 100, 60), "theme": "library", "text": (255, 245, 220)},
    {"id": "glitch_vhs", "wall": (15, 15, 20), "floor": (10, 10, 14), "board": (8, 8, 12),
     "frame": (80, 20, 60), "accent": (255, 40, 120), "window": (40, 20, 50),
     "desk": (30, 25, 35), "theme": "vhs", "text": (255, 200, 220)},
]
