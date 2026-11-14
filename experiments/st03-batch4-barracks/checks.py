"""Checks for the F02/F03/F04 barracks NBTs (new files only).

  PYTHONPATH=. python experiments/st03-batch4-barracks/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt     independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source), size equals the
          placement-table module size (13x12x11), every authored state present in the NBT unchanged
  access  3-D walk search on the NBT cells (feet + head cell passable, solid support below, step up/down 1, fences /
          walls / bars cannot be stood on; ladders are climbable). The entrance is tested ALONE: the search may not use
          any ground outside the template except that entrance cell. Must reach: every container and workstation, every
          ground-floor / loft bed, the loft floor (named "key points"), and the full central aisle.
  server  strict `place template` on the pinned 26.3 server (rotation none), every cell compared.
Rotations, the integrated q=0 layout with all built neighbours, footing and entrance clearance are checked by
experiments/st03-placement-check/place_check.py --only M-barracks_a,M-barracks_b,M-barracks_c.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import deque
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells
from tools.structure_export.stair_live import forceload, make_server
from tools.structure_export.live import _text

HERE = Path(__file__).resolve().parent
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OUT = HERE / "out"
PASS_IDS = {"minecraft:air", "minecraft:lantern", "minecraft:soul_lantern", "minecraft:white_wall_banner",
            "minecraft:short_grass", "minecraft:fern", "minecraft:tripwire_hook", "minecraft:lever",
            "minecraft:heavy_weighted_pressure_plate", "minecraft:ladder", "minecraft:candle"}
NO_STAND_ON = ("_fence", "_wall", "iron_bars", "_door", "lightning_rod", "iron_chain", "glass_pane", "ladder")
USE_IDS = {"chest", "barrel", "furnace", "crafting_table", "smithing_table", "fletching_table", "grindstone"}
# points that must be walkable feet cells (loft and the far end of each building)
KEY_POINTS = {
    "barracks_a": {"loft": (3, 5, 5), "mess_under_loft": (3, 1, 5), "aisle_mid": (8, 1, 5)},
    "barracks_b": {"loft": (10, 5, 5), "armoury_under_loft": (10, 1, 5), "gate": (1, 1, 5), "aisle_mid": (8, 1, 5)},
    "barracks_c": {"loft": (9, 6, 5), "beds_under_loft": (9, 1, 5), "stair_top": (6, 6, 7), "aisle_mid": (4, 1, 5)},
}


def load_build():
    spec = importlib.util.spec_from_file_location("batch4_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def passable(cell):
    if cell is None:
        return True
    bid = cell[0]
    return bid in PASS_IDS or bid.endswith(("_carpet", "_door", "_pressure_plate", "_button")) or (
        bid.endswith("_trapdoor") and cell[1].get("open") == "true")


def supports(cell):
    if cell is None:
        return False
    return not passable(cell) and not cell[0].endswith(NO_STAND_ON)


def is_ladder(cell):
    return cell is not None and cell[0] == "minecraft:ladder"


class World:
    def __init__(self, cells, size):
        self.cells, self.size = cells, size

    def inside(self, x, z):
        return 0 <= x < self.size[0] and 0 <= z < self.size[2]

    def at(self, x, y, z):
        if self.inside(x, z) and y >= 0:
            return self.cells.get((x, y, z))
        return ("minecraft:stone", {}) if y <= 0 else None

    def ok(self, x, y, z):
        if not (passable(self.at(x, y, z)) and passable(self.at(x, y + 1, z))):
            return False
        return supports(self.at(x, y - 1, z)) or is_ladder(self.at(x, y, z)) or is_ladder(self.at(x, y - 1, z))

    def walk(self, start, ring=False):
        """BFS from `start`; outside the template only `start` may be used, or (ring=True) the open ground ring
        one block around the footprint (for supplies stacked on the apron outside the walls)."""
        sx, sz = start
        seen, q = set(), deque()
        for y in range(1, 4):
            if self.ok(sx, y, sz):
                seen.add((sx, y, sz)); q.append((sx, y, sz))
        while q:
            x, y, z = q.popleft()
            nxt = []
            for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if not self.inside(nx, nz) and (nx, nz) != start and not (
                        ring and -1 <= nx <= self.size[0] and -1 <= nz <= self.size[2]):
                    continue
                for ny in (y, y + 1, y - 1):
                    if ny == y + 1 and not passable(self.at(x, y + 2, z)):
                        continue
                    if ny >= 1 and self.ok(nx, ny, nz):
                        nxt.append((nx, ny, nz))
                        break
            if is_ladder(self.at(x, y, z)) or is_ladder(self.at(x, y - 1, z)):
                for ny in (y + 1, y - 1):
                    if ny >= 1 and self.ok(x, ny, z):
                        nxt.append((x, ny, z))
            for p in nxt:
                if p not in seen:
                    seen.add(p); q.append(p)
        return seen


def reachable(reach, pos):
    """A block is usable when the player stands next to it (4-neighbour) with feet between 2 below and 1 above it,
    or directly on top of the block below it is not required: within normal 4.5-block reach of the eyes."""
    x, y, z = pos
    return any((x + dx, sy, z + dz) in reach for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
               for sy in (y - 2, y - 1, y, y + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    b = load_build()
    mods = A.modules()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    result = {"server_sha1": sha}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch4", "min_format": [121, 0], "max_format": [121, 0]}}))
    per, tcells, problems = {}, {}, []
    for key, bd in b.BUILDINGS.items():
        module = mods[bd["module"]]
        nbt, schem = OUT / f"{module['file']}.nbt", OUT / f"{module['file']}.schem"
        r = {"placement": bd["placement"], "module": bd["module"], "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"] == [13, 12, 11], s["size"]
        assert s["mismatches"] == 0, s
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = _template_cells(nbt)
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        assert not bad, (key, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0}
        w = World(cells, module["size"])
        use = sorted(p for p, v in cells.items() if v[0].split(":")[1] in USE_IDS)
        beds = sorted(p for p, v in cells.items() if v[0].endswith("_bed") and v[1].get("part") == "head"
                      and not (cells.get((p[0], p[1] - 1, p[2]), ("",))[0].endswith("_slab")))  # not upper bunks
        upper = sorted(p for p, v in cells.items() if v[0].endswith("_bed") and v[1].get("part") == "head"
                       and p not in beds)
        foot = lambda p: tuple(q - d for q, d in zip(p, (DV[cells[p][1]["facing"]][0], 0, DV[cells[p][1]["facing"]][1])))
        wx0, wx1, wz0, wz1 = bd["walls"]
        outside = lambda p: not (wx0 <= p[0] <= wx1 and wz0 <= p[2] <= wz1)
        ring = w.walk(next(iter(bd["entrances"].values())), ring=True)
        ext = [p for p in use if outside(p)]
        miss_ext = [[*p, cells[p][0]] for p in ext if not reachable(ring, p)]
        r["exterior_supplies"] = {"usable_on_apron": len(ext), "unreached_from_open_ground": miss_ext}
        if miss_ext:
            problems.append((key, "exterior", miss_ext))
        acc = {}
        for name, ent in bd["entrances"].items():
            reach = w.walk(ent)
            inner = {p for p in reach if w.inside(p[0], p[2])}
            miss_use = [[*p, cells[p][0]] for p in use if not outside(p) and not reachable(reach, p)]
            miss_bed = [list(p) for p in beds if not (reachable(reach, p) or reachable(reach, foot(p)))]
            keys = {k: (p in reach) for k, p in KEY_POINTS[key].items()}
            loft = sorted({p for p in inner if p[1] >= 5})
            acc[name] = {"outside_cell": list(ent), "interior_feet_cells": len(inner), "loft_feet_cells": len(loft),
                         "usable_blocks_inside": len(use) - len(ext), "usable_unreached": miss_use,
                         "beds_reachable": len(beds) - len(miss_bed), "beds_unreached": miss_bed,
                         "key_points": keys}
            if miss_use or miss_bed or not all(keys.values()):
                problems.append((key, name, miss_use, miss_bed, keys))
        r["access"] = acc
        r["counts"] = {"beds_total": len(beds) + len(upper), "beds_floor_or_loft": len(beds), "upper_bunk_beds": len(upper),
                       "chests": sum(v[0] == "minecraft:chest" for v in cells.values()),
                       "barrels": sum(v[0] == "minecraft:barrel" for v in cells.values()),
                       "ladders": sum(v[0] == "minecraft:ladder" for v in cells.values())}
        per[key] = r
        tcells[key] = cells
        (pack / f"data/experimental/structure/{key}.nbt").write_bytes(nbt.read_bytes())

    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 160, 48)
        for i, (key, cells) in enumerate(tcells.items()):
            o = (16 + i * 48, 80, 16)
            reply = server.cmd(f"place template experimental:{key} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), (key, reply)
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
            per[key]["server_strict_placement"] = {"rotation": "none", "cells": len(cells), "failures": fails}
    finally:
        server.stop()
    result["buildings"] = per
    (HERE / "check-result.json").write_text(json.dumps(result, indent=1) + "\n")
    bad = {k: len(v["server_strict_placement"]["failures"]) for k, v in per.items()}
    if problems:
        print("ACCESS PROBLEMS", json.dumps(problems, default=list))
    ok = not any(bad.values()) and not problems
    print("PASS" if ok else f"FAIL {bad}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
