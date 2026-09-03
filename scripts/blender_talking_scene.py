"""
Profile 3 — simplified cyber host + Rhubarb mouth cues.
Workbench-friendly for GitHub Actions (xvfb).

blender -b -noaudio -P blender_talking_scene.py -- \
  --out silent.mp4 --text Hello --seconds 4 --cues mouth.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

# Rhubarb mouth values -> relative mouth open / width
CUE_SCALE = {
    "X": (0.45, 0.10, 0.04),  # rest / closed
    "A": (0.55, 0.12, 0.22),  # wide open
    "B": (0.42, 0.14, 0.05),  # lips together
    "C": (0.50, 0.12, 0.12),
    "D": (0.52, 0.12, 0.16),
    "E": (0.58, 0.11, 0.18),
    "F": (0.48, 0.13, 0.10),
    "G": (0.54, 0.12, 0.20),
    "H": (0.56, 0.11, 0.24),
}


def parse_args(argv):
    args = {
        "out": "blender_silent.mp4",
        "text": "Talking Clip Factory",
        "fps": 24,
        "seconds": 4.0,
        "width": 960,
        "height": 540,
        "cues": None,
    }
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:]
            val = argv[i + 1]
            if key in ("seconds",):
                args[key] = float(val)
            elif key in ("width", "height", "fps"):
                args[key] = int(val)
            else:
                args[key] = val
            i += 2
        else:
            i += 1
    return args


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(coll):
            coll.remove(block)


def mat(name, color, emit=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = False
    m.diffuse_color = (*color, 1.0)
    # Workbench uses diffuse; emission approximated by brighter color
    if emit > 0:
        m.diffuse_color = (
            min(1.0, color[0] + emit * 0.5),
            min(1.0, color[1] + emit * 0.5),
            min(1.0, color[2] + emit * 0.8),
            1.0,
        )
    return m


def add_mesh(op, **kw):
    getattr(bpy.ops.mesh, op)(**kw)
    return bpy.context.active_object


def build_cyber_host():
    """Simplified Profile-3 cyber host: head, body, jacket lines, headset, mouth."""
    # Torso / jacket
    body = add_mesh("primitive_cube_add", size=1.0, location=(0, 0.15, 0.55))
    body.name = "Torso"
    body.scale = (0.85, 0.45, 0.9)
    body.data.materials.append(mat("Jacket", (0.05, 0.07, 0.12)))

    # Cyan collar strip
    strip = add_mesh("primitive_cube_add", size=1.0, location=(0, -0.28, 1.05))
    strip.scale = (0.7, 0.08, 0.06)
    strip.data.materials.append(mat("CyanStrip", (0.1, 0.75, 1.0), emit=0.6))

    # Neck
    neck = add_mesh("primitive_cylinder_add", radius=0.18, depth=0.25, location=(0, 0, 1.15))
    neck.data.materials.append(mat("Skin", (0.55, 0.58, 0.62)))

    # Head
    head = add_mesh("primitive_uv_sphere_add", radius=0.55, location=(0, 0, 1.7))
    head.name = "Head"
    head.scale = (0.95, 1.0, 1.1)
    head.data.materials.append(mat("SkinHead", (0.6, 0.63, 0.68)))

    # Hair cap
    hair = add_mesh("primitive_uv_sphere_add", radius=0.58, location=(0, 0.05, 1.85))
    hair.scale = (0.95, 1.05, 0.7)
    hair.data.materials.append(mat("Hair", (0.12, 0.14, 0.2)))

    # Eyes
    eyes = []
    for x in (-0.18, 0.18):
        eye = add_mesh("primitive_uv_sphere_add", radius=0.09, location=(x, -0.48, 1.75))
        eye.data.materials.append(mat("EyeWhite", (0.9, 0.95, 1.0)))
        pupil = add_mesh("primitive_uv_sphere_add", radius=0.05, location=(x, -0.55, 1.75))
        pupil.data.materials.append(mat("CyanEye", (0.15, 0.85, 1.0), emit=0.8))
        eyes.append(eye)

    # Mouth (driven by lip sync)
    mouth = add_mesh("primitive_cube_add", size=1.0, location=(0, -0.5, 1.45))
    mouth.name = "Mouth"
    mouth.scale = CUE_SCALE["X"]
    mouth.data.materials.append(mat("Mouth", (0.35, 0.12, 0.2)))

    # Headset band
    band = add_mesh("primitive_torus_add", major_radius=0.58, minor_radius=0.04, location=(0, 0, 1.72))
    band.rotation_euler = (math.radians(90), 0, 0)
    band.data.materials.append(mat("Headset", (0.08, 0.1, 0.14)))

    # Ear cup L
    cup = add_mesh("primitive_cylinder_add", radius=0.12, depth=0.08, location=(-0.58, 0, 1.7))
    cup.rotation_euler = (0, math.radians(90), 0)
    cup.data.materials.append(mat("Cup", (0.1, 0.12, 0.16)))

    # Boom mic
    boom = add_mesh("primitive_cylinder_add", radius=0.02, depth=0.45, location=(-0.35, -0.35, 1.55))
    boom.rotation_euler = (math.radians(70), 0, math.radians(20))
    boom.data.materials.append(mat("Boom", (0.15, 0.7, 0.95), emit=0.4))
    tip = add_mesh("primitive_uv_sphere_add", radius=0.04, location=(-0.22, -0.52, 1.42))
    tip.data.materials.append(mat("MicTip", (0.2, 0.8, 1.0), emit=0.7))

    # Light + camera
    sun = add_mesh  # placeholder quiet
    bpy.ops.object.light_add(type="SUN", location=(3, -4, 8))
    bpy.context.active_object.data.energy = 2.5

    bpy.ops.object.light_add(type="AREA", location=(-2, -3, 3))
    bpy.context.active_object.data.energy = 40

    bpy.ops.object.camera_add(location=(0, -3.8, 1.65))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(88), 0, 0)
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.02, 0.03, 0.06)

    return mouth


def load_cues(path):
    if not path or not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("mouthCues") or data.get("mouth_cues") or []


def apply_lip_sync(mouth, cues, fps, total_frames):
    if not cues:
        # gentle idle chatter if no cues
        for f in range(1, total_frames + 1):
            t = f / float(fps)
            open_z = 0.04 + 0.08 * abs(math.sin(t * 10.0))
            mouth.scale = (0.45, 0.10, open_z)
            mouth.keyframe_insert(data_path="scale", frame=f)
        return

    # Keyframe at each cue boundary
    for cue in cues:
        start = float(cue.get("start", 0))
        end = float(cue.get("end", start))
        value = str(cue.get("value", "X")).upper()
        sx, sy, sz = CUE_SCALE.get(value, CUE_SCALE["X"])
        f0 = max(1, int(round(start * fps)) + 1)
        f1 = max(f0, int(round(end * fps)) + 1)
        mouth.scale = (sx, sy, sz)
        mouth.keyframe_insert(data_path="scale", frame=f0)
        mouth.keyframe_insert(data_path="scale", frame=f1)

    # Hold rest at end
    mouth.scale = CUE_SCALE["X"]
    mouth.keyframe_insert(data_path="scale", frame=total_frames)


def setup_render(out_path: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = str(out_path)


def main():
    args = parse_args(sys.argv)
    fps = 24
    seconds = min(max(float(args["seconds"]), 1.0), 12.0)
    total_frames = max(fps, int(round(seconds * fps)))
    width = int(args.get("width", 960))
    height = int(args.get("height", 540))

    clear_scene()
    mouth = build_cyber_host()
    cues = load_cues(args.get("cues"))
    print(f"Loaded {len(cues)} mouth cues")
    apply_lip_sync(mouth, cues, fps, total_frames)

    # Subtle head bob
    head = bpy.data.objects.get("Head")
    if head:
        for f in range(1, total_frames + 1):
            t = f / float(fps)
            head.location.z = 1.7 + 0.02 * math.sin(t * 3.0)
            head.keyframe_insert(data_path="location", frame=f, index=2)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    setup_render(out, fps, total_frames, width, height)
    print(f"Render {total_frames}f -> {out}")
    bpy.ops.render.render(animation=True)
    if not (out.exists() and out.stat().st_size > 0):
        matches = sorted(out.parent.glob(out.stem + "*"))
        for m in matches:
            if m.suffix.lower() == ".mp4" and m.stat().st_size > 0:
                m.rename(out)
                break
    if not out.exists():
        raise SystemExit("No video written")
    print("OK", out.stat().st_size)


if __name__ == "__main__":
    main()
