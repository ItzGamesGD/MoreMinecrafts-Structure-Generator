#!/usr/bin/env python3
"""Build the SG-01 Forgotten Underground Kingdom cavern and its portable data pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid
from structure_export.datapack import DatapackBuilder
from structure_export.jigsaw import connect_templates
from structure_export.structure import grid_to_structure

NAMESPACE = "moreminecrafts"
BASE = "moreminecrafts:forgotten_kingdom/central_cavern"
DATA_VERSION = 5023
PACK_FORMAT = 121
ROOM_SIZE = (41, 17, 41)
DOOR_WIDTH = 3
DOOR_HEIGHT = 4


def _set(grid: VoxelGrid, x: int, y: int, z: int, name: str) -> None:
    grid.set(x, y, z, get_block(name).index)


def _grid(size: tuple[int, int, int]) -> VoxelGrid:
    grid = VoxelGrid()
    sx, sy, sz = size
    air = get_block("air").index
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                grid.set(x, y, z, air)
    return grid


def _jigsaw(
    grid: VoxelGrid,
    entities: dict[tuple[int, int, int], dict[str, object]],
    pos: tuple[int, int, int],
    *,
    orientation: str,
    name: str,
    target: str,
    pool: str,
    joint: str = "aligned",
) -> None:
    _set(grid, *pos, f"jigsaw[orientation={orientation}]")
    entities[pos] = {
        "id": "minecraft:jigsaw",
        "name": name,
        "target": target,
        "pool": pool,
        "joint": joint,
        "final_state": "minecraft:air",
        "placement_priority": 0,
        "selection_priority": 0,
    }


def _chamber() -> tuple[VoxelGrid, dict[tuple[int, int, int], dict[str, object]]]:
    sx, sy, sz = ROOM_SIZE
    grid = _grid(ROOM_SIZE)
    entities: dict[tuple[int, int, int], dict[str, object]] = {}
    center = sx // 2

    for x in range(sx):
        for z in range(sz):
            radius = max(abs(x - center), abs(z - center))
            floor = "polished_deepslate" if radius <= 7 else "tuff_bricks" if radius == 8 else "deepslate_tiles"
            if radius in (6, 8) and (x + z) % 2 == 0:
                floor = "chiseled_tuff_bricks"
            _set(grid, x, 0, z, floor)
            ceiling = "deepslate_tiles" if radius % 5 else "tuff_bricks"
            _set(grid, x, sy - 1, z, ceiling)

    for y in range(1, sy - 1):
        for edge in range(sx):
            material = "tuff_bricks" if y >= 13 else "deepslate_bricks"
            for x, z in ((edge, 0), (edge, sz - 1), (0, edge), (sx - 1, edge)):
                _set(grid, x, y, z, material)

    # Four built doorways are the only openings through the chamber's outer shell.
    for dx in range(-(DOOR_WIDTH // 2), DOOR_WIDTH // 2 + 1):
        for y in range(1, DOOR_HEIGHT + 1):
            for pos in ((center + dx, y, 0), (center + dx, y, sz - 1), (0, y, center + dx), (sx - 1, y, center + dx)):
                _set(grid, *pos, "air")

    # Broad support piers with heavier footings and capitals carry the vaulted roof.
    for cx in (10, 30):
        for cz in (10, 30):
            for y in (1, 2, 14, 15):
                material = "chiseled_tuff_bricks" if y in (2, 14) else "tuff_bricks"
                for x in range(cx - 2, cx + 3):
                    for z in range(cz - 2, cz + 3):
                        _set(grid, x, y, z, material)
            for y in range(3, 14):
                material = "polished_deepslate" if y % 4 else "deepslate_bricks"
                for x in range(cx - 1, cx + 2):
                    for z in range(cz - 1, cz + 2):
                        _set(grid, x, y, z, material)

    # An elevated continuous balcony ring gives the cavern a second walkable level.
    for x in range(4, 37):
        for z in (4, 5, 6, 34, 35, 36):
            _set(grid, x, 8, z, "deepslate_tiles" if (x + z) % 7 else "tuff_bricks")
    for z in range(7, 34):
        for x in (4, 5, 6, 34, 35, 36):
            _set(grid, x, 8, z, "deepslate_tiles" if (x + z) % 7 else "tuff_bricks")

    # Low wall rails on the outer side of the elevated walkways.
    for x in range(4, 37):
        for z in (4, 36):
            if not 18 <= x <= 22:
                _set(grid, x, 9, z, "deepslate_brick_wall")
    for z in range(7, 34):
        for x in (4, 36):
            if not 18 <= z <= 22:
                _set(grid, x, 9, z, "deepslate_brick_wall")

    # Four broad stair runs connect the plaza floor to the upper ring. Eight steps: the eighth sits in the ring's
    # inner band (level 8) so its back is flush with the ring floor surface and no 1.0-block jump is needed.
    for i in range(8):
        level = i + 1
        offset = 13 - i
        for x in range(center - 1, center + 2):
            _set(grid, x, level, offset, "stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
            _set(grid, x, level, sz - 1 - offset, "stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
        for z in range(center - 1, center + 2):
            _set(grid, sz - 1 - offset, level, z, "stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
            _set(grid, offset, level, z, "stone_brick_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")

    # Subtle vanilla lighting is built into the roof and upper corners.
    for x, z in ((center, center), (9, center), (31, center), (center, 9), (center, 31), (20, 5), (35, 20), (20, 35), (5, 20)):
        _set(grid, x, 15, z, "sea_lantern")

    sockets = (
        ((center, 1, 0), "north_up", "north"),
        ((sx - 1, 1, center), "east_up", "east"),
        ((center, 1, sz - 1), "south_up", "south"),
        ((0, 1, center), "west_up", "west"),
    )
    for pos, orientation, direction in sockets:
        _jigsaw(
            grid,
            entities,
            pos,
            orientation=orientation,
            name=f"{NAMESPACE}:forgotten_kingdom/cavern_link",
            target=f"{NAMESPACE}:forgotten_kingdom/tunnel_in_{direction}",
            pool=f"{BASE}/tunnels/{direction}",
        )
    return grid, entities


def _tunnel(direction: str) -> tuple[VoxelGrid, dict[tuple[int, int, int], dict[str, object]]]:
    if direction in {"north", "south"}:
        size = (5, 9, 15)
        side_wall = lambda layer, depth: ((0, layer, depth), (4, layer, depth))
        if direction == "north":
            inbound = ((2, 1, 14), "south_up")
            outbound = ((2, 1, 0), "north_up")
        else:
            inbound = ((2, 1, 0), "north_up")
            outbound = ((2, 1, 14), "south_up")
    elif direction in {"east", "west"}:
        size = (15, 9, 5)
        side_wall = lambda layer, depth: ((depth, layer, 0), (depth, layer, 4))
        if direction == "east":
            inbound = ((0, 1, 2), "west_up")
            outbound = ((14, 1, 2), "east_up")
        else:
            inbound = ((14, 1, 2), "east_up")
            outbound = ((0, 1, 2), "west_up")
    else:
        raise ValueError(f"Unknown tunnel direction: {direction}")

    grid = _grid(size)
    entities: dict[tuple[int, int, int], dict[str, object]] = {}
    sx, sy, sz = size
    for x in range(sx):
        for z in range(sz):
            _set(grid, x, 0, z, "deepslate_tiles")
            _set(grid, x, sy - 1, z, "tuff_bricks")
    for depth in range(max(sx, sz)):
        for y in range(1, sy - 1):
            for pos in side_wall(y, depth):
                x, _, z = pos
                if x < sx and z < sz:
                    _set(grid, *pos, "tuff_bricks" if depth % 5 == 0 else "deepslate_bricks")
        # Recessed transverse ribs emphasize tunnel rhythm and support the roof span.
        if depth in (4, 9):
            for x in range(sx):
                for z in range(sz):
                    if x in (0, sx - 1) or z in (0, sz - 1):
                        _set(grid, x, sy - 2, z, "polished_deepslate")

    # End walls remain built around a 3-by-4 doorway.
    # Openings are already air; close each end outside the aperture.
    for end_depth in ({0, sz - 1} if direction in {"north", "south"} else {0, sx - 1}):
        for lateral in range(1, (sx if direction in {"north", "south"} else sz) - 1):
            for y in range(1, sy - 1):
                if not (1 <= y <= DOOR_HEIGHT):
                    if direction in {"north", "south"}:
                        _set(grid, lateral, y, end_depth, "tuff_bricks")
                    else:
                        _set(grid, end_depth, y, lateral, "tuff_bricks")
        # Door lintels above the opening and jambs beside it are solid built blocks.
        for lateral in range((sx if direction in {"north", "south"} else sz)):
            if lateral not in range(1, (sx if direction in {"north", "south"} else sz) - 1):
                for y in range(1, sy - 1):
                    if direction in {"north", "south"}:
                        _set(grid, lateral, y, end_depth, "deepslate_bricks")
                    else:
                        _set(grid, end_depth, y, lateral, "deepslate_bricks")

    inbound_pos, inbound_orientation = inbound
    outbound_pos, outbound_orientation = outbound
    _jigsaw(
        grid,
        entities,
        inbound_pos,
        orientation=inbound_orientation,
        name=f"{NAMESPACE}:forgotten_kingdom/tunnel_in_{direction}",
        target="minecraft:empty",
        pool="minecraft:empty",
    )
    _jigsaw(
        grid,
        entities,
        outbound_pos,
        orientation=outbound_orientation,
        name=f"{NAMESPACE}:forgotten_kingdom/cavern_exit",
        target=f"{NAMESPACE}:forgotten_kingdom/district_entrance",
        pool="minecraft:empty",
    )
    return grid, entities


def build_templates() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build all templates and return templates plus source grids/block entities."""
    structures: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    chamber_grid, chamber_entities = _chamber()
    chamber_id = f"{BASE}/main_chamber"
    structures[chamber_id] = grid_to_structure(
        chamber_grid, data_version=DATA_VERSION, block_entities=chamber_entities
    )
    sources[chamber_id] = {"grid": chamber_grid, "block_entities": chamber_entities}
    for direction in ("north", "east", "south", "west"):
        grid, entities = _tunnel(direction)
        identifier = f"{BASE}/tunnel_{direction}"
        structures[identifier] = grid_to_structure(grid, data_version=DATA_VERSION, block_entities=entities)
        sources[identifier] = {"grid": grid, "block_entities": entities}
    return structures, sources


def validate_connections(templates: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    chamber_id = f"{BASE}/main_chamber"
    chamber = templates[chamber_id]
    positions = {
        "north": ((20, 1, 0), (2, 1, 14)),
        "east": ((40, 1, 20), (0, 1, 2)),
        "south": ((20, 1, 40), (2, 1, 0)),
        "west": ((0, 1, 20), (14, 1, 2)),
    }
    result = {}
    for direction, (parent_pos, child_pos) in positions.items():
        child = templates[f"{BASE}/tunnel_{direction}"]
        result[direction] = connect_templates(
            chamber,
            parent_pos,
            child,
            child_pos,
            doorway_width=DOOR_WIDTH,
            doorway_height=DOOR_HEIGHT,
        )
    return result


def build_pack(output: Path | str) -> Path:
    templates, _ = build_templates()
    validate_connections(templates)
    pack = DatapackBuilder(output, namespace=NAMESPACE, pack_format=PACK_FORMAT)
    for identifier, template in templates.items():
        pack.add_structure(identifier, template)

    start_pool = f"{BASE}/start"
    pack.add_template_pool(start_pool, [f"{BASE}/main_chamber"])
    for direction in ("north", "east", "south", "west"):
        pack.add_template_pool(f"{BASE}/tunnels/{direction}", [f"{BASE}/tunnel_{direction}"])

    structure_id = f"{NAMESPACE}:forgotten_kingdom/central_cavern"
    pack.add_jigsaw_structure(
        structure_id,
        start_pool=start_pool,
        size=1,
        step="vegetal_decoration",  # SG-01-C F-2: after deep-dark sculk (underground_decoration)
        terrain_adaptation="encapsulate",
        max_distance_from_center=64,
        start_height={
            "type": "minecraft:uniform",
            "min_inclusive": {"absolute": -40},
            "max_inclusive": {"absolute": -20},
        },
        biome_tag="#minecraft:is_overworld",
        dimension_padding=10,
    )
    pack.add_random_spread_set(
        f"{NAMESPACE}:forgotten_kingdom/central_cavern",
        structure=structure_id,
        spacing=34,
        separation=12,
        salt=20261017,
        biome_tag="#minecraft:is_overworld",
        exclusion_structure="minecraft:trial_chambers",
        exclusion_chunk_radius=12,
    )
    return pack.write().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        default=str(REPO_ROOT / "exports/sg-01/forgotten-underground-kingdom/datapack"),
        help="datapack output directory (default: exports/sg-01/forgotten-underground-kingdom/datapack)",
    )
    args = parser.parse_args()
    root = build_pack(args.output)
    print(root)


if __name__ == "__main__":
    main()
