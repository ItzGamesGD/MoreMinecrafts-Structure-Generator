"""Run-to-run reproducibility of 26.1.2 world generation around restored pieces.

The same seed and the same datapack were generated twice (g24 vs g24rep, h24 vs h24rep). Differences between two
runs of the SAME variant are generation noise (cross-chunk feature order); only differences beyond that noise can be
attributed to the interior clearance. Counted per region: the piece box, and shells 1-3 / 4-7 / 8-12 blocks outside.
Sculk-family blocks are counted separately (their spread varies run to run as well).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import TARGET  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
SC = {"sculk", "sculk_vein", "sculk_sensor", "sculk_shrieker", "sculk_catalyst"}
R = 12


def name(b):
    return (b or "minecraft:air").split("[")[0].split(":")[1]


def region_of(bb, x, y, z):
    d = max(bb[0] - x, x - bb[3], bb[2] - z, z - bb[5], bb[1] - y, y - bb[4], 0)
    return "box" if d == 0 else ("shell_1-3" if d <= 3 else "shell_4-7" if d <= 7 else "shell_8-12")


def diff(wa, wb, bb):
    c = Counter()
    for x in range(bb[0] - R, bb[3] + R + 1):
        for y in range(bb[1] - 4, bb[4] + R + 1):
            for z in range(bb[2] - R, bb[5] + R + 1):
                a, b = name(wa.block(x, y, z)), name(wb.block(x, y, z))
                if a == b:
                    continue
                c[region_of(bb, x, y, z) + (":sculk" if a in SC or b in SC else ":other")] += 1
    return dict(sorted(c.items()))


def main(seeds=(24005, 24008, 24009)):
    out = []
    for s in seeds:
        man = json.loads((D24H / f"worldgen/manifest-{s}-h24.json").read_text())["cities"][0]["pieces"]
        W = {v: World(OUT / f"_work/wg-{s}-{v}/world/dimensions/minecraft/overworld") for v in ("g24", "g24rep", "h24", "h24rep")}
        for i, p in enumerate(man):
            m = TARGET.get(p["template"])
            if m not in ("medium_ruin_1", "small_ruin_1", "large_ruin_1"):
                continue
            rec = {"seed": s, "piece_index": i, "module": m, "bb": p["bb"],
                   "g24_vs_g24rep (noise)": diff(W["g24"], W["g24rep"], p["bb"]),
                   "h24_vs_h24rep (noise)": diff(W["h24"], W["h24rep"], p["bb"]),
                   "g24_vs_h24 (variant)": diff(W["g24"], W["h24"], p["bb"])}
            out.append(rec)
            print(json.dumps(rec), flush=True)
    (D24H / "worldgen/reproducibility.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
