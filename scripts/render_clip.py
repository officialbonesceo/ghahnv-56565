#!/usr/bin/env python3
"""
Text → Edge TTS audio → simple captioned MP4 (ffmpeg).
Designed to run on GitHub Actions (CPU-only) and locally.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def which_or_die(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"ERROR: `{name}` not found on PATH", file=sys.stderr)
        sys.exit(1)
    return path


def safe_drawtext(text: str, max_chars: int = 120) -> str:
    """Escape text for ffmpeg drawtext and keep it short."""
    t = " ".join(text.split())
    if len(t) > max_chars:
        t = t[: max_chars - 1] + "…"
    # ffmpeg drawtext escapes
    t = t.replace("\\", "\\\\")
    t = t.replace("'", "\\'")
    t = t.replace(":", "\\:")
    t = t.replace("%", "%%")
    return t


async def synthesize(text: str, voice: str, mp3_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(mp3_path))


def probe_duration_seconds(audio_path: Path) -> float:
    ffprobe = which_or_die("ffprobe")
    out = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        text=True,
    ).strip()
    try:
        return max(0.5, float(out))
    except ValueError:
        return 3.0


def render_video(audio: Path, text: str, out_mp4: Path, width: int = 1280, height: int = 720) -> None:
    ffmpeg = which_or_die("ffmpeg")
    duration = probe_duration_seconds(audio)
    label = safe_drawtext(text)

    # Dark cyan/purple "cyber" card look, centered caption, branded footer
    vf = (
        f"drawtext=text='{label}':"
        f"fontcolor=white:fontsize=36:line_spacing=8:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"box=1:boxcolor=0x0b0e17@0.75:boxborderw=24,"
        f"drawtext=text='Talking Clip Factory':"
        f"fontcolor=0x67e8f9:fontsize=20:"
        f"x=(w-text_w)/2:y=h-48"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0b0e17:s={width}x{height}:d={duration:.3f}",
        "-i",
        str(audio),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(out_mp4),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a simple talking clip from text")
    parser.add_argument(
        "--text",
        default="Hello from Talking Clip Factory. This pipeline uses Edge TTS and ffmpeg on GitHub Actions.",
        help="Spoken script",
    )
    parser.add_argument(
        "--voice",
        default="en-US-JennyNeural",
        help="Edge TTS voice (maintained neural voice)",
    )
    parser.add_argument("--out", default="output.mp4", help="Output MP4 path")
    args = parser.parse_args()

    text = args.text.strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    # Soft length guard for free CI
    if len(text) > 800:
        print("WARNING: text truncated to 800 characters for CI limits")
        text = text[:800]

    out_mp4 = Path(args.out).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "speech.mp3"
        print(f"TTS voice={args.voice}")
        asyncio.run(synthesize(text, args.voice, mp3))
        if not mp3.exists() or mp3.stat().st_size < 100:
            print("ERROR: TTS produced empty audio", file=sys.stderr)
            sys.exit(1)
        print(f"Audio bytes={mp3.stat().st_size}")
        render_video(mp3, text, out_mp4)

    print(f"OK wrote {out_mp4} ({out_mp4.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
