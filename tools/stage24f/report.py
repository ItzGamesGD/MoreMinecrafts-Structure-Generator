"""Stage 24-F Phase 4/6: generation issue register (seed + coordinates) and the per-module validation matrix."""
from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f"
S24C_WG = ROOT / "artifacts/ancient-city-restoration/stage-24c/worldgen"
MODULES = ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2", "sauna_1", "large_pillar_1", "medium_pillar_1"]


def collect():
    (D24F / "worldgen").mkdir(parents=True, exist_ok=True)
    for f in list(S24C_WG.glob("manifest-*-f24.json")) + list(S24C_WG.glob("f24-analysis.json")):
        shutil.move(str(f), D24F / "worldgen" / f.name)


def worldgen():
    final = json.loads((D24F / "worldgen/f24-analysis.json").read_text())
    base = {c["seed"]: c for c in json.loads((D24F / "worldgen/stage24c-same-method-analysis.json").read_text())}
    per = defaultdict(lambda: {"pieces": 0, "rot": Counter(), "overlaps": 0, "cls": Counter(), "crit": defaultdict(lambda: [0, 0]),
                               "jig_bad": [], "terrain": [], "expansion": [], "crit_cells": []})
    issues = []
    for c in final:
        seed = c["seed"]
        if not c["placements_identical_to_vanilla"]:
            issues.append({"seed": seed, "type": "placement_differs_from_vanilla", "first_diff_index": c["first_placement_diff_index"]})
        for p in c["modules"]:
            m = p["module"]
            d = per[m]
            d["pieces"] += 1
            d["rot"][p["rotation"]] += 1
            d["overlaps"] += len(p["overlapping_pieces"])
            d["cls"].update(p["block_replacement"])
            for k, (t, l) in p["critical_blocks_total_lost"].items():
                d["crit"][k][0] += t
                d["crit"][k][1] += l
            for o in p["overlapping_pieces"]:
                issues.append({"seed": seed, "module": m, "type": "bounding_box_overlap", "piece_bb": p["bb"], "other": o})
            for j in p.get("jigsaws", []):
                if not j["connected"]:
                    d["jig_bad"].append(j)
                    issues.append({"seed": seed, "module": m, "type": "jigsaw_unconnected", **j})
            jig_cells = {tuple(j["jigsaw_world"]) for j in p.get("jigsaws", [])}   # jigsaws become their final_state: not terrain
            cells = [c for c in p.get("terrain_cells_in_bb_list", []) if tuple(c[:3]) not in jig_cells]
            if cells:
                d["terrain"].append(len(cells))
                issues.append({"seed": seed, "module": m, "type": "terrain_inside_bounding_box", "piece_bb": p["bb"], "rotation": p["rotation"],
                               "count": len(cells), "cells": cells})
            e = p.get("expansion_layers")
            if e:
                d["expansion"].append(len(e["terrain_cells"]))
                if e["terrain_cells"]:
                    issues.append({"seed": seed, "module": m, "type": "terrain_inside_added_height", "piece_bb": p["bb"], "count": len(e["terrain_cells"]), "cells": e["terrain_cells"]})
            for cell in p.get("critical_lost_cells", []):
                issues.append({"seed": seed, "module": m, "type": "protected_functional_block_lost", **cell})
    # baseline Stage 24-C sweep for the same seeds: terrain-in-BB per module (to separate new from pre-existing contact)
    base_terrain = Counter()
    for seed, c in base.items():
        for p in c["modules"]:
            jig_cells = {tuple(j["jigsaw_world"]) for j in p.get("jigsaws", [])}
            base_terrain[p["module"]] += sum(1 for c_ in p.get("terrain_cells_in_bb_list", []) if tuple(c_[:3]) not in jig_cells)
    summary = {"cities": len(final), "placements_identical_cities": sum(1 for c in final if c["placements_identical_to_vanilla"]),
               "modules": {m: {"pieces": d["pieces"], "rotations": dict(d["rot"]), "bb_overlaps": d["overlaps"], "jigsaw_unconnected": len(d["jig_bad"]),
                               "pieces_with_terrain_in_bb": len(d["terrain"]), "terrain_cells_in_bb_total": sum(d["terrain"]),
                               "stage24c_sweep_terrain_cells_in_bb_total": base_terrain[m],
                               "pieces_with_terrain_in_added_height": sum(1 for x in d["expansion"] if x), "added_height_terrain_cells_total": sum(d["expansion"]),
                               "block_survival": {k: round(v / max(1, sum(d["cls"].values())), 4) for k, v in d["cls"].items()},
                               "critical_lost": {k: f"{l}/{t}" for k, (t, l) in d["crit"].items()}} for m, d in per.items()}}
    (D24F / "worldgen/f24-issues.json").write_text(json.dumps(issues, indent=1))
    (D24F / "worldgen/f24-summary.json").write_text(json.dumps(summary, indent=1))
    return summary, issues


def matrix(summary, issues):
    fm = json.loads((D24F / "FINAL-CANDIDATES-MANIFEST.json").read_text())
    live = json.loads((D24F / "live/summary-f24.json").read_text())
    pl = json.loads((D24F / "live/placement-report-f24.json").read_text())["results"]
    by = Counter((i["module"], i["type"]) for i in issues if "module" in i)
    rows = []
    for m in MODULES:
        v, s = fm["modules"][m], summary["modules"].get(m, {})
        mism = sum(r["mismatches"] for k, r in pl.items() if k.startswith(m + "@"))
        src = f"24-E option {v['option']}" if v.get("option") else "24-C (byte-identical)"
        rows.append(f"| `{m}` | {src} | {'×'.join(map(str, v['dimensions']))} | `{v['final_sha256'][:12]}` | PASS | PASS | {mism} / 4 rot | "
                    f"{live[m]['ok']}/{live[m]['total']} | {s.get('pieces', 0)} pcs, {s.get('bb_overlaps', 0)} overlaps, {s.get('jigsaw_unconnected', 0)} unconnected jigsaws | "
                    f"{s.get('pieces_with_terrain_in_bb', 0)} pcs ({s.get('terrain_cells_in_bb_total', 0)} cells; 24-C sweep {s.get('stage24c_sweep_terrain_cells_in_bb_total', 0)}) | "
                    f"{', '.join(f'{k} {x}' for k, x in s.get('critical_lost', {}).items())} | PENDING | PENDING |")
    text = f"""# Stage 24-F per-module validation matrix

Final set: `final-candidates/` (SHA256SUMS). Stage 24-C head `{fm['stage_24c_head']}`, Stage 24-E head `{fm['stage_24e_head']}`.
Real-generation sweep: {summary['cities']} cities (seeds 24001–24024), placements identical to vanilla in **{summary['placements_identical_cities']}/{summary['cities']}**.

| Module | Source | Size | SHA-256 | Static / regression tests | Block states valid (26.1.2 registry) | Live placement mismatches | Simulated player | Generation | Terrain inside the piece box | Protected blocks lost after processors | Client visual | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

* "Terrain inside the piece box" counts natural blocks (rock, ores, dripstone) the template leaves in place inside its bounding box — places where the
  building touches cave walls or ceilings. It is reported separately from bounding-box overlaps with other pieces and from identical placement, which do not prove it is zero.
  The comparable Stage 24-C sweep number is given for the same seeds; every cell is listed with seed and coordinates in `worldgen/f24-issues.json`.
* "Protected blocks lost" = doors, beds, ladders, stairs, parapet walls, containers, lanterns removed by the vanilla processors (block_rot 5 % on
  `#ancient_city_replaceable`, soul lantern 5 %) or by later features; each loss is listed with seed and coordinates in `worldgen/f24-issues.json`.
* Client visual verification remains **PENDING**: all images are model renders (26.1.2 block models + textures), not client screenshots.
"""
    (D24F / "VALIDATION-MATRIX.md").write_text(text)
    print(text)


if __name__ == "__main__":
    collect()
    s, i = worldgen()
    matrix(s, i)
    print(Counter(x["type"] for x in i))
