"""Classify every terrain/lava cell found inside a restored piece's bounding box after real generation.

Classes (Stage 24-G brief):
  functional_obstruction        the cell is a body/head cell of a walkable interior cell, a doorway, or the access cell
                                of a bed/container -> it blocks use of the building
  potential_generation_hazard   lava (or other fluid) inside the box next to a walkable or interior cell
  cosmetic_intrusion            terrain in a cell the template leaves unspecified that is visible from outside the
                                building (above the roof line / beside the walls) but does not block anything
  existing_vanilla_behaviour    the same cell is also left unspecified by the vanilla template of the same piece, and
                                the block is natural terrain that pre-dates or follows structure placement
The template never writes unspecified cells (StructureTemplate only places the blocks it stores), so any terrain
there is whatever noise generation, carvers and features put in that cell before or after the piece was placed.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import load_nbt, blocks_of  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT  # noqa: E402
from tools.stage24g.roles import Template, reachable, stand, ladder, short  # noqa: E402

VANILLA = Path("/tmp/mc/vanilla_nbt/data/minecraft/structure/ancient_city/structures")
FLUIDS = {"lava", "water"}


def inv_rot(rel, r):
    x, y, z = rel
    return {0: (x, y, z), 90: (z, y, -x), 180: (-x, y, -z), 270: (-z, y, x)}[r]


def functional_cells(t: Template):
    reach = reachable(t)
    body = set()
    for p in reach:
        if stand(t, p) or ladder(t, p):
            body |= {p, (p[0], p[1] + 1, p[2])}
    for p, st in t.state.items():
        if short(st).endswith("_door"):
            body.add(p)
    return reach, body


def classify(t: Template, vanilla_cells, rel, block):
    reach, body = functional_cells(t)
    x, y, z = rel
    near = [(x + dx, y + dy, z + dz) for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    if block in FLUIDS and any(n in body for n in near + [rel]):
        return "potential_generation_hazard", "fluid touches a walkable/interior cell"
    if rel in body:
        return "functional_obstruction", "occupies a walkable body/head cell"
    if block in FLUIDS:
        return "potential_generation_hazard", "fluid inside the piece box (not touching a walkable cell)"
    if vanilla_cells is not None and rel not in vanilla_cells:
        return "existing_vanilla_behaviour", "cell is also unspecified in the vanilla template; natural terrain"
    return "cosmetic_intrusion", "cell is specified by vanilla but left unspecified by the restoration"


def run(analysis_path: Path, src: Path, label: str):
    data = json.loads(analysis_path.read_text())
    rows = []
    cache = {}
    for city in data:
        for rec in city["modules"]:
            cells = rec.get("terrain_cells_in_bb_list") or []
            if not cells:
                continue
            m = rec["module"]
            if m not in cache:
                t = Template(src / m / "restored.nbt")
                vp = VANILLA / f"{m}.nbt"
                vcells = set(blocks_of(load_nbt(vp))) if vp.exists() else None
                jig = {p for p, s in t.state.items() if s.startswith("minecraft:jigsaw")}
                cache[m] = (t, vcells, jig)
            t, vcells, jig = cache[m]
            r = ROT[rec["rotation"]]
            o = rec["pos"]
            for x, y, z, b in cells:
                rel = inv_rot((x - o[0], y - o[1], z - o[2]), r)
                if rel in jig:
                    continue  # jigsaw final_state, not terrain
                cls, why = classify(t, vcells, rel, b)
                rows.append({"variant": label, "seed": city["seed"], "module": m, "rotation": rec["rotation"], "world": [x, y, z],
                             "template_pos": list(rel), "block": b, "class": cls, "reason": why,
                             "in_added_height": rel[1] >= int(load_nbt(Path("artifacts/ancient-city-restoration/stage-24b") / m / "restored.nbt")["size"][1])})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = run(Path(a.analysis), Path(a.src), a.label)
    Path(a.out).write_text(json.dumps(rows, indent=1))
    c = Counter((r["seed"], r["module"], r["class"], r["block"]) for r in rows)
    for k, v in sorted(c.items()):
        print(v, *k)
