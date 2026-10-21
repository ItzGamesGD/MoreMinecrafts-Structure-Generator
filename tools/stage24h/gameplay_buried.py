"""Simulated player (mineflayer) on BURIED placements: the area is filled with deepslate, the Stage 24-H pool entry is
placed with /place jigsaw (real processors + protection + clearance), then only the ground OUTSIDE the piece box is
opened so the bot can walk up. Everything the bot uses inside the box was cleared by the overlay alone.
8 modules x 4 rotations. Simulated-player evidence, not client gameplay."""
from __future__ import annotations

import argparse
import json
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
from tools.stage24g.gameplay_decayed import transform  # noqa: E402
from tools.stage24g.live_processing import FLAT, Y0, ROTS, locate  # noqa: E402
from tools.stage24h.live_clearance import test_pack, fill, D24F, D24H  # noqa: E402


def world_box(loc, size):
    r, o = loc["rotation"], loc["origin"]
    pts = [rot((x, 0, z), r) for x in (0, size[0] - 1) for z in (0, size[2] - 1)]
    return (o[0] + min(p[0] for p in pts), o[2] + min(p[2] for p in pts), o[0] + max(p[0] for p in pts), o[2] + max(p[2] for p in pts))


def main(out_dir: Path, max_attempts=12, modules=None, summary_name="summary-buried.json", stage="h24"):
    work = OUT / "_work/s24h-gameplay"
    pack = work / "pack"
    if stage == "i24":
        from tools.stage24i.live import test_pack as test_pack_i
        test_pack_i(pack)
        pool = "s24itest:i24"
    else:
        test_pack(pack)
        pool = "s24htest:h24"
    root = work / "server"
    srv = Server(root, JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false",
                                   "server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival",
                                   "force-gamemode": "true"}, datapack=pack, heap="3G")
    (root / "ops.json").write_text(json.dumps([{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4,
                                                "bypassesPlayerLimit": True} for m in MODULES]))
    srv.start()
    report = {"placements": {}, "summary": {}}
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for mi, m in enumerate(MODULES):
            if modules and m not in modules:
                continue
            nbt = load_nbt(D24F / m / "restored.nbt")
            size = [int(v) for v in nbt["size"]]
            blocks = blocks_of(nbt)
            span = max(size[0], size[2]) + 3
            got = {}
            for k in range(max_attempts):
                if len(got) == 4:
                    break
                x, z = 6000 + mi * 200, 6000 + k * (2 * span + 40)
                srv.cmd(f"forceload add {x - span - 12} {z - span - 12} {x + span + 12} {z + span + 12}")
                time.sleep(0.4)
                # bury the piece box up to its own top layer; cells above the box are outside every template (in the
                # 24-seed sweep the space above the tower decks was air in 192/192 cells)
                fill(srv, x - span, Y0, z - span, x + span, Y0 + size[1] - 1, z + span, "deepslate")
                outp = srv.cmd(f"place jigsaw {pool}/{m} minecraft:connect_structure 1 {x} {Y0 + 1} {z}")
                srv.flush()
                loc = locate(World(root / "world/dimensions/minecraft/overworld"), blocks, (x, Y0 + 1, z), None)
                if loc["rotation"] in got:
                    continue
                bx0, bz0, bx1, bz1 = world_box(loc, size)
                # open the ground outside the piece box only (the box itself is left exactly as generated)
                for (a0, c0, a1, c1) in ((x - span, z - span, bx0 - 1, z + span), (bx1 + 1, z - span, x + span, z + span),
                                         (bx0, z - span, bx1, bz0 - 1), (bx0, bz1 + 1, bx1, z + span)):
                    if a0 <= a1 and c0 <= c1:
                        fill(srv, a0, Y0 + 1, c0, a1, Y0 + size[1] + 1, c1, "air")
                got[loc["rotation"]] = {"command_pos": [x, Y0 + 1, z], "place_output": outp, "box_xz": [bx0, bz0, bx1, bz1], **loc}
            srv.cmd("tick sprint 200")
            time.sleep(6)
            g = derive(m, D24F)
            for r, loc in sorted(got.items()):
                steps = transform(scenario(m, [0, 0, 0], g), r, loc["origin"])
                sp = work / f"scenario-{m}-{r}.json"
                rp = out_dir / f"result-buried-{m}-{ROTS[r]}.json"
                sp.write_text(json.dumps({"module": m, "port": PORT, "steps": steps, "global_timeout": 900}))
                srv.cmd("time set day")
                proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=1000)
                key = f"{m}@{ROTS[r]}"
                if rp.exists():
                    res = json.loads(rp.read_text())
                    res.update({"rotation": ROTS[r], "placement": loc, "scenario_steps": steps})
                    rp.write_text(json.dumps(res, indent=1))
                    report["summary"][key] = {"ok": sum(1 for s in res["steps"] if s.get("ok")), "total": len(res["steps"]),
                                              "failed": [s["name"] for s in res["steps"] if not s.get("ok")]}
                else:
                    report["summary"][key] = {"error": "no result file", "stderr": proc.stderr[-400:]}
                report["placements"][key] = loc
                print(key, report["summary"][key], flush=True)
            missing = [ROTS[r] for r in ROTS if r not in got]
            if missing:
                report["summary"][f"{m}@missing"] = missing
    finally:
        srv.stop()
    (out_dir / summary_name).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24H / "live/gameplay-buried"))
    ap.add_argument("--max", type=int, default=16)
    ap.add_argument("--modules", nargs="*")
    ap.add_argument("--summary-name", default="summary-buried.json")
    ap.add_argument("--stage", default="h24", choices=["h24", "i24"])
    a = ap.parse_args()
    main(Path(a.out), a.max, a.modules, a.summary_name, a.stage)
