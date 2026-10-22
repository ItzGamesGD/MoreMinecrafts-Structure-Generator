"""Stage 24-H vs Stage 24-I on the 24-seed sweep (identical layouts, position-seeded processors).

Per restored piece, every cell of the box plus a 1-block ring:
  roof cell   expected change: block_rot dropped it in 24-H and the roof overlay writes it back in 24-I
  other cell  must be identical; differences are classified as sculk, fluid, natural terrain or UNEXPLAINED
Also: roof continuity (every roof cell present in 24-I), mask cells (air/fluid/sculk) and sauna pool water in 24-I.
"""
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

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"


def main(seeds):
    masks = {m: {tuple(p): k for k, v in d["cleared"].items() for p in v} for m, d in json.loads((D24H / "mask/interior-masks.json").read_text()).items()}
    roofs = {m: {tuple(e["pos"]): e["state"] for e in v["roof_cells"]} for m, v in json.loads((D24I / "roof/roof-cells.json").read_text()).items()}
    arch = set()
    cache = {}
    for m in MODULES:
        nbt = load_nbt(D24F / m / "restored.nbt")
        cache[m] = ({q: s for q, (s, _) in blocks_of(nbt).items()}, [int(v) for v in nbt["size"]])
        arch.update(n(s) for s in cache[m][0].values())
    arch -= {"minecraft:deepslate", "minecraft:air", "minecraft:water", "minecraft:cave_air"} | SCULK
    out = []
    for seed in seeds:
        ph = json.loads((D24H / f"worldgen/manifest-{seed}-h24.json").read_text())["cities"][0]["pieces"]
        pi = json.loads((D24I / f"worldgen/manifest-{seed}-i24.json").read_text())["cities"][0]["pieces"]
        key = lambda p: (p["pos"], p["rotation"], p["bb"], p["template"])  # noqa: E731
        res = {"seed": seed, "layout_identical_h24_i24": [key(a) for a in ph] == [key(b) for b in pi], "pieces": []}
        wh = World(OUT / f"_work/wg-{seed}-h24/world/dimensions/minecraft/overworld")
        wi = World(OUT / f"_work/wg-{seed}-i24/world/dimensions/minecraft/overworld")
        for idx, p in enumerate(pi):
            m = TARGET.get(p["template"])
            if not m:
                continue
            blocks, size = cache[m]
            r, o = ROT[p["rotation"]], p["pos"]
            c, unexplained, roof_missing = Counter(), [], []
            for x in range(-1, size[0] + 1):
                for y in range(0, size[1] + 1):
                    for z in range(-1, size[2] + 1):
                        q = (x, y, z)
                        t = rot(q, r)
                        w = (o[0] + t[0], o[1] + t[1], o[2] + t[2])
                        a, b = wh.block(*w), wi.block(*w)
                        na, nb = n(a), n(b)
                        if q in roofs[m]:
                            ok = nb in (P.name(roofs[m][q]), P.name(roofs[m][q]).replace("minecraft:", "minecraft:cracked_"), "minecraft:sculk")
                            c["roof_present" if ok else "ROOF_MISSING"] += 1
                            if not ok:
                                roof_missing.append({"world": list(w), "template_pos": list(q), "got": b})
                            if a != b:
                                c["roof_restored_vs_h24" if P.rot_removed(roofs[m][q], w) else ("diff_sculk" if na in SCULK or nb in SCULK else "roof_other_diff")] += 1
                            continue
                        if q in masks[m]:
                            c["mask_" + ("air" if nb in AIR else "fluid_" + nb.split(":")[1] if nb in FLUIDS else
                                         "sculk" if nb in SCULK else "OTHER")] += 1
                        if q in blocks and blocks[q].startswith("minecraft:water"):
                            c["pool_water_kept" if wet(b) else "POOL_WATER_LOST"] += 1
                        if a == b:
                            c["same"] += 1
                        elif na in SCULK or nb in SCULK:
                            c["diff_sculk"] += 1
                        elif na in FLUIDS or nb in FLUIDS or na in FLUID_PRODUCTS or nb in FLUID_PRODUCTS:
                            c["diff_fluid"] += 1
                        elif na == nb:
                            c["diff_state_only"] += 1
                        elif na in arch or nb in arch:
                            c["diff_architecture_UNEXPLAINED"] += 1
                            unexplained.append({"world": list(w), "template_pos": list(q), "h24": a, "i24": b})
                        else:
                            c["diff_natural_terrain"] += 1
            res["pieces"].append({"piece_index": idx, "module": m, "rotation": p["rotation"], "bb": p["bb"], "counts": dict(c),
                                  "roof_missing": roof_missing, "unexplained": unexplained[:40]})
        out.append(res)
        tot = Counter()
        for pc in res["pieces"]:
            tot.update(pc["counts"])
        print(seed, "layout", res["layout_identical_h24_i24"], dict(tot), flush=True)
    (D24I / "worldgen/hi-comparison.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(range(24001, 24025)))
