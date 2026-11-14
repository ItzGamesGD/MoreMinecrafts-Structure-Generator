"""ST-03 batch 10: ground / road modules MQ-NW, MQ-NE, MQ-SW, MQ-SE (each 51x8x51, st03_ground_*).

NEW DESIGN (2026-11-14). The original road masterplan of the external design package (SHA-256 prefix 0b025a52) is
NOT available; nothing here restores or imitates it. The road plan below is a new design from the owner-approved
direction Q1-Q4 of 2026-11-14 and the structures that exist in this repository.

Contract kept (tools/seam01/data/st03_placements.json, untouched):
  MQ-NW GROUND-NW x5..55  z5..55   MQ-NE GROUND-NE x56..106 z5..55
  MQ-SW GROUND-SW x5..55  z56..106 MQ-SE GROUND-SE x56..106 z56..106
  size 51x8x51, air=include, order 1 (placed first; towers, walls, gate and facilities are placed over them), turns 0.
  y=0 is grade, the same plane as every facility floor, wall footing and tower / gate ground course.

Owner direction (2026-11-14):
  Q1 natural pillager village: dirt path, gravel and cobble mixed; functional but lived-in; no city grid, no fantasy
  Q2 two road levels: main roads 5-6 wide, secondary 2-3 wide; gate -> main facilities first; every entrance linked;
     buildings are never moved and widths never changed to resolve a clash (a clash is reported)
  Q3 partial levelling: roads, junctions and entrances level at grade; elsewhere natural micro-relief is kept
  Q4 lived-in, medium density: barrels, fences, torches, weeds; no passage or entrance blocked; facades not hidden;
     no new chest, loot, spawner or mob contract
Earlier ledger items read as context: Q76/Q77 (per-building grade, local smoothing), Q78 (central roads stone /
cobble, commander approach neat stone, living areas gravel / dirt / cobble, service areas rough gravel and stone,
stone emphasis at intersections), Q79 (roadside military decor without obstruction), Q93 (gate -> roads -> entrances).

The plan is authored in the q=0 structure frame (x, z in 0..111) and cut into the four modules.

  PYTHONPATH=. python experiments/st03-batch10-ground-roads/build.py
"""

import importlib.util
import json
import math
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B8 = _load("batch8_build", ROOT.parent / "st03-batch8-perimeter-walls" / "build.py")
Cells, noise = B8.Cells, B8.noise

N, S, H = 112, 51, 8
MODULES = {"MQ-NW": (5, 5), "MQ-NE": (56, 5), "MQ-SW": (5, 56), "MQ-SE": (56, 56)}  # module -> world origin (x, z)

# ---------------------------------------------------------------------------------------------- road network
# (name, kind, rect x0, z0, x1, z1 inclusive, q=0 frame). kind: main (5-6 wide), plaza, lane (3 wide), apron
# (an entrance apron: the cells in front of a door that join it to a road, 1-3 deep).
ROADS = [
    ("avenue: gate -> plaza", "main", (53, 38, 58, 99)),  # 6 wide, the gate passage is x53..58
    ("plaza before the manor", "plaza", (44, 26, 67, 37)),
    ("barracks street F02 <-> F03", "main", (37, 27, 74, 31)),  # 5 wide
    ("middle road (yard / depots / prison)", "main", (37, 73, 91, 77)),  # 5 wide
    ("south road (gate side: F07, smithy, cart shed, stable)", "main", (7, 93, 99, 97)),  # 5 wide
    ("west manor lane", "lane", (45, 7, 47, 25)),
    ("east manor lane", "lane", (65, 18, 67, 25)),
    ("north wall lane to T-NW", "lane", (13, 7, 47, 9)),
    ("north-west houses lane (F11, F12)", "lane", (13, 18, 47, 20)),
    ("F13 lane", "lane", (21, 21, 23, 31)),
    ("F13 front", "lane", (15, 29, 20, 31)),
    ("north-east houses lane (F15, F14)", "lane", (68, 18, 104, 20)),
    ("T-NE lane", "lane", (102, 13, 104, 17)),
    ("east service lane (F16, F17, F18)", "lane", (89, 21, 91, 72)),
    ("F16 front", "lane", (92, 29, 98, 31)),
    ("F17 front", "lane", (92, 47, 97, 49)),
    ("F18 front", "lane", (92, 59, 97, 61)),
    ("depot lane (F04, F08)", "lane", (72, 32, 74, 72)),
    ("F08 loft stair apron", "apron", (75, 68, 77, 70)),
    ("yard lane (F05, F06)", "lane", (37, 32, 39, 72)),
    ("F05 tower portal", "lane", (29, 42, 36, 44)),
    ("F05 service door", "lane", (29, 48, 36, 50)),
    ("F09 front", "lane", (92, 75, 99, 77)),
    ("F19 front", "lane", (31, 88, 33, 92)),
    ("F20 front", "lane", (46, 89, 48, 92)),
    ("F07 porch apron", "apron", (15, 92, 18, 92)),
    ("F10 portal apron", "apron", (84, 92, 86, 92)),
    ("T-SW door apron", "apron", (7, 98, 9, 98)),
    ("T-SE lane", "lane", (96, 98, 98, 103)),
]

# Entrance cells (the cell just outside each door, q=0), from the built modules (place_check.py offline data and
# the batch-9 tower / gate geometry). These are facts of the existing structures, not part of the new design.
ENTRANCES = {
    "F01 porch": [(55, 26), (56, 26)], "F02 front": [(37, 29)], "F03 gate": [(74, 29)], "F04 front": [(74, 44)],
    "F05 tower portal": [(29, 43)], "F05 service door": [(29, 49)], "F06 road gate": [(37, 62)],
    "F07 porch": [(16, 92), (17, 92)], "F08 unloading bay": [(74, 60)], "F08 loft stair": [(75, 68)],
    "F09 front": [(97, 75)], "F10 portal": [(85, 92)], "F11": [(18, 18)], "F12": [(30, 18)], "F13": [(17, 29)],
    "F14": [(93, 18)], "F15": [(80, 18)], "F16": [(95, 29)], "F17": [(95, 47)], "F18": [(96, 59)],
    "F19": [(32, 88)], "F20": [(47, 89)], "T-NW door": [(13, 8)], "T-NE door": [(103, 13)],
    "T-SE door": [(98, 103)], "T-SW door": [(8, 98)], "GATE passage": [(x, 99) for x in range(53, 59)],
}
# Internal connections that need no road (one facility opening into its neighbour)
INTERNAL = {"F05 loggia south -> F06": (20, 52), "F06 armory apron north -> F05": (20, 51)}


def footprints():
    """Every non-ground placement footprint, q=0."""
    return {e["placement"]: e["footprint"] for e in A.manifest(0) if not e["placement"].startswith("GROUND")}


def in_rect(x, z, r):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def plan():
    """Road kind per cell, plus the footprint owner per cell."""
    fp = footprints()
    owner = {}
    for name, r in fp.items():
        for x in range(r[0], r[2] + 1):
            for z in range(r[1], r[3] + 1):
                owner[(x, z)] = name
    road, clash = {}, []
    rank = {"plaza": 4, "main": 3, "lane": 2, "apron": 1}
    for name, kind, r in ROADS:
        for x in range(r[0], r[2] + 1):
            for z in range(r[1], r[3] + 1):
                if (x, z) in owner:
                    clash.append([name, x, z, owner[(x, z)]])
                    continue
                if rank[kind] > rank.get(road.get((x, z), (None, ""))[1], 0):
                    road[(x, z)] = (name, kind)
    return road, owner, clash


# ---------------------------------------------------------------------------------------------- materials
def smooth(x, z, scale, salt):
    """Value noise in 0..1, bilinear between lattice points `scale` apart (deterministic)."""
    gx, gz = x / scale, z / scale
    x0, z0 = math.floor(gx), math.floor(gz)
    fx, fz = gx - x0, gz - z0
    v = lambda a, b: noise(a, b, 1000, salt) / 999.0
    top = v(x0, z0) * (1 - fx) + v(x0 + 1, z0) * fx
    bot = v(x0, z0 + 1) * (1 - fx) + v(x0 + 1, z0 + 1) * fx
    return top * (1 - fz) + bot * fz


def near(road, x, z, kinds, d):
    return any(road.get((x + i, z + k), (None, ""))[1] in kinds for i in range(-d, d + 1) for k in range(-d, d + 1))


def road_block(road, x, z):
    name, kind = road[(x, z)]
    p = smooth(x, z, 3.0, 11)  # patches, not speckle
    r = noise(x, z, 20, 5)
    junction = sum(1 for n2, k2, rr in ROADS if k2 in ("main", "plaza") and in_rect(x, z, rr)) >= 2
    if kind == "plaza" or junction or (kind == "main" and name.startswith("avenue") and z <= 45):
        # Q78: commander approach / square: neat stone, still mixed
        # value noise clusters around the middle, so the middle of the list is the clean stone brick
        return ("cobblestone", "andesite", "stone_bricks", "stone_bricks", "stone_bricks", "polished_andesite",
                "cracked_stone_bricks", "mossy_stone_bricks", "cobblestone", "gravel")[int(p * 7.99) if r else 9]
    if kind == "main":
        if p < 0.30:
            return "cobblestone" if r % 4 else "mossy_cobblestone"
        if p < 0.48:
            return "gravel"
        if p < 0.70:
            return "dirt_path"
        if p < 0.82:
            return "andesite" if r % 3 else "stone"
        if p < 0.92:
            return "coarse_dirt"
        return "cobblestone"
    # lanes and aprons: trodden earth with gravel and cobble
    if p < 0.38:
        return "dirt_path"
    if p < 0.58:
        return "coarse_dirt"
    if p < 0.78:
        return "gravel"
    if p < 0.90:
        return "cobblestone"
    return "packed_mud" if r % 2 else "dirt_path"


def ground_block(x, z):
    p = smooth(x, z, 5.0, 23)
    r = noise(x, z, 12, 9)
    if p > 0.82:  # bare patches: coarse / rooted dirt (grass spreads onto exposed plain dirt on a random tick)
        return "coarse_dirt" if r % 3 else "rooted_dirt"
    if p < 0.10 and r < 4:
        return "moss_block"
    return "grass_block"


# ---------------------------------------------------------------------------------------------- the 112 x 112 plan
def design():
    road, owner, clash = plan()
    assert not clash, clash[:5]
    G = {}  # (x, y, z) world q=0 -> (block, props)
    put = lambda x, y, z, b, **p: G.__setitem__((x, y, z), (b, {k: str(v).lower() for k, v in p.items()}))
    inside = lambda x, z: 5 <= x <= 106 and 5 <= z <= 106
    ent_cells = {c for v in ENTRANCES.values() for c in v}
    # ground course and roads (y0); cells under other footprints get plain dirt (they are overwritten)
    for x in range(5, 107):
        for z in range(5, 107):
            if (x, z) in owner:
                put(x, 0, z, "coarse_dirt")  # overwritten by that placement; coarse dirt: grass does not spread onto it
            elif (x, z) in road:
                put(x, 0, z, road_block(road, x, z))
            else:
                put(x, 0, z, ground_block(x, z))
    # ragged edges: one cell beside lanes / main roads, trodden earth mixed into the grass (still level, walkable)
    fringe = set()
    for x in range(5, 107):
        for z in range(5, 107):
            if (x, z) in road or (x, z) in owner:
                continue
            if near(road, x, z, ("main", "lane", "plaza"), 1) and noise(x, z, 5, 77) < 2:
                put(x, 0, z, ("coarse_dirt", "dirt_path", "gravel", "coarse_dirt", "rooted_dirt")[noise(x, z, 5, 78)])
                fringe.add((x, z))
    # keep-clear zone: roads, fringe, entrance surroundings, 2 blocks around every footprint, 1 block inside the walls
    def clear(x, z, d_fp=2):
        if (x, z) in road or (x, z) in fringe:
            return False
        if any(abs(x - ex) <= 2 and abs(z - ez) <= 2 for ex, ez in ent_cells):
            return False
        if any((x + i, z + k) in owner for i in range(-d_fp, d_fp + 1) for k in range(-d_fp, d_fp + 1)):
            return False
        return 7 <= x <= 104 and 7 <= z <= 104
    # Q3: natural micro-relief away from roads and buildings - low grass mounds of one (rarely two) blocks
    mound = {}
    for x in range(5, 107):
        for z in range(5, 107):
            if not clear(x, z, 3) or near(road, x, z, ("main", "lane", "plaza", "apron"), 2):
                continue
            h = smooth(x, z, 6.0, 41)
            if h > 0.72:
                mound[(x, z)] = 2 if h > 0.86 and noise(x, z, 3, 1) == 0 else 1
    for (x, z), hgt in list(mound.items()):  # a 2-high cell only inside a mound, so every step is one block
        if hgt == 2 and any((x + i, z + k) not in mound for i in (-1, 0, 1) for k in (-1, 0, 1)):
            mound[(x, z)] = 1
    for (x, z), hgt in mound.items():
        for y in range(0, hgt):
            put(x, y, z, "dirt" if y < hgt - 1 or noise(x, z, 4, 2) else "coarse_dirt")
        put(x, hgt, z, "grass_block")
    # Q4: decoration clusters beside the roads (moderate density), weeds, torch posts at junctions and the plaza
    used = set()
    decor = []

    def free(cells):
        return all(clear(x, z) and (x, z) not in mound and (x, z) not in used for x, z in cells)

    def place(kind, cells, blocks):
        for (x, y, z, b, p) in blocks:
            put(x, y, z, b, **p)
        for c in cells:
            used.add(c)
        decor.append({"kind": kind, "cells": [list(c) for c in cells]})

    # candidate anchors: cells 2 beside a road edge, along each road, every ~11 blocks, alternating sides
    for name, kind, r in ROADS:
        if kind == "apron":
            continue
        horiz = (r[2] - r[0]) >= (r[3] - r[1])
        length = (r[2] - r[0]) if horiz else (r[3] - r[1])
        step = 11 if kind != "lane" else 13
        for i, t in enumerate(range(3, length - 2, step)):
            side = (i + noise(t, len(name), 2, 3)) % 2
            if horiz:
                x, z = r[0] + t, (r[1] - 2) if side == 0 else (r[3] + 2)
                along = (1, 0)
                out = (0, -1) if side == 0 else (0, 1)
            else:
                x, z = (r[0] - 2) if side == 0 else (r[2] + 2), r[1] + t
                along = (0, 1)
                out = (-1, 0) if side == 0 else (1, 0)
            pick = noise(x, z, 6, 61)
            a = (x + along[0], z + along[1])
            b = (x - along[0], z - along[1])
            if pick == 0 and free([(x, z), a]):  # barrels, one stacked
                place("barrels", [(x, z), a], [(x, 0, z, "coarse_dirt", {}), (a[0], 0, a[1], "coarse_dirt", {}),
                                               (x, 1, z, "barrel", {"facing": "up", "open": False}),
                                               (a[0], 1, a[1], "barrel", {"facing": "up", "open": False}),
                                               (x, 2, z, "barrel", {"facing": "up", "open": False})])
            elif pick == 1 and free([(x, z), a, b]):  # log pile along the road
                ax = "x" if along[0] else "z"
                place("log pile", [(x, z), a, b], [*[(c[0], 0, c[1], "coarse_dirt", {}) for c in ((x, z), a, b)],
                                                   *[(c[0], 1, c[1], "spruce_log", {"axis": ax}) for c in ((x, z), a, b)],
                                                   (x, 2, z, "spruce_log", {"axis": ax})])
            elif pick == 2 and free([(x, z), a, b]):  # fence rail with a torch on its end post
                place("fence rail + torch", [(x, z), a, b],
                      [*[(c[0], 1, c[1], "spruce_fence", {}) for c in ((x, z), a, b)],
                       (a[0], 2, a[1], "torch", {})])
            elif pick == 3 and free([(x, z), a]):  # hay
                place("hay", [(x, z), a], [(x, 0, z, "coarse_dirt", {}), (a[0], 0, a[1], "coarse_dirt", {}),
                                           (x, 1, z, "hay_block", {"axis": "y"}),
                                           (a[0], 1, a[1], "hay_block", {"axis": "x" if along[0] else "z"})])
            elif pick == 4 and free([(x, z)]):  # torch post
                place("torch post", [(x, z)], [(x, 1, z, "spruce_fence", {}), (x, 2, z, "torch", {})])
            elif pick == 5 and free([(x, z), a]):  # barrel and a chopping block
                place("barrel + chopping block", [(x, z), a],
                      [(x, 0, z, "coarse_dirt", {}), (a[0], 0, a[1], "coarse_dirt", {}),
                       (x, 1, z, "barrel", {"facing": "up", "open": False}),
                       (a[0], 1, a[1], "stripped_spruce_log", {"axis": "y"})])
    # torch posts at the plaza corners and at the main junctions (lighting, off the carriageway)
    for x, z in ((43, 25), (68, 25), (43, 38), (68, 38), (52, 72), (59, 72), (52, 92), (59, 92), (36, 32), (75, 32)):
        if free([(x, z)]):
            place("torch post", [(x, z)], [(x, 1, z, "spruce_fence", {}), (x, 2, z, "torch", {})])
    # weeds on grass (not on roads, not under or next to decor)
    for x in range(5, 107):
        for z in range(5, 107):
            top = 0 if (x, z) not in mound else mound[(x, z)]
            if (x, z) in used or (x, z) in owner or (x, z) in road or (x, z) in fringe:
                continue
            if any(abs(x - ex) <= 1 and abs(z - ez) <= 1 for ex, ez in ent_cells):
                continue
            if G[(x, top, z)][0] != "grass_block" or (x, top + 1, z) in G:
                continue
            w = noise(x, z, 9, 91)
            if w == 0:
                put(x, top + 1, z, "short_grass")
            elif w == 1 and noise(x, z, 3, 92) == 0:
                put(x, top + 1, z, "fern")
    # grass / dirt path must not lie under a block (it would turn to dirt on a random tick); plain dirt only where
    # it is covered (exposed plain dirt next to grass would turn to grass on a random tick)
    for (x, y, z), (b, p) in list(G.items()):
        above = G.get((x, y + 1, z))
        if b in ("grass_block", "dirt_path") and above and above[0] not in ("short_grass", "fern", "torch"):
            put(x, y, z, "dirt" if b == "grass_block" else "coarse_dirt")
    return G, {"road": road, "fringe": fringe, "mound": mound, "decor": decor, "owner": owner}


def module_cells(G, mid):
    ox, oz = MODULES[mid]
    c = Cells((S, H, S))
    for (x, y, z), (b, p) in G.items():
        if ox <= x < ox + S and oz <= z < oz + S:
            c[(x - ox, y, z - oz)] = ("minecraft:" + b, p)
    return c


_CACHE = {}


def designs():
    if "G" not in _CACHE:
        _CACHE["G"], _CACHE["info"] = design()
    return _CACHE["G"], _CACHE["info"]


BUILDINGS = {
    mid.lower().replace("mq-", "ground_"): dict(module=mid, placements=(f"GROUND-{mid[3:]}",),
                                                design=(lambda m=mid: module_cells(designs()[0], m)),
                                                size=(S, H, S), door=None)
    for mid in MODULES
}


def main():
    mods = A.modules()
    (ROOT / "out").mkdir(exist_ok=True)
    G, info = designs()
    for key, b in BUILDINGS.items():
        module = mods[b["module"]]
        assert module["size"] == list(b["size"]) and module["air"] == "include", (key, module)
        cells = b["design"]()
        with tempfile.TemporaryDirectory() as d:
            result = export_module(module, dict(cells), Path(d) / "pack")
            shutil.copyfile(result.config.nbt_path, ROOT / "out" / f"{module['file']}.nbt")
            shutil.copyfile(result.config.source, ROOT / "out" / f"{module['file']}.schem")
            (ROOT / "out" / f"{module['file']}.export-report.json").write_text(
                json.dumps(result.report, indent=2, sort_keys=True) + "\n")
        print(f"{module['file']}.nbt: {len(cells)} authored cells, size {module['size']}")
    kinds = {}
    for _, k in info["road"].values():
        kinds[k] = kinds.get(k, 0) + 1
    print("road cells", kinds, "fringe", len(info["fringe"]), "mound cells", len(info["mound"]),
          "decor clusters", len(info["decor"]))


if __name__ == "__main__":
    main()
