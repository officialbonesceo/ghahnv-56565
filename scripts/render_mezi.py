#!/usr/bin/env python3
"""MEZI 2D: audio + Rhubarb cues + poses -> mp4"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mezi_draw import draw_background, draw_mezi, expression_from_pose, mouth_from_cue


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return max(0.8, float(out))


def load_cues(path: Path | None):
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def cue_at(cues, t: float) -> str:
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            return str(c.get("value", "X"))
    return "X"


def pose_at(t: float, duration: float, actions: list[str]) -> str:
    if not actions:
        actions = ["idle"]
    norm = []
    for a in actions:
        a = a.strip().lower()
        if a in ("walk", "walking"):
            norm.extend(["walk1", "walk2", "walk1", "walk2"])
        elif a in ("talk", "talking"):
            norm.append("idle")
        else:
            norm.append(a if a in ("idle", "point", "laugh", "walk1", "walk2") else "idle")
    if not norm:
        norm = ["idle"]
    seg = duration / len(norm)
    idx = min(int(t / seg), len(norm) - 1)
    return norm[idx]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--cues", default=None)
    p.add_argument("--out", default="output_mezi.mp4")
    p.add_argument("--room", default="studio", choices=["studio", "tech", "science"])
    p.add_argument("--actions", default="idle,talk")
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--width", type=int, default=960)
    p.add_argument("--height", type=int, default=540)
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        sys.exit("missing audio")
    duration = min(probe_duration(audio), 20.0)
    cues = load_cues(Path(args.cues) if args.cues else None)
    actions = [a for a in args.actions.split(",") if a.strip()]
    fps = max(8, min(args.fps, 24))
    nframes = max(fps, int(duration * fps))
    bg = draw_background(args.width, args.height, args.room)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i in range(nframes):
            t = i / fps
            mouth = mouth_from_cue(cue_at(cues, t))
            pose = pose_at(t, duration, actions)
            expr = expression_from_pose(pose)
            frame = draw_mezi(bg, mouth=mouth, expression=expr, pose=pose)
            frame.save(td / f"frame_{i:05d}.png")
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", str(td / "frame_%05d.png"), "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", str(out),
        ])
        print(f"OK {out} frames={nframes} cues={len(cues)}")


if __name__ == "__main__":
    main()
