"""Checks for the F09 prison / F10 ravager stable NBTs (new files only). Reuses the batch-4 walk engine (feet + head
passable, solid support, step 1, fences / walls / bars not standable, ladders climbable).

  PYTHONPATH=. python experiments/st03-batch6-prison-stable/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt       independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source), size equals
            the placement-table module size, every authored state present in the NBT unchanged
  access    F09: iron doors are CLOSED unless a button the player can reach powers them (button -> the block it is
            attached to -> an adjacent door), iterated to a fixed point from the street entrance alone; every cell,
            bed, the corridor and the vestibule must be reached; the way out from the vestibule and from inside a
            cell is reported. F10: player walk from the portal alone to every container, both pens and the store.
  ravager   F10 geometric clearance for a ravager hitbox (1.95 x 2.2 -> a 2 x 2 x 3 block box): from each recorded
            pen position to open ground outside the portal, with only air / banner / button cells counted as free;
            the 3 x 4 portal and the open pen entries (no door, gate or fence gate) are checked cell by cell
  server    strict `place template` on the pinned 26.3 server (rotation none), every cell compared; then a vanilla-AI
            movement probe: F10 on flat ground, one real ravager per trial made to chase a NoAI villager kept alive
            by Resistance V (`damage ... by` the villager), positions sampled every 0.25 s: pen -> outside and
            outside -> pen for both pens, through the portal. This uses vanilla AI only; it is not a spawn or garrison system.
Rotations, the integrated q=0 layout with every built neighbour, footing and entrance clearance: place_check.py.
The F09 buttons are also pressed by a player in the real client: capture.py (f09_button_test).
"""

import argparse
import hashlib
import importlib.util
import json
import math
import re
import time
from collections import deque
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
DV6 = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0),
       "down": (0, -1, 0)}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B4C = _load("b4checks", EXP / "st03-batch4-barracks" / "checks.py")
passable, reachable = B4C.passable, B4C.reachable
USE_IDS = B4C.USE_IDS | {"composter", "cauldron", "water_cauldron"}
KEY_POINTS = {
    "prison": {"vestibule": (5, 1, 10), "corridor_far_end": (5, 1, 1), "cell_nw": (3, 1, 2), "cell_ne": (7, 1, 2),
               "cell_sw": (3, 1, 6), "cell_se": (7, 1, 6)},
    "stable": {"aisle_mid": (8, 1, 6), "west_pen": (3, 1, 7), "east_pen": (13, 1, 7), "aisle_head_store": (8, 1, 3)},
}
RAVAGER_FREE = ("minecraft:air", "minecraft:white_wall_banner")


class World(B4C.World):
    """batch-4 walk engine; iron doors are passable only when listed in `open_doors` (x, z)."""

    def __init__(self, cells, size, open_doors=()):
        super().__init__(cells, size)
        self.open_doors = set(open_doors)

    def at(self, x, y, z):
        c = super().at(x, y, z)
        if c is not None and c[0] == "minecraft:iron_door" and (x, z) not in self.open_doors:
            return ("minecraft:stone", {})
        return c


def walls_fn(bd):
    return lambda p: not any(x0 <= p[0] <= x1 and z0 <= p[2] <= z1 for x0, x1, z0, z1 in bd["walls"])


def button_map(cells):
    """button pos -> iron door columns it opens: the button powers the block it is attached to, which powers the
    doors next to it; the button also powers doors directly next to itself."""
    doors = {(x, z) for (x, y, z), v in cells.items() if v[0] == "minecraft:iron_door"}
    out = {}
    for p, (bid, pr) in cells.items():
        if not bid.endswith("_button"):
            continue
        assert pr.get("face") == "wall", (p, pr)
        d = DV6[pr["facing"]]
        att = (p[0] - d[0], p[1] - d[1], p[2] - d[2])
        hit = set()
        for src in (att, p):
            for e in DV6.values():
                q = (src[0] + e[0], src[1] + e[1], src[2] + e[2])
                if cells.get(q, ("",))[0] == "minecraft:iron_door":
                    hit.add((q[0], q[2]))
        out[p] = {"attached_to": att, "opens": sorted(hit)}
        assert hit <= doors
    return out


def walk_with_buttons(cells, size, start, buttons, ring=False, allowed=lambda p: True):
    """Fixed point: walk; every button within reach opens its doors; walk again."""
    open_doors, used = set(), []
    while True:
        w = World(cells, size, open_doors)
        reach = {p for p in w.walk(start, ring=ring) if allowed(p)}
        new = set()
        for b, info in buttons.items():
            if reachable(reach, b) and not set(info["opens"]) <= open_doors:
                new |= set(info["opens"]); used.append(list(b))
        if not new:
            return reach, open_doors, used
        open_doors |= new


def ravager_clearance(cells, size, spawn):
    """2x2x3 box search (ravager 1.95 wide, 2.2 tall) on the flat floor y=1; the box is keyed by its min corner."""
    W, _, D = size

    def free(x, y, z):
        if 0 <= x < W and 0 <= z < D:
            v = cells.get((x, y, z))
            return v is None or v[0] in RAVAGER_FREE or v[0].endswith("_button")
        return True

    def floor(x, z):
        if 0 <= x < W and 0 <= z < D:
            v = cells.get((x, 0, z))
            return v is not None and not passable(v)
        return True

    def fits(x, z):
        return all(free(x + i, y, z + k) and floor(x + i, z + k) for i in (0, 1) for k in (0, 1) for y in (1, 2, 3))

    cx, _, cz = spawn
    s = (math.floor(cx - 0.975), math.floor(cz - 0.975))
    if not fits(*s):
        return {"spawn_fits": False}
    prev, q = {s: None}, deque([s])
    goal = None
    while q:
        x, z = q.popleft()
        if z >= D:  # whole box on open ground beyond the street face
            goal = (x, z)
            break
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (nx, nz) in prev or not (-3 <= nx <= W + 1 and -3 <= nz <= D + 1) or not fits(nx, nz):
                continue
            # leaving the footprint is only allowed across the street face (z >= D-1), never round the sides
            if not (0 <= nx < W - 1 and 0 <= nz) and nz < D - 1:
                continue
            prev[(nx, nz)] = (x, z); q.append((nx, nz))
    path = []
    n = goal
    while n is not None:
        path.append(list(n)); n = prev[n]
    inside = [p for p in prev if 0 <= p[0] and p[0] + 1 < W and 0 <= p[1] and p[1] + 1 < D]
    return {"spawn_fits": True, "box_min_corner": list(s), "reaches_outside": goal is not None,
            "path_box_positions": len(path), "path": path[::-1], "box_positions_reachable_inside": len(inside)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true", help="skip the server step (design iteration only)")
    ap.add_argument("--probe-seconds", type=int, default=45)
    a = ap.parse_args()
    b = _load("batch6_build", HERE / "build.py")
    mods = A.modules()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    result = {"server_sha1": sha}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch6", "min_format": [121, 0], "max_format": [121, 0]}}))
    per, tcells, problems = {}, {}, []
    for key, bd in b.BUILDINGS.items():
        module = mods[bd["module"]]
        nbt, schem = HERE / "out" / f"{module['file']}.nbt", HERE / "out" / f"{module['file']}.schem"
        r = {"placement": bd["placement"], "module": bd["module"], "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"] == list(bd["size"]), s["size"]
        assert s["mismatches"] == 0, s
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = _template_cells(nbt)
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        assert not bad, (key, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0}
        size = module["size"]
        outside = walls_fn(bd)
        use = sorted(p for p, v in cells.items() if v[0].split(":")[1] in USE_IDS)
        ext = [p for p in use if outside(p)]
        btn = button_map(cells)
        ent_name, ent = next(iter(bd["entrances"].items()))
        reach, opened, used = walk_with_buttons(cells, size, ent, btn)
        inner = {p for p in reach if 0 <= p[0] < size[0] and 0 <= p[2] < size[2] and not outside(p)}
        miss_use = [[*p, cells[p][0]] for p in use if not outside(p) and not reachable(reach, p)]
        keys = {k: (p in reach) for k, p in KEY_POINTS[key].items()}
        beds = sorted(p for p, v in cells.items() if v[0].endswith("_bed") and v[1].get("part") == "head")
        acc = {"entrance": ent_name, "outside_cell": list(ent), "interior_feet_cells": len(inner),
               "usable_blocks_inside": len(use) - len(ext), "usable_unreached": miss_use, "key_points": keys,
               "beds_reached": {str(list(p)): reachable(reach, p) for p in beds}}
        ring = World(cells, size, opened).walk(ent, ring=True)
        miss_ext = [[*p, cells[p][0]] for p in ext if not reachable(ring, p)]
        acc["exterior_supplies"] = {"usable_on_apron": len(ext), "unreached_from_open_ground": miss_ext}
        if miss_use or not all(keys.values()) or not all(acc["beds_reached"].values()) or miss_ext:
            problems.append((key, "access", miss_use, keys, miss_ext))
        if btn:
            iron = sorted({(x, z) for (x, y, z), v in cells.items() if v[0] == "minecraft:iron_door"})
            acc["iron_doors"] = [list(d) for d in iron]
            acc["buttons"] = {str(list(p)): {"attached_to": list(i["attached_to"]), "opens": [list(d) for d in i["opens"]]}
                              for p, i in sorted(btn.items())}
            acc["doors_opened_from_the_street"] = sorted(list(d) for d in opened)
            acc["buttons_used"] = used
            if set(opened) != set(iron):
                problems.append((key, "iron doors not all openable", sorted(set(iron) - opened)))
            # the way out: from the vestibule, and from inside each cell with only the buttons reachable there
            vest = KEY_POINTS[key]["vestibule"]
            rv, ov, _ = walk_with_buttons(cells, size, (vest[0], vest[2]), btn, ring=True)
            acc["exit_from_vestibule"] = (ent[0], 1, ent[1]) in rv or (ent[0], 1, ent[1] - 1) in rv
            if not acc["exit_from_vestibule"]:
                problems.append((key, "cannot leave from the vestibule"))
            cell_exit = {}
            for k in ("cell_nw", "cell_ne", "cell_sw", "cell_se"):
                p = KEY_POINTS[key][k]
                rc, oc, _ = walk_with_buttons(cells, size, (p[0], p[2]), btn)
                cell_exit[k] = {"can_leave_cell_without_help": any(q[0] == 5 for q in rc), "doors_it_can_open": sorted(oc)}
            acc["from_inside_a_closed_cell"] = cell_exit
        r["access"] = acc
        ids = [v[0].split(":")[1] for v in cells.values()]
        r["counts"] = {i: ids.count(i) for i in ("chest", "barrel", "hay_block", "composter", "water_cauldron",
                                                  "cauldron", "lantern", "iron_door", "iron_bars", "stone_button")
                       if ids.count(i)}
        if key == "prison":
            r["counts"]["beds"] = len(beds)
        if key == "stable":
            rav = {}
            for name, sp in bd["ravager_spawns"].items():
                rav[name] = {"spawn_centre_local": list(sp), **ravager_clearance(cells, size, sp)}
                if not rav[name].get("reaches_outside"):
                    problems.append((key, "ravager", name, rav[name]))
            portal = [[x, y, z, cells.get((x, y, z), ("air",))[0]] for x in (7, 8, 9) for y in (1, 2, 3, 4)
                      for z in (11, 12) if cells.get((x, y, z), ("minecraft:air",))[0] != "minecraft:air"]
            entries = [[x, y, z, cells.get((x, y, z), ("air",))[0]] for x in (6, 10) for y in (1, 2, 3)
                       for z in (5, 6, 7) if cells.get((x, y, z), ("minecraft:air",))[0] != "minecraft:air"]
            closers = [[*p, v[0]] for p, v in cells.items()
                       if v[0].endswith(("_door", "_fence_gate")) or (v[0].endswith("_trapdoor") and 2 <= p[0] <= 14
                                                                       and 2 <= p[2] <= 10)]
            rav["portal_clear_3_wide_4_high"] = {"cells": "x7..9, y1..4, z11..12", "blocked": portal}
            rav["pen_entries_open_3_wide"] = {"cells": "x=6 / x=10, y1..3, z5..7", "blocked": entries}
            rav["doors_gates_inside"] = closers
            if portal or entries or closers:
                problems.append((key, "openings", portal, entries, closers))
            r["ravager_space"] = rav
        per[key] = r
        tcells[key] = cells
        (pack / f"data/experimental/structure/{key}.nbt").write_bytes(nbt.read_bytes())

    if a.offline:
        for k, v in per.items():
            acc = {x: y for x, y in v["access"].items() if x not in ("buttons", "iron_doors")}
            rav = {n: ({x: y for x, y in r.items() if x != "path"} if isinstance(r, dict) else r)
                   for n, r in v.get("ravager_space", {}).items()}
            print(k, json.dumps({"access": acc, "counts": v["counts"], "ravager": rav}, default=list))
        print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
        return
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 120, 48)
        for i, (key, cells) in enumerate(tcells.items()):
            o = (16 + i * 48, 80, 16)
            reply = server.cmd(f"place template experimental:{key} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), (key, reply)
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
            per[key]["server_strict_placement"] = {"rotation": "none", "cells": len(cells), "failures": fails}
        result["ravager_ai_probe"] = probe(server, b.BUILDINGS["stable"], a.probe_seconds)
        if not result["ravager_ai_probe"]["pass"]:
            problems.append(("stable", "ravager AI probe"))
    finally:
        server.stop()
    result["buildings"] = per
    result["problems"] = problems
    (HERE / "check-result.json").write_text(json.dumps(result, indent=1, default=list) + "\n")
    bad = {k: len(v["server_strict_placement"]["failures"]) for k, v in per.items()}
    if problems:
        print("PROBLEMS", json.dumps(problems, default=list))
    ok = not any(bad.values()) and not problems
    print("PASS" if ok else f"FAIL {bad}")
    raise SystemExit(0 if ok else 1)


def crossing_x(p, q, z_line=11.5, x0=6.5, x1=10.5):
    """True when the straight segment between two samples crosses the portal line z=11.5 inside x 6.5..10.5."""
    (za, xa), (zb, xb) = (p[3], p[1]), (q[3], q[1])
    if (za - z_line) * (zb - z_line) > 0 or za == zb:
        return False
    x = xa + (xb - xa) * (z_line - za) / (zb - za)
    return x0 <= x <= x1


POS = re.compile(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")


def probe(server, bd, seconds):
    """Vanilla-AI movement probe on flat ground (template floor y=0 replaces the grass layer at y=-61)."""
    ox, gy, oz = 200, -61, 16
    forceload(server, ox - 16, oz - 16, ox + 40, oz + 48)
    for c in ("difficulty easy", "gamerule spawn_mobs false", "gamerule doMobSpawning false", "time set noon"):
        server.cmd(c)
    reply = server.cmd(f"place template experimental:stable {ox} {gy} {oz} none none 1 0 strict")
    assert reply.startswith("Loaded template"), reply
    time.sleep(2)
    fy = gy + 1
    outside = (8.5, 22.5)
    trials = []
    for pen, (sx, _, sz) in bd["ravager_spawns"].items():
        for direction in ("pen_to_outside", "outside_to_pen"):
            server.cmd("kill @e[type=minecraft:ravager]"); server.cmd("kill @e[type=minecraft:villager]")
            time.sleep(1)
            (rx, rz), (tx, tz) = ((sx, sz), outside) if direction == "pen_to_outside" else (outside, (sx, sz))
            server.cmd(f"summon minecraft:villager {ox + tx} {fy} {oz + tz} "
                       "{NoAI:1b,PersistenceRequired:1b,Silent:1b,Tags:[\"tgt\"]}")
            # an Invulnerable entity is never a valid target in vanilla, so the villager is kept alive with
            # Resistance V (immune to the ravager's bite) instead
            server.cmd("effect give @e[tag=tgt] minecraft:resistance infinite 4 true")
            server.cmd(f"summon minecraft:ravager {ox + rx} {fy} {oz + rz} {{PersistenceRequired:1b,Tags:[\"rv\"]}}")
            time.sleep(1)
            hurt = server.cmd("damage @e[tag=rv,limit=1] 0.5 minecraft:mob_attack by @e[tag=tgt,limit=1]")
            track, best, t0 = [], 1e9, time.time()
            while time.time() - t0 < seconds:
                m = POS.search(server.cmd("data get entity @e[tag=rv,limit=1] Pos"))
                if m:
                    x, y, z = (float(v) for v in m.groups())
                    lx, lz = round(x - ox, 2), round(z - oz, 2)
                    track.append([round(time.time() - t0, 1), lx, round(y - fy, 2), lz])
                    best = min(best, math.hypot(lx - tx, lz - tz))
                    if best < 2.5:
                        break
                time.sleep(0.25)
            hp = server.cmd("data get entity @e[tag=rv,limit=1] Health")
            via_portal = any(crossing_x(p, q) for p, q in zip(track, track[1:]))
            trials.append({"pen": pen, "direction": direction, "ravager_start_local": [rx, 1, rz],
                           "target_local": [tx, 1, tz], "damage_reply": hurt, "closest_distance": round(best, 2),
                           "reached_target": best < 2.5, "passed_through_portal": via_portal,
                           "seconds": track[-1][0] if track else None, "health_after": hp, "track": track})
            print("probe", pen, direction, best, via_portal, flush=True)
    server.cmd("kill @e[type=minecraft:ravager]"); server.cmd("kill @e[type=minecraft:villager]")
    return {"method": "vanilla 26.3 AI: one ravager per trial, made to chase a NoAI villager (Resistance V) with "
                      "`damage <ravager> 0.5 minecraft:mob_attack by <villager>`; Pos sampled every 0.25 s; pass = "
                      "within 2.5 blocks of the target, and the track crosses the portal line z=11.5 within x 6.5..10.5",
            "placement_origin": [ox, gy, oz], "trials": trials,
            "pass": all(t["reached_target"] and t["passed_through_portal"] for t in trials)}


if __name__ == "__main__":
    main()
