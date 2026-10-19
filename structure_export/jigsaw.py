"""Jigsaw connector inspection and seam/rotation validation."""

from __future__ import annotations

from typing import Any

ROTATIONS = {"none", "clockwise_90", "180", "counterclockwise_90"}
_DIRECTIONS = ("north", "east", "south", "west")
_FACE_VECTORS = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}


def _parts(template: dict[str, Any]) -> tuple[tuple[int, int, int], list[dict[str, Any]], list[dict[str, Any]]]:
    size = template.get("size")
    palette = template.get("palette")
    blocks = template.get("blocks")
    if not isinstance(size, list) or len(size) != 3 or not isinstance(palette, list) or not isinstance(blocks, list):
        raise ValueError("Not a valid structure template")
    return tuple(size), palette, blocks


def _face(orientation: str) -> str:
    if not isinstance(orientation, str) or "_" not in orientation:
        raise ValueError(f"Invalid jigsaw orientation: {orientation!r}")
    face, up = orientation.split("_", 1)
    if face not in _DIRECTIONS or up != "up":
        raise ValueError(f"Only horizontal *_up jigsaw orientations are supported, got {orientation!r}")
    return face


def _rotate_direction(direction: str, rotation: str) -> str:
    if rotation not in ROTATIONS:
        raise ValueError(f"Unsupported template rotation: {rotation}")
    turns = {"none": 0, "clockwise_90": 1, "180": 2, "counterclockwise_90": 3}[rotation]
    return _DIRECTIONS[(_DIRECTIONS.index(direction) + turns) % 4]


def rotate_position(
    pos: tuple[int, int, int],
    size: tuple[int, int, int] | list[int],
    rotation: str,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Rotate a block position clockwise about the template's vertical axis."""
    if rotation not in ROTATIONS:
        raise ValueError(f"Unsupported template rotation: {rotation}")
    x, y, z = pos
    width, height, depth = size
    if rotation == "none":
        return (x, y, z), (width, height, depth)
    if rotation == "clockwise_90":
        return (depth - 1 - z, y, x), (depth, height, width)
    if rotation == "180":
        return (width - 1 - x, y, depth - 1 - z), (width, height, depth)
    return (z, y, width - 1 - x), (depth, height, width)


def find_jigsaw(template: dict[str, Any], pos: tuple[int, int, int] | list[int]) -> dict[str, Any]:
    """Return validated block-state and block-entity data for a connector at ``pos``."""
    _, palette, blocks = _parts(template)
    target_pos = tuple(pos)
    for block in blocks:
        if tuple(block.get("pos", ())) != target_pos:
            continue
        state_id = block.get("state")
        if not isinstance(state_id, int) or not 0 <= state_id < len(palette):
            raise ValueError(f"Invalid state reference at connector position {target_pos}")
        state = palette[state_id]
        entity = block.get("nbt")
        if state.get("id") != "minecraft:jigsaw" or not isinstance(entity, dict) or entity.get("id") != "minecraft:jigsaw":
            raise ValueError(f"No jigsaw block and block entity at {target_pos}")
        properties = state.get("properties", {})
        orientation = properties.get("orientation") if isinstance(properties, dict) else None
        face = _face(orientation)
        for key in ("name", "target", "pool", "final_state"):
            if not isinstance(entity.get(key), str):
                raise ValueError(f"Jigsaw at {target_pos} is missing string field {key!r}")
        return {"pos": target_pos, "face": face, **entity}
    raise ValueError(f"No jigsaw block at {target_pos}")


def _validate_mouth(template: dict[str, Any], connector: dict[str, Any], *, width: int, height: int) -> None:
    size, palette, blocks = _parts(template)
    sx, sy, sz = size
    x, y, z = connector["pos"]
    face = connector["face"]
    if face == "north" and z != 0:
        raise ValueError(f"Jigsaw mouth facing north is not on its north edge: {connector['pos']}")
    if face == "south" and z != sz - 1:
        raise ValueError(f"Jigsaw mouth facing south is not on its south edge: {connector['pos']}")
    if face == "west" and x != 0:
        raise ValueError(f"Jigsaw mouth facing west is not on its west edge: {connector['pos']}")
    if face == "east" and x != sx - 1:
        raise ValueError(f"Jigsaw mouth facing east is not on its east edge: {connector['pos']}")
    if y + height > sy:
        raise ValueError(f"Jigsaw mouth exceeds the template height at {connector['pos']}")
    if face in {"north", "south"}:
        lateral = ((x + dx, y + dy, z) for dx in range(-(width // 2), width // 2 + 1) for dy in range(height))
    else:
        lateral = ((x, y + dy, z + dz) for dz in range(-(width // 2), width // 2 + 1) for dy in range(height))
    states = {tuple(block["pos"]): palette[block["state"]]["id"] for block in blocks}
    missing = [pos for pos in lateral if states.get(pos) not in {"minecraft:air", "minecraft:jigsaw"}]
    if missing:
        raise ValueError(f"Jigsaw mouth at {connector['pos']} is obstructed at {missing[0]}")


def connect_templates(
    parent: dict[str, Any],
    parent_pos: tuple[int, int, int] | list[int],
    child: dict[str, Any],
    child_pos: tuple[int, int, int] | list[int],
    *,
    rotation: str = "none",
    doorway_width: int = 3,
    doorway_height: int = 4,
) -> dict[str, Any]:
    """Validate connector names, opposing directions, door openings, and child placement.

    The returned origin is the child's translated template origin for a parent whose origin is
    ``(0, 0, 0)``. Vanilla places the child so its jigsaw block occupies the cell directly in
    front of the parent's jigsaw block, i.e. the two connector blocks are adjacent and the
    templates do not overlap. Both are replaced by their configured final states.
    """
    if doorway_width <= 0 or doorway_width % 2 != 1 or doorway_height <= 0:
        raise ValueError("Doorway dimensions require a positive odd width and positive height")
    parent_connector = find_jigsaw(parent, parent_pos)
    child_connector = find_jigsaw(child, child_pos)
    if parent_connector["target"] != child_connector["name"]:
        raise ValueError(
            f"Jigsaw target {parent_connector['target']!r} does not match child name {child_connector['name']!r}"
        )
    if parent_connector["pool"] == "minecraft:empty":
        raise ValueError("Parent jigsaw connector uses minecraft:empty and cannot place a child")
    parent_size, _, _ = _parts(parent)
    child_size, _, _ = _parts(child)
    parent_pos = tuple(parent_pos)
    child_pos = tuple(child_pos)
    _validate_mouth(parent, parent_connector, width=doorway_width, height=doorway_height)
    _validate_mouth(child, child_connector, width=doorway_width, height=doorway_height)
    rotated_pos, rotated_size = rotate_position(child_pos, child_size, rotation)
    child_face = _rotate_direction(child_connector["face"], rotation)
    expected = _DIRECTIONS[(_DIRECTIONS.index(parent_connector["face"]) + 2) % 4]
    if child_face != expected:
        raise ValueError(f"Jigsaw faces do not oppose: parent {parent_connector['face']}, child {child_face}")
    front = _FACE_VECTORS[parent_connector["face"]]
    origin = tuple(parent_pos[i] + front[i] - rotated_pos[i] for i in range(3))
    return {
        "origin": origin,
        "rotation": rotation,
        "parent_pos": parent_pos,
        "child_connector_world_pos": tuple(origin[i] + rotated_pos[i] for i in range(3)),
        "parent_facing": parent_connector["face"],
        "world_child_facing": child_face,
        "child_size_after_rotation": rotated_size,
    }
