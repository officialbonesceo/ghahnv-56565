# Talking Clip Factory — MEZI 2D

**MEZI-style cartoon explorer** (yellow hoodie), not Blender geometry.

```
text → Edge TTS → Rhubarb mouths → MEZI 2D frames → mp4
```

## Actions

| Action | What you see |
|--------|----------------|
| `talk` | Idle bob + lip sync |
| `walk` | Side-to-side walk cycle + lips |
| `point` | Points while talking |
| `laugh` | Laugh expression + open mouth |

## Verify

1. Actions → **Render talking clip** → Run workflow  
2. Pick action (try `talk` or `point`)  
3. Download **talking-clip** → `output.mp4`  

Expect cartoon MEZI in a simple room, mouth moving with speech — closer to the MEZI sheet than the old cyber sphere.

## Honest note

This is a **procedural 2D puppet** inspired by MEZI (Pillow-drawn), not the full polished character-sheet illustration. It is the feasible automated path on free GitHub Actions. Upgrading to the exact sheet art means dropping real PNG layers into `assets/` later.
