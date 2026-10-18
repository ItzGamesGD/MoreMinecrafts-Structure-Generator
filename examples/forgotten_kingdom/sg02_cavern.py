"""SG-02 central cavern: SG-01 plaza and stairs inside a widened envelope with room interfaces."""

from __future__ import annotations

from typing import Any

from kingdom_common import (
    BASE,
    CENTER,
    LOWER_U,
    UPPER_U,
    DECK_FAR,
    DECK_NEAR,
    DECK_Y,
    GROW,
    HEIGHT,
    LOWER_DOOR,
    LOWER_JIG_Y,
    LOWER_LINK,
    LOWER_ENTRY,
    LOWER_POOL,
    MASS_DEPTH,
    NAMESPACE,
    SIDES,
    SIZE,
    STAIR_FIRST_D,
    STAIR_STEPS,
    STAIR_WIDTH_U,
    TUNNEL_DOOR,
    UPPER_DOOR,
    UPPER_ENTRY,
    UPPER_FLOOR_Y,
    UPPER_JIG_Y,
    UPPER_LINK,
    UPPER_POOL,
    Entities,
    finish_walls,
    new_grid,
    place_jigsaw,
    set_block,
    stairs,
)

PIER_U = (17, 29)       # undercroft piers per side (clear of every door slot)
NICHE_U = (17, 29)
TOP_Y = HEIGHT - 1


def side_xz(side: str, u: int, d: int) -> tuple[int, int]:
    """Map side-local (lateral u, inward depth d) to template x/z."""
    if side == "north":
        return u, d
    if side == "south":
        return u, SIZE - 1 - d
    if side == "west":
        return d, u
    if side == "east":
        return SIZE - 1 - d, u
    raise ValueError(side)


def _put(grid, side: str, u: int, d: int, y: int, name: str) -> None:
    x, z = side_xz(side, u, d)
    set_block(grid, x, y, z, name)


def _mass_material(y: int, d: int) -> str:
    if d == MASS_DEPTH and y == 9:
        return "polished_deepslate"
    if d == MASS_DEPTH and y == 13:
        return "chiseled_tuff_bricks"
    if y >= 13:
        return "tuff_bricks"
    if y == DECK_Y:
        return "deepslate_tiles"
    return "deepslate_bricks"


def build_chamber() -> tuple[Any, Entities]:
    grid = new_grid((SIZE, HEIGHT, SIZE))
    entities: Entities = {}
    sx = SIZE

    # Plaza floor and vaulted roof follow the SG-01 radial pattern about the (translated) centre.
    for x in range(sx):
        for z in range(sx):
            radius = max(abs(x - CENTER), abs(z - CENTER))
            floor = "polished_deepslate" if radius <= 7 else "tuff_bricks" if radius == 8 else "deepslate_tiles"
            if radius in (6, 8) and (x + z) % 2 == 0:
                floor = "chiseled_tuff_bricks"
            set_block(grid, x, 0, z, floor)
            set_block(grid, x, TOP_Y, z, "deepslate_tiles" if radius % 5 else "tuff_bricks")

    # Outer shell (d=0) on all four sides.
    for y in range(1, TOP_Y):
        material = "tuff_bricks" if y >= 13 else "deepslate_bricks"
        for edge in range(sx):
            for x, z in ((edge, 0), (edge, sx - 1), (0, edge), (sx - 1, edge)):
                set_block(grid, x, y, z, material)

    for side in SIDES:
        # Gallery-back masonry: a solid band at deck level and above, supported on the undercroft.
        for u in range(0, sx):
            for d in range(1, MASS_DEPTH + 1):
                for y in range(DECK_Y, TOP_Y):
                    _put(grid, side, u, d, y, _mass_material(y, d))
        # Elevated deck, SG-01 checker pattern continued in SG-01 (translated) coordinates.
        for u in range(DECK_NEAR, sx - DECK_NEAR):
            for d in range(DECK_NEAR, DECK_FAR + 1):
                x, z = side_xz(side, u, d)
                xo, zo = x - GROW, z - GROW
                set_block(grid, x, DECK_Y, z, "deepslate_tiles" if (xo + zo) % 7 else "tuff_bricks")
            # Fascia beam under the plaza-facing edge.
            _put(grid, side, u, DECK_FAR, DECK_Y - 1, "deepslate_bricks")

    # Piers carrying the deck: one pier either side of centre on every side.
    def pier(cx: int, cz: int, half: int) -> None:
        for x in range(cx - half, cx + half + 1):
            for z in range(cz - half, cz + half + 1):
                set_block(grid, x, 1, z, "deepslate_bricks")
                for y in range(2, DECK_Y - 1):
                    set_block(grid, x, y, z, "polished_deepslate")
                set_block(grid, x, DECK_Y - 1, z, "tuff_bricks")

    for side in SIDES:
        for u in PIER_U:
            x, z = side_xz(side, u, 7)
            pier(x, z, 1)

    # Recessed lamp niches facing the lanes, and a flush heraldic panel over each stair landing.
    for side in SIDES:
        for u in NICHE_U:
            for du in (-1, 0, 1):
                for d in (MASS_DEPTH - 1, MASS_DEPTH):
                    for y in range(10, 13):
                        _put(grid, side, u + du, d, y, "air")
            _put(grid, side, u, MASS_DEPTH - 2, 11, "sea_lantern")
        for du in (-1, 0, 1):
            for y in range(10, 13):
                _put(grid, side, CENTER + du, MASS_DEPTH, y, "chiseled_tuff_bricks")

    # SG-01 support piers (translated).
    for cx in (10 + GROW, 30 + GROW):
        for cz in (10 + GROW, 30 + GROW):
            for y in (1, 2, 14, 15):
                material = "chiseled_tuff_bricks" if y in (2, 14) else "tuff_bricks"
                for x in range(cx - 2, cx + 3):
                    for z in range(cz - 2, cz + 3):
                        set_block(grid, x, y, z, material)
            for y in range(3, 14):
                material = "polished_deepslate" if y % 4 else "deepslate_bricks"
                for x in range(cx - 1, cx + 2):
                    for z in range(cz - 1, cz + 2):
                        set_block(grid, x, y, z, material)

    # SG-01 stair runs (unmoved relative to the plaza), now deepslate brick stairs.
    for side in SIDES:
        for i in range(STAIR_STEPS):
            for u in STAIR_WIDTH_U:
                _put(grid, side, u, STAIR_FIRST_D - i, i + 1, stairs(side))

    # The SG-01 run ends one block below the deck (last step back-top y=8 vs deck top y=9). One more
    # stair at deck level (the open stair mouth) makes the climb continuous without moving any step.
    for side in SIDES:
        for u in STAIR_WIDTH_U:
            _put(grid, side, u, DECK_FAR, DECK_Y, stairs(side))

    # Doorways. Tunnels (SG-01 3x4) at the centre of each side.
    def carve(side: str, u: int, width: int, y0: int, height: int, depth: int) -> None:
        for du in range(-(width // 2), width // 2 + 1):
            for d in range(depth):
                for y in range(y0, y0 + height):
                    _put(grid, side, u + du, d, y, "air")

    for side in SIDES:
        carve(side, CENTER, TUNNEL_DOOR[0], 1, TUNNEL_DOOR[1], 1)
        for u in LOWER_U:
            carve(side, u, LOWER_DOOR[0], 1, LOWER_DOOR[1], 1)
            for dy in range(1, LOWER_DOOR[1] + 1):
                for du in (-2, 2):
                    _put(grid, side, u + du, 0, dy, "polished_deepslate")
            for du in range(-2, 3):
                _put(grid, side, u + du, 0, LOWER_DOOR[1] + 1, "polished_deepslate")
            # Undercroft ceiling lamp beside each lower door.
            _put(grid, side, u, 2, DECK_Y, "sea_lantern")
        for u in UPPER_U:
            # Upper vestibule: 5x5 passage through the gallery-back masonry, floor at y=9,
            # joined to the y=8 deck lane by a one-block stair so the sill is never a jump.
            carve(side, u, UPPER_DOOR[0], UPPER_JIG_Y, UPPER_DOOR[1], MASS_DEPTH + 1)
            for du in range(-(UPPER_DOOR[0] // 2), UPPER_DOOR[0] // 2 + 1):
                _put(grid, side, u + du, MASS_DEPTH, UPPER_FLOOR_Y, stairs(side))
                for d in range(MASS_DEPTH):
                    _put(grid, side, u + du, d, UPPER_FLOOR_Y, "deepslate_tiles")
            # Chiseled lintel above the upper doorway.
            for du in range(-3, 4):
                _put(grid, side, u + du, 0, UPPER_JIG_Y + UPPER_DOOR[1], "chiseled_tuff_bricks")

    # Plaza-facing rails: deepslate brick walls on the deck's exposed inner edge, open at the stairs.
    inner = DECK_FAR
    lo, hi = inner, SIZE - 1 - inner
    for side in SIDES:
        for u in range(lo, hi + 1):
            if abs(u - CENTER) <= 1:
                continue
            _put(grid, side, u, inner, DECK_Y + 1, "deepslate_brick_wall")
    finish_walls(grid)

    # Roof lighting: SG-01 positions (translated) plus lamps over the deck lanes.
    old_lights = ((20, 20), (9, 20), (31, 20), (20, 9), (20, 31), (20, 5), (35, 20), (20, 35), (5, 20))
    for ox, oz in old_lights:
        set_block(grid, ox + GROW, TOP_Y - 1, oz + GROW, "sea_lantern")
    for side in SIDES:
        for u in UPPER_U:
            _put(grid, side, u, 7, TOP_Y - 1, "sea_lantern")

    # Jigsaw connectors.
    for side in SIDES:
        orientation = f"{side}_up"
        tx, tz = side_xz(side, CENTER, 0)
        place_jigsaw(
            grid,
            entities,
            (tx, 1, tz),
            orientation=orientation,
            name=f"{NAMESPACE}:forgotten_kingdom/cavern_link",
            target=f"{NAMESPACE}:forgotten_kingdom/tunnel_in_{side}",
            pool=f"{BASE}/tunnels/{side}",
        )
        for slot, u in zip(("a", "b"), LOWER_U):
            x, z = side_xz(side, u, 0)
            place_jigsaw(
                grid, entities, (x, LOWER_JIG_Y, z), orientation=orientation,
                name=f"{LOWER_LINK}_{side}_{slot}", target=LOWER_ENTRY, pool=LOWER_POOL,
            )
        for slot, u in zip(("a", "b"), UPPER_U):
            x, z = side_xz(side, u, 0)
            place_jigsaw(
                grid, entities, (x, UPPER_JIG_Y, z), orientation=orientation,
                name=f"{UPPER_LINK}_{side}_{slot}", target=UPPER_ENTRY, pool=UPPER_POOL,
            )
    return grid, entities
