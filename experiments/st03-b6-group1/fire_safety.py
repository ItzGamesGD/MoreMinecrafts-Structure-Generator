"""Kitchen hearth fire safety on the pinned 26.3 server (vanilla fire rules, fire tick ON).

  PYTHONPATH=. python <dir>/fire_safety.py --server-jar server.jar --java java25 --work <empty dir> [--nbt st03_kitchen.nbt] [--ticks 4000]
Places the template flush with the flat-world ground, checks the fire-tick game rule, runs `tick sprint <ticks>` (the fire
block's scheduled ticks and spread rolls run at full speed) and compares EVERY cell with the template: anything the fire
burned or ignited is a failure. Also reports the analytic reach: flammable template blocks within the fire's spread
reach (dx, dz +-2, dy -2..+5 of each fire block). Writes <dir>/fire-safety-result.json.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from tools.structure_export.live import _at, _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
# FireBlock burn odds > 0 in vanilla (wood family, wool, hay, bookshelf, leaves, vines, carpets ...). Barrels, chests,
# crafting tables, furnaces, stone, cauldrons, lanterns, glass, iron bars are NOT flammable.
FLAMMABLE = re.compile(
    r"(_planks|_log|_wood|_stairs|_slab|_fence|_fence_gate|_door|_trapdoor|_carpet|_wool|hay_block|bookshelf|_leaves|"
    r"lectern|_banner|vine|scaffolding|bamboo|dried_kelp|composter|loom|_sign|barrel)$"
)
STONE_STAIRS_SLABS = re.compile(r"(stone|brick|cobble|deepslate|andesite|granite|diorite|blackstone|quartz|sandstone|tuff|prismarine|nether|purpur|mud|copper|tile)")


def flammable(bid):
    n = bid.removeprefix("minecraft:")
    if n in ("barrel", "lectern", "composter", "loom"):  # wooden but NOT in FireBlock's flammable registry
        return False
    if n.endswith(("_stairs", "_slab", "_fence", "_fence_gate")) and STONE_STAIRS_SLABS.search(n):
        return False
    return bool(FLAMMABLE.search(n)) and not n.endswith(("nether_brick_fence",))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--nbt", type=Path, default=HERE / "st03_kitchen.nbt")
    ap.add_argument("--ticks", type=int, default=4000)
    ap.add_argument("--relight", action="store_true", help="re-place each fire block after the template (worst case: a player relights it; the placed fire never ticks by itself)")
    ap.add_argument("--out", type=Path, default=HERE / "fire-safety-result.json")
    a = ap.parse_args()
    cells = _template_cells(a.nbt)
    fires = [p for p, (b, _) in cells.items() if b == "minecraft:fire"]
    res = {"nbt": a.nbt.name, "nbt_sha256": hashlib.sha256(a.nbt.read_bytes()).hexdigest(), "fire_blocks": [list(p) for p in fires]}
    near = []
    for fx, fy, fz in fires:
        for (x, y, z), (b, _) in cells.items():
            if abs(x - fx) <= 2 and abs(z - fz) <= 2 and -2 <= y - fy <= 5 and flammable(b):
                near.append({"fire": [fx, fy, fz], "flammable": [x, y, z], "block": b})
    res["flammable_within_spread_reach"] = near
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "data/experimental/structure/k.nbt").write_bytes(a.nbt.read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps({"pack": {"description": "fire", "min_format": [121, 0], "max_format": [121, 0]}}))
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 48, 48)
        # 26.3 replaced doFireTick by fire_spread_radius_around_player (spread only within that radius of a player;
        # -1 = unlimited). The headless server has no player, so the radius is set to unlimited: same fire rules as a
        # player standing next to the kitchen.
        res["gamerule_default"] = server.cmd("gamerule fire_spread_radius_around_player")
        res["gamerule_set"] = server.cmd("gamerule fire_spread_radius_around_player -1")
        res["gamerule_now"] = server.cmd("gamerule fire_spread_radius_around_player")
        o = (16, -61, 16)
        assert server.cmd(f"place template experimental:k {o[0]} {o[1]} {o[2]} none none 1 0 strict").startswith("Loaded")
        # positive control: fire on netherrack beside a plank wall far from the kitchen must burn it (proves fire ticks run)
        server.cmd("fill 40 -60 40 40 -57 42 minecraft:oak_planks")
        server.cmd("setblock 39 -61 41 minecraft:netherrack")
        server.cmd("setblock 39 -60 41 minecraft:fire")
        # control 2: the kitchen geometry in miniature - a plank 4 above and 1 beside the fire, reachable only through an
        # air cell (the spread rule: ignite an AIR cell dx,dz +-1, dy -1..4 that has a flammable neighbour)
        server.cmd("fill 60 -61 60 60 -61 60 minecraft:netherrack")
        server.cmd("setblock 60 -60 60 minecraft:fire")
        server.cmd("setblock 60 -56 59 minecraft:dark_oak_planks")
        server.cmd("setblock 60 -56 58 minecraft:cobblestone")
        res["relight"] = a.relight
        if a.relight:
            for f in fires:
                p = _at(o, f, "none")
                server.cmd(f"setblock {p[0]} {p[1]} {p[2]} minecraft:air")
                server.cmd(f"setblock {p[0]} {p[1]} {p[2]} minecraft:fire")
        res["tick_sprint"] = server.cmd(f"tick sprint {a.ticks}")
        # wait for the sprint to finish: it reports when done; poll a harmless command
        import time

        for _ in range(600):
            q = server.cmd("tick query")
            if "sprinting" not in q.lower() or "normally" in q.lower():
                break
            time.sleep(1)
        res["tick_query_after"] = server.cmd("tick query")
        res["fire_still_burning"] = [("passed" in server.cmd(f"execute if block {_at(o, f, 'none')[0]} {_at(o, f, 'none')[1]} {_at(o, f, 'none')[2]} minecraft:fire")) for f in fires]
        changed = []
        for pos, (bid, props) in sorted(cells.items()):
            p = _at(o, pos, "none")
            want = "minecraft:fire" if bid == "minecraft:fire" else _text(bid, props)  # fire's age legitimately changes
            if "passed" not in server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} {want}"):
                changed.append({"pos": list(pos), "expected": _text(bid, props)})
        # cells the template leaves as air inside the box that fire may have filled
        extra = []
        w, h, d = 9, 11, 9
        for x in range(-1, w + 1):
            for y in range(-1, h + 3):
                for z in range(-1, d + 1):
                    if (x, y, z) in cells and cells[(x, y, z)][0] != "minecraft:air":
                        continue
                    p = _at(o, (x, y, z), "none")
                    if "passed" in server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} minecraft:fire"):
                        extra.append([x, y, z])
        res["control_planks_remaining"] = sum(
            "passed" in server.cmd(f"execute if block 40 {y} {z} minecraft:oak_planks") for y in range(-60, -56) for z in range(40, 43)
        )  # of 12; < 12 means the control fire spread
        res["control2_plank_survived"] = "passed" in server.cmd("execute if block 60 -56 59 minecraft:dark_oak_planks")
        for f in fires:
            p = _at(o, f, "none")
            res["fire_age15"] = "passed" in server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} minecraft:fire[age=15]")
            res["fire_age0"] = "passed" in server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} minecraft:fire[age=0]")
        res["control2_fire_age15"] = "passed" in server.cmd("execute if block 60 -60 60 minecraft:fire[age=15]")
        res["cells_checked"] = len(cells)
        res["changed_cells"] = changed
        res["extra_fire_outside_template_fire"] = extra
    finally:
        server.stop()
    ok = not changed and not [e for e in extra if e not in [list(f) for f in fires]]
    res["result"] = "PASS" if ok else "FAIL"
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(res["result"], len(near), "flammable in reach;", len(changed), "changed cells")


if __name__ == "__main__":
    main()
