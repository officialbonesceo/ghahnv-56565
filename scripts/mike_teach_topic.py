#!/usr/bin/env python3
"""Mike teach: Tripo light, multi-cam, lip-sync from TTS WAV, audio muxed into MP4."""
from __future__ import annotations
import math, struct, subprocess, sys, tempfile, wave
from pathlib import Path
import bpy
from mathutils import Vector

TOPIC_TITLE = "What is Coding?"
TOPIC_LINE = "Step-by-step instructions for computers."

def parse_args(argv):
    args = {"glb": "assets/mike/Mikeanim.glb", "out": "assets/blender/mike_teach_topic.mp4",
            "voice": "assets/blender/mike_voice.wav", "fps": 24, "seconds": 15,
            "width": 720, "height": 1280, "topic": TOPIC_TITLE, "line": TOPIC_LINE}
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            key = argv[i][2:].replace("-", "_")
            val = argv[i + 1]
            args[key] = int(val) if key in ("fps", "width", "height", "seconds") else val
            i += 2
        else:
            i += 1
    return args

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                 bpy.data.armatures, bpy.data.actions, bpy.data.images):
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
    m.diffuse_color = (*color, 1.0)
    return m

def find_arm_body():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arm = next((a for a in arms if any("Head" in b.name for b in a.data.bones)), arms[0] if arms else None)
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
            min_c = Vector(tuple(min(min_c[i], w[i]) for i in range(3)))
            max_c = Vector(tuple(max(max_c[i], w[i]) for i in range(3)))
    height = max(0.01, max_c.z - min_c.z)
    scale = 1.70 / height
    if arm and arm.parent is None:
        arm.parent = root
    for o in list(bpy.data.objects):
        if o.type in ("MESH", "ARMATURE") and o.parent is None and o != root:
            o.parent = root
    root.scale = (scale, scale, scale)
    root.location = (0.0, 0.80, -min_c.z * scale)
    bpy.context.view_layer.update()
    print("PLACE", round(height, 3), round(scale, 3))
    return root

def ensure_textures_visible(body):
    if not body:
        return
    for slot in body.material_slots:
        mat = slot.material
        if not mat:
            continue
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    print("TEX", node.image.name)

def ensure_mouth_shape_key(body):
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
    kb = body.shape_key_add(name="mouth_open", from_mix=False)
    moved = 0
    for i, v in enumerate(me.vertices):
        if not (mouth_z0 <= v.co.z <= mouth_z1):
            continue
        dx = abs(v.co.x - cx)
        if dx > mouth_x_half:
            continue
        if (v.co.y - mn.y) / max(1e-6, size.y) > 0.50:
            continue
        tz = (v.co.z - mouth_z0) / max(1e-6, mouth_z1 - mouth_z0)
        w = max(0.0, 1.0 - dx / mouth_x_half) ** 0.65
        if tz < 0.48:
            lip_w = max(0.0, min(1.0, w * (1.0 - abs(tz - 0.25) * 1.2)))
            if lip_w < 0.08:
                continue
            kb.data[i].co.z -= lower_down * lip_w * (1.15 - tz)
            kb.data[i].co.y -= fwd * lip_w
            moved += 1
        else:
            lip_w = w * max(0.0, 1.0 - abs(tz - 0.55) * 3.0)
            if lip_w < 0.12:
                continue
            kb.data[i].co.z += upper_up * lip_w
            moved += 1
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
            else:
                kb.data[i].co.z += upper_up * w
            moved += 1
    print("SHAPEKEY_MOUTH_MOVED", moved)
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
    walk = by_name.get("Casual_Walk") or by_name.get("Walking")
    explain = by_name.get("Agree_Gesture") or by_name.get("Alert")
    for a in bpy.data.actions:
        if a.name.startswith("_") and explain is None:
            explain = a
    while arm.animation_data.nla_tracks:
        arm.animation_data.nla_tracks.remove(arm.animation_data.nla_tracks[0])
    arm.animation_data.action = None
    track = arm.animation_data.nla_tracks.new()
    track.name = "BodyTeach"
    walk_end = int(fps * 4)
    def add_strip(action, start, end, name):
        if action is None:
            return
        try:
            strip = track.strips.new(name[:40], int(start), action)
        except TypeError:
            strip = track.strips.new(int(start), action)
        strip.action = action
        strip.frame_start = start
        strip.frame_end = end
        try:
            strip.extrapolation = "HOLD"
        except Exception:
            pass
        print("BODY", name, start, end)
    add_strip(walk or explain, 1, walk_end, "walk")
    add_strip(explain or walk, walk_end + 1, total, "explain")

def wav_rms_envelope(path, fps, total_frames):
    env = [0.0] * (total_frames + 1)
    try:
        with wave.open(str(path), "rb") as w:
            nch, sw, rate, nframes = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(nframes)
    except Exception as e:
        print("WAV_READ_FAIL", e)
        return env
    if sw == 2:
        samples = list(struct.unpack("<" + "h" * (len(raw) // 2), raw))
    elif sw == 1:
        samples = [b - 128 for b in raw]
    else:
        return env
    if nch > 1:
        samples = samples[0::nch]
    spf = max(1, int(rate / fps))
    peak = 1.0
    rms_list = []
    for f in range(1, total_frames + 1):
        chunk = samples[(f - 1) * spf : f * spf]
        if not chunk:
            rms_list.append(0.0)
            continue
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        rms_list.append(rms)
        if rms > peak:
            peak = rms
    for f, rms in enumerate(rms_list, start=1):
        v = rms / peak if peak > 1e-6 else 0.0
        if v < 0.08:
            v = 0.0
        else:
            v = min(1.0, (v - 0.08) / 0.75) ** 0.7
        env[f] = v
    print("LIPSYNC", total_frames)
    return env

def animate_mouth_from_audio(kb, fps, total, voice_path):
    if voice_path and voice_path.exists():
        env = wav_rms_envelope(voice_path, fps, total)
        for f in range(1, total + 1):
            kb.value = env[f]
            kb.keyframe_insert(data_path="value", frame=f)
        print("MOUTH from audio")
        return
    cycle = max(5, int(fps * 0.28))
    for f in range(1, total + 1):
        t = f / float(fps)
        val = abs(math.sin(((f - 1) % cycle) / float(cycle) * math.pi)) ** 0.85 if t >= 4.0 else 0.02
        kb.value = val
        kb.keyframe_insert(data_path="value", frame=f)

def bone_world(arm, name):
    if not arm:
        return None
    pb = arm.pose.bones.get(name)
    return ((arm.matrix_world @ pb.matrix) @ Vector((0, 0, 0))) if pb else None

def tripo_studio():
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 4.0, 1.5))
    bpy.context.active_object.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.active_object.data.materials.append(mat_simple("Back", (0.16, 0.16, 0.17)))
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 1.0, 0))
    bpy.context.active_object.data.materials.append(mat_simple("Floor", (0.12, 0.12, 0.13)))

def setup_tripo_lights():
    for loc, e, sz in [((2.2, -2.6, 3.2), 360, 4.5), ((-2.2, -2.0, 2.5), 200, 4.0), ((0, 0.3, 4.2), 140, 5.5)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        bpy.context.active_object.data.energy = e
        bpy.context.active_object.data.size = sz
    bpy.ops.object.light_add(type="SUN", location=(1.5, -3, 5))
    bpy.context.active_object.data.energy = 2.0
    bpy.context.active_object.rotation_euler = (math.radians(48), math.radians(10), 0)
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = False
    except Exception:
        pass
    world.color = (0.11, 0.11, 0.12)

def animate_camera(arm, body, fps, total):
    # Blender 5 safe: no Action.fcurves
    bpy.context.view_layer.update()
    head = bone_world(arm, "mixamorig:Head") or bone_world(arm, "Head") or Vector((0, 0.8, 1.45))
    hips = bone_world(arm, "mixamorig:Hips") or Vector((0, 0.8, 0.75))
    mid = Vector((0.0, hips.y, (head.z + hips.z) * 0.5))
    bpy.ops.object.camera_add(location=(0, -5.5, mid.z + 0.2))
    cam = bpy.context.active_object
    cam.data.lens = 40
    bpy.context.scene.camera = cam
    shots = [
        (1, Vector((0.2, -5.8, mid.z + 0.25)), mid, 38),
        (int(fps * 3.5), Vector((0.1, -4.0, mid.z + 0.15)), mid, 40),
        (int(fps * 5.5), Vector((0.0, -2.9, mid.z + 0.05)), mid, 42),
        (int(fps * 8.0), Vector((2.3, -2.3, mid.z + 0.1)), mid, 45),
        (int(fps * 11.0), Vector((0.12, -1.30, head.z)), head, 50),
        (int(fps * 13.5), Vector((-0.25, -2.5, mid.z + 0.15)), mid + Vector((0, 0, 0.05)), 40),
        (total, Vector((0.0, -2.8, mid.z + 0.1)), mid, 42),
    ]
    for f, loc, aim, lens in shots:
        cam.location = loc
        cam.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)
        try:
            cam.data.keyframe_insert(data_path="lens", frame=f)
        except Exception:
            pass
    print("CAMERA multi-shot ok")
    return cam

def setup_workbench(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    try:
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_shadows = False
    except Exception:
        try:
            scene.display.shading.color_type = "MATERIAL"
        except Exception:
            pass

def render_frames(frame_dir, fps, width, height, total):
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
    scene.frame_start = 1
    scene.frame_end = total
    for f in range(1, total + 1):
        scene.frame_set(f)
        path = frame_dir / f"frame_{f:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if f % 24 == 0:
            print(f"RENDER {f}/{total}")

def mux_video(frame_dir, out, fps, topic, line, voice):
    frames = sorted(frame_dir.glob("frame_*.png"))
    if not frames:
        raise SystemExit("No frames")
    list_file = frame_dir / "list.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in frames))
    raw = frame_dir / "raw.mp4"
    subprocess.check_call([
        "ffmpeg", "-y", "-r", str(fps), "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(raw),
    ])
    def esc(s):
        return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "%%")
    vf = (
        f"drawtext=text='{esc(topic)}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=42:"
        f"box=1:boxcolor=black@0.40:boxborderw=10,"
        f"drawtext=text='{esc(line)}':fontcolor=white:fontsize=20:x=(w-text_w)/2:y=h-78:"
        f"box=1:boxcolor=black@0.35:boxborderw=8"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    if voice and voice.exists():
        try:
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(raw), "-i", str(voice), "-vf", vf,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                "-c:a", "aac", "-b:a", "160k", "-shortest",
                "-movflags", "+faststart", str(out),
            ])
        except subprocess.CalledProcessError:
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(raw), "-i", str(voice),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                "-c:a", "aac", "-b:a", "160k", "-shortest",
                "-movflags", "+faststart", str(out),
            ])
    else:
        try:
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(raw), "-vf", vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                "-movflags", "+faststart", str(out),
            ])
        except subprocess.CalledProcessError:
            subprocess.check_call(["cp", str(raw), str(out)])
    try:
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out),
        ], text=True).strip()
        print("AUDIO_STREAMS", probe or "NONE")
    except Exception as e:
        print("PROBE", e)
    print("OUT", out, out.stat().st_size)

def main():
    args = parse_args(sys.argv)
    glb = Path(args["glb"]).resolve()
    out = Path(args["out"]).resolve()
    voice = Path(args["voice"]).resolve()
    fps = int(args["fps"])
    seconds = int(args["seconds"])
    width = int(args["width"])
    height = int(args["height"])
    topic = args.get("topic") or TOPIC_TITLE
    line = args.get("line") or TOPIC_LINE
    total = fps * seconds
    if voice.exists():
        try:
            with wave.open(str(voice), "rb") as w:
                vdur = w.getnframes() / float(w.getframerate())
            total = max(total, int(math.ceil(vdur * fps)) + fps // 2)
            print("VOICE_DUR", round(vdur, 2), "frames", total)
        except Exception:
            pass
    if not glb.exists():
        alt = glb.parent / "Mike.glb"
        if alt.exists():
            glb = alt
        else:
            raise SystemExit(f"Missing {glb}")
    clear_scene()
    tripo_studio()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    print("IMPORTED", glb)
    arm, body, meshes = find_arm_body()
    if body is None:
        raise SystemExit("No body")
    place_character(arm, body, meshes)
    ensure_textures_visible(body)
    kb = ensure_mouth_shape_key(body)
    sequence_body(arm, fps, total)
    animate_mouth_from_audio(kb, fps, total, voice if voice.exists() else None)
    setup_tripo_lights()
    animate_camera(arm, body, fps, total)
    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp)
        render_frames(frame_dir, fps, width, height, total)
        mux_video(frame_dir, out, fps, topic, line, voice if voice.exists() else None)
    print("DONE with audio")

if __name__ == "__main__":
    main()
