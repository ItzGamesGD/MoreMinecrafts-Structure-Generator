"""Design A - "Counterfort arcade": a vertical, rhythmic stone wall.

Idea: the depth comes from the STRUCTURE, not from decoration. Two-stage counterforts (buttresses) project to the
exterior line; between them the curtain is set back two blocks and each bay is closed at the top by a segmental stone
arch. The parapet is carried forward over the arches on a corbel table, so every bay reads as a deep, shadowed
arched recess, and machicolation slots open under the crenels. Merlons are graded: full-height 4-wide merlons over
the counterforts, half-capped 2/3-wide merlons over the bays. The end piers (tower / gate abutments) are solid
full-height masses with a pointed banner niche. Inside, counterforts answer the outside ones and carry a timber
wall-walk widening (dark-oak wall plate on knee braces) with a fence rail - the timber is the walkway structure.

Planes (local z): 0 front line (counterfort feet, corbels, parapet), 1 counterfort upper stage / arch plane,
2..3 curtain (2 thick) - bay face at z2, 4 inside (counterforts, timber walk edge).
Heights: y0 footing, y1 plinth, arches y7..8, deck y9 (z1..3), parapet z0: sill y10, merlons y11..12.
"""

from common import (D, H, Cells, ashlar, ashlar_stair, banner, footing, lantern, log, noise, rubble, rubble_stair,
                    slab, stairs)

END = 4  # end-pier width


def layout(L):
    """[(kind, x0, x1)] - 'end', 'bay', 'cf' (counterfort, 2 wide). MW86: 4 + 10 bays of 6 + 9 cf + 4;
    MW31: 4 + bays 6/7/6 + 2 cf + 4."""
    widths = [6] * 10 if L == 86 else [6, 7, 6]
    out, x = [("end", 0, END - 1)], END
    for i, w in enumerate(widths):
        out.append(("bay", x, x + w - 1))
        x += w
        if i < len(widths) - 1:
            out.append(("cf", x, x + 1))
            x += 2
    out.append(("end", x, x + END - 1))
    assert x + END == L, (L, x)
    return out


def build(L):
    c = Cells((L, H, D))
    footing(c, L)
    parts = layout(L)
    # curtain z2..3 y1..8 everywhere, deck y9 z1..3
    for x in range(L):
        for y in range(1, 9):
            c.put(x, y, 2, ashlar(x, y, 2))
            c.put(x, y, 3, ashlar(x, y, 3))
        for z in (1, 2, 3):
            c.put(x, 9, z, "stone_bricks" if noise(x, z, 9, 2) else "cracked_stone_bricks")
        # parapet sill
        c.put(x, 10, 0, "stone_bricks" if noise(x, 10, 11, 5) else "cracked_stone_bricks")
    cren = set()
    for kind, a, b in parts:
        if kind == "end":
            end_pier(c, a, b, L)
        elif kind == "cf":
            counterfort(c, a, b)
        else:
            bay(c, a, b)
            cren |= {a + 1, b - 1}
    # merlons: full over counterforts / end piers, half-capped over bays
    for kind, a, b in parts:
        for x in range(a, b + 1):
            if x in cren:
                continue
            c.put(x, 11, 0, ashlar(x, 11, 0))
            if kind == "bay" and a + 1 < x < b - 1:
                slab(c, x, 12, 0, "stone_brick", "bottom")
            else:
                c.put(x, 12, 0, "stone_bricks")
    # bay merlons adjacent to a counterfort belong to the big merlon (x == a or x == b): full height already
    inside(c, L, parts)
    return c


def bay(c, a, b):
    for x in range(a, b + 1):
        # front line: battered plinth, corbels with machicolation slots under the crenels
        stairs(c, x, 1, 0, rubble_stair(x, 1, 0), "south")
        if x not in (a + 1, b - 1):
            stairs(c, x, 9, 0, ashlar_stair(x, 9, 0), "south", half="top")
        # arch plane z1: plinth, weathering, open recess, segmental arch
        c.put(x, 1, 1, rubble(x, 1, 1))
        c.put(x, 2, 1, rubble(x, 2, 1))
        stairs(c, x, 3, 1, ashlar_stair(x, 3, 1), "south")
    stairs(c, a, 7, 1, "stone_brick", "west", half="top")
    stairs(c, b, 7, 1, "stone_brick", "east", half="top")
    c.put(a, 8, 1, "stone_bricks")
    c.put(b, 8, 1, "stone_bricks")
    stairs(c, a + 1, 8, 1, "stone_brick", "west", half="top")
    stairs(c, b - 1, 8, 1, "stone_brick", "east", half="top")
    for x in range(a + 2, b - 1):
        slab(c, x, 8, 1, "stone_brick", "top")
    # one arrow slit per bay through the curtain: 2 high outside, narrowed to 1 high in the core (no passage)
    s = (a + b) // 2
    for y in (4, 5):
        del c[(s, y, 2)]
    del c[(s, 5, 3)]


def counterfort(c, a, b):
    for x in (a, b):
        for y in range(1, 5):
            c.put(x, y, 0, rubble(x, y, 0) if y <= 2 else ashlar(x, y, 0))
        stairs(c, x, 5, 0, ashlar_stair(x, 5, 0), "south")  # set-off weathering
        stairs(c, x, 9, 0, "stone_brick", "south", half="top")
        for y in range(1, 9):
            c.put(x, y, 1, ashlar(x, y, 1))
        c.put(x, 8, 1, "chiseled_stone_bricks")  # capital band where the arches spring


def end_pier(c, a, b, L):
    for x in range(a, b + 1):
        for z in (0, 1):
            for y in range(1, 10):
                c.put(x, y, z, "stone_bricks" if (x in (0, L - 1) and y % 2) else ashlar(x, y, z))
    # pointed banner niche in the middle two columns of the pier face
    m = a + 1
    for x in (m, m + 1):
        for y in range(3, 8):
            del c[(x, y, 0)]
    stairs(c, m, 8, 0, "stone_brick", "west", half="top")
    stairs(c, m + 1, 8, 0, "stone_brick", "east", half="top")
    banner(c, m, 7, 0, "north")
    banner(c, m + 1, 7, 0, "north")
    slab(c, m, 3, 0, "stone_brick", "bottom")
    slab(c, m + 1, 3, 0, "stone_brick", "bottom")


def inside(c, L, parts):
    """Counterforts answering the outside ones; a timber wall-walk widening on the inner edge."""
    cfs = [x for kind, a, b in parts if kind == "cf" for x in (a, b)]
    ends = [x for kind, a, b in parts if kind == "end" for x in range(a, b + 1)]
    for x in range(L):
        if x in ends:
            for y in range(1, 9):
                c.put(x, y, 4, ashlar(x, y, 4))
        elif x in cfs:
            for y in range(1, 8):
                c.put(x, y, 4, rubble(x, y, 4) if y <= 2 else ashlar(x, y, 4))
            stairs(c, x, 8, 4, "dark_oak", "north", half="top")  # timber corbel on the counterfort
        else:
            stairs(c, x, 1, 4, rubble_stair(x, 1, 4), "north")
        # wall-walk widening: dark-oak wall plate, fence rail with posts over the counterforts
        log(c, x, 9, 4, "x")
        c.put(x, 10, 4, "dark_oak_fence")
    # knee braces beside every counterfort
    for kind, a, b in parts:
        if kind == "cf":
            stairs(c, a - 1, 8, 4, "dark_oak", "east", half="top")
            stairs(c, b + 1, 8, 4, "dark_oak", "west", half="top")
    # end zones (toward tower / gate): lanterns under the wall plate, stores at the base
    for side in (0, 1):
        X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
        lantern(c, X(6), 8, 4)
        c.put(X(5), 1, 4, "barrel", facing="up", open=False)
        c.put(X(6), 1, 4, "barrel", facing="up", open=False)
        log(c, X(8), 1, 4, "x", wood="spruce")
        log(c, X(9), 1, 4, "x", wood="spruce")
        log(c, X(8), 2, 4, "x", wood="spruce")
        # outside: lanterns hung in the first bay's arch (a full keystone carries them)
        bay1 = [p for p in parts if p[0] == "bay"][0 if side == 0 else -1]
        k = (bay1[1] + bay1[2]) // 2 + (1 if side else 0)
        c.put(k, 8, 1, "stone_bricks")
        lantern(c, k, 7, 1)
    if L == 86:
        mid = [p for p in parts if p[0] == "bay"][5]
        banner(c, (mid[1] + mid[2]) // 2 - 1, 6, 1, "north")


def mw86():
    return build(86)


def mw31():
    return build(31)
