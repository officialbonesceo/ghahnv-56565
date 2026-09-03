"""Blender headless: simple 3D talking character. blender -b -P this.py -- --audio a.mp3 --out o.mp4 --text Hi"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy


def parse_args(argv):
    args = {"audio": None, "out": "blender_out.mp4", "text": "Talking Clip Factory", "fps": 24, "seconds": 4.0}
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--audio", "--out", "--text", "--seconds") and i + 1 < len(argv):
            key = argv[i][2:]
            args[key] = float(argv[i + 1]) if key == "seconds" else argv[i + 1]
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


def make_mat(name, color, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Emission Strength" in bsdf.inputs:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_scene(text: str, fps: int, total_frames: int):
    clear_scene()
    scene = bpy.context.scene
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames

    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(make_mat("FloorMat", (0.05, 0.07, 0.12)))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 1.2))
    body = bpy.context.active_object
    body.name = "Body"
    body.data.materials.append(make_mat("BodyMat", (0.15, 0.75, 0.95), emission=0.3))

    for x in (-0.35, 0.35):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(x, -0.85, 1.45))
        bpy.context.active_object.data.materials.append(make_mat("EyeMat", (0.95, 0.95, 1.0), emission=0.2))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -0.9, 0.95))
    mouth = bpy.context.active_object
    mouth.name = "Mouth"
    mouth.scale = (0.45, 0.12, 0.08)
    mouth.data.materials.append(make_mat("MouthMat", (0.9, 0.2, 0.45), emission=0.15))

    bpy.ops.object.light_add(type="AREA", location=(2, -2, 4))
    bpy.context.active_object.data.energy = 80

    bpy.ops.object.camera_add(location=(0, -5.5, 2.2))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(75), 0, 0)
    scene.camera = cam

    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.03, 0.06, 1.0)
    bg.inputs[1].default_value = 0.6

    for f in range(1, total_frames + 1):
        t = f / fps
        body.location.z = 1.2 + 0.08 * math.sin(t * 6.0)
        body.keyframe_insert(data_path="location", frame=f, index=2)
        mouth.scale.z = 0.06 + 0.1 * abs(math.sin(t * 12.0))
        mouth.keyframe_insert(data_path="scale", frame=f, index=2)

    bpy.ops.object.text_add(location=(0, 0, 2.8))
    txt = bpy.context.active_object
    txt.data.body = text[:80] + ("..." if len(text) > 80 else "")
    txt.data.align_x = "CENTER"
    txt.data.size = 0.35
    txt.rotation_euler = (math.radians(90), 0, 0)
    txt.data.materials.append(make_mat("TextMat", (0.8, 0.85, 1.0), emission=0.5))


def setup_render(out_path: Path, audio_path):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "AAC"
    scene.render.filepath = str(out_path)

    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "BLENDER_WORKBENCH"

    if audio_path and Path(audio_path).exists():
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        se = scene.sequence_editor
        for s in list(se.sequences_all):
            se.sequences.remove(s)
        se.sequences.new_sound("Narration", audio_path, 1, 1)


def main():
    args = parse_args(sys.argv)
    fps = 24
    seconds = min(float(args["seconds"]), 12.0)
    total_frames = max(fps, int(seconds * fps))
    build_scene(str(args["text"]), fps, total_frames)
    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    setup_render(out, args["audio"])
    print(f"Rendering {total_frames} frames -> {out}")
    bpy.ops.render.render(animation=True)
    print("Blender render done")


if __name__ == "__main__":
    main()
