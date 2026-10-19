#!/usr/bin/env python3
"""SG-03-N5 lab: generate ONE natural SG-03 site under a chosen chunk-load order and report every overwritten structure block.

Differences to run_natural.py: a single named candidate chunk; the area around it is loaded chunk by chunk in a selectable order;
optional single-threaded background executor (deterministic scheduling); every mismatching position is reported with its chunk.
Nothing is placed with /place.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_natural import STRUCT, inspect, wait_loaded  # noqa: E402  (also puts assembly_probe on sys.path)
import assembly_probe as ap  # noqa: E402
from world import Server, World  # noqa: E402


def chunk_order(mode: str, cx: int, cz: int, radius: int) -> list[tuple[int, int]]:
    cells = [(x, z) for x in range(cx - radius, cx + radius + 1) for z in range(cz - radius, cz + radius + 1)]
    if mode == "rowmajor":
        return sorted(cells)
    if mode == "rowmajor_rev":
        return sorted(cells, reverse=True)
    if mode == "colmajor":
        return sorted(cells, key=lambda c: (c[1], c[0]))
    if mode == "colmajor_rev":
        return sorted(cells, key=lambda c: (c[1], c[0]), reverse=True)
    if mode == "spiral_out":
        return sorted(cells, key=lambda c: (max(abs(c[0] - cx), abs(c[1] - cz)), c))
    if mode == "spiral_in":
        return sorted(cells, key=lambda c: (-max(abs(c[0] - cx), abs(c[1] - cz)), c))
    if mode.startswith("random"):
        rng = random.Random(int(mode.split(":")[1]))
        rng.shuffle(cells)
        return cells
    raise ValueError(mode)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jar", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--chunk", type=int, nargs=2, required=True)
    p.add_argument("--order", default="region", help="region | rowmajor | rowmajor_rev | colmajor | colmajor_rev | spiral_out | spiral_in | random:N")
    p.add_argument("--radius", type=int, default=7)
    p.add_argument("--threads", type=int, default=0, help="-Dmax.bg.threads (0 = default)")
    p.add_argument("--ticks", type=int, default=200)
    p.add_argument("--port", type=int, default=25575)
    p.add_argument("--java", default="java")
    p.add_argument("--launcher-prefix", nargs="*", default=[], help="e.g. taskset -c 0,1 to emulate a 2-vCPU runner")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    templates, _ = ap.load_pack(a.pack)
    folder = a.out / "world"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    extra = [f"-Dmax.bg.threads={a.threads}"] if a.threads else []
    launcher = None
    if a.launcher_prefix:
        launcher = [*a.launcher_prefix, a.java, "-Xmx3G", *extra, "-jar", str(a.jar.resolve()), "nogui"]
    server = Server(a.java, a.jar.resolve(), folder, a.seed, a.pack.resolve(), port=a.port, extra_args=extra, launcher=launcher,
                    extra_props={"difficulty": "normal", "spawn-monsters": "true", "max-tick-time": "-1"})
    cx, cz = a.chunk
    report = {"seed": a.seed, "chunk": [cx, cz], "order": a.order, "threads": a.threads, "prefix": a.launcher_prefix}
    try:
        t0 = time.time()
        if a.order == "region":
            server.cmd(f"forceload add {cx*16-a.radius*16} {cz*16-a.radius*16} {cx*16+a.radius*16} {cz*16+a.radius*16}")
            wait_loaded(server, cx * 16, cz * 16)
        else:
            for x, z in chunk_order(a.order, cx, cz, a.radius):
                server.cmd(f"forceload add {x*16} {z*16}")
                wait_loaded(server, x * 16, z * 16)
        server.save()
        world = World(server.region_dir)
        chunk = world.chunk(cx, cz)
        start = ((chunk.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if chunk else None
        report["generated"] = bool(start)
        if not start:
            return
        report["start_signature"] = [[c["pool_element"]["location"], c["rotation"], list(c["BB"])] for c in start["Children"]]
        boxes = [c["BB"] for c in start["Children"]]
        lo = [min(b[i] for b in boxes) for i in range(3)]
        hi = [max(b[i + 3] for b in boxes) for i in range(3)]
        report["bbox"] = lo + hi
        server.cmd(f"forceload add {lo[0]-16} {lo[2]-16} {hi[0]+16} {hi[2]+16}")
        wait_loaded(server, lo[0] - 16, lo[2] - 16)
        wait_loaded(server, hi[0] + 16, hi[2] + 16)
        server.save()
        world = World(server.region_dir)
        report["before_ticks"] = summarize(inspect(world, start, templates), world, start, templates)
        if a.ticks:
            mark = server.log_path.stat().st_size
            server.cmd(f"tick sprint {a.ticks}")
            end = time.time() + 240
            while time.time() < end and "Sprint completed" not in server.log_path.read_text(errors="replace")[mark:]:
                time.sleep(2)
            server.save()
            world = World(server.region_dir)
            report["after_ticks"] = summarize(inspect(world, start, templates), world, start, templates)
        report["elapsed_s"] = round(time.time() - t0, 1)
    finally:
        server.stop()
        shutil.copy2(server.log_path, a.out / "server.log")
        (a.out / "lab.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
        print(json.dumps({k: report.get(k) for k in ("order", "threads", "generated")} | {
            "after": {k: report.get("after_ticks", {}).get(k) for k in ("matched", "expected", "by_feature")}}))
        shutil.rmtree(folder, ignore_errors=True)


def summarize(result: dict, world: World, start: dict, templates: dict) -> dict:
    """Condense inspect(): per-position mismatches grouped by chunk and by suspected vanilla feature."""
    from run_natural import overlay_kind
    out = {"pass": result["pass"], "matched": result["matched"], "expected": result["expected"], "pieces": result["piece_count"],
           "trial_spawners": [result["trial_spawners"], result["trial_spawner_entities"]], "errors": result["errors"]}
    feature_of = {"clay": "lush_caves_clay", "water": "lush_caves_clay", "big_dripleaf": "lush_caves_clay", "big_dripleaf_stem": "lush_caves_clay",
                  "calcite": "amethyst_geode", "smooth_basalt": "amethyst_geode", "amethyst_block": "amethyst_geode", "budding_amethyst": "amethyst_geode",
                  "cobblestone": "monster_room", "mossy_cobblestone": "monster_room", "spawner": "monster_room", "chest": "monster_room",
                  "cave_air": "monster_room_or_geode_air", "air": "monster_room_or_geode_air"}
    by_feature = Counter()
    by_chunk = defaultdict(Counter)
    for t in result["state_transitions"]:
        by_feature[feature_of.get(t["actual"].split(":")[1], "other:" + t["actual"])] += t["count"]
    out["by_feature"] = dict(by_feature)
    out["interior_intrusions"] = result["interior_intrusions"]
    out["transitions"] = result["state_transitions"]
    for x, y, z, owner, exp, act in result["mismatches"]:
        by_chunk[f"{x >> 4},{z >> 4}"][feature_of.get(act.split(":")[1], "other:" + act)] += 1
    out["by_chunk"] = {k: dict(v) for k, v in sorted(by_chunk.items())}
    out["by_room"] = dict(Counter(m[3] for m in result["mismatches"]))
    out["mismatches"] = result["mismatches"]
    return out


if __name__ == "__main__":
    main()
