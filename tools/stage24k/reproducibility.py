"""Generation noise floor: the same pack generated twice (same seeds) differs in vanilla decoration (sculk, glow lichen,
dripstone, ore blobs, fluid timing). Counts, over every restored piece's box plus a 1-block ring, how the two runs of ONE
pack differ, in the categories of tools/stage24k/compare.py, plus the sauna pool-water cells and deck cells blocked by
vanilla sculk. Used to judge whether the Stage 24-I -> 24-K differences exceed what an unchanged pack already shows."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402
from tools.stage24h.sweep_compare import SCULK, FLUIDS, FLUID_PRODUCTS, wet, n  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"


def world(seed, v):
    return World(OUT / f"_work/wg-{seed}-{v}/world/dimensions/minecraft/overworld")


def pair(seeds, va, vb, man_a, tmpl_dir, label):
    tm = {m: {p: s for p, (s, _) in blocks_of(load_nbt(tmpl_dir / m / "restored.nbt")).items()} for m in MODULES}
    size = {m: [int(s) for s in load_nbt(tmpl_dir / m / "restored.nbt")["size"]] for m in MODULES}
    arch = {n(s) for m in MODULES for s in tm[m].values()} - {"minecraft:deepslate", "minecraft:air", "minecraft:water", "minecraft:cave_air"} - SCULK
    res = {"label": label, "variants": [va, vb], "seeds": seeds, "by_module": {}, "sauna_pool_cells": 0, "sauna_pool_not_wet": {va: 0, vb: 0}}
    for seed in seeds:
        pcs = json.loads((man_a / f"manifest-{seed}-{va}.json").read_text())["cities"][0]["pieces"]
        wa, wb = world(seed, va), world(seed, vb)
        for p in pcs:
            m = TARGET.get(p["template"])
            if not m:
                continue
            r, o = ROT[p["rotation"]], p["pos"]
            sx, sy, sz = size[m]
            c = res["by_module"].setdefault(m, Counter())
            for x in range(-1, sx + 1):
                for y in range(0, sy + 1):
                    for z in range(-1, sz + 1):
                        t = rot((x, y, z), r)
                        w = (o[0] + t[0], o[1] + t[1], o[2] + t[2])
                        a, b = wa.block(*w), wb.block(*w)
                        if m == "sauna_1" and tm[m].get((x, y, z), "").startswith("minecraft:water"):
                            res["sauna_pool_cells"] += 1
                            res["sauna_pool_not_wet"][va] += 0 if wet(a) else 1
                            res["sauna_pool_not_wet"][vb] += 0 if wet(b) else 1
                        if a == b:
                            continue
                        na, nb = n(a), n(b)
                        if "minecraft:glow_lichen" in (na, nb):
                            c["glow_lichen"] += 1
                        elif na in SCULK or nb in SCULK:
                            c["sculk"] += 1
                        elif na in FLUIDS or nb in FLUIDS or na in FLUID_PRODUCTS or nb in FLUID_PRODUCTS:
                            c["fluid"] += 1
                        elif na == nb:
                            c["state_only"] += 1
                        elif na in arch or nb in arch:
                            c["ARCHITECTURE"] += 1
                        else:
                            c["natural_terrain"] += 1
    res["by_module"] = {m: dict(c) for m, c in res["by_module"].items()}
    return res


def main(seeds):
    out = [pair(seeds, "k24", "k24rep", K / "worldgen", K / "final-candidates", "Stage 24-K pack, two generations"),
           pair(seeds, "i24", "i24rep", AR / "stage-24i/worldgen", AR / "stage-24f/final-candidates", "Stage 24-I pack, two generations")]
    # the first runs of the seeds are the committed sweep manifests; the repeat runs live in worldgen-rep
    (K / "worldgen/reproducibility.json").write_text(json.dumps(out, indent=1) + "\n")
    for r in out:
        tot = Counter()
        for c in r["by_module"].values():
            tot.update(c)
        print(r["label"], dict(tot), "sauna pool", r["sauna_pool_cells"], "not wet", r["sauna_pool_not_wet"])


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [24006, 24007, 24012, 24017, 24018])
