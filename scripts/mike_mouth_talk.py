#!/usr/bin/env python3
"""
Mike mouth talk with REAL mesh deformation + textures.
- Shape key mouth_open: lower lip/chin down, slight upper lift, corners out (jaw-like)
- Show basecolor texture (model has Mike_basecolor jpeg + normal)
- Never animate Root/Hips for face
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
    root.location = (0.0, 0.70, -min_c.z * scale)
    bpy.context.view_layer.update()
    print("PLACE height", round(height, 3), "scale", round(scale, 3))
    return root


def ensure_textures_visible(body):
    """Force materials to show basecolor texture; log what we found."""
    if body is None:
        return
    for slot in body.material_slots:
        mat = slot.material
        if mat is None:
            continue
        print("MATERIAL", mat.name, "nodes", mat.use_nodes)
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                print("  TEX", node.image.name, node.image.size[:]
                      if hasattr(node.image, "size") else "?")
            if node.type == "BSDF_PRINCIPLED":
                # Keep textured look readable under workbench/eevee
                if "Roughness" in node.inputs:
                    node.inputs["Roughness"].default_value = min(
                        0.85, max(0.35, node.inputs["Roughness"].default_value)
                    )
    # Ensure UV map exists name
    if body.data.uv_layers:
        print("UV_LAYERS", [u.name for u in body.data.uv_layers])


def ensure_mouth_shape_key(body):
    """
    Jaw-like mouth_open (not a face bubble):
    - Lower mouth band: strong downward + slight forward
    - Upper lip band: small upward only near lip line
    - Corners: mild outward
    - Weight falls off fast outside lip region
    """
    if body is None:
        raise SystemExit("No body mesh")

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

    print("MESH_BOUNDS h", round(h, 3))

    # Tighter lip band (lower face only)
    mouth_z0 = mn.z + h * 0.64
    mouth_z1 = mn.z + h * 0.76
    mouth_x_half = size.x * 0.18

    # Displacements as fraction of height — visible but local
    lower_down = h * 0.048
    upper_up = h * 0.012
    fwd = h * 0.016
    corner = h * 0.010

    kb = body.shape_key_add(name="mouth_open", from_mix=False)
    moved = 0

    for i, v in enumerate(me.vertices):
        if not (mouth_z0 <= v.co.z <= mouth_z1):
            continue
        dx = abs(v.co.x - cx)
        if dx > mouth_x_half:
            continue
        # Front of head only (model typically faces -Y after import)
        depth = (v.co.y - mn.y) / max(1e-6, size.y)
        if depth > 0.50:
            continue

        tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)  # 0 bottom .. 1 top
        tx = 1.0 - dx / mouth_x_half
        # Soft falloff at sides
        w = max(0.0, tx) ** 0.65

        # Lip line ~ tz 0.45: below = lower lip/chin, above = upper lip
        if tz < 0.48:
            # Lower: strongest at center bottom
            lip_w = w * (1.0 - abs(tz - 0.25) * 1.2)
            lip_w = max(0.0, min(1.0, lip_w))
            if lip_w < 0.08:
                continue
            kb.data[i].co.z -= lower_down * lip_w * (1.15 - tz)
            kb.data[i].co.y -= fwd * lip_w  # toward camera if facing -Y
            kb.data[i].co.x += corner * lip_w * (0.6 if v.co.x >= cx else -0.6)
            moved += 1
        else:
            # Upper lip: only a thin band near the line, small up
            lip_w = w * max(0.0, 1.0 - abs(tz - 0.55) * 3.0)
            if lip_w < 0.12:
                continue
            kb.data[i].co.z += upper_up * lip_w
            kb.data[i].co.y -= fwd * 0.35 * lip_w
            moved += 1

    print("SHAPEKEY_MOUTH_MOVED", moved, "of", len(me.vertices))

    if moved < 80:
        print("WIDEN fallback")
        mouth_z0 = mn.z + h * 0.60
        mouth_z1 = mn.z + h * 0.80
        mouth_x_half = size.x * 0.26
        for i, v in enumerate(me.vertices):
            if not (mouth_z0 <= v.co.z <= mouth_z1):
                continue
            if abs(v.co.x - cx) > mouth_x_half:
                continue
            depth = (v.co.y - mn.y) / max(1e-6, size.y)
            if depth > 0.60:
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
    speech = [(0.3, 3.2), (3.6, 6.8), (7.2, 9.7)]
    cycle = max(5, int(fps * 0.30))

    def in_speech(t):
        return any(a <= t <= b for a, b in speech)

    for f in range(1, total + 1):
        t = f / float(fps)
        if in_speech(t):
            phase = ((f - 1) % cycle) / float(cycle)
            # open fast, close a bit slower
            if phase < 0.45:
                val = phase / 0.45
            else:
                val = 1.0 - (phase - 0.45) / 0.55
            val = max(0.0, min(1.0, val))
            val = val ** 0.85  # slightly hold open
        else:
            val = 0.03 * abs(math.sin(t * 2.0))
        kb.value = val
        kb.keyframe_insert(data_path="value", frame=f)
    print("MOUTH_KEYS frames", total)


def setup_camera_face(arm, body):
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

    aim = head + Vector((0, 0, -0.06))
    cam_loc = Vector((aim.x, aim.y - 1.20, aim.z))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (aim - cam_loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=(1.5, -2.5, 5))
    bpy.context.active_object.data.energy = 4.5
    bpy.ops.object.light_add(type="AREA", location=(0.3, -1.2, aim.z + 0.2))
    fill = bpy.context.active_object
    fill.data.energy = 250
    fill.data.size = 2.5

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.20, 0.20, 0.24)
    print("CAMERA face", tuple(round(x, 3) for x in cam_loc))


def build_bg():
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 2.5, 1.2))
    bpy.context.active_object.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.active_object.data.materials.append(mat_simple("Back", (0.18, 0.18, 0.22)))
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0.5, 0))
    bpy.context.active_object.data.materials.append(mat_simple("Floor", (0.12, 0.12, 0.14)))


def setup_render_engine(scene):
    """Prefer EEVEE for textures; fall back to Workbench TEXTURE."""
    engines = []
    try:
        engines = list(bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys())
    except Exception:
        pass
    # Blender 4/5 names vary
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "EEVEE"):
        try:
            scene.render.engine = name
            print("ENGINE", name)
            try:
                scene.eevee.taa_render_samples = 16
            except Exception:
                pass
            return "EEVEE"
        except Exception:
            continue

    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_shadows = False
        scene.display.shading.show_specular_highlight = True
    except Exception as e:
        print("WORKBENCH_SHADE_ERR", e)
        try:
            scene.display.shading.color_type = "MATERIAL"
        except Exception:
            pass
    print("ENGINE WORKBENCH TEXTURE")
    return "WORKBENCH"


def render_video(out: Path, fps, width, height, total):
    scene = bpy.context.scene
    setup_render_engine(scene)
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

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
    ensure_textures_visible(body)
    kb = ensure_mouth_shape_key(body)
    sequence_body(arm, fps, total)
    animate_mouth(kb, fps, total)
    setup_camera_face(arm, body)
    render_video(out, fps, width, height, total)
    print("DONE mouth talk textured")


if __name__ == "__main__":
    main()
