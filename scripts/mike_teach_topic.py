#!/usr/bin/env python3
"""
Mike teaches a seeded topic:
- Tripo-style soft studio lighting + Workbench TEXTURE (colors)
- Body: walk then explain gestures (NLA)
- Mouth: jaw-like shape key while explaining
- Never moves Root/Hips for face
- Topic burned in via ffmpeg after render
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector

# Seed topic (student-friendly)
TOPIC_TITLE = "What is Coding?"
TOPIC_LINE = "Coding is how we give computers step-by-step instructions."


def parse_args(argv):
    args = {
        "glb": "assets/mike/Mikeanim.glb",
        "out": "assets/blender/mike_teach_topic.mp4",
        "fps": 24,
        "seconds": 14,
        "width": 720,
        "height": 1280,
        "topic": TOPIC_TITLE,
        "line": TOPIC_LINE,
    }
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:].replace("-", "_")
            val = argv[i + 1]
            if key in ("fps", "width", "height", "seconds"):
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
        bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
        bpy.data.lights, bpy.data.armatures, bpy.data.actions, bpy.data.images,
    ):
        for block in list(coll):
            try:
                coll.remove(block)
            except Exception:
                pass


def mat_simple(name, color):
    m = bpy.data.materials.new(name=name)
    try:
        m.use_nodes = False
    except Exception:
        pass
    r, g, b = color
    m.diffuse_color = (r, g, b, 1.0)
    return m


def find_arm_body():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arm = None
    for a in arms:
        if any("Head" in b.name for b in a.data.bones):
            arm = a
            break
    if arm is None and arms:
        arm = arms[0]
    body = None
    if meshes:
        for m in meshes:
            if any(mod.type == "ARMATURE" for mod in m.modifiers):
                body = m
                break
        if body is None:
            body = max(meshes, key=lambda o: len(o.data.vertices))
    return arm, body, meshes


def place_character(arm, body, meshes):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    min_c = Vector((1e9, 1e9, 1e9))
    max_c = Vector((-1e9, -1e9, -1e9))
    for o in ([body] if body else meshes):
        if o is None:
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max(0.01, max_c.z - min_c.z)
    scale = 1.70 / height

    if arm and arm.parent is None:
        arm.parent = root
    for o in list(bpy.data.objects):
        if o.type in ("MESH", "ARMATURE") and o.parent is None and o != root:
            o.parent = root

    root.scale = (scale, scale, scale)
    root.location = (0.0, 0.75, -min_c.z * scale)
    bpy.context.view_layer.update()
    print("PLACE height", round(height, 3), "scale", round(scale, 3))
    return root


def ensure_textures_visible(body):
    if body is None:
        return
    for slot in body.material_slots:
        mat = slot.material
        if mat is None:
            continue
        print("MATERIAL", mat.name)
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                print("  TEX", node.image.name)
            if node.type == "BSDF_PRINCIPLED" and "Roughness" in node.inputs:
                node.inputs["Roughness"].default_value = min(
                    0.8, max(0.4, node.inputs["Roughness"].default_value)
                )


def ensure_mouth_shape_key(body):
    if body is None:
        raise SystemExit("No body")
    me = body.data
    if me.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    for kb in list(me.shape_keys.key_blocks):
        if kb.name.lower() in ("mouth_open", "mouth", "jaw_open"):
            try:
                body.shape_key_remove(key=kb)
            except Exception:
                pass

    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    mn = Vector((min(xs), min(ys), min(zs)))
    mx = Vector((max(xs), max(ys), max(zs)))
    size = mx - mn
    h = size.z if size.z > 1e-6 else 1.0
    cx = (mn.x + mx.x) * 0.5

    mouth_z0 = mn.z + h * 0.64
    mouth_z1 = mn.z + h * 0.76
    mouth_x_half = size.x * 0.18
    lower_down = h * 0.055
    upper_up = h * 0.014
    fwd = h * 0.018
    corner = h * 0.012

    kb = body.shape_key_add(name="mouth_open", from_mix=False)
    moved = 0
    for i, v in enumerate(me.vertices):
        if not (mouth_z0 <= v.co.z <= mouth_z1):
            continue
        dx = abs(v.co.x - cx)
        if dx > mouth_x_half:
            continue
        depth = (v.co.y - mn.y) / max(1e-6, size.y)
        if depth > 0.50:
            continue
        tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
        w = max(0.0, 1.0 - dx / mouth_x_half) ** 0.65
        if tz < 0.48:
            lip_w = max(0.0, min(1.0, w * (1.0 - abs(tz - 0.25) * 1.2)))
            if lip_w < 0.08:
                continue
            kb.data[i].co.z -= lower_down * lip_w * (1.15 - tz)
            kb.data[i].co.y -= fwd * lip_w
            kb.data[i].co.x += corner * lip_w * (0.6 if v.co.x >= cx else -0.6)
            moved += 1
        else:
            lip_w = w * max(0.0, 1.0 - abs(tz - 0.55) * 3.0)
            if lip_w < 0.12:
                continue
            kb.data[i].co.z += upper_up * lip_w
            kb.data[i].co.y -= fwd * 0.35 * lip_w
            moved += 1

    print("SHAPEKEY_MOUTH_MOVED", moved)
    if moved < 80:
        mouth_z0 = mn.z + h * 0.60
        mouth_z1 = mn.z + h * 0.80
        mouth_x_half = size.x * 0.26
        for i, v in enumerate(me.vertices):
            if not (mouth_z0 <= v.co.z <= mouth_z1):
                continue
            if abs(v.co.x - cx) > mouth_x_half:
                continue
            if (v.co.y - mn.y) / max(1e-6, size.y) > 0.60:
                continue
            tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
            w = max(0.0, 1.0 - abs(v.co.x - cx) / mouth_x_half) ** 0.5
            if tz < 0.5:
                kb.data[i].co.z -= lower_down * 1.2 * w
                kb.data[i].co.y -= fwd * w
            else:
                kb.data[i].co.z += upper_up * w
            moved += 1
        print("SHAPEKEY_MOUTH_MOVED_AFTER", moved)
    if moved < 30:
        raise SystemExit("Too few mouth verts")
    kb.value = 0.0
    return kb


def sequence_walk_then_explain(arm, fps, total):
    """Walk first third, then explain/agree for the rest."""
    if arm is None:
        return
    if not arm.animation_data:
        arm.animation_data_create()

    by_name = {a.name: a for a in bpy.data.actions}
    walk = None
    explain = None
    for k in ("Casual_Walk", "Walking", "Running"):
        if k in by_name:
            walk = by_name[k]
            break
    for k in ("Agree_Gesture", "Alert"):
        if k in by_name:
            explain = by_name[k]
            break
    for a in bpy.data.actions:
        if a.name.startswith("_") and explain is None:
            explain = a

    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None

    track = arm.animation_data.nla_tracks.new()
    track.name = "BodyTeach"
    walk_end = max(fps * 3, total // 3)

    def add_strip(action, start, end, name):
        if action is None:
            return
        try:
            strip = track.strips.new(name[:40], int(start), action)
        except TypeError:
            strip = track.strips.new(int(start), action)
            strip.name = name[:40]
        strip.action = action
        strip.frame_start = start
        strip.frame_end = end
        try:
            strip.blend_type = "REPLACE"
            strip.extrapolation = "HOLD"
        except Exception:
            pass
        print("BODY_STRIP", name, start, "->", end)

    add_strip(walk or explain, 1, walk_end, (walk or explain).name if (walk or explain) else "walk")
    add_strip(explain or walk, walk_end + 1, total, (explain or walk).name if (explain or walk) else "explain")


def animate_mouth(kb, fps, total):
    # Quiet during walk, talk during explain
    walk_end_t = max(3.0, total / fps / 3.0)
    speech = [(walk_end_t + 0.2, total / fps - 0.2)]
    cycle = max(5, int(fps * 0.30))

    def in_speech(t):
        return any(a <= t <= b for a, b in speech)

    for f in range(1, total + 1):
        t = f / float(fps)
        if in_speech(t):
            phase = ((f - 1) % cycle) / float(cycle)
            if phase < 0.45:
                val = phase / 0.45
            else:
                val = 1.0 - (phase - 0.45) / 0.55
            val = max(0.0, min(1.0, val)) ** 0.85
        else:
            val = 0.02 * abs(math.sin(t * 1.5))
        kb.value = val
        kb.keyframe_insert(data_path="value", frame=f)
    print("MOUTH_KEYS frames", total)


def tripo_style_studio():
    """Soft dark studio like Tripo viewer: gradient-ish floor+back, soft lights."""
    # Dark gradient backdrop
    bpy.ops.mesh.primitive_plane_add(size=28, location=(0, 3.5, 1.6))
    back = bpy.context.active_object
    back.rotation_euler = (math.radians(90), 0, 0)
    back.data.materials.append(mat_simple("Back", (0.12, 0.12, 0.14)))

    bpy.ops.mesh.primitive_plane_add(size=28, location=(0, 0.8, 0))
    floor = bpy.context.active_object
    floor.data.materials.append(mat_simple("Floor", (0.10, 0.10, 0.11)))

    # Soft disc under feet
    bpy.ops.mesh.primitive_cylinder_add(radius=1.3, depth=0.02, location=(0, 0.75, 0.01))
    disc = bpy.context.active_object
    disc.data.materials.append(mat_simple("Disc", (0.08, 0.08, 0.09)))


def setup_camera_lights(arm, body):
    bpy.context.view_layer.update()
    head = None
    hips = None
    if arm:
        for name in ("mixamorig:Head", "Head"):
            pb = arm.pose.bones.get(name)
            if pb:
                head = (arm.matrix_world @ pb.matrix) @ Vector((0, 0, 0))
                break
        pb = arm.pose.bones.get("mixamorig:Hips")
        if pb:
            hips = (arm.matrix_world @ pb.matrix) @ Vector((0, 0, 0))

    if head is None:
        head = Vector((0, 0.75, 1.4))
    if hips is None:
        hips = Vector((0, 0.75, 0.7))

    # Full body / slight low angle like Tripo hero shot
    aim = Vector((0, hips.y, (head.z + hips.z) * 0.52))
    cam_loc = Vector((0.15, aim.y - 3.1, aim.z + 0.15))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (aim - cam_loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 45
    bpy.context.scene.camera = cam

    # Key (soft front-right)
    bpy.ops.object.light_add(type="AREA", location=(1.8, -2.2, 2.8))
    key = bpy.context.active_object
    key.data.energy = 280
    key.data.size = 3.5

    # Fill (front-left, weaker)
    bpy.ops.object.light_add(type="AREA", location=(-1.6, -1.8, 2.0))
    fill = bpy.context.active_object
    fill.data.energy = 140
    fill.data.size = 3.0

    # Rim / top
    bpy.ops.object.light_add(type="AREA", location=(0.2, 1.2, 3.2))
    rim = bpy.context.active_object
    rim.data.energy = 100
    rim.data.size = 2.5

    # Soft sun
    bpy.ops.object.light_add(type="SUN", location=(2, -3, 6))
    sun = bpy.context.active_object
    sun.data.energy = 2.2
    sun.rotation_euler = (math.radians(45), math.radians(15), 0)

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.08, 0.08, 0.09)
    print("CAMERA full-body Tripo-style")


def setup_workbench(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_shadows = False
        scene.display.shading.show_specular_highlight = True
    except Exception:
        try:
            scene.display.shading.color_type = "MATERIAL"
        except Exception:
            pass
    print("ENGINE WORKBENCH TEXTURE")


def render_frames(frame_dir: Path, fps, width, height, total):
    scene = bpy.context.scene
    setup_workbench(scene)
    try:
        scene.view_settings.view_transform = "Standard"
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    for f in range(1, total + 1):
        scene.frame_set(f)
        path = frame_dir / f"frame_{f:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if f % 24 == 0:
            print(f"RENDER {f}/{total}")


def frames_to_mp4_with_topic(frame_dir: Path, out: Path, fps: int, topic: str, line: str):
    frames = sorted(frame_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit("No frames")
    list_file = frame_dir / "list.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in frames))

    raw = frame_dir / "raw.mp4"
    subprocess.check_call([
        "ffmpeg", "-y", "-r", str(fps),
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        str(raw),
    ])

    # Safe text for drawtext
    def esc(s):
        return (
            s.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "%%")
        )

    title = esc(topic)
    subtitle = esc(line)
    # Title top, one line tip bottom
    vf = (
        f"drawtext=text='{title}':fontcolor=white:fontsize=36:"
        f"x=(w-text_w)/2:y=48:box=1:boxcolor=black@0.45:boxborderw=12,"
        f"drawtext=text='{subtitle}':fontcolor=white:fontsize=22:"
        f"x=(w-text_w)/2:y=h-90:box=1:boxcolor=black@0.40:boxborderw=10"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(raw),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-movflags", "+faststart",
        str(out),
    ]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        # Fallback without drawtext if font missing
        print("DRAWTEXT failed — copying raw")
        subprocess.check_call(["cp", str(raw), str(out)])
    print("OUT", out, out.stat().st_size)


def main():
    args = parse_args(sys.argv)
    glb = Path(args["glb"]).resolve()
    out = Path(args["out"]).resolve()
    fps = int(args["fps"])
    seconds = int(args["seconds"])
    width = int(args["width"])
    height = int(args["height"])
    topic = args.get("topic") or TOPIC_TITLE
    line = args.get("line") or TOPIC_LINE
    total = fps * seconds

    if not glb.exists():
        alt = glb.parent / "Mike.glb"
        if alt.exists():
            glb = alt
        else:
            raise SystemExit(f"Missing {glb}")

    clear_scene()
    tripo_style_studio()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    print("IMPORTED", glb)
    print("TOPIC", topic)

    arm, body, meshes = find_arm_body()
    if body is None:
        raise SystemExit("No body")

    place_character(arm, body, meshes)
    ensure_textures_visible(body)
    kb = ensure_mouth_shape_key(body)
    sequence_walk_then_explain(arm, fps, total)
    animate_mouth(kb, fps, total)
    setup_camera_lights(arm, body)

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        render_frames(frame_dir, fps, width, height, total)
        frames_to_mp4_with_topic(frame_dir, out, fps, topic, line)

    print("DONE teach topic")


if __name__ == "__main__":
    main()
