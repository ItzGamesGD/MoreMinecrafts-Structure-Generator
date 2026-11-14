"""Checks for the F05 armory and F06 training yard NBTs (new files only).

  PYTHONPATH=. python experiments/st03-batch3-military/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt        independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source), size equals
             the placement-table module size, every authored state present in the NBT unchanged
  access     3-D walk search on the NBT cells (feet cell + head cell passable, solid support below, step up/down 1,
             fences/walls cannot be stepped on or over). Each entrance is tested ALONE: the search may not use any
             ground outside the template except that one entrance cell, so a reached block proves that entrance.
             Every interactive block and every container (all chests/barrels in the NBT) must be within reach.
  adjacency  F05 and F06 joined at their real q=0 offset (yard = armory + (0, 0, 13)); from the yard's road gate
             alone the search must reach the armory's premium chest through the loggia bay, and from the armory's
             tower portal alone it must reach the three targets; the bay/apron pair must be walkable on both sides.
  premium    the F05 premium slot is a single chest, the only chest in the strongroom; contents are not authored.
  server     strict `place template` on the pinned 26.3 server (rotation none), every cell compared.
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
from tools.structure_export.live import _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PASS_IDS = {"minecraft:air", "minecraft:lantern", "minecraft:soul_lantern", "minecraft:wall_torch",
            "minecraft:white_wall_banner", "minecraft:short_grass", "minecraft:fern", "minecraft:tripwire_hook",
            "minecraft:lever", "minecraft:heavy_weighted_pressure_plate"}
NO_STAND_ON = ("_fence", "_wall", "iron_bars", "_door", "lightning_rod", "iron_chain")
YARD_OFFSET = (0, 0, 13)


def load_build():
    spec = importlib.util.spec_from_file_location("batch3_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def passable(cell):
    if cell is None:
        return True
    bid = cell[0]
    return bid in PASS_IDS or bid.endswith(("_carpet", "_door", "_pressure_plate", "_button"))


def supports(cell):
    if cell is None:
        return False
    bid = cell[0]
    return not passable(cell) and not bid.endswith(NO_STAND_ON)


class World:
    """Cells of one or more templates in a shared frame; everything else is open flat ground (solid at y<=0)."""

    def __init__(self, parts):
        self.cells, self.boxes = {}, []
        for cells, size, (ox, oy, oz) in parts:
            for (x, y, z), v in cells.items():
                self.cells[(x + ox, y + oy, z + oz)] = v
            self.boxes.append((ox, oz, ox + size[0] - 1, oz + size[2] - 1, size[1]))

    def inside(self, x, z):
        return any(b[0] <= x <= b[2] and b[1] <= z <= b[3] for b in self.boxes)

    def at(self, x, y, z):
        if self.inside(x, z) and y >= 0:
            return self.cells.get((x, y, z))  # air cells of an air=include template are explicit or absent
        return ("minecraft:stone", {}) if y <= 0 else None

    def stand(self, x, y, z):
        return passable(self.at(x, y, z)) and passable(self.at(x, y + 1, z)) and supports(self.at(x, y - 1, z))

    def walk(self, start, allowed_outside):
        """BFS over feet cells; outside the template boxes only `allowed_outside` columns may be used."""
        sx, sz = start
        seen = set()
        q = deque()
        for y in range(1, 4):
            if self.stand(sx, y, sz):
                seen.add((sx, y, sz)); q.append((sx, y, sz))
        while q:
            x, y, z = q.popleft()
            for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if not self.inside(nx, nz) and (nx, nz) not in allowed_outside:
                    continue
                for ny in (y, y + 1, y - 1):
                    if (nx, ny, nz) in seen or ny < 1:
                        continue
                    if ny == y + 1 and not passable(self.at(x, y + 2, z)):
                        continue  # no head room to jump
                    if self.stand(nx, ny, nz):
                        seen.add((nx, ny, nz)); q.append((nx, ny, nz))
                        break
        return seen


def reachable(reach, pos):
    x, y, z = pos
    return any((x + dx, sy, z + dz) in reach for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) for sy in (y - 1, y, y + 1))


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
        json.dumps({"pack": {"description": "batch3", "min_format": [121, 0], "max_format": [121, 0]}}))
    per, tcells, solid = {}, {}, {}
    for key, bd in b.BUILDINGS.items():
        module = mods[bd["module"]]
        nbt, schem = OUT / f"{module['file']}.nbt", OUT / f"{module['file']}.schem"
        r = {"nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"], s["size"]
        assert s["mismatches"] == 0, s
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = _template_cells(nbt)
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        assert not bad, (key, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0}
        # access, one entrance at a time
        w = World([(cells, module["size"], (0, 0, 0))])
        containers = sorted(p for p, v in cells.items() if v[0] in ("minecraft:chest", "minecraft:barrel"))
        acc = {}
        for name, ent in bd["entrances"].items():
            reach = w.walk(ent, {ent})
            inner = {p for p in reach if w.inside(p[0], p[2])}
            miss_i = sorted(n for n, p in bd["interactive"].items() if not reachable(reach, p))
            miss_c = [list(p) for p in containers if not reachable(reach, p)]
            acc[name] = {"outside_cell": list(ent), "interior_feet_cells": len(inner),
                         "interactive_unreached": miss_i, "containers_unreached": miss_c}
        r["access"] = {"entrances": acc, "interactive": sorted(bd["interactive"]), "containers": [list(p) for p in containers]}
        per[key] = r
        tcells[key] = cells
        solid[key] = {p: v for p, v in cells.items() if v[0] != "minecraft:air"}
        (pack / f"data/experimental/structure/{key}.nbt").write_bytes(nbt.read_bytes())
    # every container must be reachable from at least the main entrance of its building
    main_ent = {"armory": "tower_portal_east", "yard": "road_gate_east"}
    for key, m in main_ent.items():
        e = per[key]["access"]["entrances"][m]
        assert not e["interactive_unreached"] and not e["containers_unreached"], (key, e)
    assert not per["armory"]["access"]["entrances"]["loggia_bay_south"]["containers_unreached"]

    # premium slot
    px, py, pz = b.PREMIUM_CHEST["M-armory"]
    pc = tcells["armory"][(px, py, pz)]
    room = [p for p, v in tcells["armory"].items() if v[0] == "minecraft:chest" and 2 <= p[0] <= 3 and 3 <= p[2] <= 5]
    assert pc[0] == "minecraft:chest" and pc[1].get("type") == "single" and room == [(px, py, pz)], (pc, room)
    result["premium"] = {"module": "M-armory", "placement": "F05", "chest": [px, py, pz], "state": _text(*pc),
                         "only_chest_in_strongroom": True, "contents": "empty in template (runtime decides; 35% once per structure)"}

    # adjacency at the real q=0 offset
    mf05 = next(e for e in A.manifest(0) if e["placement"] == "F05")
    mf06 = next(e for e in A.manifest(0) if e["placement"] == "F06")
    off = (mf06["origin"][0] - mf05["origin"][0], 0, mf06["origin"][2] - mf05["origin"][2])
    assert off == YARD_OFFSET, off
    joint = World([(tcells["armory"], b.BUILDINGS["armory"]["size"], (0, 0, 0)),
                   (tcells["yard"], b.BUILDINGS["yard"]["size"], off)])
    gate = tuple(p + o for p, o in zip(b.BUILDINGS["yard"]["entrances"]["road_gate_east"], (off[0], off[2])))
    portal = b.BUILDINGS["armory"]["entrances"]["tower_portal_east"]
    from_gate = joint.walk(gate, {gate})
    from_portal = joint.walk(portal, {portal})
    targets = {k: (p[0] + off[0], p[1], p[2] + off[2]) for k, p in b.BUILDINGS["yard"]["interactive"].items() if k.startswith("target")}
    bay, apron = (8, 1, 12), (8, 1, 13)
    result["adjacency"] = {
        "yard_origin_minus_armory_origin": list(off),
        "bay_feet_cell_walkable": joint.stand(*bay), "apron_feet_cell_walkable": joint.stand(*apron),
        "gate_alone_reaches_premium_chest": reachable(from_gate, (px, py, pz)),
        "gate_alone_reaches_all_armory_interactive": all(reachable(from_gate, p) for p in b.BUILDINGS["armory"]["interactive"].values()),
        "portal_alone_reaches_targets": {k: reachable(from_portal, p) for k, p in targets.items()},
        "portal_alone_reaches_all_yard_interactive": all(
            reachable(from_portal, (p[0] + off[0], p[1], p[2] + off[2])) for p in b.BUILDINGS["yard"]["interactive"].values()),
    }
    adj = result["adjacency"]
    assert adj["bay_feet_cell_walkable"] and adj["apron_feet_cell_walkable"] and adj["gate_alone_reaches_premium_chest"]
    assert adj["gate_alone_reaches_all_armory_interactive"] and all(adj["portal_alone_reaches_targets"].values())
    assert adj["portal_alone_reaches_all_yard_interactive"]

    # strict placement on the pinned server
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
    finally:
        server.stop()
    result["buildings"] = per
    (HERE / "check-result.json").write_text(json.dumps(result, indent=1) + "\n")
    bad = {k: len(v["server_strict_placement"]["failures"]) for k, v in per.items()}
    print("PASS" if not any(bad.values()) else f"FAIL {bad}")
    raise SystemExit(1 if any(bad.values()) else 0)


if __name__ == "__main__":
    main()
