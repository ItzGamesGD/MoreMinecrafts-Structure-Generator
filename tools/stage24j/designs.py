"""Stage 24-J watchtower alternatives (proposals only; the approved Stage 24-F NBTs are never written).

Every variant starts from the approved restored NBT, keeps the template size (so the piece box, jigsaw placement and
collision behaviour are unchanged), keeps every jigsaw and block entity (the kit raises on any edit), keeps the ladder
shaft below the deck, and is written to artifacts/.../stage-24j/proposals/<module>/<variant>/candidate.nbt.

large_pillar_1 (6 x 15 x 6). Current top: 4x4 shaft -> 6x6 corbelled cap (y13) under a solid 6x6 slab (y14) with a
  ladder hatch; the player stands ON the slab (feet y15, outside the template) with no railing.
  A  open lookout:   the slab becomes a railed parapet (walls between chiseled corner merlons); the corbelled cap at y13
                     is the deck floor (feet y14). Reads as an open platform; same outline height.
  B  roofed belvedere: the 6x6 floor drops to y10 (corbel ring copied from the y13 cap); waist railing at y11, a
                     two-block open viewing band (y12-y13) between polished-basalt corner posts, low tiled roof with stair
                     eaves at y14; the basalt ladder spine continues to the roof as a central post. Weather shelter with a
                     360-degree view; the deck and its headroom lie inside the template.
medium_pillar_1 (7 x 11 x 8). Current top: 5x6 deck (y8) with a wall parapet (y9) and loose vanilla deepslate fragments
  projecting west, east, north and as a floating arm at y10.
  A  corbelled crown: fragments removed; a corbel ring on the free footprint ring (x0/x6, z0/z7) widens the deck to 7x8;
                     wall parapet on the outer ring with two-block corner merlons; one corner merlon left broken.
  B  south-west gallery: fragments removed except the idea of the west/south projection, which becomes a cantilevered
                     L-shaped gallery (corbels on x0 and z7 only); north and east keep the existing parapet; a two-block
                     corner post marks the south-west corner. Deliberately asymmetric.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import load_nbt  # noqa: E402
from tools.stage24e.kit import Variant, stair, with_props, mc, AIR  # noqa: E402
from tools.stage24g.build import write_nbt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
BASALT = "polished_basalt[axis=y]"
CHIS = "chiseled_deepslate"
POL = "polished_deepslate"
TILES = "deepslate_tiles"


def wall(mat="polished_deepslate_wall"):
    return with_props(mat, {"east": "none", "north": "none", "south": "none", "west": "none", "up": "true", "waterlogged": "false"})


def lantern(hanging):
    return with_props("soul_lantern", {"hanging": "true" if hanging else "false", "waterlogged": "false"})


class Tower(Variant):
    """Variant with explicit-air support: deck and headroom cells are stored as air so they stay clear when buried."""

    def __init__(self, module, variant, title, **meta):
        super().__init__(module, variant, title, src=D24F / module / "restored.nbt")
        self.meta = meta  # ladder column, deck level, viewing notes for the checks and renders

    def save(self, path: Path):
        super().save(path)
        write_nbt(load_nbt(path), path)   # deterministic gzip (mtime 0): rebuilds are byte-identical
        return path

    def air(self, p):
        p = tuple(p)
        if p in self.locked:
            raise ValueError(f"protected block at {p}")
        self.blocks[p] = AIR

    def ring(self, sx, sz, x0=0, z0=0):
        for x in range(x0, x0 + sx):
            for z in range(z0, z0 + sz):
                if x in (x0, x0 + sx - 1) or z in (z0, z0 + sz - 1):
                    yield x, z


def inward(x, z, x0, x1, z0, z1):
    if x == x0:
        return "east"
    if x == x1:
        return "west"
    if z == z0:
        return "south"
    return "north"


# --------------------------------------------------------------------------------------------- large_pillar_1
def large_current():
    return Tower("large_pillar_1", "current", "Current — Stage 24-F approved", ladder=(2, 2), ladder_top=13, deck_y=15,
                 deck=[(x, z) for x in range(6) for z in range(6) if not (2 <= x <= 3 and 2 <= z <= 3)])


def large_a():
    v = Tower("large_pillar_1", "A", "Open lookout — railed parapet on the corbelled cap", ladder=(2, 2), ladder_top=13, deck_y=14,
              deck=[(x, z) for x in range(1, 5) for z in range(1, 5) if (x, z) != (2, 2)])
    for x in range(6):
        for z in range(6):
            v.air((x, 14, z))
    for x, z in v.ring(6, 6):
        corner = x in (0, 5) and z in (0, 5)
        v.set((x, 14, z), CHIS if corner else wall())
    # deck floor: polished deepslate inside the corbel ring (ladder hatch kept)
    for x in range(1, 5):
        for z in range(1, 5):
            if (x, z) != (2, 2):
                v.set((x, 13, z), POL)
    v.notes.append("deck feet y14 (was y15); head cell y15 is above the template, as before (one block lower than today)")
    return v


def large_b():
    v = Tower("large_pillar_1", "B", "Roofed belvedere — two-block open viewing band under a low tiled roof", ladder=(2, 2), ladder_top=10,
              deck_y=11, deck=[(x, z) for x in range(1, 5) for z in range(1, 5) if (x, z) not in ((2, 2), (3, 2))])
    cap = {(x, z): v.get((x, 13, z)) for x, z in v.ring(6, 6)}   # corbel stairs of the approved cap
    for y in range(10, 15):
        for x in range(6):
            for z in range(6):
                v.air((x, y, z))
    # floor y10: corbel ring + polished deepslate deck; ladder hatch and basalt spine kept
    for (x, z), st in cap.items():
        v.set((x, 10, z), st)
    for x in range(1, 5):
        for z in range(1, 5):
            v.set((x, 10, z), POL)
    v.set((2, 10, 2), v.get((2, 9, 2)))      # ladder continues into the hatch
    v.set((3, 10, 2), BASALT)
    # y11 waist railing between chiseled corner bases; y12-y13 open band between polished-basalt corner posts
    for x, z in v.ring(6, 6):
        corner = x in (0, 5) and z in (0, 5)
        v.set((x, 11, z), CHIS if corner else wall())
        if corner:
            v.set((x, 12, z), BASALT)
            v.set((x, 13, z), BASALT)
    for y in (11, 12, 13):                   # the ladder spine continues to the roof as its central post
        v.set((3, y, 2), BASALT)
    for x, z in ((1, 1), (4, 1), (1, 4), (4, 4)):
        v.set((x, 13, z), lantern(True))     # above head height (feet y11, head y12)
    # roof y14: stair eaves rising inward, tiled centre
    for x, z in v.ring(6, 6):
        v.set((x, 14, z), stair(inward(x, z, 0, 5, 0, 5), "bottom"))
    for x in range(1, 5):
        for z in range(1, 5):
            v.set((x, 14, z), TILES)
    v.notes.append("deck feet y11, head y12, lanterns y13, roof y14: the deck and its headroom are inside the template")
    v.notes.append("shaft masonry ends at y9 (was y12); the approved y13 corbel ring is reused under the y10 deck")
    return v


# -------------------------------------------------------------------------------------------- medium_pillar_1
FRAGMENTS = [(0, 9, 3), (0, 9, 4), (0, 9, 5), (0, 9, 6), (6, 9, 3), (6, 9, 4), (3, 9, 0), (6, 10, 3), (0, 10, 5), (0, 10, 6),
             (0, 10, 7), (1, 10, 7), (2, 10, 7)]


def medium_current():
    return Tower("medium_pillar_1", "current", "Current — Stage 24-F approved", ladder=(4, 3), ladder_top=8, deck_y=9,
                 deck=[(x, z) for x in range(2, 5) for z in range(2, 6) if (x, z) != (4, 3)])


def _strip_fragments(v):
    for p in FRAGMENTS:
        v.clear(p)


def medium_a():
    v = Tower("medium_pillar_1", "A", "Corbelled crown — full-width deck, corner merlons, one broken merlon", ladder=(4, 3), ladder_top=8,
              deck_y=9, deck=[(x, z) for x in range(1, 6) for z in range(1, 7) if (x, z) != (4, 3)])
    _strip_fragments(v)
    for x, z in v.ring(7, 8):
        v.set((x, 8, z), stair(inward(x, z, 0, 6, 0, 7), "top"))
    for x, z in v.ring(5, 6, 1, 1):          # old parapet line becomes deck
        v.air((x, 9, z))
        v.air((x, 10, z))
    for x, z in v.ring(7, 8):
        corner = x in (0, 6) and z in (0, 7)
        v.set((x, 9, z), CHIS if corner else wall())
        if corner and (x, z) != (0, 7):
            v.set((x, 10, z), POL)
    v.set((0, 9, 7), "cracked_deepslate_bricks")   # the broken south-west merlon
    v.notes.append("deck 7x8 outline, 29 standable cells (was 11); parapet on corbels over the free footprint ring")
    return v


def medium_b():
    deck = [(x, z) for x in range(1, 5) for z in range(2, 7) if (x, z) != (4, 3)]
    v = Tower("medium_pillar_1", "B", "South-west gallery — cantilevered L-shaped deck, corner post", ladder=(4, 3), ladder_top=8,
              deck_y=9, deck=deck)
    _strip_fragments(v)
    west = [(0, z) for z in range(1, 8)]
    south = [(x, 7) for x in range(1, 6)]
    for x, z in west:
        v.set((x, 8, z), stair("east", "top"))
    for x, z in south:
        v.set((x, 8, z), stair("north", "top"))
    for x, z in deck:                        # old west/south parapet becomes deck
        v.air((x, 9, z))
        v.air((x, 10, z))
    for x, z in west + south:
        v.set((x, 9, z), wall())
    v.set((5, 9, 7), wall())
    v.set((5, 8, 7), stair("north", "top"))
    v.set((0, 9, 7), CHIS)                   # south-west corner post
    v.set((0, 10, 7), POL)
    v.set((0, 9, 1), CHIS)                   # north-west junction with the existing parapet
    v.notes.append("deck 4x5 (19 standable cells, was 11) extended over corbels on the west and south sides only")
    return v


DESIGNS = {"large_pillar_1": [large_current, large_a, large_b], "medium_pillar_1": [medium_current, medium_a, medium_b]}


def build(out_root: Path):
    res = {}
    for m, fs in DESIGNS.items():
        for f in fs:
            v = f()
            if v.variant != "current":
                v.finish()
                v.save(out_root / m / v.variant / "candidate.nbt")
            res[(m, v.variant)] = v
    return res
