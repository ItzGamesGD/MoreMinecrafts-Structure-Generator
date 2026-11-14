"""Checks for the F01 commander manor NBT (new file only). Reuses the batch-4 walk engine (feet + head passable, solid
support, step 1, fences / walls / bars not standable, ladders climbable) and the batch-6 probe helpers.

  PYTHONPATH=. python experiments/st03-batch7-commander-manor/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt        independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source), size equals
             the placement-table module size (17x27x15 after Q63), every authored state present in the NBT unchanged
  support    every lantern, wall banner and ladder has the block it needs (hanging lantern: a block with a solid
             underside above it; standing lantern: a solid top below; banner / ladder: a solid block behind)
  access     from the porch entrance ALONE: every container / workstation, every named key point on 1F, 2F, 3F and
             the attic, the rare-reward chest, the commander and armor-stand positions
  stairs     each step of both flights is walkable at both of its two cells (2-wide), with head room
  gallery    no chandelier block in or above a walkable gallery / stair cell (feet or head), the distance from the
             chandelier to the nearest walkable gallery cell, and the U gallery cells reached
  server     strict `place template` on the pinned 26.3 server (rotation none), every cell compared; then a vanilla-AI
             probe with test entities: a 40-HP vindicator (melee, so it must walk; follow range 32 like a pillager)
             started at the commander position and made to chase a NoAI villager on the west gallery, on the hall
             floor (down flight 1) and in the 3F study (up flight 2); a 40-HP
             pillager at the commander position next to a NoAI villager on the hall floor, to see whether it can shoot
             from the war room over the gallery rail. Test entities only - no commander or spawn system is authored.
Rotations, the integrated q=0 layout with every built neighbour, footing and entrance clearance: place_check.py.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import re
import time
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B4C = _load("b4checks", EXP / "st03-batch4-barracks" / "checks.py")
World, passable, reachable = B4C.World, B4C.passable, B4C.reachable
USE_IDS = B4C.USE_IDS | {"cartography_table"}
KEY_POINTS = {
    "1F_hall_centre": (7, 1, 8), "1F_west_guard_bay": (2, 1, 10), "1F_rear_supplies": (7, 1, 2),
    "1F_east_room": (12, 1, 2), "1F_flight1_foot": (10, 1, 11),
    "2F_landing": (12, 7, 4), "2F_war_room": (7, 7, 4), "2F_commander_position": (7, 7, 1),
    "2F_west_gallery_far_end": (2, 7, 11), "2F_rear_gallery_west": (2, 7, 4),
    "3F_arrival": (13, 13, 11), "3F_study": (5, 13, 8), "3F_bedroom": (7, 13, 3), "3F_armor_stand_position": (12, 13, 2),
    "attic_hatch": (3, 19, 6), "attic_lookout_platform": (7, 22, 11), "attic_rear": (7, 19, 2),
}
FLIGHTS = {"flight1_1F_to_2F": [((11, 12), 1 + i, z) for i, z in enumerate((11, 10, 9, 8, 7, 6))],
           "flight2_2F_to_3F": [((13, 14), 7 + i, z) for i, z in enumerate((6, 7, 8, 9, 10, 11))]}
GALLERY = ([(x, 7, z) for x in range(2, 4) for z in range(6, 12)]  # west arm (x=1 holds its storage)
           + [(x, 7, z) for x in range(1, 15) for z in (4,)])  # rear arm / war-room front and landing
SOLID_BAD = ("glass_pane", "iron_bars", "_fence", "_wall", "lantern", "iron_chain", "_carpet", "_button", "ladder",
             "_banner", "_door", "_trapdoor", "air")


def solid(cell):
    return cell is not None and not cell[0].endswith(SOLID_BAD) and not cell[0].endswith("_bed")


def support_problems(cells):
    bad = []
    for (x, y, z), (bid, pr) in cells.items():
        n = bid.split(":")[1]
        if n == "lantern":
            if pr.get("hanging") == "true":
                up = cells.get((x, y + 1, z))
                ok = up is not None and (up[0].endswith(("_fence", "iron_chain")) or (
                    solid(up) and not (up[0].endswith("_slab") and up[1].get("type") == "top")
                    and not (up[0].endswith("_stairs") and up[1].get("half") == "top")) or (
                    up[0].endswith("_stairs") and up[1].get("half") == "bottom") or (
                    up[0].endswith("_slab") and up[1].get("type") == "bottom"))
            else:
                dn = cells.get((x, y - 1, z))
                ok = dn is not None and (dn[0].endswith("_wall") or (solid(dn) and not (
                    dn[0].endswith("_slab") and dn[1].get("type") == "bottom")))
            if not ok:
                bad.append([x, y, z, n])
        elif n in ("white_wall_banner", "ladder"):
            dx, dz = DV[pr["facing"]]
            if not solid(cells.get((x - dx, y, z - dz))):
                bad.append([x, y, z, n])
    return bad


POS = re.compile(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
HP = re.compile(r"(-?[\d.]+)f")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--probe-seconds", type=int, default=45)
    a = ap.parse_args()
    b = _load("batch7_build", HERE / "build.py")
    bd = b.BUILDINGS["manor"]
    module = A.modules()[bd["module"]]
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    nbt, schem = HERE / "out" / f"{module['file']}.nbt", HERE / "out" / f"{module['file']}.schem"
    r = {"server_sha1": sha, "placement": "F01", "module": "M-manor", "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
    problems = []
    s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"), block_entities.load("26.3"))
    assert list(s["size"]) == module["size"] == list(bd["size"]) == [17, 27, 15], s["size"]
    assert s["mismatches"] == 0, s
    r["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                   for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
    cells = _template_cells(nbt)
    src = bd["design"]()
    bad = [list(p) for p, (bid, pr) in src.items()
           if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
    assert not bad, bad[:5]
    r["states"] = {"authored_cells_checked": len(src), "mismatches": 0}
    r["support"] = {"unsupported": support_problems(cells)}
    if r["support"]["unsupported"]:
        problems.append(("support", r["support"]["unsupported"]))

    size = module["size"]
    w = World(cells, size)
    ent = bd["entrances"]["porch_south"]
    reach = w.walk(ent)
    inside = lambda p: 0 <= p[0] <= 15 and 0 <= p[2] <= 12
    use = sorted(p for p, v in cells.items() if v[0].split(":")[1] in USE_IDS and inside(p))
    miss_use = [[*p, cells[p][0]] for p in use if not reachable(reach, p)]
    keys = {k: (p in reach) for k, p in KEY_POINTS.items()}
    floors = {"1F": 1, "2F": 7, "3F": 13, "attic": 19}
    r["access"] = {"entrance": "porch_south", "outside_cell": list(ent),
                   "feet_cells_per_floor": {f: sum(1 for p in reach if p[1] == y and inside(p)) for f, y in floors.items()},
                   "usable_blocks": len(use), "usable_unreached": miss_use, "key_points": keys,
                   "rare_reward_chest_reached": reachable(reach, tuple(bd["rare_reward_chest"]))}
    if miss_use or not all(keys.values()) or not r["access"]["rare_reward_chest_reached"]:
        problems.append(("access", miss_use, {k: v for k, v in keys.items() if not v}))
    # stairs: both cells of every step walkable, with the head room the walk engine requires
    st = {}
    for name, steps in FLIGHTS.items():
        rows = [{"z": z, "step_top_y": y, "cells_walkable": [(x, y + 1, z) in reach for x in xs]} for xs, y, z in steps]
        st[name] = {"width_blocks": 2, "steps": len(rows), "all_cells_walkable": all(all(rw["cells_walkable"]) for rw in rows),
                    "rows": rows}
        if not st[name]["all_cells_walkable"]:
            problems.append(("stairs", name, rows))
    r["stairs"] = st
    # gallery and chandelier
    chand = sorted(p for p, v in cells.items() if 5 <= p[0] <= 10 and 6 <= p[2] <= 11 and 7 <= p[1] <= 11
                   and v[0].split(":")[1] in ("dark_oak_fence", "iron_chain", "lantern"))
    walk_up = {p for p in reach if 7 <= p[1] <= 12}  # 2F gallery and stair feet cells (3F is above the ceiling)
    clash = [list(q) for q in chand for p in walk_up if (q[0], q[2]) == (p[0], p[2]) and q[1] in (p[1], p[1] + 1)]
    dist = min(math.dist((q[0], q[2]), (p[0], p[2])) for q in chand for p in walk_up if abs(q[1] - p[1]) <= 2)
    g_reached = [list(p) for p in GALLERY if p in reach]
    r["gallery_chandelier"] = {"chandelier_blocks": len(chand),
                               "chandelier_lanterns": sum(1 for q in chand if cells[q][0] == "minecraft:lantern"),
                               "blocks_in_walkable_feet_or_head_cells": clash,
                               "closest_horizontal_distance_to_walkable_upper_cell": round(dist, 2),
                               "gallery_cells_listed": len(GALLERY), "gallery_cells_reached": len(g_reached)}
    if clash or len(g_reached) != len(GALLERY):
        problems.append(("gallery", clash, len(g_reached)))
    # entity positions
    ents = {}
    for name in ("commander_spawn", "armor_stand"):
        ex, ey, ez = bd[name]
        bx, by, bz = math.floor(ex), int(ey), math.floor(ez)
        ok = passable(cells.get((bx, by, bz))) and passable(cells.get((bx, by + 1, bz))) and solid(cells.get((bx, by - 1, bz)))
        ents[name] = {"local": [ex, ey, ez], "two_cells_clear_on_solid_floor": ok, "reached": (bx, by, bz) in reach}
        if not ok or not ents[name]["reached"]:
            problems.append(("entity position", name))
    r["entity_positions"] = ents
    r["counts"] = {i: [v[0] for v in cells.values()].count("minecraft:" + i)
                   for i in ("chest", "barrel", "lantern", "white_wall_banner", "dark_oak_door", "ladder")}

    if a.offline:
        print(json.dumps({k: v for k, v in r.items() if k not in ("stairs",)}, default=list)[:3000])
        print("stairs", {k: v["all_cells_walkable"] for k, v in st.items()})
        print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
        return
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch7", "min_format": [121, 0], "max_format": [121, 0]}}))
    (pack / "data/experimental/structure/manor.nbt").write_bytes(nbt.read_bytes())
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 64, 48)
        o = (16, 80, 16)
        reply = server.cmd(f"place template experimental:manor {o[0]} {o[1]} {o[2]} none none 1 0 strict")
        assert reply.startswith("Loaded template"), reply
        fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                 if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
        r["server_strict_placement"] = {"rotation": "none", "cells": len(cells), "failures": fails}
        if fails:
            problems.append(("strict placement", len(fails)))
        r["commander_ai_probe"] = probe(server, bd, a.probe_seconds)
        if not r["commander_ai_probe"]["pass"]:
            problems.append(("commander AI probe",))
    finally:
        server.stop()
    r["problems"] = problems
    (HERE / "check-result.json").write_text(json.dumps(r, indent=1, default=list) + "\n")
    print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
    print("PASS" if not problems else "FAIL")
    raise SystemExit(0 if not problems else 1)


def probe(server, bd, seconds):
    """Vanilla-AI probe on flat ground with test entities (template floor y=0 replaces the grass layer at y=-61)."""
    ox, gy, oz = 200, -61, 16
    forceload(server, ox - 16, oz - 16, ox + 40, oz + 48)
    for c in ("difficulty normal", "gamerule spawn_mobs false", "gamerule doMobSpawning false", "time set noon"):
        server.cmd(c)
    reply = server.cmd(f"place template experimental:manor {ox} {gy} {oz} none none 1 0 strict")
    assert reply.startswith("Loaded template"), reply
    time.sleep(2)
    cx, cy, cz = bd["commander_spawn"]
    trials = []
    hp40 = "attributes:[{id:\"minecraft:max_health\",base:40d}],Health:40f"
    # a vanilla vindicator only looks 12 blocks for a path (pillagers 32); the stand-in gets the pillager's 32
    reach32 = "attributes:[{id:\"minecraft:max_health\",base:40d},{id:\"minecraft:follow_range\",base:32d}],Health:40f"
    # /summon with NBT skips the vanilla spawn equipment, so the weapon is given explicitly
    weapon = {"vindicator": "iron_axe", "pillager": "crossbow"}
    plan = [("vindicator", "west_gallery_far_end", (2.5, 7, 11.5), True),
            ("vindicator", "hall_floor_by_the_door", (7.5, 1, 10.5), True),
            ("vindicator", "3F_study", (5.5, 13, 8.5), True),
            ("pillager", "hall_floor_shot_from_war_room", (7.5, 1, 8.5), False)]
    for mob, label, (tx, ty, tz), resist in plan:
        server.cmd("kill @e[type=minecraft:vindicator]"); server.cmd("kill @e[type=minecraft:pillager]")
        server.cmd("kill @e[type=minecraft:villager]"); server.cmd("kill @e[type=minecraft:arrow]")
        time.sleep(1)
        server.cmd(f"summon minecraft:villager {ox + tx} {gy + ty} {oz + tz} "
                   "{NoAI:1b,PersistenceRequired:1b,Silent:1b,Tags:[\"tgt\"]}")
        if resist:
            server.cmd("effect give @e[tag=tgt] minecraft:resistance infinite 4 true")
        server.cmd(f"summon minecraft:{mob} {ox + cx} {gy + cy} {oz + cz} "
                   f"{{PersistenceRequired:1b,Tags:[\"cmd\"],{reach32 if mob == 'vindicator' else hp40},Rotation:[0f,0f],"
                   f"equipment:{{mainhand:{{id:\"minecraft:{weapon[mob]}\",count:1}}}}}}")
        time.sleep(1)
        hp_start = server.cmd("data get entity @e[tag=cmd,limit=1] Health")
        hurt = server.cmd("damage @e[tag=cmd,limit=1] 0.5 minecraft:mob_attack by @e[tag=tgt,limit=1]")
        v0 = server.cmd("data get entity @e[tag=tgt,limit=1] Health")
        track, best, t0, vhp = [], 1e9, time.time(), None
        while time.time() - t0 < seconds:
            m = POS.search(server.cmd("data get entity @e[tag=cmd,limit=1] Pos"))
            if m:
                x, y, z = (float(v) for v in m.groups())
                lx, ly, lz = round(x - ox, 2), round(y - gy, 2), round(z - oz, 2)
                track.append([round(time.time() - t0, 1), lx, ly, lz])
                best = min(best, math.dist((lx, ly, lz), (tx, ty, tz)))
            hv = HP.search(server.cmd("data get entity @e[tag=tgt,limit=1] Health") or "")
            vhp = float(hv.group(1)) if hv else 0.0
            if resist and best < 2.0:
                break
            if not resist and vhp < 20.0:
                break
            time.sleep(0.25)
        trial = {"test_entity": mob, "max_health_set": 40, "follow_range_set": 32 if mob == "vindicator" else "default (32)", "health_at_start": hp_start, "target": label,
                 "start_local": [cx, cy, cz], "target_local": [tx, ty, tz], "damage_reply": hurt,
                 "closest_distance": round(best, 2), "seconds": track[-1][0] if track else None,
                 "villager_health_start": v0, "villager_health_end": vhp, "track": track}
        if resist:
            trial["pass"] = best < 2.0
        else:
            trial["pass"] = vhp is not None and vhp < 20.0
            trial["stayed_in_war_room"] = all(p[2] >= 6.5 and p[3] <= 5.5 for p in track)
        trials.append(trial)
        print("probe", mob, label, trial["pass"], round(best, 2), vhp, flush=True)
    for e in ("vindicator", "pillager", "villager", "arrow"):
        server.cmd(f"kill @e[type=minecraft:{e}]")
    return {"method": "vanilla 26.3 AI, test entities only: 40-HP vindicator (iron axe; follow range raised from its default 12 to the pillager's 32) / pillager "
                      "(crossbow) summoned at the recorded "
                      "commander position and turned on a NoAI villager with `damage <it> 0.5 minecraft:mob_attack by "
                      "<villager>`; positions sampled every 0.25 s. Melee pass = within 2 blocks of the target "
                      "(villager kept alive by Resistance V); ranged pass = the villager loses health.",
            "placement_origin": [ox, gy, oz], "trials": trials, "pass": all(t["pass"] for t in trials)}


if __name__ == "__main__":
    main()
