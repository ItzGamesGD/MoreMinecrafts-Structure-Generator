#!/usr/bin/env python3
"""N7-A3 control for the existing-world sequence: vanilla (no module) continues the first-session world with the same new chunks,
then the FULL chunks that existed before are compared with the module run (E2b) on the same schedule.

Measured per session: block changes inside FULL chunks that existed before, the subset of those changes inside protected piece boxes,
and block-entity changes. A module that only cancels features must not add protected-box changes beyond what vanilla does.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from existing_world import session  # noqa: E402
from fullworld_diff import block_entities, chunk_coords, diff_chunk  # noqa: E402
from world import Chunk, read_chunk  # noqa: E402

STRUCT_CHUNK = (-19, 15)


def full_coords(regions: Path) -> list[tuple[int, int]]:
    out = []
    for cx, cz in chunk_coords(regions):
        nbt = read_chunk(regions, cx, cz)
        if (nbt.get("Status") or nbt.get("status")) in ("minecraft:full", "full"):
            out.append((cx, cz))
    return out


def protected_boxes(regions: Path) -> list[tuple[int, ...]]:
    nbt = read_chunk(regions, *STRUCT_CHUNK)
    start = ((nbt.get("structures") or {}).get("starts") or {}).get("moreminecrafts:forgotten_kingdom/central_cavern")
    return [tuple(c["BB"]) for c in start["Children"]] if start else []


def inside(box, x, y, z) -> bool:
    return box[0] <= x <= box[3] and box[1] <= y <= box[4] and box[2] <= z <= box[5]


def changes(before: Path, after: Path, coords, protected) -> dict:
    total = inside_protected = be = 0
    for cx, cz in coords:
        ca, cb = Chunk(read_chunk(before, cx, cz)), Chunk(read_chunk(after, cx, cz))
        for y, i, _, _ in diff_chunk(ca, cb):
            total += 1
            x, z = cx * 16 + (i & 15), cz * 16 + ((i >> 4) & 15)
            if any(inside(b, x, y, z) for b in protected):
                inside_protected += 1
        be += len(block_entities(ca) ^ block_entities(cb))
    return {"full_chunks": len(coords), "block_changes": total, "block_changes_in_protected": inside_protected, "block_entity_changes": be}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--existing", type=Path, required=True, help="output directory of existing_world.py")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    pack = Path(os.environ["SG_PACK"])
    e1 = a.existing / "E1_vanilla_fresh"
    w1_regions = e1 / "regions"
    fc = full_coords(w1_regions)
    prot = protected_boxes(w1_regions)
    new_all = [c for c in [(x, z) for x in range(-19, -8) for z in range(10, 21)] if not (-24 <= c[0] <= -14 and 10 <= c[1] <= 20)]
    half1, half2 = new_all[: len(new_all) // 2], new_all[len(new_all) // 2:]
    report = {"full_chunks_before": len(fc), "protected_boxes": len(prot)}
    session(a.out, "V2a_vanilla_partial", "vanilla", e1 / "world", {}, half1, pack, 40971)
    session(a.out, "V2b_vanilla_restart", "vanilla", a.out / "V2a_vanilla_partial" / "world", {}, half2, pack, 40972)
    report["vanilla_E2a"] = changes(w1_regions, a.out / "V2a_vanilla_partial" / "regions", fc, prot)
    report["vanilla_E2b"] = changes(w1_regions, a.out / "V2b_vanilla_restart" / "regions", fc, prot)
    report["module_E2a"] = changes(w1_regions, a.existing / "E2a_module_partial" / "regions", fc, prot)
    report["module_E2b"] = changes(w1_regions, a.existing / "E2b_module_restart" / "regions", fc, prot)
    (a.out / "existing_world_control.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
