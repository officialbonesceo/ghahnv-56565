#!/usr/bin/env python3
"""Text -> Edge TTS (faster rate) -> speech.mp3"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path


async def synthesize(text: str, voice: str, rate: str, mp3_path: Path) -> None:
    import edge_tts

    # rate e.g. "+25%" keeps energy up for TikTok
    await edge_tts.Communicate(text, voice, rate=rate).save(str(mp3_path))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--voice", default="en-US-ChristopherNeural")
    parser.add_argument("--rate", default="+22%")
    parser.add_argument("--audio-out", default="speech.mp3")
    args = parser.parse_args()
    text = args.text.strip()[:2200]
    audio = Path(args.audio_out).resolve()
    audio.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(synthesize(text, args.voice, args.rate, audio))
    if not audio.exists() or audio.stat().st_size < 100:
        raise SystemExit("TTS produced empty audio")
    print(f"Audio: {audio} ({audio.stat().st_size} bytes) voice={args.voice} rate={args.rate}")


if __name__ == "__main__":
    main()
