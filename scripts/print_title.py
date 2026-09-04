#!/usr/bin/env python3
import json
from pathlib import Path
p = Path("script_job.json")
if p.exists():
    print(json.loads(p.read_text()).get("title") or "Mezi")
else:
    print("Mezi")
