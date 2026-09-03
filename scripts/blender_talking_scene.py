"""
Blender headless Workbench scene (no GPU / no EGL required with xvfb).
Renders silent MP4; workflow muxes TTS audio with ffmpeg afterward.

  blender -b -noaudio -P blender_talking_scene.py -- --out out.mp4 --text Hello --seconds 4
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy


def parse_args(argv):
    args = {
        "out": "blender_silent.mp4",
        "text": "Talking Clip Factory",
        "fps": 24,
        "seconds": 4.0,
        "width": 960,
        "height": 540,
    }
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--out", "--text", "--seconds", "--width", "--height") and i + 1 < len(argv):
            key = argv[i][2:]
            if key in ("seconds",):
                args[key] = float(argv[i + 1])
            elif key in ("width", "height", "fps"):
                args[key] = int(argv[i + 1])
            else:
                args[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    for block in list(bpy.data.cameras):
        bpy.data.cameras.remove(block)


def make_mat(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = False
    mat.diffuse_color = (*color, 1.0)
    return mat


def build_scene(text: str, fps: int, total_frames: int, width: int, height: int):
    clear_scene()
    scene = bpy.context.scene

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    # Workbench display settings (when available)
    try:
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
    except Exception:
        pass

    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(make_mat("FloorMat", (0.08, 0.1, 0.16)))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 1.2))
    body = bpy.context.active_object
    body.name = "Body"
    body.data.materials.append(make_mat("BodyMat", (0.2, 0.75, 0.95)))

    for x in (-0.35, 0.35):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(x, -0.85, 1.45))
        bpy.context.active_object.data.materials.append(make_mat("EyeMat", (0.95, 0.95, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.9, 0.95))
    mouth = bpy.context.active_object
    mouth.name = "Mouth"
    mouth.scale = (0.45, 0.12, 0.08)
    mouth.data.materials.append(make_mat("MouthMat", (0.9, 0.25, 0.45)))

    bpy.ops.object.light_add(type="SUN", location=(2, -2, 6))
    bpy.context.active_object.data.energy = 2.0

    bpy.ops.object.camera_add(location=(0, -5.5, 2.2))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(75), 0, 0)
    scene.camera = cam

    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = False
    world.color = (0.03, 0.04, 0.08)

    for f in range(1, total_frames + 1):
        t = f / float(fps)
        body.location.z = 1.2 + 0.08 * math.sin(t * 6.0)
        body.keyframe_insert(data_path="location", frame=f, index=2)
        mouth.scale.z = 0.06 + 0.1 * abs(math.sin(t * 12.0))
        mouth.keyframe_insert(data_path="scale", frame=f, index=2)

    bpy.ops.object.text_add(location=(0, 0, 2.8))
    txt = bpy.context.active_object
    short = text[:72] + ("..." if len(text) > 72 else "")
    txt.data.body = short
    txt.data.align_x = "CENTER"
    txt.data.size = 0.32
    txt.rotation_euler = (math.radians(90), 0, 0)
    txt.data.materials.append(make_mat("TextMat", (0.85, 0.9, 1.0)))


def setup_render(out_path: Path):
    scene = bpy.context.scene
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

    build_scene(str(args["text"]), fps, total_frames, width, height)
    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    setup_render(out)

    print(f"Workbench silent render {total_frames}f {width}x{height} -> {out}")
    bpy.ops.render.render(animation=True)

    if out.exists() and out.stat().st_size > 0:
        print("OK", out, out.stat().st_size)
        return

    # Blender may write out0001-style names depending on settings
    matches = sorted(out.parent.glob(out.stem + "*"))
    print("Exact path missing; candidates:", matches)
    for m in matches:
        if m.suffix.lower() in (".mp4", ".mkv", ".avi") and m.stat().st_size > 0:
            m.rename(out)
            print("Renamed", m, "->", out)
            return
    raise SystemExit("Render produced no usable video file")


if __name__ == "__main__":
    main()
