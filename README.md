# Talking Clip Factory

**Text → offline polish → Edge TTS → Blender 3D (optional) → MP4**

No HuggingFace token. No large model download.

## What actually worked vs failed last run

| Step | Status |
|------|--------|
| Script expand (TinyLlama) | Worked (HF warning only) |
| Edge TTS + ffmpeg | **Worked** (`output_ffmpeg.mp4`) |
| Blender | **Failed** — missing `libEGL.so.1` on runner |

This update fixes Blender (`libegl1` + `xvfb` + Workbench engine) and replaces TinyLlama with an **offline** expander so nothing needs an HF token.

## Run / verify

1. [Actions](https://github.com/officialbonesceo/talking-clip-factory/actions)
2. **Render talking clip** → **Run workflow**
3. Download artifact **talking-clip**
4. Play `output.mp4` (and check `speech.mp3` / `script.txt`)

## Stack

- **Expand:** pure Python (no AI download)
- **TTS:** edge-tts
- **3D:** Blender 4.2 Workbench via `xvfb-run`
- **Fallback:** ffmpeg always builds a clip
