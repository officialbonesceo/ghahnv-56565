#!/usr/bin/env python3
"""Build SRT from script.txt and burn captions onto output.mp4 via ffmpeg."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def chunks(text: str, max_words: int = 7) -> list[str]:
    words = [w for w in (text or "").replace("\n", " ").split() if w.strip()]
    if not words:
        return []
    out, cur = [], []
    for w in words:
        cur.append(w)
        if (w.endswith((".", "!", "?", ",")) or len(cur) >= max_words) and len(cur) >= 3:
            out.append(" ".join(cur))
            cur = []
    if cur:
        if out and len(cur) <= 2:
            out[-1] = (out[-1] + " " + " ".join(cur)).strip()
        else:
            out.append(" ".join(cur))
    return out


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    video = Path("output.mp4")
    script = Path("script.txt")
    if not video.exists() or not script.exists():
        print("skip captions: missing output.mp4 or script.txt", file=sys.stderr)
        return
    text = script.read_text(encoding="utf-8").strip()
    parts = chunks(text, 7)
    if not parts:
        print("skip captions: empty script", file=sys.stderr)
        return
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, check=True,
        )
        duration = float(r.stdout.strip())
    except Exception as e:
        print("ffprobe fail", e, file=sys.stderr)
        return
    # Leave last ~2.6s for CTA card without competing text
    usable = max(3.0, duration - 2.6)
    slot = usable / len(parts)
    lines = []
    for i, phrase in enumerate(parts):
        start = i * slot
        end = min(usable, (i + 1) * slot - 0.05)
        if end <= start:
            end = start + 0.4
        safe = phrase.replace("\n", " ")
        lines.append(f"{i+1}\n{ts(start)} --> {ts(end)}\n{safe}\n")
    srt = Path("captions.srt")
    srt.write_text("\n".join(lines), encoding="utf-8")
    print("CAPTIONS", len(parts), "slots over", round(usable, 2), "s", file=sys.stderr)
    out = Path("output_captioned.mp4")
    # force_style: large white text, black box, bottom center
    vf = (
        f"subtitles={srt.name}:force_style="
        "'FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,"
        "Alignment=2,MarginV=180,Bold=1'"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", vf,
        "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
        print("ffmpeg captions fail", r.stderr[-600:], file=sys.stderr)
        return
    out.replace(video)
    print("CAPTIONS_OK", video.stat().st_size, file=sys.stderr)


if __name__ == "__main__":
    main()
