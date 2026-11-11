"""
Blender 3D Mike v3 — connected cartoon figure matching 2D Mike colors.
Yellow hoodie, brown skin, navy pants. Classroom set.
Workbench engine for GitHub Actions.

blender -b -noaudio -P blender_mike3d.py -- \
  --out assets/blender/mike3d_test.mp4 --seconds 4 --width 720 --height 1280
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

# Match write_mezi_assets.py
HOODIE = (1.0, 0.80, 0.16)
HOODIE_D = (0.90, 0.66, 0.08)
HOODIE_L = (1.0, 0.90, 0.45)
SKIN = (0.77, 0.55, 0.37)
SKIN_D = (0.64, 0.42, 0.27)
HAIR = (0.10, 0.07, 0.05)
PANTS = (0.11, 0.16, 0.28)
SHOE = (0.10, 0.10, 0.12)
SHOE_W = (0.95, 0.95, 0.97)
BADGE_C = (0.14, 0.20, 0.32)
WHITE = (0.98, 0.98, 0.99)
MOUTH_C = (0.55, 0.18, 0.20)


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
    m.use_nodes = False
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


def parent(child, parent_obj):
    child.parent = parent_obj


def build_room():
    # Floor
    floor = mesh("primitive_plane_add", size=16, location=(0, 0, 0))
    floor.data.materials.append(mat("Floor", (0.40, 0.26, 0.15)))

    # Back wall
    wall = mesh("primitive_cube_add", size=1, location=(0, 4.0, 2.4))
    wall.scale = (8, 0.15, 2.6)
    wall.data.materials.append(mat("Wall", (0.80, 0.88, 0.92)))

    # Yellow accent stripe
    stripe = mesh("primitive_cube_add", size=1, location=(0, 3.9, 0.5))
    stripe.scale = (7.5, 0.05, 0.16)
    stripe.data.materials.append(mat("Stripe", HOODIE, emit=0.2))

    # Side walls
    for x in (-7.0, 7.0):
        sw = mesh("primitive_cube_add", size=1, location=(x, 0.5, 2.2))
        sw.scale = (0.12, 5.5, 2.4)
        sw.data.materials.append(mat("Side", (0.74, 0.82, 0.88)))

    # Ceiling
    ceil = mesh("primitive_plane_add", size=16, location=(0, 0.5, 4.8))
    ceil.rotation_euler = (math.radians(180), 0, 0)
    ceil.data.materials.append(mat("Ceil", (0.93, 0.95, 0.97)))

    # Ceiling lights
    for x in (-2.0, 2.0):
        lamp = mesh("primitive_cube_add", size=1, location=(x, 1.0, 4.65))
        lamp.scale = (1.0, 0.4, 0.05)
        lamp.data.materials.append(mat("Lamp", (1.0, 0.97, 0.85), emit=0.6))

    # Board
    frame = mesh("primitive_cube_add", size=1, location=(0, 3.85, 2.6))
    frame.scale = (3.8, 0.1, 1.9)
    frame.data.materials.append(mat("Frame", (0.30, 0.18, 0.10)))
    board = mesh("primitive_cube_add", size=1, location=(0, 3.78, 2.6))
    board.scale = (3.5, 0.05, 1.7)
    board.data.materials.append(mat("Board", (0.15, 0.40, 0.28)))
    for i, z in enumerate((3.0, 2.6, 2.2)):
        line = mesh("primitive_cube_add", size=1, location=(0, 3.72, z))
        line.scale = (2.8, 0.01, 0.012)
        line.data.materials.append(mat(f"Chalk{i}", (0.88, 0.92, 0.88), emit=0.1))

    # Desk further forward, lower profile so full Mike visible
    desk = mesh("primitive_cube_add", size=1, location=(0, -1.1, 0.55))
    desk.scale = (2.0, 0.7, 0.06)
    desk.data.materials.append(mat("Desk", (0.48, 0.32, 0.18)))
    for x in (-0.9, 0.9):
        for y in (-1.3, -0.9):
            leg = mesh("primitive_cylinder_add", radius=0.04, depth=0.55, location=(x, y, 0.27))
            leg.data.materials.append(mat("DLeg", (0.25, 0.16, 0.1)))

    # Books
    for i, c in enumerate([(0.9, 0.3, 0.2), (0.2, 0.45, 0.9), (0.95, 0.75, 0.2)]):
        b = mesh("primitive_cube_add", size=1, location=(0.7, -1.2, 0.65 + i * 0.06))
        b.scale = (0.32, 0.25, 0.035)
        b.rotation_euler = (0, 0, math.radians(6 * i))
        b.data.materials.append(mat(f"Book{i}", c))

    # Rug under Mike
    rug = mesh("primitive_cylinder_add", radius=1.0, depth=0.025, location=(0, 1.15, 0.02))
    rug.data.materials.append(mat("Rug", (0.12, 0.22, 0.42)))

    # Window glow
    win = mesh("primitive_cube_add", size=1, location=(6.6, 1.5, 2.5))
    win.scale = (0.06, 1.5, 1.2)
    win.data.materials.append(mat("Win", (0.7, 0.88, 1.0), emit=0.5))


def build_mike():
    """Connected stylized Mike. Root empty at pelvis; all parts parented."""
    # Root
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 1.2, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    # --- Legs ---
    for side, x in (("L", -0.14), ("R", 0.14)):
        thigh = mesh("primitive_cylinder_add", radius=0.11, depth=0.5, location=(x, 0, 0.55))
        thigh.name = f"Thigh{side}"
        thigh.data.materials.append(mat(f"Pants{side}", PANTS))
        parent(thigh, root)

        shin = mesh("primitive_cylinder_add", radius=0.09, depth=0.42, location=(x, 0, 0.18))
        shin.name = f"Shin{side}"
        shin.data.materials.append(mat(f"Shin{side}", PANTS))
        parent(shin, root)

        shoe = mesh("primitive_cube_add", size=1, location=(x, -0.06, 0.04))
        shoe.scale = (0.13, 0.22, 0.07)
        shoe.data.materials.append(mat(f"Shoe{side}", SHOE))
        parent(shoe, root)

        sole = mesh("primitive_cube_add", size=1, location=(x, -0.07, 0.005))
        sole.scale = (0.135, 0.24, 0.015)
        sole.data.materials.append(mat(f"Sole{side}", SHOE_W))
        parent(sole, root)

    # Hips
    hips = mesh("primitive_cube_add", size=1, location=(0, 0, 0.85))
    hips.scale = (0.34, 0.18, 0.12)
    hips.data.materials.append(mat("Hips", PANTS))
    parent(hips, root)

    # --- Torso (yellow hoodie) — larger, human proportion ---
    torso = mesh("primitive_cube_add", size=1, location=(0, 0, 1.35))
    torso.name = "Torso"
    torso.scale = (0.38, 0.22, 0.42)
    torso.data.materials.append(mat("Hoodie", HOODIE))
    parent(torso, root)

    # Pocket panel
    pocket = mesh("primitive_cube_add", size=1, location=(0, -0.2, 1.25))
    pocket.scale = (0.2, 0.03, 0.18)
    pocket.data.materials.append(mat("Pocket", HOODIE_D))
    parent(pocket, root)

    # Drawstrings
    for x in (-0.07, 0.07):
        s = mesh("primitive_cylinder_add", radius=0.012, depth=0.22, location=(x, -0.22, 1.2))
        s.data.materials.append(mat("String", WHITE))
        parent(s, root)
        tip = mesh("primitive_uv_sphere_add", radius=0.018, location=(x, -0.22, 1.08))
        tip.data.materials.append(mat("STip", WHITE))
        parent(tip, root)

    # Hood (behind head, not a ring)
    hood = mesh("primitive_uv_sphere_add", radius=0.26, location=(0, 0.12, 1.78))
    hood.scale = (0.9, 0.55, 0.5)
    hood.data.materials.append(mat("Hood", HOODIE_D))
    parent(hood, root)

    # Badge
    badge = mesh("primitive_cube_add", size=1, location=(0.2, -0.2, 1.48))
    badge.scale = (0.07, 0.025, 0.055)
    badge.data.materials.append(mat("Badge", BADGE_C))
    parent(badge, root)
    bw = mesh("primitive_cube_add", size=1, location=(0.2, -0.22, 1.48))
    bw.scale = (0.05, 0.015, 0.04)
    bw.data.materials.append(mat("BadgeW", WHITE))
    parent(bw, root)

    # --- Arms: shoulder joint at torso side, upper + lower + hand connected ---
    for side, xsign in (("L", -1), ("R", 1)):
        sx = 0.38 * xsign
        # Upper arm from shoulder, angled down-out
        ua = mesh(
            "primitive_cylinder_add",
            radius=0.085,
            depth=0.38,
            location=(sx + 0.12 * xsign, 0, 1.42),
        )
        ua.rotation_euler = (0, math.radians(25 * xsign), math.radians(-15 * xsign))
        ua.data.materials.append(mat(f"UA{side}", HOODIE))
        parent(ua, root)

        # Elbow position roughly
        ex = sx + 0.28 * xsign
        ez = 1.15
        la = mesh(
            "primitive_cylinder_add",
            radius=0.075,
            depth=0.36,
            location=(ex, -0.05, ez),
        )
        la.rotation_euler = (math.radians(20), math.radians(10 * xsign), 0)
        la.data.materials.append(mat(f"LA{side}", HOODIE))
        parent(la, root)

        # Hand
        hx = ex + 0.05 * xsign
        hand = mesh("primitive_uv_sphere_add", radius=0.085, location=(hx, -0.08, 0.92))
        hand.scale = (0.9, 0.75, 1.05)
        hand.data.materials.append(mat(f"Hand{side}", SKIN))
        parent(hand, root)

    # --- Neck + Head ---
    neck = mesh("primitive_cylinder_add", radius=0.09, depth=0.14, location=(0, 0, 1.78))
    neck.data.materials.append(mat("Neck", SKIN))
    parent(neck, root)

    head = mesh("primitive_uv_sphere_add", radius=0.30, location=(0, 0, 2.12))
    head.name = "MikeHead"
    head.scale = (0.92, 0.95, 1.02)
    head.data.materials.append(mat("Head", SKIN))
    parent(head, root)

    # Ears
    for x in (-0.28, 0.28):
        ear = mesh("primitive_uv_sphere_add", radius=0.065, location=(x, 0, 2.1))
        ear.scale = (0.45, 0.7, 0.95)
        ear.data.materials.append(mat("Ear", SKIN_D))
        parent(ear, root)

    # Hair
    hair = mesh("primitive_uv_sphere_add", radius=0.32, location=(0, 0.05, 2.28))
    hair.scale = (0.95, 1.05, 0.7)
    hair.data.materials.append(mat("Hair", HAIR))
    parent(hair, root)
    for x, yo, zo in ((-0.1, -0.15, 0.05), (0.05, -0.18, 0.08), (0.14, -0.12, 0.02)):
        peak = mesh("primitive_uv_sphere_add", radius=0.09, location=(x, yo, 2.35 + zo))
        peak.scale = (0.7, 0.85, 1.0)
        peak.data.materials.append(mat("Peak", HAIR))
        parent(peak, root)

    # Eyes
    for x in (-0.09, 0.09):
        w = mesh("primitive_uv_sphere_add", radius=0.065, location=(x, -0.26, 2.14))
        w.scale = (0.85, 0.5, 1.0)
        w.data.materials.append(mat("EyeW", WHITE))
        parent(w, root)
        iris = mesh("primitive_uv_sphere_add", radius=0.038, location=(x, -0.30, 2.14))
        iris.data.materials.append(mat("Iris", (0.16, 0.10, 0.06)))
        parent(iris, root)
        pupil = mesh("primitive_uv_sphere_add", radius=0.02, location=(x, -0.32, 2.14))
        pupil.data.materials.append(mat("Pupil", (0.04, 0.03, 0.03)))
        parent(pupil, root)
        shine = mesh("primitive_uv_sphere_add", radius=0.01, location=(x - 0.012, -0.33, 2.16))
        shine.data.materials.append(mat("Shine", WHITE, emit=0.3))
        parent(shine, root)

    # Brows
    for x in (-0.09, 0.09):
        brow = mesh("primitive_cube_add", size=1, location=(x, -0.28, 2.26))
        brow.scale = (0.065, 0.015, 0.012)
        brow.rotation_euler = (0, 0, math.radians(10 if x > 0 else -10))
        brow.data.materials.append(mat("Brow", HAIR))
        parent(brow, root)

    # Nose
    nose = mesh("primitive_uv_sphere_add", radius=0.035, location=(0, -0.28, 2.02))
    nose.scale = (0.7, 0.85, 1.0)
    nose.data.materials.append(mat("Nose", SKIN_D))
    parent(nose, root)

    # Mouth
    mouth = mesh("primitive_cube_add", size=1, location=(0, -0.28, 1.9))
    mouth.name = "MikeMouth"
    mouth.scale = (0.08, 0.025, 0.022)
    mouth.data.materials.append(mat("Mouth", MOUTH_C))
    parent(mouth, root)

    # Cheeks
    for x in (-0.16, 0.16):
        cheek = mesh("primitive_uv_sphere_add", radius=0.045, location=(x, -0.22, 1.98))
        cheek.scale = (1.0, 0.5, 0.8)
        cheek.data.materials.append(mat("Cheek", (0.85, 0.48, 0.40), emit=0.08))
        parent(cheek, root)

    return root, head, mouth


def setup_camera_lights():
    bpy.ops.object.light_add(type="SUN", location=(3, -4, 7))
    sun = bpy.context.active_object
    sun.data.energy = 2.6
    sun.rotation_euler = (math.radians(50), math.radians(12), 0)

    bpy.ops.object.light_add(type="AREA", location=(-2.5, -2, 3.5))
    fill = bpy.context.active_object
    fill.data.energy = 55
    fill.data.size = 3

    bpy.ops.object.light_add(type="AREA", location=(4, 1, 3))
    rim = bpy.context.active_object
    rim.data.energy = 35
    rim.data.size = 2

    # Camera: full-body vertical, Mike centered, desk at bottom only
    bpy.ops.object.camera_add(location=(0, -4.0, 1.55))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(88), 0, 0)
    cam.data.lens = 32
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.58, 0.70, 0.80)


def animate(root, head, mouth, fps, total_frames):
    for f in range(1, total_frames + 1):
        t = f / float(fps)
        # gentle body sway
        root.rotation_euler = (0, 0, math.radians(2.5 * math.sin(t * 1.5)))
        root.keyframe_insert(data_path="rotation_euler", frame=f)
        # head bob
        head.location.z = 2.12 + 0.018 * math.sin(t * 2.6)
        head.rotation_euler = (
            math.radians(2 * math.sin(t * 1.3)),
            0,
            math.radians(4 * math.sin(t * 1.6)),
        )
        head.keyframe_insert(data_path="location", frame=f, index=2)
        head.keyframe_insert(data_path="rotation_euler", frame=f)
        # mouth chatter
        open_z = 0.018 + 0.03 * abs(math.sin(t * 8.0))
        mouth.scale = (0.08, 0.025, open_z)
        mouth.keyframe_insert(data_path="scale", frame=f)


def setup_render(out_path: Path, fps, total_frames, width, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_shadows = True
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
    build_room()
    root, head, mouth = build_mike()
    setup_camera_lights()
    animate(root, head, mouth, fps, total_frames)

    out = Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    setup_render(out, fps, total_frames, width, height)
    print(f"Render Mike3D v3 {total_frames}f {width}x{height} -> {out}")
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
