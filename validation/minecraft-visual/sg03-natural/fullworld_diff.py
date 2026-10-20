#!/usr/bin/env python3
"""N7-A3 full-world comparison of two saved generation areas (identical seed, site and chunk schedule).

Compares every block state and block entity of every chunk present in both region sets, then classifies each difference:
  protected      : inside a protected piece box (vanilla damage the guard prevents; checked against the template by the lab)
  cancelled      : outside protected boxes, inside a reach box of a feature the guard cancelled in the GUARDED run (intended)
  downstream     : outside those, within DOWNSTREAM margin of a cancelled reach (candidate for changed random/neighbour data)
  nondeterministic: positions that also differ between two vanilla runs of the same unit (baseline generation noise; optional --noise-a/--noise-b)
  unexplained    : everything else (must be zero or explained)
Block entities are compared as (x, y, z, id) sets and classified the same way.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from world import Chunk, read_chunk  # noqa: E402

DOWNSTREAM = 16
BOX_RE = re.compile(r"BoundingBox\{minX=(-?\d+), minY=(-?\d+), minZ=(-?\d+), maxX=(-?\d+), maxY=(-?\d+), maxZ=(-?\d+)\}")
INTERN: dict[str, int] = {}
INTER_INV: dict[int, str] = {}


def canon(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True)


def intern(key: str) -> int:
    if key not in INTERN:
        INTERN[key] = len(INTERN)
        INTER_INV[INTERN[key]] = key
    return INTERN[key]


def full_chunks(region_dir: Path, coords) -> set[tuple[int, int]]:
    """Chunks whose saved status is 'full' (generation finished); the others are intermediate stages that differ between runs by construction."""
    out = set()
    for cx, cz in coords:
        nbt = read_chunk(region_dir, cx, cz)
        if nbt and (nbt.get("Status") or nbt.get("status")) in ("minecraft:full", "full"):
            out.add((cx, cz))
    return out


def chunk_coords(region_dir: Path) -> list[tuple[int, int]]:
    out = []
    for f in sorted(region_dir.glob("r.*.*.mca")):
        _, rx, rz, _ = f.name.split(".")
        rx, rz = int(rx), int(rz)
        with f.open("rb") as fh:
            table = fh.read(4096)
        for i in range(1024):
            off = int.from_bytes(table[i * 4:i * 4 + 3], "big")
            if off:
                out.append((rx * 32 + (i % 32), rz * 32 + (i // 32)))
    return out


def block_ids(chunk: Chunk) -> dict[int, np.ndarray]:
    """Absolute section index -> interned state id per block, in index order ((y&15)<<8 | z<<4 | x)."""
    out = {}
    for sec, (palette, idx) in chunk.sections.items():
        lut = np.array([intern(canon(p)) for p in palette], dtype=np.int32)
        out[sec] = lut[idx]
    return out


def diff_chunk(a: Chunk, b: Chunk):
    """Yield (absolute y, local index, id_a, id_b) for every differing block in one chunk."""
    da, db = block_ids(a), block_ids(b)
    air = intern(canon({"id": "minecraft:air"}))
    for sec in sorted(set(da) | set(db)):
        xa = da.get(sec, np.full(4096, air, dtype=np.int32))
        xb = db.get(sec, np.full(4096, air, dtype=np.int32))
        for i in np.nonzero(xa != xb)[0].tolist():
            yield sec * 16 + ((i >> 8) & 15), i, int(xa[i]), int(xb[i])


def block_entities(chunk: Chunk) -> set[tuple]:
    return {(int(e["x"]), int(e["y"]), int(e["z"]), str(e.get("id"))) for e in chunk.nbt.get("block_entities", [])}


def boxes_from_lab(lab: dict) -> list[tuple[int, ...]]:
    return [tuple(c) for c in [sig[2] for sig in (lab.get("start_signature") or [])]]


def cancelled_reaches(lab: dict) -> list[tuple[int, ...]]:
    """Reach boxes of every cancelled feature in a guarded run (parsed from the spike's event log)."""
    out = []
    sr = lab.get("spike_report") or {}
    for key in ("geode", "monster_room"):
        for ev in (sr.get(key) or {}).get("events", []):
            if "CANCELLED" not in ev or "reaches=" not in ev:
                continue
            seg = ev.split("reaches=", 1)[1].split(" -> ", 1)[0]
            out.extend(tuple(int(v) for v in m) for m in BOX_RE.findall(seg))
    return out


def inside(box, x, y, z) -> bool:
    return box[0] <= x <= box[3] and box[1] <= y <= box[4] and box[2] <= z <= box[5]


def near(box, x, z, margin) -> bool:
    return box[0] - margin <= x <= box[3] + margin and box[2] - margin <= z <= box[5] + margin


def classify(x, y, z, protected, cancel) -> str:
    if any(inside(b, x, y, z) for b in protected):
        return "protected"
    if any(inside(b, x, y, z) for b in cancel):
        return "cancelled"
    if any(near(b, x, z, DOWNSTREAM) for b in cancel):
        return "downstream"
    return "unexplained"


def block_differences(base: Path, other: Path, coords):
    for cx, cz in coords:
        ca, cb = Chunk(read_chunk(base, cx, cz)), Chunk(read_chunk(other, cx, cz))
        for y, i, ia, ib in diff_chunk(ca, cb):
            yield cx * 16 + (i & 15), y, cz * 16 + ((i >> 4) & 15), ia, ib


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=Path, required=True, help="region dir of the reference run (e.g. vanilla)")
    p.add_argument("--other", type=Path, required=True, help="region dir of the compared run")
    p.add_argument("--other-lab", type=Path, required=True, help="lab.json of the compared run (protected boxes, cancellation events)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--require-full", action="store_true", help="compare only chunks that are status 'full' in every compared run")
    p.add_argument("--noise-pair", nargs=2, type=Path, action="append", default=[], metavar=("A", "B"),
                   help="two vanilla region dirs of the same unit; repeat the option to take the union of their differences")
    a = p.parse_args()
    lab = json.loads(a.other_lab.read_text())
    protected = boxes_from_lab(lab)
    cancel = cancelled_reaches(lab)
    coords = sorted(set(chunk_coords(a.base)) & set(chunk_coords(a.other)))
    if a.require_full:
        coords = sorted(full_chunks(a.base, coords) & full_chunks(a.other, coords))
        for na, nb in a.noise_pair:
            coords = sorted(set(coords) & full_chunks(na, coords) & full_chunks(nb, coords))
    noise = set()
    for na, nb in a.noise_pair:
        noise_coords = sorted(set(chunk_coords(na)) & set(chunk_coords(nb)) & set(coords))
        noise |= {(x, y, z) for x, y, z, _, _ in block_differences(na, nb, noise_coords)}
    totals = Counter()
    block_pairs = Counter()
    noise_hits = 0
    unexplained = []
    be_totals = Counter()
    per_chunk = {}
    for cx, cz in coords:
        ca, cb = Chunk(read_chunk(a.base, cx, cz)), Chunk(read_chunk(a.other, cx, cz))
        n_chunk = Counter()
        for y, i, ia, ib in diff_chunk(ca, cb):
            x = cx * 16 + (i & 15)
            z = cz * 16 + ((i >> 4) & 15)
            if (x, y, z) in noise:
                cat = "nondeterministic"
                noise_hits += 1
            else:
                cat = classify(x, y, z, protected, cancel)
            totals[cat] += 1
            n_chunk[cat] += 1
            block_pairs[(cat, INTER_INV[ia], INTER_INV[ib])] += 1
            if cat == "unexplained" and len(unexplained) < 200:
                unexplained.append([x, y, z, INTER_INV[ia], INTER_INV[ib]])
        ea, eb = block_entities(ca), block_entities(cb)
        for e in ea ^ eb:
            cat = classify(e[0], e[1], e[2], protected, cancel)
            be_totals[cat] += 1
        if n_chunk:
            per_chunk[f"{cx},{cz}"] = dict(n_chunk)
    report = {
        "base": str(a.base), "other": str(a.other), "chunks_compared": len(coords),
        "block_differences": dict(totals), "block_entity_differences": dict(be_totals),
        "top_block_pairs": [[cat, a_, b_, n] for (cat, a_, b_), n in block_pairs.most_common(40)],
        "unexplained_samples": unexplained, "per_chunk": per_chunk,
        "protected_boxes": len(protected), "cancelled_reach_boxes": len(cancel), "downstream_margin": DOWNSTREAM,
        "noise_positions_from_vanilla_pair": len(noise), "differences_at_noise_positions": noise_hits,
    }
    a.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("chunks_compared", "block_differences", "block_entity_differences")}))


if __name__ == "__main__":
    main()
