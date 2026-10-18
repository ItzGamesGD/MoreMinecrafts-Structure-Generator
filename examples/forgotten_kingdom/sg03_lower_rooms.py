"""SG-03 Family A: small lower-level rooms (plaza level, below the first gallery band).

Each builder returns ``(grid, block_entities)``. Footprints stay within the SG-02 reserved lower
volume (17 wide, 9 tall, 24 deep, entry centred on the south edge).
"""

from __future__ import annotations

from kingdom_common import LOWER_DOOR, LOWER_ENTRY
from rooms_common import Room

LOOT_STORAGE = "minecraft:chests/simple_dungeon"
LOOT_GUARD = "minecraft:chests/abandoned_mineshaft"
LOOT_HOME = "minecraft:chests/simple_dungeon"


def _materials(r: Room):
    wall = r.weighted(("deepslate_bricks", 70), ("cracked_deepslate_bricks", 17), ("deepslate_tiles", 9), ("tuff_bricks", 4))
    floor = r.weighted(("deepslate_tiles", 62), ("cracked_deepslate_tiles", 18), ("polished_deepslate", 14), ("tuff_bricks", 6))
    roof = r.weighted(("deepslate_tiles", 80), ("cracked_deepslate_tiles", 12), ("tuff_bricks", 8))
    return wall, floor, roof


def _cobwebs(r: Room, cells) -> None:
    for cell in cells:
        r.put(*cell, "cobweb")


def _rubble(r: Room, x0: int, x1: int, z0: int, z1: int, peak: int) -> None:
    """A deterministic collapse mound that falls off toward its edges."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    span = max(x1 - x0, z1 - z0) / 2 + 0.5
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            dist = max(abs(x - cx), abs(z - cz))
            height = int(round(peak * (1 - dist / span))) + r.rng.choice((-1, 0, 0, 1))
            for y in range(1, max(height, 0) + 1):
                r.put(x, y, z, r.weighted(("cobbled_deepslate", 70), ("deepslate_bricks", 15), ("cracked_deepslate_bricks", 15)))
            if height >= 1 and r.rng.random() < 0.5:
                r.slab(x, height + 1, z, "cobbled_deepslate_slab")


# --- A1: abandoned storage room ---------------------------------------------------------------
def storage_room():
    """13x9x17. Tall vaulted store: shelf bays between rib pilasters, crate island, raised stash, collapsed NE corner."""
    r = Room((13, 9, 17), seed=3101)
    wall, floor, roof = _materials(r)
    r.shell(floor=floor, wall=wall, roof=roof, band=(1, "polished_deepslate"))
    r.door(*LOWER_DOOR, LOWER_ENTRY)
    r.trim_door(*LOWER_DOOR)

    # Vaulted ceiling: low side bays (interior to y=6) corbelled into a taller central nave (y=7).
    for x in (1, 2, 10, 11):
        r.fill(x, 7, 1, x, 7, 15, "deepslate_bricks")
    for z in range(1, 16):
        r.stair(3, 7, z, "west", half="top")
        r.stair(9, 7, z, "east", half="top")

    # Rib pilasters and beams dividing the room into three bays.
    for z in (5, 11):
        for x in (1, 11):
            r.fill(x, 1, z, x, 6, z, "polished_deepslate")
        r.fill(2, 6, z, 10, 6, z, "deepslate_bricks")
        r.stair(2, 5, z, "east", half="top")
        r.stair(10, 5, z, "west", half="top")
        r.lantern(4, 5, z, hanging=True)
        r.lantern(8, 5, z, hanging=True)

    # Wall shelves in the three bays on both sides: boards with barrels, pots and candles.
    for side_x, facing in ((1, "east"), (11, "west")):
        for z0, z1 in ((2, 4), (6, 10), (12, 14)):
            for z in range(z0, z1 + 1):
                for board in (2, 4):
                    r.put(side_x, board, z, "dark_oak_slab[type=bottom,waterlogged=false]")
                    pick = r.rng.random()
                    if pick < 0.4:
                        r.barrel(side_x, board + 1, z, "up")
                    elif pick < 0.6:
                        r.put(side_x, board + 1, z, "decorated_pot[facing=" + facing + ",cracked=false,waterlogged=false]")
                        r.entities[(side_x, board + 1, z)] = {"id": "minecraft:decorated_pot"}
                    elif pick < 0.75:
                        r.put(side_x, board + 1, z, "candle[candles=2,lit=false,waterlogged=false]")
                if r.rng.random() < 0.55:
                    r.barrel(side_x, 1, z, "up")
    # A broken shelf (damage): remove two boards on the east wall.
    r.clear(11, 2, 7, 11, 5, 8)
    r.scatter([(11, 1, 7), (11, 1, 8)], "cobbled_deepslate_slab[type=bottom,waterlogged=false]", 1.0)

    # Crate island in the middle bay.
    for x in (5, 6, 7):
        for z in (7, 8, 9):
            r.barrel(x, 1, z, "up")
            if (x + z) % 2 == 0:
                r.barrel(x, 2, z, "up")
    r.chest(6, 3, 8, "south", LOOT_STORAGE)
    r.barrel(5, 3, 7, "up", LOOT_STORAGE)

    # Raised stash at the north end (secondary elevation) reached by stairs.
    r.fill(3, 1, 1, 9, 1, 3, "polished_deepslate")
    for x in range(3, 10):
        r.stair(x, 1, 4, "north")
    r.chest(4, 2, 2, "south", LOOT_STORAGE)
    r.chest(8, 2, 2, "south", LOOT_STORAGE)
    r.barrel(6, 2, 1, "up")
    r.put(6, 2, 3, "lectern[facing=south,has_book=false,powered=false]")
    r.entities[(6, 2, 3)] = {"id": "minecraft:lectern"}

    # Collapsed north-east corner: rubble mound and a hole in the lowered ceiling.
    _rubble(r, 8, 11, 1, 4, 3)
    r.clear(8, 7, 1, 10, 7, 3)
    r.fill(8, 8, 1, 10, 8, 3, "cracked_deepslate_bricks")
    _cobwebs(r, [(1, 6, 1), (11, 6, 15), (1, 6, 15), (3, 6, 1), (9, 6, 6)])
    r.hang_lantern(6, 7, 2, 1)
    r.hang_lantern(6, 7, 14, 1)
    return r.finish()


# --- A2: guard / watch room --------------------------------------------------------------------
def guard_room():
    """15x8x13. Gatehouse with a raised portcullis, guard closets, armoury wall and a raised watch step."""
    r = Room((15, 8, 13), seed=3102)
    wall, floor, roof = _materials(r)
    r.shell(floor=floor, wall=wall, roof=roof, band=(5, "polished_deepslate"))
    r.door(*LOWER_DOOR, LOWER_ENTRY, thickness=1)
    r.trim_door(*LOWER_DOOR)
    cx = 7

    # Gate passage (z=9..11): solid cheeks either side, opening into the main hall at z=8.
    for z in (9, 10, 11):
        r.fill(1, 1, z, 4, 6, z, wall)
        r.fill(10, 1, z, 13, 6, z, wall)
    for z in (9, 10, 11):
        r.clear(cx - 1, 1, z, cx + 1, 4, z)
        r.fill(cx - 2, 1, z, cx - 2, 5, z, "polished_deepslate")
        r.fill(cx + 2, 1, z, cx + 2, 5, z, "polished_deepslate")
        r.fill(cx - 1, 5, z, cx + 1, 5, z, "chiseled_deepslate")
    # Raised portcullis: bars hang in a slot above the inner doorway, murder-hole bars in the roof.
    r.fill(cx - 1, 5, 9, cx + 1, 6, 9, "iron_bars")
    r.put(cx, 6, 10, "iron_bars")
    r.put(cx, 6, 11, "iron_bars")
    r.lantern(cx, 4, 10, hanging=True)

    # Guard closets flanking the passage, open to the hall.
    r.clear(2, 1, 9, 3, 4, 11)
    r.clear(11, 1, 9, 12, 4, 11)
    r.clear(2, 1, 8, 3, 3, 8)
    r.clear(11, 1, 8, 12, 3, 8)
    r.bed(2, 1, 10, "north", "gray")      # foot z=10, head z=9
    r.bed(3, 1, 10, "north", "gray")
    r.chest(12, 1, 10, "west", LOOT_GUARD)
    r.barrel(11, 1, 9, "up")
    r.barrel(12, 1, 9, "up")
    r.put(11, 1, 11, "grindstone[face=floor,facing=west]")
    r.hang_lantern(3, 5, 9, 1)

    # Main hall (z=1..8): raised watch step on the north side, reached by two stair courses.
    r.fill(3, 1, 1, 11, 2, 2, "polished_deepslate")
    for x in range(6, 9):
        r.stair(x, 1, 4, "north")
        r.stair(x, 2, 3, "north")
    r.fill(6, 1, 3, 8, 1, 3, "deepslate_bricks")
    r.fill(6, 1, 1, 8, 2, 2, "polished_deepslate")
    for x in (4, 6, 8, 10):
        r.put(x, 3, 0, "iron_bars")
        r.put(x, 4, 0, "iron_bars")
    r.lantern(5, 3, 1)
    r.lantern(9, 3, 1)

    # Guard table with seats.
    for x in (6, 7, 8):
        r.put(x, 1, 6, "spruce_slab[type=bottom,waterlogged=false]")
    r.stair(5, 1, 6, "west", material="dark_oak_stairs")
    r.stair(9, 1, 6, "east", material="dark_oak_stairs")
    r.put(7, 2, 6, "candle[candles=3,lit=false,waterlogged=false]")

    # Armoury wall (west): weapon racks of chained bars, a fletching table, smithing table and anvil.
    for z in range(1, 6):
        r.put(1, 3, z, "iron_bars")
        r.put(1, 4, z, "iron_bars")
    r.put(1, 1, 1, "fletching_table")
    r.put(1, 1, 3, "smithing_table")
    r.put(1, 1, 5, "anvil[facing=east]")
    for z in (2, 4):
        r.put(2, 3, z, "chain[axis=y,waterlogged=false]")
        r.put(2, 4, z, "chain[axis=y,waterlogged=false]")
    # Armoury wall (east): stacked barrels as ammunition stores and a second rack.
    for z in range(1, 6):
        r.put(13, 3, z, "iron_bars")
    r.barrel(13, 1, 2, "up")
    r.barrel(13, 1, 3, "up")
    r.barrel(13, 2, 2, "up", LOOT_GUARD)
    r.put(13, 1, 5, "blast_furnace[facing=west,lit=false]")  # the game creates its block entity on placement

    # Damage: a cracked patch of floor and ceiling, scattered rubble and cobwebs.
    r.scatter([(x, 0, z) for x in range(2, 13) for z in range(1, 8)], "cracked_deepslate_tiles", 0.18)
    r.fill(11, 1, 6, 12, 1, 7, "cobbled_deepslate")
    r.slab(12, 2, 7, "cobbled_deepslate_slab")
    _cobwebs(r, [(1, 6, 1), (13, 6, 1), (13, 6, 8), (1, 6, 8)])
    return r.finish()


# --- A3: small residential ruin ----------------------------------------------------------------
def residence_ruin():
    """15x7x19. A low hall with hearth and a bedroom behind an arched, partly collapsed partition."""
    r = Room((15, 7, 19), seed=3103)
    wall = r.weighted(("deepslate_bricks", 62), ("cracked_deepslate_bricks", 18), ("tuff_bricks", 14), ("deepslate_tiles", 6))
    floor = r.weighted(("polished_deepslate", 40), ("deepslate_tiles", 34), ("cracked_deepslate_tiles", 14), ("tuff_bricks", 12))
    roof = r.weighted(("deepslate_tiles", 70), ("tuff_bricks", 18), ("cracked_deepslate_tiles", 12))
    r.shell(floor=floor, wall=wall, roof=roof, band=(1, "polished_tuff"))
    r.door(*LOWER_DOOR, LOWER_ENTRY)
    r.trim_door(*LOWER_DOOR, jamb="polished_tuff", lintel="chiseled_tuff_bricks")
    cx = 7

    # Timber-lined floor in the hall (dark oak planks on the south half) hints at former habitation.
    for x in range(2, 13):
        for z in range(10, 17):
            if r.rng.random() < 0.8:
                r.put(x, 0, z, r.weighted(("dark_oak_planks", 70), ("spruce_planks", 30)))

    # Partition at z=8 with an arched doorway; the east half has partly collapsed.
    r.fill(1, 1, 8, 13, 5, 8, wall)
    r.clear(cx - 1, 1, 8, cx + 1, 3, 8)
    r.arch_x(cx - 1, cx + 1, 8, 4, material="tuff_bricks")
    r.clear(cx, 4, 8, cx, 4, 8)           # keystone knocked out
    r.clear(10, 4, 8, 13, 5, 8)           # collapsed upper partition
    for x in (10, 11, 12):
        r.put(x, 3, 8, "cobbled_deepslate_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    _rubble(r, 10, 13, 6, 9, 3)

    # Hearth in the partition's hall face with a surround of stairs.
    r.clear(3, 1, 8, 4, 2, 8)
    r.put(3, 1, 8, "campfire[facing=south,lit=false,signal_fire=false,waterlogged=false]")
    r.entities[(3, 1, 8)] = {"id": "minecraft:campfire"}
    r.put(4, 1, 8, "cauldron")
    r.stair(2, 1, 9, "east", material="cobbled_deepslate_stairs")
    r.stair(5, 1, 9, "west", material="cobbled_deepslate_stairs")
    r.fill(3, 3, 8, 4, 3, 8, "chiseled_tuff_bricks")

    # Hall furnishings: table, chairs, shelf wall, workstations.
    for x in (5, 6, 7):
        r.put(x, 1, 13, "spruce_slab[type=bottom,waterlogged=false]")
    r.stair(4, 1, 13, "west", material="dark_oak_stairs")
    r.stair(8, 1, 13, "east", material="dark_oak_stairs")
    r.stair(6, 1, 15, "south", material="dark_oak_stairs")
    r.put(6, 2, 13, "candle[candles=2,lit=false,waterlogged=false]")
    for y in (1, 2, 3):
        for z in (11, 12, 13):
            r.put(13, y, z, "bookshelf")
    r.put(13, 1, 14, "lectern[facing=west,has_book=false,powered=false]")
    r.entities[(13, 1, 14)] = {"id": "minecraft:lectern"}
    r.put(1, 1, 11, "loom[facing=east]")
    r.put(1, 1, 12, "cartography_table")
    r.barrel(1, 1, 14, "up")
    r.barrel(1, 2, 14, "up", LOOT_HOME)
    r.put(1, 1, 15, "potted_azalea_bush")
    r.put(12, 1, 15, "flower_pot")
    r.fill(2, 1, 15, 4, 1, 15, "moss_carpet")
    r.scatter([(x, 0, z) for x in range(2, 13) for z in range(10, 17)], "moss_block", 0.06)

    # Bedroom (z=1..7): two beds, chest, wardrobe barrels and a moss-grown corner.
    r.bed(2, 1, 6, "north", "red")
    r.bed(4, 1, 6, "north", "white")
    r.chest(1, 1, 2, "east", LOOT_HOME)
    r.barrel(1, 1, 4, "up")
    r.barrel(1, 2, 4, "up")
    r.stair(6, 1, 2, "south", material="dark_oak_stairs")
    r.put(7, 1, 2, "spruce_slab[type=bottom,waterlogged=false]")
    r.put(7, 2, 2, "candle[candles=1,lit=false,waterlogged=false]")
    r.fill(9, 1, 1, 12, 1, 4, "moss_block")
    r.scatter([(x, 2, z) for x in range(9, 13) for z in range(1, 5)], "moss_carpet", 0.5)
    r.put(12, 1, 6, "potted_azalea_bush")
    r.hang_lantern(5, 5, 4, 1)
    r.hang_lantern(7, 5, 12, 1, soul=True)
    r.lantern(1, 3, 4)
    _cobwebs(r, [(1, 5, 1), (13, 5, 1), (1, 5, 7), (1, 5, 17), (13, 5, 17), (7, 5, 8)])
    return r.finish()


LOWER_ROOMS = {
    "storage_room": storage_room,
    "guard_room": guard_room,
    "residence_ruin": residence_ruin,
}
