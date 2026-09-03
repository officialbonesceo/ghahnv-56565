# Talking Clip Factory

**Feasible, easy-to-verify** GitHub Actions pipeline:

**Text → Edge TTS (speech) → ffmpeg video → downloadable MP4**

No GPU, no Blender install on free runners (those are slow/fragile there). This path is designed so you can **confirm it works** in a few minutes.

## How to run (verify)

1. Open: https://github.com/officialbonesceo/talking-clip-factory/actions
2. Select workflow **Render talking clip**
3. Click **Run workflow**
4. Optional: change the script text
5. Wait ~1–3 minutes
6. Open the finished run → **Artifacts** → download `talking-clip`
7. Play `output.mp4`

If the artifact appears and the video has voice + on-screen text, it works.

## What it uses (all maintained / active)

| Tool | Role |
|------|------|
| [edge-tts](https://github.com/rany2/edge-tts) | Free neural TTS (Microsoft Edge voices) |
| **ffmpeg** | Builds a simple captioned video + muxes audio |
| **GitHub Actions** | Orchestration + artifact upload |

No abandoned projects. No celebrity deepfakes — generic narrator voice only.

## Local test (optional)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/render_clip.py --text "Hello from Talking Clip Factory." --out output.mp4
```

Needs `ffmpeg` on your PATH.

## Later upgrades (optional)

- Headless **Blender** on a self-hosted / GPU runner
- **Rhubarb** lip-sync
- Small local LLM for script expansion (heavy on free Actions — keep off the default path)

## License

Your project — use as you like.
