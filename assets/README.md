# Assets

Blender cannot use concept art alone. It needs **`.blend` files** (mesh, materials, optionally armature).

## What lives here

| Path | Role |
|------|------|
| `build_cyber_host.py` | Builds `cyber_host.blend` (character + simple room) inside Blender |
| `cyber_host.blend` | **Not stored in git** (binary + large). Created on CI and **cached** |
| Optional: your own `character.blend` | Drop a Mixamo / paid / custom rig here later and point the workflow at it |

## Actions the director understands

- `talk` — mouth driven by Rhubarb (+ slight head motion)
- `nod` — head nod
- `gesture` — arm-ish shoulder bob (stylized)
- `idle` — subtle breathe

True walk cycles need a **rigged** human (Mixamo etc.). This scaffold is the repo structure for that upgrade.
