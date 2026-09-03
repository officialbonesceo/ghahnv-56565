# Talking Clip Factory

**Text → offline polish → Edge TTS → ffmpeg video (+ optional Blender 3D)**

No HuggingFace token. No TinyLlama download on CI.

## What failed in the earlier run (and what did not)

| Step | Status |
|------|--------|
| TinyLlama | Worked but odd script + needs model download |
| Edge TTS + ffmpeg | **Succeeded** (`output_ffmpeg.mp4` ~67KB, audio ~26KB) |
| Blender | **Crashed**: missing `libEGL.so.1` on headless runner |

## Current design

1. **Script polish** — local Python only (no AI download, no token)
2. **Edge TTS** — neural voice → `speech.mp3`
3. **ffmpeg** — always builds `output_ffmpeg.mp4` (guaranteed artifact)
4. **Blender** — Workbench + `xvfb` + extra GL packages; silent MP4 then **ffmpeg muxes audio**

If Blender still fails, you still get the ffmpeg clip.

## Verify

1. [Actions](https://github.com/officialbonesceo/talking-clip-factory/actions)
2. **Render talking clip** → **Run workflow** (use latest `main`)
3. Download artifact **talking-clip**
4. Play `output.mp4` (and `output_ffmpeg.mp4` if you want the baseline)

First Blender run downloads ~300MB (then cached).
