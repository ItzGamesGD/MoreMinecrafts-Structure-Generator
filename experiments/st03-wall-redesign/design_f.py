"""Design F - final perimeter wall, designed from scratch (does not continue A, B, C or B2).

Idea: a stone frame with timber set inside it. Every bay of the wall is a stone frame:
- 2-wide stone piers at the sides, rising one course above the parapet;
- a weathered plinth below;
- a corbel course and a crenellated parapet above.

Inside the frame, one block deeper, sits a dark-oak timber frame: posts against the piers, knee braces, and a beam
that carries the wall head. One block deeper again is a rough rubble infill with the arrow loop. So the face reads in
three depths, from the outside in: stone frame, timber frame, infill. The timber does structural work (it carries the
corbelled parapet) and harmonises with the half-timbered dark-oak / spruce buildings of the compound.

On the compound side, stone pilasters answer the piers. Between them a dark-oak beam on braces carries a plank
widening of the wall-walk behind a fence rail.

Planes (local z): 0 piers, plinth, corbels, parapet | 1 timber frame | 2 infill | 3 core | 4 inside pilasters and
timber walk edge.
Heights: y0 footing; y1-3 plinth; y4-7 posts and infill; y8 beam; y9 corbel and deck (feet y10); y10 breastwork;
y11 merlons; y12 pier and end merlons.
"""

from common import D, H, Cells, ashlar, banner, footing, lantern, log, noise, rubble, rubble_stair, slab, stairs

# piers between bays: ("pier", w) is a stone pier rising above the parapet, ("post", w) a timber post that pairs the
# two bays beside it into one wide timber frame
LAYOUT = {86: dict(end=8, bay=7, piers=[("post", 2), ("pier", 2)] * 3 + [("post", 2)]),
          31: dict(end=7, bay=7, piers=[("post", 3)])}


def layout(L):
    spec = LAYOUT[L]
    out, x = [("end", 0, spec["end"] - 1)], spec["end"]
    for i, p in enumerate(spec["piers"] + [None]):
        out.append(("bay", x, x + spec["bay"] - 1))
        x += spec["bay"]
        if p:
            out.append((p[0], x, x + p[1] - 1))
            x += p[1]
    out.append(("end", x, x + spec["end"] - 1))
    assert x + spec["end"] == L, (L, x)
    return out


def infill(x, y, z):
    """Rough rubble infill in coursed patches: cobble, andesite and stone, mossy cobble low down."""
    patch = noise((x + 2 * (y // 2)) // 3, y // 2, 5, 61 + z)
    r = noise(x, y, 5, 23 + z)
    v = [("cobblestone", "andesite"), ("andesite", "stone"), ("cobblestone", "stone"),
         ("cobblestone", "mossy_cobblestone"), ("stone", "cobblestone")][patch][0 if r else 1]
    return v if y <= 4 or not v.startswith("mossy") else "cobblestone"


def edge(x, y, z):
    """Pier and quoin masonry: clean stone brick with sparse cracked / mossy (low) blocks."""
    n = noise(x, y, 13, 7 + z)
    if n == 0:
        return "cracked_stone_bricks"
    if n == 1 and y <= 3:
        return "mossy_stone_bricks"
    return "stone_bricks"


def build(L):
    c = Cells((L, H, D))
    footing(c, L)
    parts = layout(L)
    for x in range(L):  # core, deck and plinth everywhere; segments cut into it
        for y in range(1, 9):
            for z in (1, 2, 3):
                c.put(x, y, z, rubble(x, y, z) if y <= 2 else ashlar(x, y, z))
        for z in (1, 2, 3):
            c.put(x, 9, z, "stone_bricks")
        c.put(x, 1, 0, edge(x, 1, 0) if noise(x, 1, 4, 5) else rubble(x, 1, 0))
        stairs(c, x, 1, 4, rubble_stair(x, 1, 4), "north")
    bays = [p for p in parts if p[0] == "bay"]
    for kind, a, b in parts:
        {"end": end_mass, "pier": pier, "post": post, "bay": bay}[kind](c, a, b, L)
    dress(c, parts, bays, L)
    return c


# ----------------------------------------------------------------------------------------------------------- bay
def bay(c, a, b, L):
    m = (a + b) // 2
    for x in range(a, b + 1):
        # outside: a three-course stone plinth with a weathered sill, then the timber panel up to the corbel course
        c.put(x, 1, 0, edge(x, 1, 0))
        c.put(x, 2, 0, edge(x, 2, 0))
        stairs(c, x, 3, 0, "stone_brick", "south")
        stairs(c, x, 9, 0, "stone_brick", "south", half="top")  # corbel course carrying the parapet
        c.put(x, 10, 0, edge(x, 10, 0))  # breastwork
        if (x - a) % 3:
            c.put(x, 11, 0, edge(x, 11, 0))  # merlons; crenels at the bay ends and centre
        # timber frame at z1: posts at the bay ends, beam over the full bay
        for y in range(4, 8):
            if x in (a, b):
                log(c, x, y, 1, "y")
            else:
                del c[(x, y, 1)]
        log(c, x, 8, 1, "x")
        # rubble infill at z2
        for y in range(4, 8):
            c.put(x, y, 2, infill(x, y, 2))
        # inside: timber beam carrying the plank walk widening, fence rail
        log(c, x, 8, 4, "x")
        c.put(x, 9, 4, "spruce_planks")
        c.put(x, 10, 4, "dark_oak_fence")
    stairs(c, a + 1, 7, 1, "dark_oak", "west", half="top")  # knee braces under the beam
    stairs(c, b - 1, 7, 1, "dark_oak", "east", half="top")
    stairs(c, a, 7, 4, "dark_oak", "west", half="top")
    stairs(c, b, 7, 4, "dark_oak", "east", half="top")
    # arrow loop in the infill: 2 high in the outer face, 1 high through the core (not a passage)
    del c[(m, 5, 2)]
    del c[(m, 6, 2)]
    del c[(m, 5, 3)]


# ---------------------------------------------------------------------------------------------------------- pier
def pier(c, a, b, L):
    for x in range(a, b + 1):
        for y in range(1, 10):
            c.put(x, y, 0, "chiseled_stone_bricks" if y == 8 else edge(x, y, 0))
        for y in (10, 11, 12):
            c.put(x, y, 0, edge(x, y, 0))
        for y in range(2, 9):  # inside pilaster
            c.put(x, y, 4, "chiseled_stone_bricks" if y == 8 else edge(x, y, 4))
        c.put(x, 9, 4, "stone_bricks")
        c.put(x, 10, 4, "stone_brick_wall")


def post(c, a, b, L):
    """Timber post pairing two bays into one wide frame: the stone frame (plinth, corbel, parapet) runs through, the
    dark-oak post stands at z1 on the plinth under the continuous beam, and a twin post carries the inside walk beam."""
    for x in range(a, b + 1):
        c.put(x, 1, 0, edge(x, 1, 0))
        c.put(x, 2, 0, edge(x, 2, 0))
        stairs(c, x, 3, 0, "stone_brick", "south")
        stairs(c, x, 9, 0, "stone_brick", "south", half="top")
        c.put(x, 10, 0, edge(x, 10, 0))
        c.put(x, 11, 0, edge(x, 11, 0))
        for y in range(4, 8):
            log(c, x, y, 1, "y")
            c.put(x, y, 2, infill(x, y, 2))
        log(c, x, 8, 1, "x")
        for y in range(2, 8):
            log(c, x, y, 4, "y")
        log(c, x, 8, 4, "x")
        c.put(x, 9, 4, "spruce_planks")
        c.put(x, 10, 4, "dark_oak_fence")


# ------------------------------------------------------------------------------------------------------ end mass
def end_mass(c, a, b, L):
    """Solid abutment toward the tower / gate: plain stone to y12 at the front with a crenel pair in its parapet. The
    abutting column (x=0 or x=L-1) is clean stone brick over the full section."""
    for x in range(a, b + 1):
        for y in range(1, 13):
            c.put(x, y, 0, edge(x, y, 0))
        for y in range(2, 9):
            c.put(x, y, 4, edge(x, y, 4))
        c.put(x, 9, 4, "stone_bricks")
        c.put(x, 10, 4, "stone_brick_wall")
    abut = 0 if a == 0 else b
    for z in range(4):
        for y in range(1, 10):
            c.put(abut, y, z, "stone_bricks")
    mid = (a + b) / 2
    for x in range(a + 1, b):
        if abs(x - mid) < 1:
            del c[(x, 12, 0)]


# ---------------------------------------------------------------------------------------------------- dressing
def dress(c, parts, bays, L):
    """Lanterns hang from the beam in the end bays only (toward the towers / gate), outside and inside. A banner hangs
    on the central post of each end frame. Barrels and a log pile sit at the inner foot near the ends."""
    n = len(bays)
    for i in (0, n - 1):
        _, a, b = bays[i]
        lantern(c, (a + b) // 2, 7, 1)
        lantern(c, (a + b) // 2, 7, 4)
    posts = [(a, b) for k, a, b in parts if k == "post"]
    for j, (a, b) in enumerate((posts[0], posts[-1]) if len(posts) > 1 else posts):
        x = (a + b) // 2 if (b - a) % 2 == 0 else (a if j == 0 else b)
        banner(c, x, 7, 0, "north")
    E = LAYOUT[L]["end"]
    for side in (0, 1):
        X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
        c.put(X(E + 1), 1, 4, "barrel", facing="up", open=False)
        c.put(X(E + 2), 1, 4, "barrel", facing="up", open=False)
        c.put(X(E + 1), 2, 4, "barrel", facing="up", open=False)
        for i in (E + 4, E + 5):
            log(c, X(i), 1, 4, "x", wood="spruce")


def mw86():
    return build(86)


def mw31():
    return build(31)
