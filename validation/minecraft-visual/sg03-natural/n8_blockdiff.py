#!/usr/bin/env python3
"""N8-B deterministic block comparison of two worlds produced by the soak loading pattern (one area at a time, settle between areas).
usage: n8_blockdiff.py OUT.json --ref REGION_DIR --other REGION_DIR --soak soak.json --first N [--radius 5]
For the first N sites it compares every block state of every chunk of the loaded area (radius chunks around the site) that is status full in both worlds.
Expected region E: chunks within 2 chunks (Chebyshev) of any chunk that contains a piece box of the structure. A guard decision can only cancel a feature
whose 3x3-chunk write zone contains a piece, and such a feature writes only inside that zone, so every guard-attributable difference lies in E.
Differences outside E are UNEXPECTED. When ref and other are two runs of the same configuration the whole comparison must be zero (determinism check)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fullworld_diff import diff_chunk  # noqa: E402
from run_natural import STRUCT  # noqa: E402
from world import Chunk, read_chunk  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--other", type=Path, required=True)
    ap.add_argument("--soak", type=Path, required=True)
    ap.add_argument("--first", type=int, default=24)
    ap.add_argument("--radius", type=int, default=5)
    a = ap.parse_args()
    sites = json.loads(a.soak.read_text())["sites"][: a.first]
    rows, tot = [], {"chunks_compared": 0, "chunks_skipped_not_full": 0, "diff_blocks": 0, "diff_blocks_in_E": 0, "diff_blocks_outside_E": 0, "chunks_differing_outside_E": 0,
                     "diff_blocks_inside_piece_boxes": 0, "sites_with_start_in_both": 0, "sites_without_start": 0}
    for cx, cz in sites:
        c0 = read_chunk(a.ref, cx, cz)
        start = ((c0.get("structures") or {}).get("starts") or {}).get(STRUCT) if c0 else None
        if not start:
            tot["sites_without_start"] += 1
            continue
        tot["sites_with_start_in_both"] += 1
        boxes = [c["BB"] for c in start["Children"]]
        pchunks = {(x, z) for b in boxes for x in range(b[0] >> 4, (b[3] >> 4) + 1) for z in range(b[2] >> 4, (b[5] >> 4) + 1)}
        row = {"site": [cx, cz], "diff_in_E": 0, "diff_outside_E": 0, "chunks_outside_E": []}
        for x in range(cx - a.radius, cx + a.radius + 1):
            for z in range(cz - a.radius, cz + a.radius + 1):
                na, nb = read_chunk(a.ref, x, z), read_chunk(a.other, x, z)
                full = lambda n: n and (n.get("Status") or n.get("status")) in ("minecraft:full", "full")  # noqa: E731
                if not (full(na) and full(nb)):
                    tot["chunks_skipped_not_full"] += 1
                    continue
                tot["chunks_compared"] += 1
                n_in_piece = 0
                n = 0
                for y, idx, ia, ib in diff_chunk(Chunk(na), Chunk(nb)):
                    n += 1
                    bx, bz, by = x * 16 + (idx & 15), z * 16 + ((idx >> 4) & 15), y
                    if any(b[0] <= bx <= b[3] and b[1] <= by <= b[4] and b[2] <= bz <= b[5] for b in boxes):
                        n_in_piece += 1
                in_e = any(max(abs(x - px), abs(z - pz)) <= 2 for px, pz in pchunks)
                tot["diff_blocks"] += n
                tot["diff_blocks_inside_piece_boxes"] += n_in_piece
                if in_e:
                    tot["diff_blocks_in_E"] += n
                    row["diff_in_E"] += n
                elif n:
                    tot["diff_blocks_outside_E"] += n
                    tot["chunks_differing_outside_E"] += 1
                    row["diff_outside_E"] += n
                    row["chunks_outside_E"].append([x, z, n])
        rows.append(row)
    a.out.write_text(json.dumps({"ref": str(a.ref), "other": str(a.other), "totals": tot, "sites": rows}, indent=1) + "\n")
    print(json.dumps(tot))


if __name__ == "__main__":
    main()
