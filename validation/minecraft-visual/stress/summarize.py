#!/usr/bin/env python3
"""Aggregate run_stress.py / run_traversal.py output into a compact JSON + Markdown evidence summary and enforce invariants."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

FLUID_KEYS = ("water", "lava")
# Vanilla features that run after the structure and may overwrite its outer blocks: deep-dark sculk growth,
# amethyst geodes (smooth_basalt/calcite/amethyst) and monster rooms (cobblestone/mossy_cobblestone).
OVERLAY_FEATURES = {
    "deep_dark_sculk": lambda t: t.startswith("minecraft:sculk"),
    "amethyst_geode": lambda t: t in {"minecraft:smooth_basalt", "minecraft:calcite", "minecraft:amethyst_block", "minecraft:budding_amethyst", "minecraft:air"},
    "monster_room": lambda t: t in {"minecraft:cobblestone", "minecraft:mossy_cobblestone"},
}


def overlay_kind(conversion: str) -> str | None:
    target = conversion.split(" -> ")[1]
    return next((name for name, test in OVERLAY_FEATURES.items() if test(target)), None)


def site_row(seed: int, site: dict) -> dict:
    post, after = site["post_generation"], site["after_ticks"]
    chamber_fluid = None
    aps = post["apertures"]
    return {
        "seed": seed,
        "chunk": site["candidate_chunk"],
        "plaza_biome": post["plaza_biome"],
        "surface_biome": post["surface_biome_at_center"],
        "rotation": post["chamber_rotation"],
        "y_range": post["y_range"],
        "surface_clearance_above_top": (post["surface_min_y_sampled"] - post["y_range"][1]) if post["surface_min_y_sampled"] is not None else None,
        "dimensions": post["dimensions"],
        "bounds": [post["bounds_inclusive"]["min"], post["bounds_inclusive"]["max"]],
        "blocks_matched": f'{post["integrity"]["matched"]}/{post["integrity"]["expected_solid_blocks"]}',
        "block_conversions_after_ticks": after["integrity"]["mismatch_kinds"],
        "footprint_biomes": post["footprint_biomes"],
        "chamber_non_air": after["interior"].get("non_air_by_piece", {}).get("main_chamber", {}),
        "tunnel_non_air": {k: v for k, v in after["interior"].get("non_air_by_piece", {}).items() if k != "main_chamber"},
        "blocks_matched_after_ticks": f'{after["integrity"]["matched"]}/{after["integrity"]["expected_solid_blocks"]}',
        "exterior_contact_blocks": post["boundary_contact"]["structure_blocks_touching"],
        "exterior_shell_counts": post["boundary_contact"]["shell_counts"],
        "apertures": {k: {"state": v["state"], "outside": v["outside_counts"], "interior": v["aperture_interior_counts"]} for k, v in aps.items()},
        "interior_non_air_post": {k: v for k, v in post["interior"]["counts"].items() if k != "air"},
        "interior_non_air_after_ticks": {k: v for k, v in after["interior"]["counts"].items() if k != "air"},
        "trial_chambers": [{"candidate_chunk": t["candidate_chunk"], "chebyshev_chunks": t["chebyshev_chunks"], "start_present": t["start_present"],
                            "bb_gap_blocks": t.get("bb_gap_to_sg01")} for t in site["trial_chambers"]],
    }


def load(directory: Path):
    seeds = []
    for f in sorted(directory.glob("seed-*.json"), key=lambda p: int(p.stem.split("-", 1)[1])):
        seeds.append(json.loads(f.read_text()))
    return seeds


def summarize(seeds: list[dict], traversal: list[dict] | None) -> dict:
    rows, outcomes, census = [], Counter(), Counter()
    inconsistent = []
    for s in seeds:
        for k, v in s["candidate_census"].items():
            census[k] += v
        for site in s["sites"]:
            outcomes[site["outcome"]] += 1
            predicted_free = all(t["chebyshev_chunks"] > 12 for t in site["trial_chambers"])
            if (site["outcome"] == "generated") != predicted_free:
                inconsistent.append([s["seed"], site["candidate_chunk"]])
            if site["outcome"] == "generated":
                rows.append(site_row(s["seed"], site))
    contact = Counter()
    for r in rows:
        for kind, count in r["exterior_contact_blocks"].items():
            if count:
                contact[kind] += 1
    apertures = Counter(a["state"] for r in rows for a in r["apertures"].values())
    interior_fluid_sites = [r for r in rows if any(k in r["interior_non_air_after_ticks"] for k in FLUID_KEYS)]
    out = {
        "seeds": [s["seed"] for s in seeds],
        "sample": {"seeds": len(seeds), "sites_loaded": sum(outcomes.values()), "generated_sites": len(rows), "outcomes": dict(outcomes),
                   "sg01_candidates_in_scanned_rings": census["candidates_in_ring"],
                   "candidates_predicted_suppressed_by_trial_exclusion": census["predicted_exclusion_suppressed"],
                   "candidates_predicted_free": census["predicted_free"],
                   "prediction_vs_minecraft_mismatches": inconsistent},
        "rotations": dict(Counter(r["rotation"] for r in rows)),
        "plaza_biomes": dict(Counter(r["plaza_biome"] for r in rows).most_common()),
        "surface_biomes": dict(Counter(r["surface_biome"] for r in rows).most_common()),
        "y_min_range": [min(r["y_range"][0] for r in rows), max(r["y_range"][0] for r in rows)] if rows else None,
        "y_top_max": max(r["y_range"][1] for r in rows) if rows else None,
        "min_surface_clearance_above_structure_top": min((r["surface_clearance_above_top"] for r in rows if r["surface_clearance_above_top"] is not None), default=None),
        "integrity": {"sites_with_all_blocks_matched_post_generation": sum(r["blocks_matched"].split("/")[0] == r["blocks_matched"].split("/")[1] for r in rows),
                      "sites_with_all_blocks_matched_after_ticks": sum(r["blocks_matched_after_ticks"].split("/")[0] == r["blocks_matched_after_ticks"].split("/")[1] for r in rows)},
        "exterior_contact_sites": {"cave_air": contact["air"], "water": contact["water"], "lava": contact["lava"], "of": len(rows)},
        "aperture_states": dict(apertures),
        "feature_overlay_sites": {name: sum(1 for r in rows if any(overlay_kind(k) == name for k in r["block_conversions_after_ticks"])) for name in OVERLAY_FEATURES},
        "interior_shrieker_sites": sum(1 for r in rows if r["interior_non_air_after_ticks"].get("block:minecraft:sculk_shrieker")),
        "sculk_conversion_sites": [{"seed": r["seed"], "chunk": r["chunk"], "converted": r["block_conversions_after_ticks"],
                                    "footprint_biomes": r["footprint_biomes"],
                                    "interior_sculk": {k: v for k, v in r["interior_non_air_after_ticks"].items() if "sculk" in k}}
                                   for r in rows if any(overlay_kind(k) == "deep_dark_sculk" for k in r["block_conversions_after_ticks"])],
        "interior_fluid_sites": [{"seed": r["seed"], "chunk": r["chunk"], "interior_non_air": r["interior_non_air_after_ticks"],
                                  "apertures": {k: v for k, v in r["apertures"].items() if v["state"] == "flooded"}} for r in interior_fluid_sites],
        "interior_vegetation_sites": sum(any(k.startswith("block:") for k in r["interior_non_air_after_ticks"]) for r in rows),
        "trial_chamber_min_bb_gap_blocks": min((t["bb_gap_blocks"] for r in rows for t in r["trial_chambers"] if t["bb_gap_blocks"] is not None), default=None),
        "trial_chamber_pairs_measured": sum(1 for r in rows for t in r["trial_chambers"] if t["bb_gap_blocks"] is not None),
        "sites": rows,
    }
    fluid_tags = {f"s{r['seed']}_c{r['chunk'][0]}_{r['chunk'][1]}" for r in interior_fluid_sites}
    if traversal:
        legs = [(t["seed"], leg) for t in traversal for leg in t["legs"]]
        sites = [site for t in traversal for site in t["sites"] if site.get("tag")]
        walk = [(s, l) for s, l in legs if ":outward_probe_" not in l["id"]]
        out["traversal"] = {
            "method": "Minecraft 26.3 runtime: player-width Zombie driven by PathNavigation/MoveControl/JumpControl and entity collision; NOT a live player",
            "sites": len(sites), "legs": len(legs), "interior_legs": len(walk),
            "interior_legs_pass": sum(l["result"] == "PASS" for _s, l in walk),
            "interior_failures": [l["id"] for _s, l in walk if l["result"] != "PASS" and l["id"].split(":")[0] not in fluid_tags],
            "failures_into_fluid_filled_mouths": [l["id"] for _s, l in walk if l["result"] != "PASS" and l["id"].split(":")[0] in fluid_tags],
            "outward_probe_counts": dict(Counter(l["result"] for _s, l in legs if ":outward_probe_" in l["id"])),
            "stair_up_legs_requiring_jump": sum(1 for _s, l in legs if "_up_to_ring" in l["id"] and l["max_y"] > l["goal"][1] + 0.1),
            "stair_up_legs": sum(1 for _s, l in legs if "_up_to_ring" in l["id"]),
            "rotations": dict(Counter(s["rotation"] for s in sites)),
            "completed": all(t["completed"] for t in traversal),
        }
    return out


def check(summary: dict) -> list[str]:
    problems = []
    s = summary["sample"]
    if not s["generated_sites"]:
        problems.append("no generated sites")
    if s["prediction_vs_minecraft_mismatches"]:
        problems.append(f"exclusion-zone prediction disagrees with Minecraft at {s['prediction_vs_minecraft_mismatches']}")
    unexplained = [(r["seed"], r["chunk"], r["block_conversions_after_ticks"]) for r in summary["sites"]
                   if any(overlay_kind(kind) is None for kind in r["block_conversions_after_ticks"])]
    if unexplained:
        problems.append(f"structure blocks replaced by something other than a known vanilla feature overlay: {unexplained}")
    shriekers = [(r["seed"], r["chunk"]) for r in summary["sites"] if r["interior_non_air_after_ticks"].get("block:minecraft:sculk_shrieker")]
    if shriekers:
        problems.append(f"summon-capable sculk shriekers inside the structure: {shriekers}")
    sculk_heavy = [(r["seed"], r["chunk"]) for r in summary["sites"]
                   if sum(v for k, v in r["block_conversions_after_ticks"].items() if k.split(" -> ")[1].startswith("minecraft:sculk")) > 20]
    if sculk_heavy:
        problems.append(f"sculk replaced more than 20 structure blocks (F-2 regression): {sculk_heavy}")
    chamber_fluid = [(r["seed"], r["chunk"]) for r in summary["sites"] if r["chamber_non_air"].get("fluid")]
    if chamber_fluid:
        problems.append(f"fluid inside the main chamber: {chamber_fluid}")
    t = summary.get("traversal")
    if t:
        if not t["completed"]:
            problems.append("traversal run did not complete")
        if t["stair_up_legs_requiring_jump"]:
            problems.append(f"{t['stair_up_legs_requiring_jump']} stair-up legs still needed a jump (F-4 regression)")
        if t["interior_failures"]:
            problems.append(f"interior traversal legs failed: {t['interior_failures']}")
    return problems


def check_pinned(summary: dict, pinned: list[dict]) -> list[str]:
    """Determinism regression: sites that showed a specific interaction must reproduce it from the same seed and datapack."""
    problems = []
    sites = {(r["seed"], tuple(r["chunk"])): r for r in summary["sites"]}
    for pin in pinned:
        key = (pin["seed"], tuple(pin["chunk"]))
        site = sites.get(key)
        if site is None:
            problems.append(f"pinned site {key} did not generate")
            continue
        for what, expected in pin["expect"].items():
            if what == "bounds":
                actual = site["bounds"]
                ok = actual == expected
            elif what == "block_conversions_to_sculk_max":
                actual = sum(v for k, v in site["block_conversions_after_ticks"].items() if k.split(" -> ")[1].startswith("minecraft:sculk"))
                ok = actual <= expected
            elif what == "interior_shriekers_max":
                actual = site["interior_non_air_after_ticks"].get("block:minecraft:sculk_shrieker", 0)
                ok = actual <= expected
            elif what == "block_conversions_to_sculk":
                actual = sum(v for k, v in site["block_conversions_after_ticks"].items() if k.split(" -> ")[1].startswith("minecraft:sculk"))
                ok = actual >= expected
            elif what == "tunnel_fluid":
                actual = sum(v.get("fluid", 0) for v in site["tunnel_non_air"].values())
                ok = actual >= expected
            elif what == "open_mouths":
                actual = sum(1 for a in site["apertures"].values() if a["state"] == "open_to_cave")
                ok = actual >= expected
            elif what == "rotation":
                actual = site["rotation"]
                ok = actual == expected
            else:
                problems.append(f"unknown pinned expectation {what}")
                continue
            if not ok:
                problems.append(f"pinned {key}: {what} expected {expected!r}, got {actual!r}")
    return problems


def markdown(summary: dict) -> str:
    s = summary["sample"]
    lines = ["# SG-01 environmental stress summary (generated)", "",
             f"Seeds: {summary['seeds']}", "",
             f"- Loaded sites: **{s['sites_loaded']}**; generated: **{s['generated_sites']}**; outcomes: `{s['outcomes']}`",
             f"- Candidate census over scanned rings: {s['sg01_candidates_in_scanned_rings']} candidates, "
             f"{s['candidates_predicted_suppressed_by_trial_exclusion']} predicted suppressed by the trial-chambers exclusion zone, "
             f"{s['candidates_predicted_free']} free. Prediction vs Minecraft mismatches: {s['prediction_vs_minecraft_mismatches'] or 'none'}",
             f"- Rotations: `{summary['rotations']}`; structure Y-min range {summary['y_min_range']}, highest top {summary['y_top_max']}; "
             f"minimum sampled surface clearance above the structure top: {summary['min_surface_clearance_above_structure_top']} blocks",
             f"- Block integrity (all 8,575 expected blocks matched): post-generation {summary['integrity']['sites_with_all_blocks_matched_post_generation']}/{s['generated_sites']}, "
             f"after advancing ticks {summary['integrity']['sites_with_all_blocks_matched_after_ticks']}/{s['generated_sites']}",
             f"- Exterior contact (sites where structure blocks touch): {summary['exterior_contact_sites']}",
             f"- Tunnel-mouth states over all mouths: `{summary['aperture_states']}`",
             f"- Sites where a later vanilla feature overwrote structure blocks: `{summary['feature_overlay_sites']}`; sites with sculk shriekers inside template air: {summary['interior_shrieker_sites']}",
             f"- Interior fluid sites: {len(summary['interior_fluid_sites'])}; sites with natural vegetation inside template air: {summary['interior_vegetation_sites']}",
             f"- Trial Chambers: {summary['trial_chamber_pairs_measured']} generated pairs, minimum bounding-box gap {summary['trial_chamber_min_bb_gap_blocks']} blocks",
             ""]
    if "traversal" in summary:
        t = summary["traversal"]
        lines += [f"- Runtime traversal ({t['method']}): {t['sites']} sites, {t['interior_legs_pass']}/{t['interior_legs']} interior legs PASS; "
                  f"stair-up legs needing a jump: {t['stair_up_legs_requiring_jump']}/{t['stair_up_legs']}; legs into fluid-filled mouths that failed (expected): {t['failures_into_fluid_filled_mouths']}; outward probes (6 blocks past a mouth): `{t['outward_probe_counts']}`", ""]
    lines += ["| seed | chunk | plaza biome | surface biome | rot | Y range | blocks | contact air/water/lava (blocks) | mouths | interior non-air |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["sites"]:
        c = r["exterior_contact_blocks"]
        mouths = ",".join(v["state"][0].upper() for v in r["apertures"].values())  # B=blocked, O=open_to_cave, F=flooded
        lines.append(f"| {r['seed']} | {r['chunk']} | {r['plaza_biome'].removeprefix('minecraft:')} | {r['surface_biome'].removeprefix('minecraft:')} | {r['rotation']} | "
                     f"{r['y_range']} | {r['blocks_matched']} | {c['air']}/{c['water']}/{c['lava']} | {mouths} | {r['interior_non_air_after_ticks'] or '-'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stress-dir", type=Path, required=True)
    p.add_argument("--traversal", type=Path)
    p.add_argument("--out-json", type=Path, required=True)
    p.add_argument("--out-md", type=Path, required=True)
    p.add_argument("--pinned", type=Path)
    p.add_argument("--synthetic", type=Path)
    p.add_argument("--no-enforce", action="store_true")
    args = p.parse_args()
    seeds = load(args.stress_dir)
    traversal = json.loads(args.traversal.read_text()) if args.traversal and args.traversal.exists() else None
    summary = summarize(seeds, traversal)
    args.out_json.write_text(json.dumps(summary, indent=1) + "\n")
    text = markdown(summary)
    if "synthetic" in summary:
        syn = summary["synthetic"]
        text += (f"\n## Synthetic fluid scenarios (supplementary, NOT natural generation)\n\nSeed {syn['seed']} chunk {syn['site_chunk']}: {syn['scenarios']} filled against sealed mouths; "
                 f"after {syn['ticks']} ticks fluid cells by piece: `{syn['fluid_cells_by_piece_after']}`; integrity {syn['integrity_after']}\n")
    args.out_md.write_text(text)
    if args.synthetic and args.synthetic.exists():
        syn = json.loads(args.synthetic.read_text())
        summary["synthetic"] = {"label": syn["label"], "seed": syn["seed"], "site_chunk": syn["site"]["chunk"], "scenarios": [(x["fluid"], x["mouth"]) for x in syn["scenarios"]],
                                "fluid_cells_by_piece_after": syn["fluid_cells_by_piece"], "integrity_after": syn["integrity_after"], "ticks": syn["after_ticks"]}
        args.out_json.write_text(json.dumps(summary, indent=1) + "\n")
    problems = check(summary)
    if args.pinned:
        problems += check_pinned(summary, json.loads(args.pinned.read_text()))
    if "synthetic" in summary:
        syn = summary["synthetic"]
        if any(k.startswith("main_chamber") for k in syn["fluid_cells_by_piece_after"]):
            problems.append("synthetic fluid reached the main chamber")
        if syn["integrity_after"]["mismatched"]:
            problems.append("synthetic fluid scenario damaged structure blocks")
    print(text.split("| seed")[0] + (text[text.index("## Synthetic"):] if "## Synthetic" in text else ""))
    if problems:
        print("INVARIANT FAILURES:", *problems, sep="\n  ")
        if not args.no_enforce:
            sys.exit(1)


if __name__ == "__main__":
    main()
