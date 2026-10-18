#!/usr/bin/env python3
"""SYNTHETIC fluid-contact scenarios on a naturally generated SG-01 site (supplementary; NOT natural-generation passes).

A natural site is generated, then a block of water or lava is /fill-ed against a tunnel mouth that terrain had sealed. Game time
is advanced and fluid is counted per piece to measure how far it enters the tunnel and whether it reaches the plaza chamber.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import FLUIDS, STRUCT, analyze, build_model, load_templates  # noqa: E402
from run_stress import read_start, sprint, wait_loaded  # noqa: E402
from spread import SG01, candidates_in_ring, exclusion_suppressed  # noqa: E402
from world import Server, World  # noqa: E402


def fluid_census(world: World, start: dict, templates: dict):
    _solid, air, _jig, _pieces = build_model(start, templates)
    piece_of = build_model.air_piece
    census: Counter = Counter()
    deepest: dict[str, int] = {}
    for pos in air:
        block = world.block_id(*pos)
        if block in FLUIDS:
            census[(piece_of[pos], FLUIDS[block])] += 1
    return {f"{piece}:{kind}": n for (piece, kind), n in sorted(census.items())}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--java", default="java")
    p.add_argument("--jar", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--seed", type=int, default=173)
    p.add_argument("--ticks", type=int, default=2400)
    p.add_argument("--port", type=int, default=25775)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    templates = load_templates(args.pack / "data/moreminecrafts/structure/forgotten_kingdom/central_cavern")
    run = args.out / "run-synthetic"
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    srv = Server(args.java, args.jar, run, args.seed, args.pack, port=args.port)
    report = {"label": "SYNTHETIC (controlled /fill against a naturally generated site); not a natural-generation result", "seed": args.seed, "scenarios": []}
    try:
        cx, cz = next(c for c in sorted(candidates_in_ring(args.seed, SG01, 6), key=lambda c: math.hypot(*c)) if not exclusion_suppressed(args.seed, c))
        srv.cmd(f"forceload add {cx * 16 - 64} {cz * 16 - 64} {cx * 16 + 80} {cz * 16 + 80}")
        wait_loaded(srv, cx * 16, cz * 16)
        time.sleep(3)
        srv.save()
        world = World(srv.region_dir)
        start, _ = read_start(world, cx, cz, STRUCT)
        base = analyze(world, start, templates, snapshot="baseline")
        report["site"] = {"chunk": [cx, cz], "rotation": base["chamber_rotation"], "baseline_apertures": {k: v["state"] for k, v in base["apertures"].items()},
                          "baseline_fluid": fluid_census(world, start, templates)}
        mouths = [(k, v) for k, v in base["apertures"].items() if v["state"] == "blocked_by_terrain"]
        scenarios = [("water", mouths[0]), ("lava", mouths[1])]
        for fluid, (name, ap) in scenarios:
            face, plane = name.split("@")
            x, y, z = ap["first_cell_outside"]
            d = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}[face]
            lo = [x - 3 if d[0] == 0 else x, y - 1, z - 3 if d[1] == 0 else z]
            hi = [x + 3 if d[0] == 0 else x + 5 * d[0], y + 5, z + 3 if d[1] == 0 else z + 5 * d[1]]
            a = [min(lo[i], hi[i]) for i in range(3)]; b = [max(lo[i], hi[i]) for i in range(3)]
            out = srv.cmd(f"fill {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} minecraft:{fluid}")
            report["scenarios"].append({"fluid": fluid, "mouth": name, "fill": [a, b], "fill_result": out})
        sprint_line = sprint(srv, args.ticks)
        srv.save()
        world2 = World(srv.region_dir)
        start2, _ = read_start(world2, cx, cz, STRUCT)
        final = analyze(world2, start2, templates, snapshot=f"after_{args.ticks}_ticks")
        report["after_ticks"] = args.ticks
        report["sprint_log"] = sprint_line
        report["fluid_cells_by_piece"] = fluid_census(world2, start2, templates)
        report["integrity_after"] = {k: final["integrity"][k] for k in ("matched", "expected_solid_blocks", "mismatched")}
        report["apertures_after"] = {k: {"interior": v["aperture_interior_counts"], "outside": v["outside_counts"]} for k, v in final["apertures"].items()}
        (args.out / "synthetic-fluid.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"fluid_cells_by_piece": report["fluid_cells_by_piece"], "integrity_after": report["integrity_after"]}, indent=1))
    finally:
        srv.stop()
        shutil.copy2(srv.log_path, args.out / "server-synthetic.log")
        shutil.rmtree(run, ignore_errors=True)


if __name__ == "__main__":
    main()
