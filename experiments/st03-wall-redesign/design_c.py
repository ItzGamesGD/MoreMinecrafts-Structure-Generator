"""Design C - "Scarp and casemates": a horizontal, layered wall with a hollowed inner face.

Idea: an hourglass section. Outside, a two-step rubble scarp sheds the base outward, the wall pulls back into a
recessed waist pierced by a band of small loops, and a two-stage machicolation pushes the parapet back out to the
front line - three strong horizontal shadow lines instead of vertical buttresses. The parapet has pointed
(gable-capped) merlons and timber shutters hinged in the crenels. The end piers are plain solid masses that stop the
bands cleanly at the tower / gate joints. Inside, the wall is hollowed into a continuous arcade of casemate niches
under dark-oak lintels with knee braces - storage bays for barrels, timber and hay - with a stone wall-rail on the
wall-walk above. Timber appears where it carries something (lintels, braces) or moves (shutters).

Planes (local z): 0 scarp foot / corbel ends / parapet, 1 scarp upper step / first corbel, 2 curtain face (waist),
3..4 inner masonry (casemate piers and spandrels). Heights: y0 footing, scarp to y2 (z0) and y4 (z1), waist y5..6,
corbels y7 (z1) and y8 (z0, alternating with machicolation slots), deck y8, sill y9, merlons y10..11, caps y12.
"""

from common import (D, H, Cells, ashlar, ashlar_stair, banner, crenels, footing, lantern, log, noise, rubble,
                    rubble_stair, slab, stairs, trap)

END = 4


def build(L):
    c = Cells((L, H, D))
    footing(c, L)
    cren = crenels(L, 1, 4, 3)  # end merlons 4 wide over the end piers, then 3-wide merlons / 1-wide crenels
    # machicolation slots under every crenel and every merlon centre (left half, mirrored)
    half = {x for x in range(END, (L + 1) // 2) if x in cren or (x - 1) % 4 == 1}
    holes = half | {L - 1 - x for x in half}
    for x in range(L):
        end = x < END or x >= L - END
        # curtain z2 (exterior face of the waist) and inner masonry z3..4 up to the deck
        for y in range(1, 8):
            c.put(x, y, 2, ashlar(x, y, 2))
            c.put(x, y, 3, ashlar(x, y, 3))
            c.put(x, y, 4, rubble(x, y, 4) if y <= 2 else ashlar(x, y, 4))
        for z in (1, 2, 3, 4):
            c.put(x, 8, z, "stone_bricks" if noise(x, z, 9, 3) else "cracked_stone_bricks")
        if end:
            for y in range(1, 9):
                c.put(x, y, 0, "stone_bricks" if x in (0, L - 1) else ashlar(x, y, 0))
                c.put(x, y, 1, ashlar(x, y, 1))
        else:
            # scarp: z0 to y2, z1 to y4
            c.put(x, 1, 0, rubble(x, 1, 0))
            stairs(c, x, 2, 0, rubble_stair(x, 2, 0), "south")
            for y in range(1, 4):
                c.put(x, y, 1, rubble(x, y, 1))
            stairs(c, x, 4, 1, rubble_stair(x, 4, 1), "south")
            # machicolation: continuous first corbel at z1 y7, alternating second corbel at z0 y8
            stairs(c, x, 7, 1, ashlar_stair(x, 7, 1), "south", half="top")
            if x not in holes:
                stairs(c, x, 8, 0, ashlar_stair(x, 8, 0), "south", half="top")
        # parapet
        c.put(x, 9, 0, "stone_bricks" if noise(x, 9, 11, 6) else "cracked_stone_bricks")
        if x in cren:
            trap(c, x, 11, 0, "spruce", "south", True, half="top")  # shutter hinged in the crenel
        else:
            c.put(x, 10, 0, ashlar(x, 10, 0))
            c.put(x, 11, 0, ashlar(x, 11, 0))
        # inner stone rail on the wall-walk
        c.put(x, 9, 4, "stone_brick_wall")
    # merlon caps: pointed on 3-wide merlons, flat-chamfered on the wider end / middle merlons
    x = 0
    while x < L:
        if x in cren:
            x += 1
            continue
        y0 = x
        while x < L and x not in cren:
            x += 1
        lo, hi = y0, x - 1
        if hi - lo == 2:
            stairs(c, lo, 12, 0, "stone_brick", "east")
            c.put(lo + 1, 12, 0, "stone_bricks")
            stairs(c, hi, 12, 0, "stone_brick", "west")
        else:
            for xx in range(lo, hi + 1):
                c.put(xx, 12, 0, "stone_bricks")
            if lo > 0:
                stairs(c, lo, 12, 0, "stone_brick", "east")
            if hi < L - 1:
                stairs(c, hi, 12, 0, "stone_brick", "west")
    casemates(c, L)
    # waist loops (1x1, through the wall above the casemates) at every second merlon centre
    centres = [x for x in range(END + 1, (L + 1) // 2) if (x - 1) % 4 == 1]
    loops = {x for i, x in enumerate(centres) if i % 2 == 1}
    loops |= {L - 1 - x for x in loops}
    for x in sorted(loops):
        for z in (2, 3, 4):
            del c[(x, 6, z)]
    # end zones: banners hung in the waist, lanterns under a keyed corbel
    for side in (0, 1):
        X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
        banner(c, X(END + 2), 6, 1, "north")
        c.put(X(END + 5), 7, 1, "stone_bricks")
        lantern(c, X(END + 5), 6, 1)
    if L == 86:
        banner(c, 41, 6, 1, "north")
    return c


def casemates(c, L):
    """Arcade of niches in the inner face (z3..4, y1..3) under dark-oak lintels (y4) with knee braces."""
    left = []
    x = END
    while x + 4 <= (L + 1) // 2:
        left.append((x, x + 3))
        x += 6
    niches = left + [(L - 1 - b, L - 1 - a) for a, b in left if (L - 1 - b) > left[-1][1] + 1]
    stores = ["barrels", "logs", "empty", "hay", "barrels", "empty", "logs"]
    for i, (a, b) in enumerate(sorted(niches)):
        for xx in range(a, b + 1):
            for y in (1, 2, 3):
                for z in (3, 4):
                    del c[(xx, y, z)]
            log(c, xx, 4, 4, "x")
        stairs(c, a, 3, 4, "dark_oak", "west", half="top")
        stairs(c, b, 3, 4, "dark_oak", "east", half="top")
        kind = stores[i % len(stores)]
        m = (a + b) // 2
        if kind == "barrels":
            c.put(a + 1, 1, 3, "barrel", facing="up", open=False)
            c.put(m + 1, 1, 3, "barrel", facing="up", open=False)
            c.put(a + 1, 2, 3, "barrel", facing="up", open=False)
        elif kind == "logs":
            for xx in range(a + 1, b):
                log(c, xx, 1, 3, "x", wood="spruce")
            log(c, m, 2, 3, "x", wood="spruce")
        elif kind == "hay":
            c.put(a + 1, 1, 3, "hay_block", axis="y")
            c.put(m + 1, 1, 3, "hay_block", axis="x")
            c.put(a + 1, 2, 3, "hay_block", axis="y")
    # lanterns in the niches nearest the ends
    for a, b in (min(niches), max(niches)):
        lantern(c, (a + b) // 2 + (1 if a > L // 2 else 0), 3, 4)


def mw86():
    return build(86)


def mw31():
    return build(31)
