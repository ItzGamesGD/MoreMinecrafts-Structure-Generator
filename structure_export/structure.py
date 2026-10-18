"""Export mcbuild voxel grids as vanilla Java structure-template NBT."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from structure_export.nbt import write_nbt

if TYPE_CHECKING:
    from mcbuild.voxel import VoxelGrid

_BLOCK_ENTITY_TYPE_BY_BLOCK = {
    "barrel": "minecraft:barrel",
    "beehive": "minecraft:beehive",
    "blast_furnace": "minecraft:furnace",
    "brewing_stand": "minecraft:brewing_stand",
    "campfire": "minecraft:campfire",
    "chest": "minecraft:chest",
    "command_block": "minecraft:command_block",
    "comparator": "minecraft:comparator",
    "daylight_detector": "minecraft:daylight_detector",
    "dispenser": "minecraft:dispenser",
    "dropper": "minecraft:dropper",
    "furnace": "minecraft:furnace",
    "hanging_sign": "minecraft:hanging_sign",
    "hopper": "minecraft:hopper",
    "jigsaw": "minecraft:jigsaw",
    "lectern": "minecraft:lectern",
    "mob_spawner": "minecraft:mob_spawner",
    "piston_head": "minecraft:piston",
    "sculk_catalyst": "minecraft:sculk_catalyst",
    "sculk_sensor": "minecraft:sculk_sensor",
    "shulker_box": "minecraft:shulker_box",
    "sign": "minecraft:sign",
    "smoker": "minecraft:furnace",
    "spawner": "minecraft:mob_spawner",
    "structure_block": "minecraft:structure_block",
    "trial_spawner": "minecraft:trial_spawner",
    "trapped_chest": "minecraft:chest",
    "vault": "minecraft:vault",
}


def _parse_block_id(mc_id: str) -> tuple[str, dict[str, str]]:
    if "[" in mc_id:
        if not mc_id.endswith("]"):
            raise ValueError(f"Malformed block state: {mc_id}")
        identifier, raw_properties = mc_id[:-1].split("[", 1)
        properties = {}
        for item in raw_properties.split(","):
            if "=" not in item:
                raise ValueError(f"Malformed block-state property in {mc_id}: {item}")
            key, value = item.split("=", 1)
            if not key or not value or key in properties:
                raise ValueError(f"Malformed block-state property in {mc_id}: {item}")
            properties[key] = value
    else:
        identifier, properties = mc_id, {}
    if ":" not in identifier:
        identifier = f"minecraft:{identifier}"
    namespace, path = identifier.split(":", 1)
    if not namespace or not path or any(char.isspace() for char in identifier):
        raise ValueError(f"Malformed block identifier: {identifier}")
    return identifier, properties


def grid_to_structure(
    grid: VoxelGrid,
    *,
    data_version: int,
    block_entities: dict[tuple[int, int, int], dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build a complete structure template, treating sparse/unset cells as explicit air."""
    bounds = grid.bounds
    if bounds is None:
        raise ValueError("Cannot export an empty voxel grid")
    if data_version <= 0:
        raise ValueError("data_version must be a positive integer")
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    size = (max_x - min_x + 1, max_y - min_y + 1, max_z - min_z + 1)
    if any(axis > 48 for axis in size):
        raise ValueError(f"Structure template axes must be at most 48 blocks, got {size}")

    from mcbuild.palette import get_block_by_index

    placed = dict(grid.items())
    supplied_entities = block_entities or {}
    for pos, entity in supplied_entities.items():
        index = placed.get(pos)
        if index is None:
            raise ValueError(f"block_entities entry at {pos} is not a placed block")
        source_block = get_block_by_index(index)
        identifier, _ = _parse_block_id(source_block.mc_id)
        if identifier == "minecraft:air":
            raise ValueError(f"block_entities entry at {pos} is attached to air")
        if not isinstance(entity, dict) or not isinstance(entity.get("id"), str):
            raise ValueError(f"block_entities entry at {pos} must have a string id")
        expected_id = _BLOCK_ENTITY_TYPE_BY_BLOCK.get(source_block.name)
        if expected_id is not None and entity["id"] != expected_id:
            raise ValueError(
                f"block_entities entry at {pos} has id {entity['id']!r}; "
                f"block {source_block.name!r} requires {expected_id!r}"
            )

    air_state = ("minecraft:air", ())
    cell_states: dict[tuple[int, int, int], tuple[str, tuple[tuple[str, str], ...]]] = {}
    for y in range(min_y, max_y + 1):
        for z in range(min_z, max_z + 1):
            for x in range(min_x, max_x + 1):
                index = placed.get((x, y, z))
                if index is None:
                    cell_states[(x, y, z)] = air_state
                    continue
                identifier, properties = _parse_block_id(get_block_by_index(index).mc_id)
                cell_states[(x, y, z)] = (identifier, tuple(sorted(properties.items())))

    palette_states = sorted(set(cell_states.values()))
    palette = []
    state_ids = {}
    for state_id, (identifier, property_items) in enumerate(palette_states):
        entry: dict[str, object] = {"id": identifier}
        if property_items:
            entry["properties"] = dict(property_items)
        palette.append(entry)
        state_ids[(identifier, property_items)] = state_id

    blocks = []
    for world_pos in sorted(cell_states, key=lambda pos: (pos[1], pos[2], pos[0])):
        state = cell_states[world_pos]
        block: dict[str, object] = {
            "pos": [world_pos[0] - min_x, world_pos[1] - min_y, world_pos[2] - min_z],
            "state": state_ids[state],
        }
        if world_pos in supplied_entities:
            block["nbt"] = deepcopy(supplied_entities[world_pos])
        blocks.append(block)

    return {
        "DataVersion": data_version,
        "size": list(size),
        "palette": palette,
        "blocks": blocks,
        "entities": [],
    }


def structure_bytes(template: dict[str, object]) -> bytes:
    """Serialize a template to the gzip-compressed NBT expected by vanilla."""
    validate_structure(template)
    return write_nbt(template)


def validate_structure(template: dict[str, object]) -> None:
    """Check core Java structure-template invariants before writing."""
    required = {"DataVersion", "size", "palette", "blocks", "entities"}
    missing = required - template.keys()
    if missing:
        raise ValueError(f"Structure template is missing required fields: {sorted(missing)}")
    size = template["size"]
    palette = template["palette"]
    blocks = template["blocks"]
    if not isinstance(size, list) or len(size) != 3 or any(not isinstance(v, int) or v <= 0 or v > 48 for v in size):
        raise ValueError("Structure template size must contain three dimensions in the range 1..48")
    if not isinstance(palette, list) or not palette:
        raise ValueError("Structure template palette cannot be empty")
    if not isinstance(blocks, list):
        raise ValueError("Structure template blocks must be a list")
    seen = set()
    for entry in palette:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ValueError("Every palette entry must contain a block id")
        _parse_block_id(entry["id"])
        props = entry.get("properties", {})
        if not isinstance(props, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in props.items()):
            raise ValueError("Block-state properties must be a string-to-string compound")
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("pos"), list) or len(block["pos"]) != 3:
            raise ValueError("Every structure block must have a three-coordinate pos")
        pos = tuple(block["pos"])
        if any(not isinstance(v, int) or v < 0 or v >= size[i] for i, v in enumerate(pos)):
            raise ValueError(f"Structure block position is outside the template: {pos}")
        if pos in seen:
            raise ValueError(f"Duplicate structure block position: {pos}")
        seen.add(pos)
        if not isinstance(block.get("state"), int) or not 0 <= block["state"] < len(palette):
            raise ValueError(f"Structure block state index is outside the palette at {pos}")
        if "nbt" in block and (not isinstance(block["nbt"], dict) or not isinstance(block["nbt"].get("id"), str)):
            raise ValueError(f"Block entity at {pos} must contain a string id")
