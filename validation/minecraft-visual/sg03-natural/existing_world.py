#!/usr/bin/env python3
"""N7-A3 existing-world compatibility (Phase 3). One world is carried through a sequence of server sessions:

  E1  vanilla jar, fresh world, site (-19,15) generated in the damaging order (colmajor_rev); a player-style block is placed in a
      protected piece; the (already damaged) structure is recorded.
  E2a module (refined guard) starts on that world; new chunks adjacent to the structure are generated in part; server stops mid-generation.
  E2b module restarts on the saved world; the rest of the new chunks are generated; server stops.
  E3  module removed (vanilla jar) on the saved world; more new chunks; stop.
  E4  module reinstalled; more new chunks; stop.

Checks after every session: chunks that existed before the session are block- and block-entity-identical (no rewrites, no repair);
the player-style block is unchanged; the already-damaged structure keeps exactly its earlier mismatch count (no automatic repair);
new chunks are reported with the same lab measurements (expected-template mismatches, foreign blocks in template air, pieces, spawners).
Environment: SERVER_JAR, SG_PACK, JAVA_HOME (JDK 25). Writes into <out>.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "validation" / "minecraft-visual"))
import assembly_probe as ap  # noqa: E402
from collision_lab import chunk_order, summarize  # noqa: E402
from fullworld_diff import block_entities, diff_chunk  # noqa: E402
from run_natural import STRUCT, inspect, wait_loaded  # noqa: E402
from world import Chunk, Server, World, read_chunk  # noqa: E402

REPO = HERE.parents[2]
SPIKE = REPO / "validation" / "fabric-protection-spike"
SEED = 173
DAMAGE_ORDER = "colmajor_rev"


def chunks_of(region_dir: Path) -> set[tuple[int, int]]:
    from fullworld_diff import chunk_coords
    return set(chunk_coords(region_dir))


def session(out: Path, name: str, kind: str, world_src: Path | None, env: dict, areas: list[tuple[int, int]], pack: Path,
            port: int, after=None) -> dict:
    """Start the server (vanilla jar or module), load the given chunks in order, run `after(server)`, save and stop.
    Returns the saved region dir and log path."""
    run_dir = (out / name / "run").resolve()
    if kind == "module":
        run_dir = (SPIKE / "run" / "server").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    if world_src is not None:
        shutil.copytree(world_src, run_dir / "world")
    if kind == "module":
        srv = Server("java", None, run_dir, SEED, pack, port=port, launcher=["./gradlew", "--no-daemon", "runServer"], launcher_cwd=SPIKE,
                     start_timeout=600, env={**env})
    else:
        srv = Server("java", Path(os.environ["SERVER_JAR"]), run_dir, SEED, pack, port=port, xmx="3G")
    result: dict = {"session": name, "kind": kind}
    try:
        for cx, cz in areas:
            srv.cmd(f"forceload add {cx * 16} {cz * 16}")
            wait_loaded(srv, cx * 16, cz * 16)
        if after is not None:
            after(srv, result)
        srv.save()
    finally:
        srv.stop()
    dest = out / name
    shutil.copytree(srv.region_dir, dest / "regions", dirs_exist_ok=True)
    shutil.copy2(srv.log_path, dest / "server.log")
    if world_src is None or True:
        shutil.rmtree(dest / "world", ignore_errors=True)
    shutil.copytree(run_dir / "world", dest / "world")
    return result


def compare_existing(before_regions: Path, after_regions: Path, before_coords: set) -> dict:
    changed = 0
    checked = 0
    be_changed = 0
    for cx, cz in sorted(before_coords):
        ca, cb = Chunk(read_chunk(before_regions, cx, cz)), Chunk(read_chunk(after_regions, cx, cz))
        checked += 1
        changed += sum(1 for _ in diff_chunk(ca, cb))
        be_changed += len(block_entities(ca) ^ block_entities(cb))
    return {"existing_chunks_checked": checked, "existing_block_changes": changed, "existing_block_entity_changes": be_changed}


def gold_preserved(regions: Path, marked: dict) -> bool:
    if not marked:
        return False
    return World(regions).block_id(marked["x"], marked["y"], marked["z"]) == "minecraft:gold_block"


def structure_report(regions: Path, pack: Path) -> dict:
    templates, _ = ap.load_pack(pack)
    world = World(regions)
    start_chunk = Chunk(read_chunk(regions, -19, 15))
    start = ((start_chunk.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if start_chunk else None
    if not start:
        return {"start": "missing"}
    return summarize(inspect(world, start, templates), world, start, templates)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--pack", type=Path, default=Path(os.environ["SG_PACK"]))
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out
    report: dict = {"seed": SEED, "centre": [-19, 15], "damage_order": DAMAGE_ORDER, "sessions": []}
    # E1: vanilla fresh world, damaging order, then a player-style block inside protected piece 0
    area0 = [(x, z) for x in range(-24, -13) for z in range(10, 21)]
    marked = {}

    def e1_after(srv, res):
        base = read_chunk(srv.region_dir, -19, 15)
        start = ((Chunk(base).nbt.get("structures") or {}).get("starts") or {}).get(STRUCT)
        bb = start["Children"][0]["BB"]
        x, y, z = (bb[0] + bb[3]) // 2, (bb[1] + bb[4]) // 2, (bb[2] + bb[5]) // 2
        srv.cmd(f"setblock {x} {y} {z} minecraft:gold_block")
        marked.update(x=x, y=y, z=z)
        res["player_block"] = [x, y, z]

    ordered = chunk_order(DAMAGE_ORDER, -19, 15, 5)
    # E1 must load the chunks in the damaging order; afterwards the player block is written.
    r1 = session(out, "E1_vanilla_fresh", "vanilla", None, {}, ordered, a.pack, 40951, after=e1_after)
    report["sessions"].append(r1)
    w1 = out / "E1_vanilla_fresh" / "regions"
    coords1 = chunks_of(w1)
    report["E1"] = structure_report(w1, a.pack)
    # E2a: module, first half of the new chunks (server stops mid-generation)
    new_all = [c for c in [(x, z) for x in range(-19, -8) for z in range(10, 21)] if c not in set(area0)]
    half1, half2 = new_all[: len(new_all) // 2], new_all[len(new_all) // 2:]
    env = {"SG01_LAB": "1", "SG01_GUARD_MODE": "enforce", "SG01_FEATURES": "both", "SG01_REFINE": "precheck", "SG01_SPIKE_REPORT": str((out / "E2a_spike.json").resolve())}
    session(out, "E2a_module_partial", "module", out / "E1_vanilla_fresh" / "world", env, half1, a.pack, 40952)
    coords2a = chunks_of(out / "E2a_module_partial" / "regions")
    report["E2a_existing_vs_E1"] = compare_existing(w1, out / "E2a_module_partial" / "regions", coords1)
    # E2b: module restarts on the saved world, rest of the new chunks
    session(out, "E2b_module_restart", "module", out / "E2a_module_partial" / "world", env, half2, a.pack, 40953)
    w2b = out / "E2b_module_restart" / "regions"
    report["E2b_existing_vs_E1"] = compare_existing(w1, w2b, coords1)
    report["E2b_existing_vs_E2a"] = compare_existing(out / "E2a_module_partial" / "regions", w2b, coords2a)
    report["E2b"] = structure_report(w2b, a.pack)
    report["E2b_gold_preserved"] = gold_preserved(w2b, marked)
    # E3: module removed, vanilla jar, more new chunks
    more3 = [(x, z) for x in range(-8, -3) for z in range(10, 21)]
    session(out, "E3_module_removed", "vanilla", out / "E2b_module_restart" / "world", {}, more3, a.pack, 40954)
    w3 = out / "E3_module_removed" / "regions"
    coords2b = chunks_of(w2b)
    report["E3_existing_vs_E2b"] = compare_existing(w2b, w3, coords2b)
    # E4: module reinstalled, more new chunks
    more4 = [(x, z) for x in range(-3, 1) for z in range(10, 21)]
    coords3 = chunks_of(w3)
    session(out, "E4_module_reinstalled", "module", out / "E3_module_removed" / "world", env, more4, a.pack, 40955)
    w4 = out / "E4_module_reinstalled" / "regions"
    report["E4_existing_vs_E3"] = compare_existing(w3, w4, coords3)
    report["E4"] = structure_report(w4, a.pack)
    report["E4_gold_preserved"] = gold_preserved(w4, marked)
    report["marked_block"] = marked
    (out / "existing_world.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if "_vs_" in k or k.endswith("_gold_preserved")}, indent=1))


if __name__ == "__main__":
    main()
