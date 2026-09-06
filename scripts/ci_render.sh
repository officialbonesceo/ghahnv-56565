#!/usr/bin/env bash
set -euo pipefail
TEXT=$(cat script.txt)
BG=classroom
if [ -f bg.txt ]; then
  BG=$(cat bg.txt)
fi
TITLE=Mike
if [ -f script_job.json ]; then
  TITLE=$(python scripts/print_title.py 2>/dev/null || python -c "import json; print(json.load(open('script_job.json')).get('short_title') or 'Mike')")
fi
BG_IMG=
if [ -f bg_path.txt ]; then
  BG_IMG=$(cat bg_path.txt)
fi
# ACTIONS optional — render_mezi uses its own performance timeline
ACTIONS="${ACTIONS:-}"

if [ -f mouth.json ]; then
  python scripts/render_mezi.py \
    --audio speech.mp3 \
    --text "${TEXT}" \
    --title "${TITLE}" \
    --bg "${BG}" \
    --bg-image "${BG_IMG}" \
    --out output.mp4 \
    --actions "${ACTIONS}" \
    --cues mouth.json
else
  python scripts/render_mezi.py \
    --audio speech.mp3 \
    --text "${TEXT}" \
    --title "${TITLE}" \
    --bg "${BG}" \
    --bg-image "${BG_IMG}" \
    --out output.mp4 \
    --actions "${ACTIONS}"
fi
ls -lh output.mp4
