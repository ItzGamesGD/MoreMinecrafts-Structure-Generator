"""One-off: the first Stage 24-G sweep recorded every list element by its first sub-template, which made vanilla's own
camp_1..3 list pieces read "camp_1" instead of "" (as in all earlier manifests). Re-derive the template field with the
corrected rule of tools/stage24c/worldgen.piece_record (only protection lists are unwrapped). Positions, rotations
and boxes are untouched."""
import json
import sys
from pathlib import Path

from tools.stage24c.worldgen import PROTECTION_PREFIX

for f in sorted(Path(sys.argv[1]).glob("manifest-*-g24.json")):
    m = json.loads(f.read_text())
    n = 0
    for c in m.get("cities", []):
        for p in c["pieces"]:
            subs = p.get("list_elements")
            if subs and not (len(subs) == 2 and subs[1].startswith(PROTECTION_PREFIX)) and p["template"]:
                p["template"] = ""
                n += 1
    f.write_text(json.dumps(m, indent=1))
    print(f.name, "camp list pieces reset", n)
