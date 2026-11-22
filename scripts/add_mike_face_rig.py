#!/usr/bin/env python3
"""
Add facial skeleton + separate face meshes to Mikeanim.glb.

Rules (from face-rig checklist):
- NEVER move/scale/animate Root, SmartRigArmature, body mesh, or Hips for face
- Facial bones ONLY, parented to mixamorig:Head
- Separate eye / eyelid / brow / mouth meshes (not merged into body)
- Blink = eyelid bone X rotation only (body/head/eyes must not move)
- Jaw open = jaw bone only
- Keep glTF Y-up via Blender import/export (no manual axis flip)
- Export new GLB + proof render (blink + jaw)

Usage:
  blender -b -noaudio -P scripts/add_mike_face_rig.py -- \
    --glb assets/mike/Mikeanim.glb \
    --out-glb assets/mike/Mike_face.glb \
    --out-mp4 assets/blender/mike_face_proof.mp4
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector, Euler, Matrix


def parse_args(argv):
    args = {
        "glb": "assets/mike/Mikeanim.glb",
        "out_glb": "assets/mike/Mike_face.glb",
        "out_mp4": "assets/blender/mike_face_proof.mp4",
        "fps": 24,
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
            if key in ("fps", "width", "height"):
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
    """World-space head/tail of a pose bone."""
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        return None, None
    # matrix is armature-object space -> world
    m = arm.matrix_world @ pb.matrix
    head = m @ Vector((0, 0, 0))
    # bone length along local Y in Blender armature
    length = pb.length if pb.length > 1e-6 else 0.05
    tail = m @ Vector((0, length, 0))
    return head, tail


def ensure_facial_bones(arm):
    """
    Add jaw / eyes / eyelids / brows under mixamorig:Head.
    Does NOT modify root, hips, or body weights.
    Returns dict of bone names created.
    """
    head_name = None
    for n in ("mixamorig:Head", "Head", "head"):
        if n in arm.data.bones:
            head_name = n
            break
    if head_name is None:
        raise SystemExit("No Head bone found in armature")

    # Measured proportions (from GLB inspect, relative to head height ~0.66)
    # Offsets in Blender rest space: after glTF import, Mixamo bones align
    # roughly with character; we place children in Head LOCAL space.
    # Head local: +Y along skull toward top, +Z roughly forward after import.

    face_defs = {
        # name: (head_local_offset, tail_local_offset)
        "face_jaw": (Vector((0.0, -0.04, 0.02)), Vector((0.0, -0.10, 0.06))),
        "face_eye_L": (Vector((-0.045, 0.08, 0.07)), Vector((-0.045, 0.08, 0.10))),
        "face_eye_R": (Vector((0.045, 0.08, 0.07)), Vector((0.045, 0.08, 0.10))),
        "face_eyelid_L": (Vector((-0.045, 0.095, 0.075)), Vector((-0.045, 0.08, 0.075))),
        "face_eyelid_R": (Vector((0.045, 0.095, 0.075)), Vector((0.045, 0.08, 0.075))),
        "face_brow_L": (Vector((-0.045, 0.12, 0.07)), Vector((-0.045, 0.13, 0.08))),
        "face_brow_R": (Vector((0.045, 0.12, 0.07)), Vector((0.045, 0.13, 0.08))),
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
        # Place in Head local space
        # edit bone head/tail are in armature local space
        # Convert Head-local offset -> armature space via head bone matrix
        # In edit mode, use head_eb matrix
        hm = head_eb.matrix  # 4x4 armature-space
        eb.head = hm @ hoff
        eb.tail = hm @ toff
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0.02, 0))
        eb.parent = head_eb
        eb.use_connect = False
        created[bname] = bname
        print(f"BONE_ADDED {bname} parent={head_name}")

    bpy.ops.object.mode_set(mode="OBJECT")

    # Deform off for control-style face bones (meshes parented, not skinned)
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
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=16, ring_count=8)
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
    """Bone-relative parenting so mesh follows bone only."""
    mesh_obj.parent = arm
    mesh_obj.parent_type = "BONE"
    mesh_obj.parent_bone = bone_name
    # Keep current world transform after parenting
    mesh_obj.matrix_parent_inverse = (
        arm.matrix_world @ arm.pose.bones[bone_name].matrix
    ).inverted()


def add_face_meshes(arm, bone_map, head_name):
    """
    Separate face meshes parented to facial bones / head.
    Positions derived from Head world pose at rest.
    """
    head_w, _ = bone_world_head_tail(arm, head_name)
    if head_w is None:
        raise SystemExit("Cannot resolve Head world position")

    # Approximate face feature positions in WORLD space from inspect ratios
    # Head height ~0.66, eyes ~Y+0.38 from head bone, mouth ~Y+0.18
    eye_L_w = head_w + Vector((-0.055, 0.10, 0.09))
    eye_R_w = head_w + Vector((0.055, 0.10, 0.09))
    mouth_w = head_w + Vector((0.0, 0.02, 0.10))
    brow_L_w = head_w + Vector((-0.055, 0.14, 0.08))
    brow_R_w = head_w + Vector((0.055, 0.14, 0.08))

    mat_eye = mat_simple("FaceEye", (0.95, 0.95, 0.98))
    mat_pupil = mat_simple("FacePupil", (0.05, 0.05, 0.08))
    mat_lid = mat_simple("FaceLid", (0.55, 0.40, 0.32))
    mat_brow = mat_simple("FaceBrow", (0.15, 0.10, 0.08))
    mat_lip = mat_simple("FaceLip", (0.65, 0.25, 0.28))
    mat_teeth = mat_simple("FaceTeeth", (0.92, 0.90, 0.85))

    meshes = {}

    # Eyes (spheres) -> eye bones
    for side, pos, bkey in (("L", eye_L_w, "face_eye_L"), ("R", eye_R_w, "face_eye_R")):
        eye = make_sphere(f"FaceEye_{side}", 0.022, pos, mat_eye)
        pupil = make_sphere(f"FacePupil_{side}", 0.009, pos + Vector((0, 0, 0.018)), mat_pupil)
        parent_mesh_to_bone(eye, arm, bone_map[bkey])
        parent_mesh_to_bone(pupil, arm, bone_map[bkey])
        meshes[f"eye_{side}"] = eye
        meshes[f"pupil_{side}"] = pupil

    # Eyelids (flat cubes) -> eyelid bones — blink rotates these ONLY
    for side, pos, bkey in (("L", eye_L_w + Vector((0, 0.012, 0.005)), "face_eyelid_L"),
                            ("R", eye_R_w + Vector((0, 0.012, 0.005)), "face_eyelid_R")):
        lid = make_cube(f"FaceEyelid_{side}", Vector((0.028, 0.006, 0.018)), pos, mat_lid)
        parent_mesh_to_bone(lid, arm, bone_map[bkey])
        meshes[f"eyelid_{side}"] = lid

    # Brows
    for side, pos, bkey in (("L", brow_L_w, "face_brow_L"), ("R", brow_R_w, "face_brow_R")):
        brow = make_cube(f"FaceBrow_{side}", Vector((0.030, 0.005, 0.010)), pos, mat_brow)
        parent_mesh_to_bone(brow, arm, bone_map[bkey])
        meshes[f"brow_{side}"] = brow

    # Mouth / lips / teeth parented to jaw
    jaw_bone = bone_map["face_jaw"]
    upper_lip = make_cube("FaceUpperLip", Vector((0.040, 0.006, 0.012)), mouth_w + Vector((0, 0.012, 0)), mat_lip)
    lower_lip = make_cube("FaceLowerLip", Vector((0.038, 0.007, 0.012)), mouth_w + Vector((0, -0.008, 0.005)), mat_lip)
    teeth = make_cube("FaceTeeth", Vector((0.032, 0.010, 0.008)), mouth_w + Vector((0, 0.002, -0.005)), mat_teeth)
    # Upper lip stays on head; lower lip + teeth follow jaw
    parent_mesh_to_bone(upper_lip, arm, head_name)
    parent_mesh_to_bone(lower_lip, arm, jaw_bone)
    parent_mesh_to_bone(teeth, arm, jaw_bone)
    meshes["upper_lip"] = upper_lip
    meshes["lower_lip"] = lower_lip
    meshes["teeth"] = teeth

    print("FACE_MESHES", list(meshes.keys()))
    return meshes


def animate_face_only(arm, bone_map, fps=24):
    """
    Two clips:
      FaceBlink  — ONLY eyelid bones rotate on X (0 -> -20 deg)
      FaceJaw    — ONLY jaw bone rotates on X
    Never keyframes root / hips / body.
    """
    if not arm.animation_data:
        arm.animation_data_create()

    def clear_action(name):
        act = bpy.data.actions.get(name)
        if act:
            bpy.data.actions.remove(act)
        act = bpy.data.actions.new(name)
        return act

    # --- Blink ---
    act_blink = clear_action("FaceBlink")
    arm.animation_data.action = act_blink
    for side in ("L", "R"):
        bname = bone_map[f"face_eyelid_{side}"]
        pb = arm.pose.bones[bname]
        pb.rotation_mode = "XYZ"
        for f, angle in ((1, 0.0), (6, -20.0), (12, 0.0)):
            pb.rotation_euler = (math.radians(angle), 0.0, 0.0)
            pb.keyframe_insert(data_path="rotation_euler", frame=f)
    print("ACTION FaceBlink frames 1-12 eyelid X only")

    # --- Jaw ---
    act_jaw = clear_action("FaceJaw")
    arm.animation_data.action = act_jaw
    pb = arm.pose.bones[bone_map["face_jaw"]]
    pb.rotation_mode = "XYZ"
    for f, angle in ((1, 0.0), (10, 25.0), (20, 0.0)):
        pb.rotation_euler = (math.radians(angle), 0.0, 0.0)
        pb.keyframe_insert(data_path="rotation_euler", frame=f)
    print("ACTION FaceJaw frames 1-20 jaw X only")

    # Push both to NLA so they export
    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None

    tr = arm.animation_data.nla_tracks.new()
    tr.name = "Face"
    s1 = tr.strips.new("FaceBlink", 1, act_blink)
    s1.frame_end = 12
    s2 = tr.strips.new("FaceJaw", 15, act_jaw)
    s2.frame_end = 35

    return act_blink, act_jaw


def setup_proof_camera(arm, head_name):
    head_w, _ = bone_world_head_tail(arm, head_name)
    if head_w is None:
        head_w = Vector((0, 1.1, 0))
    # Front face camera
    cam_loc = head_w + Vector((0.0, -0.55, 0.05))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    direction = head_w - cam_loc
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=head_w + Vector((1, -2, 3)))
    sun = bpy.context.active_object
    sun.data.energy = 5.0

    bpy.ops.object.light_add(type="AREA", location=head_w + Vector((0, -1.2, 0.8)))
    fill = bpy.context.active_object
    fill.data.energy = 200
    fill.data.size = 2.0

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.25, 0.25, 0.28)
    return cam


def render_proof(out_mp4: Path, fps: int, width: int, height: int, arm, bone_map):
    """Render blink then jaw; only face bones animated."""
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

    # Drive pose from actions manually for proof (don't touch root)
    act_blink = bpy.data.actions.get("FaceBlink")
    act_jaw = bpy.data.actions.get("FaceJaw")

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        frames_written = []
        frame_idx = 1

        def render_action(action, nframes, label):
            nonlocal frame_idx
            if action is None:
                return
            arm.animation_data.action = action
            for f in range(1, nframes + 1):
                scene.frame_set(f)
                # Safety: zero any accidental root motion
                for root_name in ("mixamorig:Hips", "root", "Root", "SmartRigArmature"):
                    pb = arm.pose.bones.get(root_name)
                    if pb is not None:
                        # do not clear hips location from body clips — we only set face action
                        pass
                path = frame_dir / f"frame_{frame_idx:04d}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                frames_written.append(path)
                frame_idx += 1
            print(f"PROOF_FRAMES {label} {nframes}")

        render_action(act_blink, 12, "blink")
        render_action(act_jaw, 20, "jaw")

        if not frames_written:
            raise SystemExit("No proof frames")

        list_file = frame_dir / "list.txt"
        list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in frames_written))
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-r", str(fps),
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart",
            str(out_mp4),
        ])
        print("PROOF_MP4", out_mp4, out_mp4.stat().st_size)


def export_glb(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Select armature + all face meshes + body
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
    # Bound box world
    corners = [body.matrix_world @ Vector(c) for c in body.bound_box]
    zs = [c.z for c in corners]
    ys = [c.y for c in corners]
    # After glTF import Blender is Z-up; height is max axis span
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

    # Record root/hips rest so we can assert unchanged
    hips = arm.pose.bones.get("mixamorig:Hips")
    hips_rest_loc = hips.location.copy() if hips else None

    bone_map, head_name = ensure_facial_bones(arm)
    print("FACIAL_BONES", bone_map)
    print("HEAD_PARENT", head_name)

    meshes = add_face_meshes(arm, bone_map, head_name)
    animate_face_only(arm, bone_map, fps=fps)

    h_after = verify_height(body, "AFTER")
    if h_before and h_after and abs(h_before - h_after) > 0.05:
        raise SystemExit(f"Height changed {h_before} -> {h_after}")

    if hips and hips_rest_loc is not None:
        if (hips.location - hips_rest_loc).length > 1e-5:
            print("WARN hips location drifted — resetting")
            hips.location = hips_rest_loc

    setup_proof_camera(arm, head_name)
    render_proof(out_mp4, fps, width, height, arm, bone_map)

    # Reset to rest before export
    for pb in arm.pose.bones:
        if pb.name.startswith("face_"):
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
    export_glb(out_glb)

    # Final bone list proof
    print("BONE_LIST_FINAL")
    for b in arm.data.bones:
        par = b.parent.name if b.parent else "None"
        if b.name.startswith("face_") or "Head" in b.name or "head" in b.name:
            print(f"  {b.name} parent={par} deform={b.use_deform}")

    print("DONE face rig OK")


if __name__ == "__main__":
    main()
