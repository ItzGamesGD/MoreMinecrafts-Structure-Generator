"""Checks for the F07/F08 warehouse NBTs (new files only). Reuses the batch-4 walk engine (feet + head passable,
solid support, step 1, fences/walls/bars not standable, ladders climbable, open trapdoors passable).

  PYTHONPATH=. python experiments/st03-batch5-warehouses/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt      independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source), size equals the
           placement-table module size, every authored state present in the NBT unchanged
  access   from the street entrance ALONE (no outside ground but that cell): every container / workstation inside the
           walls, every key point (aisle, bays, loft walkway); loft cells counted; apron supplies from the open ground
           ring; F08's external loft stair checked on its own as a second way onto the loft
  storage  storage actually built: containers, crate/sack blocks, walkable loft feet cells
  f04_f08  F04 (approved NBT) and F08 joined at their real offset: the 3-block gap z=50..52 stays empty of both
           templates' blocks at every height and is walkable along its whole length; F08's north apron stays clear
  server   strict `place template` on the pinned 26.3 server (rotation none), every cell compared
Rotations, the integrated q=0 layout with every built neighbour, footing and entrance clearance: place_check.py.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B4C = _load("b4checks", EXP / "st03-batch4-barracks" / "checks.py")
World, reachable, passable = B4C.World, B4C.reachable, B4C.passable
USE_IDS = B4C.USE_IDS | {"composter", "anvil", "chipped_anvil"}
CRATE_IDS = {"fletching_table", "smithing_table", "hay_block", "white_wool", "light_gray_wool", "brown_wool", "composter",
             "pumpkin", "melon", "iron_block"}
KEY_POINTS = {
    "warehouse_a": {"porch": (6, 1, 10), "aisle_head": (7, 1, 3), "west_bay": (3, 1, 6), "east_bay": (10, 1, 4),
                    "loft_walkway": (3, 5, 4)},
    "warehouse_b": {"unloading_bay": (5, 1, 7), "north_stores": (5, 1, 4), "south_stores": (5, 1, 10),
                    "rear_bay": (9, 1, 7), "north_gallery": (5, 6, 3), "gallery_bridge": (9, 6, 7),
                    "south_gallery": (5, 6, 11), "loft_door_landing": (6, 6, 12)},
}


def walls_fn(bd):
    return lambda p: not any(x0 <= p[0] <= x1 and z0 <= p[2] <= z1 for x0, x1, z0, z1 in bd["walls"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true", help="skip the server step (design iteration only)")
    a = ap.parse_args()
    b = _load("batch5_build", HERE / "build.py")
    mods = A.modules()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    result = {"server_sha1": sha}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch5", "min_format": [121, 0], "max_format": [121, 0]}}))
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
        w = World(cells, module["size"])
        outside = walls_fn(bd)
        use = sorted(p for p, v in cells.items() if v[0].split(":")[1] in USE_IDS)
        ext = [p for p in use if outside(p)]
        main_ent = next(iter(bd["entrances"].values()))
        ring = w.walk(main_ent, ring=True)
        miss_ext = [[*p, cells[p][0]] for p in ext if not reachable(ring, p)]
        r["exterior_supplies"] = {"usable_on_apron": len(ext), "unreached_from_open_ground": miss_ext}
        if miss_ext:
            problems.append((key, "exterior", miss_ext))
        acc = {}
        for name, ent in bd["entrances"].items():
            reach = w.walk(ent)
            inner = {p for p in reach if w.inside(p[0], p[2])}
            loft = sorted(p for p in inner if p[1] >= 5)
            miss_use = [[*p, cells[p][0]] for p in use if not outside(p) and not reachable(reach, p)]
            keys = {k: (p in reach) for k, p in KEY_POINTS[key].items()}
            acc[name] = {"outside_cell": list(ent), "interior_feet_cells": len(inner), "loft_feet_cells": len(loft),
                         "usable_blocks_inside": len(use) - len(ext), "usable_unreached": miss_use, "key_points": keys}
        # every entrance must reach the loft; the main entrance must reach everything
        m = acc[next(iter(bd["entrances"]))]
        if m["usable_unreached"] or not all(m["key_points"].values()):
            problems.append((key, "main entrance", m["usable_unreached"], m["key_points"]))
        for name, e in acc.items():
            if not e["loft_feet_cells"]:
                problems.append((key, name, "loft not reached"))
        r["access"] = acc
        ids = [v[0].split(":")[1] for v in cells.values()]
        r["storage"] = {"chests": ids.count("chest"), "barrels": ids.count("barrel"),
                        "crate_and_sack_blocks": sum(i in CRATE_IDS for i in ids), "ladders": ids.count("ladder"),
                        "loft_walkable_feet_cells": acc[next(iter(bd["entrances"]))]["loft_feet_cells"]}
        per[key] = r
        tcells[key] = cells
        (pack / f"data/experimental/structure/{key}.nbt").write_bytes(nbt.read_bytes())

    # F04-F08 gap: real offset from the placement table, the approved F04 NBT
    man = {e["placement"]: e for e in A.manifest(0)}
    f04, f08 = man["F04"], man["F08"]
    off = (f08["origin"][0] - f04["origin"][0], 0, f08["origin"][2] - f04["origin"][2])
    c04 = _template_cells(EXP / "st03-batch4-barracks" / "out" / "st03_barracks_c.nbt")
    gap_z = range(f04["footprint"][3] + 1, f08["footprint"][1])  # global z strictly between the footprints
    joint = {}
    for (x, y, z), v in c04.items():
        joint[(x + f04["origin"][0], y, z + f04["origin"][2])] = v
    for (x, y, z), v in tcells["warehouse_b"].items():
        joint[(x + f08["origin"][0], y, z + f08["origin"][2])] = v
    occupied = sorted([list(p) for p, v in joint.items() if p[2] in gap_z and v[0] != "minecraft:air"])
    walk = [[x, z] for z in gap_z for x in range(f04["footprint"][0] - 1, f04["footprint"][2] + 2)
            if not (passable(joint.get((x, 1, z))) and passable(joint.get((x, 2, z))))]
    apron = [[x, y, 0] for (x, y, z), v in tcells["warehouse_b"].items() if z == 0 and 1 <= y <= 3 and v[0] != "minecraft:air"]
    result["f04_f08"] = {"f08_origin_minus_f04_origin": list(off), "gap_global_z": [gap_z.start, gap_z.stop - 1],
                         "gap_width_blocks": len(gap_z), "blocks_in_gap": occupied,
                         "gap_cells_not_walkable_y1_y2": walk, "f08_north_apron_blocks_y1_y3": apron}
    if len(gap_z) != 3 or occupied or walk or apron:
        problems.append(("f04_f08", result["f04_f08"]))

    if a.offline:
        print(json.dumps({k: {"access": v["access"], "storage": v["storage"], "ext": v["exterior_supplies"]}
                          for k, v in per.items()}, indent=1, default=list))
        print(json.dumps(result["f04_f08"], default=list))
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


if __name__ == "__main__":
    main()
