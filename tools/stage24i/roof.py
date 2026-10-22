"""Stage 24-I roof role: the decay-vulnerable roof cells that are the only barrier between a usable enclosed room and
the open space above it.

A stored cell is a protected roof cell when all of these hold:
  * its block is in #minecraft:ancient_city_replaceable (block_rot can drop it) and it is not already protected by
    the Stage 24-G roles,
  * the cell directly below is a Stage 24-H `room_interior` mask cell (an enclosed, roofed, usable room),
  * the cell directly above is open: outside the template, or a Stage 24-H `exterior` / `decorative_void` cell.
A roof that is two blocks thick, a roof of non-rottable blocks (tile stairs, polished deepslate) and open courtyards
get nothing. Walls are never included: the owner authorised roof cells only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.roles import Template  # noqa: E402
from tools.stage24h.mask import build_mask  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"


def roof_cells(t: Template, mask: dict, protected: set):
    out = []
    for p, st in sorted(t.state.items()):
        if P.name(st) not in P.ANCIENT_CITY_REPLACEABLE or p in protected:
            continue
        below = (p[0], p[1] - 1, p[2])
        above = (p[0], p[1] + 1, p[2])
        if mask.get(below) != "room_interior":
            continue
        if t.inside(above) and mask.get(above) not in ("exterior", "decorative_void"):
            continue
        out.append(p)
    return out


def build():
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    res = {}
    for m in MODULES:
        t = Template(D24F / m / "restored.nbt")
        mask = build_mask(t)
        prot = {tuple(e["pos"]) for e in inv[m]["protected"]}
        cells = roof_cells(t, mask, prot)
        rottable = [p for p, s in t.state.items() if P.name(s) in P.ANCIENT_CITY_REPLACEABLE]
        prot_rot = [p for p in rottable if p in prot]
        res[m] = {"roof_cells": [{"pos": list(p), "state": t.at(p)} for p in cells],
                  "rottable_cells": len(rottable), "stage24g_protected_rottable": len(prot_rot),
                  "decay_eligible_before": len(rottable) - len(prot_rot),
                  "decay_eligible_after": len(rottable) - len(prot_rot) - len(cells),
                  "decay_eligible_share_after": round((len(rottable) - len(prot_rot) - len(cells)) / len(rottable), 4) if rottable else None}
    return res


if __name__ == "__main__":
    r = build()
    for m, v in r.items():
        print(m, len(v["roof_cells"]), {k: v[k] for k in ("rottable_cells", "decay_eligible_before", "decay_eligible_after", "decay_eligible_share_after")})
