#!/usr/bin/env python3
"""Compare generation-step variants against a baseline summary.json produced by summarize.py (SG-01-C, F-2)."""
import argparse
import json
from pathlib import Path

from summarize import overlay_kind


def metrics(summary: dict) -> dict:
    rows = summary["sites"]
    conv = {"deep_dark_sculk": 0, "amethyst_geode": 0, "monster_room": 0}
    sites = {k: 0 for k in conv}
    for r in rows:
        seen = set()
        for kind, n in r["block_conversions_after_ticks"].items():
            name = overlay_kind(kind)
            conv[name] += n
            seen.add(name)
        for name in seen:
            sites[name] += 1
    interior = lambda key: sum(r["interior_non_air_after_ticks"].get(key, 0) for r in rows)
    return {
        "loaded": summary["sample"]["sites_loaded"], "generated": summary["sample"]["generated_sites"],
        "suppressed": summary["sample"]["outcomes"].get("suppressed_by_exclusion_zone", 0),
        "prediction_mismatches": len(summary["sample"]["prediction_vs_minecraft_mismatches"]),
        "sites_all_blocks_match": summary["integrity"]["sites_with_all_blocks_matched_after_ticks"],
        "overlay_sites": sites, "overlay_blocks": conv,
        "interior_sculk_sensors": interior("block:minecraft:sculk_sensor"), "interior_shriekers": interior("block:minecraft:sculk_shrieker"),
        "interior_sculk_catalysts": interior("block:minecraft:sculk_catalyst"), "interior_sculk_veins": interior("block:minecraft:sculk_vein"),
        "sites_with_interior_shrieker": summary["interior_shrieker_sites"],
        "interior_vegetation_sites": summary["interior_vegetation_sites"],
        "interior_vegetation_blocks": sum(v for r in rows for k, v in r["interior_non_air_after_ticks"].items()
                                          if k in ("block:minecraft:glow_lichen", "block:minecraft:cave_vines", "block:minecraft:cave_vines_plant",
                                                   "block:minecraft:vine", "block:minecraft:spore_blossom")),
        "interior_fluid_sites": len(summary["interior_fluid_sites"]),
        "chamber_fluid_sites": sum(1 for r in rows if r["chamber_non_air"].get("fluid")),
        "trial_pairs": summary["trial_chamber_pairs_measured"], "trial_min_gap": summary["trial_chamber_min_bb_gap_blocks"],
        "rotations": summary["rotations"],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--variant", action="append", required=True, metavar="NAME=summary.json")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    runs = {"baseline(strongholds)": json.loads(a.baseline.read_text())}
    for v in a.variant:
        name, path = v.split("=", 1)
        runs[name] = json.loads(Path(path).read_text())
    table = {n: metrics(s) for n, s in runs.items()}
    # per-site comparison on common generated sites
    base_sites = {(r["seed"], tuple(r["chunk"])): r for r in runs["baseline(strongholds)"]["sites"]}
    per_site = {}
    for n, s in runs.items():
        if n.startswith("baseline"):
            continue
        same_geom = diff = 0
        for r in s["sites"]:
            b = base_sites.get((r["seed"], tuple(r["chunk"])))
            if not b:
                continue
            same = (b["bounds"], b["rotation"]) == (r["bounds"], r["rotation"])
            same_geom += same
            diff += not same
        per_site[n] = {"common_sites_identical_bounds_and_rotation": same_geom, "common_sites_different_placement": diff}
    out = {"metrics": table, "placement_vs_baseline": per_site}
    text = json.dumps(out, indent=1)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
