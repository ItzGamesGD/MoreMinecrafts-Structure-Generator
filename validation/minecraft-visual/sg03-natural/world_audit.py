#!/usr/bin/env python3
"""N8-B world audit of the region files a soak left behind. usage: world_audit.py OUT.json --region REGION_DIR --soak soak.json --pack PACK [--limit N]
Per site of the soak (same order in every arm):
  protected region: inspect() of the structure start against the exported templates (mismatches, foreign blocks in template air, piece count,
                    trial spawner blocks vs entities, errors)   [B1, deterministic]
  neighbourhood   : counts of vanilla feature blocks (geode shell/crystals, spawners, mossy cobblestone) in a ring of 2 chunks around the structure's
                    piece boxes, EXCLUDING every cell inside a piece box   [B2, statistical]
Only chunks with status full are used; the number of such chunks is recorded so arms are comparable."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_natural import STRUCT, inspect  # noqa: E402
import assembly_probe as ap  # noqa: E402
from world import World  # noqa: E402

FEATURE_BLOCKS = ("minecraft:smooth_basalt", "minecraft:calcite", "minecraft:amethyst_block", "minecraft:budding_amethyst", "minecraft:mossy_cobblestone")
SPAWNER_IDS = ("minecraft:spawner", "minecraft:mob_spawner")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--region", type=Path, required=True)
    p.add_argument("--soak", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    templates, _ = ap.load_pack(a.pack)
    world = World(a.region)
    sites = json.loads(a.soak.read_text())["sites"]
    if a.limit:
        sites = sites[: a.limit]
    rows, totals = [], Counter()
    for cx, cz in sites:
        chunk = world.chunk(cx, cz)
        start = ((chunk.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if chunk else None
        row = {"site": [cx, cz], "generated": bool(start)}
        if not start:
            rows.append(row)
            world.cache.clear()
            totals["sites_without_start"] += 1
            continue
        res = inspect(world, start, templates)
        boxes = [c["BB"] for c in start["Children"]]
        row.update({"pieces": res["piece_count"], "matched": res["matched"], "expected": res["expected"], "mismatch": res["expected"] - res["matched"],
                    "trial_spawner_blocks": res["trial_spawners"], "trial_spawner_entities": res["trial_spawner_entities"], "errors": res["errors"],
                    "interior_intrusions": res["interior_intrusions"] if isinstance(res["interior_intrusions"], int) else len(res["interior_intrusions"])})
        lo = [min(b[i] for b in boxes) for i in range(3)]
        hi = [max(b[i + 3] for b in boxes) for i in range(3)]
        cx0, cx1, cz0, cz1 = (lo[0] >> 4) - 2, (hi[0] >> 4) + 2, (lo[2] >> 4) - 2, (hi[2] >> 4) + 2
        ring, full, inside_pieces = Counter(), 0, 0
        for x in range(cx0, cx1 + 1):
            for z in range(cz0, cz1 + 1):
                ch = world.chunk(x, z)
                if ch is None or str(ch.status) != "minecraft:full":
                    continue
                full += 1
                for sec_y, (palette, idx) in ch.sections.items():
                    for name in FEATURE_BLOCKS:
                        ids = [i for i, st in enumerate(palette) if st["id"] == name]
                        if not ids:
                            continue
                        for flat in np.flatnonzero(np.isin(idx, ids)):
                            bx, by, bz = x * 16 + (flat & 15), sec_y * 16 + (flat >> 8), z * 16 + ((flat >> 4) & 15)
                            if any(b[0] <= bx <= b[3] and b[1] <= by <= b[4] and b[2] <= bz <= b[5] for b in boxes):
                                inside_pieces += 1
                            else:
                                ring[name.split(":")[1]] += 1
                for be in ch.nbt.get("block_entities", []):
                    if be.get("id") in SPAWNER_IDS:
                        bx, by, bz = be["x"], be["y"], be["z"]
                        if not any(b[0] <= bx <= b[3] and b[1] <= by <= b[4] and b[2] <= bz <= b[5] for b in boxes):
                            ring["spawner"] += 1
        row.update({"ring_full_chunks": full, "ring": dict(ring), "feature_blocks_inside_pieces": inside_pieces})
        rows.append(row)
        world.cache.clear()  # N8: the cache holds every parsed chunk; for 270 sites it exceeded 13 GB and the process was OOM-killed
        totals["sites"] += 1
        totals["mismatch"] += row["mismatch"]
        totals["sites_with_mismatch"] += row["mismatch"] > 0
        totals["bad_piece_count"] += row["pieces"] != 21
        totals["trial_spawner_mismatch"] += row["trial_spawner_blocks"] != row["trial_spawner_entities"]
        totals["errors"] += len(row["errors"])
        totals["ring_full_chunks"] += full
        for k, v in ring.items():
            totals["ring_" + k] += v
    a.out.write_text(json.dumps({"region": str(a.region), "totals": dict(totals), "sites": rows}, indent=1) + "\n")
    print(json.dumps(dict(totals)))


if __name__ == "__main__":
    main()
