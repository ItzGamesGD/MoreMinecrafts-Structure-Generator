"""ST-03 batch 9: corner tower MT (13x24x13, st03_tower) and south gatehouse MG (24x20x12, st03_gatehouse).

Contract kept (tools/seam01/data/st03_placements.json, untouched): sizes above (x, y, z), air=include, y=0 at grade.
  MT -> T-NW x0..12 z0..12 (local_turns 0), T-NE x99..111 z0..12 (1), T-SE x99..111 z99..111 (2), T-SW x0..12 z99..111 (3)
        Every turn maps local x=0 and z=0 onto the two OUTER faces of the corner; the walls meet the tower at the local
        x=12 face (rows z0..4, the wall that continues along local x) and the local z=12 face (columns x0..4). The rest of
        those two faces looks into the compound.
  MG -> GATE x44..67 z100..111 (local_turns 0): local z=11 is the exterior (south) face, z=0 the compound side;
        W-SW meets local x=0 and W-SE local x=23, both over z7..11 (the wall is 5 deep, z107..111).

Design source: owner ledger (Beta repo, docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md)
  Q81 A  four independently accessible corner towers, ladder from the ground to the lookout, no wall-top patrol route
  Q82 B  stone crenellations / arrow openings, lanterns, banners, timber details, no shooting mechanic
  Q83 A  ground floor to top by ONE direct ladder, no intermediate floor; same internal layout in all four towers
  Q84 B  stone tower, dark-oak pitched roof, open observation gaps below the roof, timber supports, hanging lanterns,
         external banners, inside the module
  Q85 B  same dimensions / height / roof / ladder for all four. The per-placement weathering and accent variation is NOT
         authored: one NBT serves all four placements (see README, owner decision D-2)
  Q86 B  massive dark-oak double-leaf gate appearance, timber / iron bracing, stone and andesite pillars, upper stone
         gatehouse with crenellations, banners, lanterns; PERMANENTLY OPEN, STATIC, NONFUNCTIONAL (no door, no
         redstone, no moving part): the leaves are solid blocks fixed against the passage sides
  Q87 B  small accessible observation room above the gate, own internal side ladder, openings toward the exterior
         approach and the interior checkpoint, battlements, timber supports, lanterns, banners, one ordinary chest,
         one weapon rack; no continuous wall walkway
  Q80 B  inside the gate: small checkpoint / muster space with timber barriers, weapon racks, banners, lanterns and
         stone paving toward the central road (the part that lies inside the GATE rectangle, z100..103)
  Q88 B  exterior approach: banners and lanterns flanking the gate, mixed cobble / andesite / stone-brick paving,
         barricades, racks, barrels, timber toward the sides, a broad straight central passage - kept INSIDE the
         112x112 box (Q88: no expansion beyond it), i.e. in a forecourt recessed between the two front turrets
  Q89 B  footing course under every column; below-grade fill is a placement step (checks.py, test terrain only)
  owner stone principle: stone / andesite / cobble / stone bricks / mossy / cracked mixed naturally, clean edges

All containers empty (block-entity allow-list); loot is a runtime decision. No mobs, spawners or mechanics authored.

  PYTHONPATH=. python experiments/st03-batch9-towers-gate/build.py
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


B8 = _load("batch8_build", ROOT.parent / "st03-batch8-perimeter-walls" / "build.py")
B3 = _load("batch3_build", ROOT.parent / "st03-batch3-military" / "build.py")
Cells, noise, stairs, foot = B8.Cells, B8.noise, B8.stairs, B8.foot
path_stone = B3.path_stone


def masonry(x, y, z, edge=False):
    """Tower / gatehouse ashlar: clean stone bricks on edges and bands, weathering in staggered patches elsewhere."""
    if edge:
        return "cracked_stone_bricks" if noise(x, z, 17, y + 5) == 0 else "stone_bricks"
    patch = noise((x + z + 2 * (y // 3)) // 4, y // 3, 9, 63)
    hit = noise(x + z, y, 3, 29) != 0
    if patch == 0 and hit:
        return "cracked_stone_bricks"
    if patch == 1 and hit and y <= 6:
        return "mossy_stone_bricks"
    if patch == 2 and hit and y <= 4:
        return ("cobblestone", "andesite", "mossy_cobblestone")[noise(x, y, 3, z + 7)]
    if patch == 3 and noise(x, y, 4, z + 11) == 0:
        return "andesite" if y <= 6 else "cracked_stone_bricks"
    return "stone_bricks"


# ================================================================================================ MT corner tower
TW, TH = 13, 24
LOOK = 14  # lookout floor (feet at 15)
EAVE = 18  # roof ring 0
DOOR_Z = 8  # door on the compound side of the local x=12 face
LADDER = (3, 5)  # ladder column, attached to the west shell (x=2), facing east
POSTS = (1, 6, 11)


def ring(x, z, n=TW):
    return min(x, z, n - 1 - x, n - 1 - z)


def exterior_face(x, z):
    """Cells of the outer layer on the two exterior faces (x=0 or z=0), and their coordinate along the face."""
    if x == 0:
        return z
    if z == 0:
        return x
    return None


def inward(x, z, k, n=TW):
    """Facing of a roof stair on ring k, ascending toward the centre, with the vanilla outer-corner shape."""
    lo, hi = k, n - 1 - k
    if (x, z) == (lo, lo):
        return "south", "outer_left"
    if (x, z) == (hi, lo):
        return "south", "outer_right"
    if (x, z) == (hi, hi):
        return "north", "outer_left"
    if (x, z) == (lo, hi):
        return "north", "outer_right"
    if z == lo:
        return "south", "straight"
    if z == hi:
        return "north", "straight"
    if x == lo:
        return "east", "straight"
    return "west", "straight"


def tower():
    c = Cells((TW, TH, TW))
    for x in range(TW):
        for z in range(TW):
            r = ring(x, z)
            c.put(x, 0, z, foot(x, 0, z) if r <= 2 else path_stone(x, z))
            if r >= 3:
                continue
            u = exterior_face(x, z)
            panel = r == 0 and u is not None and 3 <= u <= 9
            # compound faces (x=12 / z=12): a smaller recessed panel clear of the wall joints (rows / columns 0..4)
            cu = z if x == TW - 1 else x if z == TW - 1 else None
            cpanel = r == 0 and u is None and cu is not None and 6 <= cu <= 9
            for y in range(1, LOOK):
                if panel and y >= 3:
                    continue  # recessed panel between the corner quoins
                if cpanel and 5 <= y <= LOOK - 2:
                    continue
                edge = r == 0 and (u is None or u <= 2 or u >= 10) or y == LOOK - 1
                c.put(x, y, z, masonry(x, y, z, edge=edge))
            if panel:
                c.put(x, 1, z, foot(x, 1, z))
                c.put(x, 2, z, foot(x, 2, z))
                f = "east" if x == 0 else "south"
                stairs(c, x, 3, z, "stone_brick", f)  # weathering on top of the projecting plinth
                stairs(c, x, LOOK - 1, z, "stone_brick", f, half="top")  # corbel band under the sill
    # arrow slits through the shell in the exterior panels (blind at the inner face: 2 thick, open both cells)
    for u, ys in ((6, (5, 6)), (4, (10, 11)), (8, (10, 11))):
        for y in ys:
            for d in (1, 2):
                del c[(d, y, u)]
                del c[(u, y, d)]
    # door on the compound side (x=12 face): doorway recess x11..12 (3 high), dark-oak door in the inner face x10
    for y in (1, 2, 3):
        for x in (11, 12):
            del c[(x, y, DOOR_Z)]
    B8.Cells.put(c, 10, 1, DOOR_Z, "dark_oak_door", facing="west", half="lower", hinge="left", open=False, powered=False)
    B8.Cells.put(c, 10, 2, DOOR_Z, "dark_oak_door", facing="west", half="upper", hinge="left", open=False, powered=False)
    c.put(10, 3, DOOR_Z, "dark_oak_log", axis="z")  # timber lintel
    c.put(12, 3, DOOR_Z, "lantern", hanging=True, waterlogged=False)  # under the recess head (y4), above head height
    # direct ladder, ground to lookout (Q83): y1..LOOK, through a hole in the lookout floor
    lx, lz = LADDER
    for y in range(1, LOOK + 1):
        c.put(lx, y, lz, "ladder", facing="east", waterlogged=False)
    # shaft light and stores
    c.put(6, LOOK - 1, 6, "iron_chain", axis="y")
    c.put(6, LOOK - 2, 6, "lantern", hanging=True, waterlogged=False)
    c.put(9, 1, 3, "barrel", facing="up", open=False)
    c.put(9, 2, 3, "lantern", hanging=False, waterlogged=False)
    c.put(8, 1, 3, "barrel", facing="up", open=False)
    c.put(9, 1, 4, "spruce_log", axis="z")
    c.put(9, 1, 5, "spruce_log", axis="z")
    # lookout floor
    for x in range(TW):
        for z in range(TW):
            r = ring(x, z)
            if (x, z) == LADDER:
                continue
            if r == 0:
                c.put(x, LOOK, z, "stone_brick_slab", type="bottom", waterlogged=False)
            elif r <= 2:
                c.put(x, LOOK, z, masonry(x, LOOK, z, edge=True))
            else:
                c.put(x, LOOK, z, "spruce_planks")
    # observation stage: posts, breastwork, knee braces, wall plate
    for x in range(1, 12):
        for z in range(1, 12):
            if ring(x, z) != 1:
                continue
            post = x in POSTS and z in POSTS
            if post:
                for y in range(LOOK + 1, EAVE):
                    c.put(x, y, z, "dark_oak_log", axis="y")
            else:
                c.put(x, LOOK + 1, z, "stone_bricks" if noise(x, z, 5, 3) else "mossy_stone_bricks")
            along = "x" if z in (1, 11) else "z"
            c.put(x, EAVE, z, "dark_oak_log", axis="y" if post else along)
    for a in (1, 11):
        for p in POSTS:
            for d in (-1, 1):
                b = p + d
                if not 2 <= b <= 10:
                    continue
                toward = {(-1, "x"): "east", (1, "x"): "west", (-1, "z"): "south", (1, "z"): "north"}
                stairs(c, b, EAVE - 1, a, "dark_oak", toward[(d, "x")], half="top")  # brace on a z-line, beside post
                stairs(c, a, EAVE - 1, b, "dark_oak", toward[(d, "z")], half="top")
    # tie beam across the lookout carrying two hanging lanterns
    for x in range(2, 11):
        c.put(x, EAVE, 6, "dark_oak_log", axis="x")
    for x in (4, 8):
        c.put(x, EAVE - 1, 6, "lantern", hanging=True, waterlogged=False)
    # dark-oak hipped (pitched) roof: ring k at EAVE + k
    for k in range(0, 6):
        y = EAVE + k
        for x in range(TW):
            for z in range(TW):
                if ring(x, z) == k:
                    f, s = inward(x, z, k)
                    stairs(c, x, y, z, "dark_oak", f, shape=s)
    c.put(6, EAVE + 5, 6, "dark_oak_planks")
    # eave lanterns (all four sides) and external banners on the two exterior panels
    for u in (3, 9):
        for x, z in ((0, u), (u, 0), (12, u), (u, 12)):
            c.put(x, EAVE - 1, z, "lantern", hanging=True, waterlogged=False)
    c.put(0, 9, 6, "white_wall_banner", facing="west")
    c.put(6, 9, 0, "white_wall_banner", facing="north")
    c.put(TW - 1, 10, 7, "white_wall_banner", facing="east")
    c.put(7, 10, TW - 1, "white_wall_banner", facing="south")
    return c


# ================================================================================================ MG gatehouse
GW, GH, GD = 24, 20, 12
PASS_X = (9, 14)  # clear passage, 6 wide
PASS_TOP = 7  # clear to y6 over the full width, y7 between the arch corbels
CORE_Z = (4, 9)  # gatehouse core (passage roofed over z4..9)
TURRET_X = ((0, 6), (17, 23))  # front turrets, z4..11
FORE = (10, 11)  # forecourt rows between the turrets (exterior approach inside the box)
ROOM_Y = (9, 12)  # room floor y9, headroom y10..12, roof deck y13
ROOM = (2, 21, 5, 8)  # x0, x1, z0, z1
SHAFT = (2, 4, 5, 8)  # west side shaft, entered from the compound side (z=4 face)
SHAFT_DOOR = (3, 4)
G_LADDER = (3, 8)  # attached to z=9, facing north
TOP_CORE, TOP_TURRET = 13, 15


def in_turret(x):
    return any(a <= x <= b for a, b in TURRET_X)


def gatehouse():
    c = Cells((GW, GH, GD))
    p0, p1 = PASS_X
    z0, z1 = CORE_Z
    # ground course: paving where people walk (passage, apron, forecourt), footing masonry elsewhere
    for x in range(GW):
        for z in range(GD):
            walk = p0 <= x <= p1 or z < z0 or (z in FORE and not in_turret(x))
            c.put(x, 0, z, path_stone(x + 44, z + 100) if walk else foot(x, 0, z))
    # masses: core z4..9 over the full width (passage excepted), turrets x0..6 / x17..23 forward to z11
    for x in range(GW):
        for z in range(z0, GD):
            if z > z1 and not in_turret(x):
                continue  # forecourt
            top = TOP_TURRET if in_turret(x) else TOP_CORE
            for y in range(1, top + 1):
                if p0 <= x <= p1 and y <= ROOM_Y[0] - 1 and z <= z1:
                    continue  # passage (roof added below)
                if z == GD - 1 and in_turret(x) and x not in (0, GW - 1, TURRET_X[0][1], TURRET_X[1][0]) \
                        and 2 <= y <= TOP_CORE:
                    continue  # turret front set back one block between its corner piers (corbelled parapet above)
                edge = x in (0, GW - 1, TURRET_X[0][1], TURRET_X[1][0], p0 - 1, p1 + 1) or z in (z0, GD - 1) or y == top
                c.put(x, y, z, masonry(x, y, z, edge=edge))
    # passage ceiling (dark-oak beams across the passage between stone courses) and the arch corbels at both faces
    for x in range(p0, p1 + 1):
        for z in range(z0, z1 + 1):
            c.put(x, PASS_TOP + 1, z, "dark_oak_log" if z in (z0 + 1, z1 - 1) else masonry(x, 8, z, edge=True),
                  **({"axis": "x"} if z in (z0 + 1, z1 - 1) else {}))
    for z in (z0, z1):
        stairs(c, p0, PASS_TOP, z, "stone_brick", "west", half="top")
        stairs(c, p1, PASS_TOP, z, "stone_brick", "east", half="top")
        for x in range(p0, p1 + 1):  # massive dark-oak lintel over both portals
            c.put(x, PASS_TOP + 1, z, "dark_oak_log", axis="x")
    # turret fronts: corbel course carrying the parapet forward over the set-back face
    for tx0, tx1 in TURRET_X:
        for x in range(tx0 + 1, tx1):
            stairs(c, x, TOP_CORE, GD - 1, "stone_brick", "north", half="top")
    # andesite pillars framing both portals (Q86), full passage height
    for z in (z0, z1):
        for y in range(1, PASS_TOP + 2):
            c.put(p0 - 1, y, z, "polished_andesite" if y in (1, PASS_TOP + 1) else "andesite")
            c.put(p1 + 1, y, z, "polished_andesite" if y in (1, PASS_TOP + 1) else "andesite")
    # the two gate leaves, hinged at the outer portal and fixed open inward against the passage sides (static blocks,
    # no door): dark-oak boards, a dark-oak log hanging stile at the hinge, iron strap bands
    for x in (p0 - 1, p1 + 1):
        for z in range(z1 - 3, z1):
            for y in range(1, PASS_TOP):
                if z == z1 - 1:
                    c.put(x, y, z, "dark_oak_log", axis="y")
                elif y in (2, 5):
                    c.put(x, y, z, "iron_bars", waterlogged=False)
                else:
                    c.put(x, y, z, "dark_oak_planks")
    # passage lanterns hung from the ceiling beams, at the side so the clear width stays 6
    for x, z in ((p0, z0 + 1), (p1, z0 + 1), (p0, z1 - 1), (p1, z1 - 1)):
        c.put(x, PASS_TOP, z, "lantern", hanging=True, waterlogged=False)
    # ---- observation room above the gate (Q87)
    rx0, rx1, rz0, rz1 = ROOM
    for x in range(rx0, rx1 + 1):
        for z in range(rz0, rz1 + 1):
            c.put(x, ROOM_Y[0], z, "spruce_planks")
            for y in range(ROOM_Y[0] + 1, ROOM_Y[1] + 1):
                del c[(x, y, z)]
    for x in (5, 18):  # timber cross beams under the roof deck, posts at the walls
        for z in range(rz0, rz1 + 1):
            c.put(x, ROOM_Y[1], z, "dark_oak_log", axis="z")
        for z in (rz0 - 1, rz1 + 1):
            for y in range(ROOM_Y[0] + 1, ROOM_Y[1] + 1):
                c.put(x, y, z, "dark_oak_log", axis="y")
    for x in (8, 15):
        c.put(x, ROOM_Y[1], 6, "lantern", hanging=True, waterlogged=False)
    c.put(rx1, ROOM_Y[0] + 1, 6, "chest", facing="west", type="single", waterlogged=False)
    for x in (16, 17, 19):  # weapon rack against the compound-side wall
        c.put(x, ROOM_Y[0] + 1, rz0, "stripped_dark_oak_log", axis="x")
        c.put(x, ROOM_Y[0] + 2, rz0, "exposed_lightning_rod", facing="up", powered=False, waterlogged=False)
    c.put(rx0 + 2, ROOM_Y[0] + 1, rz0, "barrel", facing="up", open=False)
    # observation openings: toward the approach (z9 face over the portal) and toward the checkpoint (z4 face)
    for x in (10, 13):
        for y in (10, 11):
            del c[(x, y, z1)]
    for x in (7, 11, 12, 16):
        for y in (10, 11):
            del c[(x, y, z0)]
    for x in (3, 20):  # turret-front openings looking down the approach
        for y in (10, 11):
            for z in (10, 11):
                if (x, y, z) in c:
                    del c[(x, y, z)]
        for y in (10, 11):
            for z in (z1,):
                if (x, y, z) in c:
                    del c[(x, y, z)]
    # ---- side shaft with its own ladder (west), door from the compound side
    sx0, sx1, sz0, sz1 = SHAFT
    for x in range(sx0, sx1 + 1):
        for z in range(sz0, sz1 + 1):
            for y in range(1, ROOM_Y[0]):
                del c[(x, y, z)]
    dx, dz = SHAFT_DOOR
    for y in (1, 2):
        del c[(dx, y, dz)]
    B8.Cells.put(c, dx, 1, dz, "dark_oak_door", facing="north", half="lower", hinge="left", open=False, powered=False)
    B8.Cells.put(c, dx, 2, dz, "dark_oak_door", facing="north", half="upper", hinge="left", open=False, powered=False)
    lx, lz = G_LADDER
    for y in range(1, ROOM_Y[0] + 1):
        c.put(lx, y, lz, "ladder", facing="north", waterlogged=False)
    c.put(sx0, ROOM_Y[0] - 1, sz0, "lantern", hanging=True, waterlogged=False)
    # arrow slits in the set-back turret fronts (z10)
    for x in (3, 20):
        for y in (4, 5):
            del c[(x, y, GD - 2)]
    # ---- battlements: core deck (z4 and z9 edges) and turret tops (all edges)
    for x in range(GW):
        for z in range(z0, GD):
            if z > z1 and not in_turret(x):
                continue
            if in_turret(x):
                tx0, tx1 = next(t for t in TURRET_X if t[0] <= x <= t[1])
                perim = x in (tx0, tx1) or z in (z0, GD - 1)
                if perim:
                    u = x + z
                    if u % 3 != 0 or x in (tx0, tx1) and z in (z0, GD - 1):
                        c.put(x, TOP_TURRET + 1, z, masonry(x, 16, z, edge=True))
                        c.put(x, TOP_TURRET + 2, z, "stone_bricks")
            elif z in (z0, z1):
                if x % 3 != 1:
                    c.put(x, TOP_CORE + 1, z, masonry(x, 14, z, edge=True))
                    c.put(x, TOP_CORE + 2, z, "stone_bricks")
    # ---- banners and lanterns: checkpoint face (z4 -> z3 cells), forecourt (turret sides), over the outer portal
    for x in (6, 17):
        c.put(x, 6, z0 - 1, "white_wall_banner", facing="north")
    c.put(TURRET_X[0][1] + 1, 6, FORE[0], "white_wall_banner", facing="east")
    c.put(TURRET_X[1][0] - 1, 6, FORE[0], "white_wall_banner", facing="west")
    for x in (10, 13):
        c.put(x, 9, FORE[0], "white_wall_banner", facing="south")
    # ---- Q80 checkpoint inside (z0..3): wall-post lanterns flanking the road, racks, barriers, stores
    for x in (p0 - 1, p1 + 1):
        c.put(x, 1, 0, "stone_brick_wall")
        c.put(x, 2, 0, "stone_brick_wall")
        c.put(x, 3, 0, "lantern", hanging=False, waterlogged=False)
    for x in (5, 6):
        c.put(x, 1, z0 - 1, "stripped_dark_oak_log", axis="x")
        c.put(x, 2, z0 - 1, "exposed_lightning_rod", facing="up", powered=False, waterlogged=False)
    for x in (17, 18):
        c.put(x, 1, z0 - 1, "stripped_dark_oak_log", axis="x")
        c.put(x, 2, z0 - 1, "exposed_lightning_rod", facing="up", powered=False, waterlogged=False)
    for x in range(17, 22):  # timber barrier (east): a low spruce fence rail with a log at each end
        c.put(x, 1, 1, "dark_oak_log" if x in (17, 21) else "spruce_fence", **({"axis": "y"} if x in (17, 21) else {}))
    for x in range(5, 8):  # timber barrier (west), shorter so the shaft door at x3 stays open to the road
        c.put(x, 1, 1, "dark_oak_log" if x in (5, 7) else "spruce_fence", **({"axis": "y"} if x in (5, 7) else {}))
    c.put(0, 1, 3, "barrel", facing="up", open=False)
    c.put(1, 1, 3, "hay_block", axis="y")
    c.put(22, 1, 3, "barrel", facing="up", open=False)
    c.put(23, 1, 3, "barrel", facing="up", open=False)
    c.put(23, 2, 3, "barrel", facing="up", open=False)
    # ---- Q88 forecourt (z10..11, x7..8 / x15..16 beside the 6-wide passage)
    c.put(7, 1, 11, "barrel", facing="up", open=False)
    c.put(7, 1, 10, "spruce_log", axis="z")
    c.put(8, 1, 10, "spruce_log", axis="z")
    c.put(7, 2, 10, "spruce_log", axis="z")
    c.put(16, 1, 10, "stripped_dark_oak_log", axis="z")
    c.put(16, 2, 10, "exposed_lightning_rod", facing="up", powered=False, waterlogged=False)
    c.put(16, 1, 11, "barrel", facing="up", open=False)
    for x in (8, 15):
        if x == 8:
            c.put(x, 1, 11, "stone_brick_wall")
            c.put(x, 2, 11, "stone_brick_wall")
            c.put(x, 3, 11, "lantern", hanging=False, waterlogged=False)
        else:
            c.put(x, 1, 11, "stone_brick_wall")
            c.put(x, 2, 11, "stone_brick_wall")
            c.put(x, 3, 11, "lantern", hanging=False, waterlogged=False)
            c.put(x, 1, 10, "spruce_fence")
    return c


BUILDINGS = {
    "tower": dict(module="MT", placements=("T-NW", "T-NE", "T-SE", "T-SW"), design=tower, size=(TW, TH, TW),
                  door=None, entrance=(10, DOOR_Z)),
    "gatehouse": dict(module="MG", placements=("GATE",), design=gatehouse, size=(GW, GH, GD), door=None,
                      entrance=SHAFT_DOOR),
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
