"""Stage 24-E roof and massing alternatives for the five residential modules (proposals only).

Every variant starts from the final Stage 24-C NBT and is written to artifacts/.../stage-24e/proposals/.
Variants whose height grows beyond the Stage 24-C bounds are marked as needing owner authorisation.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24e.kit import Variant, stair, slab, with_props, BRICK, TILE, POL, TILE_ST  # noqa: E402

BASALT = "polished_basalt[axis=y]"
CHIS = "chiseled_deepslate"
GLASS = "cyan_stained_glass"


def perimeter(sx, sz):
    for x in range(sx):
        for z in range(sz):
            if x in (0, sx - 1) or z in (0, sz - 1):
                yield x, z


def inward(x, z, sx, sz):
    """facing that points into the footprint from an edge cell (x edges win at corners; shapes are fixed later)"""
    if x == 0:
        return "east"
    if x == sx - 1:
        return "west"
    if z == 0:
        return "south"
    return "north"


def portal(v, door_z, top=3, lintel=CHIS, transom=None):
    """west-facade entrance: polished-basalt jambs up to `top`, chiseled lintel over the 2-high door (door blocks untouched)"""
    for dz in (-1, 1):
        for y in range(1, top + 1):
            v.set((0, y, door_z + dz), BASALT)
    v.set((0, 3, door_z), lintel)
    if transom:
        v.set((0, 4, door_z), transom)


# ---------------------------------------------------------------- large_ruin_1 (17 x 5 x 17, court x6..10 z6..10)
def ring_heights(x, z):
    d_out = min(x, 16 - x, z, 16 - z)
    d_in = max(6 - x, x - 10, 6 - z, z - 10) - 1
    return d_out, d_in


def ring_facing(x, z):
    d_out, d_in = ring_heights(x, z)
    if d_out <= d_in:   # outer slope: rise away from the nearest outer edge
        e = min((x, "east"), (16 - x, "west"), (z, "south"), (16 - z, "north"))
        return e[1]
    ox, oz = max(6 - x, x - 10, 0), max(6 - z, z - 10, 0)   # inner slope: rise away from the court
    if ox >= oz:
        return "west" if x < 6 else "east"
    return "north" if z < 6 else "south"


def large_A():
    v = Variant("large_ruin_1", "A", "Impluvium court — stepped eaves falling outward and into the court (in bounds)")
    for x, z in perimeter(17, 17):
        v.set((x, 3, z), CHIS if (x, z) == (0, 7) else stair(inward(x, z, 17, 17)))
    for x in range(1, 16):
        for z in range(1, 16):
            if x in (1, 15) or z in (1, 15):
                v.set((x, 4, z), stair(inward(x - 1, z - 1, 15, 15)))
    for x, z in perimeter(17, 17):
        v.clear((x, 4, z))
    for x in range(5, 12):        # court rim falls into the open court
        for z in range(5, 12):
            if x in (5, 11) or z in (5, 11):
                f = "west" if x == 5 else "east" if x == 11 else "north" if z == 5 else "south"
                v.set((x, 4, z), stair(f))
    for x, z in ((0, 0), (16, 0), (0, 16), (16, 16)):
        for y in (1, 2):
            v.set((x, y, z), BASALT)
    portal(v, 7, top=2)
    v.finish()
    return v


def large_ring(v, top_wall=5, step=2):
    """raise the outer walls and partitions, then a steep double-pitched ring roof around the open court"""
    v.clear_layer(4)
    v.raise_walls(3, 4, top_wall)
    base = top_wall + 1
    for x in range(17):
        for z in range(17):
            if 6 <= x <= 10 and 6 <= z <= 10:
                continue
            h = min(ring_heights(x, z))
            y = base + step * h
            v.set((x, y, z), stair(ring_facing(x, z)))
            for yy in range(y - step + 1, y):      # steep pitch: one-block skin under each raised step
                if yy >= base:
                    v.set((x, yy, z), TILE)
    portal(v, 7, top=5, transom=GLASS)
    for x in (2, 8, 14):
        for z in (0, 16):
            v.set((x, 4, z), GLASS)
    for z in (2, 14):
        for x in (0, 16):
            v.set((x, 4, z), GLASS)
    return base


def large_B():
    v = Variant("large_ruin_1", "B", "Raised cloister house — 5-high walls under a steep (2:1) double-pitched ring roof around the court (17×11×17, needs authorisation)")
    large_ring(v)
    v.finish()
    return v


def large_C():
    v = Variant("large_ruin_1", "C", "Lancet gatehouse — raised walls, a low ring roof and one steep pointed gable over the entrance range (17×14×17, needs authorisation)")
    base = large_ring(v, step=1)
    z0, z1, zc, step = 3, 11, 7, 2
    for x in range(0, 6):                   # clear the ring roof under the cross gable
        for z in range(z0, z1 + 1):
            for y in range(base, base + 16):
                if (x, y, z) in v.blocks:
                    v.clear((x, y, z))
    prof = {z: base + step * min(z - z0, z1 - z) for z in range(z0, z1 + 1)}
    prof[zc] = prof[zc - 1] + 1             # the apex closes one block above the last stair pair
    for x in range(0, 6):
        for z in range(z0, z1 + 1):
            y = prof[z]
            v.set((x, y, z), POL if z == zc else stair("south" if z < zc else "north"))
            for yy in range(max(base, y - step + 1), y):
                v.set((x, yy, z), TILE)
    for gx in (0, 5):                       # gable walls: street front and court side
        for z in range(z0, z1 + 1):
            for y in range(base, prof[z] - (0 if z == zc else 0)):
                if (gx, y, z) not in v.blocks:
                    v.set((gx, y, z), BRICK)
    for y in range(base, base + 4):         # tall lancet window under a chiseled apex stone
        v.set((0, y, zc), GLASS)
    v.set((0, base + 4, zc), CHIS)
    for gx in (0, 5):                       # polished barge courses outline the pointed gables
        for z in range(z0, z1 + 1):
            if z != zc:
                v.set((gx, prof[z] - 1, z), POL) if prof[z] - 1 >= base and (gx, prof[z] - 1, z) in v.blocks else None
    for y in range(base + 1, base + 3):
        v.set((5, y, zc), GLASS)
    v.finish()
    return v


# ---------------------------------------------------------------- medium_ruin_1 (8 x 5 x 13, door west z=6)
def medium1_A():
    v = Variant("medium_ruin_1", "A", "Stepped hip — two-tier eaves on all four sides, polished portal (in bounds)")
    for x, z in perimeter(8, 13):
        v.set((x, 3, z), CHIS if (x, z) == (0, 6) else stair(inward(x, z, 8, 13)))
        v.clear((x, 4, z))
    for x in range(1, 7):
        for z in range(1, 12):
            if x in (1, 6) or z in (1, 11):
                v.set((x, 4, z), stair(inward(x - 1, z - 1, 6, 11)))
            else:
                v.set((x, 4, z), TILE)
    portal(v, 6, top=2)
    v.finish()
    return v


def medium1_B():
    v = Variant("medium_ruin_1", "B", "Long gable — 45° roof along the house with brick gable ends (8×8×13, needs authorisation)")
    v.clear_layer(4)
    for x in range(8):
        k = min(x, 7 - x)
        for z in range(13):
            v.set((x, 4 + k, z), stair("east" if x < 4 else "west"))
    for gz in (0, 12):
        for x in range(8):
            for y in range(4, 4 + min(x, 7 - x)):
                v.set((x, y, gz), BRICK)
    v.set((3, 5, 0), GLASS); v.set((4, 5, 0), GLASS)
    v.set((3, 5, 12), CHIS); v.set((4, 5, 12), CHIS)
    portal(v, 6, top=3)
    v.finish()
    return v


# ---------------------------------------------------------------- medium_ruin_2 (16 x 8 x 11, upper wing x7..15)
def medium2_A():
    v = Variant("medium_ruin_2", "A", "Saltbox — the hall roof climbs in a long 1:2 slope into a hipped upper storey (in bounds)")
    for x in range(0, 7):
        for z in range(0, 11):
            v.clear((x, 4, z))
    for x in range(0, 7):
        y = 4 + x // 2
        for z in range(0, 11):
            if x == 6:
                v.set((x, 7, z), TILE)                      # joins the upper roof; keeps the stair-run headroom
            elif x % 2 == 0:
                v.set((x, y, z), stair("east"))
            else:
                v.set((x, y, z), slab("top", "deepslate_tile_slab"))
        top = 7 if x == 6 else y
        for z in (0, 10):                   # saltbox side walls follow the slope
            for yy in range(4, top):
                v.set((x, yy, z), BRICK)
    for x in range(7, 16):                  # two-step hip on the upper storey
        for z in range(0, 11):
            if x == 15 or z in (0, 10):
                v.set((x, 6, z), stair("west" if x == 15 else "south" if z == 0 else "north"))
            elif x == 14 or z in (1, 9):
                v.set((x, 7, z), stair("west" if x == 14 else "south" if z == 1 else "north"))
    for z in (0, 10):
        v.set((7, 6, z), stair("south" if z == 0 else "north"))
    v.set((15, 5, 5), GLASS)
    portal(v, 5, top=2)
    v.finish()
    return v


def medium2_B():
    v = Variant("medium_ruin_2", "B", "Gabled loft — low layered slab-and-stair gable over the upper storey, gable window to the street (16×10×11, needs authorisation)")
    for x in range(7, 16):
        for z in range(0, 11):
            v.clear((x, 7, z))
    for x in range(7, 16):
        for z in range(0, 11):
            k = min(z, 10 - z)
            y = 7 + k // 2
            if k % 2 == 0 and z != 5:
                v.set((x, y, z), stair("south" if z < 5 else "north"))
            else:
                v.set((x, y, z), slab("top", "deepslate_tile_slab"))
            for yy in range(7, y):
                if x in (7, 15):
                    v.set((x, yy, z), BRICK)
    v.set((7, 8, 5), GLASS); v.set((15, 8, 5), GLASS)
    for x, z in perimeter(7, 11):           # layered eaves on the lower hall (stairwell opening kept clear)
        if x <= 6 and (x == 0 or z in (0, 10)):
            v.set((x, 3, z), CHIS if (x, z) == (0, 5) else stair(inward(x, z, 8, 11)))
    portal(v, 5, top=2)
    v.finish()
    return v


# ---------------------------------------------------------------- small_ruin_1 (7 x 5 x 8, door west z=3)
def small1_A():
    v = Variant("small_ruin_1", "A", "Stepped street gable — eaves on the long sides, pedimented gable ends (in bounds)")
    for x in range(7):
        for z in (0, 7):
            v.set((x, 3, z), stair("south" if z == 0 else "north"))
            v.clear((x, 4, z))
    for x in range(7):
        for z in range(1, 7):
            if z in (1, 6):
                v.set((x, 4, z), stair("south" if z == 1 else "north"))
            else:
                v.set((x, 4, z), POL if x in (0, 6) else TILE)
    portal(v, 3, top=2)
    v.finish()
    return v


def small1_B():
    v = Variant("small_ruin_1", "B", "Steep street gable — 45° roof with the gable and a window facing the street (7×8×8, needs authorisation)")
    v.clear_layer(4)
    for z in range(8):
        k = min(z, 7 - z)
        for x in range(7):
            v.set((x, 4 + k, z), stair("south" if z < 4 else "north"))
    for gx in (0, 6):
        for z in range(8):
            for y in range(4, 4 + min(z, 7 - z)):
                v.set((gx, y, z), BRICK)
    v.set((0, 5, 3), GLASS); v.set((0, 5, 4), GLASS); v.set((0, 6, 3), CHIS); v.set((0, 6, 4), CHIS)
    portal(v, 3, top=3)
    v.finish()
    return v


# ---------------------------------------------------------------- small_ruin_2 (8 x 5 x 4, door west z=2)
def small2_A():
    v = Variant("small_ruin_2", "A", "Mono-pitch — single slope rising to the north wall, glazed south front, framed doorway (in bounds)")
    for x in range(8):
        v.set((x, 3, 3), stair("north"))
        v.clear((x, 4, 3))
        v.set((x, 4, 2), stair("north"))
    for x in (2, 4):
        v.set((x, 2, 3), GLASS)
    portal(v, 2, top=2)
    v.finish()
    return v


def small2_B():
    v = Variant("small_ruin_2", "B", "Steep A-frame — 2:1 pitch closing in a back-to-back stair ridge (8×7×4, needs authorisation)")
    v.clear_layer(4)
    for x in range(8):
        v.set((x, 4, 0), stair("south")); v.set((x, 4, 3), stair("north"))
        for y in (4, 5):
            v.set((x, y, 1), TILE); v.set((x, y, 2), TILE)
        v.set((x, 6, 1), stair("south")); v.set((x, 6, 2), stair("north"))   # back-to-back ridge
    for gx in (0, 7):
        v.set((gx, 5, 1), POL); v.set((gx, 5, 2), POL)
    v.set((0, 4, 1), CHIS); v.set((0, 4, 2), CHIS)
    portal(v, 2, top=3)
    v.finish()
    return v


DESIGNS = {
    "large_ruin_1": [large_A, large_B, large_C],
    "medium_ruin_1": [medium1_A, medium1_B],
    "medium_ruin_2": [medium2_A, medium2_B],
    "small_ruin_1": [small1_A, small1_B],
    "small_ruin_2": [small2_A, small2_B],
}
