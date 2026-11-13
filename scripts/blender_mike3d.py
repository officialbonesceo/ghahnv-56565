"""
Blender 3D Mike — load Tripo Mike.glb + classroom.
GLB is a STATIC mesh (no armature / morph targets), so motion is root-level:
walk-in-place bob, sway, present lean. True hand wave / blink / lips need a rig.

blender -b -noaudio -P scripts/blender_mike3d.py -- \
  --glb assets/mike/Mike.glb --out assets/blender/mike3d_test.mp4 \
  --seconds 6 --width 720 --height 1280
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector

HOODIE = (1.0, 0.80, 0.16)


def parse_args(argv):
    args = {
        "out": "assets/blender/mike3d_test.mp4",
        "fps": 24,
        "seconds": 6.0,
        "width": 720,
        "height": 1280,
        "glb": "assets/mike/Mike.glb",
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
            if key == "seconds":
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
    try:
        m.use_nodes = False
    except Exception:
        pass
    r, g, b = color
    if emit > 0:
        r = min(1.0, r + emit * 0.3)
        g = min(1.0, g + emit * 0.3)
        b = min(1.0, b + emit * 0.35)
    m.diffuse_color = (r, g, b, 1.0)
    return m


def mesh(op, **kw):
    getattr(bpy.ops.mesh, op)(**kw)
    obj = bpy.context.active_object
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def build_room():
    floor = mesh("primitive_plane_add", size=16, location=(0, 0, 0))
    floor.data.materials.append(mat("Floor", (0.40, 0.26, 0.15)))

    wall = mesh("primitive_cube_add", size=1, location=(0, 4.0, 2.4))
    wall.scale = (8, 0.15, 2.6)
    wall.data.materials.append(mat("Wall", (0.80, 0.88, 0.92)))

    stripe = mesh("primitive_cube_add", size=1, location=(0, 3.9, 0.5))
    stripe.scale = (7.5, 0.05, 0.16)
    stripe.data.materials.append(mat("Stripe", HOODIE, emit=0.2))

    for x in (-7.0, 7.0):
        sw = mesh("primitive_cube_add", size=1, location=(x, 0.5, 2.2))
        sw.scale = (0.12, 5.5, 2.4)
        sw.data.materials.append(mat("Side", (0.74, 0.82, 0.88)))

    ceil = mesh("primitive_plane_add", size=16, location=(0, 0.5, 4.8))
    ceil.rotation_euler = (math.radians(180), 0, 0)
    ceil.data.materials.append(mat("Ceil", (0.93, 0.95, 0.97)))

    for x in (-2.0, 2.0):
        lamp = mesh("primitive_cube_add", size=1, location=(x, 1.0, 4.65))
        lamp.scale = (1.0, 0.4, 0.05)
        lamp.data.materials.append(mat("Lamp", (1.0, 0.97, 0.85), emit=0.6))

    frame = mesh("primitive_cube_add", size=1, location=(0, 3.85, 2.6))
    frame.scale = (3.8, 0.1, 1.9)
    frame.data.materials.append(mat("Frame", (0.30, 0.18, 0.10)))
    board = mesh("primitive_cube_add", size=1, location=(0, 3.78, 2.6))
    board.scale = (3.5, 0.05, 1.7)
    board.data.materials.append(mat("Board", (0.15, 0.40, 0.28)))

    desk = mesh("primitive_cube_add", size=1, location=(0, -1.0, 0.55))
    desk.scale = (2.0, 0.7, 0.06)
    desk.data.materials.append(mat("Desk", (0.48, 0.32, 0.18)))
    for x in (-0.9, 0.9):
        for y in (-1.2, -0.8):
            leg = mesh("primitive_cylinder_add", radius=0.04, depth=0.55, location=(x, y, 0.27))
            leg.data.materials.append(mat("DLeg", (0.25, 0.16, 0.1)))

    rug = mesh("primitive_cylinder_add", radius=1.0, depth=0.025, location=(0, 0.9, 0.02))
    rug.data.materials.append(mat("Rug", (0.12, 0.22, 0.42)))


def import_mike_glb(glb_path: Path):
    if not glb_path.exists():
        raise SystemExit(f"Missing GLB: {glb_path}")

    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    after = [o for o in bpy.data.objects if o.name not in before]
    if not after:
        raise SystemExit("GLB import produced no objects")

    # Report capability (this Tripo export is static)
    has_armature = any(o.type == "ARMATURE" for o in after)
    mesh_objs = [o for o in after if o.type == "MESH"]
    morph_count = 0
    for o in mesh_objs:
        if o.data and getattr(o.data, "shape_keys", None):
            kb = o.data.shape_keys
            if kb and kb.key_blocks:
                morph_count += max(0, len(kb.key_blocks) - 1)
    print(
        "MIKE_CAPABILITY",
        "armature=" + str(has_armature),
        "meshes=" + str(len(mesh_objs)),
        "shape_keys=" + str(morph_count),
        "animations=" + str(len(bpy.data.actions)),
    )

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0.9, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    meshes = mesh_objs or after
    min_c = Vector((1e9, 1e9, 1e9))
    max_c = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max(0.01, max_c.z - min_c.z)
    scale = 1.75 / height

    for o in after:
        o.parent = root

    root.scale = (scale, scale, scale)
    root.location = (0, 0.9, -min_c.z * scale)
    root.rotation_euler = (0, 0, 0)

    print("MIKE_GLB", glb_path, "height", round(height, 3), "scale", round(scale, 3))
    return root, has_armature, morph_count


def setup_camera_lights():
    bpy.ops.object.light_add(type="SUN", location=(3, -4, 7))
    sun = bpy.context.active_object
    sun.data.energy = 2.8
    sun.rotation_euler = (math.radians(50), math.radians(12), 0)

    bpy.ops.object.light_add(type="AREA", location=(-2.5, -2, 3.5))
    fill = bpy.context.active_object
    fill.data.energy = 60
    fill.data.size = 3

    bpy.ops.object.light_add(type="AREA", location=(4, 1, 3))
    rim = bpy.context.active_object
    rim.data.energy = 40
    rim.data.size = 2

    bpy.ops.object.camera_add(location=(0, -3.6, 1.35))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(86), 0, 0)
    cam.data.lens = 35
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.58, 0.70, 0.80)


def animate_static_mesh(root, fps, total_frames):
    """Best-effort motion without bones: walk-in-place + present lean."""
    base_z = root.location.z
    base_y = root.location.y
    for f in range(1, total_frames + 1):
        t = f / float(fps)
        # Walk cycle phase (~2 steps/sec)
        phase = t * 2.0 * math.pi * 1.0
        # Vertical bob (walk)
        bob = 0.025 * abs(math.sin(phase))
        # Side lean + slight yaw (weight shift)
        lean = math.radians(4.0 * math.sin(phase))
        yaw = math.radians(6.0 * math.sin(phase * 0.5))
        # Present: lean toward camera a bit on the beat
        pitch = math.radians(3.0 + 2.0 * math.sin(t * 1.2))
        # Tiny forward/back shift
        y_shift = 0.02 * math.sin(phase)

        root.location = (0.0, base_y + y_shift, base_z + bob)
        root.rotation_euler = (pitch, lean, yaw)
        root.keyframe_insert(data_path="location", frame=f)
        root.keyframe_insert(data_path="rotation_euler", frame=f)

    # Smooth interpolation
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"


def setup_render_png(frame_dir: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_shadows = True
    except Exception:
        try:
            scene.display.shading.color_type = "MATERIAL"
        except Exception:
            pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(frame_dir / "frame_")


def frames_to_mp4(frame_dir: Path, out: Path, fps: int) -> None:
    frames = sorted(frame_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"No frames in {frame_dir}")
    list_file = frame_dir / "list.txt"
    list_file.write_text("".join(f"file '{f.resolve()}'\n" for f in frames), encoding="utf-8")
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-r",
            str(fps),
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )


def main():
    args = parse_args(sys.argv)
    fps = int(args.get("fps", 24))
    seconds = min(max(float(args["seconds"]), 1.0), 12.0)
    total_frames = max(fps, int(round(seconds * fps)))
    width = int(args.get("width", 720))
    height = int(args.get("height", 1280))
    glb = Path(args["glb"]).resolve()

    clear_scene()
    build_room()
    root, has_arm, morphs = import_mike_glb(glb)
    setup_camera_lights()
    animate_static_mesh(root, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        setup_render_png(frame_dir, fps, total_frames, width, height)
        print(f"Render Mike3D GLB {total_frames}f {width}x{height}")
        bpy.ops.render.render(animation=True)
        n = len(list(frame_dir.glob("frame_*.png")))
        print(f"frames={n}")
        if n < 1:
            raise SystemExit("No PNG frames written")
        frames_to_mp4(frame_dir, out, fps)

    if not (out.exists() and out.stat().st_size > 0):
        raise SystemExit("No video written")
    print("OK", out, out.stat().st_size)
    print(
        "NOTE: wave/blink/mouth need armature+shape keys. "
        "Current GLB is static mesh; used walk-in-place root motion only."
    )


if __name__ == "__main__":
    main()
