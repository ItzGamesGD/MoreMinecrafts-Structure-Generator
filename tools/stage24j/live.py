"""Real 26.1.2 server test of the Stage 24-J watchtower alternatives (and the approved towers as controls).

1. Exact placement: every candidate is placed with `/place template` in all four rotations on a flat test world; every
   template cell is read back and compared with the rotated template (block id; states are rotated by the game).
2. Bot (mineflayer, NOT client gameplay): per placement the Stage 24-C tower scenario, parametrised by the variant's
   ladder and deck: walk from outside to the ladder, climb to the hatch, step onto the deck, then walk outward from the
   cell just inside every deck edge on every row and column; any drop is a failure.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT, blocks_of, load_nbt  # noqa: E402
from tools.stage24c.gameplay import offline_uuid, BOT_DIR, PORT, RPORT, deck_probes, YAW, W, C  # noqa: E402
from tools.stage24c.mcserver import Server, World  # noqa: E402
from tools.stage24c.worldgen_analyze import rot  # noqa: E402
from tools.stage24g.gameplay_decayed import transform  # noqa: E402
from tools.stage24g.live_processing import FLAT, Y0, ROTS  # noqa: E402
from tools.stage24h.live_clearance import fill  # noqa: E402
from tools.stage24j.designs import DESIGNS, D24F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24J = ROOT / "artifacts/ancient-city-restoration/stage-24j"
ROT_ARG = {0: "none", 90: "clockwise_90", 180: "180", 270: "counterclockwise_90"}


def candidates():
    for m, fs in DESIGNS.items():
        for f in fs:
            v = f()
            yield v, (D24F / m / "restored.nbt" if v.variant == "current" else D24J / "proposals" / m / v.variant / "candidate.nbt")


def pack(dest: Path):
    shutil.rmtree(dest, ignore_errors=True)
    meta = json.loads((ROOT / "artifacts/ancient-city-restoration/stage-24i/datapack/pack.mcmeta").read_text())
    meta["pack"]["description"] = "Stage 24-J watchtower alternatives (test only)"
    dest.mkdir(parents=True)
    (dest / "pack.mcmeta").write_text(json.dumps(meta))
    for v, path in candidates():
        p = dest / f"data/s24j/structure/{v.module}/{v.variant.lower()}.nbt"
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, p)


def scenario(v):
    m, (lx, lz), top, dy = v.module, v.meta["ladder"], v.meta["ladder_top"], v.meta["deck_y"]
    deck = set(v.meta["deck"])
    steps = []
    add = lambda name, **kw: steps.append({"name": name, **kw})  # noqa: E731
    if m == "large_pillar_1":
        add("tp_outside", type="tp", target=C([0, 0, 0], [-3, 1, 2]))
        add("walk_to_entry", type="goto", target=W([0, 0, 0], [1, 1, 2]), range=0, timeout=30)
        add("enter_ladder_base", type="goto", target=W([0, 0, 0], [2, 1, 2]), range=0, timeout=30)
        yaw = YAW["west"]
    else:
        add("tp_outside", type="tp", target=C([0, 0, 0], [3, 1, -3]))
        add("walk_to_entry", type="goto", target=W([0, 0, 0], [3, 1, 1]), range=0, timeout=30)
        add("walk_to_ladder_approach", type="goto", target=W([0, 0, 0], [4, 1, 2]), range=0, timeout=30)
        yaw = YAW["east"]
    add("climb_ground_to_deck", type="climb", base=[lx, 1, lz], top=[lx, top + 1, lz], yaw=yaw, timeout=60)
    first = next((lx + dx, lz + dz) for dx, dz in ((0, 1), (-1, 0), (0, -1), (1, 0)) if (lx + dx, lz + dz) in deck)
    add("step_onto_deck", type="goto", target=[first[0], dy, first[1]], range=0, timeout=20)
    xs = sorted({x for x, z in deck})
    zs = sorted({z for x, z in deck})
    # deck_probes walks outward from the cell just inside each edge; only start cells that are deck cells are kept
    for s in deck_probes([0, 0, 0], dy, range(xs[0] - 1, xs[-1] + 2), range(zs[0] - 1, zs[-1] + 2), hatch={(lx, lz)}):
        steps.append(s)
    out, keep = [], True
    for s in steps:
        if s["name"].endswith("_recentre") and s["name"].startswith("deck_edge"):
            t = s["target"]
            keep = (int(t[0] - .5), int(t[2] - .5)) in deck
        if keep or not s["name"].startswith("deck_edge"):
            out.append(s)
    return out


def main(out_dir: Path, bot=True):
    work = OUT / "_work/s24j-live"
    pk = work / "pack"
    pack(pk)
    root = work / "server"
    srv = Server(root, JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false",
                                   "server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival", "force-gamemode": "true"},
                 datapack=pk, heap="3G")
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4,
                                                "bypassesPlayerLimit": True} for m in MODULES]))
    srv.start()
    report = {"datapack_list": srv.cmd("datapack list"), "placements": []}
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        placed = []
        for i, (v, path) in enumerate(candidates()):
            nbt = load_nbt(path)
            size = [int(s) for s in nbt["size"]]
            blocks = {p: s for p, (s, _) in blocks_of(nbt).items()}
            for k, r in enumerate((0, 90, 180, 270)):
                x, z = 9000 + i * 60, 9000 + k * 60
                srv.cmd(f"forceload add {x - 24} {z - 24} {x + 24} {z + 24}")
                time.sleep(0.3)
                fill(srv, x - 20, Y0 + 1, z - 20, x + 20, Y0 + 20, z + 20, "air")
                outp = srv.cmd(f"place template s24j:{v.module}/{v.variant.lower()} {x} {Y0 + 1} {z} {ROT_ARG[r]}")
                placed.append((v, path, r, [x, Y0 + 1, z], outp, blocks, size))
        srv.flush()
        w = World(root / "world/dimensions/minecraft/overworld")
        for v, path, r, o, outp, blocks, size in placed:
            mism = []
            for p, s in blocks.items():
                q = rot(p, r)
                got = w.block(o[0] + q[0], o[1] + q[1], o[2] + q[2]) or "minecraft:air"
                want = s.split("[")[0]
                if want == "minecraft:jigsaw":
                    continue   # /place template keeps jigsaw blocks; their final_state applies only in jigsaw generation
                if got.split("[")[0] != want:
                    mism.append({"pos": list(p), "want": s, "got": got})
            rec = {"module": v.module, "variant": v.variant, "rotation": ROTS[r], "origin": o, "place_output": outp,
                   "cells": len(blocks), "mismatches": len(mism), "mismatch_sample": mism[:10]}
            report["placements"].append(rec)
            print(v.module, v.variant, ROTS[r], outp.strip()[:60], "mismatch", len(mism), flush=True)
        if bot:
            srv.cmd("time set day")
            srv.cmd("difficulty peaceful")
            for rec, (v, path, r, o, *_x) in zip(report["placements"], placed):
                steps = transform(scenario(v), r, o)
                sp = work / f"scenario-{v.module}-{v.variant}-{r}.json"
                rp = out_dir / f"bot-{v.module}-{v.variant}-{ROTS[r]}.json"
                sp.write_text(json.dumps({"module": v.module, "port": PORT, "steps": steps, "global_timeout": 900}))
                proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=1000)
                if rp.exists():
                    res = json.loads(rp.read_text())
                    res.update({"variant": v.variant, "rotation": ROTS[r], "origin": o, "scenario_steps": steps})
                    rp.write_text(json.dumps(res, indent=1))
                    rec["bot"] = {"ok": sum(1 for s in res["steps"] if s.get("ok")), "total": len(res["steps"]),
                                  "failed": [s["name"] for s in res["steps"] if not s.get("ok")]}
                else:
                    rec["bot"] = {"error": "no result", "stderr": proc.stderr[-400:]}
                print(v.module, v.variant, ROTS[r], "bot", rec["bot"], flush=True)
    finally:
        srv.stop()
    (out_dir / "live-report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24J / "live"))
    ap.add_argument("--no-bot", action="store_true")
    a = ap.parse_args()
    main(Path(a.out), not a.no_bot)
