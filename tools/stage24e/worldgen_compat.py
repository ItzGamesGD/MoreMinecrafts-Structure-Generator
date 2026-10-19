"""Summarise the real-generation sweeps of the taller Stage 24-E options (moves the raw sweep files into stage-24e/worldgen)."""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S24C = ROOT / "artifacts/ancient-city-restoration/stage-24c/worldgen"
D24E = ROOT / "artifacts/ancient-city-restoration/stage-24e"
SETS = {"e24B": "B", "e24C": "C"}
# vanilla city decoration and empty space are not terrain intrusion
NON_TERRAIN = {"air", "cave_air", "void_air", "water", "unloaded", "sculk_vein", "glow_lichen", "vine", "sculk", "sculk_sensor", "sculk_shrieker", "sculk_catalyst"}


def main():
    (D24E / "worldgen").mkdir(parents=True, exist_ok=True)
    for f in list(S24C.glob("manifest-*-e24*.json")) + list(S24C.glob("e24*-analysis.json")):
        shutil.move(str(f), D24E / "worldgen" / f.name)
    out = {}
    for tag, letter in SETS.items():
        p = D24E / "worldgen" / f"{tag}-analysis.json"
        if not p.exists():
            continue
        cities = json.loads(p.read_text())
        same = sum(1 for c in cities if c["placements_identical_to_vanilla"])
        per = {}
        for c in cities:
            for m in c["modules"]:
                if not (D24E / "proposals" / m["module"] / letter / "candidate.nbt").exists():
                    continue
                d = per.setdefault(m["module"], {"pieces": 0, "overlaps": 0, "seeds": set(), "expansion_solid": [], "fill": Counter(), "rotations": Counter(), "clear_above": []})
                d["pieces"] += 1
                d["seeds"].add(c["seed"])
                d["overlaps"] += len(m["overlapping_pieces"])
                d["rotations"][m["rotation"]] += 1
                if m.get("vertical_clearance_to_piece_above") is not None:
                    d["clear_above"].append(m["vertical_clearance_to_piece_above"])
                e = m.get("expansion_layers")
                if e:
                    terrain = sum(v for k, v in e["unspecified_fill"].items() if k not in NON_TERRAIN)
                    d["expansion_solid"].append(terrain)
                    d["fill"].update(e["unspecified_fill"])
        for mod, d in per.items():
            sol = d["expansion_solid"]
            summ = (f"{d['pieces']} generated pieces in {len(d['seeds'])} of {len(cities)} cities; placements identical to vanilla in {same}/{len(cities)} cities; "
                    f"{d['overlaps']} bounding-box overlaps; terrain cells inside the added height: max {max(sol) if sol else 0}, "
                    f"pieces with any {sum(1 for s in sol if s)} of {len(sol)}")
            out.setdefault(mod, {})[letter] = {"summary": summ, "pieces": d["pieces"], "cities": len(cities), "cities_with_piece": len(d["seeds"]),
                                                "placements_identical_cities": same, "bb_overlaps": d["overlaps"],
                                                "expansion_terrain_cells_per_piece": sol, "expansion_fill": dict(d["fill"].most_common(8)),
                                                "rotations": dict(d["rotations"]), "vertical_clearance_to_piece_above": d["clear_above"]}
            print(mod, letter, summ)
    (D24E / "worldgen-compat.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
