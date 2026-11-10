"""
Blender 3D Mike + classroom environment (test pipeline).
Seeded short take for CI.

blender -b -noaudio -P blender_mike3d.py -- \
  --out assets/blender/mike3d_test.mp4 --seconds 4 --width 720 --height 1280
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy


def parse_args(argv):
    args = {
        "out": "assets/blender/mike3d_test.mp4",
        "fps": 24,
        "seconds": 4.0,
        "width": 720,
        "height": 1280,
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
    r, g, b = color
    if emit > 0:
        r = min(1.0, r + emit * 0.4)
        g = min(1.0, g + emit * 0.4)
        b = min(1.0, b + emit * 0.5)
    m.diffuse_color = (r, g, b, 1.0)
    return m


def add_mesh(op, **kw):
    getattr(bpy.ops.mesh, op)(**kw)
    return bpy.context.active_object


def build_classroom():
    # Floor
    floor = add_mesh("primitive_plane_add", size=12, location=(0, 0, 0))
    floor.name = "Floor"
    floor.data.materials.append(mat("FloorWood", (0.35, 0.22, 0.12)))

    # Back wall
    wall = add_mesh("primitive_cube_add", size=1, location=(0, 3.2, 2.2))
    wall.scale = (6, 0.15, 2.4)
    wall.data.materials.append(mat("Wall", (0.82, 0.86, 0.9)))

    # Side walls
    for x in (-5.5, 5.5):
        sw = add_mesh("primitive_cube_add", size=1, location=(x, 0.5, 2.0))
        sw.scale = (0.12, 4.5, 2.2)
        sw.data.materials.append(mat("SideWall", (0.75, 0.8, 0.85)))

    # Board frame + surface
    frame = add_mesh("primitive_cube_add", size=1, location=(0, 3.0, 2.4))
    frame.scale = (3.4, 0.08, 1.7)
    frame.data.materials.append(mat("BoardFrame", (0.25, 0.18, 0.1)))
    board = add_mesh("primitive_cube_add", size=1, location=(0, 2.92, 2.4))
    board.scale = (3.1, 0.04, 1.5)
    board.data.materials.append(mat("ChalkBoard", (0.12, 0.32, 0.2)))

    # Desk
    desk = add_mesh("primitive_cube_add", size=1, location=(0, -0.2, 0.55))
    desk.scale = (1.6, 0.7, 0.08)
    desk.data.materials.append(mat("Desk", (0.4, 0.28, 0.16)))
    for x in (-0.7, 0.7):
        leg = add_mesh("primitive_cylinder_add", radius=0.05, depth=0.55, location=(x, -0.4, 0.28))
        leg.data.materials.append(mat("Leg", (0.2, 0.15, 0.1)))

    # Window light panel
    win = add_mesh("primitive_cube_add", size=1, location=(-4.8, 1.0, 2.2))
    win.scale = (0.05, 1.2, 1.0)
    win.data.materials.append(mat("Window", (0.7, 0.85, 1.0), emit=0.5))


def build_mike():
    """Reusable stylized 3D Mike (tutor character)."""
    # Legs
    for x in (-0.18, 0.18):
        leg = add_mesh("primitive_cylinder_add", radius=0.11, depth=0.7, location=(x, 1.1, 0.4))
        leg.data.materials.append(mat("Pants", (0.12, 0.18, 0.35)))

    # Torso
    torso = add_mesh("primitive_cube_add", size=1, location=(0, 1.1, 1.05))
    torso.name = "MikeTorso"
    torso.scale = (0.55, 0.28, 0.55)
    torso.data.materials.append(mat("Shirt", (0.15, 0.45, 0.85)))

    # Arms
    for x, rot in ((-0.55, 15), (0.55, -15)):
        arm = add_mesh("primitive_cylinder_add", radius=0.08, depth=0.55, location=(x, 1.05, 1.05))
        arm.rotation_euler = (0, math.radians(rot), 0)
        arm.data.materials.append(mat("SkinArm", (0.72, 0.55, 0.42)))

    # Neck + head
    neck = add_mesh("primitive_cylinder_add", radius=0.1, depth=0.15, location=(0, 1.1, 1.4))
    neck.data.materials.append(mat("SkinNeck", (0.72, 0.55, 0.42)))
    head = add_mesh("primitive_uv_sphere_add", radius=0.28, location=(0, 1.1, 1.72))
    head.name = "MikeHead"
    head.scale = (0.95, 1.0, 1.05)
    head.data.materials.append(mat("SkinHead", (0.74, 0.56, 0.43)))

    # Hair
    hair = add_mesh("primitive_uv_sphere_add", radius=0.3, location=(0, 1.12, 1.85))
    hair.scale = (0.95, 1.05, 0.65)
    hair.data.materials.append(mat("Hair", (0.08, 0.06, 0.05)))

    # Eyes
    for x in (-0.09, 0.09):
        eye = add_mesh("primitive_uv_sphere_add", radius=0.045, location=(x, 0.88, 1.75))
        eye.data.materials.append(mat("Eye", (0.95, 0.95, 0.98)))
        pupil = add_mesh("primitive_uv_sphere_add", radius=0.025, location=(x, 0.85, 1.75))
        pupil.data.materials.append(mat("Pupil", (0.05, 0.05, 0.08)))

    # Smile / mouth
    mouth = add_mesh("primitive_cube_add", size=1, location=(0, 0.86, 1.58))
    mouth.name = "MikeMouth"
    mouth.scale = (0.1, 0.03, 0.03)
    mouth.data.materials.append(mat("Mouth", (0.45, 0.18, 0.2)))

    # Badge on chest
    badge = add_mesh("primitive_cylinder_add", radius=0.08, depth=0.03, location=(0.2, 0.85, 1.15))
    badge.rotation_euler = (math.radians(90), 0, 0)
    badge.data.materials.append(mat("Badge", (1.0, 0.75, 0.15), emit=0.3))

    return head, mouth


def setup_camera_lights():
    bpy.ops.object.light_add(type="SUN", location=(2, -3, 6))
    bpy.context.active_object.data.energy = 2.2
    bpy.ops.object.light_add(type="AREA", location=(-2, -2, 3))
    bpy.context.active_object.data.energy = 50

    bpy.ops.object.camera_add(location=(0, -4.2, 1.6))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(88), 0, 0)
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.55, 0.65, 0.75)


def animate_mike(head, mouth, fps, total_frames):
    for f in range(1, total_frames + 1):
        t = f / float(fps)
        # head bob + slight turn
        head.location.z = 1.72 + 0.025 * math.sin(t * 3.2)
        head.rotation_euler = (0, 0, math.radians(4 * math.sin(t * 1.5)))
        head.keyframe_insert(data_path="location", frame=f, index=2)
        head.keyframe_insert(data_path="rotation_euler", frame=f, index=2)
        # mouth chatter
        open_z = 0.025 + 0.04 * abs(math.sin(t * 9.0))
        mouth.scale = (0.1, 0.03, open_z)
        mouth.keyframe_insert(data_path="scale", frame=f)


def setup_render(out_path: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
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
    fps = int(args.get("fps", 24))
    seconds = min(max(float(args["seconds"]), 1.0), 8.0)
    total_frames = max(fps, int(round(seconds * fps)))
    width = int(args.get("width", 720))
    height = int(args.get("height", 1280))

    clear_scene()
    build_classroom()
    head, mouth = build_mike()
    setup_camera_lights()
    animate_mike(head, mouth, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    setup_render(out, fps, total_frames, width, height)
    print(f"Render Mike3D {total_frames}f {width}x{height} -> {out}")
    bpy.ops.render.render(animation=True)
    if not (out.exists() and out.stat().st_size > 0):
        matches = sorted(out.parent.glob(out.stem + "*"))
        for m in matches:
            if m.suffix.lower() == ".mp4" and m.stat().st_size > 0:
                m.rename(out)
                break
    if not out.exists():
        raise SystemExit("No video written")
    print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
