# MEZI TikTok factory (GitHub Actions)

Fully automated short explainer pipeline:

```
Wikipedia (free, no seed)
  → Qwen2-0.5B GGUF script (or template fallback)
  → Edge TTS + Rhubarb
  → MEZI 2D vertical video + topic background + Ken Burns camera
  → artifact mp4
```

## Run

Actions → **Render talking clip** → Run workflow (no topic input needed).

Download artifact **mezi-tiktok**.

## Backgrounds

Auto from topic keywords: `space` · `ocean` · `money` · `tech` · `science` · `studio`

Slow zoom/pan applied every run.

## Notes

- Character is still a procedural puppet (not the full illustrated sheet).
- First run downloads ~300MB model (then cached).
- If LLM fails, template script from Wikipedia extract is used.
