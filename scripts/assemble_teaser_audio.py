#!/usr/bin/env python3
"""Teaser audio: Andrew Neural, human pace, ticks + jingle + calm bed."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

import edge_tts

VOICE = os.environ.get("VOICE", "en-US-AndrewNeural")
RATE = os.environ.get("RATE", "+0%")  # human pace
SR = 24000


async def synth(text: str, out: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(out))


def run_ff(args: list[str]) -> None:
    subprocess.check_call(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def to_wav(src: Path, dst: Path) -> None:
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(SR),
            "-c:a",
            "pcm_s16le",
            str(dst),
        ]
    )


def silence_wav(path: Path, secs: float) -> None:
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={SR}:cl=mono",
            "-t",
            str(secs),
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def make_tick(path: Path) -> None:
    """Short soft clock tick (~80ms)."""
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=880:duration=0.04:sample_rate={SR}",
            "-af",
            "volume=0.35,afade=t=out:st=0.02:d=0.02",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def make_countdown_with_ticks(path: Path, secs: float, tick: Path) -> None:
    """Silence bed + one tick per second."""
    n = max(1, int(round(secs)))
    # base silence
    base = path.with_name(path.stem + "_base.wav")
    silence_wav(base, float(n))
    # build filter: amix silence + delayed ticks
    inputs = ["-i", str(base)]
    filter_parts = []
    for i in range(n):
        inputs += ["-i", str(tick)]
        # tick at start of each second: 0,1,2,...
        filter_parts.append(
            f"[{i + 1}]adelay={i * 1000}|{i * 1000},volume=0.55[t{i}]"
        )
    mix_in = "[0]" + "".join(f"[t{i}]" for i in range(n))
    filter_complex = (
        ";".join(filter_parts)
        + f";{mix_in}amix=inputs={n + 1}:duration=first:dropout_transition=0,volume=1.2[out]"
    )
    run_ff(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def make_jingle(path: Path) -> None:
    """Short bright twinkle (~0.6s) for correct answer."""
    # C-E-G style beeps
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=523.25:duration=0.12:sample_rate={SR}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=659.25:duration=0.12:sample_rate={SR}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=783.99:duration=0.25:sample_rate={SR}",
            "-filter_complex",
            "[0]volume=0.28,afade=t=out:st=0.08:d=0.04[a0];"
            "[1]adelay=120|120,volume=0.28,afade=t=out:st=0.08:d=0.04[a1];"
            "[2]adelay=240|240,volume=0.32,afade=t=out:st=0.15:d=0.08[a2];"
            "[a0][a1][a2]amix=inputs=3:duration=longest,volume=1.1[out]",
            "-map",
            "[out]",
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def make_bed(path: Path, secs: float) -> None:
    """Very soft calm pad under whole video."""
    # low quiet sine + slow amplitude — stays in background
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=110:duration={secs}:sample_rate={SR}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=164.81:duration={secs}:sample_rate={SR}",
            "-filter_complex",
            "[0]volume=0.035[a];[1]volume=0.025[b];"
            "[a][b]amix=inputs=2:duration=first,"
            "lowpass=f=400,volume=0.9[out]",
            "-map",
            "[out]",
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def mix_voice_jingle(voice: Path, jingle: Path, out: Path) -> None:
    """Jingle at start of reveal, under/over voice."""
    run_ff(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(voice),
            "-i",
            str(jingle),
            "-filter_complex",
            "[1]volume=0.55[j];[0][j]amix=inputs=2:duration=first:dropout_transition=0,volume=1.15[out]",
            "-map",
            "[out]",
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
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
        tick = tmp_path / "tick.wav"
        jingle = tmp_path / "jingle.wav"
        make_tick(tick)
        make_jingle(jingle)

        for i, seg in enumerate(segments):
            phase = seg["phase"]
            raw = tmp_path / f"raw_{i:02d}.mp3"
            wav = tmp_path / f"seg_{i:02d}.wav"

            if phase == "countdown":
                secs = float(seg.get("secs") or 5)
                make_countdown_with_ticks(wav, secs, tick)
            else:
                text = (seg.get("text") or "").strip()
                if not text:
                    silence_wav(wav, 0.3)
                else:
                    await synth(text, raw)
                    voice_wav = tmp_path / f"voice_{i:02d}.wav"
                    to_wav(raw, voice_wav)
                    if phase == "reveal":
                        mix_voice_jingle(voice_wav, jingle, wav)
                    else:
                        # slight headroom
                        run_ff(
                            [
                                "ffmpeg",
                                "-y",
                                "-i",
                                str(voice_wav),
                                "-af",
                                "volume=1.0",
                                "-c:a",
                                "pcm_s16le",
                                str(wav),
                            ]
                        )

            dur = duration(wav)
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
            parts.append(wav)

        list_file = tmp_path / "list.txt"
        list_file.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8"
        )
        joined = tmp_path / "joined.wav"
        run_ff(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(joined),
            ]
        )

        bed = tmp_path / "bed.wav"
        make_bed(bed, max(t, 1.0))
        mixed = tmp_path / "mixed.wav"
        # voice path louder; bed quiet under everything
        run_ff(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(joined),
                "-i",
                str(bed),
                "-filter_complex",
                "[0]volume=1.0[v];[1]volume=0.45[b];"
                "[v][b]amix=inputs=2:duration=first:dropout_transition=0[out]",
                "-map",
                "[out]",
                "-ar",
                str(SR),
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(mixed),
            ]
        )
        run_ff(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mixed),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "speech.mp3",
            ]
        )

    Path("teaser_timeline.json").write_text(
        json.dumps(
            {
                "total": round(t, 3),
                "timeline": timeline,
                "voice": VOICE,
                "rate": RATE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "OK speech.mp3", "voice", VOICE, "rate", RATE, "total", round(t, 2), "s"
    )


if __name__ == "__main__":
    asyncio.run(main())
