#!/usr/bin/env python3
"""Patch scripts/mike_teach_topic.py for Blender 5 (no Action.fcurves)."""
from pathlib import Path
p = Path("scripts/mike_teach_topic.py")
t = p.read_text()
if "PLACEHOLDER" in t or len(t) < 100:
    raise SystemExit("teach script is broken/placeholder — need full restore")
# Remove Blender 4-only fcurves smooth block
old = '''    # Smooth interpolation
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
'''
if old in t:
    t = t.replace(old, "    # (Blender 5: skip Action.fcurves smoothing)\n")
    p.write_text(t)
    print("PATCHED fcurves")
else:
    print("no fcurves block or already patched")
print("script size", p.stat().st_size)
