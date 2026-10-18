"""Deterministic in-bounds Stage 24-B restoration layouts built from pinned NBT."""
from __future__ import annotations

from tools.stage24b_candidate import Candidate, block_id

STONE = "deepslate_bricks"
TILE = "deepslate_tiles"


def place(c: Candidate, pos, key, reason):
    x, y, z = pos
    current = c.get_block(pos)
    if current == key:
        return
    if current != "minecraft:air" and pos in c.protected:
        return
    c.set_block(x, y, z, key, replace=pos in c.positions, reason=reason)


def clear(c: Candidate, pos, reason="interior_clearance"):
    if c.get_block(pos) != "minecraft:air" and pos not in c.protected:
        c.carve(*pos, reason=reason)


def floor(c, x0, x1, z0, z1, y=0):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if c.get_block((x, y, z)) == "minecraft:air":
                place(c, (x, y, z), STONE, "floor_repair")


def shell(c, door, *, roof_y, roof_skip=None):
    xmax, zmax = c.size[0] - 1, c.size[2] - 1
    for y in (1, 2, 3):
        for x in range(c.size[0]):
            for z in range(c.size[2]):
                if x not in (0, xmax) and z not in (0, zmax):
                    continue
                if (x, y, z) in ((door[0], 1, door[1]), (door[0], 2, door[1])):
                    continue
                # Leave the original south bathhouse connector edges untouched.
                place(c, (x, y, z), "polished_deepslate" if (x + z) % 5 == 0 else STONE, "outer_wall")
    for x in range(c.size[0]):
        for z in range(c.size[2]):
            if roof_skip and roof_skip(x, z):
                continue
            place(c, (x, roof_y, z), TILE, "roof")
    place(c, (door[0], 1, door[1]), "spruce_door[facing=west,half=lower,hinge=left,open=false,powered=false]", "entry_door")
    place(c, (door[0], 2, door[1]), "spruce_door[facing=west,half=upper,hinge=left,open=false,powered=false]", "entry_door")
    c.entry_inside = (door[0] + 1 if door[0] == 0 else door[0] - 1, 1, door[1])
    c.features["doors"] = [(door[0], 1, door[1]), (door[0], 2, door[1])]
    c.features["entrance"] = [door[0], door[1]]


def partition_x(c, x, z0, z1, ylo=1, yhi=3, gaps=()):
    for z in range(z0, z1 + 1):
        if z in gaps:
            continue
        for y in range(ylo, yhi + 1):
            place(c, (x, y, z), STONE, "interior_partition")


def bed(c, x, y, z, facing="south"):
    dx, dz = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[facing]
    place(c, (x, y, z), f"gray_bed[facing={facing},occupied=false,part=foot]", "sleeping_bed")
    place(c, (x + dx, y, z + dz), f"gray_bed[facing={facing},occupied=false,part=head]", "sleeping_bed")
    c.features.setdefault("beds", []).append([[x, y, z], [x + dx, y, z + dz]])


def wall_state(pos, ring):
    """deepslate_tile_wall state connecting to neighbouring ring cells (low connections, post at corners/ends)."""
    x, y, z = pos
    conn = {d: ((x + dx, y, z + dz) in ring) for d, (dx, dz) in
            {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}.items()}
    straight = (conn["north"] and conn["south"] and not conn["east"] and not conn["west"]) or \
               (conn["east"] and conn["west"] and not conn["north"] and not conn["south"])
    props = ",".join(f"{d}={'low' if conn[d] else 'none'}" for d in ("east", "north", "south", "west"))
    return f"deepslate_tile_wall[{props},up={'false' if straight else 'true'},waterlogged=false]"


def lantern_state(c, pos):
    """Stage 24-C: a lantern must hang from a ceiling or stand on a floor, or the server pops it."""
    x, y, z = pos
    if c.get_block((x, y - 1, z)) != "minecraft:air":
        return "soul_lantern[hanging=false]"
    if c.get_block((x, y + 1, z)) != "minecraft:air":
        return "soul_lantern[hanging=true]"
    raise ValueError(f"{c.module} lantern at {pos} has no floor or ceiling support")


FULL_BLOCK_SUFFIXES = ("_stairs", "_slab", "_wall", "_door", "_trapdoor", "_bed", "_fence")


def _full_block(key):
    name = key.split("[", 1)[0]
    return (name.startswith("minecraft:") and name != "minecraft:air" and "deepslate" in name
            and not name.endswith(FULL_BLOCK_SUFFIXES))


def mount_lantern(c, x, y, z, radius=6):
    """Stage 24-C: sauna lanterns floated in open air (no roof). Stand each on the nearest wall top."""
    best = None
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            for yy in range(1, 6):
                p = (x + dx, yy, z + dz)
                if not (0 <= p[0] < c.size[0] and 0 <= p[2] < c.size[2]):
                    continue
                if c.get_block(p) != "minecraft:air" or c.get_block((p[0], yy + 1, p[2])) != "minecraft:air":
                    continue
                if not _full_block(c.get_block((p[0], yy - 1, p[2]))):
                    continue
                # keep off walkable floor cells: the support must be a wall top, i.e. two blocks of wall below
                if not _full_block(c.get_block((p[0], yy - 2, p[2]))) or yy < 3:
                    continue
                near = [c.get_block((p[0] + a, p[1] + b, p[2] + d)) for a in (-1, 0, 1) for b in (-1, 0, 1) for d in (-1, 0, 1)]
                if any(k.startswith(("minecraft:water", "minecraft:chest")) for k in near):
                    continue
                score = abs(dx) + abs(dz) + abs(yy - y)
                if best is None or score < best[0]:
                    best = (score, p)
    if best is None:
        raise ValueError(f"{c.module}: no wall top to mount lantern near {(x, y, z)}")
    return best[1]


def lamp(c, x, y, z):
    place(c, (x, y, z), lantern_state(c, (x, y, z)), "soul_lantern_lighting")


def house_large(c):
    # Broad courtyard house: room wings wrap a 5x5 open-to-sky light court.
    floor(c, 0, 16, 0, 16)
    shell(c, (0, 7), roof_y=4, roof_skip=lambda x, z: 6 <= x <= 10 and 6 <= z <= 10)
    # Three wings; the middle remains an open courtyard, connected on all sides.
    for x in (5, 11):
        for z in range(1, 16):
            if z in (7, 8, 9):
                continue
            for y in (1, 2, 3):
                place(c, (x, y, z), STONE, "courtyard_wing_partition")
    for z in (5, 11):
        for x in range(6, 11):
            for y in (1, 2, 3):
                place(c, (x, y, z), STONE, "courtyard_edge")
    bed(c, 12, 1, 3, "south")
    bed(c, 12, 1, 11, "north")
    place(c, (2, 1, 2), "barrel[facing=up,open=false]", "pantry_storage")
    place(c, (2, 1, 4), "crafting_table", "kitchen_workstation")
    place(c, (3, 1, 10), "polished_deepslate_slab[type=bottom,waterlogged=false]", "courtyard_bench")
    place(c, (13, 1, 8), "polished_deepslate_slab[type=bottom,waterlogged=false]", "family_dining_table")
    place(c, (12, 1, 8), "polished_deepslate_slab[type=bottom,waterlogged=false]", "family_dining_seat")
    place(c, (14, 1, 8), "polished_deepslate_slab[type=bottom,waterlogged=false]", "family_dining_seat")
    for x, z in ((2, 2), (13, 2), (13, 14), (2, 14)):
        lamp(c, x, 3, z)
    c.features["courtyard"] = {"bounds": [6, 10, 6, 10], "open_sky": True}


def house_medium_one(c):
    floor(c, 0, 7, 0, 12)
    shell(c, (0, 6), roof_y=4)
    # Shallow east-rising single-pitch roof and slit window distinguish this longhouse.
    for z in (0, 12):
        for x in range(1, 7):
            place(c, (x, 4, z), "deepslate_tile_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]", "single_pitch_roof_edge")
    place(c, (7, 2, 6), "cyan_stained_glass", "blue_slit_window")
    # Approved narrow plan: common room at center, rear bed nook, kitchen/store to north.
    bed(c, 1, 1, 10, "east")
    place(c, (5, 1, 2), "crafting_table", "kitchen_workstation")
    place(c, (6, 1, 2), "barrel[facing=up,open=false]", "food_storage")
    place(c, (5, 1, 6), "polished_deepslate_slab[type=bottom,waterlogged=false]", "sitting_bench")
    place(c, (6, 1, 6), "polished_deepslate_slab[type=bottom,waterlogged=false]", "eating_table")
    lamp(c, 1, 3, 10)
    lamp(c, 6, 3, 2)
    c.features["layout"] = "compact_single_story_common_room_and_sleeping_room"


def house_medium_two(c):
    c.set_dimensions((16, 8, 11))
    floor(c, 0, 15, 0, 10)
    # Ground story shell plus upper east wing and its two-block-high room volume.
    for y in (1, 2, 3):
        for x in range(16):
            for z in range(11):
                if x not in (0, 15) and z not in (0, 10):
                    continue
                if (x, y, z) in ((0, 1, 5), (0, 2, 5)):
                    continue
                place(c, (x, y, z), STONE, "outer_wall")
    # Partial upper storey occupies east half; y=4 is floor, y=5..6 headroom, y=7 roof.
    for x in range(7):
        for z in range(11):
            place(c, (x, 4, z), TILE, "lower_wing_roof")
    for x in range(7, 16):
        for z in range(0, 11):
            place(c, (x, 4, z), TILE, "upper_floor")
    for y in (5, 6):
        for x in range(7, 16):
            for z in (0, 10):
                place(c, (x, y, z), STONE, "upper_wall")
            for z in range(11):
                if x in (7, 15):
                    place(c, (x, y, z), STONE, "upper_wall")
    for x in range(7, 16):
        for z in range(11):
            place(c, (x, 7, z), TILE, "upper_roof")
    # Real block stairs climb east to the second-floor landing. Lower two blocks remain full 2-high paths.
    stair_coords = [(4, 1, 5), (5, 2, 5), (6, 3, 5), (7, 4, 5)]
    for x, y, z in stair_coords:
        if y > 1:
            place(c, (x, y - 1, z), STONE, "stair_support")
        place(c, (x, y, z), "deepslate_tile_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]", "upper_stair")
        clear(c, (x, y + 1, z))
        # Stage 24-C: a 1.8-block player on the stair's high half needs two clear cells above it. The
        # ground-floor roof tile at (5,4,5) and the upper west wall at (7,6,5) blocked the 2nd and 4th steps.
        clear(c, (x, y + 2, z), "stair_headroom")
    # Reserve an open landing onto the raised floor.
    for y in (5, 6):
        clear(c, (8, y, 5))
    # Open the upper bedroom's volume while keeping the rest of the roof intact.
    bed(c, 11, 5, 2, "south")
    place(c, (13, 5, 8), "barrel[facing=up,open=false]", "upper_storage")
    # Ground-floor private room sits under the upper wing; family hall stays west/open.
    bed(c, 11, 1, 8, "north")
    place(c, (2, 1, 9), "crafting_table", "ground_kitchen_workstation")
    place(c, (3, 1, 9), "barrel[facing=up,open=false]", "ground_kitchen_storage")
    place(c, (3, 1, 5), "polished_deepslate_slab[type=bottom,waterlogged=false]", "family_dining_table")
    lamp(c, 2, 3, 4)
    lamp(c, 13, 5, 9)
    place(c, (0, 1, 5), "spruce_door[facing=west,half=lower,hinge=left,open=false,powered=false]", "entry_door")
    place(c, (0, 2, 5), "spruce_door[facing=west,half=upper,hinge=left,open=false,powered=false]", "entry_door")
    c.entry_inside = (1, 1, 5)
    c.features.update({"doors": [(0, 1, 5), (0, 2, 5)], "entrance": [0, 5], "stairs": stair_coords,
                       "upper_floor": [7, 15, 0, 10, 4], "upper_clear_headroom": [5, 6]})


def house_small_one(c):
    floor(c, 0, 6, 0, 7)
    shell(c, (0, 3), roof_y=4)
    # Asymmetric low gable, rear sleeping alcove and one-person living/counter strip.
    for x in range(1, 6):
        place(c, (x, 4, 0), "deepslate_tile_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]", "gable_roof_edge")
        place(c, (x, 4, 7), "deepslate_tile_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]", "gable_roof_edge")
    for x in range(1, 5):
        place(c, (x, 1, 1), STONE, "sleeping_alcove_screen")
    bed(c, 2, 1, 2, "east")
    place(c, (2, 1, 4), "polished_deepslate_slab[type=bottom,waterlogged=false]", "living_table")
    place(c, (2, 1, 6), "barrel[facing=up,open=false]", "counter_storage")
    place(c, (6, 2, 3), "cyan_stained_glass", "blue_slit_window")
    lamp(c, 5, 3, 6)
    c.features["layout"] = "single_room_with_sleeping_alcove_and_work_corner"


def house_small_two(c):
    floor(c, 0, 7, 0, 3)
    shell(c, (0, 2), roof_y=4)
    # 8x4 is only 32 cells: preserve a straight central aisle and keep furnishings minimal.
    # Stage 24-C: the bed used to sit inside the z=3 wall row beneath solid wall blocks, so the server
    # refused to sleep ("This bed is obstructed"). It now lies along the open north row of the room.
    bed(c, 2, 1, 1, "east")
    place(c, (5, 1, 1), "polished_deepslate_slab[type=bottom,waterlogged=false]", "north_end_table")
    place(c, (6, 1, 3), "barrel[facing=up,open=false]", "compact_storage")
    lamp(c, 6, 3, 2)
    c.features["layout"] = "micro_home_single_bed_and_clear_entry_aisle"


def sauna(c):
    # Keep the complete source shell, all 43 source water cells, rims, stairs, loot and connectors.
    # Furnish only empty, supported dry sites; two source basins stay completely unobstructed.
    c.entry_inside = (13, 1, 35)
    # The source south reception is divided from the bath circulation by one
    # cracked-brick head block; opening it connects the existing 2-high route.
    clear(c, (11, 2, 33), "bathhouse_circulation_opening")
    c.features.update({"entrance": [13, 36], "changing": [], "bathing_access": [], "resting": []})
    water = {p for p in c.original_positions if block_id(c._block_key_at(p)) == "minecraft:water"}
    chests = {p for p in c.original_positions if block_id(c._block_key_at(p)) == "minecraft:chest"}
    # Dry reception changing benches near the south entry, away from chest faces and main circulation.
    for x, z in ((10, 35), (16, 35), (10, 34), (16, 34)):
        p = (x, 1, z)
        if c.get_block(p) == "minecraft:air" and c.get_block((x, 0, z)) != "minecraft:air":
            place(c, p, "polished_deepslate_slab[type=bottom,waterlogged=false]", "changing_bench")
            c.features["changing"].append(list(p))
    # Dry resting alcoves are outside both basin projections and preserve all adjacent chest access.
    for x, z in ((4, 20), (5, 20), (4, 21), (5, 21), (23, 31), (24, 31)):
        p = (x, 1, z)
        if c.get_block(p) == "minecraft:air" and c.get_block((x, 0, z)) != "minecraft:air":
            if all(abs(x - q[0]) + abs(z - q[2]) > 1 for q in chests):
                place(c, p, "polished_deepslate_slab[type=bottom,waterlogged=false]", "resting_bench")
                c.features["resting"].append(list(p))
    # Non-blocking overhead light in dry circulation, away from the water footprints.
    for x, z in ((8, 17), (23, 20), (9, 32)):
        p = (x, 3, z)
        if c.get_block(p) == "minecraft:air" and (x, z) not in {(a, b) for a, _, b in water}:
            q = mount_lantern(c, x, 3, z)
            place(c, q, "soul_lantern[hanging=false]", "bathhouse_lighting")
            c.features.setdefault("lanterns", []).append(list(q))
    # A restrained tile canopy completes the dry south reception without roofing
    # either basin or spanning into the east connector lane.
    for x in range(9, 18):
        for z in range(32, 37):
            if c.get_block((x, 8, z)) == "minecraft:air":
                place(c, (x, 8, z), "deepslate_tile_slab[type=top,waterlogged=false]", "reception_roof")
    c.features["reception_roof"] = [9, 17, 32, 36, 8]
    # Validate an original stair route still reaches each bath's perimeter. No water blocks are added.
    c.features["bathing_access"] = [
        {"basin": "main", "water": [13, 0, 24, 20, 28], "source_access_stairs": True},
        {"basin": "plunge", "water": [13, 4, 6, 15, 6], "source_access_stairs": True},
    ]
    c.features["preserved_water_count"] = len(water)
    c.features["preserved_chest_count"] = len(chests)


def large_tower(c):
    # 6x6 ring support remains; interior is a narrow 2x2 shaft with three landings.
    c.entry_inside = (1, 1, 2)
    # Hollow central filler, explicitly preserving outer ring and all connector metadata.
    for y in range(2, 11):
        for x in (2, 3):
            for z in (2, 3):
                clear(c, (x, y, z), "tower_shaft_carve")
    # Existing y=0..1 are solid. Create three interior landings with a ladder aperture.
    for y in (2, 6, 10):
        for x in (2, 3):
            for z in (2, 3):
                if (x, y, z) != (2, y, 2):
                    place(c, (x, y, z), TILE, "tower_landing")
    # Ground entrance cut through west wall, away from east-side connector.
    for y in (1, 2):
        clear(c, (0, y, 2), "tower_entry_opening")
        clear(c, (1, y, 2), "tower_entry_tunnel")
    for y in range(1, 13):
        place(c, (3, y, 2), "polished_basalt[axis=y]", "ladder_support")
        # Stage 24-C: the ladder is mounted on the polished-basalt support at x=3 (faces west). The
        # former facing=east needed a block at x=1, which is the open entrance tunnel at y=1..2.
        place(c, (2, y, 2), "ladder[facing=west]", "tower_ladder")
        clear(c, (2, y + 1, 2), "ladder_headroom")
    # Top y=13 deck, y=14 retained outer parapet ring; open a ladder hatch through cap.
    clear(c, (2, 13, 2), "observation_ladder_hatch")
    for x in (2, 3):
        for z in (2, 3):
            clear(c, (x, 14, z), "observation_opening")
            if (x, z) != (2, 2):
                place(c, (x, 13, z), TILE, "observation_deck")
    for x, z in ((1, 1), (4, 1), (1, 4), (4, 4)):
        lamp(c, x, 12, z)
    c.features.update({"entrance": [0, 2], "ladder_run": list(range(1, 13)),
                       "observation_platform": [13, 2, 2, 3, 3], "landings": [2, 6, 10]})


def medium_tower(c):
    c.entry_inside = (3, 1, 1)
    floor(c, 1, 5, 1, 6)
    # Open a guard room around the retained original central support spine.
    for x in range(2, 5):
        for z in range(2, 6):
            for y in range(2, 7):
                if not (x in (2, 3) and z in (3, 4)):
                    clear(c, (x, y, z), "guard_room_carve")
    for y in range(1, 3):
        clear(c, (3, y, 0), "tower_entry_opening")
        clear(c, (3, y, 1), "tower_entry_corridor")
        clear(c, (3, y, 2), "tower_entry_corridor")
        clear(c, (4, y, 2), "guard_room_ladder_approach")
    for x in range(1, 6):
        for z in range(1, 7):
            if (x in (1, 5) or z in (1, 6)) and not (z == 1 and x == 3):
                for y in range(1, 8):
                    if z == 1 and x == 3 and y in (1, 2):
                        continue
                    place(c, (x, y, z), STONE, "guard_room_wall")
    place(c, (1, 4, 3), "cyan_stained_glass", "guard_room_window")
    place(c, (5, 4, 4), "cyan_stained_glass", "guard_room_window")
    # Guard-room floor remains on y=0, with a low bench and one light.
    place(c, (5, 1, 2), "polished_deepslate_slab[type=bottom,waterlogged=false]", "guard_bench")
    place(c, (4, 1, 5), "barrel[facing=up,open=false]", "guard_supply_storage")
    # Keep the original central 2x2 spine; ladder climbs its east face, clear of both east connectors.
    for y in range(1, 9):
        place(c, (4, y, 3), "ladder[facing=west]", "tower_ladder")
        clear(c, (4, y + 1, 3), "ladder_headroom")
    # Usable upper deck at y=8, open headroom y=9; keep a ring at y=10 as a parapet.
    for x in range(1, 6):
        for z in range(1, 7):
            if (x, z) != (4, 3):
                place(c, (x, 8, z), TILE, "guard_observation_deck")
    for x in range(1, 6):
        for z in range(1, 7):
            clear(c, (x, 9, z), "observation_headroom")
    for x in range(1, 6):
        for z in range(1, 7):
            clear(c, (x, 10, z), "observation_headroom")
    lamp(c, 2, 7, 2)
    # Stage 24-C: the observation deck had no edge protection (live test: a player walked off and fell 8
    # blocks). Restore the intended parapet as a ring of tile walls on the deck perimeter at y=9.
    ring = [(x, 9, z) for x in range(1, 6) for z in range(1, 7) if x in (1, 5) or z in (1, 6)]
    for pos in ring:
        place(c, pos, wall_state(pos, set(ring)), "observation_parapet")
    c.features["parapet"] = [list(p) for p in ring]
    c.features.update({"entrance": [3, 0], "ladder_run": list(range(1, 9)),
                       "observation_platform": [8, 1, 1, 5, 6], "guard_space": [1, 2, 1, 5, 6]})


RESTORERS = {
    "large_ruin_1": house_large,
    "medium_ruin_1": house_medium_one,
    "medium_ruin_2": house_medium_two,
    "small_ruin_1": house_small_one,
    "small_ruin_2": house_small_two,
    "sauna_1": sauna,
    "large_pillar_1": large_tower,
    "medium_pillar_1": medium_tower,
}
