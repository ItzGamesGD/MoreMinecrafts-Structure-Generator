"""Design B2 - "Hoarded wall, revised": a buttressed stone curtain that visibly carries short timber hoardings.

Starts from prototype B (stone below, timber fighting gallery above) and keeps its character: a dark-oak / spruce
hoarding projecting from the wall head over stone. What changes is the stone, the proportions, and the way the two
meet.

Stone (the weak part of B):
- Three-stage batter at the foot (footing y0, rubble block y1, rubble stair y2).
- A three-plane face: buttress ribs and pilasters z0 > wall frame z1 > recessed field z2. The ribs taper: 3 wide at
  the foot, 1 wide above y4. Each bay has a recessed field (y4-6) under a chamfered lintel, with two arrow loops.
  The loops are 2 high on the outside and 1 high through the core, so they are not a passage.
- A stone corbel course (upside-down stairs) runs under every parapet and every hoarding.
- End masses (6 wide) are corbelled, crowned and solid, with a banner niche.

Timber (B's character, shorter and lighter):
- Hoardings are 6 wide and 2 deep (B: 12 wide, 5 deep, a gable roof over the full wall thickness). They alternate with
  open stone-crenellated bays and sit at both ends of every module, which is where Q90 wants timber.
- Each hoarding is carried by a stone corbel course, stone pilasters under its two stone cheek walls, and dark-oak
  joists whose log ends show at the front. The roof is a one-sided pent roof falling to the outside: two stairs, no
  ridge, so it does not read as a hut.
- Inside, the box opens onto the wall-walk through a post-and-beam portal.

Planes (local z): 0 ribs / talus / corbels / parapet / hoarding front, 1 wall frame, 2..3 core and recessed field,
4 inside plinth and ribs. Heights: y0 footing, deck y8 (feet y9), sill y9, merlons y10..11, caps y12.
"""

from common import (D, H, Cells, ashlar, ashlar_stair, banner, footing, lantern, log, noise, rubble, rubble_stair,
                    slab, stairs, trap)

E, P, W = 6, 3, 8  # end mass, pier, bay widths: identical in MW86 (7 bays) and MW31 (2 bays)
BAYS = {86: "HSHSHSH", 31: "HH"}  # H hoarding bay, S open stone bay; every module is H at both ends


def layout(L):
    types = BAYS[L]
    out, x = [("end", 0, E - 1)], E
    for i, t in enumerate(types):
        out.append(("bay" + t, x, x + W - 1))
        x += W
        if i < len(types) - 1:
            out.append(("pier", x, x + P - 1))
            x += P
    out.append(("end", x, x + E - 1))
    assert x + E == L, (L, x)
    return out


def sb(x, y, z):
    return "stone_bricks" if noise(x, y, 11, z + 3) else "cracked_stone_bricks"


def build(L):
    c = Cells((L, H, D))
    footing(c, L)
    parts = layout(L)
    for x in range(L):
        c.put(x, 1, 0, rubble(x, 1, 0))  # talus
        stairs(c, x, 2, 0, rubble_stair(x, 2, 0), "south")
        for y in range(1, 8):  # curtain z1..3
            for z in (1, 2, 3):
                c.put(x, y, z, rubble(x, y, z) if y <= 2 else ashlar(x, y, z))
        for z in (1, 2, 3):  # deck
            c.put(x, 8, z, "stone_bricks")
        stairs(c, x, 1, 4, rubble_stair(x, 1, 4), "north")  # inside plinth
    boxes, cheeks = set(), set()
    for kind, a, b in parts:
        if kind == "end":
            end_mass(c, a, b)
        elif kind == "pier":
            pier(c, a, b)
        else:
            bay(c, a, b, kind == "bayH")
            if kind == "bayH":
                boxes |= set(range(a, b + 1))
    ends = {x for k, a, b in parts if k == "end" for x in range(a, b + 1)}
    parapet(c, L, parts, ends | boxes)
    for kind, a, b in parts:
        if kind == "bayH":
            hoarding(c, a, b)
    # inside lip: stone wall behind the parapet, timber fence behind the hoardings
    for x in range(E, L - E):
        c.put(x, 9, 3, "dark_oak_fence" if x in boxes else "stone_brick_wall")
    decoration(c, parts, L)
    return c


# ------------------------------------------------------------------------------------------------------- piers
def pier(c, a, b):
    """Tapering buttress rib (z0) and its inside twin (z4)."""
    m = (a + b) // 2
    for x in range(a, b + 1):
        for z in (0, 4):
            for y in ((1, 2, 3) if z == 0 else (2, 3)):
                c.put(x, y, z, rubble(x, y, z) if y <= 2 else ashlar(x, y, z))
            if x == m:
                for y in (4, 5, 6, 7):
                    c.put(x, y, z, ashlar(x, y, z))
            else:
                stairs(c, x, 4, z, ashlar_stair(x, 4, z), "east" if x < m else "west")


# -------------------------------------------------------------------------------------------------------- bays
def bay(c, a, b, hoard):
    """Two recessed niches outside (a+1..a+2, b-2..b-1; y4..6, z1 removed) with an arrow loop each, a plain pilaster
    between them, and an inside pilaster at z4 behind it."""
    for lo in (a + 1, b - 2):
        for x in (lo, lo + 1):
            for y in (4, 5, 6):
                del c[(x, y, 1)]
            if not hoard:
                stairs(c, x, 7, 1, ashlar_stair(x, 7, 1), "south", half="top")  # chamfered lintel
    for x in (a + 2, b - 2):  # loops: 2 high on the outside (z2), 1 high through the core (z3)
        del c[(x, 5, 2)]
        del c[(x, 6, 2)]
        del c[(x, 5, 3)]
    for x in (a + 3, b - 3):  # inside pilaster answering the outside pilaster, with a dark-oak capital
        for y in (2, 3, 4, 5, 6):
            c.put(x, y, 4, rubble(x, y, 4) if y <= 2 else ashlar(x, y, 4))
        stairs(c, x, 7, 4, "dark_oak", "north", half="top")


def hoarding(c, a, b):
    """Eight-wide, two-deep hoarding filling the bay. Its floor is y7 (a step below the wall-walk), carried by a stone
    corbel course (y6), the stone ribs of the adjacent piers and dark-oak joists with their log ends at the front."""
    h = list(range(a, b + 1))
    posts = (a, a + 3, a + 4, b)
    for i, x in enumerate(h):
        if x in posts:  # dark-oak bracket under each joist, stone corbel stairs between
            stairs(c, x, 6, 0, "dark_oak", "south", half="top")
        else:
            stairs(c, x, 6, 0, "stone_brick", "south", half="top")
        del c[(x, 8, 1)]  # the box interior replaces the deck at z1
        if x in posts:  # joists
            log(c, x, 7, 0, "z")
            log(c, x, 7, 1, "z")
        else:
            if x in (a + 2, b - 2):
                trap(c, x, 7, 0, "spruce", "north", False, half="top")  # murder-hole hatch
            else:
                slab(c, x, 7, 0, "spruce", "top")
            c.put(x, 7, 1, "spruce_planks")
        if x in posts:  # front posts
            for y in (8, 9, 10):
                log(c, x, y, 0, "y")
        else:
            c.put(x, 8, 0, "spruce_planks")
            if x not in (a + 1, a + 2, b - 2, b - 1):
                c.put(x, 9, 0, "spruce_planks")  # loophole row stays open in the two panels
            c.put(x, 10, 0, "spruce_planks")
        stairs(c, x, 11, 0, "dark_oak", "south")  # pent roof falling to the outside
        stairs(c, x, 12, 1, "dark_oak", "south")
        log(c, x, 11, 1, "x")  # beam under the high edge
    for x in (a, b):  # rear posts of the portal onto the wall-walk
        for y in (8, 9, 10):
            log(c, x, y, 1, "y")


# ---------------------------------------------------------------------------------------------- end masses
def end_mass(c, a, b):
    m_lo, m_hi = (a + b) // 2, (a + b) // 2 + 1
    for x in range(a, b + 1):
        for y in (1, 2):
            c.put(x, y, 0, rubble(x, y, 0))
        stairs(c, x, 3, 0, ashlar_stair(x, 3, 0), "south")
        stairs(c, x, 7, 0, "stone_brick", "south", half="top")  # crown corbel
        for y in (8, 9, 10, 11):
            for z in range(4):
                c.put(x, y, z, "stone_bricks" if y == 8 else ashlar(x, y, z))
        for z in range(4):  # chamfered cap: stairs lean to the centre, full blocks in the middle
            if z in (0, 3) or x in (a, b):
                face = "south" if z == 0 else "north" if z == 3 else "east" if x == a else "west"
                stairs(c, x, 12, z, "stone_brick", face)
            else:
                c.put(x, 12, z, "stone_bricks")
    for x in (m_lo, m_hi):  # banner niche: the shaft face steps back from z1 to z2
        for y in (4, 5, 6):
            del c[(x, y, 1)]
    edge = 0 if a == 0 else b  # clean abutment edge: a 1-wide jamb in the z0 plane over the full height
    for y in range(1, 9):
        c.put(edge, y, 0, "stone_bricks")


# --------------------------------------------------------------------------------------------------- parapet
def parapet(c, L, parts, skip):
    """Stone parapet set back to z1 (the hoardings project in front of it at z0): a moulding of upside-down stairs at
    z0 y8, sill y9, merlons y10..11 and caps y12. Each open bay together with its two piers (14 columns) reads
    M M C M M C M M C M M C M M, symmetric; the piers are no taller than the bay."""
    crenel = set()
    for i, (kind, a, b) in enumerate(parts):
        if kind == "bayS":
            lo = a - P  # the pier before the bay
            crenel |= {lo + 2, lo + 5, lo + 8, lo + 11}
    for x in range(L):
        if x in skip:
            continue
        stairs(c, x, 8, 0, "stone_brick", "south", half="top")
        c.put(x, 9, 1, sb(x, 9, 1))
        if x in crenel:
            continue
        c.put(x, 10, 1, ashlar(x, 10, 1))
        c.put(x, 11, 1, ashlar(x, 11, 1))
        stairs(c, x, 12, 1, "stone_brick", "south")


# ---------------------------------------------------------------------------------------------- decoration
def decoration(c, parts, L):
    """Q90: military dressing concentrated at the ends (lantern in the end hoardings, banners in the end niches,
    barrels and a log pile at the inner foot), restrained in the middle (two banners on pier ribs on MW86)."""
    ends = [(a, b) for k, a, b in parts if k == "end"]
    for a, b in ends:  # banners in the niches
        for x in ((a + b) // 2, (a + b) // 2 + 1):
            banner(c, x, 6, 1, "north")
    bays = [(a, b) for k, a, b in parts if k == "bayH"]
    first, last = bays[0], bays[-1]
    lantern(c, first[0] + 3, 10, 1)  # hanging from the beam inside the end hoardings
    lantern(c, last[0] + 4, 10, 1)
    piers = [(a, b) for k, a, b in parts if k == "pier"]
    if L == 86:  # irregular banners on two inner pier ribs
        a, b = piers[1]
        banner(c, a, 6, 0, "west")
        a, b = piers[4]
        banner(c, b, 6, 0, "east")
    for side in (0, 1):  # stores at the inner foot of the ends
        X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
        c.put(X(E + 1), 1, 4, "barrel", facing="up", open=False)
        c.put(X(E + 2), 1, 4, "barrel", facing="up", open=False)
        c.put(X(E + 2), 2, 4, "barrel", facing="up", open=False)
        for i in (E + 5, E + 6):
            log(c, X(i), 1, 4, "x", wood="spruce")
        log(c, X(E + 5), 2, 4, "x", wood="spruce")


def mw86():
    return build(86)


def mw31():
    return build(31)
