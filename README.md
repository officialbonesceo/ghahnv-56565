# Talking Clip Factory

**prompt → TinyLlama (optional) → Edge TTS → Blender 3D (optional) → MP4**

If Blender fails, ffmpeg fallback still produces a clip.

## Verify

1. [Actions](https://github.com/officialbonesceo/talking-clip-factory/actions)
2. **Render talking clip** → **Run workflow**
3. Toggle **use_llm** / **use_blender**
4. Download artifact **talking-clip** → play `output.mp4`

First run downloads Blender + TinyLlama (cached after that).

## Stack

| Step | Tool |
|------|------|
| LLM | TinyLlama 1.1B Chat Q4 (llama-cpp-python) |
| TTS | edge-tts |
| 3D | Blender 4.2 headless |
| Fallback | ffmpeg |

Keep scripts short on free CPU runners.
