# Talking Clip Factory — Profile 3 + Rhubarb

Pipeline:

**text → Edge TTS → Rhubarb lip cues → Blender cyber host → MP4**

## Lip sync: Rhubarb vs others

| Tool | Fit for this project |
|------|----------------------|
| **Rhubarb Lip Sync** | Best free offline CLI for CI. Audio → mouth shapes (A–H, X). Active project. |
| Papagayo | Older UI tool, weaker automation |
| Wav2Lip / SadTalker | Better realism, needs GPU + heavy models — not free Actions |
| Audio2Face | High quality, NVIDIA stack |
| Azure visemes | Needs paid cloud TTS API |

We use **Rhubarb** on purpose: no token, no GPU, works on GitHub runners.

## Character

Simplified **Profile 3** cyber host (head, jacket, cyan accents, headset). Not the full concept-art mesh — same vibe, CI-safe.

## Verify

1. Actions → **Render talking clip** → Run workflow  
2. Artifact includes `output.mp4`, `mouth.json`, `speech.mp3`  
3. Mouth should open/close with speech (Rhubarb cues)
