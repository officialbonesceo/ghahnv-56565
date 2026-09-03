#!/usr/bin/env python3
"""Text -> Edge TTS -> ffmpeg captioned MP4 (baseline / fallback)."""
from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


def which_or_die(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"ERROR: `{name}` not found", file=sys.stderr)
        sys.exit(1)
    return path


def safe_drawtext(text: str, max_chars: int = 120) -> str:
    t = " ".join(text.split())
    if len(t) > max_chars:
        t = t[: max_chars - 1] + "..."
    return t.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "%%")


async def synthesize(text: str, voice: str, mp3_path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice).save(str(mp3_path))


def probe_duration_seconds(audio_path: Path) -> float:
    out = subprocess.check_output(
        [which_or_die("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        text=True,
    ).strip()
    try:
        return max(0.5, float(out))
    except ValueError:
        return 3.0


def render_ffmpeg(audio: Path, text: str, out_mp4: Path) -> None:
    duration = probe_duration_seconds(audio)
    label = safe_drawtext(text)
    vf = (
        f"drawtext=text='{label}':fontcolor=white:fontsize=36:line_spacing=8:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x0b0e17@0.75:boxborderw=24,"
        f"drawtext=text='Talking Clip Factory':fontcolor=0x67e8f9:fontsize=20:x=(w-text_w)/2:y=h-48"
    )
    subprocess.check_call([
        which_or_die("ffmpeg"), "-y",
        "-f", "lavfi", "-i", f"color=c=0x0b0e17:s=1280x720:d={duration:.3f}",
        "-i", str(audio), "-vf", vf,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_mp4),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--voice", default="en-US-JennyNeural")
    parser.add_argument("--out", default="output.mp4")
    parser.add_argument("--audio-out", default="speech.mp3")
    args = parser.parse_args()
    text = args.text.strip()[:800]
    audio = Path(args.audio_out).resolve()
    out_mp4 = Path(args.out).resolve()
    audio.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(synthesize(text, args.voice, audio))
    print(f"Audio: {audio} ({audio.stat().st_size} bytes)")
    render_ffmpeg(audio, text, out_mp4)
    print(f"OK {out_mp4}")


if __name__ == "__main__":
    main()
