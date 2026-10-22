"""Decay openings that remain after Stage 24-I: decay-eligible cells (rottable, not protected by 24-G or the 24-I roof)
that touch a usable interior cell (Stage 24-H mask), split by where they sit relative to it. These are the openings
the owner did not authorise closing (walls, floors, thick-roof layers) and which still decay as in vanilla."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.roles import Template  # noqa: E402
from tools.stage24h.mask import build_mask, CLEARED  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"


def main():
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    roofs = json.loads((D24I / "roof/roof-cells.json").read_text())
    out = {}
    for m in MODULES:
        t = Template(D24F / m / "restored.nbt")
        mask = build_mask(t)
        prot = {tuple(e["pos"]) for e in inv[m]["protected"]} | {tuple(e["pos"]) for e in roofs[m]["roof_cells"]}
        c = Counter()
        for p, st in t.state.items():
            if P.name(st) not in P.ANCIENT_CITY_REPLACEABLE or p in prot:
                continue
            x, y, z = p
            if mask.get((x, y - 1, z)) in CLEARED:
                c["above_interior_not_single_layer_roof"] += 1
            elif any(mask.get(q) in CLEARED for q in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1))):
                c["wall_beside_interior"] += 1
            elif mask.get((x, y + 1, z)) in CLEARED:
                c["floor_below_interior"] += 1
            else:
                c["not_touching_interior"] += 1
        out[m] = dict(c)
        print(m, dict(c))
    (D24I / "roof/remaining-decay-openings.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
