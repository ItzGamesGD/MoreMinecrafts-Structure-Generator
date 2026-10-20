#!/usr/bin/env python3
"""N7-A4 statistical world comparison for runs whose generation is not reproducible.

Method (per unit = same seed, site, order and settings):
  * N vanilla replicates give all N*(N-1)/2 vanilla-vs-vanilla pairs. For each chunk the per-chunk block-difference counts of those pairs form the
    vanilla noise distribution of that chunk (its maximum is the 'noise ceiling').
  * The guarded run is compared with every vanilla replicate. A chunk is ABOVE NOISE when the guarded run's difference from EVERY vanilla replicate
    exceeds the chunk's noise ceiling.
  * Above-noise chunks are classified: CANCELLATION chunk (overlaps a reach box of a feature the guard cancelled, or a protected piece box),
    ADJACENT (within one chunk of such a chunk: plausible downstream effect), UNEXPECTED (anywhere else: plausibly attributable to the guard,
    needs inspection). Chunks at or below the noise ceiling are NOT shown to be unaffected; they are only not distinguishable from vanilla noise.
Only chunks that are status 'full' in every compared run are used.
usage: fullworld_stats.py OUT.json --guarded REGIONS --guarded-lab LAB --vanilla REGIONS [REGIONS ...]
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fullworld_diff import boxes_from_lab, cancelled_reaches, chunk_coords, diff_chunk, full_chunks  # noqa: E402
from world import Chunk, read_chunk  # noqa: E402


def per_chunk(a: Path, b: Path, coords) -> dict:
    out = {}
    for cx, cz in coords:
        out[(cx, cz)] = sum(1 for _ in diff_chunk(Chunk(read_chunk(a, cx, cz)), Chunk(read_chunk(b, cx, cz))))
    return out


def overlaps_chunk(box, cx, cz) -> bool:
    return box[0] <= cx * 16 + 15 and box[3] >= cx * 16 and box[2] <= cz * 16 + 15 and box[5] >= cz * 16


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--guarded", type=Path, required=True)
    ap.add_argument("--guarded-lab", type=Path, required=True)
    ap.add_argument("--vanilla", type=Path, nargs="+", required=True)
    a = ap.parse_args()
    lab = json.loads(a.guarded_lab.read_text())
    footprint = boxes_from_lab(lab) + cancelled_reaches(lab)
    coords = set(chunk_coords(a.guarded))
    coords &= full_chunks(a.guarded, coords)
    for v in a.vanilla:
        coords &= set(chunk_coords(v))
        coords &= full_chunks(v, coords)
    coords = sorted(coords)
    noise = [per_chunk(x, y, coords) for x, y in itertools.combinations(a.vanilla, 2)]
    ceiling = {c: max(n[c] for n in noise) for c in coords}
    guarded = [per_chunk(v, a.guarded, coords) for v in a.vanilla]
    above = [c for c in coords if all(g[c] > ceiling[c] for g in guarded)]
    cancel_chunks = {c for c in coords if any(overlaps_chunk(b, *c) for b in footprint)}
    adjacent = {c for c in coords if any(abs(c[0] - k[0]) <= 1 and abs(c[1] - k[1]) <= 1 for k in cancel_chunks)} - cancel_chunks
    cls = Counter()
    unexpected = []
    for c in above:
        if c in cancel_chunks:
            cls["cancellation_footprint"] += 1
        elif c in adjacent:
            cls["adjacent_to_footprint"] += 1
        else:
            cls["unexpected"] += 1
            unexpected.append({"chunk": list(c), "guarded_min_diff": min(g[c] for g in guarded), "noise_ceiling": ceiling[c]})
    report = {
        "chunks_compared": len(coords), "vanilla_replicates": len(a.vanilla), "vanilla_pairs": len(noise),
        "noise_ceiling_total_blocks": sum(ceiling.values()), "guarded_mean_diff_total_blocks": round(sum(sum(g.values()) for g in guarded) / len(guarded), 1),
        "chunks_with_footprint": len(cancel_chunks), "chunks_above_noise": len(above), "classification": dict(cls), "unexpected_chunks": unexpected[:40],
        "caveat": "chunks at or below the noise ceiling are not distinguishable from vanilla variation; this is not proof that they are unaffected",
    }
    a.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("chunks_compared", "vanilla_pairs", "chunks_with_footprint", "chunks_above_noise", "classification")}))


if __name__ == "__main__":
    main()
