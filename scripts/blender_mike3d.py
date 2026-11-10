"""
Blender 3D Mike — matches 2D Mike (yellow hoodie, brown skin, navy pants).
Richer classroom set. Workbench-friendly for GitHub Actions.

blender -b -noaudio -P blender_mike3d.py -- \
  --out assets/blender/mike3d_test.mp4 --seconds 4 --width 720 --height 1280
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

# Colors aligned with write_mezi_assets.py (normalized 0-1)
HOODIE = (1.0, 0.80, 0.16)
HOODIE_D = (0.92, 0.68, 0.10)
HOODIE_L = (1.0, 0.90, 0.43)
SKIN = (0.77, 0.55, 0.37)
SKIN_D = (0.66, 0.44, 0.28)
SKIN_L = (0.86, 0.67, 0.49)
HAIR = (0.12, 0.09, 0.07)
PANTS = (0.11, 0.16, 0.27)
SHOE = (0.12, 0.12, 0.14)
SHOE_W = (0.96, 0.96, 0.97)
BADGE = (0.16, 0.22, 0.35)
WHITE = (0.98, 0.98, 0.99)
MOUTH = (0.59, 0.22, 0.24)


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
        r = min(1.0, r + emit * 0.35)
        g = min(1.0, g + emit * 0.35)
        b = min(1.0, b + emit * 0.4)
    m.diffuse_color = (r, g, b, 1.0)
    return m


def add(op, **kw):
    getattr(bpy.ops.mesh, op)(**kw)
    return bpy.context.active_object


def shade_smooth(obj):
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def build_classroom():
    # Floor — warm wood planks feel (single plane + strip accents)
    floor = add("primitive_plane_add", size=14, location=(0, 0.2, 0))
    floor.name = "Floor"
    floor.data.materials.append(mat("Floor", (0.42, 0.28, 0.16)))

    for i, y in enumerate((-1.2, 0.0, 1.2, 2.4)):
        plank = add("primitive_cube_add", size=1, location=(0, y, 0.01))
        plank.scale = (6.5, 0.55, 0.02)
        c = (0.38 + 0.04 * (i % 2), 0.24 + 0.03 * (i % 2), 0.13)
        plank.data.materials.append(mat(f"Plank{i}", c))

    # Back wall — soft teal-grey
    wall = add("primitive_cube_add", size=1, location=(0, 3.4, 2.3))
    wall.scale = (7.0, 0.12, 2.5)
    wall.data.materials.append(mat("WallBack", (0.78, 0.88, 0.92)))

    # Accent stripe on wall
    stripe = add("primitive_cube_add", size=1, location=(0, 3.32, 0.55))
    stripe.scale = (6.8, 0.04, 0.18)
    stripe.data.materials.append(mat("WallStripe", (1.0, 0.78, 0.15), emit=0.25))

    # Side walls
    for x, name in ((-6.2, "L"), (6.2, "R")):
        sw = add("primitive_cube_add", size=1, location=(x, 0.6, 2.1))
        sw.scale = (0.1, 5.0, 2.3)
        sw.data.materials.append(mat(f"Side{name}", (0.72, 0.82, 0.88)))

    # Ceiling
    ceil = add("primitive_plane_add", size=14, location=(0, 0.5, 4.5))
    ceil.rotation_euler = (math.radians(180), 0, 0)
    ceil.data.materials.append(mat("Ceiling", (0.92, 0.94, 0.96)))

    # Ceiling lights (glow panels)
    for x in (-2.2, 0.0, 2.2):
        lamp = add("primitive_cube_add", size=1, location=(x, 0.8, 4.35))
        lamp.scale = (0.9, 0.35, 0.04)
        lamp.data.materials.append(mat(f"CLight{x}", (1.0, 0.98, 0.85), emit=0.7))

    # Chalkboard with frame + green surface + chalk lines (thin cubes)
    frame = add("primitive_cube_add", size=1, location=(0, 3.25, 2.55))
    frame.scale = (3.6, 0.1, 1.85)
    frame.data.materials.append(mat("BoardFrame", (0.28, 0.18, 0.1)))
    board = add("primitive_cube_add", size=1, location=(0, 3.18, 2.55))
    board.scale = (3.3, 0.05, 1.65)
    board.data.materials.append(mat("Board", (0.14, 0.38, 0.26)))
    # chalk-ish horizontal guides
    for i, z in enumerate((2.9, 2.55, 2.2)):
        line = add("primitive_cube_add", size=1, location=(0, 3.12, z))
        line.scale = (2.6, 0.01, 0.015)
        line.data.materials.append(mat(f"Chalk{i}", (0.85, 0.9, 0.85), emit=0.15))

    # Yellow "MIKE" accent bar under board
    bar = add("primitive_cube_add", size=1, location=(0, 3.15, 1.55))
    bar.scale = (2.0, 0.05, 0.12)
    bar.data.materials.append(mat("MikeBar", HOODIE, emit=0.35))

    # Desk in foreground
    desk_top = add("primitive_cube_add", size=1, location=(0, -0.35, 0.72))
    desk_top.scale = (1.9, 0.85, 0.07)
    desk_top.data.materials.append(mat("DeskTop", (0.45, 0.3, 0.17)))
    for x in (-0.85, 0.85):
        for y in (-0.55, -0.15):
            leg = add("primitive_cylinder_add", radius=0.045, depth=0.7, location=(x, y, 0.35))
            leg.data.materials.append(mat("DeskLeg", (0.22, 0.15, 0.1)))

    # Books stack on desk
    colors = [(0.85, 0.25, 0.2), (0.2, 0.45, 0.85), (0.95, 0.75, 0.2)]
    for i, c in enumerate(colors):
        book = add("primitive_cube_add", size=1, location=(0.55, -0.5, 0.82 + i * 0.07))
        book.scale = (0.35, 0.28, 0.04)
        book.rotation_euler = (0, 0, math.radians(8 * i))
        book.data.materials.append(mat(f"Book{i}", c))

    # Poster panels on side wall
    for i, z in enumerate((2.8, 1.7)):
        poster = add("primitive_cube_add", size=1, location=(-5.9, 1.5, z))
        poster.scale = (0.04, 0.7, 0.55)
        poster.data.materials.append(
            mat(f"Poster{i}", (0.95, 0.55, 0.2) if i == 0 else (0.3, 0.55, 0.95), emit=0.2)
        )

    # Window glow (right)
    win = add("primitive_cube_add", size=1, location=(5.9, 1.2, 2.4))
    win.scale = (0.05, 1.4, 1.1)
    win.data.materials.append(mat("Window", (0.75, 0.9, 1.0), emit=0.55))
    # window frame cross
    for scale, loc in (
        ((0.06, 1.4, 0.06), (5.85, 1.2, 2.4)),
        ((0.06, 0.06, 1.1), (5.85, 1.2, 2.4)),
    ):
        fr = add("primitive_cube_add", size=1, location=loc)
        fr.scale = scale
        fr.data.materials.append(mat("WinFrame", (0.9, 0.9, 0.92)))

    # Floor rug under Mike
    rug = add("primitive_cylinder_add", radius=1.1, depth=0.03, location=(0, 1.0, 0.03))
    rug.data.materials.append(mat("Rug", (0.15, 0.25, 0.45)))


def build_mike():
    """Human-proportioned Mike: yellow hoodie, navy pants, brown skin."""
    # --- legs / pants ---
    for x in (-0.13, 0.13):
        thigh = add("primitive_cylinder_add", radius=0.12, depth=0.55, location=(x, 1.05, 0.55))
        thigh.data.materials.append(mat("Pants", PANTS))
        shade_smooth(thigh)
        shin = add("primitive_cylinder_add", radius=0.1, depth=0.45, location=(x, 1.05, 0.18))
        shin.data.materials.append(mat("Pants2", PANTS))
        shade_smooth(shin)
        # shoe
        shoe = add("primitive_cube_add", size=1, location=(x, 0.95, 0.05))
        shoe.scale = (0.14, 0.22, 0.07)
        shoe.data.materials.append(mat("Shoe", SHOE))
        sole = add("primitive_cube_add", size=1, location=(x, 0.92, 0.015))
        sole.scale = (0.145, 0.24, 0.02)
        sole.data.materials.append(mat("Sole", SHOE_W))

    # hips
    hips = add("primitive_cube_add", size=1, location=(0, 1.05, 0.88))
    hips.scale = (0.32, 0.18, 0.12)
    hips.data.materials.append(mat("Hips", PANTS))

    # --- torso / yellow hoodie ---
    torso = add("primitive_cube_add", size=1, location=(0, 1.05, 1.35))
    torso.name = "MikeTorso"
    torso.scale = (0.42, 0.24, 0.42)
    torso.data.materials.append(mat("Hoodie", HOODIE))
    shade_smooth(torso)

    # hoodie belly darker panel
    panel = add("primitive_cube_add", size=1, location=(0, 0.88, 1.28))
    panel.scale = (0.22, 0.04, 0.22)
    panel.data.materials.append(mat("HoodiePanel", HOODIE_D))

    # drawstrings
    for x in (-0.08, 0.08):
        s = add("primitive_cylinder_add", radius=0.012, depth=0.28, location=(x, 0.82, 1.25))
        s.data.materials.append(mat("String", WHITE))
        tip = add("primitive_uv_sphere_add", radius=0.02, location=(x, 0.82, 1.1))
        tip.data.materials.append(mat("StringTip", WHITE))

    # hoodie hood flap behind neck
    hood = add("primitive_uv_sphere_add", radius=0.28, location=(0, 1.22, 1.72))
    hood.scale = (0.95, 0.7, 0.55)
    hood.data.materials.append(mat("Hood", HOODIE_D))

    # collar ring
    collar = add("primitive_torus_add", major_radius=0.2, minor_radius=0.04, location=(0, 1.05, 1.72))
    collar.rotation_euler = (math.radians(90), 0, 0)
    collar.data.materials.append(mat("Collar", HOODIE_L))

    # badge (chest)
    badge = add("primitive_cube_add", size=1, location=(0.22, 0.84, 1.48))
    badge.scale = (0.08, 0.03, 0.06)
    badge.data.materials.append(mat("Badge", BADGE))
    badge_w = add("primitive_cube_add", size=1, location=(0.22, 0.82, 1.48))
    badge_w.scale = (0.06, 0.02, 0.045)
    badge_w.data.materials.append(mat("BadgeW", WHITE))

    # --- arms (hoodie sleeves + skin hands) ---
    # upper arms
    for x, ang in ((-0.48, 18), (0.48, -18)):
        ua = add("primitive_cylinder_add", radius=0.09, depth=0.42, location=(x, 1.05, 1.4))
        ua.rotation_euler = (0, math.radians(ang), 0)
        ua.data.materials.append(mat("Sleeve", HOODIE))
        shade_smooth(ua)
    # lower arms slightly out
    for x, ang in ((-0.62, 8), (0.62, -8)):
        la = add("primitive_cylinder_add", radius=0.08, depth=0.38, location=(x, 1.0, 1.05))
        la.rotation_euler = (math.radians(12), math.radians(ang), 0)
        la.data.materials.append(mat("Sleeve2", HOODIE))
        shade_smooth(la)
    # hands
    for x in (-0.7, 0.7):
        hand = add("primitive_uv_sphere_add", radius=0.09, location=(x, 0.95, 0.82))
        hand.scale = (0.85, 0.7, 1.1)
        hand.data.materials.append(mat("Hand", SKIN))
        shade_smooth(hand)

    # --- neck + head ---
    neck = add("primitive_cylinder_add", radius=0.1, depth=0.16, location=(0, 1.05, 1.78))
    neck.data.materials.append(mat("Neck", SKIN))
    shade_smooth(neck)

    head = add("primitive_uv_sphere_add", radius=0.32, location=(0, 1.05, 2.12))
    head.name = "MikeHead"
    head.scale = (0.92, 0.95, 1.05)
    head.data.materials.append(mat("Head", SKIN))
    shade_smooth(head)

    # ears
    for x in (-0.3, 0.3):
        ear = add("primitive_uv_sphere_add", radius=0.07, location=(x, 1.05, 2.1))
        ear.scale = (0.5, 0.7, 1.0)
        ear.data.materials.append(mat("Ear", SKIN_D))

    # hair cap + peaks (Mike's volume)
    hair = add("primitive_uv_sphere_add", radius=0.34, location=(0, 1.08, 2.28))
    hair.scale = (0.95, 1.05, 0.72)
    hair.data.materials.append(mat("Hair", HAIR))
    shade_smooth(hair)
    # front peaks
    for x, zoff in ((-0.12, 0.02), (0.05, 0.05), (0.18, 0.0)):
        peak = add("primitive_uv_sphere_add", radius=0.1, location=(x, 0.88, 2.35 + zoff))
        peak.scale = (0.7, 0.9, 1.1)
        peak.data.materials.append(mat("HairPeak", HAIR))

    # eyes — bigger, friendly
    for x in (-0.1, 0.1):
        white = add("primitive_uv_sphere_add", radius=0.07, location=(x, 0.78, 2.14))
        white.scale = (0.85, 0.55, 1.0)
        white.data.materials.append(mat("EyeW", WHITE))
        iris = add("primitive_uv_sphere_add", radius=0.04, location=(x, 0.74, 2.14))
        iris.data.materials.append(mat("Iris", (0.18, 0.11, 0.07)))
        pupil = add("primitive_uv_sphere_add", radius=0.022, location=(x, 0.72, 2.14))
        pupil.data.materials.append(mat("Pupil", (0.05, 0.04, 0.04)))
        shine = add("primitive_uv_sphere_add", radius=0.012, location=(x - 0.015, 0.71, 2.16))
        shine.data.materials.append(mat("Shine", WHITE, emit=0.4))

    # brows
    for x in (-0.1, 0.1):
        brow = add("primitive_cube_add", size=1, location=(x, 0.76, 2.26))
        brow.scale = (0.07, 0.02, 0.015)
        brow.rotation_euler = (0, 0, math.radians(8 if x > 0 else -8))
        brow.data.materials.append(mat("Brow", HAIR))

    # nose
    nose = add("primitive_uv_sphere_add", radius=0.04, location=(0, 0.76, 2.02))
    nose.scale = (0.7, 0.9, 1.0)
    nose.data.materials.append(mat("Nose", SKIN_D))

    # mouth (smile-ish)
    mouth = add("primitive_cube_add", size=1, location=(0, 0.75, 1.9))
    mouth.name = "MikeMouth"
    mouth.scale = (0.09, 0.03, 0.025)
    mouth.data.materials.append(mat("Mouth", MOUTH))

    # soft cheek tint
    for x in (-0.18, 0.18):
        cheek = add("primitive_uv_sphere_add", radius=0.05, location=(x, 0.82, 1.98))
        cheek.scale = (1.0, 0.5, 0.8)
        cheek.data.materials.append(mat("Cheek", (0.85, 0.5, 0.42), emit=0.1))

    return head, mouth


def setup_camera_lights():
    # Key sun from front-left
    bpy.ops.object.light_add(type="SUN", location=(2.5, -4, 7))
    sun = bpy.context.active_object
    sun.data.energy = 2.8
    sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(10))

    # Fill
    bpy.ops.object.light_add(type="AREA", location=(-2.5, -2.5, 3.2))
    fill = bpy.context.active_object
    fill.data.energy = 60
    fill.data.size = 3

    # Rim / window side
    bpy.ops.object.light_add(type="AREA", location=(4, 0.5, 3))
    rim = bpy.context.active_object
    rim.data.energy = 40
    rim.data.size = 2

    # Camera — slightly above eye, looking at Mike
    bpy.ops.object.camera_add(location=(0, -3.6, 1.85))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(82), 0, 0)
    cam.data.lens = 35
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.55, 0.68, 0.78)


def animate_mike(head, mouth, fps, total_frames):
    for f in range(1, total_frames + 1):
        t = f / float(fps)
        head.location.z = 2.12 + 0.02 * math.sin(t * 2.8)
        head.rotation_euler = (
            math.radians(2 * math.sin(t * 1.2)),
            0,
            math.radians(5 * math.sin(t * 1.4)),
        )
        head.keyframe_insert(data_path="location", frame=f, index=2)
        head.keyframe_insert(data_path="rotation_euler", frame=f)
        open_z = 0.02 + 0.035 * abs(math.sin(t * 8.5))
        mouth.scale = (0.09, 0.03, open_z)
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
