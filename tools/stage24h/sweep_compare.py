"""Stage 24-F / 24-G / 24-H comparison on the 24-seed sweep (identical layouts, position-seeded processors).

For every restored piece and every cell of its box plus a 1-block ring:
  * mask cells: what fills them in 24-G (terrain = obstruction) and in 24-H (air / fluid / sculk / other)
  * every other cell: 24-G vs 24-H block identity; differences classified as sculk-patch, fluid, or UNEXPLAINED
  * stored decorative cells: same state in 24-G and 24-H (decay identity outside the mask)
  * stored water (sauna pools): still water in 24-H
  * fluid inside the mask in 24-H: connected fluid component, its sources, and the entry cell it came in through
"""
from __future__ import annotations

import json
import sys
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.roles import Template  # noqa: E402
from tools.stage24g.terrain import inv_rot  # noqa: E402
from tools.stage24h.mask import build_mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
MAN = {"f24": ROOT / "artifacts/ancient-city-restoration/stage-24f/worldgen",
       "g24": ROOT / "artifacts/ancient-city-restoration/stage-24g/worldgen",
       "h24": ROOT / "artifacts/ancient-city-restoration/stage-24h/worldgen"}
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
SCULK = {"minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker", "minecraft:sculk_sensor"}
FLUIDS = {"minecraft:lava", "minecraft:water"}
FLUID_PRODUCTS = {"minecraft:obsidian", "minecraft:cobblestone", "minecraft:stone", "minecraft:basalt", "minecraft:fire"}
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
ROCK = {"minecraft:deepslate", "minecraft:stone", "minecraft:tuff", "minecraft:granite", "minecraft:diorite", "minecraft:andesite",
        "minecraft:calcite", "minecraft:smooth_basalt", "minecraft:dripstone_block", "minecraft:cobbled_deepslate"}
D6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def world(variant, seed):
    return World(OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld")


def pieces(variant, seed):
    return json.loads((MAN[variant] / f"manifest-{seed}-{variant}.json").read_text())["cities"][0]["pieces"]


def n(b):
    return P.name(b or "minecraft:air")


def fluid_trace(w, start_cells, mask_world):
    """Connected fluid component from the mask cells holding fluid; sources and entry points."""
    comp, q = set(start_cells), deque(start_cells)
    while q and len(comp) < 20000:
        c = q.popleft()
        for d in D6:
            nb = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if nb not in comp and n(w.block(*nb)) in FLUIDS:
                comp.add(nb)
                q.append(nb)
    sources = []
    for c in comp:
        b = w.block(*c) or ""
        if "level=0" in b:
            rock = sum(1 for d in D6 if n(w.block(c[0] + d[0], c[1] + d[1], c[2] + d[2])) in ROCK)
            sources.append({"world": list(c), "block": b, "rock_neighbours": rock,
                            "kind": "spring-like source (rock on 4+ sides)" if rock >= 4 else "open source / pool"})
    entries = [c for c in comp if c in mask_world and any((c[0] + d[0], c[1] + d[1], c[2] + d[2]) in comp and
                                                          (c[0] + d[0], c[1] + d[1], c[2] + d[2]) not in mask_world for d in D6)]
    return comp, sources, entries


def compare_seed(seed, masks, stored_cache, full):
    pf, pg, ph = pieces("f24", seed), pieces("g24", seed), pieces("h24", seed)
    key = lambda p: (p["pos"], p["rotation"], p["bb"])  # noqa: E731
    layout_same = [key(a) for a in pf] == [key(a) for a in pg] == [key(a) for a in ph]
    wf, wg, wh = world("f24", seed), world("g24", seed), world("h24", seed)
    res = {"seed": seed, "layout_identical_fgh": layout_same, "pieces": []}
    for idx, p in enumerate(ph):
        m = TARGET.get(p["template"])
        if not m:
            continue
        blocks, size = stored_cache[m]
        mcls = masks[m]
        r, o = ROT[p["rotation"]], p["pos"]
        W = lambda q: (o[0] + rot(q, r)[0], o[1] + rot(q, r)[1], o[2] + rot(q, r)[2])  # noqa: E731
        mask_world = {W(q): c for q, c in mcls.items()}
        c = Counter()
        unexplained, fluid_cells = [], []
        terrain_g, terrain_f = Counter(), Counter()
        for x in range(-1, size[0] + 1):
            for y in range(0, size[1] + 1):
                for z in range(-1, size[2] + 1):
                    q = (x, y, z)
                    w_ = W(q)
                    bg, bh = wg.block(*w_), wh.block(*w_)
                    ng, nh = n(bg), n(bh)
                    if w_ in mask_world:
                        if ng not in AIR and ng not in SCULK:
                            terrain_g[ng] += 1
                        nf = n(wf.block(*w_))
                        if nf not in AIR and nf not in SCULK:
                            terrain_f[nf] += 1
                        if nh in AIR:
                            c["mask_air"] += 1
                        elif nh in FLUIDS:
                            c["mask_fluid_" + nh.split(":")[1]] += 1
                            fluid_cells.append(w_)
                        elif nh in SCULK:
                            c["mask_sculk_" + nh.split(":")[1]] += 1
                        elif nh in FLUID_PRODUCTS:
                            c["mask_fluid_product_" + nh.split(":")[1]] += 1
                        else:
                            c["mask_OTHER"] += 1
                            unexplained.append({"where": "mask", "world": list(w_), "template_pos": list(q), "h24": bh, "g24": bg})
                        continue
                    stored = q in blocks
                    if bg == bh:
                        c["same_" + ("stored" if stored else "other")] += 1
                        if stored and blocks[q].startswith("minecraft:water"):
                            c["pool_water_kept"] += 1
                        continue
                    if ng in SCULK or nh in SCULK:
                        c["diff_sculk"] += 1
                    elif ng in FLUIDS or nh in FLUIDS or ng in FLUID_PRODUCTS or nh in FLUID_PRODUCTS:
                        c["diff_fluid"] += 1
                    elif ng == nh:
                        c["diff_state_only"] += 1  # e.g. sculk-vein faces, stair/wall connections next to a cleared cell
                    else:
                        c["diff_UNEXPLAINED"] += 1
                        unexplained.append({"where": "stored" if stored else "outside_mask", "world": list(w_), "template_pos": list(q), "h24": bh, "g24": bg})
                    if stored and blocks[q].startswith("minecraft:water") and nh != "minecraft:water":
                        c["POOL_WATER_LOST"] += 1
        rec = {"piece_index": idx, "module": m, "rotation": p["rotation"], "pos": o, "bb": p["bb"], "counts": dict(c),
               "mask_terrain_f24": dict(terrain_f), "mask_terrain_g24": dict(terrain_g), "unexplained": unexplained[:50]}
        if fluid_cells:
            comp, sources, entries = fluid_trace(wh, fluid_cells, mask_world)
            ent = []
            for e in entries[:20]:
                outs = []
                for d in D6:
                    nb = (e[0] + d[0], e[1] + d[1], e[2] + d[2])
                    if nb in comp and nb not in mask_world:
                        tq = inv_rot((nb[0] - o[0], nb[1] - o[1], nb[2] - o[2]), r)
                        cls = full[m].get(tq, "outside_box")
                        if cls == "stored_architecture":
                            cls = "decay_hole (stored " + n(blocks[tq]).split(":")[1] + " dropped by block_rot)" if P.rot_removed(blocks[tq], nb) \
                                else "stored " + n(blocks[tq]).split(":")[1]
                        outs.append({"world": list(nb), "template_pos": list(tq), "via": cls})
                ent.append({"mask_cell": list(e), "class": mask_world[e], "fluid_from": outs})
            rec["fluid"] = {"cells_in_mask": len(fluid_cells), "component_size": len(comp), "sources": sources[:10], "entries": ent}
        res["pieces"].append(rec)
    return res


def main(seeds):
    masks_json = json.loads((D24H / "mask/interior-masks.json").read_text())
    masks = {m: {tuple(p): k for k, v in d["cleared"].items() for p in v} for m, d in masks_json.items()}
    cache, full = {}, {}
    for m in MODULES:
        full[m] = build_mask(Template(D24F / m / "restored.nbt"))
        nbt = load_nbt(D24F / m / "restored.nbt")
        cache[m] = ({q: s for q, (s, _) in blocks_of(nbt).items()}, [int(v) for v in nbt["size"]])
    out = []
    for s in seeds:
        r = compare_seed(s, masks, cache, full)
        out.append(r)
        tot = Counter()
        for pc in r["pieces"]:
            tot.update(pc["counts"])
        print(s, "layout", r["layout_identical_fgh"], dict(tot), flush=True)
    (D24H / "worldgen/fgh-comparison.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(range(24001, 24025)))
