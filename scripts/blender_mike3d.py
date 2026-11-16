"""
Blender 3D Mike — play baked clips from Mikeanim.glb in sequence.
Short vertical test with transitions between multiple actions.
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
        "out": "assets/blender/mike3d_test.mp4",
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


def action_duration_frames(action, fps):
    """Return length of action in frames (at least 1)."""
    if action is None:
        return 1
    # Blender 5: frame_range on action
    fr = getattr(action, "frame_range", None)
    if fr is not None and len(fr) >= 2:
        span = float(fr[1]) - float(fr[0])
        if span > 0.5:
            return max(1, int(round(span)))
    # Fallback: scan fcurves / layered
    mn, mx = None, None
    def consider(fc):
        nonlocal mn, mx
        for kp in fc.keyframe_points:
            f = kp.co[0]
            mn = f if mn is None else min(mn, f)
            mx = f if mx is None else max(mx, f)
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        for fc in fcurves:
            consider(fc)
    else:
        for layer in getattr(action, "layers", []) or []:
            for strip in getattr(layer, "strips", []) or []:
                bags = getattr(strip, "channelbags", None)
                if bags is None:
                    bag = getattr(strip, "channelbag", None)
                    bags = [bag] if bag else []
                for bag in bags or []:
                    if bag is None:
                        continue
                    for fc in getattr(bag, "fcurves", []) or []:
                        consider(fc)
    if mn is None or mx is None:
        return max(1, fps)  # 1s default
    return max(1, int(round(mx - mn)))


def list_actions():
    return list(bpy.data.actions)


def pick_clip_sequence(actions):
    """Prefer teaching uuid, Agree_Gesture, Alert — short multi-clip demo."""
    by_name = {a.name: a for a in actions}
    names = list(by_name.keys())
    print("ACTIONS_AVAILABLE", names)

    preferred = []
    # teaching gesture (unnamed uuid from Tripo/Meshy)
    for n in names:
        if n.startswith("_"):
            preferred.append(n)
            break
    for key in ("Agree_Gesture", "Alert", "Casual_Walk", "Walking"):
        if key in by_name and key not in preferred:
            preferred.append(key)
    if not preferred:
        preferred = names[:3]
    # max 3 clips for short video
    preferred = preferred[:3]
    return [by_name[n] for n in preferred if n in by_name]


def import_mike_glb(glb_path: Path):
    if not glb_path.exists():
        # fall back to older Mike.glb
        alt = glb_path.parent / "Mike.glb"
        if alt.exists():
            print("FALLBACK", alt)
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
    print(
        "MIKE_CAPABILITY",
        "armature=" + str(bool(arm)),
        "meshes=" + str(len(meshes)),
        "bones=" + str(len(arm.pose.bones) if arm else 0),
        "new_actions=" + str(len(new_actions)),
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

    if arm and body:
        for mod in body.modifiers:
            if mod.type == "ARMATURE":
                try:
                    mod.use_deform_preserve_volume = True
                except Exception:
                    pass

    print("MIKE_GLB height", round(height, 3), "scale", round(scale, 3))
    return root, arm, body, new_actions or list_actions()


def sequence_clips_on_armature(arm, actions, fps, max_total_frames):
    """Place clips back-to-back on NLA so render plays transitions."""
    if arm is None:
        print("NO_ARMATURE")
        return 1

    clips = pick_clip_sequence(actions)
    if not clips:
        print("NO_CLIPS")
        return 1

    if not arm.animation_data:
        arm.animation_data_create()
    # clear old NLA
    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None

    track = arm.animation_data.nla_tracks.new()
    track.name = "MikeClips"

    frame = 1
    used = []
    for action in clips:
        dur = action_duration_frames(action, fps)
        # Cap each clip so total stays short (~12s)
        max_each = max(fps, max_total_frames // max(1, len(clips)))
        use = min(dur, max_each)
        # NLA strip: start at `frame`, action frame range
        fr = getattr(action, "frame_range", None)
        act_start = float(fr[0]) if fr is not None and len(fr) >= 2 else 0.0
        try:
            strip = track.strips.new(action.name, int(frame), action)
        except TypeError:
            # older API
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
        used.append((action.name, frame, frame + use, use))
        print(f"NLA_STRIP {action.name!r} frames {frame}-{frame+use} (len {use})")
        frame += use

    total = max(1, frame - 1)
    if total > max_total_frames:
        total = max_total_frames
    print("CLIP_SEQUENCE", used, "total_frames", total)
    return total


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
    seconds = min(max(float(args["seconds"]), 1.0), 20.0)
    max_frames = max(fps, int(round(seconds * fps)))
    width = int(args.get("width", 720))
    height = int(args.get("height", 1280))
    glb = Path(args["glb"]).resolve()

    clear_scene()
    build_room()
    root, arm, body, actions = import_mike_glb(glb)
    setup_camera_lights()
    total_frames = sequence_clips_on_armature(arm, actions, fps, max_frames)

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
