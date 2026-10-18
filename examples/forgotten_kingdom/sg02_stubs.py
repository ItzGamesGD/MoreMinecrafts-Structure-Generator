"""SG-02 reserved-volume room stubs: empty shells at the maximum footprint of each interface."""

from __future__ import annotations

from kingdom_common import (
    LOWER_DOOR,
    LOWER_ENTRY,
    LOWER_MAX,
    UPPER_DOOR,
    UPPER_ENTRY,
    UPPER_MAX,
    Entities,
    new_grid,
    place_jigsaw,
    set_block,
)


def shell_room(size: tuple[int, int, int], door: tuple[int, int], entry: str):
    """Hollow deepslate shell with one south-edge doorway; entry jigsaw centred at floor level + 1."""
    sx, sy, sz = size
    grid = new_grid(size)
    entities: Entities = {}
    for x in range(sx):
        for z in range(sz):
            set_block(grid, x, 0, z, "deepslate_tiles")
            set_block(grid, x, sy - 1, z, "deepslate_bricks")
    for y in range(1, sy - 1):
        for edge_x in range(sx):
            set_block(grid, edge_x, y, 0, "deepslate_bricks")
            set_block(grid, edge_x, y, sz - 1, "deepslate_bricks")
        for edge_z in range(sz):
            set_block(grid, 0, y, edge_z, "deepslate_bricks")
            set_block(grid, sx - 1, y, edge_z, "deepslate_bricks")
    cx = sx // 2
    for dx in range(-(door[0] // 2), door[0] // 2 + 1):
        for y in range(1, 1 + door[1]):
            set_block(grid, cx + dx, y, sz - 1, "air")
    place_jigsaw(
        grid, entities, (cx, 1, sz - 1), orientation="south_up",
        name=entry, target="minecraft:empty", pool="minecraft:empty",
    )
    return grid, entities


def lower_stub():
    return shell_room(LOWER_MAX, LOWER_DOOR, LOWER_ENTRY)


def upper_stub():
    return shell_room(UPPER_MAX, UPPER_DOOR, UPPER_ENTRY)
