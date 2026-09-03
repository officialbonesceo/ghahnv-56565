"""
Run inside Blender:
  blender -b -P assets/build_cyber_host.py -- --out assets/cyber_host.blend

Creates a savable .blend: stylized cyber host + simple room set.
Still procedural (no Mixamo mesh), but persisted as a real .blend asset.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy


def parse_out(argv):
    out = "assets/cyber_host.blend"
    if "--" in argv:
        a = argv[argv.index("--") + 1 :]
        for i, v in enumerate(a):
            if v == "--out" and i + 1 < len(a):
                out = a[i + 1]
    return Path(out)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = False
    m.diffuse_color = (*color, 1.0)
    return m


def build_room():
    # Floor
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    bpy.context.active_object.name = "Floor"
    bpy.context.active_object.data.materials.append(mat("Floor", (0.12, 0.13, 0.16)))
    # Back wall
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 3.5, 2.5))
    w = bpy.context.active_object
    w.name = "BackWall"
    w.rotation_euler = (math.radians(90), 0, 0)
    w.data.materials.append(mat("Wall", (0.08, 0.1, 0.18)))
    # Side accent panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.5, 2.8, 1.5))
    p = bpy.context.active_object
    p.scale = (0.08, 1.2, 1.4)
    p.data.materials.append(mat("Panel", (0.1, 0.55, 0.85)))
    # Ceiling strip light
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.0, 3.6))
    c = bpy.context.active_object
    c.scale = (2.0, 0.15, 0.05)
    c.data.materials.append(mat("CeilLight", (0.6, 0.85, 1.0)))


def build_host():
    # Torso
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
    torso = bpy.context.active_object
    torso.name = "Torso"
    torso.scale = (0.7, 0.4, 0.75)
    torso.data.materials.append(mat("Jacket", (0.06, 0.08, 0.12)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.35, 1.35))
    strip = bpy.context.active_object
    strip.name = "CyanCollar"
    strip.scale = (0.55, 0.06, 0.05)
    strip.data.materials.append(mat("Cyan", (0.15, 0.8, 1.0)))

    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(0, 0, 1.95))
    head = bpy.context.active_object
    head.name = "Head"
    head.scale = (0.95, 1.0, 1.05)
    head.data.materials.append(mat("Skin", (0.55, 0.58, 0.64)))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.48, location=(0, 0.05, 2.05))
    hair = bpy.context.active_object
    hair.name = "Hair"
    hair.scale = (0.95, 1.0, 0.65)
    hair.data.materials.append(mat("Hair", (0.1, 0.12, 0.16)))

    for x in (-0.15, 0.15):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(x, -0.4, 2.0))
        bpy.context.active_object.data.materials.append(mat("Eye", (0.2, 0.9, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.42, 1.75))
    mouth = bpy.context.active_object
    mouth.name = "Mouth"
    mouth.scale = (0.35, 0.08, 0.04)
    mouth.data.materials.append(mat("Mouth", (0.4, 0.15, 0.2)))

    # Headset
    bpy.ops.mesh.primitive_torus_add(major_radius=0.48, minor_radius=0.035, location=(0, 0, 1.98))
    band = bpy.context.active_object
    band.name = "Headset"
    band.rotation_euler = (math.radians(90), 0, 0)
    band.data.materials.append(mat("Band", (0.1, 0.1, 0.14)))

    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.4, location=(-0.3, -0.3, 1.85))
    boom = bpy.context.active_object
    boom.name = "Boom"
    boom.rotation_euler = (math.radians(65), 0, math.radians(15))
    boom.data.materials.append(mat("Boom", (0.2, 0.75, 0.95)))

    # Simple "arm" markers for gesture (not a full rig)
    for x, name in ((-0.55, "ArmL"), (0.55, "ArmR")):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0.05, 1.0))
        arm = bpy.context.active_object
        arm.name = name
        arm.scale = (0.12, 0.12, 0.45)
        arm.data.materials.append(mat("Sleeve", (0.07, 0.09, 0.13)))


def setup_camera_lights():
    bpy.ops.object.light_add(type="AREA", location=(1.5, -2.0, 3.0))
    bpy.context.active_object.data.energy = 50
    bpy.ops.object.light_add(type="SUN", location=(-2, -3, 5))
    bpy.context.active_object.data.energy = 2.0

    bpy.ops.object.camera_add(location=(0, -3.2, 1.8))
    cam = bpy.context.active_object
    cam.name = "RenderCam"
    cam.rotation_euler = (math.radians(88), 0, 0)
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = False
    world.color = (0.03, 0.04, 0.07)


def main():
    out = parse_out(sys.argv)
    out.parent.mkdir(parents=True, exist_ok=True)
    reset()
    build_room()
    build_host()
    setup_camera_lights()
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print("Wrote", out.resolve())


if __name__ == "__main__":
    main()
