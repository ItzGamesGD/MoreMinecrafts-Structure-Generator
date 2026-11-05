"""ST-03 warehouse batch: F07 military depot (M-warehouse_a 15x12x13) and F08 timber stores (M-warehouse_b 13x12x15).

Contract kept (tools/seam01/data/st03_placements.json, untouched): sizes above (x, y, z), air=include, floor y=0,
local_turns 0. F07 x=10..24, z=79..91 - its street face is +z (south), onto the open strip along the south wall that
leads to the gate; F19 is 3 blocks east, F06 6 blocks north. F08 x=75..87, z=53..67 - its street face is -x (west), onto
the central street like F03/F04; F04 is 3 blocks north (that gap is left clear), F18/F09 4 blocks east.

Free design brief ST03-IMPLEMENT-06; Q39-Q45 read as reference and kept where they fit:
  Q39 F07 more stone, thick timber supports, strong gable; F08 more timber, wider entrance, taller ventilated roof.
  Q40 ground-floor storage + accessible loft: F07 central aisle, military racks, small loft; F08 unloading area and loft.
  Q42 F07 stone-framed 2-block double timber door; F08 3-block-wide unloading entrance under a timber awning.
  Q43/Q44 windows, vents, lanterns, crates/barrels/hay outside, kept inside the footprint and off the doorways.

F07 "military depot" - a buttressed stone tithe barn. Tall stone walls on a rubble footing, a half-hipped (jerkinhead)
  deepslate roof, a projecting gabled cart porch on the street side with a stone-framed double door and a timber
  gable, ventilation slits. Inside: heavy tie beams on knee braces span the hall; a stone-brick carrying aisle runs
  from the porch to the back wall between the two storage bays - west: weapon crates and chests under a railed loft
  (arrow stores) reached by a ladder; east: tall slab racks of barrels and crates, spears, shields, anvil.
F08 "timber stores" - a tall timber-framed granary store. Steep dark-oak roof along the street with a full-height cross
  gable over a 3-wide unloading bay under a timber awning, shuttered windows, louvred gable vents, an external timber
  stair up the south gable to the loft door. Inside: a double-height unloading bay framed by a U-shaped gallery loft
  (sacks, hay), food barrels, grain bins, sacks and racks below, a ladder as the inside way up.

All containers are empty (block-entity allow-list); loot is a runtime decision. No mobs, spawners or loot authored.

  PYTHONPATH=. python experiments/st03-batch5-warehouses/build.py
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


B4 = _load("batch4_build", ROOT.parent / "st03-batch4-barracks" / "build.py")
Cells, stone, floor_stone, plinth, noise, path_stone = B4.Cells, B4.stone, B4.floor_stone, B4.plinth, B4.noise, B4.path_stone
stairs, trap, door, bed, hroof, base_course, OPP = B4.stairs, B4.trap, B4.door, B4.bed, B4.hroof, B4.base_course, B4.OPP


def roof_layers(c, base, raised, mat, ridge, skip=()):
    """hroof over `raised` (max of the main roof and a cross roof), then the main roof stair is also laid at its own
    height under every raised cell that is still empty, so no gap opens between the two eave lines."""
    hroof(c, raised, mat, ridge, skip=skip)
    under = {k: v for k, v in base.items() if raised.get(k, v) != v}
    tmp = Cells((c.W, c.H, c.D))
    hroof(tmp, base, mat, ridge)
    for (x, z), y in under.items():
        if (x, y, z) not in c and (x, y, z) in tmp:
            c[(x, y, z)] = tmp[(x, y, z)]


# ================================================================================================ F07 military depot
F7W, F7H, F7D = 15, 12, 13


def f07():
    """Street face +z. Barn walls x=1/12, z=1/8 (eaves x=0/13, z=0/9); cart porch walls x=4/9, front z=11 (verge 12);
    east strip x=14 is an open supply apron."""
    c = Cells((F7W, F7H, F7D))
    W, D = F7W, F7D
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, path_stone(x, z))
    for x in range(2, 12):
        for z in range(2, 8):
            c.put(x, 0, z, floor_stone(x, z))
    for x in (6, 7):  # carrying aisle: stone-brick runner from the porch to the back wall
        for z in range(2, 13):
            c.put(x, 0, z, "stone_bricks" if (x + z) % 3 else "polished_andesite")
    for x in (5, 8):
        for z in range(9, 11):
            c.put(x, 0, z, "polished_andesite")

    def wall(x, y, z):
        c.put(x, y, z, base_course(x, y, z) if y <= 2 else stone(x, y, z))

    g = lambda z: 6 + min(z, 9 - z)          # main gable along x, eaves y=6 at z=0/9, ridge y=10 at z=4/5
    cap = lambda x: 9 + min(x, 13 - x)       # half-hip (clipped gable): the ridge course turns down over the ends
    base = {(x, z): min(g(z), cap(x)) for x in range(0, 14) for z in range(0, 10)}
    # long walls z=1 / z=8, x=1..12, y1..6; gable walls x=1 / x=12 up to the roof
    for z in (1, 8):
        for x in range(1, 13):
            for y in range(1, 7):
                wall(x, y, z)
            c.put(x, 6, z, "stripped_dark_oak_log", axis="x")  # wall plate
    for xg in (1, 12):
        for z in range(1, 9):
            for y in range(1, base[(xg, z)]):
                wall(xg, y, z)
        for z in (1, 8):
            for y in range(1, 7):
                c.put(xg, y, z, "polished_andesite" if y % 2 else "stone_bricks")
        for y in (6, 7):  # paired high vents in the gable
            c.put(xg, y, 4, "iron_bars")
            c.put(xg, y, 5, "iron_bars")
        c.put(xg, 8, 4, "polished_andesite"); c.put(xg, 8, 5, "polished_andesite")
    # buttresses: north wall, gable ends, south wall either side of the porch
    for x in (3, 10):
        for y in range(1, 5):
            wall(x, y, 0)
        stairs(c, x, 5, 0, "stone_brick", "south")
    for x in (2, 11):
        for y in range(1, 5):
            wall(x, y, 9)
        stairs(c, x, 5, 9, "stone_brick", "north")
    for xo, face in ((0, "east"), (13, "west")):
        for z in (3, 6):
            for y in range(1, 5):
                wall(xo, y, z)
            stairs(c, xo, 5, z, "stone_brick", face)
    # ventilation slits
    for x in (2, 5, 8, 11):
        for y in (3, 4):
            c.put(x, y, 1, "iron_bars")
    for x in (3, 10):
        for y in (3, 4):
            c.put(x, y, 8, "iron_bars")

    # cart porch: walls x=4/9 (z=8..11), front z=11, timber gable, stone-framed double door (2 wide, x=6..7)
    p = lambda x: 6 + min(x - 3, 10 - x)    # porch gable along z, eaves y=6 at x=3/10, ridge y=9 at x=6/7
    for x in (4, 9):
        for z in range(9, 12):
            for y in range(1, 6):
                wall(x, y, z)
        for y in (2, 3):
            c.put(x, y, 10, "iron_bars")
    for x in range(4, 10):
        for y in range(1, p(x)):
            if y <= 4:
                wall(x, y, 11)
            elif x in (4, 9) or y == 5:
                c.put(x, y, 11, "dark_oak_log" if x in (4, 9) else "stripped_dark_oak_log",
                      axis="y" if x in (4, 9) else "x")
            else:
                c.put(x, y, 11, "spruce_planks")
    for x in (4, 9):
        for y in range(1, 5):
            c.put(x, y, 11, "polished_andesite" if y % 2 else "stone_bricks")
    for x in (5, 8):  # door jambs and arched head
        for y in (1, 2, 3):
            c.put(x, y, 11, "chiseled_stone_bricks" if y == 2 else "stone_bricks")
    stairs(c, 5, 4, 11, "stone_brick", "west", half="top")
    stairs(c, 8, 4, 11, "stone_brick", "east", half="top")
    for x in (6, 7):
        c.put(x, 3, 11, "stripped_dark_oak_log", axis="x")
        c.put(x, 4, 11, "stone_bricks")
    door(c, 6, 11, "dark_oak", "south", "left")
    door(c, 7, 11, "dark_oak", "south", "right")
    c.put(6, 6, 11, "dark_oak_log", axis="y"); c.put(7, 6, 11, "dark_oak_log", axis="y")
    c.put(6, 7, 11, "glass_pane"); c.put(7, 7, 11, "glass_pane")
    c.put(6, 8, 11, "dark_oak_log", axis="y"); c.put(7, 8, 11, "dark_oak_log", axis="y")
    for x in (5, 8):
        c.put(x, 3, 12, "white_wall_banner", facing="south")
    # arch from the porch into the barn (main wall z=8, x=5..8)
    for x in range(5, 9):
        for y in (1, 2, 3):
            c.put(x, y, 8, "air")
        c.put(x, 4, 8, "stripped_dark_oak_log", axis="x")

    # roofs
    raised = dict(base)
    for x in range(3, 11):
        for z in range(5, 13):
            raised[(x, z)] = max(raised.get((x, z), -99), p(x))
    roof_layers(c, base, raised, lambda x, z: "deepslate_tile", lambda x, z: ("deepslate_tiles", {}))
    for x, face in ((1, "east"), (12, "west")):  # ridge ends turn down into the clipped hips
        for z in (4, 5):
            stairs(c, x, 10, z, "deepslate_tile", face)

    # ---- interior: heavy tie beams wall to wall on knee braces (floor kept free), loft over the west bay, stores
    for x in (5, 8):
        for z in range(2, 8):
            c.put(x, 6, z, "stripped_dark_oak_log", axis="z")
        stairs(c, x, 5, 2, "dark_oak", "north", half="top")
        stairs(c, x, 5, 7, "dark_oak", "south", half="top")
        for y in (7, 8):  # king post up to the ridge
            c.put(x, y, 4, "dark_oak_log", axis="y")
    c.put(5, 5, 4, "lantern", hanging=True)
    c.put(8, 5, 5, "lantern", hanging=True)
    for x in range(5, 9):  # porch tie beam with a lantern over the doorway
        c.put(x, 6, 10, "stripped_dark_oak_log", axis="x")
    c.put(6, 5, 10, "lantern", hanging=True)

    # west bay x=2..4: loft floor y4 (x=2..4, z=2..7), ladder against the south wall, weapon crates below
    for x in (2, 3, 4):
        for z in range(2, 8):
            if (x, z) != (2, 7):
                c.put(x, 4, z, "spruce_planks")
    for z in range(2, 8):
        c.put(4, 5, z, "dark_oak_fence")
    for y in (1, 2, 3, 4):
        c.put(2, y, 7, "ladder", facing="north", waterlogged=False)
    c.put(2, 1, 2, "chest", facing="east", type="single")
    c.put(2, 1, 3, "fletching_table")
    c.put(2, 2, 3, "fletching_table")
    c.put(2, 1, 4, "chest", facing="east", type="single")
    c.put(2, 1, 5, "smithing_table")
    c.put(2, 1, 6, "barrel", facing="east", open=False)
    c.put(2, 2, 6, "barrel", facing="east", open=False)
    c.put(3, 3, 5, "lantern", hanging=True)
    # loft: arrow and bolt stores, target, hay bedding
    c.put(2, 5, 2, "barrel", facing="east", open=False)
    c.put(2, 6, 2, "barrel", facing="east", open=False)
    c.put(3, 5, 2, "fletching_table")
    c.put(2, 5, 3, "target")
    c.put(2, 5, 5, "barrel", facing="up", open=False)
    c.put(2, 5, 6, "hay_block", axis="z")
    c.put(3, 5, 4, "lantern", hanging=False)

    # east bay x=9..11: tall racks against the gable (slab shelves on posts), shield wall, iron stock
    for z in range(2, 8):
        for y in (2, 4):
            c.put(11, y, z, "spruce_slab", type="top")
        if z in (2, 4, 7):
            c.put(11, 1, z, "barrel", facing="west", open=False)
    c.put(11, 1, 3, "fletching_table")
    c.put(11, 1, 5, "chest", facing="west", type="single")
    c.put(11, 1, 6, "smithing_table")
    for z in (2, 3, 6, 7):
        c.put(11, 3, z, "barrel", facing="west", open=False)
    c.put(11, 3, 4, "fletching_table")
    c.put(11, 3, 5, "fletching_table")
    for z in (2, 5, 7):
        c.put(11, 5, z, "hay_block", axis="z")
    c.put(11, 5, 3, "hay_block", axis="y")
    c.put(9, 1, 2, "barrel", facing="up", open=False)  # spears standing in a barrel, shields on the north wall
    c.put(9, 2, 2, "exposed_lightning_rod", facing="up")
    for x in (9, 10):
        c.put(x, 3, 2, "grindstone", face="wall", facing="south")
    c.put(9, 1, 7, "anvil", facing="east")
    c.put(9, 3, 7, "white_wall_banner", facing="north")
    for y in (7, 8, 9):  # lantern on a chain from the ridge over the east bay
        c.put(10, y, 5, "iron_chain", axis="y")
    c.put(10, 6, 5, "lantern", hanging=True)
    # back wall of the aisle: banner between two shield racks, a cart's worth of crates in the aisle head
    c.put(6, 3, 2, "white_wall_banner", facing="south")
    c.put(7, 3, 2, "white_wall_banner", facing="south")
    c.put(6, 1, 2, "barrel", facing="south", open=False)
    c.put(7, 1, 2, "fletching_table")
    c.put(5, 1, 7, "barrel", facing="up", open=False)
    c.put(8, 1, 7, "barrel", facing="up", open=False)

    # ---- street apron: stacked supply crates on the east strip, lantern posts at the porch, approach kept clear
    for z in (2, 6, 10):
        c.put(14, 1, z, "barrel", facing="east", open=False)
    for z in (3, 5, 9):
        c.put(14, 1, z, "hay_block", axis="z")
    for z in (2, 9):
        c.put(14, 2, z, "barrel", facing="up", open=False)
    c.put(14, 1, 4, "stripped_spruce_log", axis="z")
    for x, z in ((3, 12), (10, 12)):
        c.put(x, 1, z, "stone_brick_wall")
        c.put(x, 2, z, "lantern", hanging=False)
    c.put(1, 1, 11, "barrel", facing="up", open=False)
    c.put(2, 1, 11, "fletching_table")
    c.put(1, 1, 10, "barrel", facing="south", open=False)
    c.put(12, 1, 11, "hay_block", axis="x")
    c.put(12, 2, 11, "hay_block", axis="z")
    c.put(11, 1, 11, "barrel", facing="up", open=False)
    return c


# ================================================================================================= F08 timber stores
F8W, F8H, F8D = 13, 12, 15


def f08():
    """Street face -x. Walls x=1 (front) / x=11 (rear), gables z=1 / z=13 (verges z=0 / z=14); main ridge along z at
    x=6 (y=11); cross gable over the unloading bay, face x=1, z=3..11, ridge along x at z=7 (y=11)."""
    c = Cells((F8W, F8H, F8D))
    W, D = F8W, F8D
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, path_stone(x, z) if x > 0 else ["gravel", "coarse_dirt", "gravel", "stone_bricks"][noise(x, z, 4, 3)])
    for x in range(2, 11):
        for z in range(2, 13):
            c.put(x, 0, z, "spruce_planks")
    for x in range(0, 9):  # worn unloading lane
        for z in (6, 7, 8):
            c.put(x, 0, z, ["coarse_dirt", "gravel", "packed_mud", "coarse_dirt", "stripped_spruce_log"][noise(x, z, 5, 4)]
                  if x < 2 else ("stripped_spruce_log" if z != 7 else "spruce_planks"),
                  **({"axis": "x"} if (x >= 2 and z != 7) or (x < 2 and noise(x, z, 5, 4) == 4) else {}))

    m = lambda x: 5 + min(x, 12 - x)        # main roof: eaves y=5 at x=0/12, ridge y=11 at x=6
    cg = lambda z: 7 + min(z - 3, 11 - z)   # cross gable: eaves y=7 at z=3/11, ridge y=11 at z=7
    base = {(x, z): m(x) for x in range(W) for z in range(D)}
    raised = dict(base)
    for x in range(0, 7):
        for z in range(3, 12):
            raised[(x, z)] = max(base[(x, z)], cg(z))
    posts_z = (1, 3, 5, 9, 11, 13)

    def frame(x, y, z, post, rail_axis):
        """Timber frame cell: two-course stone footing (y1-2), dark-oak posts, wall plate y5, spruce board infill."""
        if y <= 2:
            c.put(x, y, z, base_course(x, y, z) if y == 1 else stone(x, y, z))
        elif post:
            c.put(x, y, z, "dark_oak_log", axis="y")
        elif y == 5:
            c.put(x, y, z, "stripped_dark_oak_log", axis=rail_axis)
        else:
            c.put(x, y, z, "spruce_planks")

    # long walls x=1 (outside the cross gable) and x=11, y1..5
    for xw in (1, 11):
        for z in range(1, 14):
            if xw == 1 and 3 <= z <= 11:
                continue
            for y in range(1, 6):
                frame(xw, y, z, z in posts_z or z in (7,), "z")
    # gables z=1 / z=13 up to the main roof
    for zg in (1, 13):
        for x in range(1, 12):
            for y in range(1, m(x)):
                post = x in (1, 3, 6, 9, 11) and y <= 5 or (x == 6)
                if y > 5 and not post:
                    c.put(x, y, zg, "spruce_planks")
                else:
                    frame(x, y, zg, post, "x")
        for x in (5, 7):  # louvred vents high in the gable
            trap(c, x, 9, zg, "spruce", "north" if zg == 1 else "south", open_=False, half="top")
        for x in (4, 8):
            c.put(x, 2, zg, "glass_pane"); c.put(x, 3, zg, "glass_pane")
    # cross-gable face x=1, z=3..11 (cheeks at z=3/11 reach up under its eaves)
    for z in range(3, 12):
        for y in range(1, cg(z)):
            post = z in (3, 5, 9, 11) or (z == 7 and y >= 6)
            if y > 5 and not post:
                c.put(1, y, z, "spruce_planks")
            else:
                frame(1, y, z, post, "z")
    # unloading opening 3 wide x 3 high (z=6..8), heavy lintel, awning on brackets
    for z in (6, 7, 8):
        for y in (1, 2, 3):
            c.put(1, y, z, "air")
        c.put(1, 4, z, "stripped_dark_oak_log", axis="z")
    for z in (5, 9):
        for y in (1, 2, 3, 4):
            c.put(1, y, z, "dark_oak_log", axis="y")
        stairs(c, 0, 3, z, "dark_oak", "east", half="top")
    for z in range(4, 11):
        stairs(c, 0, 4, z, "dark_oak" if z in (4, 10) else "spruce", "east")
    c.put(0, 3, 7, "lantern", hanging=True)
    # windows either side of the bay, glazed loft door between two windows above the awning, louvred apex vent
    for z in (4, 10):
        c.put(1, 2, z, "glass_pane")
    for z in (6, 8):
        c.put(1, 6, z, "glass_pane"); c.put(1, 7, z, "glass_pane")
    c.put(1, 6, 7, "spruce_door", facing="west", half="lower", hinge="left", open=False, powered=False)
    c.put(1, 7, 7, "spruce_door", facing="west", half="upper", hinge="left", open=False, powered=False)
    c.put(0, 5, 7, "spruce_slab", type="top")  # little loading ledge on the awning ridge
    for y in (9, 10):
        trap(c, 1, y, 7, "spruce", "west", open_=False, half="top")
    # front wall windows outside the cross gable, rear windows (Q43: 2-3 medium shuttered)
    for z in (2, 12):
        c.put(1, 2, z, "glass_pane")
        c.put(1, 4, z, "glass_pane")
    for z in (4, 7, 10):
        c.put(11, 2, z, "glass_pane"); c.put(11, 4, z, "glass_pane")
        trap(c, 12, 2, z - 1, "dark_oak", "east")
        trap(c, 12, 2, z + 1, "dark_oak", "east")

    # roofs: dark oak throughout (a dark outline over the light board gables), log ridge
    roof_layers(c, base, raised,
                lambda x, z: "dark_oak",
                lambda x, z: ("dark_oak_log", {"axis": "z" if x == 6 else "x"}) if z in (0, 14) or x == 0 else
                ("stripped_dark_oak_log", {"axis": "z" if x == 6 and not (3 <= z <= 11) else ("x" if x < 6 else "z")}))

    # ---- interior: U-shaped gallery loft (floor y5) round the double-height unloading bay
    loft = {(x, z) for x in range(2, 11) for z in list(range(2, 5)) + list(range(10, 13))}
    loft |= {(x, z) for x in (8, 9, 10) for z in range(5, 10)}
    for x, z in loft:
        c.put(x, 5, z, "spruce_planks")
    c.put(3, 5, 2, "air")  # ladder hole
    for x in range(3, 8):
        c.put(x, 6, 4, "spruce_fence"); c.put(x, 6, 10, "spruce_fence")
    for z in range(4, 11):
        c.put(8, 6, z, "spruce_fence")
    for y in (1, 2, 3, 4, 5):
        c.put(3, y, 2, "ladder", facing="south", waterlogged=False)
    for x, z in ((8, 4), (8, 10), (4, 4), (4, 10)):  # gallery posts
        for y in (1, 2, 3, 4):
            c.put(x, y, z, "dark_oak_log", axis="y")
    for x in range(2, 9):  # gallery edge beams
        if x not in (4, 8):
            c.put(x, 4, 4, "stripped_dark_oak_log", axis="x")
            c.put(x, 4, 10, "stripped_dark_oak_log", axis="x")
    for z in range(5, 10):
        c.put(8, 4, z, "stripped_dark_oak_log", axis="z")
    c.put(5, 9, 7, "iron_chain", axis="y"); c.put(5, 8, 7, "iron_chain", axis="y")
    c.put(5, 7, 7, "lantern", hanging=True)
    c.put(5, 10, 7, "stripped_dark_oak_log", axis="x")
    # unloading bay: a loaded handcart, sacks being sorted
    for z in (6, 8):
        c.put(6, 1, z, "spruce_trapdoor", facing="north" if z == 6 else "south", half="bottom", open=True, powered=False, waterlogged=False)
    c.put(6, 1, 7, "spruce_slab", type="top")
    c.put(6, 2, 7, "barrel", facing="up", open=False)
    c.put(7, 1, 7, "spruce_fence")
    # under the north gallery (z=2..3): food barrels, grain bins, sacks
    for x in (5, 7):
        c.put(x, 1, 2, "barrel", facing="up", open=False)
    for x in (4, 6):
        c.put(x, 1, 2, "composter")
    c.put(7, 2, 2, "barrel", facing="south", open=False)
    for x in (5, 7):
        c.put(x, 1, 3, "light_gray_wool")
    c.put(6, 1, 3, "brown_wool")
    c.put(9, 1, 2, "chest", facing="south", type="single")
    c.put(10, 1, 2, "hay_block", axis="x")
    c.put(10, 2, 2, "hay_block", axis="z")
    c.put(10, 1, 3, "hay_block", axis="y")
    c.put(5, 4, 3, "lantern", hanging=True)
    # under the south gallery (z=11..12): racks of preserved food, pumpkins, melons
    for x in range(3, 8):
        c.put(x, 2, 12, "spruce_slab", type="top")
        if x in (3, 7):
            c.put(x, 1, 12, "barrel", facing="north", open=False)
        else:
            c.put(x, 1, 12, "pumpkin" if x == 5 else "melon")
    c.put(4, 3, 12, "barrel", facing="north", open=False)
    c.put(6, 3, 12, "barrel", facing="north", open=False)
    c.put(9, 1, 12, "chest", facing="north", type="single")
    c.put(10, 1, 12, "barrel", facing="up", open=False)
    c.put(10, 1, 11, "barrel", facing="west", open=False)
    c.put(5, 1, 11, "brown_wool")
    c.put(5, 4, 11, "lantern", hanging=True)
    # rear of the bay (x=9..10 under the gallery bridge): flour sacks and hay
    c.put(10, 1, 5, "brown_wool")
    c.put(10, 1, 6, "light_gray_wool")
    c.put(10, 2, 5, "hay_block", axis="z")
    c.put(9, 1, 5, "light_gray_wool")
    c.put(10, 1, 8, "hay_block", axis="z"); c.put(10, 1, 9, "hay_block", axis="y"); c.put(10, 2, 9, "hay_block", axis="x")
    c.put(9, 4, 7, "lantern", hanging=True)
    # gallery stores: hay and sacks (bedding/feed), a few barrels
    for x in (5, 6, 7):
        c.put(x, 6, 2, "hay_block", axis="x")
    c.put(6, 7, 2, "hay_block", axis="z")
    c.put(3, 6, 12, "barrel", facing="up", open=False)
    c.put(4, 6, 12, "light_gray_wool")
    c.put(5, 6, 12, "brown_wool")
    c.put(7, 6, 12, "hay_block", axis="y")
    for z in (6, 8):
        c.put(10, 6, z, "hay_block", axis="z")
    c.put(10, 6, 7, "light_gray_wool")
    c.put(9, 6, 2, "barrel", facing="up", open=False)
    c.put(6, 6, 12, "air")

    # external stair up the south gable to the loft door (z=13, x=6, y6..7)
    for i, x in enumerate(range(1, 6)):
        stairs(c, x, 1 + i, 14, "spruce", "east")
        if x in (3, 5):  # the flight is carried on two dark-oak posts, open underneath
            for y in range(1, 1 + i):
                c.put(x, y, 14, "dark_oak_log", axis="y")
    c.put(6, 5, 14, "spruce_planks")
    for y in (1, 2, 3, 4):
        c.put(6, y, 14, "dark_oak_log", axis="y")
    c.put(6, 6, 13, "spruce_door", facing="south", half="lower", hinge="left", open=False, powered=False)
    c.put(6, 7, 13, "spruce_door", facing="south", half="upper", hinge="left", open=False, powered=False)

    # ---- street apron: crates/barrels and hay by the bay (doorway lane z=6..8 kept clear), loading step
    c.put(0, 1, 2, "barrel", facing="up", open=False)
    c.put(0, 1, 3, "barrel", facing="west", open=False)
    c.put(0, 2, 2, "barrel", facing="up", open=False)
    c.put(0, 1, 11, "hay_block", axis="z")
    c.put(0, 1, 12, "hay_block", axis="y")
    c.put(0, 2, 12, "hay_block", axis="x")
    c.put(0, 1, 4, "composter")
    c.put(0, 1, 10, "barrel", facing="up", open=False)
    return c


# -------------------------------------------------------------------------------------------- registry
# door: entrance column on the street face; walls: (x0, x1, z0, z1) boxes of the walled body (outside = open apron).
BUILDINGS = {
    "warehouse_a": dict(module="M-warehouse_a", placement="F07", design=f07, size=(F7W, F7H, F7D),
                        door=(6, 12), entrances={"cart_porch_south": (6, 13), "cart_porch_south_b": (7, 13)},
                        walls=[(1, 12, 1, 8), (4, 9, 8, 11)]),
    "warehouse_b": dict(module="M-warehouse_b", placement="F08", design=f08, size=(F8W, F8H, F8D),
                        door=(0, 7), entrances={"unloading_bay_west": (-1, 7), "loft_stair_south": (0, 15)},
                        walls=[(1, 11, 1, 13)]),
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
