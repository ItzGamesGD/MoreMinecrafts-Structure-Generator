"""Live player-simulation of the eight restored modules on a real 26.1.2 server (mineflayer bot)."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa
from tools.stage24c.goals import derive
from tools.stage24c.mcserver import Server, World

BOT_DIR = ROOT / "tools/stage24c/bot"
FLAT = '{"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:stone","height":3}],"biome":"minecraft:plains"}'
GROUND_TOP = -61   # y of the top stone block; standing feet level outside is GROUND_TOP + 1
ORIGIN_Y = -61     # structure layer y=0 replaces the ground surface, so floors are flush with outside terrain
PORT, RPORT = 25566, 25576


def offline_uuid(name):
    d = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    d[6] = (d[6] & 0x0F) | 0x30
    d[8] = (d[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(d)))


def W(o, p):
    return [o[0] + p[0], o[1] + p[1], o[2] + p[2]]


def C(o, p):
    """block-centre world coordinates for tp"""
    w = W(o, p)
    return [w[0] + 0.5, w[1], w[2] + 0.5]


YAW = {"west": math.pi / 2, "east": -math.pi / 2, "north": 0.0, "south": math.pi}  # mineflayer forward = (-sin yaw, -cos yaw): yaw 0 = north (-z)


DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def deck_probes(o, y, xs, zs, hatch=()):
    """Walk outward from the cell just inside every deck edge on every row/column; any drop is a failure."""
    out = []
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    for d, (dx, dz) in DIRS.items():
        lines = xs if dz else zs
        for ln in lines:
            if d == "north":
                cell = (ln, y, z0 + 1 if z1 > z0 else z0)
            elif d == "south":
                cell = (ln, y, z1 - 1 if z1 > z0 else z1)
            elif d == "west":
                cell = (x0 + 1 if x1 > x0 else x0, y, ln)
            else:
                cell = (x1 - 1 if x1 > x0 else x1, y, ln)
            path = []
            cx, cz = cell[0], cell[2]
            while x0 <= cx <= x1 and z0 <= cz <= z1:
                path.append((cx, cz))
                cx, cz = cx + dx, cz + dz
            if any(c in hatch for c in path):
                continue  # crossing the ladder hatch is an intended descent, not an edge
            out.append({"name": f"deck_edge_{d}_line{ln}_from{cell[0]}_{cell[2]}_recentre", "type": "tp",
                        "target": [o[0] + cell[0] + .5, o[1] + y, o[2] + cell[2] + .5]})
            out.append({"name": f"deck_edge_{d}_line{ln}", "type": "walk", "yaw": YAW[d], "ms": 2500})
    return out


def scenario(module, o, g):
    steps = []
    add = lambda name, **kw: steps.append({"name": name, **kw})
    door = g["doors"][0] if g["doors"] else None
    if module in {"large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"}:
        dx, dy, dz = door
        outside = [dx - 3, 1, dz]
        inside = [dx + 1, 1, dz]
        add("tp_outside", type="tp", target=C(o, outside))
        add("walk_to_door_front", type="goto", target=W(o, [dx - 1, 1, dz]), range=0, timeout=30)
        add("door_open_from_outside", type="door", pos=W(o, [dx, 1, dz]), expect="open")
        add("manual_walk_through_open_door", type="walk", yaw=YAW["east"], ms=1800, min_move=1.6)
        add("walk_to_entry_inside", type="goto", target=W(o, inside), range=0, timeout=60)
        add("manual_walk_out_through_door", type="walk", yaw=YAW["west"], ms=2200, min_move=1.8, pre=W(o, inside))
        add("door_front_after_exit", type="goto", target=W(o, [dx - 1, 1, dz]), range=0, timeout=20)
        add("door_close_from_outside", type="door", pos=W(o, [dx, 1, dz]), expect="closed")
        add("door_reopen", type="door", pos=W(o, [dx, 1, dz]), expect="open")
        add("re_enter_manual", type="walk", yaw=YAW["east"], ms=900, min_move=0.8)
        add("re_enter", type="goto", target=W(o, inside), range=0, timeout=30)
        for i, bed in enumerate(g["beds"]):
            if bed["pos"][1] > 1:
                continue
            acc = bed["access"][0]
            add(f"bed{i}_{bed['pos']}_reach", type="goto", target=W(o, acc), range=0, timeout=60)
            add(f"bed{i}_night", type="cmd", cmd="time set night")
            add(f"bed{i}_sleep", type="sleep", pos=W(o, bed["pos"]))
        for c in g["containers"]:
            if c["block"] == "crafting_table" or c["pos"][1] > 1:
                continue
            acc = c["access"][0]
            add(f"{c['block']}_{c['pos']}_reach", type="goto", target=W(o, acc), range=0, timeout=60)
            add(f"{c['block']}_{c['pos']}_open", type="container", pos=W(o, c["pos"]))
        if module == "medium_ruin_2":
            # physical stair climb: walk east along the stair run from the ground floor to the upper landing
            add("stairs_tp_foot", type="tp", target=C(o, [3, 1, 5]))
            add("stairs_walk_up_east", type="walk", yaw=YAW["east"], ms=2600, min_end_y=o[1] + 5 - 0.05)
            add("stairs_tp_foot_again", type="tp", target=C(o, [3, 1, 5]))
            add("stairs_walk_up_east_with_jump", type="walk", yaw=YAW["east"], ms=3500, jump=True, min_end_y=o[1] + 5 - 0.05)
            for i, bed in enumerate(g["beds"]):
                if bed["pos"][1] > 1:
                    add(f"upper_bed{i}_{bed['pos']}_reach", type="goto", target=W(o, bed["access"][0]), range=0, timeout=60)
                    add(f"upper_bed{i}_night", type="cmd", cmd="time set night")
                    add(f"upper_bed{i}_sleep", type="sleep", pos=W(o, bed["pos"]))
            for c in g["containers"]:
                if c["block"] != "crafting_table" and c["pos"][1] > 1:
                    add(f"upper_{c['block']}_{c['pos']}_reach", type="goto", target=W(o, c["access"][0]), range=0, timeout=60)
                    add(f"upper_{c['block']}_{c['pos']}_open", type="container", pos=W(o, c["pos"]))
            add("upstairs_tp_landing", type="tp", target=C(o, [8, 5, 5]))
            add("stairs_walk_down_west", type="walk", yaw=YAW["west"], ms=3200, descend=True, max_end_y=o[1] + 1.1)
    elif module == "sauna_1":
        inside = [13, 1, 35]
        add("tp_outside", type="tp", target=C(o, [13, 1, 40]))
        add("walk_to_reception", type="goto", target=W(o, inside), range=0, timeout=40)
        for i, c in enumerate(g["containers"]):
            acc = c["access"][0]
            add(f"chest{i}_{c['pos']}_reach", type="goto", target=W(o, acc), range=0, timeout=90)
            add(f"chest{i}_{c['pos']}_open", type="container", pos=W(o, c["pos"]))
        for i, wb in enumerate(g["water_bodies"]):
            rim = wb["rim_standable"][0]
            add(f"bath{i}_{wb['cells']}cells_rim_reach", type="goto", target=W(o, rim), range=0, timeout=90, xz_tol=1.2)
            add(f"bath{i}_{wb['cells']}cells_swim", type="swim", target=C(o, wb["sample_cell"]))
    elif module == "large_pillar_1":
        add("tp_outside", type="tp", target=C(o, [-3, 1, 2]))
        add("walk_to_entry", type="goto", target=W(o, [1, 1, 2]), range=0, timeout=30)
        add("enter_ladder_base", type="goto", target=W(o, [2, 1, 2]), range=0, timeout=30)
        add("climb_ground_to_deck", type="climb", base=W(o, [2, 1, 2]), top=W(o, [2, 14, 2]), yaw=YAW["west"], timeout=60)
        add("step_onto_deck", type="goto", target=W(o, [3, 14, 3]), range=0, timeout=20)
        steps.extend(deck_probes(o, 14, [2, 3], [2, 3], hatch={(2, 2)}))
    elif module == "medium_pillar_1":
        add("tp_outside", type="tp", target=C(o, [3, 1, -3]))
        add("walk_to_entry", type="goto", target=W(o, [3, 1, 1]), range=0, timeout=30)
        add("walk_to_ladder_approach", type="goto", target=W(o, [4, 1, 2]), range=0, timeout=30)
        add("climb_ground_to_deck", type="climb", base=W(o, [4, 1, 3]), top=W(o, [4, 9, 3]), yaw=YAW["east"], timeout=60)
        add("step_onto_deck", type="goto", target=W(o, [3, 9, 4]), range=0, timeout=20)
        steps.extend(deck_probes(o, 9, range(1, 6), range(1, 7), hatch={(4, 3)}))
    # walk steps with "pre" are preceded by a tp to that cell (see below)
    # deck edge walks need a re-centre first: expand into tp + walk
    out = []
    for s in steps:
        if s.get("pre"):
            out.append({"name": s["name"] + "_recentre", "type": "tp", "target": [s["pre"][0] + .5, s["pre"][1], s["pre"][2] + .5]})
            s = {k: v for k, v in s.items() if k != "pre"}
        out.append(s)
    return out


def main(variant="candidate", src_root=None, modules=None):
    src_root = src_root or S24B
    modules = modules or MODULES
    pack = OUT / "_work/pack-gameplay"
    shutil.rmtree(pack, ignore_errors=True)
    write_pack(pack, {m: ("s24c", src_root / m / "restored.nbt") for m in MODULES})
    root = OUT / f"_work/gameplay-server-{variant}"
    srv = Server(root, JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false",
                                   "server-port": str(PORT), "rcon.port": str(RPORT), "gamemode": "survival",
                                   "force-gamemode": "true"}, datapack=pack)
    ops = [{"uuid": offline_uuid("S24C_" + m[:8]), "name": "S24C_" + m[:8], "level": 4, "bypassesPlayerLimit": True} for m in MODULES]
    (root / "ops.json").write_text(json.dumps(ops))
    srv.start()
    report = {}
    try:
        origins = {}
        for i, m in enumerate(MODULES):
            o = [100 + i * 70, ORIGIN_Y, 100]
            origins[m] = o
            srv.cmd(f"forceload add {o[0] - 16} {o[2] - 16} {o[0] + 50} {o[2] + 60}")
        time.sleep(3)
        for m in MODULES:
            o = origins[m]
            print(srv.cmd(f"place template s24c:{m} {o[0]} {o[1]} {o[2]} none"))
        srv.cmd("tick sprint 400")
        time.sleep(10)
        (OUT / "gameplay").mkdir(parents=True, exist_ok=True)
        for m in modules:
            o = origins[m]
            g = derive(m, src_root)
            sc = {"module": m, "port": PORT, "steps": scenario(m, o, g), "global_timeout": 900}
            sp = root / f"scenario-{m}.json"
            rp = OUT / "gameplay" / f"result-{variant}-{m}.json"
            sp.write_text(json.dumps(sc))
            srv.cmd("time set day")
            srv.cmd("gamerule advance_time false") if False else None
            print("=== bot:", m, flush=True)
            proc = subprocess.run(["node", "gameplay_bot.js", str(sp), str(rp)], cwd=BOT_DIR, capture_output=True, text=True, timeout=1000)
            print(proc.stdout[-3000:], proc.stderr[-500:], flush=True)
            if rp.exists():
                res = json.loads(rp.read_text())
                res["origin"] = o
                res["scenario_steps"] = sc["steps"]
                rp.write_text(json.dumps(res, indent=1))
                report[m] = {"ok": sum(1 for s in res["steps"] if s.get("ok")), "total": len(res["steps"]),
                             "failed": [s["name"] for s in res["steps"] if not s.get("ok")]}
            else:
                report[m] = {"error": "no result file", "stderr": proc.stderr[-300:]}
        srv.flush()
        (OUT / "gameplay" / f"summary-{variant}.json").write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1))
    finally:
        srv.stop()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="candidate")
    ap.add_argument("--src", default=None)
    ap.add_argument("--modules", nargs="*", default=None)
    a = ap.parse_args()
    main(a.variant, Path(a.src) if a.src else None, a.modules)
