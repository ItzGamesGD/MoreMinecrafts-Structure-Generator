"""Real 26.1.2 server test of the Stage 24-I pool entries, 8 modules x 4 rotations, on buried placements.

Same procedure as tools/stage24h/live_clearance.py (fill with deepslate, /place jigsaw, classify every cell of the box
and its ring), with the Stage 24-I roof cells treated as protected overlay cells. Per placement it also records roof
continuity: how many roof cells block_rot would have dropped at that world position and whether every roof cell is
present. A Stage 24-H control placement per module shows the same roof without protection.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import Server, World  # noqa: E402
from tools.stage24c.worldgen_analyze import rot  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.live_processing import FLAT, Y0, ROTS, locate  # noqa: E402
from tools.stage24h.live_clearance import pool_entries, fill, analyse  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"


def test_pack(dest: Path):
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(D24I / "datapack", dest)
    for kind, src in (("i24", D24I / "datapack"), ("h24", D24H / "datapack")):
        for m, el in pool_entries(src).items():
            p = dest / f"data/s24itest/worldgen/template_pool/{kind}/{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"fallback": "minecraft:empty", "elements": [{"element": el, "weight": 1}]}, indent=1))


def roof_check(world, m, loc, roofs):
    r, o = loc["rotation"], loc["origin"]
    c = Counter()
    missing = []
    for e in roofs[m]["roof_cells"]:
        p = tuple(e["pos"])
        q = rot(p, r)
        w = (o[0] + q[0], o[1] + q[1], o[2] + q[2])
        got = P.name(world.block(*w) or "minecraft:air")
        c["would_rot"] += P.rot_removed(e["state"], w)
        ok = got in (P.name(e["state"]), P.name(e["state"]).replace("minecraft:", "minecraft:cracked_"), "minecraft:sculk")
        c["present" if ok else "MISSING"] += 1
        if not ok:
            missing.append({"pos": list(p), "world": list(w), "got": got})
    return {"counts": dict(c), "missing": missing[:20]}


def main(out_dir: Path, max_attempts=16, modules=MODULES, name="live-roof-report.json"):
    work = OUT / "_work/s24i-live"
    pack = work / "pack"
    test_pack(pack)
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    roofs = json.loads((D24I / "roof/roof-cells.json").read_text())
    inv_i = copy.deepcopy(inv)
    for m in MODULES:  # roof cells are protected overlay cells in Stage 24-I
        inv_i[m]["protected"] += [{"pos": e["pos"], "roles": ["roof"]} for e in roofs[m]["roof_cells"]]
        inv_i[m]["overlay"] += [{"pos": e["pos"], "state": e["state"]} for e in roofs[m]["roof_cells"]]
    masks = json.loads((D24H / "mask/interior-masks.json").read_text())
    srv = Server(work / "server", JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT,
                                               "generate-structures": "false"}, datapack=pack, heap="3G").start()
    report = {"datapack_list": srv.cmd("datapack list"), "placements": []}
    try:
        for mi, m in enumerate(MODULES):
            if m not in modules:
                continue
            root = load_nbt(D24F / m / "restored.nbt")
            size = [int(v) for v in root["size"]]
            blocks = blocks_of(root)
            mask = {tuple(p) for v in masks[m]["cleared"].values() for p in v}
            span = max(size[0], size[2]) + 3
            plan = [("i24", "deepslate")] * max_attempts + [("h24", "deepslate")]
            seen = set()
            for k, (kind, fb) in enumerate(plan):
                if kind == "i24" and len(seen) == 4:
                    continue
                x, z = 8000 + mi * 200, 8000 + k * (2 * span + 30)
                srv.cmd(f"forceload add {x - span - 2} {z - span - 2} {x + span + 2} {z + span + 2}")
                time.sleep(0.4)
                srv.cmd("tick freeze")
                fill(srv, x - span, Y0, z - span, x + span, Y0 + size[1] + 1, z + span, fb)
                outp = srv.cmd(f"place jigsaw s24itest:{kind}/{m} minecraft:connect_structure 1 {x} {Y0 + 1} {z}")
                srv.flush()
                w = World(srv.root / "world/dimensions/minecraft/overworld")
                loc = locate(w, blocks, (x, Y0 + 1, z), None)
                rec = {"module": m, "kind": kind, "fill": fb, "command_pos": [x, Y0 + 1, z], "place_output": outp, **loc}
                rec["analysis"] = analyse(w, m, "h24", loc, inv_i if kind == "i24" else inv, mask, fb)
                rec["roof"] = roof_check(w, m, loc, roofs)
                srv.cmd("tick unfreeze")
                if kind == "i24":
                    seen.add(loc["rotation"])
                report["placements"].append(rec)
                a = rec["analysis"]
                print(m, kind, ROTS[loc["rotation"]], loc["match"], "/", loc["probe"], "VIOL", Counter(v["type"] for v in a["violations"]),
                      "roof", rec["roof"]["counts"], flush=True)
    finally:
        srv.stop()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(json.dumps(report, indent=1, default=list))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24I / "live"))
    ap.add_argument("--max", type=int, default=16)
    ap.add_argument("--modules", nargs="*", default=MODULES)
    ap.add_argument("--report-name", default="live-roof-report.json")
    a = ap.parse_args()
    main(Path(a.out), a.max, a.modules, a.report_name)
