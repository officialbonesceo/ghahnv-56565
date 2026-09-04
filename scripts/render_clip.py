#!/usr/bin/env python3
"""Text -> Edge TTS -> speech.mp3 only (no --out video flag)."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path


async def synthesize(text: str, voice: str, mp3_path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice).save(str(mp3_path))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--voice", default="en-US-GuyNeural")
    parser.add_argument("--audio-out", default="speech.mp3")
    args = parser.parse_args()
    text = args.text.strip()[:800]
    audio = Path(args.audio_out).resolve()
    audio.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(synthesize(text, args.voice, audio))
    if not audio.exists() or audio.stat().st_size < 100:
        raise SystemExit("TTS produced empty audio")
    print(f"Audio: {audio} ({audio.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
