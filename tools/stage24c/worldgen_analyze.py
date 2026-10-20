"""Analyse generated Ancient Cities: piece layout diff vs vanilla, BB overlap/adjacency, block replacement, terrain exposure."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa
from tools.stage24c.mcserver import World

TARGET = {f"minecraft:ancient_city/structures/{m}": m for m in MODULES}
ROT = {"NONE": 0, "CLOCKWISE_90": 90, "CLOCKWISE_180": 180, "COUNTERCLOCKWISE_90": 270}


def rot(pos, r):
    x, y, z = pos
    return {0: (x, y, z), 90: (-z, y, x), 180: (-x, y, -z), 270: (z, y, -x)}[r]


CW = ["north", "east", "south", "west"]


NON_TERRAIN = {"air", "cave_air", "void_air", "water", "unloaded", "sculk_vein", "glow_lichen", "vine", "sculk", "sculk_sensor", "sculk_shrieker", "sculk_catalyst"}


def rotate_state(state, deg):
    """Apply StructureTemplate rotation to block-state properties (clockwise steps of 90 degrees)."""
    steps = deg // 90
    if steps == 0 or "[" not in state:
        return state
    name, props = state.split("[", 1)
    kv = dict(p.split("=", 1) for p in props.rstrip("]").split(","))
    out = {}
    for k, v in kv.items():
        if k == "facing" and v in CW:
            v = CW[(CW.index(v) + steps) % 4]
        elif k in CW:                      # wall / fence / glass-pane / vine connections
            out[CW[(CW.index(k) + steps) % 4]] = v
            continue
        elif k == "axis" and v in ("x", "z") and steps % 2:
            v = "z" if v == "x" else "x"
        elif k == "rotation" and v.isdigit():
            v = str((int(v) + 4 * steps) % 16)
        out[k] = v
    return name + "[" + ",".join(f"{k}={v}" for k, v in sorted(out.items())) + "]"


def sort_props(state):
    if "[" not in state:
        return state
    name, props = state.split("[", 1)
    return name + "[" + ",".join(sorted(props.rstrip("]").split(","))) + "]"


def inter(a, b):
    """volume of BB intersection; bb = [x0,y0,z0,x1,y1,z1] inclusive"""
    d = [min(a[i + 3], b[i + 3]) - max(a[i], b[i]) + 1 for i in range(3)]
    return d[0] * d[1] * d[2] if all(v > 0 for v in d) else 0


def touching(a, b):
    """BBs share a face (gap 0 on exactly one axis, overlap on the others)"""
    gaps = [max(a[i], b[i]) - min(a[i + 3], b[i + 3]) - 1 for i in range(3)]
    return sorted(gaps)[-1] == 0 and all(g <= 0 for g in sorted(gaps)[:2]) and inter(a, b) == 0


def norm(s):
    return s.replace(",waterlogged=false", "").replace("waterlogged=false,", "").replace("[waterlogged=false]", "")


def classify(expected, got):
    if got is None:
        return "unloaded"
    e, g = sort_props(norm(expected)), sort_props(norm(got))
    if e == g:
        return "identical"
    en, gn = e.split("[")[0], g.split("[")[0]
    if en == gn:
        return "same_block_other_state"
    if gn == "minecraft:air":
        return "removed_to_air"
    if gn in ("minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker", "minecraft:sculk_sensor"):
        return "sculk_feature_overlay"
    if gn.startswith("minecraft:cracked_") and gn.replace("cracked_", "") == en:
        return "cracked_by_processor"
    return "replaced_by_other"


def analyse_seed(seed, src_root, variant="candidate", manifests=None):
    vm = json.loads((OUT / f"worldgen/manifest-{seed}-vanilla.json").read_text())
    cm = json.loads(((manifests or OUT / "worldgen") / f"manifest-{seed}-{variant}.json").read_text())
    if not vm.get("cities") or not cm.get("cities"):
        return None
    vp, cp = vm["cities"][0]["pieces"], cm["cities"][0]["pieces"]
    sig = lambda ps: [(p["template"], tuple(p["pos"]), p["rotation"]) for p in ps]
    layout_same = len(vp) == len(cp) and sig(vp) == sig(cp)
    first_diff = next((i for i, (a, b) in enumerate(zip(sig(vp), sig(cp))) if a != b), None)
    bb_diffs = [{"index": i, "template": a["template"].split("/")[-1], "vanilla_bb": a["bb"], "candidate_bb": b["bb"]}
                for i, (a, b) in enumerate(zip(vp, cp)) if a["bb"] != b["bb"]]
    wdir = OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld"
    world = World(wdir) if wdir.exists() else None
    res = {"seed": seed, "city_xz": cm["city_xz"], "pieces_vanilla": len(vp), "pieces_candidate": len(cp),
           "placements_identical_to_vanilla": layout_same, "first_placement_diff_index": first_diff,
           "bounding_box_differences": bb_diffs, "modules": []}
    # BB overlaps across the whole candidate city
    n = len(cp)
    for i, p in enumerate(cp):
        m = TARGET.get(p["template"])
        if not m:
            continue
        others_overlap, others_touch = [], []
        for j, q in enumerate(cp):
            if i == j or not q["template"]:
                continue  # empty pool elements carry a 1-block placeholder BB; they place nothing
            v = inter(p["bb"], q["bb"])
            if v:
                others_overlap.append({"template": q["template"].split("/")[-1], "bb": q["bb"], "volume": v})
            elif touching(p["bb"], q["bb"]):
                others_touch.append(q["template"].split("/")[-1])
        rec = {"module": m, "rotation": p["rotation"], "pos": p["pos"], "bb": p["bb"],
               "bb_size": [p["bb"][3] - p["bb"][0] + 1, p["bb"][4] - p["bb"][1] + 1, p["bb"][5] - p["bb"][2] + 1],
               "overlapping_pieces": others_overlap, "adjacent_piece_count": len(others_touch),
               "adjacent_templates": sorted(set(others_touch))}
        # vanilla counterpart BB (same index when layouts identical)
        if layout_same:
            rec["vanilla_bb"] = vp[i]["bb"]
        above = [q["bb"][1] - p["bb"][4] - 1 for q in cp if q is not p and q["bb"][1] > p["bb"][4]
                 and min(p["bb"][3], q["bb"][3]) >= max(p["bb"][0], q["bb"][0]) and min(p["bb"][5], q["bb"][5]) >= max(p["bb"][2], q["bb"][2])]
        rec["vertical_clearance_to_piece_above"] = min(above) if above else None
        if world:
            root = load_nbt(src_root / m / "restored.nbt")
            blocks = blocks_of(root)
            r = ROT[p["rotation"]]
            origin = p["pos"]
            size = [int(v) for v in root["size"]]
            pts = [rot((cx, 0, cz), r) for cx in (0, size[0] - 1) for cz in (0, size[2] - 1)]
            rec["model_bb_x"] = [origin[0] + min(q[0] for q in pts), origin[0] + max(q[0] for q in pts)]
            rec["model_bb_z"] = [origin[2] + min(q[2] for q in pts), origin[2] + max(q[2] for q in pts)]
            rec["model_matches_piece_bb"] = (rec["model_bb_x"] == [p["bb"][0], p["bb"][3]] and rec["model_bb_z"] == [p["bb"][2], p["bb"][5]])
            cls, samples = Counter(), []
            crit = {}
            crit_lost_cells = []
            template_cells = set()
            for pos, (st, _) in blocks.items():
                if st.startswith(("minecraft:jigsaw", "minecraft:structure_void")):
                    continue
                rx, ry, rz = rot(pos, r)
                w = (origin[0] + rx, origin[1] + ry, origin[2] + rz)
                template_cells.add(w)
                got = world.block(*w)
                c = classify(rotate_state(st, r), got)
                cls[c] += 1
                n_ = st.split("[")[0].replace("minecraft:", "")
                cat = ("ladder" if n_ == "ladder" else "stairs" if n_.endswith("_stairs") else "parapet_wall" if n_.endswith("_wall")
                       else "lantern" if n_ == "soul_lantern" else "bed" if n_.endswith("_bed") else "door" if n_.endswith("_door")
                       else "container" if n_ in ("chest", "barrel") else None)
                if cat:
                    t_ = crit.setdefault(cat, [0, 0])
                    t_[0] += 1
                    t_[1] += 1 if c in ("removed_to_air", "replaced_by_other") else 0
                    if c in ("removed_to_air", "replaced_by_other"):
                        crit_lost_cells.append({"category": cat, "block": n_, "world": list(w), "got": got})
                if c in ("replaced_by_other",) and len(samples) < 6:
                    samples.append({"rel": list(pos), "world": list(w), "expected": st, "got": got})
            rec["block_replacement"] = dict(cls)
            rec["critical_blocks_total_lost"] = crit
            rec["critical_lost_cells"] = crit_lost_cells
            rec["block_replacement_samples"] = samples
            # what fills the BB cells the template does not specify?
            fill = Counter()
            bb = p["bb"]
            for x in range(bb[0], bb[3] + 1):
                for y in range(bb[1], bb[4] + 1):
                    for z in range(bb[2], bb[5] + 1):
                        if (x, y, z) in template_cells:
                            continue
                        b = world.block(x, y, z)
                        fill[(b or "unloaded").split("[")[0].replace("minecraft:", "")] += 1
            rec["unspecified_cell_fill"] = dict(fill.most_common(8))
            terrain_cells = []
            for x in range(bb[0], bb[3] + 1):
                for y in range(bb[1], bb[4] + 1):
                    for z in range(bb[2], bb[5] + 1):
                        if (x, y, z) not in template_cells:
                            n = (world.block(x, y, z) or "unloaded").split("[")[0].replace("minecraft:", "")
                            if n not in NON_TERRAIN:
                                terrain_cells.append([x, y, z, n])
            rec["terrain_cells_in_bb"] = len(terrain_cells)
            rec["terrain_cells_in_bb_list"] = terrain_cells[:300]
            # jigsaw connectivity: the cell each template jigsaw points at must lie inside another generated piece
            jig = []
            for pos, (st, nb) in blocks.items():
                if not st.startswith("minecraft:jigsaw"):
                    continue
                ori = st.split("orientation=")[1].split("_")[0].rstrip("]")
                f = rotate_state(f"minecraft:x[facing={ori}]", r).split("facing=")[1].rstrip("]") if ori in CW else ori
                d = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}[f]
                rx, ry, rz = rot(pos, r)
                w = (origin[0] + rx, origin[1] + ry, origin[2] + rz)
                tgt = (w[0] + d[0], w[1] + d[1], w[2] + d[2])
                hosts = [(q["template"].split("/")[-1] or q["element_type"].replace("minecraft:", "")) for q in cp if q is not p
                         and q["bb"][0] <= tgt[0] <= q["bb"][3] and q["bb"][1] <= tgt[1] <= q["bb"][4] and q["bb"][2] <= tgt[2] <= q["bb"][5]]
                # template pieces, vanilla feature elements (sculk patches) and empty elements are all valid jigsaw resolutions
                jig.append({"jigsaw_world": list(w), "facing": f, "target": list(tgt), "connected_to": hosts, "connected": bool(hosts),
                            "pool": str(nb["pool"]) if nb is not None and "pool" in nb else None})
            rec["jigsaws"] = jig
            tot = sum(fill.values())
            rec["unspecified_cells"] = tot
            rec["unspecified_air_fraction"] = round(fill.get("air", 0) / tot, 3) if tot else None
            rec["unspecified_solid_fraction"] = round(sum(v for k, v in fill.items() if k not in ("air", "cave_air", "void_air", "water", "unloaded", "sculk_vein", "glow_lichen", "vine")) / tot, 3) if tot else None
            # terrain exposure: 1-block shell around the BB
            shell = Counter()
            for x in range(bb[0] - 1, bb[3] + 2):
                for z in range(bb[2] - 1, bb[5] + 2):
                    for y in (bb[1] - 1, bb[4] + 1):
                        shell[(world.block(x, y, z) or "unloaded").split("[")[0].replace("minecraft:", "")] += 1
            rec["shell_top_bottom"] = dict(shell.most_common(6))
            # cells added by a taller proposal (above the Stage 24-C height) that the template leaves empty: terrain intrusion check
            base_h = int(load_nbt(S24B / m / "restored.nbt")["size"][1])
            if size[1] > base_h:
                extra = Counter()
                for x in range(bb[0], bb[3] + 1):
                    for y in range(bb[1] + base_h, bb[4] + 1):
                        for z in range(bb[2], bb[5] + 1):
                            if (x, y, z) not in template_cells:
                                extra[(world.block(x, y, z) or "unloaded").split("[")[0].replace("minecraft:", "")] += 1
                rec["expansion_layers"] = {"from_y": bb[1] + base_h, "to_y": bb[4], "unspecified_fill": dict(extra.most_common(8)),
                                           "terrain_cells": [c for c in terrain_cells if c[1] >= bb[1] + base_h],
                                           "solid_terrain_cells": sum(v for k, v in extra.items() if k not in ("air", "cave_air", "void_air", "water", "unloaded", "sculk_vein", "glow_lichen", "vine"))}
            rec["bb_y_range"] = [bb[1], bb[4]]
        res["modules"].append(rec)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--out", default="worldgen-analysis.json")
    ap.add_argument("--variant", default="candidate")
    ap.add_argument("--manifests", default=None, help="directory holding the variant manifests (default stage-24c/worldgen)")
    ap.add_argument("--out-dir", default=None, help="directory for --out (default stage-24c/worldgen)")
    a = ap.parse_args()
    src = Path(a.src) if a.src else S24B
    out = []
    for s in a.seeds:
        r = analyse_seed(s, src, a.variant, Path(a.manifests) if a.manifests else None)
        if r:
            out.append(r)
            mods = Counter(m["module"] for m in r["modules"])
            print(s, "same" if r["placements_identical_to_vanilla"] else "DIFF@%s" % r["first_placement_diff_index"], dict(mods), flush=True)
    (Path(a.out_dir) if a.out_dir else OUT / "worldgen").joinpath(a.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
