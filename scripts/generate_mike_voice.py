#!/usr/bin/env python3
"""Generate Mike teaching voice with Kokoro TTS (CPU). Fallback: edge-tts."""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

DEFAULT_TEXT = (
    "Hey! I'm Mike. Coding is how we give computers step-by-step instructions. "
    "You write rules in a language the computer understands, and it follows them. "
    "Start small, practice every day, and you can build apps, games, and tools. "
    "Let's learn together!"
)


def synth_kokoro(text: str, out_wav: Path, voice: str = "am_michael") -> bool:
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
    except Exception as e:
        print("KOKORO_IMPORT_FAIL", e)
        return False

    # lang_code 'a' = American English
    pipeline = KPipeline(lang_code="a")
    chunks = []
    for _gs, _ps, audio in pipeline(text, voice=voice, speed=1.0):
        chunks.append(audio)
    if not chunks:
        print("KOKORO_EMPTY")
        return False
    audio = np.concatenate(chunks)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), audio, 24000)
    print("KOKORO_OK", out_wav, out_wav.stat().st_size, "voice", voice)
    return True


def synth_edge(text: str, out_wav: Path) -> bool:
    try:
        import edge_tts
    except Exception as e:
        print("EDGE_IMPORT_FAIL", e)
        return False

    out_mp3 = out_wav.with_suffix(".mp3")

    async def _run():
        # Clear male teaching voice
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        await communicate.save(str(out_mp3))

    try:
        asyncio.run(_run())
    except Exception as e:
        print("EDGE_FAIL", e)
        return False

    if not out_mp3.exists():
        return False
    # Convert to wav for consistent mux
    subprocess.check_call([
        "ffmpeg", "-y", "-i", str(out_mp3),
        "-ar", "24000", "-ac", "1", str(out_wav),
    ])
    print("EDGE_OK", out_wav, out_wav.stat().st_size)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=DEFAULT_TEXT)
    ap.add_argument("--out", default="assets/blender/mike_voice.wav")
    ap.add_argument("--voice", default="am_michael")
    args = ap.parse_args()
    out = Path(args.out)
    text = args.text.strip()
    if not text:
        text = DEFAULT_TEXT

    ok = synth_kokoro(text, out, voice=args.voice)
    if not ok:
        print("FALLBACK edge-tts")
        ok = synth_edge(text, out)
    if not ok:
        raise SystemExit("TTS failed")
    # duration probe
    try:
        r = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(out),
        ], text=True).strip()
        print("VOICE_DURATION", r)
    except Exception:
        pass


if __name__ == "__main__":
    main()
