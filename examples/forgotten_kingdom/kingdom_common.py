"""Shared voxel helpers and layout constants for the SG-02/SG-03 Forgotten Underground Kingdom."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid

NAMESPACE = "moreminecrafts"
BASE = "moreminecrafts:forgotten_kingdom/central_cavern"
DATA_VERSION = 5023
PACK_FORMAT = 121

SIDES = ("north", "east", "south", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

# --- Central cavern envelope (SG-02) -------------------------------------------------------
# SG-01 was 41x17x41. The envelope grows by GROW blocks on every side (the exporter's
# 48-block template limit makes 47 the largest symmetric envelope); the plaza, stairs and
# pillars are the SG-01 geometry translated by GROW.
OLD_SIZE = 41
GROW = 3
SIZE = OLD_SIZE + 2 * GROW  # 47
HEIGHT = 17
CENTER = SIZE // 2  # 23

# Side-local depth ``d`` is the distance inward from the outer shell plane (d=0).
MASS_DEPTH = 4            # d=1..4: solid gallery-back masonry (carries vestibules and niches)
DECK_NEAR, DECK_FAR = 5, 9  # d=5..9 elevated deck floor at y=8; d=9 is the plaza-facing edge
DECK_Y = 8
LANE_DEPTHS = tuple(range(DECK_NEAR, DECK_FAR))  # d=5..8: four fully clear walking lanes
STAIR_WIDTH_U = (CENTER - 1, CENTER, CENTER + 1)
STAIR_FIRST_D, STAIR_STEPS = 16, 7  # step i is at d=16-i, y=i+1 (SG-01 geometry, translated)

# --- Room connection interfaces -------------------------------------------------------------
UPPER_U = (11, 35)  # upper-room lateral slots on every side, symmetric about CENTER
# Lower doors sit at u=8/38 so that the SG-01 pillar footings (x/z 11..15 and 31..35) never stand
# in the line of sight between the plaza and a door.
LOWER_U = (8, 38)
TUNNEL_DOOR = (3, 4)    # width, height (SG-01)
LOWER_DOOR = (3, 4)
UPPER_DOOR = (5, 5)
LOWER_JIG_Y = 1         # feet level above the plaza-level floor (y=0)
UPPER_JIG_Y = 10        # feet level above the vestibule floor (y=9)
UPPER_FLOOR_Y = 9

# Maximum room footprints guaranteed collision-free by construction, measured in the room's
# own frame (entry centred on its south edge): (lateral width, height, depth outward).
# Lateral extents stay inside the chamber's own 0..SIZE-1 span, so rooms on adjacent sides can
# never meet at a corner, and the two slots on one side cannot meet each other. Lower rooms
# additionally stay clear of the centre tunnel; upper rooms start above the tunnel's top layer.
LOWER_MAX = (17, 9, 24)
UPPER_MAX = (23, 17, 32)

LOWER_POOL = f"{BASE}/lower_rooms"
UPPER_POOL = f"{BASE}/upper_rooms"
LOWER_ENTRY = f"{NAMESPACE}:forgotten_kingdom/lower_room_entry"
UPPER_ENTRY = f"{NAMESPACE}:forgotten_kingdom/upper_room_entry"
LOWER_LINK = f"{NAMESPACE}:forgotten_kingdom/lower_room_link"
UPPER_LINK = f"{NAMESPACE}:forgotten_kingdom/upper_room_link"

Entities = dict[tuple[int, int, int], dict[str, object]]

# The vendored mcbuild registry predates 26.3. Blocks it cannot name correctly are authored under
# their registry name and renamed here on export; every exported id is then checked against the
# 26.3 data-generator report (validation/minecraft-visual/block-states-26.3.json) by the tests.
ID_RENAMES_26_3 = {"minecraft:chain": "minecraft:iron_chain"}


def to_26_3(template: dict) -> dict:
    """Rename palette ids to their 26.3 names (in place) and return the template."""
    for entry in template["palette"]:
        entry["id"] = ID_RENAMES_26_3.get(entry["id"], entry["id"])
    return template


def set_block(grid: VoxelGrid, x: int, y: int, z: int, name: str) -> None:
    grid.set(x, y, z, get_block(name).index)


def new_grid(size: tuple[int, int, int]) -> VoxelGrid:
    grid = VoxelGrid()
    sx, sy, sz = size
    air = get_block("air").index
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                grid.set(x, y, z, air)
    return grid


def place_jigsaw(
    grid: VoxelGrid,
    entities: Entities,
    pos: tuple[int, int, int],
    *,
    orientation: str,
    name: str,
    target: str,
    pool: str,
    joint: str = "aligned",
) -> None:
    set_block(grid, *pos, f"jigsaw[orientation={orientation}]")
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


def stairs(facing: str, *, half: str = "bottom", material: str = "deepslate_brick_stairs", shape: str = "straight") -> str:
    return f"{material}[facing={facing},half={half},shape={shape},waterlogged=false]"


def block_name(grid: VoxelGrid, pos: tuple[int, int, int]) -> str | None:
    index = grid.get(*pos)
    if index is None:
        return None
    from mcbuild.palette import get_block_by_index

    return get_block_by_index(index).name


_NON_FULL = ("stairs", "slab", "wall", "jigsaw", "lantern", "fence", "door", "trapdoor", "bars", "button", "carpet")


def _is_full_block(name: str | None) -> bool:
    if name is None or name == "air":
        return False
    if name in {"barrel", "chest", "bookshelf", "chiseled_bookshelf", "cobweb", "sea_lantern"}:
        return name != "cobweb"
    return not any(token in name for token in _NON_FULL)


def finish_walls(grid: VoxelGrid) -> None:
    """Rewrite every deepslate-brick wall with the connection state vanilla would derive."""
    from mcbuild.palette import get_block_by_index

    walls = [pos for pos, index in grid.items() if get_block_by_index(index).name == "deepslate_brick_wall"]
    neighbours = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
    for x, y, z in walls:
        sides = {}
        for side, (dx, _dy, dz) in neighbours.items():
            other = block_name(grid, (x + dx, y, z + dz))
            sides[side] = "low" if other == "deepslate_brick_wall" or _is_full_block(other) else "none"
        n, e, s, w = (sides[k] != "none" for k in ("north", "east", "south", "west"))
        straight = (n and s and not e and not w) or (e and w and not n and not s)
        above = block_name(grid, (x, y + 1, z))
        up = (not straight) or (above is not None and above != "air")
        set_block(
            grid,
            x,
            y,
            z,
            "deepslate_brick_wall["
            f"east={sides['east']},north={sides['north']},south={sides['south']},"
            f"up={'true' if up else 'false'},waterlogged=false,west={sides['west']}]",
        )
