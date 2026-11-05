"""ST-03 batch 6: F09 prison (M-prison 11x10x13) and F10 ravager stable (M-stable 17x13x13).

Contract kept (tools/seam01/data/st03_placements.json, untouched): sizes above (x, y, z), air=include, floor y=0,
local_turns 0. F09 x=92..102, z=62..74; F10 x=77..93, z=79..91. Both street faces are +z (south):
  F09 - north is F18 (3 blocks), west F08 (4), east the W-E wall (4), south-west F10 (4, overlapping x only at
        92..93); its south face looks onto the open south-east ground (x 94..106 is free down to the south wall).
  F10 - north is F08 (11), north-east F09 (4); its south face opens onto the strip along the south wall that runs
        west to the gate, so the ravagers' sortie runs straight to the gate.

Design source: owner ledger Q46-Q59 (Beta repo, docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md):
  F09 Q46/Q47/Q49 stone-heavy, straight central corridor, two cells each side = four cells, NO guard room, NO loft;
      Q48 simple bed/straw per cell, minimal differing details, chains, iron bars, corridor lanterns;
      Q50 single iron entry door in a stone-brick frame, two tiny barred windows, lantern above, a button opens it,
      no guard post / awning / banner; Q51 heavy stone brick, sparing cracked/mossy, low stone gable, minimal roof wood.
  F10 Q53 fortified stone lower walls/pillars, dark-oak frame, spruce upper walls, high gable roof, broad entrance;
      Q54 two large side pens, straight central aisle, individual pen entries and feeders, small rear hay/feed store;
      Q55 stone-brick pillars/low walls, dark-oak fences, wide reinforced openings; Q56 coarse/packed dirt and hay in
      the pens, cobble/stone-brick aisle, rear hay/barrels/crates, hanging lanterns; Q57 central stone-and-timber
      entrance >= 3 wide x 4 high with an open decorative gate; Q58 side windows with shutters, high vents, exposed
      beams, ample headroom.

F09 "cell block": a buttressed stone-brick block on a battered plinth, a corbelled cornice under a low dark rubble-slab
  gable roof over stone gables, with a stone verge projecting over the street gable. Front: one iron door in a
  chiselled frame under a hood moulding with a lantern, a stone button either side of the door, two tiny barred
  windows, a string course, angle buttresses. Inside: a vestibule, then a
  one-block corridor between iron-bar cell fronts; each cell has an iron door opened by a button on the corridor side
  (jailer side only, on the lintel over the door - no button inside a cell), a bed or straw pallet, a chain, a barred slit window.
F10 "monitor stable": a raised central nave (high spruce gable, clerestory vents) over the aisle between two lean-to
  pen wings on stone lower walls with buttresses. Front: a 3x4 stone-and-timber portal with folded-back dark-oak gate
  leaves, lantern pillars, illager banner, hay and barrels. Inside: two open pens (no gate, no restraint) with dirt
  and hay bedding, a feed bin and water trough each, low stone walls with dark-oak rails, exposed tie beams with king
  posts, hanging lanterns, a rear hay stack, feed store and tack chest at the aisle head.

All containers empty (block-entity allow-list). No mobs, spawners, AI or loot authored. The two ravager initial
positions are recorded in BUILDINGS (local coordinates), not placed as entities.

  PYTHONPATH=. python experiments/st03-batch6-prison-stable/build.py
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
Cells, floor_stone, noise, path_stone = B4.Cells, B4.floor_stone, B4.noise, B4.path_stone
stairs, trap, door, bed, hroof, base_course = B4.stairs, B4.trap, B4.door, B4.bed, B4.hroof, B4.base_course


def wall_stone(x, y, z):
    """Heavy stone brick, sparing cracked / mossy variation, more of it low on the wall (owner stone principle)."""
    h = noise(x * 3 + y, z, 23, y + 5)
    if h == 0:
        return "cracked_stone_bricks"
    if h == 1 or (h == 2 and y <= 2):
        return "mossy_stone_bricks"
    return "stone_bricks"


def slab(c, x, y, z, mat, half):
    c.put(x, y, z, f"{mat}_slab", type=half, waterlogged=False)


def button(c, x, y, z, facing, mat="stone"):
    """Wall button at (x, y, z); `facing` points away from the block it is attached to."""
    c.put(x, y, z, f"{mat}_button", face="wall", facing=facing, powered=False)


def iron_door(c, x, z, facing, hinge, y=1):
    door(c, x, z, "iron", facing, hinge, y=y)


def half_roof(c, x_eave, x_top, ys, z0, z1, mat):
    """Low-pitch slab roof: x from the eave toward the ridge rises half a block per column; ys[i] = (y, half)."""
    step = 1 if x_top > x_eave else -1
    for i, x in enumerate(range(x_eave, x_top + step, step)):
        y, half = ys[i]
        for z in range(z0, z1 + 1):
            slab(c, x, y, z, mat(x, z), half)


# ================================================================================================= F09 prison
P_W, P_H, P_D = 11, 10, 13
# roof surface per x (y, half): half-pitch rubble slabs from the eaves (x=0/10) to the ridge (x=5)
P_ROOF = {0: (6, "bottom"), 1: (6, "top"), 2: (7, "bottom"), 3: (7, "top"), 4: (8, "bottom"), 5: (8, "top")}


def p_roof_at(x):
    return P_ROOF[min(x, P_W - 1 - x)]


def f09():
    """Street face +z. Walls x=1/9, z=0 (rear) and z=11 (front); buttresses x=0/10; z=12 front apron.
    Inside: cells x2..3 / x7..8 at z1..3 and z5..7, cell fronts (bars + iron door) x=4/6, corridor x=5 z1..8,
    vestibule x2..8 z9..10."""
    c = Cells((P_W, P_H, P_D))
    W, D = P_W, P_D
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, path_stone(x, z))
    for x in range(2, 9):
        for z in range(1, 11):
            c.put(x, 0, z, floor_stone(x, z))
    for z in range(1, 11):  # corridor and vestibule runner
        c.put(5, 0, z, "stone_bricks" if noise(5, z, 5, 2) else "cracked_stone_bricks")
    for x in range(2, 9):
        for z in (9, 10):
            c.put(x, 0, z, "stone_bricks" if noise(x, z, 6, 3) else "polished_andesite")

    # ---- outer walls y1..5 (plinth course y1), front z=11, rear z=0
    for y in range(1, 6):
        for z in range(0, 12):
            for x in (1, 9):
                c.put(x, y, z, base_course(x, y, z) if y == 1 else wall_stone(x, y, z))
        for x in range(2, 9):
            for z in (0, 11):
                c.put(x, y, z, base_course(x, y, z) if y == 1 else wall_stone(x, y, z))
    # corbel table under the eaves between the buttresses (x=0/10, y=5)
    for z in range(1, 11):
        if z in (4, 8):
            continue
        stairs(c, 0, 5, z, "stone_brick", "east", half="top")
        stairs(c, 10, 5, z, "stone_brick", "west", half="top")
    # buttresses: full-height corner piers (carry the eaves), stepped intermediate ones at the partitions
    for z in (0, 11):
        for x in (0, 10):
            for y in range(1, 6):
                c.put(x, y, z, "stone_bricks" if y > 1 else "cobblestone")
    for z in (4, 8):
        for x, f in ((0, "east"), (10, "west")):
            for y in range(1, 4):
                c.put(x, y, z, "stone_bricks" if y > 1 else base_course(x, y, z))
            stairs(c, x, 4, z, "stone_brick", f)
            c.put(x, 5, z, "stone_bricks")
    # angle buttresses on the street face
    for x in (1, 9):
        for y in range(1, 5):
            c.put(x, y, 12, "stone_bricks" if y > 1 else "cobblestone")
        stairs(c, x, 5, 12, "stone_brick", "north")
    # cell slits (side walls) and a rear slit at the corridor end
    for x in (1, 9):
        for z in (2, 6):
            c.put(x, 2, z, "iron_bars"); c.put(x, 3, z, "iron_bars")
    c.put(5, 3, 0, "iron_bars")
    # battered plinth between the buttresses (sides) and either side of the door (street face)
    for z in range(1, 11):
        if z not in (4, 8):
            stairs(c, 0, 1, z, "stone_brick", "east"); stairs(c, 10, 1, z, "stone_brick", "west")
    for x in (2, 3, 7, 8):
        stairs(c, x, 1, 12, "stone_brick", "north")
    # string course under the front gable, between the angle buttresses
    for x in range(2, 9):
        stairs(c, x, 5, 12, "stone_brick", "north", half="top")

    # ---- roof: dark rubble slabs over stone gables; the roof runs out over the street gable as a verge (z=12) and
    # stops flush on the rear gable (z=0 is the module edge). Corner piers carry the eaves.
    def rmat(x, z):
        return "deepslate_tile" if noise(x, z, 5, 9) == 0 else "cobbled_deepslate"

    for x in range(W):
        y, half = p_roof_at(x)
        for z in range(0, 13):
            if z == 11 and half == "top":
                c.put(x, y, z, wall_stone(x, y, z))  # street gable carried up flush under the verge's top-slab step
            elif z == 0 and half == "top":
                c.put(x, y, z, "cobbled_deepslate")  # rear edge: a full rubble block keeps the roof line closed
            else:
                slab(c, x, y, z, rmat(x, z), half)
        for z in (0, 11):  # gable wall up to the roof line
            for yy in range(6, y):
                c.put(x, yy, z, wall_stone(x, yy, z))
    c.put(5, 7, 11, "iron_bars")  # gable vent over the door
    c.put(5, 7, 0, "iron_bars")

    # ---- street face: iron door in a chiselled frame, buttons both sides, hood moulding, lantern, two tiny windows
    for y in (1, 2):
        for x in (4, 6):
            c.put(x, y, 11, "chiseled_stone_bricks" if y == 1 else "stone_bricks")
    c.put(4, 3, 11, "chiseled_stone_bricks"); c.put(5, 3, 11, "stone_bricks"); c.put(6, 3, 11, "chiseled_stone_bricks")
    iron_door(c, 5, 11, "north", "left")
    button(c, 4, 2, 12, "south")  # outside: on the west jamb
    button(c, 6, 2, 10, "north")  # inside: on the east jamb
    for x in (4, 5, 6):
        stairs(c, x, 3, 12, "stone_brick", "north", half="top")
    c.put(5, 4, 12, "lantern", hanging=False, waterlogged=False)
    for x in (2, 8):
        c.put(x, 3, 11, "iron_bars")
    c.put(5, 0, 12, "stone_bricks")
    for x in (4, 6):
        c.put(x, 0, 12, "polished_andesite")

    # ---- interior: partitions (z=4), cell back walls (z=8), cell fronts (x=4/6), ceilings y4
    for y in range(1, 5):
        for x in (2, 3, 4, 6, 7, 8):
            for z in (4, 8):
                c.put(x, y, z, wall_stone(x, y, z) if y > 1 else "stone_bricks")
    for z in range(1, 9):
        for x in (2, 3, 4, 6, 7, 8):
            c.put(x, 4, z, "stone_bricks" if noise(x, z, 7, 4) else "cracked_stone_bricks")
    # cell fronts: iron bars with one iron door each under a stone lintel; west doors at z=2/6, east doors at z=3/7
    # so each door's button can sit on its own lintel, on the corridor side only (jailer side)
    doors = {(4, 2): "west", (4, 6): "west", (6, 3): "east", (6, 7): "east"}
    for x in (4, 6):
        for z in (1, 2, 3, 5, 6, 7):
            if (x, z) in doors:
                iron_door(c, x, z, doors[(x, z)], "right" if x == 4 else "left")
                c.put(x, 3, z, "chiseled_stone_bricks")
                button(c, 5, 3, z, "east" if x == 4 else "west")
            else:
                for y in (1, 2, 3):
                    c.put(x, y, z, "iron_bars")
    # minimal roof wood: three tie beams with hanging lanterns over the corridor and vestibule
    for z in (2, 6, 9):
        for x in range(2, 9):
            c.put(x, 5, z, "dark_oak_log", axis="x")
        c.put(5, 4, z, "lantern", hanging=True, waterlogged=False)

    # ---- cells: simple bed or straw, a chain, small differing details
    bed(c, 2, 1, 1, "brown", "north")                       # NW: bed, wall chain
    c.put(3, 3, 1, "iron_chain", axis="y"); c.put(3, 2, 1, "iron_chain", axis="y")
    bed(c, 8, 1, 1, "gray", "north")                        # NE: bed, slop bucket (cauldron)
    c.put(7, 1, 1, "cauldron")
    c.put(8, 3, 3, "cobweb")
    c.put(2, 1, 7, "hay_block", axis="z"); c.put(2, 1, 6, "hay_block", axis="z")  # SW: straw pallet, chain
    c.put(3, 3, 5, "iron_chain", axis="y")
    bed(c, 8, 1, 5, "brown", "north")                       # SE: bed, straw
    c.put(8, 1, 7, "hay_block", axis="x")
    c.put(7, 3, 7, "cobweb")
    for x, z in ((3, 2), (2, 5), (7, 6), (8, 2)):
        c.put(x, 0, z, "mossy_cobblestone")
    # vestibule: one barrel for confiscated gear, nothing else (no guard room, Q46/Q49)
    c.put(2, 1, 10, "barrel", facing="up", open=False)
    return c


# ========================================================================================= F10 ravager stable
S_W, S_H, S_D = 17, 13, 13
# lean-to pen roofs: half-pitch slabs from the eaves (x=0 / 16) up to the clerestory (x=5 / 11)
LEAN = [(5, "bottom"), (5, "top"), (6, "bottom"), (6, "top"), (7, "bottom"), (7, "top")]
# monitor (central nave) gable roof: stairs x5..11, ridge x8 at y12
NAVE = {5: 9, 6: 10, 7: 11, 8: 12, 9: 11, 10: 10, 11: 9}
RAVAGER_SPAWNS = {"west_pen": (4.0, 1.0, 7.0), "east_pen": (13.0, 1.0, 7.0)}  # entity centre, local coordinates


def f10():
    """Street face +z. Outer walls x=1/15, z=1 (rear) / 11 (front), eaves x=0/16, verges z=0/12.
    Monitor post lines x=6/10 (posts z=4, 8), aisle x7..9, pens x2..5 / x11..14 at z4..10, hay / feed stacks
    behind the pens at z2..3, store and tack at the aisle head x6..10 z2..3."""
    c = Cells((S_W, S_H, S_D))
    W, D = S_W, S_D
    for x in range(W):
        for z in range(D):
            h = noise(x, z, 6, 21)
            c.put(x, 0, z, ["gravel", "cobblestone", "coarse_dirt", "gravel", "stone", "andesite"][h])
    for x in range(2, 15):
        for z in range(2, 11):
            h = noise(x, z, 9, 22)
            c.put(x, 0, z, ["coarse_dirt", "packed_mud", "coarse_dirt", "rooted_dirt", "hay_block", "coarse_dirt",
                            "packed_mud", "hay_block", "dirt"][h], **({"axis": "x"} if h in (4, 7) else {}))
    for z in range(1, 13):  # aisle: cobble with a stone-brick runner
        for x in (7, 8, 9):
            c.put(x, 0, z, "stone_bricks" if x == 8 or noise(x, z, 4, 23) == 0 else
                  ("cobblestone" if noise(x, z, 3, 24) else "mossy_cobblestone"))

    # ---- outer walls: fortified stone y1..3 (rubble course y1), dark-oak wall plate y4; spruce only above
    def wall(x, y, z):
        if y == 1:
            c.put(x, y, z, base_course(x, y, z))
        elif y <= 3:
            c.put(x, y, z, wall_stone(x, y, z))
        else:
            c.put(x, y, z, "dark_oak_log", axis="z" if x in (1, 15) else "x")

    for z in range(1, 12):
        for x in (1, 15):
            for y in range(1, 5):
                wall(x, y, z)
    for x in range(2, 15):
        for z in (1, 11):
            if 6 <= x <= 10:
                continue
            for y in range(1, 5):
                wall(x, y, z)
    for x in (1, 15):  # stone corner quoins full height
        for z in (1, 11):
            for y in range(1, 5):
                c.put(x, y, z, "stone_bricks" if (y + z) % 2 else "polished_andesite")
    # side windows: two per side, 2 wide, dark-oak rails and open spruce shutters
    for x, f in ((1, "west"), (15, "east")):
        ox = 0 if x == 1 else 16
        for z0 in (3, 8):
            for z in (z0, z0 + 1):
                c.put(x, 3, z, "dark_oak_fence")
            trap(c, ox, 3, z0 - 1, "spruce", f)
            trap(c, ox, 3, z0 + 2, "spruce", f)
    # buttresses at mid-wall and the corners
    for x, f in ((0, "east"), (16, "west")):
        for z in (1, 6, 11):
            for y in (1, 2, 3):
                c.put(x, y, z, "stone_bricks" if y > 1 else "cobblestone")
            stairs(c, x, 4, z, "stone_brick", f)

    # ---- monitor frame: post lines x=6/10, beams y7 along z, clerestory walls y8..9 with vents
    for x in (6, 10):
        for z in (1, 4, 8, 11):
            for y in range(1, 7):
                c.put(x, y, z, ("stone_bricks" if y > 1 else "chiseled_stone_bricks") if y <= 2 or z in (1, 11)
                      else "dark_oak_log", **({} if y <= 2 or z in (1, 11) else {"axis": "y"}))
        for z in range(1, 12):
            c.put(x, 7, z, "dark_oak_log", axis="z")
            if z in (1, 4, 8, 11):
                c.put(x, 8, z, "dark_oak_log", axis="y"); c.put(x, 9, z, "dark_oak_log", axis="y")
            else:
                c.put(x, 8, z, "dark_oak_fence")  # clerestory vent strip, just above the lean-to roofs
                c.put(x, 9, z, "spruce_planks")
    # tie beams across the nave on the post lines, king posts to the ridge, lanterns under them
    for z in (4, 8):
        for x in (7, 8, 9):
            c.put(x, 8, z, "dark_oak_log", axis="x")
        for y in (9, 10, 11):
            c.put(8, y, z, "dark_oak_log", axis="y")
        c.put(8, 7, z, "lantern", hanging=True, waterlogged=False)
    # pen cross beams (wall to post) at y5, lanterns hanging over the pens
    for z in (4, 8):
        for x in list(range(2, 6)) + list(range(11, 15)):
            c.put(x, 5, z, "dark_oak_log", axis="x")
    for x in (3, 13):
        c.put(x, 4, 8, "lantern", hanging=True, waterlogged=False)

    # ---- pen fronts: entry z5..7 always open (no gate, no restraint); feeder + low wall + rail at z9..10
    for x in (6, 10):
        c.put(x, 1, 9, "composter", level=7)
        c.put(x, 1, 10, "stone_bricks")
        c.put(x, 2, 9, "dark_oak_fence"); c.put(x, 2, 10, "dark_oak_fence")
    # water troughs in the outer front corner of each pen
    c.put(2, 1, 10, "water_cauldron", level=3); c.put(14, 1, 10, "water_cauldron", level=3)
    # rear stacks behind the pens (>= 2 high so the pen is bounded by them): west hay, east feed
    for x in range(2, 6):
        for z in (2, 3):
            c.put(x, 1, z, "hay_block", axis="x"); c.put(x, 2, z, "hay_block", axis="z" if x % 2 else "x")
        if x <= 4:
            c.put(x, 3, 2, "hay_block", axis="x")
    east = {(11, 2): ["barrel", "barrel"], (12, 2): ["brown_wool", "hay_block"], (13, 2): ["hay_block", "hay_block"],
            (14, 2): ["light_gray_wool", "hay_block"], (11, 3): ["barrel", "hay_block"], (12, 3): ["barrel", "brown_wool"],
            (13, 3): ["hay_block", "brown_wool"], (14, 3): ["barrel", "hay_block"]}  # barrels only where reachable
    for (x, z), stack in east.items():
        for i, b in enumerate(stack):
            if b == "barrel":
                c.put(x, 1 + i, z, "barrel", facing="up" if i else "south", open=False)
            elif b == "hay_block":
                c.put(x, 1 + i, z, "hay_block", axis="y")
            else:
                c.put(x, 1 + i, z, b)
    # aisle-head store and tack: chest, barrels, lantern on a barrel
    c.put(8, 1, 2, "chest", facing="south", type="single", waterlogged=False)
    c.put(7, 1, 2, "barrel", facing="up", open=False)
    c.put(9, 1, 2, "barrel", facing="up", open=False)
    c.put(9, 2, 2, "lantern", hanging=False, waterlogged=False)

    # ---- front: 3x4 portal x7..9 y1..4 in stone jambs, timber lintel and gable, folded gate leaves
    for x in (6, 10):
        for y in range(1, 6):
            c.put(x, y, 11, "stone_bricks" if (x + y) % 2 else "polished_andesite")
        for y in (1, 2, 3):  # projecting lantern pillars
            c.put(x, y, 12, "stone_bricks" if y > 1 else "chiseled_stone_bricks")
        c.put(x, 4, 12, "lantern", hanging=False, waterlogged=False)
    for x in range(6, 11):
        c.put(x, 5, 11, "dark_oak_log", axis="x")
    for x in (4, 5, 11, 12):
        for y in range(1, 5):
            trap(c, x, y, 12, "dark_oak", "south", half="bottom" if y % 2 else "top")
    # lean-to front walls (pen gables) and the rear wall continue up to the roof line; small front windows
    for z in (1, 11):
        for x in list(range(2, 6)) + list(range(11, 16)):
            i = min(x, W - 1 - x)
            if i < 1:
                continue
            ly, half = LEAN[i]
            top = ly if half == "top" else ly - 1
            for y in range(5, top + 1):
                c.put(x, y, z, "spruce_planks")
        for x in (3, 4, 12, 13):
            c.put(x, 3, z, "dark_oak_fence")
    # nave gables z=1 (rear, closed) and z=11 (above the lintel): frame, spruce, vents
    for z in (1, 11):
        for x in range(6, 11):
            for y in range(6 if z == 11 else 1, NAVE[x]):
                if z == 1 and y <= 2:
                    c.put(x, y, z, wall_stone(x, y, z) if y == 2 else base_course(x, y, z))
                elif x in (6, 10) or (x == 8 and y >= 6):
                    c.put(x, y, z, "dark_oak_log", axis="y")
                elif y == 8 and x in (7, 9):
                    c.put(x, y, z, "dark_oak_log", axis="x")
                else:
                    c.put(x, y, z, "spruce_planks")
        for x in (7, 9):
            c.put(x, 9, z, "dark_oak_fence")
        for x in (5, 11):  # close the slot under the nave eave at the gable planes
            c.put(x, 8, z, "spruce_planks")
    c.put(8, 3, 1, "dark_oak_fence")  # rear window over the store
    c.put(8, 7, 12, "white_wall_banner", facing="south")

    # ---- roofs: lean-to slabs (spruce, dark-oak verges) and the nave gable (spruce stairs, dark-oak barge, log ridge)
    for x in range(0, 6):
        for xx in (x, W - 1 - x):
            ly, half = LEAN[x]
            for z in range(D):
                gable = z in (1, 11)
                if gable and half == "top" and 1 <= xx <= 15:
                    c.put(xx, ly, z, "spruce_planks")
                else:
                    slab(c, xx, ly, z, "dark_oak" if z in (0, D - 1) else "spruce", half)
    nave = {(x, z): y for x, y in NAVE.items() for z in range(D)}
    hroof(c, nave, lambda x, z: "dark_oak" if z in (0, D - 1) else "spruce",
          lambda x, z: ("dark_oak_log", {"axis": "z"}))

    # ---- outside the portal: hay and barrels under the verges, clear of the 3-wide approach
    c.put(2, 1, 12, "hay_block", axis="y"); c.put(3, 1, 12, "hay_block", axis="x"); c.put(2, 2, 12, "hay_block", axis="z")
    c.put(13, 1, 12, "barrel", facing="up", open=False); c.put(14, 1, 12, "barrel", facing="south", open=False)
    c.put(14, 2, 12, "barrel", facing="up", open=False)
    return c


# ---------------------------------------------------------------------------------------------- registry
# door: entrance column on the street face (+z); walls: boxes (x0, x1, z0, z1) of the walled body - anything outside
# stands on the open apron. buttons/iron doors and the ravager spawn points are checked by checks.py.
BUILDINGS = {
    "prison": dict(module="M-prison", placement="F09", design=f09, size=(P_W, P_H, P_D),
                   door=(5, 12), entrances={"front_door_south": (5, 13)}, walls=[(1, 9, 0, 11)]),
    "stable": dict(module="M-stable", placement="F10", design=f10, size=(S_W, S_H, S_D),
                   door=(8, 12), entrances={"portal_south": (8, 13)}, walls=[(1, 15, 1, 11)],
                   ravager_spawns=RAVAGER_SPAWNS),
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
