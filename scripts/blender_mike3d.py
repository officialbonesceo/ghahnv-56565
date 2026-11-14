"""
Blender 3D Mike — Mixamo-rigged GLB, close teaching shot.
Cleaner poses: real raised-arm wave, calm head, less rubber stretch.
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Euler, Vector


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
    for coll in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.armatures,
        bpy.data.actions,
    ):
        for block in list(coll):
            try:
                coll.remove(block)
            except Exception:
                pass


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
    floor.data.materials.append(mat("Floor", (0.42, 0.28, 0.16)))

    wall = mesh("primitive_cube_add", size=1, location=(0, 3.2, 2.2))
    wall.scale = (6, 0.12, 2.5)
    wall.data.materials.append(mat("Wall", (0.82, 0.88, 0.92)))

    for x in (-5.5, 5.5):
        sw = mesh("primitive_cube_add", size=1, location=(x, 0.8, 2.0))
        sw.scale = (0.1, 4.0, 2.3)
        sw.data.materials.append(mat("Side", (0.76, 0.84, 0.90)))

    ceil = mesh("primitive_plane_add", size=16, location=(0, 0.5, 4.4))
    ceil.rotation_euler = (math.radians(180), 0, 0)
    ceil.data.materials.append(mat("Ceil", (0.94, 0.96, 0.98)))

    for x in (-1.5, 1.5):
        lamp = mesh("primitive_cube_add", size=1, location=(x, 1.0, 4.25))
        lamp.scale = (0.9, 0.35, 0.04)
        lamp.data.materials.append(mat("Lamp", (1.0, 0.97, 0.88), emit=0.7))

    frame = mesh("primitive_cube_add", size=1, location=(0, 3.05, 2.35))
    frame.scale = (3.2, 0.08, 1.7)
    frame.data.materials.append(mat("Frame", (0.28, 0.16, 0.08)))
    board = mesh("primitive_cube_add", size=1, location=(0, 2.98, 2.35))
    board.scale = (2.95, 0.04, 1.5)
    board.data.materials.append(mat("Board", (0.14, 0.38, 0.26)))

    rug = mesh("primitive_cylinder_add", radius=0.9, depth=0.02, location=(0, 0.5, 0.015))
    rug.data.materials.append(mat("Rug", (0.12, 0.22, 0.40)))


def bone_map(arm_obj):
    m = {}
    for pb in arm_obj.pose.bones:
        n = pb.name
        m[n] = pb
        if ":" in n:
            m[n.split(":", 1)[1]] = pb
        m[n.replace("mixamorig:", "")] = pb
    return m


def find_armature_and_mesh(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    meshes = [o for o in objects if o.type == "MESH"]
    arm = arms[0] if arms else None
    body = None
    if arm and meshes:
        for mo in meshes:
            if any(m.type == "ARMATURE" and m.object == arm for m in mo.modifiers):
                body = mo
                break
        if body is None:
            body = max(meshes, key=lambda o: len(o.data.vertices) if o.data else 0)
    elif meshes:
        body = meshes[0]
    return arm, body, meshes


def import_mike_glb(glb_path: Path):
    if not glb_path.exists():
        raise SystemExit(f"Missing GLB: {glb_path}")

    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    after = [o for o in bpy.data.objects if o.name not in before]
    if not after:
        raise SystemExit("GLB import produced no objects")

    arm, body, meshes = find_armature_and_mesh(after)
    print(
        "MIKE_CAPABILITY",
        "armature=" + str(bool(arm)),
        "meshes=" + str(len(meshes)),
        "bones=" + str(len(arm.pose.bones) if arm else 0),
    )

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0.5, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    min_c = Vector((1e9, 1e9, 1e9))
    max_c = Vector((-1e9, -1e9, -1e9))
    for o in meshes or after:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max(0.01, max_c.z - min_c.z)
    scale = 1.95 / height

    if arm and arm.parent is None:
        arm.parent = root
    for o in after:
        if o.parent is None:
            o.parent = root

    root.scale = (scale, scale, scale)
    root.location = (0, 0.55, -min_c.z * scale)
    root.rotation_euler = (0, 0, 0)

    # Soften extreme mesh stretch from skinning
    if arm:
        for mod in list(getattr(body, "modifiers", []) if body else []):
            if mod.type == "ARMATURE":
                try:
                    mod.use_deform_preserve_volume = True
                except Exception:
                    pass

    print("MIKE_GLB height", round(height, 3), "scale", round(scale, 3))
    return root, arm, body


def add_facial_shape_keys(body):
    if body is None or body.type != "MESH":
        return

    me = body.data
    if me.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)

    coords = [v.co.copy() for v in me.vertices]
    if not coords:
        return
    zs = [c.z for c in coords]
    ys = [c.y for c in coords]
    xs = [c.x for c in coords]
    zmin, zmax = min(zs), max(zs)
    ymin, ymax = min(ys), max(ys)
    xmin, xmax = min(xs), max(xs)
    zspan = max(1e-6, zmax - zmin)
    yspan = max(1e-6, ymax - ymin)

    mouth = body.shape_key_add(name="mouth_open", from_mix=False)
    blink = body.shape_key_add(name="blink", from_mix=False)

    for i, _v in enumerate(me.vertices):
        c = coords[i]
        zn = (c.z - zmin) / zspan
        yn = (c.y - ymin) / yspan
        xn = (c.x - xmin) / max(1e-6, xmax - xmin)

        if 0.70 < zn < 0.92 and 0.28 < xn < 0.72 and yn > 0.40:
            w = (1.0 - abs(xn - 0.5) * 1.6) * max(0.0, min(1.0, (0.92 - zn) / 0.20))
            mouth.data[i].co.z -= 0.040 * w * zspan
            mouth.data[i].co.y -= 0.015 * w * yspan

        if 0.80 < zn < 0.94 and yn > 0.45 and (xn < 0.45 or xn > 0.55):
            w = max(0.0, 1.0 - abs(zn - 0.87) / 0.08)
            blink.data[i].co.z -= 0.025 * w * zspan
            blink.data[i].co.y -= 0.010 * w * yspan

    print("FACIAL_SHAPEKEYS on", body.name)


def key_rot(pb, frame, rx=0.0, ry=0.0, rz=0.0):
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")
    pb.keyframe_insert(data_path="rotation_euler", frame=frame)


def smooth_action(arm):
    if not arm.animation_data or not arm.animation_data.action:
        return
    for fc in arm.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def animate_rig(arm, body, fps, total_frames):
    """Calm idle + clear wave. Minimal head motion. No rubber stretch poses."""
    if arm is None:
        print("NO_ARMATURE")
        return

    bm = bone_map(arm)

    def B(*names):
        for n in names:
            if n in bm:
                return bm[n]
        return None

    hips = B("Hips")
    spine = B("Spine")
    spine1 = B("Spine1")
    neck = B("Neck")
    head = B("Head")
    larm = B("LeftArm")
    lfore = B("LeftForeArm")
    lhand = B("LeftHand")
    rarm = B("RightArm")
    rfore = B("RightForeArm")
    luleg = B("LeftUpLeg")
    ruleg = B("RightUpLeg")

    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.object.mode_set(mode="POSE")
    except Exception:
        pass

    # Key only a few poses (not every frame) → smoother, less rubber jitter
    # Wave pattern: rest → raise → side flap → raise → rest
    # frames at 0%, 20%, 40%, 60%, 80%, 100%
    keys = [
        # t_frac, wave_phase 0=down 1=up/side
        (0.00, 0.0),
        (0.18, 1.0),
        (0.35, 0.55),
        (0.52, 1.0),
        (0.70, 0.55),
        (0.88, 1.0),
        (1.00, 0.2),
    ]

    for t_frac, wave in keys:
        f = max(1, int(round(t_frac * (total_frames - 1))) + 1)
        f = min(total_frames, f)

        # Body: almost still (stops rubber sway)
        if hips:
            key_rot(hips, f, rx=1, ry=0, rz=0)
        if spine:
            key_rot(spine, f, rx=4, ry=0, rz=0)
        if spine1:
            key_rot(spine1, f, rx=2, ry=0, rz=0)
        if luleg:
            key_rot(luleg, f, rx=3, ry=0, rz=0)
        if ruleg:
            key_rot(ruleg, f, rx=3, ry=0, rz=0)

        # Head/neck: tiny nod only (no shake)
        if neck:
            key_rot(neck, f, rx=2, ry=0, rz=0)
        if head:
            key_rot(head, f, rx=3 + 2 * wave, ry=0, rz=0)

        # LEFT ARM — clear wave: raise high, forearm flaps
        if larm:
            # down → up beside head
            key_rot(
                larm,
                f,
                rx=-35 - 55 * wave,
                ry=-5,
                rz=25 + 55 * wave,
            )
        if lfore:
            key_rot(lfore, f, rx=0, ry=0, rz=-10 - 55 * wave)
        if lhand:
            key_rot(lhand, f, rx=0, ry=10 * wave, rz=-15 * wave)

        # RIGHT ARM — stable open present (almost static)
        if rarm:
            key_rot(rarm, f, rx=-20, ry=12, rz=-30)
        if rfore:
            key_rot(rfore, f, rx=0, ry=0, rz=15)

        # Face
        if body and body.data.shape_keys:
            kb = body.data.shape_keys.key_blocks
            if "mouth_open" in kb:
                kb["mouth_open"].value = 0.2 + 0.55 * wave
                kb["mouth_open"].keyframe_insert(data_path="value", frame=f)
            if "blink" in kb:
                # one blink near middle
                kb["blink"].value = 1.0 if 0.45 < t_frac < 0.52 else 0.0
                kb["blink"].keyframe_insert(data_path="value", frame=f)

    smooth_action(arm)
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass
    print("ANIM_RIG sparse-keys wave frames", total_frames)


def setup_camera_lights():
    bpy.ops.object.light_add(type="SUN", location=(2, -3, 6))
    sun = bpy.context.active_object
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(48), math.radians(8), 0)

    bpy.ops.object.light_add(type="AREA", location=(-2, -1.5, 2.8))
    fill = bpy.context.active_object
    fill.data.energy = 80
    fill.data.size = 3.5

    bpy.ops.object.light_add(type="AREA", location=(2.5, 0.5, 2.5))
    rim = bpy.context.active_object
    rim.data.energy = 50
    rim.data.size = 2

    bpy.ops.object.camera_add(location=(0, -2.05, 1.15))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(88), 0, 0)
    cam.data.lens = 45
    cam.data.clip_start = 0.05
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.62, 0.72, 0.82)


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
    root, arm, body = import_mike_glb(glb)
    setup_camera_lights()
    add_facial_shape_keys(body)
    animate_rig(arm, body, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        setup_render_png(frame_dir, fps, total_frames, width, height)
        print(f"Render Mike3D {total_frames}f {width}x{height}")
        bpy.ops.render.render(animation=True)
        n = len(list(frame_dir.glob("frame_*.png")))
        print(f"frames={n}")
        if n < 1:
            raise SystemExit("No PNG frames written")
        frames_to_mp4(frame_dir, out, fps)

    if not (out.exists() and out.stat().st_size > 0):
        raise SystemExit("No video written")
    print("OK", out, out.stat().st_size)


if __name__ == "__main__":
    main()
