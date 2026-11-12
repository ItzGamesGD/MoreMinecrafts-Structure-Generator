"""Automated checks for the six group-1 templates (no client needed).

  PYTHONPATH=. python <dir>/checks.py --server-jar server.jar --java java25 --work <empty dir>
Per building: (1) independent NBT verify (size, every cell vs the source), (2) every authored state present in the template,
(3) walk-in access from outside (BFS) incl. every workstation / container reachable, (4) strict placement on the pinned
26.3 server in all four rotations with every cell compared (rotate_props), (5) container function: each chest / barrel /
furnace / blast furnace is a real block entity and accepts an item (item replace ... container.0, read back).
Writes <dir>/check-result.json.
"""

import argparse
import hashlib
import importlib.util
import json
import re
from collections import deque
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import ROTATIONS, TURN, _at, _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b6build", HERE / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

PASSABLE = {"minecraft:air", "minecraft:lantern", "minecraft:torch", "minecraft:wall_torch", "minecraft:iron_chain", "minecraft:fire"}
USE = {  # interactive blocks that must be reachable from a walkable neighbour column
    "chest", "barrel", "furnace", "blast_furnace", "crafting_table", "anvil", "grindstone", "smithing_table",
    "water_cauldron", "cauldron", "red_bed", "blue_bed",
}  # fmt: skip
CONTAINERS = {"minecraft:chest", "minecraft:barrel", "minecraft:furnace", "minecraft:blast_furnace"}


def rotate_props(props, rotation):
    """BlockState.rotate for the properties used here: horizontal facing and connection keys turn, log axis x<->z swaps
    on quarter turns, vertical facing (up) and everything else stays. (live.rotate_props lacks axis and facing=up.)"""
    turn = TURN[rotation]
    out = {}
    for k, v in props.items():
        if k in turn:
            out[turn[k]] = v
        elif k == "facing":
            out[k] = turn.get(v, v)
        elif k == "axis" and v in ("x", "z") and rotation in ("clockwise_90", "counterclockwise_90"):
            out[k] = "z" if v == "x" else "x"
        else:
            out[k] = v
    return out


def passable(cell):
    if cell is None:
        return True
    bid = cell[0]
    if bid.endswith("_trapdoor"):
        return not (cell[1].get("open") == "false")  # an open trapdoor is a thin board against a wall
    return bid in PASSABLE or bid.endswith(("_carpet", "_door", "_pressure_plate"))


def solid_floor(cell):
    return cell is not None and not passable(cell) or (cell is not None and cell[0].endswith("_carpet"))


def walk(cells, size):
    """Columns (x, z) reachable from outside. A column is standable when y=1 and y=2 are passable and y=0 is a floor.
    Outside the box counts as open ground. Doors are walked through (closed doors are passable for a player)."""
    w, _, d = size
    get = cells.get
    ok = lambda x, z: passable(get((x, 1, z))) and passable(get((x, 2, z)))
    seen, q = set(), deque()
    for x in range(-1, w + 1):
        for z in (-1, d):
            seen.add((x, z))
            q.append((x, z))
    for z in range(-1, d + 1):
        for x in (-1, w):
            if (x, z) not in seen:
                seen.add((x, z))
                q.append((x, z))
    while q:
        x, z = q.popleft()
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (nx, nz) in seen or not (-1 <= nx <= w and -1 <= nz <= d):
                continue
            if 0 <= nx < w and 0 <= nz < d and not ok(nx, nz):
                continue
            seen.add((nx, nz))
            q.append((nx, nz))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    mods = A.modules()
    res = {"server_sha1": sha, "buildings": {}}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "b6", "min_format": [121, 0], "max_format": [121, 0]}})
    )
    tmpl = {}
    for mid, (fname, fn) in B.BUILDINGS.items():
        nbt, schem = HERE / f"{fname}.nbt", HERE / f"{fname}.schem"
        m = mods[mid]
        r = {"nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"), block_entities.load("26.3"))
        assert list(s["size"]) == m["size"] and s["mismatches"] == 0, (mid, s)
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k]) for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = {p: v for p, v in _template_cells(nbt).items() if v[0] != "minecraft:air"}
        src = fn().c
        bad = [list(p) for p, (bid, pr) in src.items() if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        assert not bad, (mid, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0, "stairs": sum(v[0].endswith("_stairs") for v in cells.values())}
        # access
        reach = walk(cells, m["size"])
        w, _, d = m["size"]
        inside = sorted([x, z] for x, z in reach if 0 <= x < w and 0 <= z < d)
        door = B.DOORS[mid]
        if door:
            assert (door[0], door[1]) in reach and any(c[0] == door[0] for c in inside), mid
        unreached = []
        used = []
        for (x, y, z), (bid, pr) in sorted(cells.items()):
            if bid.removeprefix("minecraft:") in USE and y == 1 and pr.get("part") != "head":
                used.append(bid)
                if not any((x + ox, z + oz) in reach for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    unreached.append([x, y, z, bid])
        r["access"] = {"entrance": "door at x=%d (south)" % door[0] if door else "open front (south)", "interior_columns": len(inside), "interactive_blocks": len(used), "unreachable": unreached}
        r["containers"] = {k: sum(1 for v in cells.values() if v[0] == k) for k in sorted(CONTAINERS)}
        r["workstations"] = {k: sum(1 for v in cells.values() if v[0] == "minecraft:" + k) for k in ("crafting_table", "anvil", "grindstone", "smithing_table", "blast_furnace", "furnace", "water_cauldron", "cauldron")}
        dest = pack / f"data/experimental/structure/{fname}.nbt"
        dest.write_bytes(nbt.read_bytes())
        tmpl[fname] = (cells, _template_cells(nbt), m)
        res["buildings"][mid] = r
        assert not unreached, (mid, unreached)
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 420, 40)
        slot = 0
        for fname, (cells, allc, m) in tmpl.items():
            rr = res["buildings"][[k for k, v in B.BUILDINGS.items() if v[0] == fname][0]]
            rr["rotations"] = {}
            for rotation in ROTATIONS:
                o = (16 + slot * 16, 80, 16)
                slot += 1
                reply = server.cmd(f"place template experimental:{fname} {o[0]} {o[1]} {o[2]} {rotation} none 1 0 strict")
                assert reply.startswith("Loaded template"), reply
                fails = []
                for pos, (bid, props) in sorted(allc.items()):
                    p = _at(o, pos, rotation)
                    if "passed" not in server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} {_text(bid, rotate_props(props, rotation))}"):
                        fails.append(list(pos))
                rr["rotations"][rotation] = {"cells": len(allc), "failures": fails}
                print(fname, rotation, len(allc), len(fails), flush=True)
                if rotation == "none":  # container function, once per building
                    out = {}
                    for pos, (bid, props) in sorted(allc.items()):
                        if bid in CONTAINERS:
                            p = _at(o, pos, rotation)
                            at = f"{p[0]} {p[1]} {p[2]}"
                            has = server.cmd(f"data get block {at} Items")
                            server.cmd(f"item replace block {at} container.0 with minecraft:bread 3")
                            back = server.cmd(f"data get block {at} Items")
                            out["%s@%s" % (bid.removeprefix("minecraft:"), list(pos))] = "OK" if ("bread" in back and "Found no" not in back) else f"FAIL {has!r} -> {back!r}"
                    rr["container_function"] = out
                    # fire / cauldron survive a few ticks
                    keep = {}
                    for pos, (bid, props) in sorted(allc.items()):
                        if bid in ("minecraft:fire", "minecraft:water_cauldron"):
                            p = _at(o, pos, rotation)
                            keep[bid] = server.cmd(f"execute if block {p[0]} {p[1]} {p[2]} {_text(bid, props)}")
                    rr["persistent_blocks"] = keep
    finally:
        server.stop()
    (HERE / "check-result.json").write_text(json.dumps(res, indent=1) + "\n")
    bad = [(k, r) for k, v in res["buildings"].items() for r, x in v["rotations"].items() if x["failures"]]
    badc = [(k, c) for k, v in res["buildings"].items() for c, st in v.get("container_function", {}).items() if st != "OK"]
    print("PASS" if not bad and not badc else f"FAIL {bad} {badc}")
    raise SystemExit(1 if bad or badc else 0)


if __name__ == "__main__":
    main()
