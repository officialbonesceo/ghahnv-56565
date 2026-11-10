#!/usr/bin/env python3
"""If speech.mp3 is longer than ~62s, speed it up to fit under 60s."""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    try:
        dur = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    "speech.mp3",
                ],
                text=True,
            ).strip()
        )
    except Exception as e:
        print("cap_audio skip ffprobe", e, file=sys.stderr)
        return

    print("duration", dur)
    if dur <= 62:
        return

    factor = min(dur / 58.0, 1.35)
    print("speed_up", factor)
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            "speech.mp3",
            "-filter:a",
            f"atempo={factor:.4f}",
            "speech_fast.mp3",
        ]
    )
    os.replace("speech_fast.mp3", "speech.mp3")
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", "speech.mp3", "-ar", "16000", "-ac", "1", "speech.wav"]
    )
    dur2 = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                "speech.mp3",
            ],
            text=True,
        ).strip()
    )
    print("duration_after", dur2)


if __name__ == "__main__":
    main()
