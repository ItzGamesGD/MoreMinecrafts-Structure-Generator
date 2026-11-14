"""ST-03 batch 7: F01 commander manor (M-manor 17x27x15, the Q63 size).

Contract: tools/seam01/data/st03_placements.json - F01 x=48..64, z=11..25, local_turns 0. The module size is 17x27x15
since owner decision Q63 (it was 17x23x15); that one module entry is the only change to the placement table. Street face
+z (south): the central street runs south from F01 to the gate; the W-N wall is 6 blocks north.

Design source: owner ledger Q60-Q73 (Beta repo, docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md).
  Q60 fortified manor, stone lower storey, dark-oak / spruce upper storeys, high gable, banners, lanterns
  Q61 1F hall / guards / supplies; 2F command / war room; 3F private quarters; small lookout attic
  Q62 continuous side staircase 1F-3F with landings, 2-wide flights, ladder to the attic
  Q63 double-height central hall, hanging chandelier, 2F gallery; 17x27x15
  Q64 U-shaped 2F gallery overlooking the hall; rear war room with map / war table
  Q65 large 3F bedroom, open study, chest + armor stand, attic ladder
  Q66 symmetric gable (jettied on the street side), central lookout window with a raised platform, attic lantern /
      chest, timber beams
  Q67 2-wide dark-oak front doors, thick stone pillars, projecting timber porch, lanterns, two banners, tall hall windows
  Q68 tall paired hall windows, narrow barred 1F side windows, 2F gallery windows, wider shuttered 3F windows
  Q69 two-tier chandelier (rings ~3 and ~5 across, here 4 and 6 on the even grid), 8 lanterns, gallery clearance
  Q70 symmetric stone floor motif with a central accent, stone-bottom / timber-top columns, banners, lanterns, ties
  Q71/Q72 commander initial position in the rear 2F war room; 1F/2F/attic ordinary containers, 3F rare-reward chest

Body x=0..15 (16 wide, symmetric about x=7.5 so the 2-wide door is centred), z=0 (rear) .. 12 (front); the porch
projects to z=14; the chimney stands at x=16. Floors: 1F y0, 2F y6, 3F y12, attic y18; eaves y19, ridge y26.
Hall void x5..10 z6..11 open y1..11. Stair (east strip): flight 1 x11..12 rises north z11->z6 to the 2F landing
z4..5; flight 2 x13..14 rises south z6->z11 to the 3F (opening x13..14 z8..10); six half-block steps a storey. Attic by ladder.

Entities cannot be written by this exporter (schem.py rejects them), so the armor stand and the commander are recorded
as positions in BUILDINGS, like the F10 ravager positions. No mob, loot, reward roll or AI is authored.

  PYTHONPATH=. python experiments/st03-batch7-commander-manor/build.py
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


B6 = _load("batch6_build", ROOT.parent / "st03-batch6-prison-stable" / "build.py")
Cells, floor_stone, noise, path_stone = B6.Cells, B6.floor_stone, B6.noise, B6.path_stone
stairs, trap, door, bed, hroof, base_course = B6.stairs, B6.trap, B6.door, B6.bed, B6.hroof, B6.base_course
wall_stone, slab = B6.wall_stone, B6.slab

W, H, D = 17, 27, 15
F2, F3, AT, EAVE = 6, 12, 18, 19   # floor levels (block y of the floor), eave course
VOID = (5, 10, 6, 11)               # hall void x0, x1, z0, z1 (open y1..11)
COMMANDER = (7.5, 7.0, 1.5)         # entity centre, local: behind the war table, facing the hall
ARMOR_STAND = (12.5, 13.0, 2.5)     # entity position, local: 3F bedroom
RARE_CHEST = (5, 13, 1)


def roof_y(x):
    return EAVE + min(x, 15 - x)


def f01():
    c = Cells((W, H, D))
    # ------------------------------------------------------------------ ground and floors
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, path_stone(x, z))
    for x in range(1, 15):
        for z in range(1, 12):
            c.put(x, 0, z, floor_stone(x, z))
    x0, x1, z0, z1 = VOID
    for x in range(x0, x1 + 1):  # symmetric hall motif: andesite border and cross, chiselled centre and corners
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            cross = x in (7, 8) or z in (8, 9)
            if x in (7, 8) and z in (8, 9):
                b = "chiseled_stone_bricks"
            elif (x, z) in ((6, 7), (9, 7), (6, 10), (9, 10)):
                b = "chiseled_stone_bricks"
            elif edge or cross:
                b = "polished_andesite"
            else:
                b = "stone_bricks"
            c.put(x, 0, z, b)
    for z in range(1, 6):  # the runner continues under the mezzanine to the rear wall
        for x in (7, 8):
            c.put(x, 0, z, "polished_andesite")
    for x in range(1, 15):  # 2F floor (dark oak), 3F floor and attic floor (spruce); openings cut below
        for z in range(1, 12):
            c.put(x, F2, z, "dark_oak_planks")
            c.put(x, F3, z, "spruce_planks")
            c.put(x, AT, z, "spruce_planks")
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            del c[(x, F2, z)]
    for z in range(6, 12):  # well over flight 1 (x11..12)
        for x in (11, 12):
            del c[(x, F2, z)]
    for z in (8, 9, 10):  # 3F opening over the top of flight 2 (z8 too: the head passes it while stepping up)
        for x in (13, 14):
            del c[(x, F3, z)]
    del c[(3, AT, 6)]  # attic hatch over the ladder

    # ------------------------------------------------------------------ 1F stone walls, upper timber frame
    def stone_at(x, y, z):
        corner = x in (0, 15) and z in (0, 12)
        if corner:
            return "polished_andesite" if y % 2 else "stone_bricks"
        return base_course(x, y, z) if y == 1 else wall_stone(x, y, z)

    for y in range(1, F2):
        for z in range(0, 13):
            for x in (0, 15):
                c.put(x, y, z, stone_at(x, y, z))
        for x in range(1, 15):
            for z in (0, 12):
                c.put(x, y, z, stone_at(x, y, z))
    posts_z, posts_x = (0, 4, 8, 12), (0, 4, 11, 15)
    for band in (F2, F3, AT):  # dark-oak girts at every floor
        for z in range(0, 13):
            for x in (0, 15):
                c.put(x, band, z, "dark_oak_log", axis="z")
        for x in range(1, 15):
            for z in (0, 12):
                c.put(x, band, z, "dark_oak_log", axis="x")
    for lo, hi in ((F2 + 1, F3 - 1), (F3 + 1, AT - 1)):
        for y in range(lo, hi + 1):
            for z in range(0, 13):
                for x in (0, 15):
                    c.put(x, y, z, "dark_oak_log" if z in posts_z else "spruce_planks", **({"axis": "y"} if z in posts_z else {}))
            for x in range(1, 15):
                for z in (0, 12):
                    c.put(x, y, z, "dark_oak_log" if x in posts_x else "spruce_planks", **({"axis": "y"} if x in posts_x else {}))

    # ------------------------------------------------------------------ windows
    def pane(x, y, z):
        c.put(x, y, z, "glass_pane")

    for x in (0, 15):  # sides: narrow barred 1F slits, 2F gallery windows, wider shuttered 3F windows
        f = "west" if x == 0 else "east"
        ox = -1 if x == 0 else 1
        for z in (3, 9):
            for y in (2, 3, 4):
                c.put(x, y, z, "iron_bars")
        for z in (2, 3, 6, 7, 9, 10):
            for y in (8, 9, 10):
                pane(x, y, z)
        for z in (6, 7):
            for y in (14, 15, 16):
                pane(x, y, z)
        for zz in ((2, 3), (9, 10)):
            for z in zz:
                for y in (14, 15, 16):
                    pane(x, y, z)
            if 0 <= x + ox < W:
                for y in (14, 15, 16):
                    trap(c, x + ox, y, zz[0] - 1, "spruce", f)
                    trap(c, x + ox, y, zz[1] + 1, "spruce", f)
    for x in (3, 12):  # rear
        for y in (2, 3, 4):
            c.put(x, y, 0, "iron_bars")
    for x in (2, 3, 12, 13):
        for y in (8, 9, 10):
            pane(x, y, 0)
        for y in (14, 15, 16):
            pane(x, y, 0)
    for x in (2, 13):  # front 1F side bays: barred
        for y in (2, 3, 4):
            c.put(x, y, 12, "iron_bars")
    for x in (5, 6, 9, 10):  # tall paired hall windows over the porch
        for y in range(8, 12):
            pane(x, y, 12)
    for x in (2, 3, 12, 13):  # 2F gallery windows (front)
        for y in (8, 9, 10):
            pane(x, y, 12)
    for xs, l, r in (((2, 3), 1, 4), ((12, 13), 11, 14)):  # 3F front: wide windows with shutters
        for x in xs:
            for y in (14, 15, 16):
                pane(x, y, 12)
        for y in (14, 15, 16):
            trap(c, l, y, 13, "spruce", "south"); trap(c, r, y, 13, "spruce", "south")
    for x in (7, 8):
        for y in (14, 15, 16):
            pane(x, y, 12)

    # ------------------------------------------------------------------ roof, gables, lookout
    hmap = {(x, z): roof_y(x) for x in range(0, 16) for z in range(0, 15)}
    hroof(c, hmap, lambda x, z: "dark_oak" if z in (0, 14) else "deepslate_tile",
          lambda x, z: ("deepslate_tiles", {}))
    # the street gable is jettied one block (z=13) on a sill beam and brackets; the rear gable stays flush (z=0)
    for x in range(0, 16):
        c.put(x, AT, 13, "dark_oak_log", axis="x")
    for x in (0, 4, 11, 15):  # brackets under the jettied gable and under the 3F girt on the street face
        stairs(c, x, AT - 1, 13, "dark_oak", "north", half="top")
        stairs(c, x, F3 - 1, 13, "dark_oak", "north", half="top")
    for z in (0, 13):
        for x in range(1, 15):
            for y in range(AT + 1, roof_y(x)):
                if x in (4, 11) or (x in (7, 8) and y <= AT + 2):
                    c.put(x, y, z, "dark_oak_log", axis="y")
                elif y == 22 and 4 < x < 11:
                    c.put(x, y, z, "dark_oak_log", axis="x")
                else:
                    c.put(x, y, z, "spruce_planks")
    for x in (7, 8):  # central lookout window in the jettied gable, and a small rear window
        pane(x, 23, 13); pane(x, 24, 13)
        pane(x, 21, 0)
        stairs(c, x, 22, 14, "dark_oak", "north", half="top")  # sill
    for x in (6, 9):
        trap(c, x, 23, 14, "spruce", "south"); trap(c, x, 24, 14, "spruce", "south")
    # attic: tie beams (y22) with king posts, a raised lookout platform with steps so the eye meets the window
    for z in (2, 6):
        for x in range(4, 12):
            c.put(x, 22, z, "dark_oak_log", axis="x")
        for x in (7, 8):
            for y in (23, 24, 25):
                c.put(x, y, z, "dark_oak_log", axis="y")
    for x in range(6, 10):
        for z in (10, 11, 12):
            c.put(x, 21, z, "spruce_planks")
            for y in (19, 20):
                c.put(x, y, z, "dark_oak_planks" if x in (6, 9) else "spruce_planks")
    for x in (7, 8):
        stairs(c, x, 19, 8, "spruce", "south"); stairs(c, x, 20, 9, "spruce", "south"); c.put(x, 19, 9, "spruce_planks")
    for z in (10, 11, 12):
        c.put(6, 22, z, "dark_oak_fence"); c.put(9, 22, z, "dark_oak_fence")
    c.put(7, 25, 4, "lantern", hanging=True, waterlogged=False)
    c.put(5, 19, 2, "chest", facing="south", type="single", waterlogged=False)
    c.put(10, 19, 2, "barrel", facing="up", open=False)

    # ------------------------------------------------------------------ chimney (east, x=16)
    for y in range(0, 23):
        for z in (2, 3, 4):
            if y <= 19 or z == 3:
                c.put(16, y, z, "stone_bricks" if (y + z) % 3 else "cobblestone")
    slab(c, 16, 23, 3, "stone_brick", "bottom")
    for y in (1, 2, 3, 4, 5):  # chimney breast inside the 1F east room with a stove
        for z in (2, 3, 4):
            c.put(14, y, z, "stone_bricks" if z != 3 or y > 2 else "polished_andesite")
    c.put(14, 1, 3, "furnace", facing="west", lit=False)
    c.put(14, 2, 3, "furnace", facing="west", lit=False)

    # ------------------------------------------------------------------ street face: door, porch, banners, lanterns
    door(c, 7, 12, "dark_oak", "north", "left")
    door(c, 8, 12, "dark_oak", "north", "right")
    for x in (6, 9):
        for y in (1, 2, 3):
            c.put(x, y, 12, "chiseled_stone_bricks" if y == 1 else "stone_bricks")
    stairs(c, 6, 4, 12, "stone_brick", "east", half="top"); stairs(c, 9, 4, 12, "stone_brick", "west", half="top")
    c.put(7, 3, 12, "stone_bricks"); c.put(8, 3, 12, "stone_bricks")
    c.put(7, 4, 12, "chiseled_stone_bricks"); c.put(8, 4, 12, "chiseled_stone_bricks")
    for x in range(5, 11):
        for z in (13, 14):
            c.put(x, 0, z, "polished_andesite" if x in (5, 10) or z == 14 else "stone_bricks")
    for x in (5, 10):  # thick stone pillars (1x2) with chiselled base and andesite capital
        for z in (13, 14):
            c.put(x, 1, z, "chiseled_stone_bricks")
            c.put(x, 2, z, "stone_bricks"); c.put(x, 3, z, "stone_bricks")
            c.put(x, 4, z, "polished_andesite")
    for x in range(5, 11):  # timber porch: beams at y5, shed roof sloping to the street
        c.put(x, 5, 14, "dark_oak_log", axis="x")
    for z in (13,):
        for x in (5, 10):
            c.put(x, 5, z, "dark_oak_log", axis="z")
    for x in range(4, 12):
        stairs(c, x, 6, 14, "dark_oak", "north")
        stairs(c, x, 7, 13, "dark_oak", "north")
        if x in (4, 11):
            c.put(x, 6, 13, "dark_oak_planks")
    for x in (4, 11):
        stairs(c, x, 5, 14, "dark_oak", "west" if x == 4 else "east", half="top")
    for x in (6, 9):
        c.put(x, 6, 13, "lantern", hanging=True, waterlogged=False)
    c.put(4, 4, 13, "white_wall_banner", facing="south")
    c.put(11, 4, 13, "white_wall_banner", facing="south")
    for x in (1, 14):  # lantern posts at the corners of the forecourt
        c.put(x, 1, 14, "stone_brick_wall"); c.put(x, 2, 14, "stone_brick_wall")
        c.put(x, 3, 14, "lantern", hanging=False, waterlogged=False)

    # ------------------------------------------------------------------ hall: columns, gallery rails, ceiling frame
    for (x, z) in ((4, 5), (4, 8), (4, 11), (11, 5)):  # stone-bottom / timber-top columns
        c.put(x, 1, z, "chiseled_stone_bricks"); c.put(x, 2, z, "stone_bricks")
        for y in (3, 4, 5):
            c.put(x, y, z, "dark_oak_log", axis="y")
    for z in range(5, 12):  # gallery rim beams (part of the 2F floor)
        c.put(4, F2, z, "dark_oak_log", axis="z")
    for x in range(4, 12):
        c.put(x, F2, 5, "dark_oak_log", axis="x")
    for z in range(6, 12):
        c.put(4, F2 + 1, z, "dark_oak_fence")
    for x in range(5, 11):
        c.put(x, F2 + 1, 5, "dark_oak_fence")
    c.put(4, F2 + 1, 5, "dark_oak_fence")
    for z in range(6, 12):  # ceiling frame around the void (y11)
        c.put(5, 11, z, "dark_oak_log", axis="z"); c.put(10, 11, z, "dark_oak_log", axis="z")
    for x in range(6, 10):
        c.put(x, 11, 6, "dark_oak_log", axis="x"); c.put(x, 11, 11, "dark_oak_log", axis="x")
    # two-tier chandelier: small square ring (4 across) y10 hung from the ceiling, large stepped ring (6 across) y8
    small = [(x, z) for x in range(6, 10) for z in range(7, 11) if x in (6, 9) or z in (7, 10)]
    big = ([(5, z) for z in range(7, 11)] + [(10, z) for z in range(7, 11)] + [(x, 6) for x in range(6, 10)]
           + [(x, 11) for x in range(6, 10)] + [(6, 7), (9, 7), (6, 10), (9, 10)])
    for x, z in small:
        c.put(x, 10, z, "dark_oak_fence")
    for x, z in big:
        c.put(x, 8, z, "dark_oak_fence")
    for x, z in ((6, 7), (9, 7), (6, 10), (9, 10)):  # one chain line: ceiling - small ring - big ring
        c.put(x, 11, z, "iron_chain", axis="y"); c.put(x, 9, z, "iron_chain", axis="y")
    for x, z in ((5, 8), (10, 9), (8, 6), (7, 11), (8, 7), (9, 9), (7, 10), (6, 8)):
        c.put(x, 7 if (x, z) in ((5, 8), (10, 9), (8, 6), (7, 11)) else 9, z, "lantern", hanging=True, waterlogged=False)
    # banners and lanterns in the hall
    for x in (6, 9):
        c.put(x, 4, 1, "white_wall_banner", facing="south")
    for x, z in ((2, 8), (2, 3), (12, 3), (7, 3)):
        c.put(x, 5, z, "lantern", hanging=True, waterlogged=False)

    # ------------------------------------------------------------------ staircase (east strip)
    # six steps per 6-block storey, so every rise is half a block (no full-block step at a landing)
    f1 = {z: 1 + i for i, z in enumerate((11, 10, 9, 8, 7, 6))}   # flight 1: x11..12, rising north to the landing
    f2 = {z: F2 + 1 + i for i, z in enumerate((6, 7, 8, 9, 10, 11))}  # flight 2: x13..14, rising south to the 3F
    for z, k in f1.items():
        for x in (11, 12):
            stairs(c, x, k, z, "dark_oak", "north")
            for y in range(1, k):  # flight 1 stands on a stone base inside the stone storey
                c.put(x, y, z, "stone_bricks" if (y + z) % 4 else "polished_andesite")
    for z, m in f2.items():
        for x in (13, 14):
            stairs(c, x, m, z, "spruce", "south")
            for y in range(F2 + 1, m):
                c.put(x, y, z, "dark_oak_planks")
    for z in range(6, 12):  # timber screen / balustrade between the flights, above flight-1 head room (k+3)
        k, m = f1[z], f2[z]
        for y in range(k + 3, m + 1):
            c.put(12, y, z, "dark_oak_planks")
        if m + 1 >= k + 3 and z < 11:  # a rail only where there is a drop to guard; z=11 is the 3F exit
            c.put(12, m + 1, z, "dark_oak_fence")
    for x in (13, 14):  # 3F railing around the stair opening
        c.put(x, F3 + 1, 7, "dark_oak_fence")
    for z in (8, 9, 10):
        c.put(12, F3 + 1, z, "dark_oak_fence")

    # ------------------------------------------------------------------ 1F: guards and supplies
    for z in (7, 10):  # west guard bay under the gallery: weapon racks, supplies
        c.put(1, 1, z, "barrel", facing="east", open=False)
    c.put(1, 2, 7, "barrel", facing="up", open=False)
    c.put(1, 1, 8, "chest", facing="east", type="single", waterlogged=False)
    c.put(1, 1, 9, "fletching_table")
    for z in (8, 9):
        c.put(2, 1, z, "spruce_slab", type="top", waterlogged=False)  # guard table
    stairs(c, 3, 1, 8, "spruce", "west"); stairs(c, 3, 1, 9, "spruce", "west")
    for x in (1, 2):  # rear supplies
        c.put(x, 1, 1, "barrel", facing="up", open=False)
    c.put(1, 2, 1, "barrel", facing="up", open=False)
    c.put(3, 1, 1, "chest", facing="south", type="single", waterlogged=False)
    c.put(12, 1, 1, "chest", facing="south", type="single", waterlogged=False)
    c.put(13, 1, 1, "barrel", facing="up", open=False)
    c.put(1, 1, 4, "smithing_table")
    c.put(1, 1, 3, "grindstone", face="floor", facing="east")

    # ------------------------------------------------------------------ 2F: war room (rear mezzanine), west gallery
    for x in range(6, 10):  # war table with a carpet map
        for z in (2, 3):
            c.put(x, 7, z, "dark_oak_planks")
    for (x, z), col in {(6, 2): "green", (7, 2): "lime", (8, 2): "green", (9, 2): "brown", (6, 3): "light_blue",
                        (7, 3): "green", (8, 3): "red", (9, 3): "lime"}.items():
        c.put(x, 8, z, f"{col}_carpet")
    for z in (2, 3):
        stairs(c, 5, 7, z, "dark_oak", "west"); stairs(c, 10, 7, z, "dark_oak", "east")
    c.put(13, 7, 1, "cartography_table")  # in the corner, off the walking line to the landing
    mural = {(6, 9): "green_terracotta", (7, 9): "brown_terracotta", (8, 9): "green_terracotta",
             (9, 9): "light_blue_terracotta", (6, 10): "light_blue_terracotta", (7, 10): "green_terracotta",
             (8, 10): "red_terracotta", (9, 10): "brown_terracotta"}
    for (x, y), b in mural.items():
        c.put(x, y, 1, b)
    for x in (5, 10):
        for y in (9, 10):
            c.put(x, y, 1, "dark_oak_log", axis="y")
    for x in range(5, 11):
        c.put(x, 11, 1, "dark_oak_log", axis="x")
    c.put(4, 10, 1, "white_wall_banner", facing="south"); c.put(11, 10, 1, "white_wall_banner", facing="south")  # on posts
    c.put(1, 7, 1, "chest", facing="east", type="single", waterlogged=False)  # military containers
    c.put(1, 7, 2, "barrel", facing="east", open=False); c.put(1, 8, 2, "barrel", facing="up", open=False)
    c.put(14, 7, 1, "barrel", facing="up", open=False); c.put(14, 7, 2, "chest", facing="west", type="single", waterlogged=False)
    c.put(1, 7, 8, "barrel", facing="east", open=False); c.put(1, 7, 10, "chest", facing="east", type="single", waterlogged=False)
    c.put(1, 7, 9, "smithing_table")
    for z in (8, 11):  # on the post (z=8) and the wall between the windows (z=11)
        c.put(1, 9, z, "white_wall_banner", facing="east")
    for x, z in ((7, 3), (2, 9), (13, 2)):
        c.put(x, 11, z, "lantern", hanging=True, waterlogged=False)

    # ------------------------------------------------------------------ 3F: bedroom (rear) and open study (front)
    for x in range(1, 15):  # partition z=5 with a 2-wide opening, ladder to the attic on its south face
        for y in range(F3 + 1, AT):
            if x in (7, 8) and y <= F3 + 3:
                continue
            c.put(x, y, 5, "dark_oak_log" if x in (1, 4, 11, 14) else "spruce_planks",
                  **({"axis": "y"} if x in (1, 4, 11, 14) else {}))
    for y in range(F3 + 1, AT + 1):
        c.put(3, y, 6, "ladder", facing="south", waterlogged=False)
    bed(c, 7, F3 + 1, 1, "red", "north"); bed(c, 8, F3 + 1, 1, "red", "north")
    for x in (6, 9):
        c.put(x, F3 + 1, 1, "dark_oak_planks")
        c.put(x, F3 + 2, 1, "lantern", hanging=False, waterlogged=False)
    for x in range(6, 10):
        for z in (3, 4):
            c.put(x, F3 + 1, z, "red_carpet")
    rx, ry, rz = RARE_CHEST
    c.put(rx, ry, rz, "chest", facing="south", type="single", waterlogged=False)
    for z in (1, 2, 3, 4):
        c.put(1, F3 + 1, z, "bookshelf")
        if z in (1, 2):
            c.put(1, F3 + 2, z, "bookshelf")
    c.put(14, F3 + 3, 1, "white_wall_banner", facing="west")
    for z in range(7, 12):  # study: bookshelves, desk, map table, candles
        c.put(1, F3 + 1, z, "bookshelf"); c.put(1, F3 + 2, z, "bookshelf")
    for x in (5, 6):
        c.put(x, F3 + 1, 9, "dark_oak_planks")
    c.put(5, F3 + 2, 9, "candle", candles=3, lit=False, waterlogged=False)
    stairs(c, 5, F3 + 1, 10, "dark_oak", "north"); stairs(c, 6, F3 + 1, 10, "dark_oak", "north")
    c.put(9, F3 + 1, 8, "cartography_table")
    c.put(10, F3 + 1, 8, "dark_oak_planks"); c.put(10, F3 + 2, 8, "lantern", hanging=False, waterlogged=False)
    for x, z in ((7, 3), (7, 9)):
        c.put(x, AT - 1, z, "lantern", hanging=True, waterlogged=False)
    return c


# ---------------------------------------------------------------------------------------------- registry
# door: entrance column on the street face (+z, the porch edge z=14); walls: boxes (x0, x1, z0, z1) of the walled body.
BUILDINGS = {
    "manor": dict(module="M-manor", placement="F01", design=f01, size=(W, H, D),
                  door=(7, 14), entrances={"porch_south": (7, 15), "porch_south_b": (8, 15)},
                  walls=[(0, 15, 0, 12)], commander_spawn=COMMANDER, armor_stand=ARMOR_STAND,
                  rare_reward_chest=RARE_CHEST),
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
