"""Minimal checks for a House A variant: NBT validity, bounds, key block states, walk-in access, 26.3 strict placement.

  PYTHONPATH=. python <dir>/checks.py --server-jar server.jar --java java25 --work <empty dir>
Writes <dir>/check-result.json. Imports the variant's build.py (design(), DOOR, INTERACTIVE) from the same folder.
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
PASSABLE = {
    "minecraft:air",
    "minecraft:lantern",
    "minecraft:torch",
    "minecraft:wall_torch",
    "minecraft:iron_chain",
}


def load_build():
    spec = importlib.util.spec_from_file_location("variant_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def passable(cell):
    if cell is None:
        return True
    bid = cell[0]
    if bid.endswith("_trapdoor"):
        return False
    return bid in PASSABLE or bid.endswith(("_carpet", "_door", "_pressure_plate"))


def access(cells, size, door):
    """Floor-level BFS: a column (x, z) is walkable when y=1 and y=2 are passable and y=0 is solid ground or floor.
    Starts outside the box in front of the door (z = depth), which stands for the surrounding ground."""
    w, _, d = size
    get = cells.get
    start = (door[0], d)  # first cell outside the south face
    seen, q = {start}, deque([start])
    while q:
        x, z = q.popleft()
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (nx, nz) in seen or not (-1 <= nx <= w and -1 <= nz <= d):
                continue
            inside = 0 <= nx < w and 0 <= nz < d
            if inside and not (
                passable(get((nx, 1, nz))) and passable(get((nx, 2, nz)))
            ):
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
    b = load_build()
    nbt, schem = HERE / "st03_house_a.nbt", HERE / "st03_house_a.schem"
    module = A.modules()["M-house_a"]
    res = {"nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
    # 1. validity + bounds (independent decoder, every cell against the source)
    s = V.verify(
        nbt,
        schem,
        C.load_reference("26.3"),
        "include",
        C.load_connectivity("26.3"),
        block_entities.load("26.3"),
    )
    assert s["size"] == tuple(module["size"]) or list(s["size"]) == module["size"], s[
        "size"
    ]
    res["verify"] = {
        k: s[k]
        for k in (
            "size",
            "blocks",
            "non_air_blocks",
            "palette",
            "cells_compared",
            "mismatches",
        )
    }
    res["verify"]["size"] = list(res["verify"]["size"])
    # 2. key states: every authored cell (stairs facing/half/shape, door, beds, ...) equals the template
    cells = {p: v for p, v in _template_cells(nbt).items() if v[0] != "minecraft:air"}
    src = b.design()
    bad = [
        list(p)
        for p, (bid, pr) in src.items()
        if bid != "minecraft:air"
        and (
            cells.get(p, ("", {}))[0] != bid
            or any(cells[p][1].get(k) != v for k, v in pr.items())
        )
    ]
    assert not bad, bad[:5]
    dx, dz = b.DOOR
    lower, upper = cells[(dx, 1, dz)], cells[(dx, 2, dz)]
    assert (
        lower[0].endswith("_door")
        and lower[1]["facing"] == "south"
        and lower[1]["half"] == "lower"
        and upper[1]["half"] == "upper"
    )
    stairs = {p: v for p, v in cells.items() if v[0].endswith("_stairs")}
    res["states"] = {
        "authored_cells_checked": len(src),
        "mismatches": 0,
        "stairs": len(stairs),
        "door": f"{lower[0]} at {[dx, 1, dz]} facing south, lower+upper",
    }
    # 3. access: walk in through the door, reach every interactive block
    reach = access(cells, tuple(module["size"]), (dx, dz))
    assert (dx, dz) in reach, "door column not reachable"
    unreached = []
    for name, (x, y, z) in b.INTERACTIVE.items():
        if not any(
            (x + ox, z + oz) in reach for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            unreached.append(name)
    assert not unreached, unreached
    res["access"] = {
        "door_reachable_from_outside": True,
        "interior_walkable_columns": sorted(
            [
                list(c)
                for c in reach
                if 0 <= c[0] < module["size"][0] and 0 <= c[1] < module["size"][2]
            ]
        ),
        "interactive_reachable": sorted(b.INTERACTIVE),
    }
    # 4. strict placement on the pinned 26.3 server, rotation none, every cell compared
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    pack = a.work / "pack"
    dest = pack / "data/experimental/structure/house_a.nbt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(nbt.read_bytes())
    (pack / "pack.mcmeta").write_text(
        json.dumps(
            {
                "pack": {
                    "description": "house a",
                    "min_format": [121, 0],
                    "max_format": [121, 0],
                }
            }
        )
    )
    all_cells = _template_cells(nbt)
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 32, 32)
        o = (16, 80, 16)
        reply = server.cmd(
            f"place template experimental:house_a {o[0]} {o[1]} {o[2]} none none 1 0 strict"
        )
        assert reply.startswith("Loaded template"), reply
        fails = [
            list(p)
            for p, (bid, pr) in sorted(all_cells.items())
            if "passed"
            not in server.cmd(
                f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}"
            )
        ]
    finally:
        server.stop()
    res["server_strict_placement"] = {
        "server_sha1": sha,
        "rotation": "none",
        "cells": len(all_cells),
        "failures": fails,
    }
    (HERE / "check-result.json").write_text(json.dumps(res, indent=1) + "\n")
    print("PASS" if not fails else f"FAIL {len(fails)}")
    if fails:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
