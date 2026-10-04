#!/usr/bin/env python3
"""Build teaser audio segment-by-segment so answers are never spoken during ask."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

VOICE = "en-US-ChristopherNeural"
RATE = "+8%"


async def synth(text: str, out: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(out))


def silence_wav(path: Path, secs: float) -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            str(secs),
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
    )


async def main() -> None:
    job = json.loads(Path("teaser_job.json").read_text(encoding="utf-8"))
    segments = job["segments"]
    timeline = []
    t = 0.0
    parts: list[Path] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, seg in enumerate(segments):
            phase = seg["phase"]
            out = tmp_path / f"seg_{i:02d}.mp3"
            if phase == "countdown":
                secs = float(seg.get("secs") or 5)
                silence_wav(out, secs)
            else:
                text = (seg.get("text") or "").strip()
                if not text:
                    silence_wav(out, 0.3)
                else:
                    await synth(text, out)
            dur = duration(out)
            timeline.append(
                {
                    "phase": phase,
                    "q": seg.get("q"),
                    "start": round(t, 3),
                    "end": round(t + dur, 3),
                    "duration": round(dur, 3),
                }
            )
            t += dur
            parts.append(out)

        # concat
        list_file = tmp_path / "list.txt"
        list_file.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8"
        )
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "speech.mp3",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    Path("teaser_timeline.json").write_text(
        json.dumps({"total": round(t, 3), "timeline": timeline}, indent=2),
        encoding="utf-8",
    )
    print("OK speech.mp3 total", round(t, 2), "s", len(timeline), "segments")


if __name__ == "__main__":
    asyncio.run(main())
