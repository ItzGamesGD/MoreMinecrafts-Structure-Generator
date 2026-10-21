"""Simulated player from the city path to the inside of a house door, in generated sweep worlds.

Start: the open-city cell at the end of the entrance survey path (`tools/stage24i/entrances.py`), i.e. a free walkable
cell of the city's open space. Steps: the mineflayer pathfinder (no digging, no block placing) walks from there to the cell in front of the door,
the door is opened, the player jump-walks through it (the city path is often one block below the threshold; the
pathfinder alone does not step up into a doorway, even at unobstructed doors), must stand in the cell just inside,
then the pathfinder walks back out to the start.
Mineflayer bot on a real 26.1.2 server; NOT Minecraft-client gameplay.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT  # noqa: E402
from tools.stage24c.gameplay import offline_uuid, BOT_DIR, PORT, RPORT  # noqa: E402
from tools.stage24c.mcserver import Server  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
SURVEY = {"h24": D24I / "investigation/h24-entrance-survey.json", "i24": D24I / "worldgen/i24-entrance-survey.json",
          "i24x": D24I / "worldgen/i24-entrance-survey.json"}  # the experiment world has the same layout; start from the i24 path end
MAN = {"h24": ROOT / "artifacts/ancient-city-restoration/stage-24h/worldgen", "i24": D24I / "worldgen",
       "i24x": D24I / "experiment-entrance/worldgen"}


YAW = {(1, 0): -math.pi / 2, (-1, 0): math.pi / 2, (0, -1): 0.0, (0, 1): math.pi}  # mineflayer yaw of a walk direction


def steps_for(r):
    door, out = r["door_world"], r["outward"]
    inward = (-out[0], -out[2])
    inside = [door[0] + inward[0], door[1], door[2] + inward[1]]
    start, front = r["path"][-1], r["path"][1]
    c = lambda p: [p[0] + 0.5, p[1], p[2] + 0.5]  # noqa: E731
    return [{"name": "tp_city_path", "type": "tp", "target": c(start)},
            {"name": "walk_city_path_to_door_front", "type": "goto", "target": front, "range": 0, "timeout": 90},
            {"name": "door_open", "type": "door", "pos": door, "expect": "open"},
            {"name": "jump_walk_through_door", "type": "walk", "yaw": YAW[inward], "jump": True, "ms": 1500, "min_move": 0.8},
            {"name": "inside_door_reached", "type": "goto", "target": inside, "range": 0, "timeout": 20},
            {"name": "walk_inside_to_city_path", "type": "goto", "target": start, "range": 0, "timeout": 90}]


def run(seed, idx, variant, out_dir: Path):
    r = next(x for x in json.loads(SURVEY[variant].read_text()) if x["seed"] == seed and x["piece_index"] == idx)
    p = json.loads((MAN[variant] / f"manifest-{seed}-{variant}.json").read_text())["cities"][0]["pieces"][idx]
    root = OUT / f"_work/s24i-nav-{seed}-{variant}"
    srv = Server(root, JAR, JAVA, {"server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival", "force-gamemode": "true",
                                   "level-seed": str(seed)})
    shutil.rmtree(root / "world", ignore_errors=True)
    shutil.copytree(OUT / f"_work/wg-{seed}-{variant}/world", root / "world")
    (root / "world/session.lock").unlink(missing_ok=True)
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4,
                                                "bypassesPlayerLimit": True} for m in MODULES]))
    srv.start()
    try:
        bb = p["bb"]
        srv.cmd(f"forceload add {bb[0] - 16} {bb[2] - 16} {bb[3] + 16} {bb[5] + 16}")
        time.sleep(4)
        for c in ("difficulty peaceful", "gamerule doDaylightCycle false", "time set day"):
            srv.cmd(c)
        steps = steps_for(r)
        sp = root / "scenario.json"
        sp.write_text(json.dumps({"module": r["module"], "port": PORT, "steps": steps, "global_timeout": 300}))
        out_dir.mkdir(parents=True, exist_ok=True)
        rp = out_dir / f"result-nav-{seed}-{idx}-{r['module']}-{variant}.json"
        proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=600)
        if not rp.exists():
            return {"error": "no result", "stderr": proc.stderr[-400:]}
        res = json.loads(rp.read_text())
        res.update({"seed": seed, "variant": variant, "piece_index": idx, "survey": {k: r[k] for k in r if k != "path"},
                    "survey_path": r["path"], "scenario_steps": steps})
        rp.write_text(json.dumps(res, indent=1))
        return {s["name"]: {"ok": s.get("ok"), "end": s.get("end"), "error": s.get("horizontal_error")} for s in res["steps"]}
    finally:
        srv.stop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24I / "live/entrance-nav"))
    ap.add_argument("--cases", nargs="+", required=True, help="seed:piece_index:variant")
    a = ap.parse_args()
    summary = {}
    for c in a.cases:
        s, i, v = c.split(":")
        summary[c] = run(int(s), int(i), v, Path(a.out))
        print(c, summary[c], flush=True)
    (Path(a.out) / "summary-entrance-nav.json").write_text(json.dumps(summary, indent=1))
