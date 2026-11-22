#!/usr/bin/env python3
"""
Add facial skeleton + separate face meshes to Mikeanim.glb.

Rules:
- NEVER move/scale/animate Root, SmartRigArmature, body mesh, or Hips for face
- Facial bones ONLY, parented to mixamorig:Head
- Separate eye / eyelid / brow / mouth meshes
- Blink = eyelid bone X rotation only
- Jaw open = jaw bone only
- Export GLB + full ~10s proof video with visible face motion
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
        "out_glb": "assets/mike/Mike_face.glb",
        "out_mp4": "assets/blender/mike_face_proof.mp4",
        "fps": 24,
        "width": 720,
        "height": 1280,
        "seconds": 10,
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
    if arm and meshes:
        for m in meshes:
            if any(mod.type == "ARMATURE" and mod.object == arm for mod in m.modifiers):
                body = m
                break
        if body is None:
            body = max(meshes, key=lambda o: len(o.data.vertices))
    return arm, body


def bone_world_head_tail(arm, bone_name):
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        return None, None
    m = arm.matrix_world @ pb.matrix
    head = m @ Vector((0, 0, 0))
    length = pb.length if pb.length > 1e-6 else 0.05
    tail = m @ Vector((0, length, 0))
    return head, tail


def ensure_facial_bones(arm):
    head_name = None
    for n in ("mixamorig:Head", "Head", "head"):
        if n in arm.data.bones:
            head_name = n
            break
    if head_name is None:
        raise SystemExit("No Head bone found in armature")

    face_defs = {
        "face_jaw": (Vector((0.0, -0.04, 0.02)), Vector((0.0, -0.12, 0.08))),
        "face_eye_L": (Vector((-0.05, 0.09, 0.08)), Vector((-0.05, 0.09, 0.12))),
        "face_eye_R": (Vector((0.05, 0.09, 0.08)), Vector((0.05, 0.09, 0.12))),
        "face_eyelid_L": (Vector((-0.05, 0.11, 0.09)), Vector((-0.05, 0.08, 0.09))),
        "face_eyelid_R": (Vector((0.05, 0.11, 0.09)), Vector((0.05, 0.08, 0.09))),
        "face_brow_L": (Vector((-0.05, 0.14, 0.08)), Vector((-0.05, 0.15, 0.10))),
        "face_brow_R": (Vector((0.05, 0.14, 0.08)), Vector((0.05, 0.15, 0.10))),
    }

    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = arm.data.edit_bones
    head_eb = ebones.get(head_name)
    if head_eb is None:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise SystemExit(f"Edit bone {head_name} missing")

    created = {}
    for bname, (hoff, toff) in face_defs.items():
        if bname in ebones:
            eb = ebones[bname]
        else:
            eb = ebones.new(bname)
        hm = head_eb.matrix
        eb.head = hm @ hoff
        eb.tail = hm @ toff
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0.02, 0))
        eb.parent = head_eb
        eb.use_connect = False
        created[bname] = bname
        print(f"BONE_ADDED {bname} parent={head_name}")

    bpy.ops.object.mode_set(mode="OBJECT")
    for bname in created:
        db = arm.data.bones.get(bname)
        if db:
            db.use_deform = False
    return created, head_name


def mat_simple(name, color, alpha=1.0):
    m = bpy.data.materials.new(name=name)
    try:
        m.use_nodes = False
    except Exception:
        pass
    r, g, b = color
    m.diffuse_color = (r, g, b, alpha)
    return m


def make_sphere(name, radius, location, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=20, ring_count=12)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def make_cube(name, scale, location, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    return obj


def parent_mesh_to_bone(mesh_obj, arm, bone_name):
    mesh_obj.parent = arm
    mesh_obj.parent_type = "BONE"
    mesh_obj.parent_bone = bone_name
    mesh_obj.matrix_parent_inverse = (
        arm.matrix_world @ arm.pose.bones[bone_name].matrix
    ).inverted()


def add_face_meshes(arm, bone_map, head_name):
    """Larger, more visible face parts for clear motion in video."""
    head_w, _ = bone_world_head_tail(arm, head_name)
    if head_w is None:
        raise SystemExit("Cannot resolve Head world position")

    # Slightly exaggerated positions so pieces sit on/near the face front
    eye_L_w = head_w + Vector((-0.06, 0.11, 0.12))
    eye_R_w = head_w + Vector((0.06, 0.11, 0.12))
    mouth_w = head_w + Vector((0.0, 0.01, 0.14))
    brow_L_w = head_w + Vector((-0.06, 0.16, 0.11))
    brow_R_w = head_w + Vector((0.06, 0.16, 0.11))

    mat_eye = mat_simple("FaceEye", (0.98, 0.98, 1.0))
    mat_pupil = mat_simple("FacePupil", (0.02, 0.02, 0.05))
    mat_lid = mat_simple("FaceLid", (0.70, 0.48, 0.38))
    mat_brow = mat_simple("FaceBrow", (0.12, 0.08, 0.05))
    mat_lip = mat_simple("FaceLip", (0.80, 0.25, 0.30))
    mat_teeth = mat_simple("FaceTeeth", (0.95, 0.93, 0.88))

    meshes = {}

    for side, pos, bkey in (("L", eye_L_w, "face_eye_L"), ("R", eye_R_w, "face_eye_R")):
        eye = make_sphere(f"FaceEye_{side}", 0.030, pos, mat_eye)
        pupil = make_sphere(f"FacePupil_{side}", 0.012, pos + Vector((0, 0, 0.024)), mat_pupil)
        parent_mesh_to_bone(eye, arm, bone_map[bkey])
        parent_mesh_to_bone(pupil, arm, bone_map[bkey])
        meshes[f"eye_{side}"] = eye
        meshes[f"pupil_{side}"] = pupil

    # Thick eyelids — rotation is very visible
    for side, pos, bkey in (
        ("L", eye_L_w + Vector((0, 0.018, 0.01)), "face_eyelid_L"),
        ("R", eye_R_w + Vector((0, 0.018, 0.01)), "face_eyelid_R"),
    ):
        lid = make_cube(f"FaceEyelid_{side}", Vector((0.038, 0.010, 0.028)), pos, mat_lid)
        parent_mesh_to_bone(lid, arm, bone_map[bkey])
        meshes[f"eyelid_{side}"] = lid

    for side, pos, bkey in (("L", brow_L_w, "face_brow_L"), ("R", brow_R_w, "face_brow_R")):
        brow = make_cube(f"FaceBrow_{side}", Vector((0.040, 0.008, 0.014)), pos, mat_brow)
        parent_mesh_to_bone(brow, arm, bone_map[bkey])
        meshes[f"brow_{side}"] = brow

    jaw_bone = bone_map["face_jaw"]
    upper_lip = make_cube("FaceUpperLip", Vector((0.055, 0.010, 0.018)), mouth_w + Vector((0, 0.018, 0)), mat_lip)
    lower_lip = make_cube("FaceLowerLip", Vector((0.052, 0.012, 0.018)), mouth_w + Vector((0, -0.014, 0.008)), mat_lip)
    teeth = make_cube("FaceTeeth", Vector((0.045, 0.014, 0.012)), mouth_w + Vector((0, 0.0, -0.004)), mat_teeth)
    parent_mesh_to_bone(upper_lip, arm, head_name)
    parent_mesh_to_bone(lower_lip, arm, jaw_bone)
    parent_mesh_to_bone(teeth, arm, jaw_bone)
    meshes["upper_lip"] = upper_lip
    meshes["lower_lip"] = lower_lip
    meshes["teeth"] = teeth

    print("FACE_MESHES", list(meshes.keys()))
    return meshes


def animate_face_talking(arm, bone_map, fps=24, seconds=10):
    """
    Single long FaceTalk action:
    - Jaw cycles open/close (talking)
    - Periodic blinks on eyelids only
    - Mild brow raise on some beats
    Never keys root/hips/body.
    """
    if not arm.animation_data:
        arm.animation_data_create()

    total = max(1, int(fps * seconds))
    act = bpy.data.actions.get("FaceTalk")
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new("FaceTalk")
    arm.animation_data.action = act

    jaw = arm.pose.bones[bone_map["face_jaw"]]
    jaw.rotation_mode = "XYZ"
    lid_L = arm.pose.bones[bone_map["face_eyelid_L"]]
    lid_R = arm.pose.bones[bone_map["face_eyelid_R"]]
    lid_L.rotation_mode = "XYZ"
    lid_R.rotation_mode = "XYZ"
    brow_L = arm.pose.bones[bone_map["face_brow_L"]]
    brow_R = arm.pose.bones[bone_map["face_brow_R"]]
    brow_L.rotation_mode = "XYZ"
    brow_R.rotation_mode = "XYZ"

    # Jaw: open/close every ~0.4s (strong 40 deg)
    jaw_cycle = max(6, int(fps * 0.4))
    for f in range(1, total + 1):
        phase = ((f - 1) % jaw_cycle) / float(jaw_cycle)
        # half open, half close
        if phase < 0.5:
            t = phase / 0.5
            ang = 40.0 * t
        else:
            t = (phase - 0.5) / 0.5
            ang = 40.0 * (1.0 - t)
        jaw.rotation_euler = (math.radians(ang), 0.0, 0.0)
        jaw.keyframe_insert(data_path="rotation_euler", frame=f)

    # Blink every ~2.2s, duration ~0.35s, -40 deg (very clear)
    blink_period = max(20, int(fps * 2.2))
    blink_len = max(6, int(fps * 0.35))
    for f in range(1, total + 1):
        cycle_pos = (f - 1) % blink_period
        if cycle_pos < blink_len:
            # 0 -> closed -> 0
            mid = blink_len / 2.0
            if cycle_pos <= mid:
                t = cycle_pos / mid
            else:
                t = 1.0 - (cycle_pos - mid) / mid
            ang = -40.0 * t
        else:
            ang = 0.0
        lid_L.rotation_euler = (math.radians(ang), 0.0, 0.0)
        lid_R.rotation_euler = (math.radians(ang), 0.0, 0.0)
        lid_L.keyframe_insert(data_path="rotation_euler", frame=f)
        lid_R.keyframe_insert(data_path="rotation_euler", frame=f)

    # Occasional brow raise
    for f in range(1, total + 1):
        # raise slightly when jaw is more open
        phase = ((f - 1) % jaw_cycle) / float(jaw_cycle)
        raise_amt = 8.0 if 0.2 < phase < 0.55 else 0.0
        brow_L.rotation_euler = (math.radians(-raise_amt), 0.0, 0.0)
        brow_R.rotation_euler = (math.radians(-raise_amt), 0.0, 0.0)
        brow_L.keyframe_insert(data_path="rotation_euler", frame=f)
        brow_R.keyframe_insert(data_path="rotation_euler", frame=f)

    print(f"ACTION FaceTalk frames 1-{total} jaw+blink+brow (face bones only)")

    # NLA for export
    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new()
    tr.name = "Face"
    s = tr.strips.new("FaceTalk", 1, act)
    s.frame_end = total
    return act, total


def setup_proof_camera(arm, head_name):
    head_w, _ = bone_world_head_tail(arm, head_name)
    if head_w is None:
        head_w = Vector((0, 1.1, 0))
    # Tight front face camera
    cam_loc = head_w + Vector((0.0, -0.42, 0.08))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    direction = (head_w + Vector((0, 0.05, 0))) - cam_loc
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 55
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=head_w + Vector((1.5, -2.5, 3.5)))
    sun = bpy.context.active_object
    sun.data.energy = 6.0

    bpy.ops.object.light_add(type="AREA", location=head_w + Vector((0, -0.9, 0.6)))
    fill = bpy.context.active_object
    fill.data.energy = 350
    fill.data.size = 1.5

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.18, 0.18, 0.22)
    return cam


def render_full_video(out_mp4: Path, fps: int, width: int, height: int, arm, total_frames: int):
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

    act = bpy.data.actions.get("FaceTalk")
    if act is None:
        raise SystemExit("FaceTalk action missing")
    arm.animation_data.action = act

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        frames = []
        for f in range(1, total_frames + 1):
            scene.frame_set(f)
            path = frame_dir / f"frame_{f:04d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            frames.append(path)
            if f % 24 == 0:
                print(f"RENDER_PROGRESS {f}/{total_frames}")

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
        print("PROOF_MP4", out_mp4, out_mp4.stat().st_size, "frames", len(frames))


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
        export_morph=True,
        export_apply=False,
    )
    print("EXPORTED_GLB", path, path.stat().st_size if path.exists() else 0)


def verify_height(body, label):
    if body is None:
        return None
    corners = [body.matrix_world @ Vector(c) for c in body.bound_box]
    zs = [c.z for c in corners]
    ys = [c.y for c in corners]
    height = max(max(zs) - min(zs), max(ys) - min(ys))
    print(f"HEIGHT_{label}", round(height, 4))
    return height


def main():
    args = parse_args(sys.argv)
    glb = Path(args["glb"]).resolve()
    out_glb = Path(args["out_glb"]).resolve()
    out_mp4 = Path(args["out_mp4"]).resolve()
    fps = int(args["fps"])
    width = int(args["width"])
    height = int(args["height"])
    seconds = int(args.get("seconds", 10))

    if not glb.exists():
        alt = glb.parent / "Mike.glb"
        if alt.exists():
            glb = alt
        else:
            raise SystemExit(f"Missing GLB {glb}")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    print("IMPORTED", glb)

    arm, body = find_armature_and_body()
    if arm is None:
        raise SystemExit("No armature")
    print("ARMATURE", arm.name, "bones", len(arm.data.bones))
    print("BODY", body.name if body else None, "verts", len(body.data.vertices) if body else 0)

    h_before = verify_height(body, "BEFORE")
    hips = arm.pose.bones.get("mixamorig:Hips")
    hips_rest_loc = hips.location.copy() if hips else None

    bone_map, head_name = ensure_facial_bones(arm)
    print("FACIAL_BONES", bone_map)
    print("HEAD_PARENT", head_name)

    add_face_meshes(arm, bone_map, head_name)
    act, total = animate_face_talking(arm, bone_map, fps=fps, seconds=seconds)

    h_after = verify_height(body, "AFTER")
    if h_before and h_after and abs(h_before - h_after) > 0.05:
        raise SystemExit(f"Height changed {h_before} -> {h_after}")

    if hips and hips_rest_loc is not None:
        if (hips.location - hips_rest_loc).length > 1e-5:
            print("WARN hips location drifted — resetting")
            hips.location = hips_rest_loc

    setup_proof_camera(arm, head_name)
    render_full_video(out_mp4, fps, width, height, arm, total)

    for pb in arm.pose.bones:
        if pb.name.startswith("face_"):
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
    export_glb(out_glb)

    print("BONE_LIST_FINAL")
    for b in arm.data.bones:
        par = b.parent.name if b.parent else "None"
        if b.name.startswith("face_") or "Head" in b.name or "head" in b.name:
            print(f"  {b.name} parent={par} deform={b.use_deform}")

    print("DONE face rig OK full video")


if __name__ == "__main__":
    main()
