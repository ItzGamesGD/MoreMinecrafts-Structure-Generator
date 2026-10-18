#!/usr/bin/env python3
"""Bounded, deterministic multi-seed natural-generation stress run for SG-01 against a vanilla Minecraft 26.3 server.

For each seed the nearest ``--sites`` random_spread candidates to the origin (within ``--ring`` regions) are
force-loaded so Minecraft itself decides whether a structure is generated. Nothing is placed with /place.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import STRUCT, analyze, load_templates  # noqa: E402
from spread import SG01, TRIAL_CHAMBERS, candidates_in_ring, exclusion_suppressed  # noqa: E402
from world import Server, World, export_chunks  # noqa: E402

TRIAL = "minecraft:trial_chambers"


def wait_loaded(srv: Server, x: int, z: int, timeout: float = 240) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if "Test passed" in srv.cmd(f"execute if loaded {x} 0 {z}"):
            return
        time.sleep(1)
    raise TimeoutError(f"chunk at {x},{z} never loaded")


def read_start(world: World, cx: int, cz: int, name: str):
    chunk = world.chunk(cx, cz)
    if chunk is None:
        return None, None
    starts = (chunk.nbt.get("structures") or {}).get("starts") or {}
    return starts.get(name), chunk.status


def union_bb(start: dict):
    boxes = [c["BB"] for c in start.get("Children", [])]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), min(b[2] for b in boxes),
            max(b[3] for b in boxes), max(b[4] for b in boxes), max(b[5] for b in boxes)]


def bb_gap(a: list[int], b: list[int]) -> int:
    """Axis-aligned gap in blocks between two inclusive boxes (negative when they intersect)."""
    gaps = [max(a[i] - b[i + 3], b[i] - a[i + 3]) for i in range(3)]
    return max(gaps)


def sprint(srv: Server, ticks: int) -> str:
    """Advance game time with /tick sprint and return the server's own completion line."""
    mark = srv.log_path.stat().st_size
    srv.cmd(f"tick sprint {ticks}")
    end = time.time() + 900
    while time.time() < end:
        time.sleep(2)
        for line in srv.log_path.read_text(errors="replace")[mark:].splitlines():
            if "Sprint completed" in line:
                return line.split("]: ", 1)[-1]
    raise TimeoutError("tick sprint did not finish")


def notable(site: dict) -> bool:
    """Sites worth keeping a saved-world excerpt for: any fluid/ cave mouth contact, interior fluid, or biome-decoration conversion."""
    after = site.get("after_ticks")
    if not after:
        return False
    states = {a["state"] for a in after["apertures"].values()}
    touch = after["boundary_contact"]["structure_blocks_touching"]
    return bool(after["integrity"]["mismatched"] or states - {"blocked_by_terrain"} or touch.get("water") or touch.get("lava")
                or after["interior"]["counts"].get("water") or after["interior"]["counts"].get("lava"))


def run_seed(args, seed: int, templates: dict) -> dict:
    run = args.out / "runs" / f"seed-{seed}"
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    srv = Server(args.java, args.jar, run, seed, args.pack, port=args.port)
    t0 = time.time()
    try:
        ordered = sorted(candidates_in_ring(seed, SG01, args.ring), key=lambda c: math.hypot(c[0] * 16, c[1] * 16))
        free = [c for c in ordered if not exclusion_suppressed(seed, c)]
        blocked = [c for c in ordered if exclusion_suppressed(seed, c)]
        cands = free[: args.sites] + blocked[: args.suppressed_sample]
        for spec in args.extra_site:
            extra_seed, ex, ez = (int(v) for v in spec.split(":"))
            if extra_seed == seed and (ex, ez) not in cands:
                cands.append((ex, ez))
        census = {"candidates_in_ring": len(ordered), "predicted_exclusion_suppressed": len(blocked), "predicted_free": len(free)}
        trials = candidates_in_ring(seed, TRIAL_CHAMBERS, args.ring + 1)
        sites = []
        for cx, cz in cands:
            near_trials = [t for t in trials if max(abs(t[0] - cx), abs(t[1] - cz)) <= 14]
            for tx, tz in near_trials:
                srv.cmd(f"forceload add {tx * 16} {tz * 16}")
            srv.cmd(f"forceload add {cx * 16 - 64} {cz * 16 - 64} {cx * 16 + 80} {cz * 16 + 80}")
            wait_loaded(srv, cx * 16, cz * 16)
            for tx, tz in near_trials:
                wait_loaded(srv, tx * 16, tz * 16)
            sites.append({"candidate_chunk": [cx, cz], "candidate_block": [cx * 16, cz * 16], "near_trial_candidates": near_trials})
        time.sleep(3)
        srv.save()
        world = World(srv.region_dir)
        for site in sites:
            cx, cz = site["candidate_chunk"]
            start, status = read_start(world, cx, cz, STRUCT)
            site["chunk_status"] = status
            trial_found = []
            for tx, tz in site["near_trial_candidates"]:
                tstart, _ = read_start(world, tx, tz, TRIAL)
                trial_found.append({"candidate_chunk": [tx, tz], "chebyshev_chunks": max(abs(tx - cx), abs(tz - cz)),
                                    "start_present": tstart is not None,
                                    "bb": union_bb(tstart) if tstart else None})
            site["trial_chambers"] = trial_found
            if start is None:
                # Vanilla's exclusion zone is positional: a trial_chambers *candidate* chunk within range suppresses
                # SG-01 even when no trial chamber actually generates there.
                within = [t for t in trial_found if t["chebyshev_chunks"] <= 12]
                site["outcome"] = "suppressed_by_exclusion_zone" if within else "no_structure_unexplained"
                continue
            site["outcome"] = "generated"
            site["exclusion_prediction_consistent"] = not any(t["chebyshev_chunks"] <= 12 for t in trial_found)
            site["start_bb"] = union_bb(start)
            site["post_generation"] = analyze(world, start, templates, snapshot="post_generation")
            for t in trial_found:
                if t["start_present"]:
                    t["bb_gap_to_sg01"] = bb_gap(site["start_bb"], t["bb"])
        # fluid spread: advance game time with every site force-loaded, then re-read the saved world
        ticks_done = 0
        sprint_line = None
        if args.ticks and any(s["outcome"] == "generated" for s in sites):
            sprint_line = sprint(srv, args.ticks)
            ticks_done = args.ticks
            srv.save()
            world2 = World(srv.region_dir)
            for site in sites:
                if site["outcome"] != "generated":
                    continue
                start, _ = read_start(world2, *site["candidate_chunk"], STRUCT)
                site["after_ticks"] = analyze(world2, start, templates, snapshot=f"after_{args.ticks}_ticks")
        if args.keep_notable:
            for site in sites:
                if site["outcome"] != "generated" or not notable(site):
                    continue
                cx, cz = site["candidate_chunk"]
                lo, hi = site["start_bb"][0] >> 4, site["start_bb"][3] >> 4
                loz, hiz = site["start_bb"][2] >> 4, site["start_bb"][5] >> 4
                chunks = [(x, z) for x in range(lo - 2, hi + 3) for z in range(loz - 2, hiz + 3)]
                dest = args.out / "worlds" / f"seed-{seed}_chunk-{cx}_{cz}" / "region"
                site["saved_world_excerpt"] = {"path": str(dest.relative_to(args.out)), "chunks": export_chunks(srv.region_dir, chunks, dest)}
        return {"seed": seed, "candidate_census": census, "ticks_advanced": ticks_done, "sprint_log": sprint_line, "elapsed_s": round(time.time() - t0, 1), "sites": sites}
    finally:
        srv.stop()
        shutil.copy2(srv.log_path, args.out / f"server-seed-{seed}.log")
        shutil.rmtree(run, ignore_errors=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--java", default="java")
    p.add_argument("--jar", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--sites", type=int, default=6)
    p.add_argument("--ring", type=int, default=3)
    p.add_argument("--suppressed-sample", type=int, default=1, help="nearest predicted-suppressed candidates to also load, to check the prediction")
    p.add_argument("--ticks", type=int, default=2400)
    p.add_argument("--port", type=int, default=25675)
    p.add_argument("--extra-site", action="append", default=[], metavar="SEED:CHUNK_X:CHUNK_Z", help="also load this candidate chunk (repeatable)")
    p.add_argument("--keep-notable", action="store_true", help="keep a chunk-level saved-world excerpt for sites with fluid/cave/biome interactions")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    templates = load_templates(args.pack / "data/moreminecrafts/structure/forgotten_kingdom/central_cavern")
    for seed in args.seeds:
        result = run_seed(args, seed, templates)
        (args.out / f"seed-{seed}.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"seed {seed}: {[(s['candidate_block'], s['outcome']) for s in result['sites']]} in {result['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    main()
