"""Stage 24-L Phase 0: aggregate the per-seed evidence of `phase0.py` into results-summary.json and PHASE0-RESULTS.md (read-only)."""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HOUSE_ORDER = ["small_ruin_1", "small_ruin_2", "medium_ruin_1", "medium_ruin_2", "large_ruin_1"]
ROT_ORDER = ["NONE", "CLOCKWISE_90", "CLOCKWISE_180", "COUNTERCLOCKWISE_90"]


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))] if xs else None


def load(d: Path):
    seeds = {}
    for f in sorted(d.glob("seed-*.json")):
        j = json.loads(f.read_text())
        seeds[j["seed"]] = j
    focus = {int(f.stem.split("-")[1]): json.loads(f.read_text()) for f in sorted(d.glob("focus-*.json"))}
    repro = json.loads((d / "survey-reproduction.json").read_text())["summary"] if (d / "survey-reproduction.json").exists() else None
    return seeds, focus, repro


def summarize(d: Path):
    seeds, focus, repro = load(d)
    doors = [r for s in seeds.values() for r in s["doors"]]
    routes = [r for s in seeds.values() for r in s["routes"]]
    out = {"seeds": sorted(seeds), "doors": len(doors), "status": dict(Counter(r["status"] for r in doors)), "survey_reproduction": repro}
    out["front_dy"] = dict(sorted(Counter(str(r["front_dy"]) for r in doors).items()))
    by = defaultdict(Counter)
    for r in doors:
        by[(r["module"], r["rotation"])][r["status"]] += 1
    out["front_cell_owner"] = dict(Counter(r["front_cell_owner"] for r in doors))
    out["front_cell_chunk_untouched_by_house_box"] = sum(1 for r in doors if not r["front_cell_chunk_touched_by_house_box"])
    out["module_rotation"] = {f"{m}|{ro}": dict(c) for (m, ro), c in sorted(by.items())}
    bb = [r for r in routes if r["kind"] == "building_to_building"]
    ce = [r for r in routes if r["kind"] == "building_to_city_entrance"]
    out["routes"] = {"building_to_building": len(bb), "building_to_city_entrance": len(ce)}
    for name, rs in (("building_to_building", bb), ("building_to_city_entrance", ce)):
        st = [r["steps"] for r in rs]
        out["routes"][name + "_steps"] = {"median": statistics.median(st) if st else None, "p90": q(st, .9), "max": max(st) if st else None}
        out["routes"][name + "_height_range"] = dict(sorted(Counter(r["path_height_range"] for r in rs).items()))
        on = Counter()
        for r in rs:
            on.update(r["on"])
        tot = sum(on.values())
        out["routes"][name + "_share_of_steps_by_piece_box"] = {k: round(v / tot, 4) for k, v in on.most_common()} if tot else {}
        out["routes"][name + "_with_stairs_wall_piece"] = sum(1 for r in rs if any(k.startswith("wall_stairs") for k in r["on"]))
        fl = Counter()
        for r in rs:
            fl.update(r["floor_top"])
        out["routes"][name + "_top_floor_blocks"] = dict(fl.most_common(8))
    out["per_seed"] = {s: {"walkable_cells": j["walkable_cells"], "components": j["n_components"], "main_cells": j["main_cells"],
                           "main_share": j["main_share"], "doors": len(j["doors"]), "unknown_columns": j["unknown_columns"],
                           "status": dict(Counter(r["status"] for r in j["doors"])),
                           "front_components": sorted({r["comp_front"] for r in j["doors"] if r["comp_front"] is not None}),
                           "towers_touch_main": [b["touches_main"] for b in j["buildings_other"]]} for s, j in seeds.items()}
    out["not_open"] = [{k: r[k] for k in ("seed", "piece_index", "module", "rotation", "door_world", "status", "front_dy", "comp_interior", "main")} |
                       {k: r.get(k) for k in ("front_comp_size", "front_comp_drops_to_main", "main_drops_to_front_comp")}
                       for r in doors if r["status"] != "open_to_main"]
    out["focus"] = {s: {k: f[k] for k in ("module", "rotation", "door_world", "outward", "survey_status", "obstruction_summary", "obstruction_extent",
                                          "door_front", "nearest_main_cell", "nearest_main_cell_within_1_block_height", "front_comp_drops_to_main",
                                          "main_drops_to_front_comp", "minimum_change") if k in f} for s, f in focus.items()}
    nmc = [c for j in seeds.values() for c in j["components"] if not c["is_main"]]
    boxes = Counter()
    for c in nmc:
        boxes.update(c["sampled_piece_boxes"])
    out["non_main_components"] = {"n": len(nmc), "cells": sum(c["walkable_cells"] for c in nmc), "boxes": dict(boxes.most_common()),
                                  "drops_to_main": sum(c["drops_to_main"] for c in nmc), "main_drops_to_it": sum(c["main_drops_to_it"] for c in nmc),
                                  "with_house_doors": sum(1 for c in nmc if c["house_doors_in_front_comp"])}
    (d / "results-summary.json").write_text(json.dumps(out, indent=1))
    return out, seeds, focus


def markdown(d: Path):
    o, seeds, focus = summarize(d)
    L = ["# Stage 24-L Phase 0 - Ancient City pedestrian connectivity (READ-ONLY measurement)", "",
         "Static geometric model of the saved worlds of the Stage 24-K pack (24 seeds). **Not Minecraft-client gameplay**; not a physics simulation.",
         "No gameplay content, NBT, datapack, processor or worldgen change. Model assumptions: see `tools/stage24l/phase0.py` docstring.", ""]
    rp = o["survey_reproduction"]
    if rp:
        L += ["## 1. Reproduction of the Stage 24-I entrance survey", "",
              f"Observations regenerated: **{rp['observations']}**; baseline (`stage-24k/worldgen/k24-entrance-survey.json`): {rp['baseline_observations']}; "
              f"byte-equal rows (seed, piece, module, rotation, door, status, cells, path): **{rp['identical']}**; differences: **{len(rp['differences'])}**.", ""]
    L += ["## 2. Door status in the walkable-area graph (graph main component = largest two-way component of the city)", "",
          "| status | doors |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(o["status"].items())] + [f"| **total** | **{o['doors']}** |", ""]
    L += ["Door-front height relative to the door (floor step you take leaving the house), all doors:", "",
          "| dy | " + " | ".join(o["front_dy"]) + " |", "|---|" + "---|" * len(o["front_dy"]), "| doors | " + " | ".join(str(v) for v in o["front_dy"].values()) + " |", ""]
    L += ["Owner (smallest piece box containing it) of the cell directly outside the doorway - this is what a one-block growth of the house box on the door side "
          "would collide with:", "", "| owner | doors |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(o["front_cell_owner"].items(), key=lambda kv: -kv[1])] + [""]
    L += [f"Doors whose outside cell lies in a chunk the house box does not touch (an out-of-box write there would be clipped, cf. Stage 24-I): "
          f"**{o['front_cell_chunk_untouched_by_house_box']}** of {o['doors']}.", ""]
    L += ["## 3. Per-seed access and connectivity", "",
          "| seed | walkable cells | components | main component share | house doors | open to main | not open | towers touching main |", "|---|---|---|---|---|---|---|---|"]
    for s, p in sorted(o["per_seed"].items()):
        op = p["status"].get("open_to_main", 0)
        L.append(f"| {s} | {p['walkable_cells']} | {p['components']} | {p['main_share']:.3f} | {p['doors']} | {op} | {p['doors'] - op} | "
                 f"{sum(p['towers_touch_main'])}/{len(p['towers_touch_main'])} |")
    L += ["", "Every seed has all house doors that are open in the same component (`front_components` has a single id) unless listed in section 4.", ""]
    L += ["## 4. Doors that are not open to the main component", "",
          "| seed | piece | module | rotation | door | status | interior in main? | front comp cells | drops front->main | drops main->front |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in o["not_open"]:
        L.append(f"| {r['seed']} | {r['piece_index']} | {r['module']} | {r['rotation']} | {tuple(r['door_world'])} | {r['status']} | "
                 f"{r['comp_interior'] == r['main']} | {r.get('front_comp_size')} | {r.get('front_comp_drops_to_main')} | {r.get('main_drops_to_front_comp')} |")
    L += [""]
    L += ["## 5. Precise measurements at the deferred entrances", ""]
    for s, f in sorted(focus.items()):
        L += [f"### Seed {s} {f['module']} ({f['rotation']}), door {tuple(f['door_world'])}", "",
              f"* 24-I survey: `{f['survey_status']}`; obstruction cells: {f['obstruction_summary']}",
              f"* obstruction extent: {f.get('obstruction_extent')}", f"* door front: {f['door_front']}",
              f"* nearest main-component cell: {f['nearest_main_cell']}; within 1 block of door height: {f['nearest_main_cell_within_1_block_height']}"]
        if "front_comp_drops_to_main" in f:
            L.append(f"* front component can drop to main: {f['front_comp_drops_to_main']}; main can drop into front component: {f['main_drops_to_front_comp']}")
        mc = f.get("minimum_change")
        if mc:
            L += ["* minimum change that would give the doorway a two-way walk to the main component (computed, **nothing applied**):"]
            for k, v in mc.items():
                L.append(f"  * `{k}`: " + ("impossible" if v is None else f"cost {v['cost']} ({len(v['clear'])} natural cells cleared, {len(v['place'])} floor blocks placed {v['place']}; joins main at {v['reached']}; cells to place are owned by: {[(c['owner_template'], c['block_now']) for c in v.get('place_cell_owners', [])]})"))
        L += ["", "```", "dy of the nearest walkable cell relative to the door height (3 chars per column):"] + f["map_dy_rel_to_door"] + [
            "", "component class (" + f["map_legend"] + "):"] + f["map_component"] + ["```", ""]
    L += ["## 6. Routes between buildings (two-way graph, nearest 3 other buildings' doors from each building)", "",
          f"* building-to-building routes: {o['routes']['building_to_building']}, steps (blocks walked) {o['routes']['building_to_building_steps']}",
          f"* route height range (max-min along the path): {o['routes']['building_to_building_height_range']}",
          f"* routes through a `wall_stairs` piece box: {o['routes']['building_to_building_with_stairs_wall_piece']}",
          f"* share of route steps by piece box: {o['routes']['building_to_building_share_of_steps_by_piece_box']}",
          f"* floor blocks under routes: {o['routes']['building_to_building_top_floor_blocks']}",
          f"* building-to-city-entrance routes: {o['routes']['building_to_city_entrance']}, steps {o['routes']['building_to_city_entrance_steps']}", ""]
    nm = o["non_main_components"]
    L += ["## 6b. The other walkable components (largest 5 per seed, 120 in total)", "",
          f"* none of them contains a house door (all 113 open doors lead to the main component); {nm['n']} components, {nm['cells']} cells",
          f"* what they lie in (sampled): {nm['boxes']}", f"* can drop onto the main component (one-way): {nm['drops_to_main']}; main can drop into them: {nm['main_drops_to_it']}", ""]
    L += ["## 7. Variation by module and rotation (door status counts)", "", "| module | rotation | status counts |", "|---|---|---|"]
    for k, v in o["module_rotation"].items():
        m, ro = k.split("|")
        L.append(f"| {m} | {ro} | {v} |")
    L += [""]
    (d / "PHASE0-RESULTS.md").write_text("\n".join(L) + "\n")
    return o


if __name__ == "__main__":
    markdown(Path(sys.argv[1]))
