#!/usr/bin/env python3
"""Rotate classroom environments (image + procedural) and readable fonts."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "data" / "environments.json"

# Fallback if config missing
DEFAULT_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]


def load_cfg() -> dict:
    if CFG_PATH.exists():
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    return {}


def topic_seed(topic: str) -> int:
    return int(hashlib.md5((topic or "x").encode()).hexdigest(), 16)


def pick_font_path(topic: str, size: int = 48) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    cfg = load_cfg()
    fonts = cfg.get("fonts") or []
    seed = topic_seed(topic)
    ordered: list[str] = []
    if fonts:
        # rotate: start at seed index
        n = len(fonts)
        start = seed % n
        for i in range(n):
            entry = fonts[(start + i) % n]
            for p in entry.get("paths") or []:
                ordered.append(p)
    ordered.extend(DEFAULT_FONTS)
    for path in ordered:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def pick_caption_font_name(topic: str) -> str:
    cfg = load_cfg()
    names = cfg.get("caption_fonts") or [
        "DejaVu Sans", "Liberation Sans", "FreeSans", "Noto Sans", "Ubuntu",
    ]
    return names[topic_seed(topic) % len(names)]


def available_image_envs(cfg: dict | None = None) -> list[dict]:
    cfg = cfg or load_cfg()
    out = []
    for env in cfg.get("image_environments") or []:
        f = ROOT / env.get("file", "")
        if f.exists() and f.stat().st_size > 3000:
            out.append(env)
    return out


def pick_environment(topic: str, rooms: list[dict] | None = None) -> dict[str, Any]:
    """Return env descriptor: type image|procedural, room/image meta."""
    cfg = load_cfg()
    seed = topic_seed(topic)
    images = available_image_envs(cfg)
    prefer = float(cfg.get("prefer_image_ratio", 0.55))
    include_proc = bool(cfg.get("include_procedural", True))

    choices: list[dict[str, Any]] = []
    for env in images:
        choices.append({"kind": "image", **env})
    if include_proc and rooms:
        for r in rooms:
            choices.append({"kind": "procedural", "id": r.get("id", "room"), "room": r})

    if not choices:
        # last resort procedural index 0 shape
        return {"kind": "procedural", "id": "fallback", "room": (rooms or [{}])[0] if rooms else {}}

    # Prefer images roughly prefer_image_ratio of the time when both exist
    if images and include_proc and rooms:
        use_image = (seed % 100) < int(prefer * 100)
        pool = [c for c in choices if c["kind"] == ("image" if use_image else "procedural")]
        if not pool:
            pool = choices
    else:
        pool = choices

    pick = pool[seed % len(pool)]
    print("ENV_PICK", pick.get("kind"), pick.get("id"), file=__import__("sys").stderr)
    return pick


def board_rect_px(env: dict, width: int, height: int) -> tuple[int, int, int, int]:
    """Return board (x0,y0,x1,y1) in pixels for image env."""
    b = env.get("board") or {"x": 0.12, "y": 0.08, "w": 0.76, "h": 0.38}
    x0 = int(float(b["x"]) * width)
    y0 = int(float(b["y"]) * height)
    x1 = int((float(b["x"]) + float(b["w"])) * width)
    y1 = int((float(b["y"]) + float(b["h"])) * height)
    return x0, y0, x1, y1


def wrap_text(draw: ImageDraw.ImageDraw, text: str, tf, max_w: int) -> list[str]:
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=tf)[2] > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_board_text(
    base: Image.Image,
    topic: str,
    definition: str,
    board: tuple[int, int, int, int],
    text_color: tuple[int, int, int] = (255, 255, 240),
) -> Image.Image:
    """Write topic + definition inside the board rectangle (SVG-like sharp text layer)."""
    img = base.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = board
    pad = 28
    max_w = max(40, x1 - x0 - pad * 2)

    # slight translucent panel so text stays readable on any photo board
    d.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], 10, fill=(0, 0, 0, 55))

    title_f = pick_font_path(topic, 52)
    # shrink title to fit
    while True:
        bb = d.textbbox((0, 0), topic or "Lesson", font=title_f)
        if bb[2] - bb[0] <= max_w or getattr(title_f, "size", 24) <= 26:
            break
        try:
            title_f = ImageFont.truetype(title_f.path, title_f.size - 3)  # type: ignore[attr-defined]
        except Exception:
            break

    y = y0 + pad + 8
    for line in wrap_text(d, topic or "Lesson", title_f, max_w)[:2]:
        bb = d.textbbox((0, 0), line, font=title_f)
        tw = bb[2] - bb[0]
        d.text((x0 + (x1 - x0 - tw) // 2, y), line, font=title_f, fill=(*text_color, 255))
        y += getattr(title_f, "size", 40) + 10

    if definition:
        y += 10
        body_f = pick_font_path(topic + "_body", 28)
        for line in wrap_text(d, definition, body_f, max_w)[:7]:
            bb = d.textbbox((0, 0), line, font=body_f)
            tw = bb[2] - bb[0]
            d.text((x0 + (x1 - x0 - tw) // 2, y), line, font=body_f, fill=(*text_color, 245))
            y += getattr(body_f, "size", 26) + 6
            if y > y1 - pad:
                break

    return Image.alpha_composite(img, overlay).convert("RGB")


def load_image_classroom(env: dict, topic: str, definition: str, width: int = 1080, height: int = 1920) -> Image.Image | None:
    path = ROOT / env.get("file", "")
    if not path.exists():
        return None
    try:
        base = Image.open(path).convert("RGB")
        base = base.resize((width, height), Image.Resampling.LANCZOS)
    except Exception as e:
        print("image classroom load fail", e, file=__import__("sys").stderr)
        return None
    board = board_rect_px(env, width, height)
    tc = env.get("text_color") or [255, 255, 240]
    text_color = (int(tc[0]), int(tc[1]), int(tc[2]))
    return draw_board_text(base, topic, (definition or "")[:320], board, text_color)
