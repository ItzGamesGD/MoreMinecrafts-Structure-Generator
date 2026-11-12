"""Automated checks for the six group-1 templates (no client needed).

  PYTHONPATH=. python <dir>/checks.py --server-jar server.jar --java java25 --work <empty dir>
Per template (8: house B F12 / F15, house C F13 / F16, house D, kitchen, smithy, cart shed): (1) independent NBT verify with the
facility's loot table declared (size, every cell vs the source, block-entity data incl. LootTable), (2) every authored state in
the template, (3) walk-in access from outside (BFS) incl. every workstation / container reachable, (4) strict placement on the
pinned 26.3 server in all four rotations with every cell compared, (5) block entities IN THE GAME: live.block_entity_failures in
all four rotations (id, exact LootTable on chests/barrels, none elsewhere, no Items, banner pattern counts), (6) containers
accept items, (7) the loot tables load (`loot replace`), (8) loot binding: exactly one table per container, one table id per
facility, table files have empty pools and unique random sequences, (9) variants differ only in decoration, (10) templates whose
look did not change have block states identical to the committed b0c8644 files.
Writes <dir>/check-result.json.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from collections import deque
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import ROTATIONS, TURN, _at, _template_cells, _text, block_entity_failures
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b6build", HERE / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

PASSABLE = {"minecraft:air", "minecraft:lantern", "minecraft:torch", "minecraft:wall_torch", "minecraft:iron_chain", "minecraft:fire"}
USE = {  # interactive blocks that must be reachable from a walkable neighbour column
    "chest", "barrel", "furnace", "blast_furnace", "smoker", "campfire", "lectern", "crafting_table", "anvil", "grindstone",
    "smithing_table", "water_cauldron", "cauldron", "red_bed", "blue_bed",
}  # fmt: skip
LOOT_BLOCKS = {"minecraft:chest", "minecraft:barrel"}  # ordinary-loot containers: the only blocks bound to a table
CONTAINERS = LOOT_BLOCKS | {"minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker"}  # accept items
BASE = "b0c8644"  # the previous commit: reference for "the look did not change"
UNCHANGED_LOOK = {  # new template -> file at BASE with identical block states (only the LootTable tags are new)
    "st03_house_b_f12": "st03_house_b", "st03_house_c_f13": "st03_house_c", "st03_house_d": "st03_house_d",
    "st03_smithy": "st03_smithy", "st03_cart_shed": "st03_cart_shed",
}  # fmt: skip


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


def template_block_entities(path):
    """{pos: nbt compound} straight from the template file (what the game must reproduce)."""
    import gzip
    import io

    import nbtlib

    f = nbtlib.File.parse(io.BytesIO(gzip.decompress(Path(path).read_bytes())))
    return {tuple(int(v) for v in b["pos"]): b["nbt"] for b in f["blocks"] if "nbt" in b}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    mods = A.modules()
    res = {"server_sha1": sha, "templates": {}}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "b6", "min_format": [121, 0], "max_format": [121, 0]}})
    )
    # the empty loot tables, as the mod's datapack would carry them
    import shutil

    shutil.copytree(HERE / "datapack/data/moreminecrafts", pack / "data/moreminecrafts", dirs_exist_ok=True)
    tmpl, designs = {}, {}
    for fname, (mid, fn, key, placements) in B.TEMPLATES.items():
        nbt, schem = HERE / f"{fname}.nbt", HERE / f"{fname}.schem"
        m = mods[mid]
        loot = B.loot_id(key)
        r = {"module": mid, "placements": placements, "loot_table": loot, "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"), block_entities.load("26.3"), loot_table=loot)
        assert list(s["size"]) == m["size"] and s["mismatches"] == 0, (fname, s)
        r["verify"] = {k: (list(s[k]) if k == "size" else s[k]) for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = {p: v for p, v in _template_cells(nbt).items() if v[0] != "minecraft:air"}
        g = fn()
        designs[fname] = g
        src = g.c
        bad = [list(p) for p, (bid, pr) in src.items() if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        assert not bad, (fname, bad[:5])
        r["states"] = {"authored_cells_checked": len(src), "mismatches": 0, "stairs": sum(v[0].endswith("_stairs") for v in cells.values())}
        # access
        reach = walk(cells, m["size"])
        w, _, d = m["size"]
        inside = sorted([x, z] for x, z in reach if 0 <= x < w and 0 <= z < d)
        door = B.DOORS[mid]
        if door:
            assert (door[0], door[1]) in reach and any(c[0] == door[0] for c in inside), fname
        unreached, used = [], []
        for (x, y, z), (bid, pr) in sorted(cells.items()):
            if bid.removeprefix("minecraft:") in USE and y == 1 and pr.get("part") != "head":
                used.append(bid)
                if not any((x + ox, z + oz) in reach for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    unreached.append([x, y, z, bid])
        r["access"] = {"entrance": "door at x=%d (south)" % door[0] if door else "open front (south)", "interior_columns": len(inside), "interactive_blocks": len(used), "unreachable": unreached}
        r["containers"] = {k.removeprefix("minecraft:"): sum(1 for v in cells.values() if v[0] == k) for k in sorted(CONTAINERS)}
        r["workstations"] = {k: sum(1 for v in cells.values() if v[0] == "minecraft:" + k) for k in ("crafting_table", "anvil", "grindstone", "smithing_table", "blast_furnace", "furnace", "smoker", "campfire", "lectern", "water_cauldron", "cauldron")}
        # loot binding, statically from the template file
        bes = template_block_entities(nbt)
        tagged = {p: str(n["LootTable"]) for p, n in bes.items() if "LootTable" in n}
        want_pos = {p for p, v in cells.items() if v[0] in LOOT_BLOCKS}
        assert set(tagged) == want_pos and all(t == loot for t in tagged.values()), (fname, sorted(set(tagged) ^ want_pos))
        assert all("Items" not in n and "LootTableSeed" not in n for n in bes.values())
        assert not [p for p, n in bes.items() if "LootTable" in n and cells[p][0] not in LOOT_BLOCKS]
        r["loot_binding"] = {"containers_bound": len(tagged), "table_ids": sorted(set(tagged.values())), "tags_per_container": 1,
                             "non_loot_block_entities_without_table": sum(1 for p, n in bes.items() if "LootTable" not in n)}  # fmt: skip
        (pack / f"data/experimental/structure/{fname}.nbt").write_bytes(nbt.read_bytes())
        tmpl[fname] = (cells, _template_cells(nbt), m, bes, loot)
        res["templates"][fname] = r
        assert not unreached, (fname, unreached)
    # module-default copies are byte-identical to their first variant
    res["module_default_copies"] = {}
    for copy, src in B.MODULE_DEFAULT_COPY.items():
        same = (HERE / f"{copy}.nbt").read_bytes() == (HERE / f"{src}.nbt").read_bytes()
        res["module_default_copies"][copy] = {"identical_to": src, "bytes_identical": same}
        assert same
    # loot table files: empty pools, one table per facility, unique random sequences, each id used by exactly one facility
    tables, seqs = {}, set()
    for key in B.LOOT_KEYS:
        t = json.loads((B.LOOT_DIR / f"{key}.json").read_text())
        assert t["type"] == "minecraft:chest" and t["pools"] == [] and t["random_sequence"] == B.loot_id(key), key
        assert t["random_sequence"] not in seqs
        seqs.add(t["random_sequence"])
        tables[key] = {"id": B.loot_id(key), "pools": 0, "random_sequence": t["random_sequence"]}
    used_ids = {}
    for fname, (_, _, key, _) in B.TEMPLATES.items():
        used_ids.setdefault(B.loot_id(key), set()).add(key)
    assert all(len(v) == 1 for v in used_ids.values()) and set(used_ids) == {B.loot_id(k) for k in B.LOOT_KEYS}
    res["loot_tables"] = {"files": tables, "ids_per_facility": {k: sorted(v) for k, v in used_ids.items()}}
    # variants: identical bounds / footprint / door / room program, differing only in recorded decoration cells
    res["variants"] = {}
    for a_, b_ in (("st03_house_b_f12", "st03_house_b_f15"), ("st03_house_c_f13", "st03_house_c_f16")):
        ga, gb = designs[a_], designs[b_]
        assert (ga.W, ga.H, ga.D) == (gb.W, gb.H, gb.D)
        diff = {p for p in set(ga.c) | set(gb.c) if ga.c.get(p) != gb.c.get(p)}
        bedcolour = {  # same bed cell, same facing / part, only the colour differs: decoration
            p for p in diff
            if p in ga.c and p in gb.c and ga.c[p][0].endswith("_bed") and gb.c[p][0].endswith("_bed") and ga.c[p][1] == gb.c[p][1]
        }  # fmt: skip
        assert (diff - bedcolour) <= (ga.decor | gb.decor), sorted(diff - bedcolour - (ga.decor | gb.decor))[:5]
        prog = lambda g: {p: v for p, v in g.c.items() if p not in g.decor}  # noqa: E731
        same_prog = {p: v for p, v in prog(ga).items() if v[0] != "minecraft:blue_bed" and v[0] != "minecraft:red_bed"}
        other_prog = {p: v for p, v in prog(gb).items() if v[0] != "minecraft:blue_bed" and v[0] != "minecraft:red_bed"}
        assert same_prog == other_prog  # beds differ only in colour (checked next)
        beds = lambda g: sorted(p for p, v in g.c.items() if v[0].endswith("_bed"))  # noqa: E731
        assert beds(ga) == beds(gb)
        doors = lambda g: sorted(p for p, v in g.c.items() if v[0].endswith("_door"))  # noqa: E731
        assert doors(ga) == doors(gb)
        kinds = lambda g: sorted((p, v[0]) for p, v in g.c.items() if v[0] in CONTAINERS | {"minecraft:crafting_table"})  # noqa: E731
        assert kinds(ga) == kinds(gb)
        res["variants"][f"{a_} vs {b_}"] = {"size_equal": True, "door_cells_equal": True, "bed_cells_equal": True,
                                             "container_and_workstation_cells_equal": True,
                                             "differing_cells": len(diff), "of_which_bed_colour_only": len(bedcolour), "all_differing_cells_are_decoration": True}  # fmt: skip
    # look unchanged since BASE (block states, ignoring block-entity data)
    res["unchanged_look_vs_" + BASE] = {}
    for new, old in UNCHANGED_LOOK.items():
        blob = subprocess.run(["git", "show", f"{BASE}:experiments/st03-b6-group1/{old}.nbt"], capture_output=True, check=True, cwd=HERE).stdout
        tmp = a.work / "old.nbt"
        tmp.write_bytes(blob)
        o, n = _template_cells(tmp), _template_cells(HERE / f"{new}.nbt")
        assert o == n, (new, [p for p in set(o) | set(n) if o.get(p) != n.get(p)][:5])
        res["unchanged_look_vs_" + BASE][new] = {"cells": len(n), "block_state_differences": 0}
    # the game
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, 0, 0, 640, 40)
        res["datapack_loaded"] = server.cmd("datapack list enabled")
        slot = 0
        for fname, (cells, allc, m, bes, loot) in tmpl.items():
            rr = res["templates"][fname]
            rr["rotations"] = {}
            rr["block_entities_in_game"] = {}
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
                be_fail = block_entity_failures(server, o, rotation, bes)
                rr["block_entities_in_game"][rotation] = {"block_entities": len(bes), "failures": be_fail}
                print(fname, rotation, len(allc), len(fails), len(be_fail), flush=True)
                if rotation == "none":  # per building, once: loot tag in the game, loot table loads, containers take items
                    out, tags = {}, {}
                    for pos, (bid, props) in sorted(allc.items()):
                        if bid in CONTAINERS:
                            p = _at(o, pos, rotation)
                            at = f"{p[0]} {p[1]} {p[2]}"
                            if bid in LOOT_BLOCKS:
                                lt = server.cmd(f"data get block {at} LootTable")
                                # `data get block <pos> LootTable` prints the single string value: exactly one table, the facility's
                                tags[f"{bid.removeprefix('minecraft:')}@{list(pos)}"] = "OK" if (lt.endswith(f'"{loot}"') and lt.count('"') == 2) else f"FAIL {lt!r}"
                                ld = server.cmd(f"loot replace block {at} container.0 loot {loot}")
                                tags[f"{bid.removeprefix('minecraft:')}@{list(pos)} loot replace"] = ld
                            server.cmd(f"item replace block {at} container.1 with minecraft:bread 3" if bid in LOOT_BLOCKS else f"item replace block {at} container.0 with minecraft:bread 3")
                            back = server.cmd(f"data get block {at} Items")
                            out[f"{bid.removeprefix('minecraft:')}@{list(pos)}"] = "OK" if ("bread" in back and "Found no" not in back) else f"FAIL {back!r}"
                    rr["container_function"] = out
                    rr["loot_tag_in_game"] = tags
    finally:
        server.stop()
    (HERE / "check-result.json").write_text(json.dumps(res, indent=1) + "\n")
    bad = [(k, r) for k, v in res["templates"].items() for r, x in v["rotations"].items() if x["failures"]]
    badbe = [(k, r) for k, v in res["templates"].items() for r, x in v["block_entities_in_game"].items() if x["failures"]]
    badc = [(k, c) for k, v in res["templates"].items() for c, st in v.get("container_function", {}).items() if st != "OK"]
    badt = [(k, c) for k, v in res["templates"].items() for c, st in v.get("loot_tag_in_game", {}).items() if " loot replace" not in c and st != "OK"]
    badl = [(k, c, st) for k, v in res["templates"].items() for c, st in v.get("loot_tag_in_game", {}).items() if " loot replace" in c and (not st.startswith("Dropped 0 items"))]
    ok = not (bad or badbe or badc or badt or badl)
    print("PASS" if ok else f"FAIL {bad} {badbe} {badc} {badt} {badl}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
