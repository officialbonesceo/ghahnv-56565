"""
Blender 3D Mike — Tripo Mixamo-rigged GLB + classroom.
Body: Mixamo bones (walk-in-place, wave, present).
Face: procedural shape keys (mouth open + blink) driven on a talk cycle.
No face bones/morphs in the GLB — facial is approximate mesh deformation.

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
from mathutils import Euler, Vector

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
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.armatures, bpy.data.actions):
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


def bone_map(arm_obj):
    """Map short name -> pose bone (handles mixamorig: prefix)."""
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
            body = meshes[0]
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
    morph_count = 0
    if body and body.data and getattr(body.data, "shape_keys", None):
        kb = body.data.shape_keys
        if kb and kb.key_blocks:
            morph_count = max(0, len(kb.key_blocks) - 1)

    print(
        "MIKE_CAPABILITY",
        "armature=" + str(bool(arm)),
        "meshes=" + str(len(meshes)),
        "shape_keys=" + str(morph_count),
        "bones=" + str(len(arm.pose.bones) if arm else 0),
    )

    # Root empty for placement
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0.9, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    # Bounds from meshes in world space
    min_c = Vector((1e9, 1e9, 1e9))
    max_c = Vector((-1e9, -1e9, -1e9))
    targets = meshes or after
    for o in targets:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max(0.01, max_c.z - min_c.z)
    scale = 1.75 / height

    # Parent hierarchy under root without breaking armature-mesh link
    tops = [o for o in after if o.parent is None or o.parent.name not in before]
    for o in tops:
        # keep relative parent if already parented inside import tree
        if o.parent is None:
            o.parent = root

    # Prefer parenting the armature root if present
    if arm and arm.parent is None:
        arm.parent = root
    for o in after:
        if o.parent is None:
            o.parent = root

    root.scale = (scale, scale, scale)
    root.location = (0, 0.9, -min_c.z * scale)
    root.rotation_euler = (0, 0, 0)

    print("MIKE_GLB", glb_path, "height", round(height, 3), "scale", round(scale, 3))
    return root, arm, body, morph_count


def add_facial_shape_keys(body):
    """Create approximate mouth_open and blink shape keys from head-region verts."""
    if body is None or body.type != "MESH":
        return None, None

    me = body.data
    # Ensure basis
    if me.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)

    # World-ish local coords
    coords = [v.co.copy() for v in me.vertices]
    if not coords:
        return None, None
    zs = [c.z for c in coords]
    ys = [c.y for c in coords]
    xs = [c.x for c in coords]
    zmin, zmax = min(zs), max(zs)
    ymin, ymax = min(ys), max(ys)
    xmin, xmax = min(xs), max(xs)
    zspan = max(1e-6, zmax - zmin)
    yspan = max(1e-6, ymax - ymin)
    xspan = max(1e-6, xmax - xmin)

    # Head band: upper 25% of height
    head_z0 = zmin + 0.72 * zspan
    # Mouth: lower part of head, center X, forward Y
    mouth = body.shape_key_add(name="mouth_open", from_mix=False)
    blink = body.shape_key_add(name="blink", from_mix=False)

    for i, v in enumerate(me.vertices):
        c = coords[i]
        zn = (c.z - zmin) / zspan
        yn = (c.y - ymin) / yspan
        xn = (c.x - xmin) / xspan

        # Mouth: lower-face center, pull down + slightly back
        if zn > 0.72 and zn < 0.90 and 0.35 < xn < 0.65 and yn > 0.45:
            w = (1.0 - abs(xn - 0.5) * 2.0) * max(0.0, (0.90 - zn) / 0.18)
            mouth.data[i].co.z -= 0.018 * w * zspan
            mouth.data[i].co.y -= 0.006 * w * yspan

        # Blink: upper-face thin band near eyes (approx), pull lids down
        if zn > 0.82 and zn < 0.92 and (xn < 0.42 or xn > 0.58) and yn > 0.50:
            w = max(0.0, 1.0 - abs(zn - 0.87) / 0.06)
            blink.data[i].co.z -= 0.010 * w * zspan
            blink.data[i].co.y -= 0.004 * w * yspan

    print("FACIAL_SHAPEKEYS mouth_open+blink created on", body.name)
    return mouth, blink


def key_pose_bone(pb, frame, rot_euler=None, loc=None):
    if rot_euler is not None:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = rot_euler
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert(data_path="location", frame=frame)


def animate_rig(arm, body, mouth_key, blink_key, fps, total_frames):
    """Walk-in-place + wave + head talk + shape-key face."""
    if arm is None:
        print("NO_ARMATURE — skipping bone animation")
        return

    bm = bone_map(arm)
    def B(*names):
        for n in names:
            if n in bm:
                return bm[n]
        return None

    hips = B("Hips", "mixamorig:Hips")
    spine = B("Spine", "mixamorig:Spine")
    spine1 = B("Spine1", "mixamorig:Spine1")
    spine2 = B("Spine2", "mixamorig:Spine2")
    neck = B("Neck", "mixamorig:Neck")
    head = B("Head", "mixamorig:Head")
    luleg = B("LeftUpLeg", "mixamorig:LeftUpLeg")
    lleg = B("LeftLeg", "mixamorig:LeftLeg")
    ruleg = B("RightUpLeg", "mixamorig:RightUpLeg")
    rleg = B("RightLeg", "mixamorig:RightLeg")
    larm = B("LeftArm", "mixamorig:LeftArm")
    lfore = B("LeftForeArm", "mixamorig:LeftForeArm")
    lhand = B("LeftHand", "mixamorig:LeftHand")
    rarm = B("RightArm", "mixamorig:RightArm")
    rfore = B("RightForeArm", "mixamorig:RightForeArm")

    # Ensure pose mode data path works from object mode keyframes
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.object.mode_set(mode="POSE")
    except Exception:
        pass

    for f in range(1, total_frames + 1):
        t = f / float(fps)
        phase = t * 2.0 * math.pi * 1.1  # walk frequency

        # Legs — walk cycle
        if luleg:
            key_pose_bone(luleg, f, Euler((math.radians(25 * math.sin(phase)), 0, 0), "XYZ"))
        if lleg:
            key_pose_bone(lleg, f, Euler((math.radians(20 * max(0, math.sin(phase))), 0, 0), "XYZ"))
        if ruleg:
            key_pose_bone(ruleg, f, Euler((math.radians(25 * math.sin(phase + math.pi)), 0, 0), "XYZ"))
        if rleg:
            key_pose_bone(rleg, f, Euler((math.radians(20 * max(0, math.sin(phase + math.pi))), 0, 0), "XYZ"))

        # Hips bob / sway
        if hips:
            key_pose_bone(
                hips,
                f,
                Euler((0, math.radians(3 * math.sin(phase)), math.radians(4 * math.sin(phase * 0.5))), "XYZ"),
                loc=Vector((0, 0, 0.01 * abs(math.sin(phase)))),
            )

        # Spine present lean
        if spine:
            key_pose_bone(spine, f, Euler((math.radians(4 + 2 * math.sin(t * 1.3)), 0, 0), "XYZ"))
        if spine1:
            key_pose_bone(spine1, f, Euler((math.radians(3 * math.sin(t * 1.1)), 0, 0), "XYZ"))

        # Right arm idle, left arm WAVE
        wave = 0.5 + 0.5 * math.sin(t * 2.5 * math.pi)  # ~1.25 Hz wave
        if larm:
            key_pose_bone(
                larm,
                f,
                Euler(
                    (
                        math.radians(-40 - 25 * wave),
                        math.radians(-20),
                        math.radians(70 + 30 * wave),
                    ),
                    "XYZ",
                ),
            )
        if lfore:
            key_pose_bone(lfore, f, Euler((0, 0, math.radians(-20 - 40 * wave)), "XYZ"))
        if lhand:
            key_pose_bone(lhand, f, Euler((0, 0, math.radians(-10 * wave)), "XYZ"))
        if rarm:
            key_pose_bone(rarm, f, Euler((math.radians(-15), math.radians(10), math.radians(-25)), "XYZ"))
        if rfore:
            key_pose_bone(rfore, f, Euler((0, 0, math.radians(15)), "XYZ"))

        # Head / neck talk nod
        talk = 0.5 + 0.5 * math.sin(t * 5.5)  # ~ speech-ish rate
        if neck:
            key_pose_bone(neck, f, Euler((math.radians(4 * talk), math.radians(3 * math.sin(t * 1.7)), 0), "XYZ"))
        if head:
            key_pose_bone(head, f, Euler((math.radians(6 * talk), math.radians(4 * math.sin(t * 2.1)), 0), "XYZ"))

        # Facial shape keys
        if body and body.data.shape_keys:
            kb = body.data.shape_keys.key_blocks
            if "mouth_open" in kb:
                # open on talk peaks
                kb["mouth_open"].value = 0.15 + 0.85 * max(0.0, math.sin(t * 6.0))
                kb["mouth_open"].keyframe_insert(data_path="value", frame=f)
            if "blink" in kb:
                # blink every ~2.5s for 2 frames
                blink_v = 1.0 if (int(t * 10) % 25 in (0, 1)) else 0.0
                kb["blink"].value = blink_v
                kb["blink"].keyframe_insert(data_path="value", frame=f)

    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass
    print("ANIM_RIG walk+wave+talk+face frames", total_frames)


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
    root, arm, body, morphs = import_mike_glb(glb)
    setup_camera_lights()

    mouth_key, blink_key = add_facial_shape_keys(body)
    animate_rig(arm, body, mouth_key, blink_key, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        setup_render_png(frame_dir, fps, total_frames, width, height)
        print(f"Render Mike3D rigged {total_frames}f {width}x{height}")
        bpy.ops.render.render(animation=True)
        n = len(list(frame_dir.glob("frame_*.png")))
        print(f"frames={n}")
        if n < 1:
            raise SystemExit("No PNG frames written")
        frames_to_mp4(frame_dir, out, fps)

    if not (out.exists() and out.stat().st_size > 0):
        raise SystemExit("No video written")
    print("OK", out, out.stat().st_size)
    print("NOTE: body=Mixamo bones; face=procedural shape keys (no native face morphs in GLB)")


if __name__ == "__main__":
    main()
