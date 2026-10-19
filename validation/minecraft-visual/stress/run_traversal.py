#!/usr/bin/env python3
"""Runtime traversal probe over naturally generated SG-01 sites using the Fabric fixture's TraversalProbe (real mob locomotion)."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import STRUCT, load_templates  # noqa: E402
from run_stress import read_start, union_bb, wait_loaded  # noqa: E402
from spread import SG01, candidates_in_ring, exclusion_suppressed  # noqa: E402
from traversal import legs_for_site  # noqa: E402
from world import Server, World  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="*", default=[])
    p.add_argument("--site", action="append", default=[], metavar="SEED:CHUNK_X:CHUNK_Z", help="pin a specific candidate chunk (repeatable)")
    p.add_argument("--sites", type=int, default=2)
    p.add_argument("--ring", type=int, default=5)
    p.add_argument("--port", type=int, default=25875)
    p.add_argument("--allow-jump", action="store_true", help="let the mob jump (default: walk-only, jumping disabled)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    templates = load_templates(args.pack / "data/moreminecrafts/structure/forgotten_kingdom/central_cavern")
    run_dir = args.fixture / "run" / "server"
    request = args.out / "traverse-request.txt"
    result = args.out / "traverse-result.jsonl"
    summary = []
    pins: dict[int, list[tuple[int, int]]] = {}
    for spec in args.site:
        seed_s, cx_s, cz_s = spec.split(":")
        pins.setdefault(int(seed_s), []).append((int(cx_s), int(cz_s)))
    for seed in sorted({*args.seeds, *pins}):
        shutil.rmtree(run_dir, ignore_errors=True)
        run_dir.mkdir(parents=True)
        result.unlink(missing_ok=True)
        srv = Server("", Path(), run_dir, seed, args.pack, port=args.port,
                     launcher=["./gradlew", "--no-daemon", "runServer"], launcher_cwd=args.fixture,
                     env={"SG01_TRAVERSE_REQUEST": str(request), "SG01_TRAVERSE_RESULT": str(result), "SG01_TRAVERSE_ALLOW_JUMP": "1" if args.allow_jump else "0"}, start_timeout=600,
                     extra_props={"difficulty": "easy", "spawn-monsters": "false"})
        try:
            free = [c for c in sorted(candidates_in_ring(seed, SG01, args.ring), key=lambda c: math.hypot(c[0] * 16, c[1] * 16))
                    if not exclusion_suppressed(seed, c)]
            cands = pins.get(seed, []) + ([c for c in free if c not in pins.get(seed, [])][: args.sites] if seed in args.seeds else [])
            for cx, cz in cands:
                srv.cmd(f"forceload add {cx * 16 - 64} {cz * 16 - 64} {cx * 16 + 80} {cz * 16 + 80}")
                wait_loaded(srv, cx * 16, cz * 16)
            time.sleep(3)
            srv.save()
            world = World(srv.region_dir)
            all_legs, sites = [], []
            for cx, cz in cands:
                start, _ = read_start(world, cx, cz, STRUCT)
                if start is None:
                    sites.append({"candidate_chunk": [cx, cz], "outcome": "no_structure"})
                    continue
                tag = f"s{seed}_c{cx}_{cz}"
                legs = legs_for_site(start, templates, tag)
                sites.append({"candidate_chunk": [cx, cz], "tag": tag, "start_bb": union_bb(start),
                              "rotation": next(c["rotation"] for c in start["Children"] if c["pool_element"]["location"].endswith("main_chamber")),
                              "leg_count": len(legs)})
                all_legs += legs
            request.write_text("".join(f"{i} {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} {t}\n" for i, a, b, t in all_legs))
            srv.cmd("time set midnight")
            srv.cmd("tick sprint 40000")
            deadline = time.time() + 1500
            done = False
            while time.time() < deadline and not done:
                time.sleep(3)
                if result.exists() and '"__done__"' in result.read_text():
                    done = True
            srv.cmd("tick sprint stop")
            rows = [json.loads(line) for line in result.read_text().splitlines()] if result.exists() else []
            rows = [r for r in rows if r["id"] != "__done__"]
            summary.append({"mode": "jump_allowed" if args.allow_jump else "walk_only", "seed": seed, "sites": sites, "legs": rows, "completed": done, "expected_legs": len(all_legs)})
            print(f"seed {seed}: {len(rows)}/{len(all_legs)} legs, done={done}", flush=True)
            shutil.copy2(srv.log_path, args.out / f"traversal-server-seed-{seed}.log")
        finally:
            srv.stop()
        (args.out / "traversal.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
