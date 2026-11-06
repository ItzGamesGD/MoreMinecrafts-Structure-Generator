"""Design B - "Hoarded wall": stone below, a roofed timber fighting gallery above.

Idea: the medieval answer to a thin curtain - a timber hoarding cantilevered out over the battered stone wall on
dark-oak joists. Stone and timber each do structural work: a two-step rubble talus and a stone curtain carry the
deck; projecting stone piers (with a blind cross loop and their own crenellation) divide the wall into bays and
take the ends of the hoardings; each bay is spanned by a covered gallery - joists on brackets, a plank floor with
murder-hole hatches, a boarded front with loopholes between posts, and a low dark-oak gable roof. The roofs give
the wall a rhythmic, broken silhouette; the stone piers keep the crenellated military line (Q82). The gallery is
open to the compound side behind a rail; the pier tops are open platforms between the galleries.

Planes (local z): 0 talus foot / pier faces / hoarding front, 1 talus upper step / joists, 2..3 curtain, 4 inside.
Heights: y0 footing, talus to y2 (z0) and y5 (z1), joists y8, gallery floor y8 (feet y9), loopholes y10,
roof eaves y11, ridge y12. Piers: deck y8, sill y9, merlons y10..12.
"""

from common import (D, H, Cells, ashlar, ashlar_stair, banner, footing, lantern, log, noise, rubble, rubble_stair,
                    slab, stairs, trap)

END = 3
PIER = 5


def layout(L):
    """MW86: 3 + 5 bays of 12 + 4 piers of 5 + 3; MW31: 3 + 10 + 5 + 10 + 3."""
    n, w = (5, 12) if L == 86 else (2, 10)
    out, x = [("end", 0, END - 1)], END
    for i in range(n):
        out.append(("bay", x, x + w - 1))
        x += w
        if i < n - 1:
            out.append(("pier", x, x + PIER - 1))
            x += PIER
    out.append(("end", x, x + END - 1))
    assert x + END == L
    return out


def panels(a, b):
    """Posts 3 in from each end of the bay; returns (posts, [panel ranges])."""
    p = [a + 3, b - 3]
    return p, [(a, p[0] - 1), (p[0] + 1, p[1] - 1), (p[1] + 1, b)]


def centres(lo, hi):
    m = (lo + hi) / 2
    return {int(m)} if m == int(m) else {int(m), int(m) + 1}


def build(L):
    c = Cells((L, H, D))
    footing(c, L)
    parts = layout(L)
    for x in range(L):  # curtain and stone deck
        for y in range(1, 8):
            c.put(x, y, 2, ashlar(x, y, 2))
            c.put(x, y, 3, ashlar(x, y, 3))
        c.put(x, 8, 2, "stone_bricks")
        c.put(x, 8, 3, "stone_bricks")
    bays = [p for p in parts if p[0] == "bay"]
    for kind, a, b in parts:
        if kind == "bay":
            bay(c, a, b)
        else:
            pier(c, a, b, kind == "end", L)
    # banners on the pier flanks next to the tower / gate ends, and irregularly on two inner piers (MW86)
    banner(c, END, 6, 0, "east")
    banner(c, L - 1 - END, 6, 0, "west")
    if L == 86:
        piers = [p for p in parts if p[0] == "pier"]
        banner(c, piers[0][1] - 1, 6, 0, "west")
        banner(c, piers[2][2] + 1, 6, 0, "east")
    # lanterns: under the end bays' outer joists; one in every gallery under the ridge
    for i, (_, a, b) in enumerate(bays):
        posts, _ = panels(a, b)
        if i == 0:
            lantern(c, posts[0], 7, 0)
        if i == len(bays) - 1:
            lantern(c, posts[1], 7, 0)
        lantern(c, (a + b) // 2 + (1 if (a + b) // 2 >= L // 2 else 0), 11, 2)
    # stores at the inner foot of the end bays
    for side in (0, 1):
        X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
        c.put(X(END + 1), 1, 4, "barrel", facing="up", open=False)
        c.put(X(END + 2), 1, 4, "barrel", facing="up", open=False)
        c.put(X(END + 2), 2, 4, "barrel", facing="up", open=False)
        for i in (END + 5, END + 6):
            log(c, X(i), 1, 4, "x", wood="spruce")
        log(c, X(END + 5), 2, 4, "x", wood="spruce")
    return c


def bay(c, a, b):
    posts, pans = panels(a, b)
    for x in range(a, b + 1):
        # two-step rubble talus
        c.put(x, 1, 0, rubble(x, 1, 0))
        stairs(c, x, 2, 0, rubble_stair(x, 2, 0), "south")
        for y in range(1, 5):
            c.put(x, y, 1, rubble(x, y, 1) if y <= 2 else ashlar(x, y, 1))
        stairs(c, x, 5, 1, ashlar_stair(x, 5, 1), "south")
        # gallery floor
        if x in posts:
            log(c, x, 8, 0, "z")
            log(c, x, 8, 1, "z")
            stairs(c, x, 7, 1, "dark_oak", "south", half="top")  # bracket under the joist
        else:
            c.put(x, 8, 1, "spruce_planks")
            slab(c, x, 8, 0, "spruce", "top")
        # front: posts and boarding, loopholes at y10
        if x in posts:
            log(c, x, 9, 0, "y")
            log(c, x, 10, 0, "y")
        else:
            c.put(x, 9, 0, "spruce_planks")
            c.put(x, 10, 0, "spruce_planks")
        # roof: low dark-oak gable over z0..4
        stairs(c, x, 11, 0, "dark_oak", "south")
        stairs(c, x, 12, 1, "dark_oak", "south")
        slab(c, x, 12, 2, "dark_oak", "bottom")
        stairs(c, x, 12, 3, "dark_oak", "north")
        stairs(c, x, 11, 4, "dark_oak", "north")
        # inside: edge beam, rail, posts; battered foot
        log(c, x, 8, 4, "x")
        if x in posts:
            log(c, x, 9, 4, "y")
            log(c, x, 10, 4, "y")
            stairs(c, x, 7, 4, "dark_oak", "north", half="top")
        else:
            c.put(x, 9, 4, "spruce_fence")
        stairs(c, x, 1, 4, rubble_stair(x, 1, 4), "north")
    for lo, hi in pans:
        for x in centres(lo, hi):
            del c[(x, 10, 0)]  # loophole
            trap(c, x, 8, 0, "spruce", "north", False, half="top")  # murder-hole hatch in the floor
    # gallery floor is open at z1..3 y9..11 (air): nothing to place


def pier(c, a, b, end, L):
    cx = (a + b) // 2
    for x in range(a, b + 1):
        for z in (0, 1, 4):
            for y in range(1, 9):
                c.put(x, y, z, rubble(x, y, z) if y <= 2 else ashlar(x, y, z))
        if x in (0, L - 1):  # clean abutment edge
            for y in range(1, 9):
                c.put(x, y, 0, "stone_bricks")
        c.put(x, 8, 1, "stone_bricks")
        c.put(x, 9, 0, "stone_bricks" if noise(x, 9, 7, 1) else "cracked_stone_bricks")
        if end or x != cx:
            for y in (10, 11, 12):
                c.put(x, y, 0, ashlar(x, y, 0) if y < 12 else "stone_bricks")
    if not end:
        # blind cross loop (2 deep, the curtain behind is solid)
        for y in (4, 5, 6):
            del c[(cx, y, 0)]
            del c[(cx, y, 1)]
        del c[(cx - 1, 5, 0)]
        del c[(cx + 1, 5, 0)]
        # chamfered cap of the two merlons
        stairs(c, a, 12, 0, "stone_brick", "east")
        stairs(c, b, 12, 0, "stone_brick", "west")


def mw86():
    return build(86)


def mw31():
    return build(31)
