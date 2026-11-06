"""ST-03 placement check of the BUILT facilities at their real positions from tools/seam01/data/st03_placements.json.

Scope: only facilities that have a built NBT today (House A F11/F14, houses B/C/D, kitchen, smithy, cart shed,
batch 3: F05 armory, F06 training yard, batch 4: F02/F03/F04 barracks, batch 5: F07/F08 warehouses, batch 6:
F09 prison / F10 ravager stable, batch 7: F01 commander manor at the Q63 size 17x27x15, and batch 8: the perimeter
walls MW86 (W-N, W-E, W-W) and MW31 (W-SW, W-SE), air=omit, no entrance of their own).
Roads are NOT part of the placement table (the road masterplan and ground modules MQ-* are not in this repository and
not built), so a road connection cannot be asserted here; the check reports the free corridor in front of each entrance.

  offline  footprint overlaps (all 34 placements, q=0..3), per-building nearest neighbour and front clearance
  live A   whole-structure turns q=1..3: every cell of every built facility (House A excluded, it was verified before)
           placed `strict` at the manifest origin/rotation and compared with the rotated template (block + rotated states)
  live B   q=0: all built facilities placed together at their real coordinates, every cell of every one compared
           (adjacent facilities must not overwrite each other)
  live C   q=0 on a TEST terrain that falls away to the north (0..2 blocks): floor level kept at the entrance-side
           ground, stone footing filled straight down under every footprint column (Q09 / Q76-77 policy), and a
           check that no footprint column is left hollow. Test world only, not natural worldgen.

  PYTHONPATH=. python experiments/st03-placement-check/place_check.py --server-jar server.jar --java java25 --work <dir>
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export.live import _template_cells, _text, rotate_props
from tools.structure_export.stair_live import forceload, make_server

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "experiments"
G = -61  # flat world grass layer; structure y=0 floor is placed flush with it


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def built_modules(perimeter=False):
    """module id -> dict(nbt, door (x, z) boundary column, front = +z). perimeter=True adds the batch-8 walls (door None);
    the earlier capture scripts call it without, so their layouts stay what they photographed."""
    out = {}
    b1 = _load(EXP / "st03-batch1-support" / "build.py", "b1")
    b2 = _load(EXP / "st03-batch2-houses" / "build.py", "b2")
    b3 = _load(EXP / "st03-batch3-military" / "build.py", "b3")
    b4 = _load(EXP / "st03-batch4-barracks" / "build.py", "b4")
    b5 = _load(EXP / "st03-batch5-warehouses" / "build.py", "b5")
    b6 = _load(EXP / "st03-batch6-prison-stable" / "build.py", "b6")
    b7 = _load(EXP / "st03-batch7-commander-manor" / "build.py", "b7")
    for mod, folder in ((b1, "st03-batch1-support"), (b2, "st03-batch2-houses"), (b3, "st03-batch3-military"),
                        (b4, "st03-batch4-barracks"), (b5, "st03-batch5-warehouses"),
                        (b6, "st03-batch6-prison-stable"), (b7, "st03-batch7-commander-manor")):
        d = EXP / folder / "out"
        for b in mod.BUILDINGS.values():
            m = A.modules()[b["module"]]
            out[b["module"]] = {"nbt": d / f"{m['file']}.nbt", "door": b["door"], "size": b["size"],
                                "entrances": b.get("entrances")}
    if perimeter:
        b8 = _load(EXP / "st03-batch8-perimeter-walls" / "build.py", "b8")
        for b in b8.BUILDINGS.values():
            m = A.modules()[b["module"]]
            out[b["module"]] = {"nbt": EXP / "st03-batch8-perimeter-walls" / "out" / f"{m['file']}.nbt", "door": None,
                                "size": b["size"], "entrances": None}
    ha = _load(EXP / "st03-b5a-house-a" / "build.py", "ha")
    out["M-house_a"] = {"nbt": EXP / "st03-b5a-house-a" / "st03_house_a.nbt", "door": ha.DOOR, "size": (ha.W, ha.H, ha.D)}
    return out


def rot(props, rotation):
    """rotate_props, plus: vertical `facing` (barrels, grindstones: up/down) stays; horizontal `axis` swaps x/z on 90-degree turns."""
    vert = {k: v for k, v in props.items() if k == "facing" and v in ("up", "down")}
    out = rotate_props({k: v for k, v in props.items() if k not in vert}, rotation)
    out.update(vert)
    if out.get("axis") in ("x", "z") and rotation in ("clockwise_90", "counterclockwise_90"):
        out["axis"] = "z" if out["axis"] == "x" else "x"  # logs/chains turn with the structure; the helper omits axis
    return out


def overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 1) - 1
    dz = max(b[1] - a[3], a[1] - b[3], 1) - 1
    return max(dx, dz)


def offline(built):
    res = {"overlaps": {}, "facilities": {}}
    for q in range(4):
        man = A.manifest(q)
        solid = [e for e in man if not e["placement"].startswith("GROUND")]
        res["overlaps"][q] = [[x["placement"], y["placement"]] for i, x in enumerate(solid) for y in solid[i + 1:]
                              if overlap(x["footprint"], y["footprint"])]
        for e in solid:
            if e["module"] not in built:
                continue
            door = built[e["module"]]["door"]
            if door is None:  # perimeter walls: no entrance; their joints are checked in batch 8 checks.py
                continue
            turns = {v: k for k, v in A.ROT_NAME.items()}[e["rotation"]]
            w, _, d = e["size"]
            fx, fz = A.ROT[turns](0, 1)  # outward direction of the module's +z face after rotation
            # entrance cell just outside the front, in the structure frame
            ex, _, ez = A.place_cell(e, (door[0], 0, d))
            clear = 0
            while True:
                cx, cz = ex + fx * clear, ez + fz * clear
                if not (0 <= cx < 112 and 0 <= cz < 112):
                    break
                if any(s is not e and s["footprint"][0] <= cx <= s["footprint"][2] and s["footprint"][1] <= cz <= s["footprint"][3]
                       for s in solid):
                    break
                clear += 1
            nearest = min(((gap(e["footprint"], s["footprint"]), s["placement"]) for s in solid if s is not e))
            ents = {}
            for name, (lx, lz) in (built[e["module"]].get("entrances") or {}).items():
                dx, dz = (1, 0) if lx == w else (-1, 0) if lx == -1 else (0, 1) if lz == d else (0, -1)
                wx, _, wz = A.place_cell(e, (lx, 0, lz))
                ox, oz = A.ROT[turns](dx, dz)
                run, hit = 0, None
                while 0 <= wx + ox * run < 112 and 0 <= wz + oz * run < 112:
                    cx, cz = wx + ox * run, wz + oz * run
                    hit = next((s["placement"] for s in solid if s is not e and s["footprint"][0] <= cx <= s["footprint"][2]
                                and s["footprint"][1] <= cz <= s["footprint"][3]), None)
                    if hit:
                        break
                    run += 1
                ents[name] = {"outside_cell": [wx, wz], "outward": [ox, oz], "free_blocks": run, "runs_into": hit}
            res["facilities"].setdefault(str(q), {})[e["placement"]] = {
                "module": e["module"], "rotation": e["rotation"], "footprint": e["footprint"],
                "entrance_outside_cell": [ex, ez], "front_direction": [fx, fz],
                "front_free_blocks": clear, "nearest_neighbour_gap": nearest[0], "nearest": nearest[1],
                **({"entrances": ents} if ents else {}),
            }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "place-check-result.json")
    ap.add_argument("--only", default="", help="comma-separated module ids for live A and C (default: all built)")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    built = built_modules(perimeter=True)
    result = {"server_sha1": sha, "offline": offline(built)}
    templates = {m: _template_cells(v["nbt"]) for m, v in built.items()}
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(json.dumps({"pack": {"description": "st03 placement", "min_format": [121, 0], "max_format": [121, 0]}}))
    for m, v in built.items():
        (pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt").write_bytes(v["nbt"].read_bytes())
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()

    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    live = {}
    try:
        server.start()
        forceload(server, 0, 0, 1000, 127)

        def place(e, ax):
            ox, _, oz = e["origin"]
            r = server.cmd(f"place template {tid(e['module'])} {ax + ox} {G} {oz} {e['rotation']} none 1 0 strict")
            assert r.startswith("Loaded template"), (e["placement"], r)

        def compare(e, ax, ay=G):
            fails, n = [], 0
            for cell, (bid, props) in sorted(templates[e["module"]].items()):
                if bid == "minecraft:air":
                    continue
                x, y, z = A.place_cell(e, cell)
                want = _text(bid, rot(props, e["rotation"]))
                n += 1
                if "passed" not in server.cmd(f"execute if block {ax + x} {ay + y} {z} {want}"):
                    fails.append([x, y, z, bid])
            return n, fails

        # live A: whole-structure turns 1..3 (rotation 0 per module was verified in the batch checks)
        live["A_rotations"] = {}
        for q in (1, 2, 3):
            ax = 150 * q
            rows = {}
            for e in A.manifest(q):
                if e["module"] in built and e["module"] != "M-house_a" and (not only or e["module"] in only):
                    place(e, ax)
                    n, fails = compare(e, ax)
                    rows[e["placement"]] = {"rotation": e["rotation"], "cells": n, "failures": fails[:10], "failure_count": len(fails)}
            live["A_rotations"][A.ROT_NAME[q]] = rows
        # live B: q=0, everything together at the real coordinates
        ax = 600
        rows = {}
        man = [e for e in A.manifest(0) if e["module"] in built]
        for e in man:
            place(e, ax)
        for e in man:
            n, fails = compare(e, ax)
            rows[e["placement"]] = {"cells": n, "failure_count": len(fails), "failures": fails[:10]}
        live["B_integrated_q0"] = rows
        # live C: test terrain falling away to the north, footing fill, hollow-column check
        ax = 800
        rows = {}
        for e in man:
            if only and e["module"] not in only:
                continue
            x0, z0, x1, z1 = e["footprint"]
            tmpl = templates[e["module"]]
            heights = {}
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    drop = min(2, (z1 - z) // 3)
                    heights[(x, z)] = G - drop
                    if drop:
                        server.cmd(f"fill {ax + x} {G - drop + 1} {z} {ax + x} {G} {z} minecraft:air")
                        server.cmd(f"setblock {ax + x} {G - drop} {z} minecraft:grass_block")
            place(e, ax)
            hollow, filled = [], 0
            # footing material per column = the stone-like template floor block of that column (cobblestone otherwise)
            for cell, (bid, props) in tmpl.items():
                if cell[1] != 0:
                    continue
                x, _, z = A.place_cell(e, cell)
                h = heights.get((x, z))
                if h is None or h >= G:
                    continue
                stone_like = bid.split(":")[1] in ("cobblestone", "mossy_cobblestone", "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "andesite")
                foot = bid if stone_like else "minecraft:cobblestone"
                if h + 1 <= G - 1:  # a 1-block drop needs no fill (fill would swap its corners and overwrite the floor)
                    server.cmd(f"fill {ax + x} {h + 1} {z} {ax + x} {G - 1} {z} {foot}")
                filled += 1
                for y in range(h + 1, G):
                    if "passed" in server.cmd(f"execute if block {ax + x} {y} {z} minecraft:air"):
                        hollow.append([x, y, z])
            n, fails = compare(e, ax)
            rows[e["placement"]] = {"max_drop": max(G - h for h in heights.values()), "footing_columns_filled": filled,
                                    "hollow_cells": hollow[:10], "hollow_count": len(hollow),
                                    "template_cells": n, "template_failures": len(fails), "failures": fails[:12]}
        live["C_test_terrain_q0"] = rows
    finally:
        server.stop()
    result["live"] = live
    a.out.write_text(json.dumps(result, indent=1, default=str) + "\n")
    bad = sum(r["failure_count"] for q in live["A_rotations"].values() for r in q.values())
    bad += sum(r["failure_count"] for r in live["B_integrated_q0"].values())
    bad += sum(r["hollow_count"] + r["template_failures"] for r in live["C_test_terrain_q0"].values())
    bad += sum(len(v) for v in result["offline"]["overlaps"].values())
    print("PASS" if not bad else f"FAIL {bad}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
