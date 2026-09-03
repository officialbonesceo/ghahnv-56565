# Talking Clip Factory

## Can we “add the .blend”?

**Yes, as a pipeline — with limits.**

- I **cannot** invent a Mixamo-quality human from concept art inside git as pure magic.
- I **can** (and did) add:
  1. `assets/build_cyber_host.py` — builds a real **`cyber_host.blend`** (character + simple room)
  2. CI **caches** that `.blend` so later runs open the file like a normal studio asset
  3. `scripts/director_render.py` — plays **actions** + **Rhubarb** mouth on that file

### Actions input (workflow)

`talk,idle,nod,gesture,walk`

- **talk** — Rhubarb lips
- **nod** — head nod
- **gesture** — arm lift
- **walk** — stylized sway (not a real walk cycle)
- **idle** — breathe

### Upgrade path to “real” acting

Put your own rigged file at `assets/character.blend` (Mixamo etc.), then point the workflow at it. Same director pattern: actions + lips + room.

### Verify

Actions → **Render talking clip** → set actions e.g. `talk,nod,gesture` → download `output.mp4`.
