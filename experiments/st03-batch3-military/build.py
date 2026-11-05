"""ST-03 military batch: F05 armory (M-armory 17x12x13) and F06 training yard (M-yard 25x5x21).

Contract kept (tools/seam01/data/st03_placements.json, untouched): sizes above (x, y, z), air=include, floor y=0,
local_turns 0. F05 x=12..28, z=39..51; F06 x=12..36, z=52..72 -> the armory's +z face (local z=12) touches the
yard's -z edge (local z=0) along yard x=0..16. Neither module is rotated or moved here.

Free design brief (ST03-IMPLEMENT-04). Q27-Q38 were read as reference; where they shape gameplay they are kept:
  F05 35% premium reward is a CHEST SLOT only (PREMIUM_CHEST below); no loot, item or probability is authored.
  All containers are empty (block-entity allow-list), loot is a runtime decision. F06 has exactly 3 targets (Q33).

F05 armory - "a fortified arsenal": a long, heavy stone hall under a deep deepslate-tile roof, fronted on the road
  side (+x) by a square gate tower that rises above the ridge and ends in a corbelled, crenellated parapet. On the
  yard side (+z) the hall roof sweeps down over a low timber-and-stone maintenance loggia (catslide) that opens on to
  the training yard. Inside: the portal leads along a processional axis between weapon tables to a barred strongroom
  holding the premium chest; weapon walls (blades, shields, mail) line the hall; the loggia holds the workstations.
  Entrances: tower portal (east, road side), loggia bay (south, to F06), loggia service door (east).
F06 training yard - "an open drill ground": dark-oak post-and-rail enclosure, a stone parade path from the road gate
  (east) to a canopied command dais (west), a stone spur to the armory loggia, a stone-edged sparring ring with three
  straw pells (north-east), an equipment rack shelter by the armory (north-west), and an archery range (south) with a
  stone firing line, worn shooting lanes, a hay butt with exactly three targets and an earth backstop berm.

  PYTHONPATH=. python experiments/st03-batch3-military/build.py
"""

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("batch1_build", ROOT.parent / "st03-batch1-support" / "build.py")
B1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B1)
Cells, stone, floor_stone = B1.Cells, B1.stone, B1.floor_stone


def plinth(x, y, z):
    """Dark deepslate base course."""
    h = (x * 13 + y * 7 + z * 5) % 5
    return ["deepslate_bricks", "cobbled_deepslate", "deepslate_bricks", "polished_deepslate", "cracked_deepslate_bricks"][h]


def noise(x, z, n, salt=0):
    """Deterministic scatter without visible stripes or checkerboards."""
    h = (x * 73856093) ^ (z * 19349663) ^ (salt * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return (h ^ (h >> 16)) % n


def path_stone(x, z):
    h = (x * 11 + z * 7 + x * z * 3) % 10
    return ["stone_bricks", "cobblestone", "stone_bricks", "andesite", "stone_bricks",
            "cracked_stone_bricks", "cobblestone", "stone_bricks", "mossy_cobblestone", "gravel"][h]


# ------------------------------------------------------------------------------------------------ F05 armory
AW, AH, AD = 17, 12, 13
TOWER = (11, 15, 2, 6)  # shaft x0, x1, z0, z1


def rh(z):
    """Hall roof height at z (ridge along x at z=4)."""
    return 5 + min(z, 8 - z)


def in_tower(x, z):
    return TOWER[0] <= x <= TOWER[1] and TOWER[2] <= z <= TOWER[3]


def armory():
    c = Cells((AW, AH, AD))
    # ---- floor (y=0)
    for x in range(AW):
        for z in range(AD):
            if 2 <= x <= 13 and 1 <= z <= 7:
                f = "stone_bricks" if z in (1, 7) or x in (2, 13) else "polished_andesite"
            elif z >= 9:
                f = floor_stone(x, z)
            else:
                f = path_stone(x, z)
            c.put(x, 0, z, f)
    for x in range(5, AW):  # processional runner: portal -> strongroom
        c.put(x, 0, 4, "polished_deepslate")
    c.put(13, 0, 4, "chiseled_stone_bricks")
    for z in (3, 4, 5):
        for x in (2, 3):
            c.put(x, 0, z, "polished_deepslate")
    c.put(4, 0, 4, "chiseled_stone_bricks")
    for x in (7, 8, 9):  # loggia bay threshold
        for z in (11, 12):
            c.put(x, 0, z, "stone_bricks")

    def wall(x, y, z):
        if y == 1:
            c.put(x, y, z, plinth(x, y, z))
        else:
            c.put(x, y, z, stone(x, y, z))

    # ---- hall walls: north z=0 and south z=8 (x=1..14), west gable x=1, east shoulders x=14
    for x in range(1, 15):
        for z in (0, 8):
            if in_tower(x, z):
                continue
            for y in range(1, 4):
                wall(x, y, z)
            c.put(x, 4, z, "stripped_dark_oak_log", axis="x")  # wall plate under the eave
    for z in range(0, 9):
        top = rh(z) - 1
        for y in range(1, top + 1):
            wall(1, y, z)
        if z in (0, 1, 7, 8):
            for y in range(1, top + 1):
                wall(14, y, z)
    for x in (1, 14):  # dark quoins at the hall corners
        for z in (0, 8):
            for y in range(1, 5):
                c.put(x, y, z, "deepslate_bricks" if y % 2 else "polished_deepslate")
    # north wall slit windows (iron bars) at x = 3, 6, 9, 12
    for x in (3, 6, 9, 12):
        for y in (2, 3):
            c.put(x, y, 0, "iron_bars")
    c.put(1, 6, 4, "iron_bars"); c.put(1, 7, 4, "iron_bars")  # west gable slit
    # west buttresses
    for z in (2, 6):
        for y in (1, 2, 3):
            c.put(0, y, z, plinth(0, y, z) if y == 1 else stone(0, y, z))
        c.put(0, 4, z, "stone_brick_stairs", facing="east", half="bottom", shape="straight")
    # south wall: arch to the loggia at x=7..9
    for x in (7, 8, 9):
        for y in (1, 2):
            c.put(x, y, 8, "air")
    c.put(8, 3, 8, "air")
    c.put(7, 3, 8, "stone_brick_stairs", facing="west", half="top", shape="straight")
    c.put(9, 3, 8, "stone_brick_stairs", facing="east", half="top", shape="straight")

    # ---- hall roof (deepslate tile, dark-oak barge on the west gable)
    for x in range(0, 15):
        for z in range(0, 9):
            if in_tower(x, z):
                continue
            y = rh(z)
            if z == 4:
                c.put(x, y, z, "dark_oak_log" if x == 0 else "deepslate_tiles", **({"axis": "x"} if x == 0 else {}))
                continue
            blk = "dark_oak_stairs" if x == 0 else "deepslate_tile_stairs"
            c.put(x, y, z, blk, facing="south" if z < 4 else "north", half="bottom", shape="straight")
    # eave continuation over the corner east of the hall (x=15..16, z=8) and the loggia's north closure
    for x in (15, 16):
        for y in range(1, 5):
            c.put(x, y, 8, stone(x, y, 8) if y > 1 else plinth(x, y, 8))
        c.put(x, 5, 8, "deepslate_tile_stairs", facing="north", half="bottom", shape="straight")
    for y in range(1, 5):
        c.put(0, y, 8, stone(0, y, 8) if y > 1 else plinth(0, y, 8))

    # ---- inner timber: wall plates and tie beams with hanging lanterns
    for x in range(2, 11):
        c.put(x, 5, 1, "stripped_dark_oak_log", axis="x")
        c.put(x, 5, 7, "stripped_dark_oak_log", axis="x")
    for x in (5, 8):
        for z in range(2, 7):
            c.put(x, 5, z, "stripped_dark_oak_log", axis="z")
        c.put(x, 4, 4, "lantern", hanging=True)
        c.put(x, 4, 2, "iron_chain", axis="y")
        c.put(x, 4, 6, "iron_chain", axis="y")

    # ---- gate tower: shaft x=11..15, z=2..6, walls to y=8, corbelled deck y=9, parapet y=10, merlons y=11
    x0, x1, z0, z1 = TOWER
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(1, 9):
                if x in (x0, x1) or z in (z0, z1):
                    corner = x in (x0, x1) and z in (z0, z1)
                    if y <= 2:
                        c.put(x, y, z, plinth(x, y, z))
                    elif corner:
                        c.put(x, y, z, "polished_andesite" if y % 2 else "stone_bricks")
                    else:
                        c.put(x, y, z, stone(x, y, z))
                else:
                    c.put(x, y, z, "air")
    for x in range(x0, x1 + 1):  # dark string course
        for z in range(z0, z1 + 1):
            if (x in (x0, x1) or z in (z0, z1)) and not (x == x0 and 3 <= z <= 5):
                c.put(x, 5, z, "polished_deepslate")
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            ring = x in (x0 - 1, x1 + 1) or z in (z0 - 1, z1 + 1)
            corner = x in (x0 - 1, x1 + 1) and z in (z0 - 1, z1 + 1)
            if not ring:
                c.put(x, 9, z, "stone_bricks")
                c.put(x, 10, z, "air")
                c.put(x, 11, z, "air")
                continue
            if corner:
                c.put(x, 9, z, "stone_bricks")
            else:
                face = {x0 - 1: "east", x1 + 1: "west"}.get(x) or {z0 - 1: "south", z1 + 1: "north"}[z]
                c.put(x, 9, z, "stone_brick_stairs", facing=face, half="top", shape="straight")
            c.put(x, 10, z, "stone_bricks")
            i = (x - (x0 - 1)) if z in (z0 - 1, z1 + 1) else (z - (z0 - 1))
            c.put(x, 11, z, "stone_bricks" if i % 2 == 0 else "air")
    # portal (east face x=15) and inner arch (x=11), z=3..5, round-headed
    for xx in (x1, x0):
        for z in (3, 4, 5):
            for y in (1, 2):
                c.put(xx, y, z, "air")
        c.put(xx, 3, 4, "air")
        c.put(xx, 3, 3, "stone_brick_stairs", facing="north", half="top", shape="straight")
        c.put(xx, 3, 5, "stone_brick_stairs", facing="south", half="top", shape="straight")
        c.put(xx, 4, 4, "chiseled_stone_bricks")
    # tower slits, banner over the portal, lantern on a chain in the shaft
    for y in (6, 7):
        c.put(x1, y, 4, "iron_bars")
        c.put(13, y, z0, "iron_bars")
        c.put(13, y, z1, "iron_bars")
    c.put(16, 5, 4, "white_wall_banner", facing="east")
    for y in (8, 7):
        c.put(13, y, 4, "iron_chain", axis="y")
    c.put(13, 6, 4, "lantern", hanging=True)
    c.put(14, 3, 4, "lantern", hanging=True)  # under the portal arch, inside
    c.put(14, 4, 4, "iron_chain", axis="y")
    # tower buttresses on the road face
    for z in (2, 6):
        for y in (1, 2, 3):
            c.put(16, y, z, plinth(16, y, z) if y == 1 else stone(16, y, z))
        c.put(16, 4, z, "stone_brick_stairs", facing="west", half="bottom", shape="straight")

    # ---- loggia (maintenance aisle) z=9..12 along the whole length, catslide roof
    for x in range(AW):
        c.put(x, 5, 9, "deepslate_tile_slab", type="bottom")
        c.put(x, 4, 10, "deepslate_tile_slab", type="top")
        c.put(x, 4, 11, "deepslate_tile_slab", type="bottom")
        c.put(x, 3, 12, "deepslate_tile_slab", type="top")
    for xe in (0, 16):  # end walls
        for z, top in ((9, 4), (10, 3), (11, 3)):
            for y in range(1, top + 1):
                c.put(xe, y, z, plinth(xe, y, z) if y == 1 else stone(xe, y, z))
    c.put(16, 1, 10, "spruce_door", facing="east", half="lower", hinge="left", open=False, powered=False)
    c.put(16, 2, 10, "spruce_door", facing="east", half="upper", hinge="left", open=False, powered=False)
    c.put(0, 2, 10, "iron_bars")
    # front line z=11: posts on stone bases, sills in the closed bays, continuous lintel
    for x in range(1, 16):
        c.put(x, 3, 11, "stripped_dark_oak_log", axis="x")
    for x in (3, 6, 10, 13):
        c.put(x, 1, 11, "stone_bricks")
        c.put(x, 2, 11, "dark_oak_log", axis="y")
    for x in (1, 2, 4, 5, 11, 12, 14, 15):
        c.put(x, 1, 11, "stone_brick_wall")
    # lanterns hanging under the eave beside the bay, and inside the loggia
    c.put(6, 2, 12, "lantern", hanging=True)
    c.put(10, 2, 12, "lantern", hanging=True)
    c.put(3, 3, 10, "lantern", hanging=True)
    c.put(13, 3, 10, "lantern", hanging=True)
    # workstations against the hall wall (z=9)
    c.put(1, 1, 9, "barrel", facing="up", open=False)
    c.put(1, 2, 9, "barrel", facing="south", open=False)
    c.put(2, 1, 9, "water_cauldron", level=3)
    c.put(3, 1, 9, "grindstone", face="floor", facing="east")
    c.put(4, 1, 9, "anvil", facing="east")
    c.put(5, 1, 9, "smithing_table")
    c.put(6, 1, 9, "chest", facing="south", type="single")
    c.put(10, 1, 9, "chest", facing="south", type="single")
    c.put(11, 1, 9, "fletching_table")
    c.put(12, 1, 9, "crafting_table")
    c.put(13, 1, 9, "grindstone", face="floor", facing="east")
    c.put(14, 1, 9, "barrel", facing="south", open=False)
    c.put(15, 1, 9, "barrel", facing="up", open=False)
    # tools hung on the wall above the benches
    c.put(2, 3, 9, "grindstone", face="wall", facing="south")
    for x in (4, 5):
        c.put(x, 3, 9, "lever", face="wall", facing="south", powered=False)  # hammers / tongs on pegs
    for x in (11, 12):
        c.put(x, 3, 9, "tripwire_hook", facing="south", attached=False, powered=False)
    c.put(14, 3, 9, "grindstone", face="wall", facing="south")

    # ---- strongroom (premium chest) at the west end of the axis
    for x in (2, 3):
        for z in (2, 6):
            for y in (1, 2, 3):
                c.put(x, y, z, stone(x, y, z))
    for z in (2, 6):
        for y in (1, 2, 3):
            c.put(4, y, z, "chiseled_stone_bricks" if y == 2 else "stone_bricks")
    for z in (3, 5):
        for y in (1, 2, 3):
            c.put(4, y, z, "iron_bars")
    c.put(4, 1, 4, "spruce_door", facing="east", half="lower", hinge="left", open=False, powered=False)
    c.put(4, 2, 4, "spruce_door", facing="east", half="upper", hinge="left", open=False, powered=False)
    c.put(4, 3, 4, "iron_bars")
    for x in (2, 3, 4):
        for z in range(2, 7):
            c.put(x, 4, z, "stone_brick_slab", type="bottom")
    c.put(2, 1, 4, "chest", facing="east", type="single")  # PREMIUM_CHEST
    for z in (3, 5):
        c.put(2, 1, z, "polished_andesite")
        c.put(2, 2, z, "soul_lantern", hanging=False)
    c.put(2, 3, 4, "white_wall_banner", facing="east")
    c.put(3, 3, 4, "soul_lantern", hanging=True)
    # rear stores flanking the strongroom: stacked haft timber (no containers in this dead-end corner)
    for z in (1, 7):
        for x in (2, 3):
            c.put(x, 1, z, "stripped_spruce_log", axis="x")
        c.put(2, 2, z, "stripped_spruce_log", axis="x")
        c.put(3, 2, z, "spruce_slab", type="bottom")

    # ---- weapon walls (north z=1, south z=7) and pockets beside the tower
    c.put(5, 1, 1, "chest", facing="south", type="single")
    c.put(5, 2, 1, "grindstone", face="wall", facing="south")
    c.put(5, 3, 1, "iron_chain", axis="y")
    for x in (7, 8):  # spears standing in barrels under a banner
        c.put(x, 1, 1, "barrel", facing="up", open=False)
        c.put(x, 2, 1, "exposed_lightning_rod", facing="up")
        c.put(x, 3, 1, "white_wall_banner", facing="south")
    c.put(10, 1, 1, "chest", facing="south", type="single")
    c.put(10, 2, 1, "grindstone", face="wall", facing="south")
    c.put(10, 3, 1, "iron_chain", axis="y")
    c.put(5, 1, 7, "chest", facing="north", type="single")
    c.put(5, 2, 7, "grindstone", face="wall", facing="north")
    c.put(6, 1, 7, "barrel", facing="north", open=False)
    for y in (2, 3):  # mail hauberks: chains hung on the wall
        c.put(6, y, 7, "iron_chain", axis="y")
    c.put(10, 1, 7, "barrel", facing="up", open=False)
    c.put(10, 2, 7, "exposed_lightning_rod", facing="up")
    for z in (1, 7):  # spear racks in the pockets either side of the tower
        for x in (11, 12, 13):
            c.put(x, 1, z, "stripped_dark_oak_log", axis="x")
            c.put(x, 2, z, "exposed_lightning_rod", facing="up")
    # weapon tables either side of the axis
    for z in (3, 5):
        for x in (6, 7, 8, 9):
            c.put(x, 1, z, "dark_oak_slab", type="top")
        c.put(6, 2, z, "heavy_weighted_pressure_plate", power=0)  # breastplates laid out
        c.put(7, 2, z, "iron_chain", axis="x")  # mail
        c.put(8, 2, z, "heavy_weighted_pressure_plate", power=0)
        c.put(9, 2, z, "lever", face="floor", facing="east", powered=False)  # a blade on the table
    return c


# ------------------------------------------------------------------------------------------------- F06 yard
YW, YH, YD = 25, 5, 21


def worn(x, z):
    h = (x * 7 + z * 13 + x * z) % 7
    return ["coarse_dirt", "rooted_dirt", "coarse_dirt", "coarse_dirt", "rooted_dirt", "coarse_dirt", "gravel"][h]


def grassy(x, z):
    h = (x * 5 + z * 11 + x * z * 7) % 9
    return "coarse_dirt" if h == 0 else ("dirt_path" if h == 1 else "grass_block")


def yard():
    c = Cells((YW, YH, YD))
    # ---- ground
    for x in range(YW):
        for z in range(YD):
            c.put(x, 0, z, grassy(x, z))
    for x in range(0, 17):
        c.put(x, 0, 0, path_stone(x, 0))
    for x in range(7, 10):
        for z in range(1, 9):
            c.put(x, 0, z, path_stone(x, z))
    for x in range(6, YW):
        for z in range(9, 12):
            c.put(x, 0, z, "stone_bricks" if z == 10 and x % 3 else path_stone(x, z))
    for x in range(1, 7):  # equipment area: trodden gravel
        for z in range(1, 8):
            c.put(x, 0, z, ["gravel", "gravel", "coarse_dirt", "gravel", "packed_mud"][noise(x, z, 5, 1)])
    # sparring ring x=11..22, z=1..7: stone outline, worn earth inside, cut corners
    for x in range(11, 23):
        for z in range(1, 8):
            corner = x in (11, 22) and z in (1, 7)
            edge = x in (11, 22) or z in (1, 7)
            if corner:
                continue
            c.put(x, 0, z, "polished_andesite" if edge else worn(x, z))
    # archery range z=12..19
    for x in range(1, 5):
        for z in range(13, 20):
            c.put(x, 0, z, ["gravel", "gravel", "coarse_dirt"][noise(x, z, 3, 2)])
    for z in range(13, 20):
        c.put(5, 0, z, "stone_bricks" if z % 2 else "polished_andesite")
    for x in range(6, 20):
        for z in range(13, 20):
            if z in (14, 16, 18):  # worn shooting lanes
                c.put(x, 0, z, "coarse_dirt" if noise(x, z, 9, 3) else "rooted_dirt")
            else:
                c.put(x, 0, z, "packed_mud" if noise(x, z, 8, 4) else "gravel")
    for z in range(12, 20):
        c.put(20, 0, z, "coarse_dirt")

    # ---- enclosure: dark-oak post-and-rail fence, lantern posts at the corners
    fence = "dark_oak_fence"
    for z in range(0, 21):
        c.put(0, 1, z, fence)
    for x in range(0, 25):
        c.put(x, 1, 20, fence)
    for z in range(0, 21):
        if not 9 <= z <= 11:
            c.put(24, 1, z, fence)
    for x in range(17, 25):
        c.put(x, 1, 0, fence)
    for x, z in ((0, 20), (24, 20), (24, 0), (0, 0)):
        c.put(x, 2, z, fence)
        c.put(x, 3, z, "lantern", hanging=False)

    # ---- road gate (east): log posts, beam, banners outside, hanging lantern
    for z in (8, 12):
        for y in (1, 2, 3):
            c.put(23, y, z, "dark_oak_log", axis="y")
        c.put(24, 4, z, "white_wall_banner", facing="east")
    for z in range(8, 13):
        c.put(23, 4, z, "stripped_dark_oak_log", axis="z")
    c.put(23, 3, 10, "lantern", hanging=True)

    # ---- processional posts half-way along the parade path, banners over the path
    for z in (8, 12):
        for y in (1, 2, 3):
            c.put(10, y, z, "dark_oak_log", axis="y")
        c.put(10, 4, z, "lantern", hanging=False)
    c.put(10, 3, 9, "white_wall_banner", facing="south")
    c.put(10, 3, 11, "white_wall_banner", facing="north")

    # ---- command dais (west end of the parade path) x=1..5, z=8..12
    for x in range(1, 6):
        for z in range(8, 13):
            edge = x in (1, 5) or z in (8, 12)
            c.put(x, 1, z, "stone_bricks" if edge else "spruce_planks")
    for z in (9, 10, 11):
        c.put(6, 1, z, "stone_brick_stairs", facing="west", half="bottom", shape="straight")
    for x, z in ((1, 8), (1, 12)):
        for y in (2, 3):
            c.put(x, y, z, "dark_oak_log", axis="y")
    for z in (8, 12):  # slender front posts keep the dais open toward the parade path
        for y in (2, 3):
            c.put(5, y, z, fence)
    for x in range(1, 6):
        for z in range(8, 13):
            c.put(x, 4, z, "dark_oak_slab", type="bottom")
    for x in (2, 3, 4):
        c.put(x, 2, 8, fence)
        c.put(x, 2, 12, fence)
    for z in (9, 10, 11):
        c.put(1, 2, z, "dark_oak_planks")
        c.put(1, 3, z, "dark_oak_planks")
        c.put(2, 3, z, "white_wall_banner", facing="east")
    c.put(2, 2, 10, "dark_oak_stairs", facing="west", half="bottom", shape="straight")  # commander's seat
    c.put(3, 2, 10, "cartography_table")
    c.put(3, 3, 10, "lantern", hanging=True)

    # ---- equipment rack shelter by the armory (north-west) x=1..4, z=2..6
    for z in range(2, 7):
        for y in (1, 2, 3):
            c.put(1, y, z, "dark_oak_log" if z in (2, 6) else "spruce_planks", **({"axis": "y"} if z in (2, 6) else {}))
    for z in (2, 6):
        for y in (1, 2, 3):
            c.put(4, y, z, fence)
    for z in range(2, 7):
        c.put(1, 4, z, "spruce_planks")
        c.put(2, 4, z, "spruce_stairs", facing="west", half="bottom", shape="straight")
        c.put(3, 4, z, "spruce_stairs", facing="west", half="bottom", shape="straight")
        c.put(4, 4, z, "spruce_slab", type="bottom")
    for z in (3, 4, 5):
        c.put(2, 1, z, "stripped_spruce_log", axis="z")
        c.put(2, 2, z, "exposed_lightning_rod", facing="up")
    c.put(2, 3, 3, "grindstone", face="wall", facing="east")
    c.put(2, 3, 5, "grindstone", face="wall", facing="east")
    c.put(2, 3, 4, "white_wall_banner", facing="east")
    c.put(2, 1, 2, "barrel", facing="east", open=False)
    c.put(2, 1, 6, "barrel", facing="east", open=False)
    # supplies by the armory loggia
    c.put(5, 1, 1, "barrel", facing="up", open=False)
    c.put(6, 1, 1, "hay_block", axis="y")
    c.put(6, 2, 1, "hay_block", axis="x")
    c.put(5, 1, 5, "grindstone", face="floor", facing="south")

    # ---- sparring ring: three straw pells along the north edge, lantern posts, practice-weapon barrel
    for x in (13, 17, 21):
        c.put(x, 1, 2, fence)
        c.put(x, 2, 2, "hay_block", axis="y")
        c.put(x, 3, 2, "carved_pumpkin", facing="south")
        c.put(x - 1, 2, 2, fence)
        c.put(x + 1, 2, 2, fence)
    for x, z in ((11, 7), (22, 7), (11, 1), (22, 1)):
        c.put(x, 1, z, fence)
        c.put(x, 2, z, "lantern", hanging=False)
    c.put(23, 1, 3, "grindstone", face="floor", facing="west")
    c.put(23, 1, 4, "barrel", facing="up", open=False)
    c.put(23, 2, 4, "exposed_lightning_rod", facing="up")
    c.put(23, 1, 5, "chest", facing="west", type="single")

    # ---- archery range: rail along the path, firing line supplies, hay butt with 3 targets, earth berm
    for x in range(7, 20):
        if x != 10:
            c.put(x, 1, 12, fence)
    for z in range(13, 20):
        c.put(20, 1, z, "hay_block", axis="z")
        c.put(20, 2, z, "target" if z in (14, 16, 18) else "hay_block", **({} if z in (14, 16, 18) else {"axis": "z"}))
        c.put(20, 3, z, "spruce_stairs", facing="east", half="bottom", shape="straight")
    for z in range(12, 21):  # timber arrow screen behind the butt: plank infill between log posts, slab cap
        post = z in (12, 16, 20)
        for y in (1, 2, 3):
            c.put(21, y, z, "dark_oak_log" if post else "spruce_planks", **({"axis": "y"} if post else {}))
        c.put(21, 4, z, "spruce_slab", type="bottom")
    for x in (22, 23):
        for z in range(12, 20):
            if noise(x, z, 4, 6) == 0:
                c.put(x, 1, z, "short_grass" if noise(x, z, 2, 7) else "fern")
    c.put(4, 1, 15, "barrel", facing="up", open=False)
    c.put(4, 1, 17, "barrel", facing="up", open=False)
    c.put(1, 1, 13, "hay_block", axis="y")
    c.put(2, 1, 13, "hay_block", axis="x")
    c.put(1, 2, 13, "hay_block", axis="z")
    c.put(1, 1, 15, "fletching_table")
    c.put(1, 1, 16, "chest", facing="east", type="single")
    c.put(1, 1, 18, "spruce_stairs", facing="west", half="bottom", shape="straight")
    c.put(1, 1, 19, "spruce_stairs", facing="west", half="bottom", shape="straight")
    c.put(3, 1, 19, fence)
    c.put(3, 2, 19, "lantern", hanging=False)
    return c


# -------------------------------------------------------------------------------------------- registry
PREMIUM_CHEST = {"M-armory": (2, 1, 4)}  # F05 35% once-per-structure premium slot (runtime decides contents)

BUILDINGS = {
    "armory": dict(
        module="M-armory", design=armory, size=(AW, AH, AD),
        door=(8, 12),  # yard-side loggia bay (module front +z); outside cell (8, 13)
        entrances={"tower_portal_east": (17, 4), "loggia_bay_south": (8, 13), "service_door_east": (17, 10)},
        interactive={
            "premium_chest": (2, 1, 4), "chest_n_a": (5, 1, 1), "barrel_n_a": (7, 1, 1), "barrel_n_b": (8, 1, 1),
            "chest_n_b": (10, 1, 1), "chest_s": (5, 1, 7), "barrel_s_a": (6, 1, 7), "barrel_s_b": (10, 1, 7),
            "barrel_l_a": (1, 1, 9), "cauldron": (2, 1, 9), "grindstone_a": (3, 1, 9), "anvil": (4, 1, 9),
            "smithing_table": (5, 1, 9), "chest_l_a": (6, 1, 9), "chest_l_b": (10, 1, 9),
            "fletching_table": (11, 1, 9), "crafting_table": (12, 1, 9), "grindstone_b": (13, 1, 9),
            "barrel_l_b": (14, 1, 9), "barrel_l_c": (15, 1, 9),
        },
    ),
    "yard": dict(
        module="M-yard", design=yard, size=(YW, YH, YD),
        door=(24, 10),  # road gate is on the east edge, not the +z face (see README)
        entrances={"road_gate_east": (25, 10), "armory_apron_north": (8, -1)},
        interactive={
            "shelter_barrel_a": (2, 1, 2), "shelter_barrel_b": (2, 1, 6), "supply_barrel": (5, 1, 1),
            "grindstone_yard": (5, 1, 5), "ring_grindstone": (23, 1, 3), "ring_barrel": (23, 1, 4),
            "ring_chest": (23, 1, 5), "quiver_a": (4, 1, 15), "quiver_b": (4, 1, 17),
            "fletching_table": (1, 1, 15), "range_chest": (1, 1, 16), "cartography_table": (3, 2, 10),
            "target_a": (20, 2, 14), "target_b": (20, 2, 16), "target_c": (20, 2, 18),
        },
    ),
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
