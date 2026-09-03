"""
Blender director: open cyber_host.blend, apply actions + Rhubarb, render silent mp4.

blender -b assets/cyber_host.blend -P scripts/director_render.py -- \
  --out silent.mp4 --seconds 5 --cues mouth.json --actions talk,nod,gesture
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

CUE_SCALE = {
    "X": (0.35, 0.08, 0.04),
    "A": (0.42, 0.1, 0.18),
    "B": (0.34, 0.1, 0.05),
    "C": (0.38, 0.09, 0.1),
    "D": (0.4, 0.09, 0.14),
    "E": (0.44, 0.09, 0.16),
    "F": (0.36, 0.1, 0.09),
    "G": (0.41, 0.09, 0.17),
    "H": (0.43, 0.09, 0.2),
}


def parse_args(argv):
    args = {
        "out": "blender_silent.mp4",
        "seconds": 4.0,
        "fps": 24,
        "cues": None,
        "actions": "talk,idle",
        "width": 960,
        "height": 540,
    }
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            k = argv[i][2:]
            v = argv[i + 1]
            if k == "seconds":
                args[k] = float(v)
            elif k in ("fps", "width", "height"):
                args[k] = int(v)
            else:
                args[k] = v
            i += 2
        else:
            i += 1
    return args


def load_cues(path):
    if not path or not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("mouthCues") or []


def apply_mouth(cues, fps, total_frames):
    mouth = bpy.data.objects.get("Mouth")
    if not mouth:
        return
    if not cues:
        for f in range(1, total_frames + 1):
            t = f / float(fps)
            mouth.scale = (0.35, 0.08, 0.04 + 0.06 * abs(math.sin(t * 11)))
            mouth.keyframe_insert("scale", frame=f)
        return
    for cue in cues:
        start = float(cue.get("start", 0))
        end = float(cue.get("end", start))
        val = str(cue.get("value", "X")).upper()
        scale = CUE_SCALE.get(val, CUE_SCALE["X"])
        f0 = max(1, int(round(start * fps)) + 1)
        f1 = max(f0, int(round(end * fps)) + 1)
        mouth.scale = scale
        mouth.keyframe_insert("scale", frame=f0)
        mouth.keyframe_insert("scale", frame=f1)
    mouth.scale = CUE_SCALE["X"]
    mouth.keyframe_insert("scale", frame=total_frames)


def apply_actions(actions, fps, total_frames):
    head = bpy.data.objects.get("Head")
    arm_l = bpy.data.objects.get("ArmL")
    arm_r = bpy.data.objects.get("ArmR")
    hair = bpy.data.objects.get("Hair")
    acts = {a.strip().lower() for a in actions.split(",") if a.strip()}

    for f in range(1, total_frames + 1):
        t = f / float(fps)
        # idle breathe
        z_off = 0.0
        if "idle" in acts or "talk" in acts:
            z_off += 0.015 * math.sin(t * 2.5)
        if "nod" in acts:
            # nod mid-clip
            phase = (f / total_frames)
            if 0.3 < phase < 0.6:
                z_off += -0.04 * math.sin((phase - 0.3) / 0.3 * math.pi)
        if head:
            base = 1.95
            head.location.z = base + z_off
            head.keyframe_insert("location", frame=f, index=2)
        if hair:
            hair.location.z = 2.05 + z_off
            hair.keyframe_insert("location", frame=f, index=2)

        if "gesture" in acts and arm_r:
            # lift right arm slightly in second half
            phase = f / total_frames
            lift = 0.15 * max(0.0, math.sin((phase - 0.4) * math.pi)) if phase > 0.4 else 0.0
            arm_r.location.z = 1.0 + lift
            arm_r.keyframe_insert("location", frame=f, index=2)

        if "walk" in acts and head:
            # stylized sway (not a real walk cycle)
            head.location.x = 0.03 * math.sin(t * 6.0)
            head.keyframe_insert("location", frame=f, index=0)


def setup_render(out: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = str(out)
    if scene.camera is None and "RenderCam" in bpy.data.objects:
        scene.camera = bpy.data.objects["RenderCam"]


def main():
    args = parse_args(sys.argv)
    fps = int(args["fps"])
    seconds = min(max(float(args["seconds"]), 1.0), 12.0)
    total_frames = max(fps, int(round(seconds * fps)))
    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cues = load_cues(args.get("cues"))
    print("cues", len(cues), "actions", args["actions"])
    apply_mouth(cues, fps, total_frames)
    apply_actions(args["actions"], fps, total_frames)
    setup_render(out, fps, total_frames, int(args["width"]), int(args["height"]))
    bpy.ops.render.render(animation=True)
    if not out.exists():
        for m in sorted(out.parent.glob(out.stem + "*")):
            if m.suffix.lower() == ".mp4" and m.stat().st_size > 0:
                m.rename(out)
                break
    if not out.exists():
        raise SystemExit("render failed")
    print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
