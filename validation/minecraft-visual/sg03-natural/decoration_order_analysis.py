#!/usr/bin/env python3
"""N7-A4 Phase 5: do world differences between two runs of the same configuration follow the decoration order of neighbouring chunks?
usage: decoration_order_analysis.py OUT.json RUN_A RUN_B [REACH=2]   (each run dir holds lab.json with spike_report.decoration_order, and regions/)
For two runs it finds the pairs of adjacent chunks (Chebyshev distance up to REACH, default 2) whose relative decoration order differs between the runs ('swapped pairs'),
counts block differences per chunk (chunks that are status full in both), and compares the share of chunks with differences among chunks that belong
to a swapped pair with the share among chunks that do not. A cross-chunk write whose order changed is the mechanism under test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fullworld_diff import chunk_coords, diff_chunk, full_chunks  # noqa: E402
from world import Chunk, read_chunk  # noqa: E402


def order_of(run: Path) -> dict:
    seq = json.loads((run / "lab.json").read_text())["spike_report"]["decoration_order"]
    return {tuple(int(v) for v in c.split(",")): i for i, c in enumerate(seq)}


def main() -> None:
    out, ra, rb = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    oa, ob = order_of(ra), order_of(rb)
    common = sorted(set(oa) & set(ob))
    swapped_chunks = set()
    swapped_pairs = 0
    pairs = 0
    reach = int(sys.argv[4]) if len(sys.argv) > 4 else 2  # 2: two chunks that share a neighbour can both write into it, so their order matters too
    for c in common:
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                d = (c[0] + dx, c[1] + dz)
                if d <= c or d not in oa or d not in ob:
                    continue
                pairs += 1
                if (oa[c] < oa[d]) != (ob[c] < ob[d]):
                    swapped_pairs += 1
                    swapped_chunks.update((c, d))
    ca, cb = ra / "regions", rb / "regions"
    coords = sorted(set(chunk_coords(ca)) & set(chunk_coords(cb)))
    coords = sorted(full_chunks(ca, coords) & full_chunks(cb, coords))
    diffs = {c: sum(1 for _ in diff_chunk(Chunk(read_chunk(ca, *c)), Chunk(read_chunk(cb, *c)))) for c in coords}
    in_sw = [c for c in coords if c in swapped_chunks]
    not_sw = [c for c in coords if c not in swapped_chunks]
    share = lambda cs: (sum(1 for c in cs if diffs[c] > 0) / len(cs)) if cs else None  # noqa: E731
    rep = {
        "chunks_decorated_in_both": len(common), "adjacent_pairs": pairs, "swapped_pairs": swapped_pairs,
        "full_chunks_compared": len(coords), "chunks_in_a_swapped_pair": len(in_sw), "chunks_not_in_a_swapped_pair": len(not_sw),
        "share_with_differences_in_swapped": share(in_sw), "share_with_differences_not_swapped": share(not_sw),
        "blocks_differing_in_swapped": sum(diffs[c] for c in in_sw), "blocks_differing_not_swapped": sum(diffs[c] for c in not_sw),
        "total_blocks_differing": sum(diffs.values()),
        "identical_decoration_order": oa == ob,
    }
    out.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
