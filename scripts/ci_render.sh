#!/usr/bin/env bash
set -euo pipefail
TEXT=$(cat script.txt)
BG=studio
if [ -f bg.txt ]; then
  BG=$(cat bg.txt)
fi
TITLE=Mezi
if [ -f script_job.json ]; then
  TITLE=$(python scripts/print_title.py)
fi
if [ -f mouth.json ]; then
  python scripts/render_mezi.py \
    --audio speech.mp3 \
    --text "${TEXT}" \
    --title "${TITLE}" \
    --bg "${BG}" \
    --out output.mp4 \
    --actions "${ACTIONS}" \
    --cues mouth.json
else
  python scripts/render_mezi.py \
    --audio speech.mp3 \
    --text "${TEXT}" \
    --title "${TITLE}" \
    --bg "${BG}" \
    --out output.mp4 \
    --actions "${ACTIONS}"
fi
ls -lh output.mp4
