#!/usr/bin/env python3
"""N9 L10 control: does the 'Can't keep up' stall seen right after the driver's /locate + forceload rows also occur on a vanilla server and without a client?
usage: n9_stall_control.py --variant vanilla|production --out FILE.json   (env: JAVA_HOME, SERVER_JAR for vanilla, SG_PACK)
Same server properties and the same command sequence as live_acceptance.py (locate, then nine one-chunk-row forceloads 3 s apart); no client joins."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from world import Server  # noqa: E402

MOD = HERE.parents[2] / "mod" / "sg-worldgen-protection"
PROPS = {"difficulty": "normal", "spawn-monsters": "true", "spawn-animals": "false", "view-distance": "6", "simulation-distance": "6",
         "pause-when-empty-seconds": "-1", "max-tick-time": "-1", "gamemode": "survival", "spawn-protection": "0"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["vanilla", "production"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=173)
    a = ap.parse_args()
    run_dir = (MOD / "run" / "server").resolve() if a.variant == "production" else (a.out.parent / f"vanilla-run-{os.getpid()}").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    pack = Path(os.environ["SG_PACK"])
    if a.variant == "production":
        srv = Server("java", None, run_dir, a.seed, pack, port=25765, launcher=["./gradlew", "--no-daemon", "jar", "runJarServer"], launcher_cwd=MOD, start_timeout=900, extra_props=PROPS)
    else:
        srv = Server("java", Path(os.environ["SERVER_JAR"]), run_dir, a.seed, pack, port=25765, extra_props=PROPS, start_timeout=600)
    events = []
    try:
        time.sleep(20)  # the live run's client join takes about this long
        mark = len((run_dir / "server.log").read_text(errors="replace"))
        t0 = time.time()
        r = srv.cmd("execute in minecraft:overworld positioned 0 64 0 run locate structure moreminecrafts:forgotten_kingdom/central_cavern")
        events.append({"cmd": "locate", "t_s": round(time.time() - t0, 2), "reply": r[:120]})
        m = re.search(r"\[(-?\d+), (~|-?\d+), (-?\d+)\]", r)
        sx, sz = int(m.group(1)), int(m.group(3))
        for row in range(-4, 5):
            t1 = time.time()
            srv.cmd(f"forceload add {sx - 64} {sz + row * 16} {sx + 64} {sz + row * 16}")
            events.append({"cmd": f"forceload row {row}", "t_s": round(time.time() - t1, 2)})
            time.sleep(3)
        time.sleep(30)
        text = (run_dir / "server.log").read_text(errors="replace")[mark:]
        stalls = [ln for ln in text.splitlines() if "Can't keep up" in ln]
        tick = srv.cmd("tick query")
        res = {"variant": a.variant, "cant_keep_up": stalls, "events": events, "tick_query": tick[:240]}
    finally:
        srv.stop()
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"variant": res["variant"], "cant_keep_up": res["cant_keep_up"], "locate_s": events[0]["t_s"]}))


if __name__ == "__main__":
    main()
