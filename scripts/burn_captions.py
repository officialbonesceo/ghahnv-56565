#!/usr/bin/env python3
"""Burn short bottom captions onto output.mp4 — readable on YT/TikTok, never cover Mike's face."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def chunks(text: str, max_words: int = 4) -> list[str]:
    words = [w for w in (text or "").replace("\n", " ").split() if w.strip()]
    if not words:
        return []
    out, cur = [], []
    for w in words:
        cur.append(w)
        hard = w.endswith((".", "!", "?"))
        soft = w.endswith(",") or len(cur) >= max_words
        if (hard or soft) and len(cur) >= 2:
            out.append(" ".join(cur))
            cur = []
    if cur:
        if out and len(cur) <= 2:
            out[-1] = (out[-1] + " " + " ".join(cur)).strip()
        else:
            out.append(" ".join(cur))
    cleaned = []
    for p in out:
        ws = p.split()
        while len(ws) > 5:
            cleaned.append(" ".join(ws[:4]))
            ws = ws[4:]
        if ws:
            cleaned.append(" ".join(ws))
    return cleaned


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(parts: list[str], duration: float, path: Path) -> None:
    usable = max(3.0, duration - 2.8)
    slot = usable / max(len(parts), 1)
    # Fontsize 52 on 1920 PlayRes ≈ readable on phone YT Shorts; MarginV keeps off face/board
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,48,48,96,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, phrase in enumerate(parts):
        start = i * slot
        end = min(usable, (i + 1) * slot - 0.04)
        if end <= start:
            end = start + 0.35
        safe = phrase.replace("\n", " ").replace("{", "(").replace("}", ")")
        events.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{safe}\n"
        )
    path.write_text(header + "".join(events), encoding="utf-8")


def main() -> None:
    video = Path("output.mp4")
    script = Path("script.txt")
    if not video.exists() or not script.exists():
        print("skip captions: missing output.mp4 or script.txt", file=sys.stderr)
        return
    text = script.read_text(encoding="utf-8").strip()
    text = re.sub(
        r"(?is)\s*(Tap the bookmark.*|Share it with a classmate.*|Follow for daily.*)$",
        "",
        text,
    ).strip()
    parts = chunks(text, 4)
    if not parts:
        print("skip captions: empty script", file=sys.stderr)
        return
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(video),
            ],
            capture_output=True, text=True, check=True,
        )
        duration = float(r.stdout.strip())
    except Exception as e:
        print("ffprobe fail", e, file=sys.stderr)
        return

    ass = Path("captions.ass")
    write_ass(parts, duration, ass)
    srt_lines = []
    usable = max(3.0, duration - 2.8)
    slot = usable / len(parts)

    def srt_ts(sec: float) -> str:
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

    for i, phrase in enumerate(parts):
        start = i * slot
        end = min(usable, (i + 1) * slot - 0.04)
        if end <= start:
            end = start + 0.35
        srt_lines.append(f"{i+1}\n{srt_ts(start)} --> {srt_ts(end)}\n{phrase}\n")
    Path("captions.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    print("CAPTIONS", len(parts), "bottom lines over", round(usable, 2), "s", file=sys.stderr)

    out = Path("output_captioned.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"ass={ass.name}",
        "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
        print("ffmpeg ass fail, trying subtitles fallback", (r.stderr or "")[-500:], file=sys.stderr)
        style = (
            "FontName=DejaVu Sans,FontSize=16,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=70,MarginL=50,MarginR=50,Bold=1"
        )
        vf = f"subtitles={Path('captions.srt').name}:force_style='{style}'"
        cmd2 = [
            "ffmpeg", "-y", "-i", str(video),
            "-vf", vf,
            "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out),
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True)
        if r2.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
            print("ffmpeg captions fail", (r2.stderr or "")[-600:], file=sys.stderr)
            return
    out.replace(video)
    print("CAPTIONS_OK", video.stat().st_size, file=sys.stderr)


if __name__ == "__main__":
    main()
