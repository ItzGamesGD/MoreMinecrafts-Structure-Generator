"""Control experiment: does the simulated player climb a plain open-air stair run built with the same geometry?"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *
from tools.stage24c.mcserver import Server
from tools.stage24c.gameplay import FLAT, offline_uuid, BOT_DIR, YAW, PORT, RPORT

def main():
    root = OUT / "_work/stair-control-server"
    srv = Server(root, JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false",
                                   "server-port": str(PORT), "rcon.port": str(RPORT)})
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_stairctl"), "name": "S24C_stairctl", "level": 4, "bypassesPlayerLimit": True}]))
    srv.start()
    try:
        srv.cmd("forceload add 790 90 830 120")
        time.sleep(10)
        # open-air run: stairs facing east rising one block per cell, each over a full-block support, like medium_ruin_2
        for k in range(4):
            x, y = 800 + k, -60 + k
            if k:
                srv.cmd(f"fill {x} -60 100 {x} {y-1} 100 minecraft:deepslate_bricks")
            print(srv.cmd(f"setblock {x} {y} 100 minecraft:deepslate_tile_stairs[facing=east,half=bottom]"))
        srv.cmd("fill 804 -60 100 806 -57 100 minecraft:deepslate_tiles")
        sc = {"module": "stairctl", "port": PORT, "global_timeout": 200, "steps": [
            {"name": "tp", "type": "tp", "target": [799.5, -60, 100.5]},
            {"name": "probe", "type": "probe", "cells": [[800, -60, 100], [801, -59, 100], [801, -60, 100], [802, -58, 100]]},
            {"name": "walk_east", "type": "walk", "yaw": YAW["east"], "ms": 3000, "min_end_y": -56.05}]}
        sp = root / "sc.json"; sp.write_text(json.dumps(sc))
        rp = OUT / "gameplay/stair-control-result.json"
        p = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=300)
        print(p.stdout[-800:], p.stderr[-300:])
    finally:
        srv.stop()
main()
