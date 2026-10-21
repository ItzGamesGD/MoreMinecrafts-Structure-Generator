"""Simulated player inside GENERATED cities: boot a 26.1.2 server on a saved sweep world (Stage 24-G or 24-H) and run the
Stage 24-C/24-F mineflayer scenario at a specific restored piece of that city (rotation/origin from the manifest).
Simulated-player evidence on real generated worlds; not client gameplay."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT  # noqa: E402
from tools.stage24c.goals import derive  # noqa: E402
from tools.stage24c.gameplay import scenario, offline_uuid, BOT_DIR, PORT, RPORT  # noqa: E402
from tools.stage24c.mcserver import Server  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, TARGET  # noqa: E402
from tools.stage24g.gameplay_decayed import transform  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
MAN = {"g24": ROOT / "artifacts/ancient-city-restoration/stage-24g/worldgen", "h24": D24H / "worldgen",
       "i24": D24I / "worldgen", "i24x": D24I / "experiment-entrance/worldgen"}
CASES = [(24005, "medium_ruin_1", 71), (24009, "large_ruin_1", 59), (24008, "small_ruin_1", 93)]


def run_case(seed, module, idx, variant, out_dir: Path):
    p = json.loads((MAN[variant] / f"manifest-{seed}-{variant}.json").read_text())["cities"][0]["pieces"][idx]
    assert TARGET.get(p["template"]) == module, (p["template"], module)
    root = OUT / f"_work/s24h-city-{seed}-{variant}"
    srv = Server(root, JAR, JAVA, {"server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival", "force-gamemode": "true",
                                   "level-seed": str(seed)})
    shutil.rmtree(root / "world", ignore_errors=True)
    shutil.copytree(OUT / f"_work/wg-{seed}-{variant}/world", root / "world")
    for f in ("session.lock",):
        (root / "world" / f).unlink(missing_ok=True)
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4,
                                                "bypassesPlayerLimit": True} for m in MODULES]))
    srv.start()
    try:
        bb = p["bb"]
        srv.cmd(f"forceload add {bb[0] - 16} {bb[2] - 16} {bb[3] + 16} {bb[5] + 16}")
        time.sleep(4)
        srv.cmd("difficulty peaceful")
        srv.cmd("gamerule doDaylightCycle false")
        srv.cmd("time set day")
        steps = transform(scenario(module, [0, 0, 0], derive(module, D24F)), ROT[p["rotation"]], p["pos"])
        sp = root / "scenario.json"
        sp.write_text(json.dumps({"module": module, "port": PORT, "steps": steps, "global_timeout": 900}))
        rp = out_dir / f"result-city-{seed}-{module}-{variant}.json"
        out_dir.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=1000)
        if not rp.exists():
            return {"error": "no result", "stderr": proc.stderr[-400:]}
        res = json.loads(rp.read_text())
        res.update({"seed": seed, "variant": variant, "piece_index": idx, "piece": p, "scenario_steps": steps})
        rp.write_text(json.dumps(res, indent=1))
        return {"ok": sum(1 for s in res["steps"] if s.get("ok")), "total": len(res["steps"]),
                "failed": [s["name"] for s in res["steps"] if not s.get("ok")]}
    finally:
        srv.stop()


def main(out_dir: Path, variants=("g24", "h24"), cases=CASES, summary_name="summary-city.json"):
    summary = {}
    for seed, m, idx in cases:
        for v in variants:
            k = f"{seed}:{m}#{idx}:{v}"
            summary[k] = run_case(seed, m, idx, v, out_dir)
            print(k, summary[k], flush=True)
    (out_dir / summary_name).write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24H / "live/city-gameplay"))
    ap.add_argument("--variants", nargs="*", default=["g24", "h24"])
    ap.add_argument("--cases", nargs="*", default=None, help="seed:module:piece_index")
    ap.add_argument("--summary-name", default="summary-city.json")
    a = ap.parse_args()
    cases = [(int(c.split(":")[0]), c.split(":")[1], int(c.split(":")[2])) for c in a.cases] if a.cases else CASES
    main(Path(a.out), a.variants, cases, a.summary_name)
