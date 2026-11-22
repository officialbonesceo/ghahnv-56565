#!/usr/bin/env python3
"""
Full 3D Mike teaching video — fixed face attach + framing.
- Face meshes parented in bone LOCAL space (no floating eyes)
- Character scaled once under MikeRoot
- Camera tracks head, waist-up fill of frame
- Body NLA gestures + face jaw/blink only (never root)
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector, Matrix


def parse_args(argv):
    args = {
        "glb": "assets/mike/Mikeanim.glb",
        "out": "assets/blender/mike_teach.mp4",
        "out_glb": "assets/mike/Mike_face.glb",
        "fps": 24,
        "seconds": 12,
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


def build_studio():
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 4.0, 1.5))
    back = bpy.context.active_object
    back.rotation_euler = (math.radians(90), 0, 0)
    back.data.materials.append(mat_simple("Back", (0.18, 0.20, 0.26)))

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0.8, 0))
    floor = bpy.context.active_object
    floor.data.materials.append(mat_simple("Floor", (0.12, 0.12, 0.14)))

    bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=0.04, location=(0, 0.7, 0.02))
    disc = bpy.context.active_object
    disc.data.materials.append(mat_simple("Disc", (0.08, 0.10, 0.14)))


def find_armature_and_body():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arm = None
    for a in arms:
        names = {b.name for b in a.data.bones}
        if "mixamorig:Head" in names or any("Head" in n for n in names):
            arm = a
            break
    if arm is None and arms:
        arm = arms[0]
    body = None
    skinned = []
    if arm and meshes:
        for m in meshes:
            if any(mod.type == "ARMATURE" and mod.object == arm for mod in m.modifiers):
                skinned.append(m)
        if skinned:
            body = max(skinned, key=lambda o: len(o.data.vertices))
        else:
            body = max(meshes, key=lambda o: len(o.data.vertices))
    return arm, body, meshes


def update_scene():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()


def bone_world(arm, bone_name):
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        return None
    return (arm.matrix_world @ pb.matrix) @ Vector((0, 0, 0))


def ensure_facial_bones(arm):
    head_name = None
    for n in ("mixamorig:Head", "Head", "head"):
        if n in arm.data.bones:
            head_name = n
            break
    if head_name is None:
        raise SystemExit("No Head bone")

    # Local offsets in Head bone space (Mixamo: +Y toward skull top roughly)
    face_defs = {
        "face_jaw": (Vector((0.0, -0.03, 0.02)), Vector((0.0, -0.08, 0.05))),
        "face_eye_L": (Vector((-0.035, 0.06, 0.05)), Vector((-0.035, 0.06, 0.08))),
        "face_eye_R": (Vector((0.035, 0.06, 0.05)), Vector((0.035, 0.06, 0.08))),
        "face_eyelid_L": (Vector((-0.035, 0.075, 0.055)), Vector((-0.035, 0.055, 0.055))),
        "face_eyelid_R": (Vector((0.035, 0.075, 0.055)), Vector((0.035, 0.055, 0.055))),
        "face_brow_L": (Vector((-0.035, 0.10, 0.05)), Vector((-0.035, 0.11, 0.07))),
        "face_brow_R": (Vector((0.035, 0.10, 0.05)), Vector((0.035, 0.11, 0.07))),
    }

    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = arm.data.edit_bones
    head_eb = ebones[head_name]
    created = {}
    for bname, (hoff, toff) in face_defs.items():
        eb = ebones.get(bname) or ebones.new(bname)
        hm = head_eb.matrix
        eb.head = hm @ hoff
        eb.tail = hm @ toff
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0.015, 0))
        eb.parent = head_eb
        eb.use_connect = False
        created[bname] = bname
        print("BONE_ADDED", bname)
    bpy.ops.object.mode_set(mode="OBJECT")
    for bname in created:
        db = arm.data.bones.get(bname)
        if db:
            db.use_deform = False
    update_scene()
    return created, head_name


def make_sphere(name, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, 0), segments=16, ring_count=10)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def make_cube(name, dims, mat):
    """dims = (sx, sy, sz) full size."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = Vector(dims)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    return obj


def parent_mesh_bone_local(mesh_obj, arm, bone_name, local_xyz):
    """
    Parent mesh to bone and set location in BONE local space.
    This keeps eyes on the head after armature/root scale.
    """
    mesh_obj.parent = arm
    mesh_obj.parent_type = "BONE"
    mesh_obj.parent_bone = bone_name
    # Clear inverse so local = bone space
    mesh_obj.matrix_parent_inverse = Matrix.Identity(4)
    mesh_obj.location = Vector(local_xyz)
    mesh_obj.rotation_euler = (0, 0, 0)
    mesh_obj.scale = (1, 1, 1)


def add_face_meshes(arm, bone_map, head_name):
    """
    Face parts sized from measured head span AFTER character scale.
    Parent in bone-local space so they stick to the head.
    """
    update_scene()
    head_w = bone_world(arm, head_name)
    top_w = bone_world(arm, "mixamorig:HeadTop_End")
    if head_w is None:
        raise SystemExit("Head world missing")

    head_h = 0.35
    if top_w is not None:
        head_h = max(0.15, (top_w - head_w).length)

    # Feature sizes proportional to head
    eye_r = head_h * 0.07
    pupil_r = eye_r * 0.40
    lid_w = head_h * 0.16
    lid_h = head_h * 0.04
    lid_d = head_h * 0.10
    brow_w = head_h * 0.15
    lip_w = head_h * 0.20

    print("HEAD_WORLD", tuple(round(x, 3) for x in head_w), "head_h", round(head_h, 3))

    mat_eye = mat_simple("FaceEye", (0.97, 0.97, 1.0))
    mat_pupil = mat_simple("FacePupil", (0.03, 0.03, 0.06))
    mat_lid = mat_simple("FaceLid", (0.68, 0.46, 0.36))
    mat_brow = mat_simple("FaceBrow", (0.12, 0.08, 0.05))
    mat_lip = mat_simple("FaceLip", (0.78, 0.24, 0.28))
    mat_teeth = mat_simple("FaceTeeth", (0.94, 0.92, 0.87))

    # Bone-local offsets (same space as face bone defs)
    # Eyes sit slightly forward of eye bones
    for side, bk, x in (("L", "face_eye_L", -1), ("R", "face_eye_R", 1)):
        eye = make_sphere(f"FaceEye_{side}", eye_r, mat_eye)
        parent_mesh_bone_local(eye, arm, bone_map[bk], (0, 0, eye_r * 0.3))
        pupil = make_sphere(f"FacePupil_{side}", pupil_r, mat_pupil)
        parent_mesh_bone_local(pupil, arm, bone_map[bk], (0, 0, eye_r * 0.9))

    for side, bk in (("L", "face_eyelid_L"), ("R", "face_eyelid_R")):
        lid = make_cube(f"FaceEyelid_{side}", (lid_w, lid_h, lid_d), mat_lid)
        parent_mesh_bone_local(lid, arm, bone_map[bk], (0, 0, 0))

    for side, bk in (("L", "face_brow_L"), ("R", "face_brow_R")):
        brow = make_cube(f"FaceBrow_{side}", (brow_w, head_h * 0.03, head_h * 0.05), mat_brow)
        parent_mesh_bone_local(brow, arm, bone_map[bk], (0, 0, 0))

    upper = make_cube("FaceUpperLip", (lip_w, head_h * 0.035, head_h * 0.06), mat_lip)
    parent_mesh_bone_local(upper, arm, head_name, (0, head_h * 0.02, head_h * 0.18))

    lower = make_cube("FaceLowerLip", (lip_w * 0.95, head_h * 0.04, head_h * 0.06), mat_lip)
    parent_mesh_bone_local(lower, arm, bone_map["face_jaw"], (0, 0, head_h * 0.05))

    teeth = make_cube("FaceTeeth", (lip_w * 0.8, head_h * 0.04, head_h * 0.04), mat_teeth)
    parent_mesh_bone_local(teeth, arm, bone_map["face_jaw"], (0, 0, head_h * 0.02))

    update_scene()
    # Sanity: eye world should be near head
    eye_obj = bpy.data.objects.get("FaceEye_L")
    if eye_obj:
        ew = eye_obj.matrix_world.translation
        dist = (ew - head_w).length
        print("EYE_L_WORLD", tuple(round(x, 3) for x in ew), "dist_to_head", round(dist, 3))
        if dist > head_h * 3:
            print("WARN face still far from head")
    print("FACE_MESHES_OK")


def place_character(arm, body, meshes):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "MikeRoot"

    # Bounds of body mesh only (ignore later face props)
    min_c = Vector((1e9, 1e9, 1e9))
    max_c = Vector((-1e9, -1e9, -1e9))
    targets = [body] if body else [m for m in (meshes or []) if m.type == "MESH"]
    for o in targets:
        if o is None:
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max(0.01, max_c.z - min_c.z)
    # Target ~1.7m tall in Blender units
    scale = 1.70 / height

    if arm and arm.parent is None:
        arm.parent = root
    for o in list(bpy.data.objects):
        if o.type in ("MESH", "ARMATURE") and o.parent is None and o != root:
            # don't parent studio planes
            if o.name in ("Back", "Floor", "Disc") or (o.data and o.data.name.startswith("Plane")):
                continue
            o.parent = root

    root.scale = (scale, scale, scale)
    # Feet on z=0
    root.location = (0.0, 0.70, -min_c.z * scale)
    root.rotation_euler = (0, 0, 0)
    update_scene()
    print("ROOT_PLACE height", round(height, 3), "scale", round(scale, 3), "root_z", round(root.location.z, 3))
    return root


def sequence_body_clips(arm, fps, total_frames):
    if not arm.animation_data:
        arm.animation_data_create()

    by_name = {a.name: a for a in bpy.data.actions}
    preferred = []
    for key in ("Agree_Gesture", "Alert", "Casual_Walk"):
        if key in by_name:
            preferred.append(by_name[key])
    for a in bpy.data.actions:
        if a.name.startswith("_") and a not in preferred:
            preferred.insert(0, a)
            break
    if not preferred:
        preferred = list(bpy.data.actions)[:2]

    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None

    track = arm.animation_data.nla_tracks.new()
    track.name = "BodyTeach"
    frame = 1
    for action in preferred:
        if frame > total_frames:
            break
        fr = getattr(action, "frame_range", None)
        span = int(fr[1] - fr[0]) if fr is not None and len(fr) >= 2 else fps * 3
        use = min(max(span, fps), total_frames - frame + 1, fps * 5)
        try:
            strip = track.strips.new(action.name[:40], int(frame), action)
        except TypeError:
            strip = track.strips.new(int(frame), action)
            strip.name = action.name[:40]
        strip.action = action
        strip.frame_start = frame
        strip.frame_end = frame + use
        try:
            strip.blend_type = "REPLACE"
            strip.extrapolation = "HOLD"
        except Exception:
            pass
        print("BODY_STRIP", action.name, frame, "->", frame + use)
        frame += use

    if frame < total_frames and preferred:
        action = preferred[-1]
        try:
            strip = track.strips.new(action.name[:40] + "_hold", int(frame), action)
        except TypeError:
            strip = track.strips.new(int(frame), action)
        strip.action = action
        strip.frame_start = frame
        strip.frame_end = total_frames
        try:
            strip.extrapolation = "HOLD"
        except Exception:
            pass
    return track


def animate_face_talk(arm, bone_map, fps, total_frames):
    act = bpy.data.actions.get("FaceTalk")
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new("FaceTalk")

    if not arm.animation_data:
        arm.animation_data_create()
    prev = arm.animation_data.action
    arm.animation_data.action = act

    jaw = arm.pose.bones[bone_map["face_jaw"]]
    lid_L = arm.pose.bones[bone_map["face_eyelid_L"]]
    lid_R = arm.pose.bones[bone_map["face_eyelid_R"]]
    brow_L = arm.pose.bones[bone_map["face_brow_L"]]
    brow_R = arm.pose.bones[bone_map["face_brow_R"]]
    for pb in (jaw, lid_L, lid_R, brow_L, brow_R):
        pb.rotation_mode = "XYZ"

    jaw_cycle = max(6, int(fps * 0.38))
    blink_period = max(20, int(fps * 2.4))
    blink_len = max(6, int(fps * 0.32))
    speech = [(0.4, 3.5), (4.0, 7.5), (8.0, 11.5)]

    def in_speech(t):
        return any(a <= t <= b for a, b in speech)

    for f in range(1, total_frames + 1):
        t = f / float(fps)
        if in_speech(t):
            phase = ((f - 1) % jaw_cycle) / float(jaw_cycle)
            ang = 28.0 * math.sin(phase * math.pi)
        else:
            ang = 2.0 * abs(math.sin(t * 1.5))
        jaw.rotation_euler = (math.radians(ang), 0, 0)
        jaw.keyframe_insert(data_path="rotation_euler", frame=f)

        cycle_pos = (f - 1) % blink_period
        if cycle_pos < blink_len:
            mid = blink_len / 2.0
            tblink = cycle_pos / mid if cycle_pos <= mid else 1.0 - (cycle_pos - mid) / mid
            bang = -30.0 * tblink
        else:
            bang = 0.0
        lid_L.rotation_euler = (math.radians(bang), 0, 0)
        lid_R.rotation_euler = (math.radians(bang), 0, 0)
        lid_L.keyframe_insert(data_path="rotation_euler", frame=f)
        lid_R.keyframe_insert(data_path="rotation_euler", frame=f)

        raise_amt = 5.0 if in_speech(t) and ang > 10 else 0.0
        brow_L.rotation_euler = (math.radians(-raise_amt), 0, 0)
        brow_R.rotation_euler = (math.radians(-raise_amt), 0, 0)
        brow_L.keyframe_insert(data_path="rotation_euler", frame=f)
        brow_R.keyframe_insert(data_path="rotation_euler", frame=f)

    arm.animation_data.action = prev

    face_track = arm.animation_data.nla_tracks.new()
    face_track.name = "Face"
    strip = face_track.strips.new("FaceTalk", 1, act)
    strip.frame_start = 1
    strip.frame_end = total_frames
    try:
        strip.blend_type = "COMBINE"
        strip.extrapolation = "NOTHING"
    except Exception:
        pass
    print("FACE_TALK frames", total_frames)
    return act


def setup_camera_lights(arm, head_name):
    """Frame head + upper torso filling the vertical video."""
    update_scene()
    head_w = bone_world(arm, head_name) or Vector((0, 0.7, 1.4))
    hips_w = bone_world(arm, "mixamorig:Hips") or Vector((0, 0.7, 0.7))

    # Aim point: between chest and face
    aim = Vector((
        head_w.x,
        head_w.y,
        (head_w.z + hips_w.z) * 0.55 + head_w.z * 0.15,
    ))
    # Camera in front, close enough that character is large
    dist = 2.0
    cam_loc = Vector((aim.x, aim.y - dist, aim.z + 0.05))

    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    direction = aim - cam_loc
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    bpy.context.scene.camera = cam
    print("CAMERA aim", tuple(round(x, 3) for x in aim), "loc", tuple(round(x, 3) for x in cam_loc))

    bpy.ops.object.light_add(type="SUN", location=(2.0, -3.0, 6.0))
    sun = bpy.context.active_object
    sun.data.energy = 5.5
    sun.rotation_euler = (math.radians(40), math.radians(12), 0)

    bpy.ops.object.light_add(type="AREA", location=(0, -1.5, aim.z))
    fill = bpy.context.active_object
    fill.data.energy = 280
    fill.data.size = 3.5

    bpy.ops.object.light_add(type="AREA", location=(-2.0, 0.0, aim.z + 0.5))
    left = bpy.context.active_object
    left.data.energy = 140
    left.data.size = 2.5

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.22, 0.22, 0.26)
    return cam


def render_video(out_mp4: Path, fps: int, width: int, height: int, total_frames: int):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_shadows = False
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "PNG"

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        for f in range(1, total_frames + 1):
            scene.frame_set(f)
            path = frame_dir / f"frame_{f:04d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            if f % 24 == 0:
                print(f"RENDER {f}/{total_frames}")

        frames = sorted(frame_dir.glob("frame_*.png"))
        list_file = frame_dir / "list.txt"
        list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in frames))
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-r", str(fps),
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart",
            str(out_mp4),
        ])
        print("TEACH_MP4", out_mp4, out_mp4.stat().st_size)


def export_glb(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type in ("ARMATURE", "MESH"):
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_apply=False,
    )
    print("EXPORTED_GLB", path, path.stat().st_size if path.exists() else 0)


def main():
    args = parse_args(sys.argv)
    glb = Path(args["glb"]).resolve()
    out = Path(args["out"]).resolve()
    out_glb = Path(args["out_glb"]).resolve()
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
    build_studio()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    print("IMPORTED", glb)

    arm, body, meshes = find_armature_and_body()
    if arm is None:
        raise SystemExit("No armature")
    print("ARMATURE", arm.name, "bones", len(arm.data.bones))

    # Order matters: scale body first, THEN face bones/meshes in bone-local space
    place_character(arm, body, meshes)
    bone_map, head_name = ensure_facial_bones(arm)
    add_face_meshes(arm, bone_map, head_name)

    sequence_body_clips(arm, fps, total)
    animate_face_talk(arm, bone_map, fps, total)

    setup_camera_lights(arm, head_name)
    render_video(out, fps, width, height, total)

    for pb in arm.pose.bones:
        if pb.name.startswith("face_"):
            pb.rotation_euler = (0, 0, 0)
    export_glb(out_glb)
    print("DONE teach video")


if __name__ == "__main__":
    main()
