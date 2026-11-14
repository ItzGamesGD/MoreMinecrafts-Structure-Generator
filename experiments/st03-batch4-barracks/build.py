"""ST-03 barracks batch: F02 / F03 / F04 (M-barracks_a / _b / _c, each 13x12x11).

Contract kept (tools/seam01/data/st03_placements.json, untouched): size 13x12x11 (x, y, z), air=include, floor y=0,
local_turns 0. F02 x=24..36, z=24..34 (west of the central street, entrance faces +x / east);
F03 x=75..87, z=24..34 and F04 x=75..87, z=39..49 (east of the street, entrances face -x / west).

Free design brief ST03-IMPLEMENT-05. The Q18-Q26 barracks decisions were read as reference, not as a recipe.

F02 "standard hall" - symmetrical, gable-front to the street. Stone ground storey under a jettied dark-oak and plaster
  timber gable carried on brackets, steep dark-oak roof with eave brackets, a jettied plastered cross gable centred on
  each long side, small dark-oak-shuttered windows in a regular rhythm. Inside: four bunk frames (8 berths) either
  side of a central aisle, a ladder in the axis to a rear storage loft with the
  sergeant's bed, a mess table under the loft.
F03 "stone keep" - fortified. All-stone hall with crow-stepped gables front and rear, deepslate-tile roof, a round-
  arched gate with a raised portcullis grille under an oak bretèche (machicolation box) on stone corbels, buttressed
  flanks with barred slits, a chimney stack through the north slope. Inside: equipment barracks: bunk frames, weapon
  racks, an arms table, a hearth, an armoury under and on a rear loft reached by a ladder.
F04 "timber lodge" - residential/logistics. Spruce gambrel roof with a projecting hoist hood (beam, chain, hoisted bale),
  dark-oak frame with mud-brick nogging, loft hay door and louvres in the street gable, pent canopy over the door, broad
  shuttered windows with flower ledges, a louvred ridge vent, a stone chimney on the rear gable. Inside: four single
  beds under a big loft reached by a timber stair, stove, dining table, stores; two more beds and hay on the loft.

All containers are empty (block-entity allow-list); loot is a runtime decision. No mobs, spawners or loot authored.

  PYTHONPATH=. python experiments/st03-batch4-barracks/build.py
"""

import importlib.util
import json
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


B1 = _load("batch1_build", ROOT.parent / "st03-batch1-support" / "build.py")
B3 = _load("batch3_build", ROOT.parent / "st03-batch3-military" / "build.py")
Cells, stone, floor_stone = B1.Cells, B1.stone, B1.floor_stone
plinth, noise, path_stone = B3.plinth, B3.noise, B3.path_stone

W, H, D = 13, 12, 11
PLASTER = "calcite"  # daub infill between the F02 timber frame
INFILL = "mud_bricks"  # F04 brick nogging between the dark-oak frame (F02 uses plaster)

DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
CCW = {"north": "west", "west": "south", "south": "east", "east": "north"}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def stairs(c, x, y, z, mat, facing, half="bottom", shape="straight"):
    c.put(x, y, z, f"{mat}_stairs", facing=facing, half=half, shape=shape)


def trap(c, x, y, z, mat, facing, open_=True, half="bottom"):
    c.put(x, y, z, f"{mat}_trapdoor", facing=facing, half=half, open=open_, powered=False, waterlogged=False)


def door(c, x, z, mat, facing, hinge, open_=False, y=1):
    c.put(x, y, z, f"{mat}_door", facing=facing, half="lower", hinge=hinge, open=open_, powered=False)
    c.put(x, y + 1, z, f"{mat}_door", facing=facing, half="upper", hinge=hinge, open=open_, powered=False)


def bed(c, x, y, z, color, facing):
    """Bed whose head is at (x, y, z); `facing` points from foot to head."""
    dx, dz = DV[facing]
    c.put(x, y, z, f"{color}_bed", facing=facing, part="head", occupied=False)
    c.put(x - dx, y, z - dz, f"{color}_bed", facing=facing, part="foot", occupied=False)


def corner(kind, f, g):
    return f"{kind}_{'left' if g == CCW[f] else 'right'}"


def hroof(c, hmap, mat, ridge, skip=()):
    """Roof surface from a height map {(x, z): y}: a stair faces uphill, valleys get inner corners, hips outer
    corners, local maxima get `ridge(x, z)` (block id, props). `mat(x, z)` gives the stair material prefix."""
    def h(x, z):
        return hmap.get((x, z), -99)

    for (x, z), y in hmap.items():
        if (x, z) in skip:
            continue
        up = [d for d in DV if h(x + DV[d][0], z + DV[d][1]) > y]
        m = mat(x, z)
        if not up:
            diag = [(a, b) for a in ("north", "south") for b in ("west", "east")
                    if h(x + DV[a][0] + DV[b][0], z + DV[a][1] + DV[b][1]) > y]
            if len(diag) == 1:
                stairs(c, x, y, z, m, diag[0][0], shape=corner("outer", *diag[0]))
            else:
                bid, props = ridge(x, z)
                c.put(x, y, z, bid, **props)
        elif len(up) == 1:
            stairs(c, x, y, z, m, up[0])
        elif len(up) == 2 and OPP[up[0]] != up[1]:
            stairs(c, x, y, z, m, up[0], shape=corner("inner", up[0], up[1]))
        else:
            bid, props = ridge(x, z)
            c.put(x, y, z, bid, **props)


def base_course(x, y, z):
    """Rough stone footing course of the barracks walls (stone family, no deepslate - that is the armory's)."""
    return ["cobblestone", "stone_bricks", "mossy_cobblestone", "cobblestone", "andesite", "stone_bricks",
            "cobblestone"][noise(x, z, 7, y + 11)]


def apron(c):
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, path_stone(x, z))


# =============================================================================================== F02 standard hall
def f02():
    """Front (street) = +x. Ground storey walls x=1..11, z=1..9; jettied timber gable at x=12; ridge along x."""
    c = Cells((W, H, D))
    rf = lambda z: 6 + min(z, 10 - z)  # eave y=6 at z=0/10, ridge y=11 at z=5
    apron(c)
    for x in range(2, 11):
        for z in range(2, 9):
            c.put(x, 0, z, "spruce_planks" if z not in (4, 5, 6) or x < 5 else "stripped_spruce_log",
                  **({"axis": "x"} if z in (4, 5, 6) and x >= 5 else {}))
    for x in range(5, 11):
        c.put(x, 0, 5, "polished_andesite")
    for z in (4, 5, 6):
        c.put(11, 0, z, "stone_bricks")
    for z in range(1, 10):
        c.put(12, 0, z, "stone_bricks" if z in (4, 5, 6) else "polished_andesite")

    posts = (1, 5, 7, 11)
    # long walls z=1 / z=9: footing y1, stone y2-3, timber y4-5, wall plate y6
    for z in (1, 9):
        for x in range(1, 13):
            if x <= 11:
                c.put(x, 1, z, base_course(x, 1, z))
                for y in (2, 3):
                    c.put(x, y, z, stone(x, y, z))
            for y in (4, 5):
                if x in posts or x == 12:
                    c.put(x, y, z, "dark_oak_log", axis="y")
                else:
                    c.put(x, y, z, PLASTER)
            c.put(x, 6, z, "stripped_dark_oak_log", axis="x")
        for x in (1, 11):  # quoins
            for y in (1, 2, 3):
                c.put(x, y, z, "polished_andesite" if y % 2 else "stone_bricks")
        c.put(12, 3, z, "dark_oak_stairs", facing="west", half="top", shape="straight")  # jetty corner bracket
    # small shuttered windows, regular rhythm (x=3, 9 low; x=6 in the timber band), symmetric about x=6
    for z, out in ((1, 0), (9, 10)):
        face = "north" if z == 1 else "south"
        for x in (3, 9):
            for y in (2, 3):
                c.put(x, y, z, "glass_pane")
                trap(c, x - 1, y, out, "dark_oak", face)
                trap(c, x + 1, y, out, "dark_oak", face)
            c.put(x, 1, out, "stone_brick_stairs", facing=OPP[face], half="top", shape="straight")  # sill
        c.put(6, 4, z, "glass_pane")
        c.put(6, 5, z, "glass_pane")
    # eave brackets under the overhang at the post positions
    for x in posts:
        stairs(c, x, 5, 0, "dark_oak", "south", half="top")
        stairs(c, x, 5, 10, "dark_oak", "north", half="top")

    # rear gable x=1: all stone, buttresses, loft window
    for z in range(1, 10):
        for y in range(1, rf(z)):
            if y >= 1 and z in (1, 9) and y <= 6:
                continue
            c.put(1, y, z, base_course(1, y, z) if y == 1 else stone(1, y, z))
    for z in (3, 7):
        for y in (1, 2, 3):
            c.put(0, y, z, base_course(0, y, z) if y == 1 else stone(0, y, z))
        stairs(c, 0, 4, z, "stone_brick", "east")
    c.put(1, 6, 5, "glass_pane"); c.put(1, 7, 5, "glass_pane")
    c.put(1, 8, 5, "chiseled_stone_bricks")
    c.put(1, 9, 5, "iron_bars")

    # front: stone ground wall x=11 with a 3-wide doorway, open dark-oak leaves folded against the jambs
    for z in range(2, 9):
        for y in (1, 2, 3):
            c.put(11, y, z, base_course(11, y, z) if y == 1 else stone(11, y, z))
    for z in (3, 7):
        for y in (1, 2):
            c.put(11, y, z, "polished_andesite" if y == 1 else "chiseled_stone_bricks")
    for z in (4, 5, 6):
        for y in (1, 2):
            c.pop((11, y, z), None)
    for z in range(3, 8):
        c.put(11, 3, z, "stripped_dark_oak_log", axis="z")  # lintel
    door(c, 11, 4, "dark_oak", "west", "right", open_=True)
    door(c, 11, 6, "dark_oak", "west", "left", open_=True)
    for z in (2, 8):  # small windows either side of the door, under the jetty
        c.put(11, 2, z, "glass_pane")
    # jetty: beam y4 on brackets, timber gable x=12 up to the roof
    for z in range(1, 10):
        c.put(12, 4, z, "stripped_dark_oak_log", axis="z")
        if 2 <= z <= 8:
            c.put(11, 4, z, "stripped_dark_oak_log", axis="z")
    for z in (3, 7):
        stairs(c, 12, 3, z, "dark_oak", "west", half="top")
    for z in range(1, 10):
        for y in range(5, rf(z)):
            if z in (1, 3, 7, 9) or (z == 5 and y >= 8):
                c.put(12, y, z, "dark_oak_log", axis="y")
            elif y == 7:
                c.put(12, y, z, "stripped_dark_oak_log", axis="z")
            else:
                c.put(12, y, z, PLASTER)
    for z in (4, 5, 6):  # hall window over the door
        for y in (5, 6):
            c.put(12, y, z, "glass_pane")
    c.put(12, 9, 4, "spruce_trapdoor", facing="east", half="bottom", open=True, powered=False, waterlogged=False)
    c.put(12, 9, 6, "spruce_trapdoor", facing="east", half="bottom", open=True, powered=False, waterlogged=False)
    c.put(12, 3, 5, "lantern", hanging=True)
    c.put(12, 2, 3, "white_wall_banner", facing="east")
    c.put(12, 2, 7, "white_wall_banner", facing="east")

    # roof: dark oak, spruce barge boards, ridge beam; a jettied cross gable centred on each long side (x=4..8), its
    # plastered timber face flush with the eave line and carried on the eave brackets - the street gable's motif again
    hmap = {(x, z): rf(z) for x in range(W) for z in range(D)}
    cross = set()
    for x in range(4, 9):
        for z in (0, 1, 2, 8, 9, 10):
            hmap[(x, z)] = max(hmap[(x, z)], 9 - abs(x - 6))
            cross.add((x, z))
    hroof(c, hmap, lambda x, z: "spruce" if x in (0, 12) or ((x, z) in cross and z in (0, 10)) else "dark_oak",
          lambda x, z: ("dark_oak_log", {"axis": "x"}) if x in (0, 12) else
          ("stripped_dark_oak_log", {"axis": "z" if (x, z) in cross else "x"}))
    for zf, zw in ((0, 1), (10, 9)):
        for x in range(4, 9):
            c.put(x, 6, zf, "stripped_dark_oak_log", axis="x")  # jetty sill beam
            c.put(x, 6, zw, "stripped_dark_oak_log", axis="x")
            for y in range(7, 9 - abs(x - 6)):
                c.put(x, y, zf, "dark_oak_log" if x in (4, 8) else PLASTER, **({"axis": "y"} if x in (4, 8) else {}))
        c.put(6, 7, zf, "glass_pane")
        c.put(6, 8, zf, "glass_pane")
        for x in (4, 8):
            stairs(c, x, 5, zf, "dark_oak", "south" if zf == 0 else "north", half="top")
    # ---- interior
    # loft over the rear (x=2..4), floor y=4, railing, ladder on a post in the axis
    for x in (2, 3, 4):
        for z in range(2, 9):
            c.put(x, 4, z, "spruce_planks")
    for z in range(2, 9):
        if z != 5:
            c.put(4, 5, z, "dark_oak_fence")
    for y in (1, 2, 3):
        c.put(4, y, 5, "dark_oak_log", axis="y")
    for y in (1, 2, 3, 4):
        c.put(5, y, 5, "ladder", facing="east", waterlogged=False)
    for z in (2, 8):
        c.put(4, 3, z, "stripped_dark_oak_log", axis="y")
        c.put(4, 2, z, "stripped_dark_oak_log", axis="y")
        c.put(4, 1, z, "stripped_dark_oak_log", axis="y")
    # tie beams with lanterns
    for x in (7, 10):
        for z in range(2, 9):
            c.put(x, 6, z, "stripped_dark_oak_log", axis="z")
        c.put(x, 5, 5, "lantern", hanging=True)
    # bunks: lower bed y1, plank deck y2, upper bed y3, posts at the foot
    for x in (6, 8):
        for zh, zf, face in ((2, 3, "north"), (8, 7, "south")):
            bed(c, x, 1, zh, "gray", face)
            for zz in (zh, zf):
                c.put(x, 2, zz, "spruce_slab", type="top")
            bed(c, x, 3, zh, "gray", face)
    for x in (5, 9):
        for zf in (3, 7):
            for y in (1, 2, 3):
                c.put(x, y, zf, "dark_oak_fence")
    # between the bunks: footlocker chest + banner (north), barrel + banner (south)
    c.put(7, 1, 2, "chest", facing="south", type="single")
    c.put(7, 1, 8, "barrel", facing="north", open=False)
    c.put(7, 3, 2, "white_wall_banner", facing="south")
    c.put(7, 3, 8, "white_wall_banner", facing="north")
    c.put(5, 1, 2, "spruce_slab", type="top")
    c.put(5, 2, 2, "candle", candles=3, lit=True, waterlogged=False)
    c.put(5, 1, 8, "spruce_slab", type="top")
    c.put(5, 2, 8, "candle", candles=2, lit=True, waterlogged=False)
    c.put(9, 1, 2, "spruce_slab", type="top")
    c.put(9, 1, 8, "spruce_slab", type="top")
    c.put(9, 2, 2, "flower_pot")
    # weapon racks inside the door
    for z, f in ((2, "south"), (8, "north")):
        c.put(10, 1, z, "stripped_spruce_log", axis="x")
        c.put(10, 2, z, "exposed_lightning_rod", facing="up")
        c.put(10, 3, z, "grindstone", face="wall", facing=f)
    # mess under the loft: table and stools, stores in the corners
    for z in (4, 6):
        c.put(2, 1, z, "spruce_slab", type="top")
        stairs(c, 3, 1, z, "spruce", "east")
    c.put(2, 1, 5, "spruce_slab", type="top")
    c.put(2, 2, 5, "candle", candles=4, lit=True, waterlogged=False)
    c.put(2, 2, 4, "flower_pot")
    c.put(2, 1, 2, "barrel", facing="up", open=False)
    c.put(3, 1, 2, "hay_block", axis="x")
    c.put(2, 2, 2, "hay_block", axis="z")
    c.put(2, 1, 8, "barrel", facing="east", open=False)
    c.put(3, 1, 8, "barrel", facing="up", open=False)
    c.put(3, 3, 5, "lantern", hanging=True)
    # loft: sergeant's bed, stores
    bed(c, 2, 5, 7, "red", "west")
    c.put(2, 5, 8, "spruce_slab", type="bottom")
    c.put(2, 5, 2, "barrel", facing="up", open=False)
    c.put(3, 5, 2, "hay_block", axis="y")
    c.put(2, 5, 3, "hay_block", axis="x")
    c.put(2, 6, 2, "barrel", facing="east", open=False)
    c.put(3, 5, 5, "lantern", hanging=False)

    # ---- street supplies under the jetty and the eaves
    c.put(12, 1, 1, "barrel", facing="up", open=False)
    c.put(12, 1, 9, "hay_block", axis="z")
    return c


# ================================================================================================= F03 stone keep
def f03():
    """Front (street) = -x. Crow-stepped gables x=1 (front) / x=12 (rear), long walls z=1 / z=9, ridge along x at
    z=5 (y=10), crowning step y=11. Oak bretèche on stone corbels over a round-arched gate; buttressed flanks."""
    c = Cells((W, H, D))
    rf = lambda z: 5 + min(z, 10 - z)  # eave y=5 at z=0/10, ridge y=10 at z=5
    T = {0: 6, 1: 8, 2: 8, 3: 10, 4: 10, 5: 11, 6: 10, 7: 10, 8: 8, 9: 8, 10: 6}  # crow-step tops
    apron(c)
    for x in range(2, 12):
        for z in range(2, 9):
            c.put(x, 0, z, "polished_andesite" if z == 5 else floor_stone(x, z))
    for z in (4, 5, 6):
        c.put(0, 0, z, "stone_bricks")
        c.put(1, 0, z, "polished_andesite" if z == 5 else "stone_bricks")

    def wall(x, y, z):
        c.put(x, y, z, plinth(x, y, z) if y == 1 else stone(x, y, z))

    # long walls z=1 / z=9 (y1..5) with buttresses on the outer face and barred slits between them
    for z, out, face in ((1, 0, "south"), (9, 10, "north")):
        for x in range(1, 13):
            for y in range(1, 6):
                wall(x, y, z)
        for x in (4, 8):
            for y in (1, 2, 3):
                wall(x, y, out)
            stairs(c, x, 4, out, "stone_brick", face)
        for x in (2, 6, 10):
            for y in (2, 3):
                c.put(x, y, z, "iron_bars")
    # crow-stepped gables, slab-capped steps, dark quoins, string course
    for xg in (1, 12):
        for z in range(D):
            for y in range(1, T[z] + 1):
                wall(xg, y, z)
            if T[z] < 11:
                c.put(xg, T[z], z, "stone_brick_slab", type="bottom")
            else:
                c.put(xg, T[z], z, "chiseled_stone_bricks")
            if T[z] > 5:
                c.put(xg, 5, z, "polished_andesite")
        for z in (0, 1, 9, 10):
            for y in range(1, 5):
                c.put(xg, y, z, "polished_andesite" if (y + z) % 2 else "stone_bricks")
    # front gable: round-arched gate (3 wide), raised portcullis grille, open dark-oak leaves
    for z in (4, 5, 6):
        for y in (1, 2):
            c.put(1, y, z, "air")
    c.put(1, 3, 5, "iron_bars")
    stairs(c, 1, 3, 4, "stone_brick", "north", half="top")
    stairs(c, 1, 3, 6, "stone_brick", "south", half="top")
    c.put(1, 4, 5, "chiseled_stone_bricks")
    door(c, 1, 4, "dark_oak", "west", "right", open_=True)
    door(c, 1, 6, "dark_oak", "west", "left", open_=True)
    # bretèche: oak box on stone corbels above the gate, pent deepslate roof, loop in the middle
    for z in (4, 6):
        stairs(c, 0, 3, z, "stone_brick", "east", half="top")
    for z in (4, 5, 6):
        c.put(0, 4, z, "stripped_dark_oak_log", axis="z")
        stairs(c, 0, 6, z, "deepslate_tile", "east")
    c.put(0, 5, 4, "dark_oak_log", axis="y")
    c.put(0, 5, 6, "dark_oak_log", axis="y")
    c.put(0, 5, 5, "dark_oak_fence")
    c.put(0, 3, 5, "lantern", hanging=True)
    for y in (7, 8):  # high loop in the gable
        c.put(1, y, 5, "iron_bars")
    # front corner buttresses
    for z in (1, 9):
        for y in (1, 2, 3):
            wall(0, y, z)
        stairs(c, 0, 4, z, "stone_brick", "east")
    # rear gable slits
    for z in (3, 7):
        for y in (2, 3):
            c.put(12, y, z, "iron_bars")
    for y in (7, 8):
        c.put(12, y, 5, "iron_bars")

    # roof between the gables: deepslate tiles, polished-deepslate ridge
    hmap = {(x, z): rf(z) for x in range(2, 12) for z in range(D)}
    hroof(c, hmap, lambda x, z: "deepslate_tile", lambda x, z: ("polished_deepslate", {}))
    # chimney stack in the north wall near the rear, rising through the roof; hearth below
    for x in (10, 11):
        for y in range(6, 11):
            c.put(x, y, 1, stone(x, y, 1))
        c.put(x, 11, 1, "stone_brick_slab", type="bottom")
        c.put(x, 10, 1, "polished_andesite")
    c.put(10, 1, 1, "furnace", facing="south", lit=False)
    c.put(10, 2, 1, "stone_bricks")
    stairs(c, 10, 3, 2, "stone_brick", "south", half="top")

    # ---- interior x=2..11, z=2..8
    for x in (4, 7):  # tie beams with lanterns
        for z in range(2, 9):
            c.put(x, 5, z, "stripped_dark_oak_log", axis="z")
        c.put(x, 4, 5, "lantern", hanging=True)
    # loft over the rear x=9..11 (floor y4), ladder against the north wall at x=11
    for x in (9, 10, 11):
        for z in range(2, 9):
            if (x, z) != (11, 2):
                c.put(x, 4, z, "dark_oak_planks")
    for z in range(2, 9):
        c.put(9, 5, z, "dark_oak_fence")
    for y in (1, 2, 3, 4):
        c.put(11, y, 2, "ladder", facing="south", waterlogged=False)
    for z in (3, 7):
        for y in (1, 2, 3):
            c.put(9, y, z, "dark_oak_log", axis="y")
    # bunk frames along the long walls (x=3, x=5), heads at the walls
    for x in (3, 5):
        for zh, zf, face in ((2, 3, "north"), (8, 7, "south")):
            bed(c, x, 1, zh, "black", face)
            for zz in (zh, zf):
                c.put(x, 2, zz, "dark_oak_slab", type="top")
            bed(c, x, 3, zh, "black", face)
    for zf in (3, 7):
        for y in (1, 2, 3):
            c.put(6, y, zf, "dark_oak_fence")
    c.put(4, 1, 2, "chest", facing="south", type="single")
    c.put(4, 1, 8, "barrel", facing="north", open=False)
    c.put(4, 3, 2, "white_wall_banner", facing="south")
    c.put(4, 3, 8, "white_wall_banner", facing="north")
    # weapon racks inside the gate
    for z, f in ((2, "south"), (8, "north")):
        c.put(2, 1, z, "stripped_dark_oak_log", axis="x")
        c.put(2, 2, z, "exposed_lightning_rod", facing="up")
        c.put(2, 3, z, "grindstone", face="wall", facing=f)
    # arms table with benches
    for x in (6, 7):
        c.put(x, 1, 5, "dark_oak_slab", type="top")
        stairs(c, x, 1, 4, "spruce", "north")
        stairs(c, x, 1, 6, "spruce", "south")
    c.put(6, 2, 5, "heavy_weighted_pressure_plate", power=0)
    c.put(7, 2, 5, "iron_chain", axis="x")
    # armoury under the loft
    c.put(11, 1, 3, "grindstone", face="floor", facing="west")
    c.put(11, 1, 4, "barrel", facing="up", open=False)
    c.put(11, 2, 4, "exposed_lightning_rod", facing="up")
    c.put(11, 1, 5, "smithing_table")
    c.put(11, 1, 6, "barrel", facing="up", open=False)
    c.put(11, 2, 6, "exposed_lightning_rod", facing="up")
    c.put(11, 1, 7, "chest", facing="west", type="single")
    c.put(11, 1, 8, "fletching_table")
    c.put(10, 3, 5, "lantern", hanging=True)
    # loft armoury stores
    c.put(11, 5, 3, "barrel", facing="up", open=False)
    c.put(11, 5, 4, "target")
    c.put(11, 5, 6, "barrel", facing="west", open=False)
    c.put(11, 5, 7, "hay_block", axis="x")
    c.put(10, 5, 8, "barrel", facing="up", open=False)
    c.put(11, 5, 8, "stripped_spruce_log", axis="x")
    c.put(11, 6, 8, "stripped_spruce_log", axis="x")
    c.put(10, 5, 5, "lantern", hanging=False)

    # ---- street supplies either side of the gate, banners on the gable
    c.put(0, 1, 2, "barrel", facing="up", open=False)
    c.put(0, 1, 3, "barrel", facing="west", open=False)
    c.put(0, 1, 8, "hay_block", axis="z")
    c.put(0, 1, 7, "stripped_dark_oak_log", axis="z")
    c.put(0, 2, 7, "exposed_lightning_rod", facing="up")
    c.put(0, 3, 3, "white_wall_banner", facing="west")
    c.put(0, 3, 7, "white_wall_banner", facing="west")
    return c


# =============================================================================================== F04 timber lodge
def f04():
    """Front (street) = -x. Gable walls x=1 (front) / x=11 (rear), side walls z=1 / z=9; gambrel ridge along x at
    z=5; roof x=0..12 (verge overhang = hoist hood at the front)."""
    c = Cells((W, H, D))
    apron(c)
    for x in range(2, 11):
        for z in range(2, 9):
            c.put(x, 0, z, "spruce_planks")
    for x in range(2, 7):
        c.put(x, 0, 5, "stripped_spruce_log", axis="x")
    for z in (4, 5, 6):
        c.put(0, 0, z, "stone_bricks")
        c.put(1, 0, z, "stone_bricks")

    # gambrel profile per z: list of (y, kind) where kind is 'stair' (facing toward ridge), 'full', 'slab', 'ridge'
    prof = {0: [(4, "stair")], 1: [(5, "full"), (6, "stair")], 2: [(7, "full"), (8, "stair")],
            3: [(9, "stair")], 4: [(10, "slab")], 5: [(10, "ridge")]}
    under = {1: 5, 2: 7, 3: 9, 4: 10, 5: 10}  # lowest roof cell per z (walls/gables fill below)

    def zz(z):
        return z if z <= 5 else 10 - z

    # walls: side walls z=1/9 (y1 stone, y2..4 timber frame), gables x=1/11
    posts = (1, 4, 6, 8, 11)
    for z in (1, 9):
        for x in range(1, 12):
            c.put(x, 1, z, base_course(x, 1, z))
            for y in (2, 3, 4):
                if x in posts:
                    c.put(x, y, z, "dark_oak_log", axis="y")
                elif y == 4:
                    c.put(x, y, z, "stripped_dark_oak_log", axis="x")
                else:
                    c.put(x, y, z, INFILL)
    for x in (1, 11):
        for z in range(1, 10):
            top = under[zz(z)] - 1
            for y in range(1, top + 1):
                if y == 1:
                    blk, pr = base_course(x, y, z), {}
                elif z in (1, 9) or (z == 5 and y >= 5):
                    blk, pr = "dark_oak_log", {"axis": "y"}
                elif y == 4:
                    blk, pr = "stripped_dark_oak_log", {"axis": "z"}
                elif y == 7 and 2 <= z <= 8:
                    blk, pr = "stripped_dark_oak_log", {"axis": "z"}
                else:
                    blk, pr = INFILL, {}
                c.put(x, y, z, blk, **pr)
    for x in (1, 11):  # stone quoins at the corners
        for z in (1, 9):
            c.put(x, 2, z, "stone_bricks")
    # broad windows with shutters on the side walls (x=2..3 and x=9..10)
    for z, out, f in ((1, 0, "north"), (9, 10, "south")):
        for x0 in (2, 9):
            for x in (x0, x0 + 1):
                for y in (2, 3):
                    c.put(x, y, z, "glass_pane")
                trap(c, x, 1, out, "spruce", f, open_=False, half="top")  # flower-box ledge
            for y in (2, 3):
                trap(c, x0 - 1, y, out, "spruce", f)
                trap(c, x0 + 2, y, out, "spruce", f)
        c.put(5, 2, z, "glass_pane"); c.put(5, 3, z, "glass_pane")
        c.put(7, 2, z, "glass_pane"); c.put(7, 3, z, "glass_pane")
    for x in (2, 3, 9, 10):
        c.put(x, 1, 0, "spruce_trapdoor", facing="north", half="top", open=False, powered=False, waterlogged=False)
        c.put(x, 1, 10, "spruce_trapdoor", facing="south", half="top", open=False, powered=False, waterlogged=False)
    for x in (2, 10):
        c.put(x, 2, 0, "potted_red_tulip" if x == 2 else "potted_fern")
        c.put(x, 2, 10, "potted_fern" if x == 2 else "potted_dandelion")

    # roof
    for x in range(W):
        barge = x in (0, 12)
        for z in range(D):
            for y, kind in prof[zz(z)]:
                face = "south" if z < 5 else "north"
                if kind == "stair":
                    stairs(c, x, y, z, "dark_oak" if barge else "spruce", face)
                elif kind == "full":
                    if barge:
                        stairs(c, x, y, z, "dark_oak", OPP[face], half="top")
                    else:
                        stairs(c, x, y, z, "spruce", OPP[face], half="top")
                elif kind == "slab":
                    c.put(x, y, z, "dark_oak_slab" if barge else "spruce_slab", type="bottom")
                else:
                    c.put(x, y, z, "dark_oak_log" if barge else "dark_oak_planks", **({"axis": "x"} if barge else {}))
    # front gable features: door + canopy, side windows, loft hay door, louvres, hoist beam
    door(c, 1, 5, "spruce", "west", "left")
    c.put(1, 3, 5, "stripped_dark_oak_log", axis="z")
    for z in (2, 3, 7, 8):
        c.put(1, 2, z, "glass_pane"); c.put(1, 3, z, "glass_pane")
    for z in (4, 6):
        c.put(1, 2, z, "dark_oak_log", axis="y"); c.put(1, 3, z, "dark_oak_log", axis="y")
    for z in range(2, 9):  # pent canopy across the front
        if z in (2, 8):
            stairs(c, 0, 4, z, "dark_oak", "east", shape="straight")
        else:
            stairs(c, 0, 4, z, "spruce", "east")
    for z in (2, 8):
        for y in (1, 2, 3):
            c.put(0, y, z, "dark_oak_fence")
    c.put(0, 3, 5, "lantern", hanging=True)
    for y in (6, 7):  # loft hay door between open shutters
        trap(c, 0, y, 4, "spruce", "west")
        trap(c, 0, y, 6, "spruce", "west")
        c.put(1, y, 4, "dark_oak_log", axis="y")
        c.put(1, y, 6, "dark_oak_log", axis="y")
    c.put(1, 6, 5, "spruce_fence")
    c.put(1, 7, 5, "air")
    for z in (3, 7):  # louvres
        trap(c, 1, 8, z, "spruce", "west", open_=False, half="top")
    c.put(1, 9, 5, "stripped_dark_oak_log", axis="x")
    c.put(0, 9, 5, "stripped_dark_oak_log", axis="x")
    c.put(0, 8, 5, "iron_chain", axis="y")
    c.put(0, 7, 5, "hay_block", axis="y")
    # rear chimney on the gable (x=12), stove inside
    for y in range(1, 12):
        for z in ((4, 5, 6) if y <= 3 else (5,)):
            c.put(12, y, z, base_course(12, y, z) if y <= 3 else stone(12, y, z))
    for z in (4, 6):
        stairs(c, 12, 4, z, "stone_brick", "west")
    c.put(12, 11, 5, "cobblestone_wall")
    c.put(12, 10, 5, "stone_bricks")
    c.put(11, 1, 5, "furnace", facing="west", lit=False)
    c.put(11, 2, 5, "stone_bricks")
    c.put(11, 3, 5, "stone_bricks")
    stairs(c, 10, 3, 5, "stone_brick", "west", half="top")
    c.put(11, 6, 5, "glass_pane")
    for z in (3, 7):
        c.put(11, 2, z, "glass_pane"); c.put(11, 3, z, "glass_pane")

    # ---- interior: loft x=7..10 at y5, stair along z=7 (x=2..6)
    for x in range(7, 11):
        for z in range(2, 9):
            c.put(x, 5, z, "spruce_planks")
    for z in range(2, 7):
        c.put(7, 6, z, "spruce_fence")
    for i, x in enumerate(range(2, 7)):
        stairs(c, x, 1 + i, 7, "spruce", "east")
        for y in range(1, 1 + i):
            c.put(x, y, 7, "spruce_planks")
    c.put(6, 6, 6, "air")
    for z in (2, 8):
        for y in (1, 2, 3, 4):
            c.put(7, y, z, "dark_oak_log", axis="y")
    for z in range(3, 8):
        c.put(7, 4, z, "stripped_dark_oak_log", axis="z")
    # tie beam with lantern over the front hall
    for z in range(2, 9):
        c.put(3, 6, z, "stripped_dark_oak_log", axis="z")
    c.put(3, 5, 5, "lantern", hanging=True)
    # beds under the loft
    for x in (8, 10):
        bed(c, x, 1, 2, "brown", "north")
        c.put(x, 1, 4, "brown_carpet")
    bed(c, 8, 1, 8, "brown", "south")
    bed(c, 10, 1, 8, "light_gray", "south")
    c.put(9, 1, 2, "chest", facing="south", type="single")
    c.put(9, 2, 2, "candle", candles=2, lit=True, waterlogged=False)
    c.put(9, 1, 8, "barrel", facing="north", open=False)
    c.put(9, 2, 8, "flower_pot")
    c.put(9, 4, 5, "lantern", hanging=True)
    # dining corner (front north) and stores
    for x in (3, 4, 5):
        c.put(x, 1, 3, "spruce_slab", type="top")
    stairs(c, 3, 1, 4, "spruce", "south"); stairs(c, 5, 1, 4, "spruce", "south")
    c.put(4, 2, 3, "candle", candles=3, lit=True, waterlogged=False)
    c.put(2, 1, 2, "barrel", facing="up", open=False)
    c.put(2, 2, 2, "barrel", facing="east", open=False)
    c.put(6, 1, 2, "crafting_table")
    c.put(2, 1, 8, "hay_block", axis="y")
    c.put(3, 1, 8, "barrel", facing="up", open=False)
    c.put(4, 1, 8, "barrel", facing="up", open=False)
    for x in (5, 6):
        c.put(x, 1, 8, "stripped_spruce_log", axis="x")
    c.put(10, 1, 6, "barrel", facing="up", open=False)
    # loft: two beds and hay stores
    bed(c, 10, 6, 4, "light_gray", "east")
    bed(c, 10, 6, 6, "light_gray", "east")
    c.put(10, 6, 5, "candle", candles=1, lit=False, waterlogged=False)
    c.put(8, 6, 3, "hay_block", axis="x")
    c.put(9, 6, 3, "hay_block", axis="y")
    c.put(8, 6, 8, "barrel", facing="up", open=False)
    c.put(9, 6, 8, "hay_block", axis="z")
    c.put(10, 6, 8, "hay_block", axis="y")
    c.put(10, 6, 2, "barrel", facing="up", open=False)
    c.put(9, 8, 5, "lantern", hanging=True)
    c.put(9, 9, 5, "iron_chain", axis="y")

    # louvred ridge vent (Q25 loft ventilation) over the loft: slab cap on fence posts
    for x in (8, 9):
        c.put(x, 11, 5, "spruce_slab", type="bottom")
    # ---- yard supplies: firewood along the south eave, crates under the canopy, cart-wheel barrels north
    for x in (3, 4, 5, 6, 7):
        c.put(x, 1, 10, "stripped_spruce_log" if x % 2 else "spruce_log", axis="x")
    for x in (4, 5, 6):
        c.put(x, 2, 10, "spruce_log", axis="x")
    c.put(0, 1, 3, "barrel", facing="up", open=False)
    c.put(0, 1, 7, "hay_block", axis="z")
    c.put(0, 2, 7, "hay_block", axis="y")
    c.put(5, 1, 0, "barrel", facing="up", open=False)
    c.put(6, 1, 0, "barrel", facing="north", open=False)
    return c


# ---------------------------------------------------------------------------------------------- registry
# door: entrance column on the street face (+x for F02, -x for F03/F04 - NOT the +z face); walls: x0, x1, z0, z1 of the
# walled body - anything outside it stands on the open apron.
BUILDINGS = {
    "barracks_a": dict(module="M-barracks_a", placement="F02", design=f02, size=(W, H, D),
                       door=(12, 5), entrances={"front_door_east": (13, 5)}, walls=(1, 11, 1, 9)),
    "barracks_b": dict(module="M-barracks_b", placement="F03", design=f03, size=(W, H, D),
                       door=(0, 5), entrances={"gate_west": (-1, 5)}, walls=(1, 12, 1, 9)),
    "barracks_c": dict(module="M-barracks_c", placement="F04", design=f04, size=(W, H, D),
                       door=(0, 5), entrances={"front_door_west": (-1, 5)}, walls=(1, 11, 1, 9)),
}


def main():
    mods = A.modules()
    (ROOT / "out").mkdir(exist_ok=True)
    for key, b in BUILDINGS.items():
        module = mods[b["module"]]
        assert module["size"] == list(b["size"]) and module["air"] == "include", (key, module)
        cells = b["design"]()
        assert (cells.W, cells.H, cells.D) == tuple(b["size"])
        with tempfile.TemporaryDirectory() as d:
            result = export_module(module, dict(cells), Path(d) / "pack")
            shutil.copyfile(result.config.nbt_path, ROOT / "out" / f"{module['file']}.nbt")
            shutil.copyfile(result.config.source, ROOT / "out" / f"{module['file']}.schem")
            (ROOT / "out" / f"{module['file']}.export-report.json").write_text(
                json.dumps(result.report, indent=2, sort_keys=True) + "\n"
            )
        print(f"{module['file']}.nbt: {len(cells)} authored cells, size {module['size']}")


if __name__ == "__main__":
    main()
