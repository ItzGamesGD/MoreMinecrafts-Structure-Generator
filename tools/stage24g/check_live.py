"""Fail when a live /place jigsaw placement of a Stage 24-G pool entry lost a protected cell or showed a block the
processor model does not explain."""
from __future__ import annotations

import json
import sys
from collections import defaultdict

rep = json.loads(open(sys.argv[1]).read())
bad, seen = [], defaultdict(set)
for p in rep["placements"]:
    a = p["analysis"]
    if p["kind"] == "g24":
        seen[p["module"]].add(p["rotation"])
        if a["protected_lost"] or a["unexplained_count"]:
            bad.append((p["module"], p["rotation"], len(a["protected_lost"]), a["unexplained_count"]))
for m, r in sorted(seen.items()):
    print(m, "rotations", sorted(r))
print("g24 placements", sum(1 for p in rep["placements"] if p["kind"] == "g24"), "failures", bad)
sys.exit(1 if bad or not seen else 0)
