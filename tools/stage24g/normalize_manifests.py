"""Re-derive the template field of list-element pieces with the current rule of tools/stage24c/worldgen.piece_record
(only lists whose extra elements are our overlays are unwrapped; vanilla camps keep ""). Used once for the first
Stage 24-G sweep (camps were unwrapped) and once for the Stage 24-H sweep (3-element lists were not unwrapped).
Positions, rotations and boxes are untouched."""
import json
import sys
from pathlib import Path

from tools.stage24c.worldgen import OVERLAY_PREFIX

variant = sys.argv[2] if len(sys.argv) > 2 else "g24"
for f in sorted(Path(sys.argv[1]).glob(f"manifest-*-{variant}.json")):
    m = json.loads(f.read_text())
    n = 0
    for c in m.get("cities", []):
        for p in c["pieces"]:
            subs = p.get("list_elements")
            if not subs:
                continue
            ours = len(subs) >= 2 and all(x.startswith(OVERLAY_PREFIX) for x in subs[1:])
            want = subs[0] if ours else ""
            if p["template"] != want:
                p["template"] = want
                n += 1
    f.write_text(json.dumps(m, indent=1))
    print(f.name, "list pieces re-derived", n)
