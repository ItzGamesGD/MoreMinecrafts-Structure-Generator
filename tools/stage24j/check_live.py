"""Fail when a live Stage 24-J placement differs from its template or a bot run on a candidate failed.

Every candidate and approved tower must be placed exactly in all four rotations (0 mismatching cells). When bot results
are present, every step on every OPTION must pass; failures on the approved towers are reported (the approved large
tower has no deck railing, so its deck-edge walks are expected to fail) but do not fail the check."""
from __future__ import annotations

import json
import sys
from collections import defaultdict

rep = json.loads(open(sys.argv[1]).read())
bad, rots, baseline = [], defaultdict(set), []
for p in rep["placements"]:
    key = (p["module"], p["variant"])
    rots[key].add(p["rotation"])
    if p["mismatches"]:
        bad.append((key, p["rotation"], "placement mismatches", p["mismatches"]))
    b = p.get("bot")
    if b and (b.get("error") or b.get("failed")):
        (baseline if p["variant"] == "current" else bad).append((key, p["rotation"], b.get("failed") or b.get("error")))
short = [k for k, r in rots.items() if len(r) < 4]
print("placements", len(rep["placements"]), "rotations short", short)
print("approved-tower bot failures (reported, not failing)", baseline)
print("failures", bad)
sys.exit(1 if bad or short or not rots else 0)
