"""
Blender 3D Mike — body clips (Mikeanim.glb) + procedural facial animation.
Creates usable mouth_open / blink shape keys from mesh bounds when the
Tripo export has none. Never moves the root (avoids bounce).

Usage:
  blender -b -noaudio -P scripts/blender_mike3d_facial.py -- \
    --out assets/blender/mike3d_test.mp4 \
    --glb assets/mike/Mikeanim.glb \
    --seconds 12 --width 720 --height 1280
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args(argv):
    args = {
        "out": "assets/blender/mike_facial.mp4",
        "fps": 24,
        "seconds": 12.0,
        "width": 720,
        "height": 1280,
        "glb": "assets/mike/Mikeanim.glb",
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
        r = min(1.0, r + emit * 0.25)
        g = min(1.0, g + emit * 0.25)
        b = min(1.0, b + emit * 0.30)
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


def build_bright_studio():
    back = mesh("primitive_plane_add", size=20, location=(0, 2.8, 1.6))
    back.rotation_euler = (math.radians(90), 0, 0)
    back.data.materials.append(mat("Back", (0.22, 0.22, 0.24)))

    floor = mesh("primitive_plane_add", size=20, location=(0, 0.5, 0))
    floor.data.materials.append(mat("Floor", (0.18, 0.18, 0.20)))

    disc = mesh("primitive_cylinder_add", radius=1.1, depth=0.02, location=(0, 0.55, 0.01))
    disc.data.materials.append(mat("Disc", (0.12, 0.12, 0.14)))


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


def boost_imported_materials(meshes):
    for obj in meshes or []:
        for slot in obj.material_slots:
            m = slot.material
            if m is None:
                continue
            try:
                if m.use_nodes:
                    for node in m.node_tree.nodes:
                        if node.type == "BSDF_PRINCIPLED":
                            if "Emission Strength" in node.inputs:
                                node.inputs["Emission Strength"].default_value = max(
                                    node.inputs["Emission Strength"].default_value, 0.05
                                )
                            if "Roughness" in node.inputs:
                                node.inputs["Roughness"].default_value = min(
                                    0.85, max(0.35, node.inputs["Roughness"].default_value)
                                )
                else:
                    r, g, b, a = m.diffuse_color
                    m.diffuse_color = (min(1, r * 1.15), min(1, g * 1.15), min(1, b * 1.15), a)
            except Exception:
                pass


def import_mike_glb(glb_path: Path):
    if not glb_path.exists():
        alt = glb_path.parent / "Mike.glb"
        if alt.exists():
            glb_path = alt
        else:
            raise SystemExit(f"Missing GLB: {glb_path}")

    before_objs = set(bpy.data.objects.keys())
    before_actions = set(bpy.data.actions.keys())
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    after = [o for o in bpy.data.objects if o.name not in before_objs]
    new_actions = [a for a in bpy.data.actions if a.name not in before_actions]
    if not after:
        raise SystemExit("GLB import produced no objects")

    arm, body, meshes = find_armature_and_mesh(after)

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

    if arm and body:
        for mod in body.modifiers:
            if mod.type == "ARMATURE":
                try:
                    mod.use_deform_preserve_volume = True
                except Exception:
                    pass

    boost_imported_materials(meshes)

    jaw_bone = head_bone = eye_l = eye_r = None
    if arm and arm.pose:
        for pb in arm.pose.bones:
            n = pb.name.lower()
            if "jaw" in n:
                jaw_bone = pb
            elif n in ("head", "head_end") or n.endswith("head"):
                head_bone = pb
            elif "lefteye" in n or "eye_l" in n or "left_eye" in n:
                eye_l = pb
            elif "righteye" in n or "eye_r" in n or "right_eye" in n:
                eye_r = pb

    print(
        "MIKE_IMPORT",
        "armature", bool(arm),
        "meshes", len(meshes),
        "bones", len(arm.pose.bones) if arm else 0,
        "jaw", bool(jaw_bone),
        "head", bool(head_bone),
        "shape_keys", bool(body and body.data.shape_keys),
    )
    return root, arm, body, new_actions or list(bpy.data.actions), jaw_bone, head_bone, eye_l, eye_r


def _mesh_bounds_local(mesh_obj):
    """Axis-aligned bounds in object-local space."""
    me = mesh_obj.data
    if not me.vertices:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def ensure_shape_keys(mesh_obj):
    """
    Create geometric mouth_open and blink shape keys from mesh bounds.
    Works on Tripo / arbitrary humanoid topology that has no keys.
    """
    if mesh_obj is None:
        return {}
    me = mesh_obj.data
    if me.shape_keys is None:
        mesh_obj.shape_key_add(name="Basis", from_mix=False)

    keys = {}
    existing = {kb.name.lower(): kb for kb in me.shape_keys.key_blocks}

    mn, mx = _mesh_bounds_local(mesh_obj)
    size = mx - mn
    if size.z < 1e-6:
        size.z = 1.0
    h = size.z
    mouth_z0 = mn.z + h * 0.42
    mouth_z1 = mn.z + h * 0.58
    eye_z0 = mn.z + h * 0.62
    eye_z1 = mn.z + h * 0.78
    mouth_x_half = size.x * 0.22
    eye_x_half = size.x * 0.28
    cx = (mn.x + mx.x) * 0.5
    y_mid = (mn.y + mx.y) * 0.5

    def falloff_mouth(v):
        if not (mouth_z0 <= v.co.z <= mouth_z1):
            return 0.0
        if abs(v.co.x - cx) > mouth_x_half:
            return 0.0
        if v.co.y < y_mid - size.y * 0.05:
            return 0.0
        tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
        lip = 1.0 - abs(tz - 0.35) * 1.6
        lip = max(0.0, min(1.0, lip))
        tx = 1.0 - abs(v.co.x - cx) / mouth_x_half
        return lip * max(0.0, tx) ** 0.7

    def falloff_blink(v):
        if not (eye_z0 <= v.co.z <= eye_z1):
            return 0.0
        if abs(v.co.x - cx) > eye_x_half:
            return 0.0
        if v.co.y < y_mid - size.y * 0.02:
            return 0.0
        tz = (v.co.z - eye_z0) / max(1e-6, eye_z1 - eye_z0)
        lid = 1.0 - abs(tz - 0.55) * 2.2
        lid = max(0.0, min(1.0, lid))
        tx = 1.0 - abs(v.co.x - cx) / eye_x_half
        return lid * max(0.0, tx) ** 0.8

    if "mouth_open" not in existing and "mouthopen" not in existing and "jawopen" not in existing:
        kb = mesh_obj.shape_key_add(name="mouth_open", from_mix=False)
        open_down = h * 0.028
        open_fwd = h * 0.012
        for i, v in enumerate(me.vertices):
            w = falloff_mouth(v)
            if w <= 0.01:
                continue
            tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
            down = open_down * w * (1.15 - 0.7 * tz)
            fwd = open_fwd * w * (0.6 + 0.4 * (1.0 - tz))
            kb.data[i].co.z -= down
            kb.data[i].co.y += fwd
        keys["mouth_open"] = kb
        print("SHAPEKEY_CREATED mouth_open")
    else:
        keys["mouth_open"] = (
            existing.get("mouth_open")
            or existing.get("mouthopen")
            or existing.get("jawopen")
        )

    if "blink" not in existing and "eyeblink" not in existing and "eyeblinkleft" not in existing:
        kb = mesh_obj.shape_key_add(name="blink", from_mix=False)
        close = h * 0.014
        for i, v in enumerate(me.vertices):
            w = falloff_blink(v)
            if w <= 0.01:
                continue
            kb.data[i].co.z -= close * w
        keys["blink"] = kb
        print("SHAPEKEY_CREATED blink")
    else:
        keys["blink"] = (
            existing.get("blink")
            or existing.get("eyeblink")
            or existing.get("eyeblinkleft")
        )

    if "mouth_open" in keys and keys["mouth_open"] is not None:
        kb = keys["mouth_open"]
        moved = sum(
            1
            for i, v in enumerate(me.vertices)
            if (kb.data[i].co - v.co).length > 1e-5
        )
        print("SHAPEKEY_MOUTH_MOVED", moved, "of", len(me.vertices))

    return keys


def animate_face(root, body, jaw_bone, head_bone, eye_l, eye_r, fps, total_frames):
    """Subtle face only. Never keyframe root — body NLA owns body motion."""
    random.seed(42)
    sk_map = ensure_shape_keys(body)

    speech_windows = [(0.8, 3.5), (4.2, 7.0), (8.0, 11.2)]

    def in_speech(t):
        return any(a <= t <= b for a, b in speech_windows)

    blink_times = []
    t = 1.2
    while t < (total_frames / fps) - 0.4:
        blink_times.append(t)
        t += random.uniform(2.4, 4.2)

    for f in range(1, total_frames + 1):
        t = f / float(fps)

        if head_bone is not None:
            try:
                head_bone.rotation_euler = (
                    math.radians(0.7 * math.sin(t * 0.9)),
                    math.radians(0.5 * math.sin(t * 1.3)),
                    math.radians(0.9 * math.sin(t * 1.1)),
                )
                head_bone.keyframe_insert(data_path="rotation_euler", frame=f)
            except Exception:
                pass

        mouth_amt = 0.0
        if in_speech(t):
            mouth_amt = 0.28 + 0.48 * abs(math.sin(t * 9.5))
            mouth_amt *= 0.65 + 0.35 * abs(math.sin(t * 3.2))
        else:
            mouth_amt = 0.03 * abs(math.sin(t * 1.8))

        if sk_map.get("mouth_open") is not None:
            try:
                sk_map["mouth_open"].value = mouth_amt
                sk_map["mouth_open"].keyframe_insert(data_path="value", frame=f)
            except Exception:
                pass

        if jaw_bone is not None:
            try:
                jaw_bone.rotation_euler = (math.radians(10.0 * mouth_amt), 0, 0)
                jaw_bone.keyframe_insert(data_path="rotation_euler", frame=f)
            except Exception:
                pass

        blink_val = 0.0
        for bt in blink_times:
            if abs(t - bt) < 0.06:
                blink_val = 1.0
            elif abs(t - bt) < 0.12:
                blink_val = 0.4

        if sk_map.get("blink") is not None:
            try:
                sk_map["blink"].value = blink_val
                sk_map["blink"].keyframe_insert(data_path="value", frame=f)
            except Exception:
                pass

        if eye_l is not None:
            try:
                eye_l.rotation_euler = (
                    math.radians(1.0 * math.sin(t * 0.7)),
                    math.radians(1.5 * math.sin(t * 0.55)),
                    0,
                )
                eye_l.keyframe_insert(data_path="rotation_euler", frame=f)
            except Exception:
                pass
        if eye_r is not None:
            try:
                eye_r.rotation_euler = (
                    math.radians(1.0 * math.sin(t * 0.7 + 0.3)),
                    math.radians(1.5 * math.sin(t * 0.55 + 0.2)),
                    0,
                )
                eye_r.keyframe_insert(data_path="rotation_euler", frame=f)
            except Exception:
                pass


def action_duration_frames(action, fps):
    if action is None:
        return 1
    fr = getattr(action, "frame_range", None)
    if fr is not None and len(fr) >= 2:
        span = float(fr[1]) - float(fr[0])
        if span > 0.5:
            return max(1, int(round(span)))
    return max(1, fps)


def pick_clip_sequence(actions):
    by_name = {a.name: a for a in actions}
    names = list(by_name.keys())
    preferred = []
    for n in names:
        if n.startswith("_"):
            preferred.append(n)
            break
    for key in ("Agree_Gesture", "Alert", "Casual_Walk", "Walking"):
        if key in by_name and key not in preferred:
            preferred.append(key)
    if not preferred:
        preferred = names[:3]
    return [by_name[n] for n in preferred[:3] if n in by_name]


def sequence_clips_on_armature(arm, actions, fps, max_total_frames):
    if arm is None:
        return 1
    clips = pick_clip_sequence(actions)
    if not clips:
        return 1

    if not arm.animation_data:
        arm.animation_data_create()
    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None

    track = arm.animation_data.nla_tracks.new()
    track.name = "MikeClips"

    frame = 1
    for action in clips:
        dur = action_duration_frames(action, fps)
        max_each = max(fps, max_total_frames // max(1, len(clips)))
        use = min(dur, max_each)
        fr = getattr(action, "frame_range", None)
        act_start = float(fr[0]) if fr is not None and len(fr) >= 2 else 0.0
        try:
            strip = track.strips.new(action.name, int(frame), action)
        except TypeError:
            strip = track.strips.new(int(frame), action)
            strip.name = action.name
        strip.action = action
        try:
            strip.action_frame_start = act_start
            strip.action_frame_end = act_start + use
        except Exception:
            pass
        strip.frame_start = frame
        strip.frame_end = frame + use
        try:
            strip.blend_type = "REPLACE"
            strip.extrapolation = "NOTHING"
        except Exception:
            pass
        frame += use

    return max(1, min(frame - 1, max_total_frames))


def setup_camera_lights():
    bpy.ops.object.light_add(type="SUN", location=(1.5, -2.5, 7))
    sun = bpy.context.active_object
    sun.data.energy = 6.5
    sun.rotation_euler = (math.radians(40), math.radians(12), 0)

    bpy.ops.object.light_add(type="AREA", location=(0, -2.2, 2.2))
    fill = bpy.context.active_object
    fill.data.energy = 350
    fill.data.size = 5.0

    bpy.ops.object.light_add(type="AREA", location=(-2.5, -0.5, 2.5))
    left = bpy.context.active_object
    left.data.energy = 180
    left.data.size = 3.5

    bpy.ops.object.light_add(type="AREA", location=(2.8, 0.2, 2.8))
    rim = bpy.context.active_object
    rim.data.energy = 120
    rim.data.size = 2.5

    bpy.ops.object.camera_add(location=(0, -2.35, 1.05))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(86), 0, 0)
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.35, 0.35, 0.38)


def setup_render_png(frame_dir: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_shadows = False
    except Exception:
        pass
    try:
        scene.view_settings.exposure = 0.35
        scene.view_settings.gamma = 1.0
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


def frames_to_mp4(frame_dir: Path, out: Path, fps: int):
    frames = sorted(frame_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"No frames in {frame_dir}")
    list_file = frame_dir / "list.txt"
    list_file.write_text("".join(f"file '{f.resolve()}'\n" for f in frames), encoding="utf-8")
    subprocess.check_call([
        "ffmpeg", "-y", "-r", str(fps),
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-movflags", "+faststart",
        str(out),
    ])


def main():
    args = parse_args(sys.argv)
    fps = int(args.get("fps", 24))
    seconds = min(max(float(args["seconds"]), 2.0), 20.0)
    max_frames = max(fps, int(round(seconds * fps)))
    width = int(args.get("width", 720))
    height = int(args.get("height", 1280))
    glb = Path(args["glb"]).resolve()

    clear_scene()
    build_bright_studio()
    root, arm, body, actions, jaw, head, eye_l, eye_r = import_mike_glb(glb)
    setup_camera_lights()
    total_frames = sequence_clips_on_armature(arm, actions, fps, max_frames)

    animate_face(root, body, jaw, head, eye_l, eye_r, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        setup_render_png(frame_dir, fps, total_frames, width, height)
        print(f"Render Mike3D+Face {total_frames}f {width}x{height}")
        bpy.ops.render.render(animation=True)
        n = len(list(frame_dir.glob("frame_*.png")))
        print(f"frames={n}")
        if n < 1:
            raise SystemExit("No PNG frames written")
        frames_to_mp4(frame_dir, out, fps)

    print("OK", out, out.stat().st_size if out.exists() else 0)


if __name__ == "__main__":
    main()
