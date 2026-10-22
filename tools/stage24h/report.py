"""Stage 24-H sweep summary: F/G/H comparison, the four reported cases, fluids, decay identity, issue register."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "artifacts/ancient-city-restoration/stage-24f/worldgen"
G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
C = ROOT / "artifacts/ancient-city-restoration/stage-24c/worldgen"
KEY = ("pos", "rotation", "bb", "ground_level_delta", "junction_count", "template")
CASES = [(24005, "medium_ruin_1"), (24009, "large_ruin_1"), (24008, "small_ruin_1"), (24014, "sauna_1")]


def j(p):
    return json.loads(Path(p).read_text())


def main():
    s = {}
    same_fg = same_gh = 0
    for seed in range(24001, 24025):
        f = j(F / f"manifest-{seed}-f24.json")["cities"][0]["pieces"]
        g = j(G / f"worldgen/manifest-{seed}-g24.json")["cities"][0]["pieces"]
        h = j(H / f"worldgen/manifest-{seed}-h24.json")["cities"][0]["pieces"]
        same_fg += [tuple(str(p[k]) for k in KEY) for p in f] == [tuple(str(p[k]) for k in KEY) for p in g]
        same_gh += [tuple(str(p[k]) for k in KEY) for p in g] == [tuple(str(p[k]) for k in KEY) for p in h]
    s["cities_layout_identical_f24_g24"] = same_fg
    s["cities_layout_identical_g24_h24"] = same_gh
    ana = j(H / "worldgen/h24-analysis.json")
    s["vanilla_identical_except_approved_heights"] = sum(1 for c in ana if c["placements_identical_to_vanilla"])
    s["bounding_box_overlaps"] = sum(len(m["overlapping_pieces"]) for c in ana for m in c["modules"])
    surv = {}
    for v, p in (("g24", G / "worldgen/g24-functional-survival.json"), ("h24", H / "worldgen/h24-functional-survival.json")):
        d = j(p)
        surv[v] = {"cells": len(d), "status": dict(Counter(r["status"] for r in d))}
    s["protected_cell_survival"] = surv
    rep = {}
    for v, p in (("g24", G / "worldgen/g24-processor-replay.json"), ("h24", H / "worldgen/h24-processor-replay.json")):
        d = j(p)
        t = Counter()
        rot_cells = set()
        for r in d:
            t.update(r["tally"])
            rot_cells |= {(r["seed"], tuple(x["world"])) for x in r["losses"] if x["cause"] == "block_rot"}
        rep[v] = {"tally": dict(t), "block_rot_cells": len(rot_cells), "_cells": rot_cells}
    s["decay"] = {"g24_block_rot_cells": rep["g24"]["block_rot_cells"], "h24_block_rot_cells": rep["h24"]["block_rot_cells"],
                  "identical_positions": rep["g24"]["_cells"] == rep["h24"]["_cells"],
                  "h24_tally": rep["h24"]["tally"]}
    cmp_ = j(H / "worldgen/fgh-comparison.json")
    tot = Counter()
    for r in cmp_:
        for p in r["pieces"]:
            tot.update(p["counts"])
    s["fgh_cell_comparison_totals"] = dict(sorted(tot.items()))
    s["mask_cells_total"] = sum(v for k, v in tot.items() if k.startswith("mask_"))
    cases = []
    for seed, m in CASES:
        r = next(x for x in cmp_ if x["seed"] == seed)
        pcs = [p for p in r["pieces"] if p["module"] == m]
        p = max(pcs, key=lambda q: sum(q["mask_terrain_g24"].values()) + q.get("fluid", {}).get("cells_in_mask", 0))
        mask_cells = sum(v for k, v in p["counts"].items() if k.startswith("mask_"))
        cases.append({"seed": seed, "module": m, "piece_index": p["piece_index"], "rotation": p["rotation"], "bb": p["bb"],
                      "mask_cells": mask_cells, "terrain_in_mask_f24": p["mask_terrain_f24"], "terrain_in_mask_g24": p["mask_terrain_g24"],
                      "h24_mask_states": {k: v for k, v in p["counts"].items() if k.startswith("mask_")},
                      "architecture_differences_g24_h24": p["counts"].get("diff_architecture_UNEXPLAINED", 0),
                      "fluid": p.get("fluid")})
    s["cases"] = cases
    terr = {v: dict(Counter((r["seed"], r["module"], r["class"], r["block"]) for r in j(p)).items())
            for v, p in (("g24", G / "worldgen/g24-terrain-classification.json"), ("h24", H / "worldgen/h24-terrain-classification.json"))}
    s["terrain_classes"] = {v: dict(Counter(k[2] for k, n in t.items() for _ in range(n))) for v, t in terr.items()}
    city = H / "live/city-gameplay/summary-city.json"
    if city.exists():
        s["city_gameplay"] = j(city)
    s["reproducibility"] = j(H / "worldgen/reproducibility.json")
    (H / "worldgen/h24-summary.json").write_text(json.dumps(s, indent=1, default=str))
    issues = []
    for t in j(H / "worldgen/h24-terrain-classification.json"):
        issues.append({"seed": t["seed"], "structure": t["module"], "world": t["world"], "template_pos": t["template_pos"], "type": "terrain_" + t["class"],
                       "block": t["block"], "root_cause": t["reason"]})
    for r in cmp_:
        for p in r["pieces"]:
            if p.get("fluid"):
                f = p["fluid"]
                issues.append({"seed": r["seed"], "structure": p["module"], "type": "fluid_in_interior_mask", "cells": f["cells_in_mask"],
                               "sources": f["sources"], "entries": f["entries"],
                               "root_cause": "fluid placed or flowing after the piece (spring / exterior flow) entering through decay holes or open paving"})
            for k in ("mask_sculk_sculk_sensor", "mask_sculk_sculk_shrieker", "mask_sculk_sculk_catalyst"):
                if p["counts"].get(k):
                    issues.append({"seed": r["seed"], "structure": p["module"], "type": "sculk_block_in_interior_mask", "block": k.split("_", 3)[-1],
                                   "cells": p["counts"][k], "root_cause": "vanilla sculk patches (deep dark decoration, after the piece) grow into cleared air"})
            if p["counts"].get("diff_natural_terrain_outside_mask") or p["counts"].get("diff_natural_terrain_stored_cell"):
                issues.append({"seed": r["seed"], "structure": p["module"], "type": "natural_terrain_differs_g24_h24",
                               "cells": p["counts"].get("diff_natural_terrain_outside_mask", 0) + p["counts"].get("diff_natural_terrain_stored_cell", 0),
                               "root_cause": "natural features differ between runs; see reproducibility.json for which part is noise and which follows the cleared room"})
    (H / "worldgen/h24-issues.json").write_text(json.dumps(issues, indent=1))
    print(json.dumps({k: v for k, v in s.items() if k not in ("cases", "reproducibility")}, indent=1, default=str))
    for c in cases:
        print(c["seed"], c["module"], c["mask_cells"], c["terrain_in_mask_f24"], c["terrain_in_mask_g24"], c["h24_mask_states"])


if __name__ == "__main__":
    main()
