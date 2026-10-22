"""Fail when a live buried placement of a Stage 24-H entry broke an invariant.

Deepslate-filled placements must show no violation at all (every mask cell air, every stored block as the processor
model predicts, every other cell untouched). Lava-filled placements must be clean right after placement; after the
fluid ticks only MASK_FLUID_RETURNED is accepted (lava re-entering through decay holes — the documented late-fluid
mechanism), never excavation outside the mask or lost architecture."""
from __future__ import annotations

import json
import sys
from collections import defaultdict

rep = json.loads(open(sys.argv[1]).read())
bad, rots = [], defaultdict(set)
for p in rep["placements"]:
    v = p["analysis"]["violations"]
    if v:
        bad.append((p["module"], p["kind"], p["fill"], p["rotation"], sorted({x["type"] for x in v})))
    if p["kind"] == "h24" and p["fill"] == "deepslate":
        rots[p["module"]].add(p["rotation"])
    after = p.get("analysis_after_1200_ticks")
    if after:
        other = {x["type"] for x in after["violations"]} - {"MASK_FLUID_RETURNED"}
        if other:
            bad.append((p["module"], p["kind"], "after-ticks", p["rotation"], sorted(other)))
for m, r in sorted(rots.items()):
    print(m, "rotations", sorted(r))
print("placements", len(rep["placements"]), "failures", bad)
sys.exit(1 if bad or not rots else 0)
