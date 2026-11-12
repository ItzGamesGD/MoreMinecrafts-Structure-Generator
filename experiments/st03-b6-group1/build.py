"""ST-03 group 1 (living + support), B3-06: houses B / C / D and the kitchen (F18), smithy (F19) and cart shed (F20).

Contract (unchanged, asserted at build time against tools/seam01/data/st03_placements.json): module ids, sizes and
air=include. Local frame: +x east, +z south, y=0 floor, door on the south face. Authority: ST03_OWNER_APPROVED_DESIGN
Q01-Q17 (palette: stone-brick family + spruce + dark oak). Containers are real but empty: loot is a runtime decision.

  PYTHONPATH=. python experiments/st03-b6-group1/build.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import G  # noqa: E402

from tools.seam01 import assembly as A  # noqa: E402
from tools.seam01.export import export_module  # noqa: E402


def stone(g, x, y, z):
    """Stone bricks with restrained, deterministic mossy / cracked weathering (owner stone principle)."""
    n = (x * 7 + y * 13 + z * 17 + x * z) % 11
    g.put(x, y, z, "mossy_stone_bricks" if n == 0 else "cracked_stone_bricks" if n == 1 else "stone_bricks")


def cobble(g, x, y, z):
    g.put(x, y, z, "mossy_cobblestone" if (x * 5 + y * 3 + z * 11) % 9 == 0 else "cobblestone")


def edge(g, x, z, x0=0, x1=None, z0=0, z1=None):
    x1 = g.W - 1 if x1 is None else x1
    z1 = g.D - 1 if z1 is None else z1
    return x in (x0, x1) or z in (z0, z1)


# ---------------------------------------------------------------- House B (9x10x7): regular gable, covered porch
def house_b():
    g = G(9, 10, 7)
    # floor: cobblestone rim, spruce room, stone-brick porch
    for x in range(9):
        for z in range(6):
            if x in (0, 8) or z in (0, 5):
                cobble(g, x, 0, z)
            else:
                g.put(x, 0, z, "spruce_planks")
    for x in range(9):
        (cobble if x in (0, 8) else stone)(g, x, 0, 6)
    # walls on x=0, x=8, z=0 and the front plane z=5 (z=6 is the covered porch row)
    for x in range(9):
        for z in range(6):
            if not (x in (0, 8) or z in (0, 5)):
                continue
            if (x in (0, 8)) and (z in (0, 5)):
                g.fill(x, x, 1, 4, z, z, "dark_oak_log", axis="y")
                continue
            cobble(g, x, 1, z)
            g.fill(x, x, 2, 3, z, z, "spruce_planks")
            g.put(x, 4, z, "stripped_dark_oak_log", axis="z" if x in (0, 8) else "x")
    for x, z in ((4, 0), (3, 5), (5, 5)):  # back mid post, door posts
        g.fill(x, x, 1, 4, z, z, "dark_oak_log", axis="y")
    g.door(4, 1, 5, "dark_oak", "south")
    g.put(4, 3, 5, "stripped_dark_oak_log", axis="x")
    # larger shuttered windows: shutter | pane | shutter (front: one pane, one shutter each side of the door posts)
    def unit(cells, outward):
        for (x, z), kind in cells:
            for y in (2, 3):
                if kind == "p":
                    g.put(x, y, z, "glass_pane")
                else:
                    g.shutter(x, y, z, outward)
    unit([((1, 5), "s"), ((2, 5), "p"), ((6, 5), "p"), ((7, 5), "s")], "south")
    unit([((1, 0), "s"), ((2, 0), "p"), ((3, 0), "s"), ((5, 0), "s"), ((6, 0), "p"), ((7, 0), "s")], "north")
    unit([((0, 1), "s"), ((0, 2), "p"), ((0, 3), "s")], "west")
    unit([((8, 1), "s"), ((8, 2), "p"), ((8, 3), "s")], "east")
    # porch: posts, beam, lanterns, illager banner
    for x in (0, 3, 5, 8):
        g.fill(x, x, 1, 4, 6, 6, "dark_oak_log", axis="y")
    for x in (1, 2, 4, 6, 7):
        g.put(x, 4, 6, "stripped_dark_oak_log", axis="x")
    for x in (2, 6):
        g.put(x, 3, 6, "lantern", hanging=True)
    g.put(4, 3, 6, "white_wall_banner", facing="south")
    # frieze above the front wall, ceiling
    for x in range(9):
        g.put(x, 5, 5, "spruce_planks")
    for x in range(1, 8):
        for z in range(1, 5):
            g.put(x, 5, z, "spruce_planks")
    # roof: dark-oak stairs, ridge along x at z=3, regular gable ends closed with spruce + king post
    h = g.gable_ew(5, "dark_oak", ("dark_oak_log",))
    for x in (0, 8):
        for z in range(1, 6):
            for y in range(5, h(z)):
                if x in (0, 8) and z == 3:
                    g.put(x, y, z, "dark_oak_log", axis="y")
                else:
                    g.put(x, y, z, "spruce_planks")
    # interior: two-bed communal room
    g.bed(1, 2, "red", "north")
    g.bed(2, 2, "blue", "north")
    g.fill(3, 4, 1, 2, 1, 1, "bookshelf")
    g.put(5, 1, 1, "spruce_fence")
    g.put(5, 2, 1, "spruce_pressure_plate")
    g.put(4, 1, 2, "spruce_stairs", facing="east", half="bottom", shape="straight")
    g.put(7, 1, 1, "crafting_table")
    g.put(7, 1, 2, "furnace", facing="west", lit=False)
    g.put(7, 1, 3, "barrel", facing="west", open=False)
    g.put(7, 1, 4, "chest", facing="west", type="single")
    g.put(1, 1, 4, "barrel", facing="east", open=False)
    for x in (3, 4, 5):
        for z in (3, 4):
            g.put(x, 1, z, "brown_carpet")
    g.put(4, 4, 2, "lantern", hanging=True)
    g.put(3, 3, 4, "wall_torch", facing="north")
    g.put(5, 3, 4, "wall_torch", facing="north")
    return g


# ---------------------------------------------------------------- House C (7x9x7): asymmetric gable, recessed door
def house_c():
    g = G(7, 9, 7)
    wtop = {0: 4, 1: 5, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2}  # last wall row under the saltbox roof, by x
    # floor
    for x in range(7):
        for z in range(7):
            if x in (0, 6) or z in (0, 6):
                cobble(g, x, 0, z)
            else:
                g.put(x, 0, z, "spruce_planks")
    g.put(3, 0, 6, "stone_bricks")
    # outer walls on the box edge: partial stone (base course everywhere, whole east wall), timber elsewhere
    for x in range(7):
        for z in range(7):
            if not (x in (0, 6) or z in (0, 6)):
                continue
            if x == 3 and z == 6:
                continue  # recess cell in front of the door
            top = wtop[x]
            corner = x in (0, 6) and z in (0, 6)
            for y in range(1, top + 1):
                if corner:
                    g.put(x, y, z, "dark_oak_log", axis="y")
                elif x == 6 or y == 1:
                    stone(g, x, y, z)
                else:
                    g.put(x, y, z, "spruce_planks")
    # recessed door: door plane at z=5, posts at (2,6)/(4,6), alcove (3,*,6) open under the roof
    g.door(3, 1, 5, "dark_oak", "south")
    g.fill(3, 3, 3, 4, 5, 5, "spruce_planks")
    for x in (2, 4):
        g.fill(x, x, 1, 4, 6, 6, "dark_oak_log", axis="y")
    for y in range(1, 5):
        g.clear(3, y, 6)
    g.put(3, 3, 6, "lantern", hanging=True)
    g.put(3, 3, 5, "stripped_dark_oak_log", axis="x")  # lintel (replaces the plank above the door)
    # two/three small asymmetric windows
    g.put(1, 2, 6, "glass_pane")
    g.put(1, 3, 6, "glass_pane")
    g.put(0, 3, 4, "glass_pane")
    g.put(4, 2, 0, "glass_pane")
    # roof: saltbox, ridge x=2 (y7), short west slope, long low east slope; spruce stairs, dark-oak ridge
    roof = {0: 5, 1: 6, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3}
    for z in range(7):
        for x in range(7):
            y = roof[x]
            if x == 2:
                g.put(x, y, z, "dark_oak_log", axis="z")
            else:
                g.stair(x, y, z, "spruce", "east" if x < 2 else "west")
    # gable ends at z=0 and z=6: close the triangle under the roof (all columns), stone at the east end
    for z in (0, 6):
        for x in range(7):
            if z == 6 and x == 3:
                continue
            for y in range(wtop[x] + 1, roof[x]):
                if z == 6 and x == 3:
                    continue
                g.put(x, y, z, "spruce_planks")
    # the front gable above the recess
    g.fill(3, 3, 4, 5, 6, 6, "spruce_planks")
    g.put(3, 3, 6, "lantern", hanging=True)
    # stone chimney on the east wall, with a real furnace behind the room
    g.put(5, 1, 3, "furnace", facing="west", lit=False)
    for y in range(1, 9):
        stone(g, 6, y, 3)
    g.put(6, 8, 3, "cobblestone_wall")
    # interior: one bed + shelves
    g.bed(1, 2, "red", "north")
    g.fill(2, 3, 1, 2, 1, 1, "bookshelf")
    g.put(4, 1, 1, "crafting_table")
    g.put(5, 1, 1, "barrel", facing="south", open=False)
    g.put(1, 1, 4, "chest", facing="east", type="single")
    g.put(3, 1, 3, "brown_carpet")
    g.put(2, 1, 3, "brown_carpet")
    g.put(2, 6, 3, "lantern", hanging=True)
    return g


# ---------------------------------------------------------------- House D (7x9x7): small hip roof, stone doorway
def house_d():
    g = G(7, 9, 7)
    for x in range(7):
        for z in range(7):
            if x in (0, 6) or z in (0, 6):
                cobble(g, x, 0, z)
            else:
                g.put(x, 0, z, "dark_oak_planks")
    g.put(3, 0, 6, "stone_bricks")
    for x in range(7):
        for z in range(7):
            if not (x in (0, 6) or z in (0, 6)):
                continue
            if x in (0, 6) and z in (0, 6):
                g.fill(x, x, 1, 4, z, z, "dark_oak_log", axis="y")
                continue
            for y in (1, 2):
                stone(g, x, y, z)
            g.put(x, 3, z, "spruce_planks")
            g.put(x, 4, z, "stripped_dark_oak_log", axis="z" if x in (0, 6) else "x")
    # defensive stone-framed doorway
    for x in (2, 4):
        for y in (1, 2, 3):
            stone(g, x, y, 6)
    g.put(3, 3, 6, "chiseled_stone_bricks")
    g.door(3, 1, 6, "dark_oak", "south")
    # narrow barred windows
    for p in ((1, 3, 6), (5, 3, 6), (0, 3, 2), (0, 3, 4), (6, 3, 2), (6, 3, 4), (3, 3, 0), (1, 3, 0), (5, 3, 0)):
        g.put(*p, "iron_bars")
    # ceiling + hip roof (dark oak)
    for x in range(1, 6):
        for z in range(1, 6):
            g.put(x, 5, z, "dark_oak_planks")
    g.hip(5, "dark_oak")
    # interior: one guard bed, weapon decor, gear
    g.bed(1, 2, "red", "north")
    g.put(5, 1, 1, "chest", facing="west", type="single")
    g.put(5, 1, 3, "barrel", facing="west", open=False)
    g.put(5, 1, 4, "grindstone", face="floor", facing="west")
    for x in (2, 3, 4):  # weapon rack on the back wall: open trapdoor boards with an iron-bar rail
        g.shutter(x, 2, 1, "south", mat="dark_oak")
    g.put(3, 3, 1, "iron_bars")
    g.put(2, 1, 1, "dark_oak_fence")
    g.put(4, 1, 1, "dark_oak_fence")
    g.put(3, 1, 3, "gray_carpet")
    g.put(3, 4, 3, "lantern", hanging=True)
    return g


# ---------------------------------------------------------------- shared roof for kitchen / smithy (E-W gable, y6 eave)
def stone_hall(g, front_open):
    """Stone shell 9x11x9: walls y1..5, dark-oak gable roof (eave y6, ridge z=4 y10), stone gable ends."""
    for x in range(9):
        for z in range(9):
            if x in (0, 8) or z in (0, 8):
                if front_open and z == 8:
                    continue
                if x in (0, 8) and z in (0, 8):
                    g.fill(x, x, 1, 5, z, z, "dark_oak_log", axis="y")
                else:
                    for y in range(1, 5):
                        stone(g, x, y, z)
                    g.put(x, 5, z, "stripped_dark_oak_log", axis="z" if x in (0, 8) else "x")
    h = g.gable_ew(6, "dark_oak", ("dark_oak_log",))
    for x in (0, 8):
        for z in range(1, 8):
            for y in range(6, h(z)):
                stone(g, x, y, z)
    g.put(0, 7, 4, "iron_bars")
    g.put(8, 7, 4, "iron_bars")
    return h


# ---------------------------------------------------------------- Kitchen F18 (9x11x9)
def kitchen():
    g = G(9, 11, 9)
    for x in range(9):
        for z in range(9):
            stone(g, x, 0, z)
    stone_hall(g, front_open=False)
    # door with stone frame and lintel
    for x in (3, 5):
        for y in (1, 2, 3):
            stone(g, x, y, 8)
    g.put(4, 3, 8, "stripped_dark_oak_log", axis="x")
    g.door(4, 1, 8, "dark_oak", "south")
    for p in ((0, 3, 4), (8, 3, 4), (2, 3, 8), (6, 3, 8), (2, 3, 0), (6, 3, 0)):
        g.put(*p, "glass_pane")
    # tie beams + lanterns
    for z in (2, 6):
        for x in range(1, 8):
            g.put(x, 5, z, "dark_oak_log", axis="x")
    for x, z in ((2, 2), (6, 2), (2, 6), (6, 6)):
        g.put(x, 4, z, "lantern", hanging=True)
    # wall fireplace and chimney (back wall): breast x2..6, z1..2; hearth x3..5; flue at x=4,z=1 up through the roof
    for x in range(2, 7):
        for z in (1, 2):
            for y in range(1, 6):
                stone(g, x, y, z)
    for x in range(3, 6):
        for z in (1, 2):
            for y in (1, 2):
                g.clear(x, y, z)
    for y in (3, 4, 5):
        g.clear(4, y, 1)
    for x in range(3, 6):
        for z in range(0, 3):
            for y in range(6, 11):
                if (x, z) != (4, 1):
                    stone(g, x, y, z)
    g.put(4, 0, 1, "netherrack")
    g.put(4, 1, 1, "fire", age=0, north=False, east=False, south=False, west=False, up=False)
    g.put(3, 1, 1, "cauldron")
    for x in (3, 4, 5):  # stone hearth lip
        stone(g, x, 0, 2)
    # preparation counter (west wall), real furnace + crafting table
    g.put(1, 1, 3, "crafting_table")
    for z in (4, 5, 6):
        g.put(1, 1, z, "spruce_planks")
    g.put(1, 2, 5, "lantern", hanging=False)
    g.put(1, 1, 7, "furnace", facing="east", lit=False)
    g.put(1, 2, 4, "cake", bites=0)
    # storage (east wall): real barrels and chests, cosmetic hay
    g.put(7, 1, 3, "barrel", facing="west", open=False)
    g.put(7, 1, 4, "barrel", facing="west", open=False)
    g.put(7, 1, 5, "chest", facing="west", type="single")
    g.put(7, 1, 6, "chest", facing="west", type="single")
    g.put(7, 1, 7, "hay_block", axis="y")
    g.put(7, 2, 7, "hay_block", axis="y")
    g.put(7, 2, 3, "barrel", facing="up", open=False)
    return g


# ---------------------------------------------------------------- Smithy F19 (9x11x9)
def smithy():
    g = G(9, 11, 9)
    for x in range(9):
        for z in range(9):
            (cobble if (x + z) % 3 else stone)(g, x, 0, z)
    stone_hall(g, front_open=True)
    # open front: stone ends, timber posts and a beam
    for x in range(9):
        g.put(x, 5, 8, "dark_oak_log", axis="x")
    for x in (0, 8):
        for y in range(1, 5):
            stone(g, x, y, 8)
    for x in (1, 7):
        g.fill(x, x, 1, 4, 8, 8, "dark_oak_log", axis="y")
    for p in ((1, 3, 0), (7, 3, 0), (0, 3, 4), (8, 3, 4)):
        g.put(*p, "iron_bars")
    # forge: breast x2..6, z0..1 with furnace | blast furnace | furnace in the front face, chimney stack to y10
    for x in range(2, 7):
        for z in (0, 1):
            for y in range(1, 5):
                stone(g, x, y, z)
    g.put(3, 1, 1, "furnace", facing="south", lit=False)
    g.put(4, 1, 1, "blast_furnace", facing="south", lit=False)
    g.put(5, 1, 1, "furnace", facing="south", lit=False)
    for x in range(3, 6):
        for z in (0, 1):
            for y in range(5, 11):
                stone(g, x, y, z)
    # workstations and containers
    g.put(4, 1, 3, "anvil", facing="east")
    g.put(2, 1, 3, "smithing_table")
    g.put(6, 1, 3, "grindstone", face="floor", facing="east")
    g.put(6, 1, 5, "water_cauldron", level=3)
    g.put(1, 1, 3, "chest", facing="east", type="single")
    g.put(1, 1, 4, "chest", facing="east", type="single")
    g.put(7, 1, 6, "barrel", facing="west", open=False)
    g.put(7, 1, 7, "barrel", facing="west", open=False)
    g.put(7, 1, 2, "coal_block")
    g.put(7, 2, 2, "coal_block")
    g.put(7, 1, 3, "coal_block")
    g.put(1, 2, 3, "iron_bars")
    for x in (3, 5):
        g.put(x, 4, 4, "lantern", hanging=True)
    for z in (4,):
        for x in range(1, 8):
            g.put(x, 5, z, "dark_oak_log", axis="x")
    return g


# ---------------------------------------------------------------- Cart shed F20 (8x9x7)
def cart_shed():
    g = G(8, 9, 7)
    for x in range(8):
        for z in range(7):
            g.put(x, 0, z, "coarse_dirt" if (x * 3 + z) % 4 == 0 else "gravel" if (x + z) % 3 == 0 else "spruce_planks")
    # back wall z=0 and west wall x=0 timber on a stone-brick course; front (z=6) and east (x=7) open
    for x in range(8):
        stone(g, x, 1, 0)
        g.fill(x, x, 2, 3, 0, 0, "spruce_planks")
        g.put(x, 4, 0, "stripped_dark_oak_log", axis="x")
    for z in range(1, 6):
        stone(g, 0, 1, z)
        g.fill(0, 0, 2, 3, z, z, "spruce_planks")
        g.put(0, 4, z, "stripped_dark_oak_log", axis="z")
    for x, z in ((0, 0), (7, 0), (0, 6), (7, 6), (3, 0), (0, 3)):
        g.fill(x, x, 1, 4, z, z, "dark_oak_log", axis="y")
    for x in range(8):
        g.put(x, 4, 6, "stripped_dark_oak_log", axis="x")
    for z in range(1, 6):
        g.put(7, 4, z, "stripped_dark_oak_log", axis="z")
    h = g.gable_ew(5, "spruce", ("dark_oak_log",))
    for z in range(1, 6):
        for y in range(5, h(z)):
            g.put(0, y, z, "spruce_planks")
    g.put(0, 5, 3, "dark_oak_log", axis="y")
    # small cart: slab bed, rails, hay, wheels, shafts
    g.fill(3, 6, 1, 1, 3, 4, "spruce_slab", type="bottom")
    for x, z in ((3, 3), (3, 4), (6, 3), (6, 4)):
        g.put(x, 2, z, "spruce_fence")
    g.put(4, 2, 3, "hay_block", axis="y")
    g.put(5, 2, 3, "hay_block", axis="y")
    for x in (4, 6):
        g.put(x, 1, 2, "spruce_trapdoor", facing="north", half="bottom", open=True, powered=False)
        g.put(x, 1, 5, "spruce_trapdoor", facing="south", half="bottom", open=True, powered=False)
    g.put(7, 1, 3, "spruce_fence")
    g.put(7, 1, 4, "spruce_fence")
    # storage and tools within the bounds
    g.put(1, 1, 1, "barrel", facing="south", open=False)
    g.put(2, 1, 1, "barrel", facing="south", open=False)
    g.put(1, 2, 1, "barrel", facing="up", open=False)
    g.put(3, 1, 1, "chest", facing="south", type="single")
    g.put(1, 1, 5, "grindstone", face="floor", facing="east")
    g.put(1, 1, 3, "hay_block", axis="y")
    g.put(1, 1, 4, "hay_block", axis="y")
    for x in (5, 6):  # tool rack: open boards on the back wall + iron bars
        g.shutter(x, 2, 1, "south")
    g.put(5, 3, 1, "iron_bars")
    for x in (2, 5):
        g.put(x, 3, 3, "lantern", hanging=True)
        for z in range(1, 6):
            g.put(x, 4, z, "dark_oak_log", axis="z")
    return g


BUILDINGS = {
    "M-house_b": ("st03_house_b", house_b),
    "M-house_c": ("st03_house_c", house_c),
    "M-house_d": ("st03_house_d", house_d),
    "M-kitchen": ("st03_kitchen", kitchen),
    "M-smithy": ("st03_smithy", smithy),
    "M-cart_shed": ("st03_cart_shed", cart_shed),
}
DOORS = {  # (x, z) of the door column on the south face, or None for an open front
    "M-house_b": (4, 5), "M-house_c": (3, 5), "M-house_d": (3, 6),
    "M-kitchen": (4, 8), "M-smithy": None, "M-cart_shed": None,
}  # fmt: skip


def main(only=None):
    mods = A.modules()
    rep = {}
    for mid, (fname, fn) in BUILDINGS.items():
        if only and mid not in only:
            continue
        m = mods[mid]
        g = fn()
        assert [g.W, g.H, g.D] == m["size"] and m["air"] == "include" and m["file"] == fname, (mid, m)
        with tempfile.TemporaryDirectory() as d:
            r = export_module(m, g.c, Path(d) / "pack")
            shutil.copyfile(r.config.nbt_path, HERE / f"{fname}.nbt")
            shutil.copyfile(r.config.source, HERE / f"{fname}.schem")
            rep[fname] = r.report
        print(f"{fname}.nbt: {len(g.c)} authored cells, size {m['size']}")
    (HERE / "export-report.json").write_text(json.dumps(rep, indent=1, sort_keys=True, default=str) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
