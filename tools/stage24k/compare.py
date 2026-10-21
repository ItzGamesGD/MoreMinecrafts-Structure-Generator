"""Stage 24-I vs Stage 24-K on the 24-seed sweep (same seeds; position-seeded processors).

Per restored piece, every cell of the box plus a 1-block ring:
  design cells   (two towers only) cells where the Stage 24-K template differs from the Stage 24-I template: the world must
                 hold what the processors predict for the new block (rot / cracking model) or a documented later feature
  every other cell  must equal the Stage 24-I world; differences are classified as sculk spread, fluid, state-only, natural
                 terrain, or ARCHITECTURE_UNEXPLAINED
Plus, per generated tower: deck cells (feet and head) clear, ladder column intact, railing cells present, and the layout
(positions, rotations, boxes) of every piece identical to Stage 24-I; sauna pool water."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24h.sweep_compare import SCULK, FLUIDS, FLUID_PRODUCTS, AIR, wet, n  # noqa: E402
from tools.stage24j import designs as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
D24F, D24I, K = AR / "stage-24f/final-candidates", AR / "stage-24i", AR / "stage-24k"
TOWERS = {"large_pillar_1": D.large_a, "medium_pillar_1": D.medium_a}
OPEN = AIR | {"minecraft:sculk_vein", "minecraft:glow_lichen"}


def wld(seed, v):
    return World(OUT / f"_work/wg-{seed}-{v}/world/dimensions/minecraft/overworld")


def expected(state, w):
    """block id the processors write for a template block at world pos w (None = dropped by block_rot)"""
    if P.rot_removed(state, w):
        return None
    out = P.rule_output(state, w)
    return P.name(out if out else state)


def main(seeds):
    tmpl_old = {m: {p: s for p, (s, _) in blocks_of(load_nbt(D24F / m / "restored.nbt")).items()} for m in MODULES}
    tmpl_new = {m: {p: s for p, (s, _) in blocks_of(load_nbt(K / "final-candidates" / m / "restored.nbt")).items()} for m in MODULES}
    size = {m: [int(s) for s in load_nbt(K / "final-candidates" / m / "restored.nbt")["size"]] for m in MODULES}
    arch = {n(s) for m in MODULES for s in tmpl_old[m].values()} | {n(s) for m in TOWERS for s in tmpl_new[m].values()}
    arch -= {"minecraft:deepslate", "minecraft:air", "minecraft:water", "minecraft:cave_air"} | SCULK
    design = {m: {p for p in set(tmpl_old[m]) | set(tmpl_new[m]) if tmpl_old[m].get(p) != tmpl_new[m].get(p)} for m in MODULES}
    meta = {m: f().meta for m, f in TOWERS.items()}
    out = []
    for seed in seeds:
        pi = json.loads((D24I / f"worldgen/manifest-{seed}-i24.json").read_text())["cities"][0]["pieces"]
        pk = json.loads((K / f"worldgen/manifest-{seed}-k24.json").read_text())["cities"][0]["pieces"]
        key = lambda p: (p["pos"], p["rotation"], p["bb"], p["template"])  # noqa: E731
        res = {"seed": seed, "layout_identical_i24_k24": [key(a) for a in pi] == [key(b) for b in pk], "pieces_i24": len(pi), "pieces_k24": len(pk), "pieces": []}
        wi, wk = wld(seed, "i24"), wld(seed, "k24")
        for idx, p in enumerate(pk):
            m = TARGET.get(p["template"])
            if not m:
                continue
            sx, sy, sz = size[m]
            r, o = ROT[p["rotation"]], p["pos"]
            c, unexplained, design_other = Counter(), [], []
            for x in range(-1, sx + 1):
                for y in range(0, sy + 1):
                    for z in range(-1, sz + 1):
                        q = (x, y, z)
                        t = rot(q, r)
                        w = (o[0] + t[0], o[1] + t[1], o[2] + t[2])
                        a, b = wi.block(*w), wk.block(*w)
                        if q in design[m]:
                            st = tmpl_new[m].get(q)
                            if st is None or st.startswith("minecraft:jigsaw"):
                                c["design_cell_removed_from_template"] += 1
                                continue
                            want = expected(st, w)
                            nb = n(b)
                            if want is None and nb in OPEN | SCULK | FLUIDS:
                                c["design_cell_rot_dropped_as_predicted"] += 1
                            elif want is not None and nb == want:
                                c["design_cell_as_predicted"] += 1
                            elif nb in SCULK or nb in FLUIDS or nb in FLUID_PRODUCTS:
                                c["design_cell_sculk_or_fluid"] += 1
                            else:
                                c["DESIGN_CELL_UNEXPLAINED"] += 1
                                design_other.append({"world": list(w), "template_pos": list(q), "want": want, "k24": b, "i24": a})
                            continue
                        if a == b:
                            c["same"] += 1
                            continue
                        na, nb = n(a), n(b)
                        if na in SCULK or nb in SCULK:
                            c["diff_sculk"] += 1
                        elif na in FLUIDS or nb in FLUIDS or na in FLUID_PRODUCTS or nb in FLUID_PRODUCTS:
                            c["diff_fluid"] += 1
                        elif na == nb:
                            c["diff_state_only"] += 1
                        elif na in arch or nb in arch:
                            c["diff_architecture_UNEXPLAINED"] += 1
                            unexplained.append({"world": list(w), "template_pos": list(q), "i24": a, "k24": b})
                        else:
                            c["diff_natural_terrain"] += 1
                        if m == "sauna_1" and tmpl_new[m].get(q, "").startswith("minecraft:water"):
                            c["POOL_WATER_LOST"] += 0 if wet(b) else 1
            piece = {"piece_index": idx, "module": m, "rotation": p["rotation"], "bb": p["bb"], "counts": dict(c),
                     "unexplained": unexplained[:30], "design_unexplained": design_other[:30]}
            if m == "sauna_1":
                lost = sum(1 for q, s in tmpl_new[m].items() if s.startswith("minecraft:water") and not wet(wk.block(*[o[i] + rot(q, r)[i] for i in range(3)])))
                piece["pool_water_cells"] = sum(1 for s in tmpl_new[m].values() if s.startswith("minecraft:water"))
                piece["pool_water_lost"] = lost
            if m in TOWERS:
                mt = meta[m]
                wp = lambda q: tuple(o[i] + rot(q, r)[i] for i in range(3))  # noqa: E731
                deck_bad = [[x, z, y] for x, z in mt["deck"] for y in (mt["deck_y"], mt["deck_y"] + 1)
                            if n(wk.block(*wp((x, y, z)))) not in OPEN]
                ladder_bad = [y for y in range(1, mt["ladder_top"] + 1) if n(wk.block(*wp((mt["ladder"][0], y, mt["ladder"][1])))) != "minecraft:ladder"]
                rail_cells = [q for q, s in tmpl_new[m].items() if q[1] >= mt["deck_y"] - 1 and P.name(s).endswith("_wall")]
                rail_bad = [list(q) for q in rail_cells if not n(wk.block(*wp(q))).endswith("_wall")]
                piece["tower"] = {"deck_cells": len(mt["deck"]), "deck_cells_not_clear": deck_bad, "ladder_cells_missing": ladder_bad,
                                  "railing_cells": len(rail_cells), "railing_cells_missing": rail_bad}
            res["pieces"].append(piece)
        out.append(res)
        tot = Counter()
        for pc in res["pieces"]:
            tot.update(pc["counts"])
        tw = [pc["tower"] for pc in res["pieces"] if "tower" in pc]
        print(seed, "layout", res["layout_identical_i24_k24"], {k: v for k, v in tot.items() if k not in ("same",)},
              "towers", len(tw), "deck_bad", sum(len(t["deck_cells_not_clear"]) for t in tw), "ladder_bad", sum(len(t["ladder_cells_missing"]) for t in tw),
              "rail_bad", sum(len(t["railing_cells_missing"]) for t in tw), flush=True)
    (K / "worldgen/ik-comparison.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(range(24001, 24025)))
