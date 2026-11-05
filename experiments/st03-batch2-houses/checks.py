"""Checks for the batch-2 houses (B, C, D). Only the new NBTs are checked.

  PYTHONPATH=. python experiments/st03-batch2-support/checks.py --server-jar server.jar --java java25 --work <dir>
Writes check-result.json: independent NBT verification, authored-state equality, floor-level walk-in access to every
interactive block, and a strict `place template` on the pinned 26.3 server (rotation none) comparing every cell.
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
PASSABLE = {
    "minecraft:air",
    "minecraft:lantern",
    "minecraft:wall_torch",
    "minecraft:iron_chain",
    "minecraft:white_wall_banner",
    "minecraft:grindstone_never",
}


def load_build():
    spec = importlib.util.spec_from_file_location("batch2_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def passable(cell):
    if cell is None:
        return True
    bid = cell[0]
    if bid.endswith("_trapdoor") and cell[1].get("open") != "true":
        return False
    if bid.endswith("_trapdoor"):
        return False  # open trapdoors are cart wheels: treat as solid for the walk check
    return bid in PASSABLE or bid.endswith(("_carpet", "_door", "_pressure_plate"))


def access(cells, size, door):
    """BFS over floor columns: walkable when y=1 and y=2 are passable. Starts just outside the front (z = depth)."""
    w, _, d = size
    start = (door[0], d)
    seen, q = {start}, deque([start])
    while q:
        x, z = q.popleft()
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (nx, nz) in seen or not (-1 <= nx <= w and -1 <= nz <= d):
                continue
            inside = 0 <= nx < w and 0 <= nz < d
            if inside and not (passable(cells.get((nx, 1, nz))) and passable(cells.get((nx, 2, nz)))):
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
    mods = A.modules()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    result = {"server_sha1": sha}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch2", "min_format": [121, 0], "max_format": [121, 0]}})
    )
    per = {}
    template_cells = {}
    for key, bd in b.BUILDINGS.items():
        module = mods[bd["module"]]
        nbt, schem = OUT / f"{module['file']}.nbt", OUT / f"{module['file']}.schem"
        r = {"nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"], s["size"]
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        assert s["mismatches"] == 0, s
        cells = {p: v for p, v in _template_cells(nbt).items() if v[0] != "minecraft:air"}
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if bid != "minecraft:air"
               and (cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items()))]
        assert not bad, (key, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0}
        dx, dz = bd["door"]
        reach = access(cells, module["size"], (dx, dz))
        assert (dx, dz) in reach, f"{key}: entrance column not reachable"
        unreached = [n for n, (x, y, z) in bd["interactive"].items()
                     if not any((x + ox, z + oz) in reach for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        assert not unreached, (key, unreached)
        containers = sorted(n for n in bd["interactive"] if n.startswith(("chest", "barrel")))
        r["access"] = {"entrance_reachable_from_outside": True,
                       "interior_walkable_columns": sum(1 for c in reach if 0 <= c[0] < module["size"][0] and 0 <= c[1] < module["size"][2]),
                       "interactive_reachable": sorted(bd["interactive"]), "containers": containers}
        # entrance clearance: 2 high at the entrance column
        if key != "cart_shed":
            r["entrance_clearance_ok"] = passable(cells.get((dx, 1, dz))) and passable(cells.get((dx, 2, dz)))
        per[key] = r
        template_cells[key] = _template_cells(nbt)
        (pack / f"data/experimental/structure/{key}.nbt").write_bytes(nbt.read_bytes())
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 120, 32)
        for i, (key, cells) in enumerate(template_cells.items()):
            o = (16 + i * 40, 80, 16)
            reply = server.cmd(f"place template experimental:{key} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), (key, reply)
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(
                         f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
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
