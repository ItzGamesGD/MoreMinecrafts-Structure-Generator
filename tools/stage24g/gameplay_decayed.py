"""Player simulation on *decayed* placements: every module x 4 rotations placed by `/place jigsaw` from the Stage 24-G
pool entry (real processors), then the Stage 24-C/24-F mineflayer scenario transformed into that placement's rotation."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.goals import derive  # noqa: E402
from tools.stage24c.gameplay import scenario, offline_uuid, BOT_DIR, PORT, RPORT  # noqa: E402
from tools.stage24c.mcserver import Server, World  # noqa: E402
from tools.stage24c.worldgen_analyze import rot  # noqa: E402
from tools.stage24g.build import D24G, D24F  # noqa: E402
from tools.stage24g.live_processing import FLAT, Y0, ROTS, test_pack, locate  # noqa: E402

BLOCK_KEYS = ("pos", "base", "top")


def cont(p, r):
    """Rotate a continuous point inside the template the way StructureTemplate rotates the block that contains it."""
    x, y, z = p
    return {0: (x, y, z), 90: (1 - z, y, x), 180: (1 - x, y, 1 - z), 270: (z, y, 1 - x)}[r]


def transform(steps, r, o):
    out = []
    for s in steps:
        s = dict(s)
        for k in BLOCK_KEYS:
            if k in s:
                q = rot(tuple(s[k]), r)
                s[k] = [o[0] + q[0], o[1] + q[1], o[2] + q[2]]
        if "target" in s:
            t = s["target"]
            if s["type"] in ("tp", "swim"):
                q = cont(tuple(t), r)
                s["target"] = [o[0] + q[0], o[1] + q[1], o[2] + q[2]]
            else:
                q = rot(tuple(t), r)
                s["target"] = [o[0] + q[0], o[1] + q[1], o[2] + q[2]]
        if "yaw" in s:
            s["yaw"] = s["yaw"] - (r // 90) * math.pi / 2
        for k in ("min_end_y", "max_end_y"):
            if k in s:
                s[k] = s[k] + o[1]
        out.append(s)
    return out


def main(out_dir: Path, modules=None, max_attempts=14):
    modules = modules or MODULES
    work = OUT / "_work/s24g-gameplay"
    pack = work / "pack"
    test_pack(pack, D24G / "datapack")
    root = work / "server"
    srv = Server(root, JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false",
                                   "server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival",
                                   "force-gamemode": "true"}, datapack=pack)
    root.mkdir(parents=True, exist_ok=True)
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4,
                                                "bypassesPlayerLimit": True} for m in MODULES]))
    srv.start()
    report = {"placements": {}, "summary": {}}
    try:
        for mi, m in enumerate(modules):
            blocks = blocks_of(load_nbt(D24F / m / "restored.nbt"))
            size = [int(v) for v in load_nbt(D24F / m / "restored.nbt")["size"]]
            span = max(size[0], size[2]) + 8
            got = {}
            for k in range(max_attempts):
                if len(got) == 4:
                    break
                x, z = 2000 + mi * 200, 2000 + k * (2 * span + 30)
                srv.cmd(f"forceload add {x - span} {z - span} {x + span} {z + span}")
                time.sleep(0.4)
                outp = srv.cmd(f"place jigsaw s24gtest:g24/{m} minecraft:connect_structure 1 {x} {Y0 + 1} {z}")
                srv.flush()
                loc = locate(World(root / "world/dimensions/minecraft/overworld"), blocks, (x, Y0 + 1, z), None)
                if loc["rotation"] not in got:  # a repeated rotation is simply left standing
                    got[loc["rotation"]] = {"command_pos": [x, Y0 + 1, z], "place_output": outp, **loc}
            srv.cmd("tick sprint 400")
            time.sleep(10)
            g = derive(m, D24F)
            for r, loc in sorted(got.items()):
                o = loc["origin"]
                steps = transform(scenario(m, [0, 0, 0], g), r, o)
                sc = {"module": m, "port": PORT, "steps": steps, "global_timeout": 900}
                sp = work / f"scenario-{m}-{r}.json"
                rp = out_dir / f"result-decayed-{m}-{ROTS[r]}.json"
                out_dir.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(sc))
                srv.cmd("time set day")
                proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=1000)
                key = f"{m}@{ROTS[r]}"
                if rp.exists():
                    res = json.loads(rp.read_text())
                    res.update({"origin": o, "rotation": ROTS[r], "placement": loc, "scenario_steps": steps})
                    rp.write_text(json.dumps(res, indent=1))
                    report["summary"][key] = {"ok": sum(1 for s in res["steps"] if s.get("ok")), "total": len(res["steps"]),
                                              "failed": [s["name"] for s in res["steps"] if not s.get("ok")]}
                else:
                    report["summary"][key] = {"error": "no result file", "stderr": proc.stderr[-400:]}
                report["placements"][key] = loc
                print(key, report["summary"][key], flush=True)
            missing = sorted(set(ROTS) - set(got))
            if missing:
                report["summary"][f"{m}@missing"] = [ROTS[r] for r in missing]
        srv.flush()
    finally:
        srv.stop()
    (out_dir / "summary-decayed.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24G / "live/gameplay"))
    ap.add_argument("--modules", nargs="*")
    a = ap.parse_args()
    main(Path(a.out), a.modules)
