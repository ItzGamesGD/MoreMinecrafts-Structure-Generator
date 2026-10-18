"""SG-03 Family B: large upper-level rooms (above the lower band, entered from the elevated galleries).

Footprints stay within the SG-02 reserved upper volume (23 wide, 17 tall, 32 deep, entry centred on
the south edge, floor at y=0). Each builder returns ``(grid, block_entities)``.

Stair rule used throughout: a run of stairs whose last step is at cell height ``y`` meets a floor
whose *block* is at the same cell height ``y`` (the stair back is flush with that floor's top).
"""

from __future__ import annotations

from kingdom_common import UPPER_DOOR, UPPER_ENTRY
from rooms_common import Room

LOOT_HALL = "minecraft:chests/simple_dungeon"
LOOT_BARRACKS = "minecraft:chests/abandoned_mineshaft"
LOOT_TRIAL = "minecraft:chests/trial_chambers/corridor"


def _materials(r: Room):
    wall = r.weighted(("deepslate_bricks", 66), ("cracked_deepslate_bricks", 14), ("deepslate_tiles", 8), ("tuff_bricks", 12))
    floor = r.weighted(("deepslate_tiles", 58), ("cracked_deepslate_tiles", 14), ("polished_deepslate", 18), ("tuff_bricks", 10))
    roof = r.weighted(("deepslate_tiles", 76), ("cracked_deepslate_tiles", 10), ("tuff_bricks", 14))
    return wall, floor, roof


def _cobwebs(r: Room, cells) -> None:
    for cell in cells:
        r.put(*cell, "cobweb")


def _rubble(r: Room, x0: int, x1: int, z0: int, z1: int, peak: int, base_y: int = 1) -> None:
    """A deterministic collapse mound that falls off toward its edges."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    span = max(x1 - x0, z1 - z0) / 2 + 0.5
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            dist = max(abs(x - cx), abs(z - cz))
            height = int(round(peak * (1 - dist / span))) + r.rng.choice((-1, 0, 0, 1))
            for y in range(base_y, base_y + max(height, 0)):
                r.put(x, y, z, r.weighted(("cobbled_deepslate", 70), ("deepslate_bricks", 15), ("cracked_deepslate_bricks", 15)))
            if height >= 1 and r.rng.random() < 0.5:
                r.slab(x, base_y + height, z, "cobbled_deepslate_slab")


# --- B1: grand hall -----------------------------------------------------------------------------
GALLERY_Y = 6


def grand_hall():
    """23x17x31. Nave and aisles under high vaults, arcaded colonnades, side galleries, a three-tier dais."""
    r = Room((23, 17, 31), seed=4101)
    w, h, d = r.size
    wall, floor, roof = _materials(r)
    r.shell(floor=floor, wall=wall, roof=roof, band=(7, "polished_deepslate"))
    r.door(*UPPER_DOOR, UPPER_ENTRY)
    r.trim_door(*UPPER_DOOR, jamb="chiseled_tuff_bricks", lintel="chiseled_tuff_bricks")

    # Nave floor stripe.
    for z in range(1, d - 1):
        for x in range(9, 14):
            r.put(x, 0, z, "polished_deepslate" if (z // 2) % 2 == 0 else "tuff_bricks")

    # Colonnades: 2x2 piers at x=6..7 and x=15..16, z = 4..5, 10..11, 16..17, 22..23, joined by arcades.
    piers = (4, 10, 16, 22)
    for z0 in piers:
        for x0 in (6, 15):
            r.pillar(x0, z0, x0 + 1, z0 + 1, 1, 12)
    for x0 in (6, 15):
        for a, b in zip(piers, piers[1:]):
            z0, z1 = a + 2, b - 1
            r.fill(x0, 9, z0, x0 + 1, 11, z1, "deepslate_bricks")
            r.clear(x0, 1, z0, x0 + 1, 8, z1)
            for xx in (x0, x0 + 1):
                r.arch_z(z0, z1, xx, 9)
        r.fill(x0, 12, 4, x0 + 1, 12, 23, "chiseled_tuff_bricks")
        r.fill(x0, 13, 4, x0 + 1, 15, 23, "deepslate_bricks")
        for zc in (7, 13, 19):  # clerestory windows glazed with bars
            r.clear(x0, 13, zc, x0 + 1, 14, zc + 1)
            r.fill(x0, 13, zc, x0, 14, zc + 1, "iron_bars")
            r.fill(x0 + 1, 13, zc, x0 + 1, 14, zc + 1, "iron_bars")

    # Side galleries over the aisles: floor block at y=6, rail on the nave edge, stair run at the entry end.
    for x0, x1, rail_x, stair_x in ((1, 5, 5, 2), (17, 21, 17, 20)):
        r.fill(x0, GALLERY_Y, 1, x1, GALLERY_Y, 20, "polished_deepslate")
        r.fill(rail_x, GALLERY_Y + 1, 1, rail_x, GALLERY_Y + 1, 20, "deepslate_brick_wall")
        for step in range(GALLERY_Y):  # steps y=1..6 at z=26..21 (north-ascending), floor block y=6 continues at z=20
            for xx in (stair_x - 1, stair_x, stair_x + 1):
                r.stair(xx, 1 + step, 26 - step, "north")
                for yy in range(1, 1 + step):
                    r.put(xx, yy, 26 - step, "polished_deepslate")  # solid core under each step
    # Dais: three tiers; each front stair is flush with the terrace it climbs onto.
    for tier, (z0, z1) in enumerate(((1, 6), (1, 4), (1, 2))):
        r.fill(8, 1, z0, 14, 1 + tier, z1, "polished_deepslate")
    for tier, z_front in enumerate((7, 5, 3)):
        for x in range(9, 14):
            r.stair(x, 1 + tier, z_front, "north")
    r.stair(11, 4, 2, "north")                       # seat
    r.fill(11, 4, 1, 11, 6, 1, "chiseled_deepslate")  # throne back
    r.put(10, 4, 2, "deepslate_brick_wall")
    r.put(12, 4, 2, "deepslate_brick_wall")
    for x in (9, 13):
        r.hang_lantern(x, 15, 2, 4)

    # Lighting: a chain of lanterns down the nave, soul lanterns in the aisles, lit clerestory.
    for z in (7, 13, 19, 25):
        r.hang_lantern(11, 15, z, 4)
    for z in (8, 18):
        for x in (3, 19):
            r.hang_lantern(x, 15, z, 5, soul=True)
    for x0 in (6, 15):
        r.put(x0, 12, 13, "sea_lantern")

    # Aisle furnishing: benches under the galleries, a loot chest and barrels.
    for z in (6, 12):
        r.stair(3, 1, z, "west", material="dark_oak_stairs")
        r.stair(19, 1, z, "east", material="dark_oak_stairs")
    r.chest(1, 1, 11, "east", LOOT_HALL)
    r.barrel(21, 1, 9, "up")
    r.barrel(21, 1, 10, "up", LOOT_HALL)

    # Damage: a fallen column across the nave and a collapsed north bay of the east gallery.
    for x in range(9, 14):
        r.put(x, 1, 15, "polished_deepslate")
    r.put(8, 1, 15, "cracked_deepslate_bricks")
    r.slab(14, 1, 15, "cobbled_deepslate_slab")
    r.clear(17, GALLERY_Y, 1, 21, GALLERY_Y, 5)
    r.clear(17, GALLERY_Y + 1, 1, 17, GALLERY_Y + 1, 5)
    _rubble(r, 17, 21, 1, 5, 4)
    r.scatter([(x, 0, z) for x in range(1, 22) for z in range(8, 29)], "moss_block", 0.04)
    r.scatter([(x, 1, z) for x in range(1, 22) for z in range(26, 29)], "moss_carpet", 0.2)
    _cobwebs(r, [(1, 15, 1), (21, 15, 1), (1, 15, 29), (21, 15, 29), (6, 11, 3), (16, 11, 3), (8, 14, 14)])
    return r.finish()


# --- B2: multi-level barracks -------------------------------------------------------------------
def barracks_hall():
    """21x16x27. Mess hall, two-tier dormitory, a west catwalk and an officers' mezzanine over the armoury."""
    r = Room((21, 16, 27), seed=4102)
    w, h, d = r.size
    wall, floor, roof = _materials(r)
    r.shell(floor=floor, wall=wall, roof=roof, band=(7, "polished_deepslate"))
    r.door(*UPPER_DOOR, UPPER_ENTRY)
    r.trim_door(*UPPER_DOOR)
    # Timber floor through the dormitory and mess.
    for x in range(2, 19):
        for z in range(10, 25):
            if r.rng.random() < 0.75:
                r.put(x, 0, z, r.weighted(("dark_oak_planks", 60), ("spruce_planks", 40)))
    # Roof beams every four blocks with wall pilasters (clear of the stair/catwalk on the west side).
    for z in (3, 7, 11, 15, 19, 23):
        for x in range(1, 20):
            r.put(x, 14, z, "stripped_dark_oak_log[axis=x]")
        r.pillar(19, z, 19, z, 1, 13, base="polished_deepslate", shaft="deepslate_bricks", cap="chiseled_tuff_bricks")
        if not 9 <= z <= 19:
            r.pillar(1, z, 1, z, 1, 13, base="polished_deepslate", shaft="deepslate_bricks", cap="chiseled_tuff_bricks")

    # Officers' mezzanine (z=1..9, floor block y=6) above the armoury (y=1..5).
    r.fill(1, 6, 1, 19, 6, 9, "polished_deepslate")
    for x in range(3, 20):
        r.put(x, 7, 9, "deepslate_brick_wall")          # balustrade over the dormitory
    r.fill(1, 1, 9, 19, 5, 9, wall)                    # armoury partition, carrying the mezzanine lip
    for lo, hi in ((4, 6), (14, 16)):                  # two doorways with polished jambs and lintels
        r.clear(lo, 1, 9, hi, 3, 9)
        r.fill(lo - 1, 1, 9, lo - 1, 4, 9, "polished_deepslate")
        r.fill(hi + 1, 1, 9, hi + 1, 4, 9, "polished_deepslate")
        r.fill(lo, 4, 9, hi, 4, 9, "chiseled_deepslate")
    # Armoury stock (below the mezzanine): racks, workstations and loot.
    for z in range(2, 8):
        r.put(1, 3, z, "iron_bars")
        r.put(1, 4, z, "iron_bars")
        r.put(19, 3, z, "iron_bars")
    r.put(2, 1, 2, "fletching_table")
    r.put(4, 1, 2, "smithing_table")
    r.put(6, 1, 2, "grindstone[face=floor,facing=south]")
    r.put(15, 1, 2, "anvil[facing=south]")
    r.chest(18, 1, 2, "south", LOOT_BARRACKS)
    r.chest(18, 1, 6, "west", LOOT_BARRACKS)
    for x in range(10, 13):
        for z in (2, 3):
            r.barrel(x, 1, z, "up")
    for x in (9, 13):
        r.lantern(x, 4, 7, hanging=True)
        r.put(x, 5, 7, "iron_bars")
    # Mezzanine furnishing: officers' beds, a desk and shelves.
    r.bed(3, 7, 3, "north", "blue")
    r.bed(5, 7, 3, "north", "blue")
    for y in (7, 8, 9):
        r.put(19, y, 4, "bookshelf")
        r.put(19, y, 5, "bookshelf")
    r.put(17, 7, 2, "lectern[facing=south,has_book=false,powered=false]")
    r.entities[(17, 7, 2)] = {"id": "minecraft:lectern"}
    r.chest(15, 7, 2, "south", LOOT_BARRACKS)
    r.hang_lantern(10, 13, 4, 3)

    # West stair run (x=1..2) climbing north to the catwalk: steps y=1..6 at z=18..13, catwalk floor block y=6.
    for step in range(6):
        for x in (1, 2):
            r.stair(x, 1 + step, 18 - step, "north")
            for yy in range(1, 1 + step):
                r.put(x, yy, 18 - step, "polished_deepslate")
    for z in range(10, 13):
        for x in (1, 2):
            r.put(x, 6, z, "polished_deepslate")
        r.put(3, 7, z, "deepslate_brick_wall")
    for x in (1, 2):
        r.put(x, 6, 12, "polished_deepslate")
    # Catwalk supports: a pier under the catwalk's open edge.
    r.pillar(3, 11, 3, 11, 1, 5, base="polished_deepslate", shaft="deepslate_bricks", cap="chiseled_tuff_bricks")

    # Dormitory: two-tier bunk units each side of the central aisle, each with a two-step stair at its foot.
    for xs0 in (5, 14):
        for z0 in (11, 16):
            for x in (xs0, xs0 + 1):
                r.bed(x, 1, z0 + 1, "north", "gray")            # lower bed: foot z0+1, head z0
                r.fill(x, 2, z0, x, 2, z0 + 1, "spruce_planks")  # upper deck
                r.bed(x, 3, z0 + 1, "north", "red")
            for post_x in (xs0 - 1, xs0 + 2):
                r.fill(post_x, 1, z0, post_x, 3, z0, "dark_oak_log[axis=y]")
            r.put(xs0, 1, z0 + 2, "spruce_planks")
            r.stair(xs0, 2, z0 + 2, "north", material="spruce_stairs")   # back flush with the deck top
            r.stair(xs0, 1, z0 + 3, "north", material="spruce_stairs")
    # Footlockers and a loot barrel along the east wall.
    for z in (11, 14, 17):
        r.barrel(18, 1, z, "up", LOOT_BARRACKS if z == 14 else None)

    # Mess hall (z=19..25): long tables with benches either side of a clear central aisle.
    for x0, x1 in ((3, 8), (12, 17)):
        for z in (21, 24):
            for x in range(x0, x1 + 1):
                r.put(x, 1, z, "spruce_slab[type=bottom,waterlogged=false]")
                r.stair(x, 1, z - 1, "south", material="dark_oak_stairs")
                r.stair(x, 1, z + 1, "north", material="dark_oak_stairs")
    r.put(18, 1, 21, "campfire[facing=west,lit=false,signal_fire=false,waterlogged=false]")
    r.entities[(18, 1, 21)] = {"id": "minecraft:campfire"}
    r.barrel(18, 1, 23, "up")
    # Lighting.
    for z in (5, 13, 21):
        r.hang_lantern(10, 13, z, 3)
    for x in (4, 16):
        r.hang_lantern(x, 13, 17, 3, soul=True)
    # Damage: a broken catwalk rail, a missing beam run and rubble.
    r.clear(3, 7, 11, 3, 7, 12)
    r.clear(8, 14, 11, 12, 14, 11)
    _rubble(r, 15, 19, 21, 25, 3)
    _cobwebs(r, [(1, 13, 1), (19, 13, 1), (1, 13, 25), (19, 13, 25), (10, 13, 10)])
    return r.finish()


# --- B3: trial / combat chamber ------------------------------------------------------------------
def trial_chamber():
    """23x15x29. Entry hall opening onto a sunken arena with cover, ramped ledges and a reserved reward alcove."""
    r = Room((23, 15, 29), seed=4103)
    w, h, d = r.size
    wall, floor, roof = _materials(r)
    r.shell(floor=floor, wall=wall, roof=roof, band=(5, "waxed_oxidized_cut_copper"))
    r.door(*UPPER_DOOR, UPPER_ENTRY)
    r.trim_door(*UPPER_DOOR, jamb="waxed_oxidized_cut_copper", lintel="waxed_chiseled_copper")

    # Arena floor with copper grates.
    for x in range(4, 19):
        for z in range(5, 28):
            r.put(x, 0, z, r.weighted(("deepslate_tiles", 58), ("waxed_copper_grate[waterlogged=false]", 14), ("cracked_deepslate_tiles", 28)))
    # Ledges (two blocks high): west, east (z=5..23) and north (z=1..4), flush stair ramps onto each.
    for z in range(5, 24):
        r.fill(1, 1, z, 3, 2, z, "polished_deepslate")
        r.fill(19, 1, z, 21, 2, z, "polished_deepslate")
    r.fill(1, 1, 1, 21, 2, 4, "polished_deepslate")
    ramps_z = (8, 9, 19, 20)
    for z in ramps_z:
        r.stair(4, 1, z, "west")
        r.stair(3, 2, z, "west")
        r.put(3, 1, z, "polished_deepslate")
        r.stair(18, 1, z, "east")
        r.stair(19, 2, z, "east")
        r.put(19, 1, z, "polished_deepslate")
    for x in (10, 11, 12):
        r.stair(x, 1, 5, "north")
        r.stair(x, 2, 4, "north")
        r.put(x, 1, 4, "polished_deepslate")
    # Ledge balustrades with gaps at the ramps.
    for z in range(5, 24):
        if z not in ramps_z:
            r.put(3, 3, z, "deepslate_brick_wall")
            r.put(19, 3, z, "deepslate_brick_wall")
    for x in range(4, 19):
        if x not in (10, 11, 12):
            r.put(x, 3, 4, "deepslate_brick_wall")
    # Trial spawners with distinct vanilla configs: one central on a plinth, two on the north ledge corners.
    def spawner(x, y, z, kind):
        r.put(x, y, z, "trial_spawner[ominous=false,trial_spawner_state=inactive]")
        r.entities[(x, y, z)] = {
            "id": "minecraft:trial_spawner",
            "normal_config": f"minecraft:trial_chamber/{kind}/normal",
            "ominous_config": f"minecraft:trial_chamber/{kind}/ominous",
        }

    spawner(11, 1, 14, "ranged/skeleton")
    spawner(5, 3, 2, "melee/spider")
    spawner(17, 3, 2, "melee/zombie")
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if (dx, dz) != (0, 0):
                r.put(11 + dx, 0, 14 + dz, "chiseled_deepslate")
    for x in (5, 17):
        r.put(x, 2, 2, "waxed_chiseled_copper")
    # Cover: paired low walls and pillars breaking sight-lines in a symmetric, readable layout.
    for x, z in ((7, 10), (15, 10), (7, 18), (15, 18)):
        r.fill(x, 1, z, x + 1, 2, z, "deepslate_bricks")
        r.slab(x, 3, z)
        r.slab(x + 1, 3, z)
    for z in (9, 20):
        r.fill(10, 1, z, 12, 1, z, "cracked_deepslate_bricks")
    for x in (5, 17):
        r.pillar(x, 14, x, 14, 1, 7, base="polished_deepslate", shaft="deepslate_bricks", cap="waxed_chiseled_copper")
    # Reserved reward alcove at the top of the north ramp (vanilla loot placeholder; balancing deferred).
    r.clear(9, 3, 1, 13, 6, 3)
    r.chest(11, 3, 1, "south", LOOT_TRIAL)
    for z in (1, 2, 3):
        for y in (3, 4):
            r.put(8, y, z, "iron_bars")
            r.put(14, y, z, "iron_bars")
    for x in range(8, 15):
        r.put(x, 7, 1, "waxed_chiseled_copper")
        r.put(x, 7, 2, "waxed_chiseled_copper")
        r.put(x, 7, 3, "waxed_chiseled_copper")
    # Lighting: lit copper bulbs in the walls and soul lanterns above the arena.
    for z in (5, 11, 17, 23):
        r.put(0, 7, z, "waxed_copper_bulb[lit=true,powered=false]")
        r.put(22, 7, z, "waxed_copper_bulb[lit=true,powered=false]")
    for x, z in ((8, 12), (14, 12), (8, 16), (14, 16)):
        r.hang_lantern(x, 13, z, 4, soul=True)
    r.hang_lantern(11, 13, 14, 5)
    for z in range(2, 27, 6):
        for y in range(6, 13):
            r.put(0, y, z, "waxed_oxidized_cut_copper")
            r.put(22, y, z, "waxed_oxidized_cut_copper")
    # Damage.
    _rubble(r, 19, 21, 24, 27, 3)
    _cobwebs(r, [(1, 13, 1), (21, 13, 1), (1, 13, 27), (21, 13, 27), (11, 13, 8)])
    return r.finish()


UPPER_ROOMS = {
    "grand_hall": grand_hall,
    "barracks_hall": barracks_hall,
    "trial_chamber": trial_chamber,
}
