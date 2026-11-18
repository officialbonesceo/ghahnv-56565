#!/usr/bin/env python3
"""
Generate animated 2D mouth + eyes (SVG-style timing) and composite onto a base MP4.
Mouth open amount follows the same speech windows as the 3D facial script.
No true face tracking — places overlay in upper-center face region of the frame.
Works fully headless on GitHub Actions (stdlib + ffmpeg).
"""
from __future__ import annotations

import math
import random
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


def parse_args(argv):
    args = {
        "base": "assets/blender/mike3d_test.mp4",
        "out": "assets/blender/mike3d_overlay.mp4",
        "fps": 24,
        "seconds": 12.0,
        "width": 720,
        "height": 1280,
    }
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:]
            val = argv[i + 1]
            if key == "seconds":
                args[key] = float(val)
            elif key in ("width", "height", "fps"):
                args[key] = int(val)
            else:
                args[key] = val
            i += 2
        else:
            i += 1
    return args


def png_rgba(w: int, h: int, pixels: bytes) -> bytes:
    """Minimal PNG writer (RGBA)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b""
    row = w * 4
    for y in range(h):
        raw += b"\x00" + pixels[y * row : (y + 1) * row]
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def fill_ellipse(buf, w, h, cx, cy, rx, ry, rgba):
    r, g, b, a = rgba
    for y in range(max(0, int(cy - ry - 1)), min(h, int(cy + ry + 2))):
        for x in range(max(0, int(cx - rx - 1)), min(w, int(cx + rx + 2))):
            dx = (x - cx) / max(0.001, rx)
            dy = (y - cy) / max(0.001, ry)
            if dx * dx + dy * dy <= 1.0:
                i = (y * w + x) * 4
                # alpha blend over existing
                oa = buf[i + 3] / 255.0
                na = a / 255.0
                out_a = na + oa * (1 - na)
                if out_a < 1e-6:
                    continue
                buf[i] = int((r * na + buf[i] * oa * (1 - na)) / out_a)
                buf[i + 1] = int((g * na + buf[i + 1] * oa * (1 - na)) / out_a)
                buf[i + 2] = int((b * na + buf[i + 2] * oa * (1 - na)) / out_a)
                buf[i + 3] = int(out_a * 255)


def mouth_amount(t: float) -> float:
    windows = [(0.6, 3.8), (4.0, 7.2), (7.6, 11.4)]
    if any(a <= t <= b for a, b in windows):
        amt = 0.45 + 0.55 * abs(math.sin(t * 11.0))
        amt *= 0.75 + 0.25 * abs(math.sin(t * 4.1))
        return min(1.0, amt)
    return 0.05 * abs(math.sin(t * 1.6))


def blink_amount(t: float, blink_times) -> float:
    for bt in blink_times:
        if abs(t - bt) < 0.05:
            return 1.0
        if abs(t - bt) < 0.10:
            return 0.55
    return 0.0


def make_face_layer(w: int, h: int, mouth: float, blink: float) -> bytes:
    """Transparent RGBA layer with cartoon mouth + eyes in face region."""
    buf = bytearray(w * h * 4)  # all transparent

    # Face region (upper-center of vertical video)
    fx = w * 0.50
    fy = h * 0.32  # mouth height in frame
    eye_y = h * 0.24
    eye_dx = w * 0.08

    # Eyes (white + pupil), lids close on blink
    for side in (-1, 1):
        ex = fx + side * eye_dx
        eye_open = max(0.12, 1.0 - blink)
        rx, ry = w * 0.045, h * 0.018 * eye_open
        fill_ellipse(buf, w, h, ex, eye_y, rx, ry, (250, 250, 250, 230))
        fill_ellipse(buf, w, h, ex, eye_y, rx * 0.35, ry * 0.55, (30, 30, 40, 240))

    # Mouth: closed line -> open ellipse
    mw = w * (0.07 + 0.06 * mouth)
    mh = h * (0.006 + 0.045 * mouth)
    # dark inner mouth
    fill_ellipse(buf, w, h, fx, fy, mw, mh, (40, 15, 20, 220))
    # lip outline (slightly larger, reddish)
    if mouth > 0.15:
        fill_ellipse(buf, w, h, fx, fy - mh * 0.15, mw * 1.05, mh * 0.35, (180, 70, 80, 180))
        fill_ellipse(buf, w, h, fx, fy + mh * 0.35, mw * 1.0, mh * 0.25, (160, 55, 65, 160))
    else:
        # thin closed lips
        fill_ellipse(buf, w, h, fx, fy, mw, max(2.0, mh), (150, 60, 70, 200))

    return png_rgba(w, h, bytes(buf))


def main():
    args = parse_args(sys.argv[1:])
    base = Path(args["base"])
    out = Path(args["out"])
    fps = int(args["fps"])
    seconds = float(args["seconds"])
    width = int(args["width"])
    height = int(args["height"])
    total = max(1, int(round(seconds * fps)))

    if not base.exists():
        raise SystemExit(f"Missing base video: {base}")

    random.seed(42)
    blink_times = []
    t = 1.0
    while t < seconds - 0.3:
        blink_times.append(t)
        t += random.uniform(2.0, 3.6)

    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        layer_dir = tmp / "layers"
        layer_dir.mkdir()
        for f in range(1, total + 1):
            tsec = f / float(fps)
            m = mouth_amount(tsec)
            b = blink_amount(tsec, blink_times)
            png = make_face_layer(width, height, m, b)
            (layer_dir / f"layer_{f:04d}.png").write_bytes(png)

        # Overlay transparent layers onto base
        # scale base if needed, then overlay
        cmd = [
            "ffmpeg", "-y",
            "-i", str(base),
            "-framerate", str(fps),
            "-i", str(layer_dir / "layer_%04d.png"),
            "-filter_complex",
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[base];"
            f"[1:v]format=rgba[ov];"
            f"[base][ov]overlay=0:0:format=auto",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart",
            "-t", str(seconds),
            str(out),
        ]
        print("FFMPEG", " ".join(cmd[:8]), "...")
        subprocess.check_call(cmd)

    print("OK_OVERLAY", out, out.stat().st_size if out.exists() else 0)


if __name__ == "__main__":
    main()
