"""Fail when a live Stage 24-I placement broke an invariant or lost a roof cell.

Every i24 placement must show no violation and every roof cell present; all four rotations of every module must be
seen. h24 control placements are reported (roof cells missing there is the unprotected baseline) but never fail."""
from __future__ import annotations

import json
import sys
from collections import defaultdict

rep = json.loads(open(sys.argv[1]).read())
bad, rots, ctl = [], defaultdict(set), []
for p in rep["placements"]:
    if p["kind"] != "i24":
        ctl.append((p["module"], p["rotation"], p["roof"]["counts"]))
        continue
    rots[p["module"]].add(p["rotation"])
    v = p["analysis"]["violations"]
    if v or p["roof"]["counts"].get("MISSING"):
        bad.append((p["module"], p["rotation"], sorted({x["type"] for x in v}), p["roof"]["counts"]))
for m, r in sorted(rots.items()):
    print(m, "rotations", sorted(r))
print("h24 controls", ctl)
need = int(sys.argv[2]) if len(sys.argv) > 2 else 4
short = [m for m, r in rots.items() if len(r) < need]
print("placements", len(rep["placements"]), "failures", bad, "rotations short", short)
sys.exit(1 if bad or not rots or short else 0)
