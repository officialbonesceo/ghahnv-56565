#!/usr/bin/env python3
"""
Mike MOUTH TALK — deform the REAL mesh mouth (no floating cubes).

The character GLB has 0 morph targets. We build a strong 'mouth_open'
shape key by moving lower-face vertices, then drive it while body
plays a teaching gesture. Camera frames the face so motion is obvious.

Never animates Root/Hips for face (no bounce).
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args(argv):
    args = {
        "glb": "assets/mike/Mikeanim.glb",
        "out": "assets/blender/mike_mouth_talk.mp4",
        "fps": 24,
        "seconds": 10,
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
        bpy.data.lights, bpy.data.armatures, bpy.data.actions,
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
    root.location = (0.0, 0.70, -min_c.z * scale)
    bpy.context.view_layer.update()
    print("PLACE height", round(height, 3), "scale", round(scale, 3))
    return root


def ensure_mouth_shape_key(body):
    """
    Build a VERY visible mouth_open shape key on the real mesh.
    Uses local mesh bounds (Y-up in original GLB becomes Z-up in Blender).
    After glTF import Blender is Z-up: height is Z.
    """
    if body is None:
        raise SystemExit("No body mesh")

    me = body.data
    if me.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)

    # Remove old mouth keys
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
    # Front of face: in Mixamo/glTF after import, character often faces -Y or +Y
    # Use the half of depth that has more "face" — try both by picking max |y| center band
    cy = (mn.y + mx.y) * 0.5

    print("MESH_BOUNDS", tuple(round(v, 3) for v in mn), "->", tuple(round(v, 3) for v in mx), "h", round(h, 3))

    # Head is upper ~40% of height. Mouth is lower third of head.
    head_z0 = mn.z + h * 0.58
    head_z1 = mx.z
    mouth_z0 = mn.z + h * 0.62
    mouth_z1 = mn.z + h * 0.78
    mouth_x_half = size.x * 0.22

    # Prefer front-facing verts: take the side with greater average |projection|
    # After typical Mixamo import, character faces -Y (camera looks +Y toward them)
    # So mouth verts tend to have y toward the front (lower y if facing -Y)
    front_sign = -1.0  # open mouth slightly forward toward camera

    kb = body.shape_key_add(name="mouth_open", from_mix=False)

    # Strong displacements relative to head height
    open_down = h * 0.055   # lower lip / chin drop
    open_up = h * 0.018     # upper lip slight raise
    open_fwd = h * 0.025    # lips push forward
    open_side = h * 0.012   # corners pull out

    moved = 0
    for i, v in enumerate(me.vertices):
        if not (mouth_z0 <= v.co.z <= mouth_z1):
            continue
        if abs(v.co.x - cx) > mouth_x_half:
            continue
        # Prefer front half of head depth
        depth = (v.co.y - mn.y) / max(1e-6, size.y)
        # If model faces -Y, front is small y (depth near 0). Keep verts in front 55%.
        if depth > 0.55:
            continue

        tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)  # 0=bottom mouth, 1=top
        tx = 1.0 - abs(v.co.x - cx) / mouth_x_half
        w = max(0.0, tx) ** 0.5
        # Center of mouth opens more
        lip = 1.0 - abs(tz - 0.40) * 1.6
        lip = max(0.0, min(1.0, lip))
        w *= lip
        if w < 0.05:
            continue

        # Lower part of mouth band goes down; upper goes slightly up
        if tz < 0.55:
            kb.data[i].co.z -= open_down * w * (1.1 - tz)
        else:
            kb.data[i].co.z += open_up * w * (tz - 0.45)

        kb.data[i].co.y += front_sign * open_fwd * w
        kb.data[i].co.x += open_side * w * (1.0 if v.co.x >= cx else -1.0)
        moved += 1

    print("SHAPEKEY_MOUTH_MOVED", moved, "of", len(me.vertices))
    if moved < 50:
        # Fallback: wider band, no front filter
        print("FALLBACK wider mouth band")
        mouth_z0 = mn.z + h * 0.58
        mouth_z1 = mn.z + h * 0.82
        mouth_x_half = size.x * 0.30
        for i, v in enumerate(me.vertices):
            if not (mouth_z0 <= v.co.z <= mouth_z1):
                continue
            if abs(v.co.x - cx) > mouth_x_half:
                continue
            tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
            tx = 1.0 - abs(v.co.x - cx) / mouth_x_half
            w = max(0.0, tx) ** 0.5
            if w < 0.05:
                continue
            if tz < 0.5:
                kb.data[i].co.z -= open_down * 1.3 * w
            else:
                kb.data[i].co.z += open_up * 1.2 * w
            kb.data[i].co.y += front_sign * open_fwd * w
            moved += 1
        print("SHAPEKEY_MOUTH_MOVED_FALLBACK", moved)

    if moved < 20:
        raise SystemExit("Mouth shape key moved too few verts — abort")

    kb.value = 0.0
    return kb


def sequence_body(arm, fps, total):
    if arm is None:
        return
    if not arm.animation_data:
        arm.animation_data_create()
    by_name = {a.name: a for a in bpy.data.actions}
    preferred = []
    for k in ("Agree_Gesture", "Alert"):
        if k in by_name:
            preferred.append(by_name[k])
    for a in bpy.data.actions:
        if a.name.startswith("_") and a not in preferred:
            preferred.insert(0, a)
            break
    if not preferred:
        preferred = list(bpy.data.actions)[:1]

    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None
    if not preferred:
        return
    track = arm.animation_data.nla_tracks.new()
    track.name = "Body"
    action = preferred[0]
    try:
        strip = track.strips.new(action.name[:40], 1, action)
    except TypeError:
        strip = track.strips.new(1, action)
    strip.action = action
    strip.frame_start = 1
    strip.frame_end = total
    try:
        strip.extrapolation = "HOLD"
    except Exception:
        pass
    print("BODY", action.name)


def animate_mouth(kb, fps, total):
    """Drive mouth_open 0→1→0 in speech pulses."""
    speech = [(0.3, 3.2), (3.6, 6.8), (7.2, 9.7)]
    cycle = max(5, int(fps * 0.28))

    def in_speech(t):
        return any(a <= t <= b for a, b in speech)

    for f in range(1, total + 1):
        t = f / float(fps)
        if in_speech(t):
            phase = ((f - 1) % cycle) / float(cycle)
            # sharp open/close
            val = abs(math.sin(phase * math.pi))
            val = min(1.0, val * 1.15)
        else:
            val = 0.04 * abs(math.sin(t * 2.0))
        kb.value = val
        kb.keyframe_insert(data_path="value", frame=f)
    print("MOUTH_KEYS frames", total)


def setup_camera_face(arm, body):
    """Close enough to clearly see the mouth."""
    bpy.context.view_layer.update()
    head = None
    if arm:
        for name in ("mixamorig:Head", "Head"):
            pb = arm.pose.bones.get(name)
            if pb:
                head = (arm.matrix_world @ pb.matrix) @ Vector((0, 0, 0))
                break
    if head is None and body:
        corners = [body.matrix_world @ Vector(c) for c in body.bound_box]
        zs = [c.z for c in corners]
        ys = [c.y for c in corners]
        xs = [c.x for c in corners]
        head = Vector((sum(xs) / len(xs), sum(ys) / len(ys), max(zs) * 0.85))

    aim = head + Vector((0, 0, -0.05))
    cam_loc = Vector((aim.x, aim.y - 1.15, aim.z))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (aim - cam_loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=(1.5, -2.5, 5))
    bpy.context.active_object.data.energy = 5.5
    bpy.ops.object.light_add(type="AREA", location=(0, -1.2, aim.z))
    fill = bpy.context.active_object
    fill.data.energy = 300
    fill.data.size = 2.5

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.25, 0.25, 0.28)
    print("CAMERA face", tuple(round(x, 3) for x in cam_loc))


def build_bg():
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 2.5, 1.2))
    bpy.context.active_object.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.active_object.data.materials.append(mat_simple("Back", (0.22, 0.22, 0.26)))
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0.5, 0))
    bpy.context.active_object.data.materials.append(mat_simple("Floor", (0.14, 0.14, 0.16)))


def render_video(out: Path, fps, width, height, total):
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
    scene.render.image_settings.file_format = "PNG"

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        for f in range(1, total + 1):
            scene.frame_set(f)
            path = frame_dir / f"frame_{f:04d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            if f % 24 == 0:
                print(f"RENDER {f}/{total}")
        frames = sorted(frame_dir.glob("frame_*.png"))
        list_file = frame_dir / "list.txt"
        list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in frames))
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-r", str(fps),
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart",
            str(out),
        ])
        print("OUT", out, out.stat().st_size)


def main():
    args = parse_args(sys.argv)
    glb = Path(args["glb"]).resolve()
    out = Path(args["out"]).resolve()
    fps = int(args["fps"])
    seconds = int(args["seconds"])
    width = int(args["width"])
    height = int(args["height"])
    total = fps * seconds

    if not glb.exists():
        alt = glb.parent / "Mike.glb"
        if alt.exists():
            glb = alt
        else:
            raise SystemExit(f"Missing {glb}")

    clear_scene()
    build_bg()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    print("IMPORTED", glb)

    arm, body, meshes = find_arm_body()
    if body is None:
        raise SystemExit("No body")
    print("BODY verts", len(body.data.vertices))

    place_character(arm, body, meshes)
    kb = ensure_mouth_shape_key(body)
    sequence_body(arm, fps, total)
    animate_mouth(kb, fps, total)
    setup_camera_face(arm, body)
    render_video(out, fps, width, height, total)
    print("DONE mouth talk")


if __name__ == "__main__":
    main()
