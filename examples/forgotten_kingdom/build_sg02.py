#!/usr/bin/env python3
"""Build the SG-02 expanded central cavern with multi-level room interfaces and reserved-volume stubs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kingdom_common import (
    BASE, CENTER, LOWER_U, UPPER_U, DATA_VERSION, LOWER_DOOR, LOWER_POOL, NAMESPACE, OPPOSITE, PACK_FORMAT,
    REPO_ROOT, SIDES, SIZE, TUNNEL_DOOR, UPPER_DOOR, UPPER_POOL, to_26_3,
)
from build_cavern import _tunnel
from worldgen_steps import SG02_STEP, STRUCTURE_STEP
from sg02_cavern import build_chamber, side_xz
from sg02_stubs import lower_stub, upper_stub
from structure_export.datapack import DatapackBuilder
from structure_export.jigsaw import ROTATIONS, connect_templates
from structure_export.structure import grid_to_structure

ROTATION_BY_TURNS = ("none", "clockwise_90", "180", "counterclockwise_90")
MAIN = f"{BASE}/main_chamber"
LOWER_STUB_ID = f"{BASE}/rooms/lower/stub"
UPPER_STUB_ID = f"{BASE}/rooms/upper/stub"
DEFAULT_OUTPUT = REPO_ROOT / "exports/sg-02/forgotten-underground-kingdom/datapack"


def room_modules() -> dict[str, tuple[Any, dict]]:
    """Room templates for the lower and upper pools; SG-03 replaces this with the real modules."""
    return {LOWER_STUB_ID: lower_stub(), UPPER_STUB_ID: upper_stub()}


def lower_pool_members() -> list[str]:
    return [LOWER_STUB_ID]


def upper_pool_members() -> list[str]:
    return [UPPER_STUB_ID]


def build_templates(rooms: dict[str, tuple[Any, dict]] | None = None) -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    grid, entities = build_chamber()
    templates[MAIN] = to_26_3(grid_to_structure(grid, data_version=DATA_VERSION, block_entities=entities))
    for direction in SIDES:
        tgrid, tentities = _tunnel(direction)
        templates[f"{BASE}/tunnel_{direction}"] = to_26_3(grid_to_structure(
            tgrid, data_version=DATA_VERSION, block_entities=tentities
        ))
    for identifier, (rgrid, rentities) in (rooms if rooms is not None else room_modules()).items():
        templates[identifier] = to_26_3(grid_to_structure(rgrid, data_version=DATA_VERSION, block_entities=rentities))
    return templates


def rotation_for(parent_face: str, child_face: str = "south") -> str:
    """Template rotation that turns a child authored facing ``child_face`` to oppose ``parent_face``."""
    want = OPPOSITE[parent_face]
    return ROTATION_BY_TURNS[(SIDES.index(want) - SIDES.index(child_face)) % 4]


def connector_positions() -> dict[str, dict[str, tuple[int, int, int]]]:
    """Chamber-local jigsaw positions keyed ``tunnel_<side>``, ``lower_<side>_<a|b>``, ``upper_<side>_<a|b>``."""
    from kingdom_common import LOWER_JIG_Y, UPPER_JIG_Y

    result: dict[str, dict[str, tuple[int, int, int]]] = {"tunnel": {}, "lower": {}, "upper": {}}
    for side in SIDES:
        x, z = side_xz(side, CENTER, 0)
        result["tunnel"][side] = (x, 1, z)
        for slot, u in zip(("a", "b"), LOWER_U):
            x, z = side_xz(side, u, 0)
            result["lower"][f"{side}_{slot}"] = (x, LOWER_JIG_Y, z)
        for slot, u in zip(("a", "b"), UPPER_U):
            x, z = side_xz(side, u, 0)
            result["upper"][f"{side}_{slot}"] = (x, UPPER_JIG_Y, z)
    return result


def validate_connections(templates: dict[str, dict[str, Any]], lower: str, upper: str) -> dict[str, dict[str, Any]]:
    """Run the exporter's seam validation for every tunnel and room connector."""
    chamber = templates[MAIN]
    positions = connector_positions()
    results: dict[str, dict[str, Any]] = {}
    tunnel_children = {
        "north": (2, 1, 14), "east": (0, 1, 2), "south": (2, 1, 0), "west": (14, 1, 2),
    }
    for side, parent_pos in positions["tunnel"].items():
        results[f"tunnel_{side}"] = connect_templates(
            chamber, parent_pos, templates[f"{BASE}/tunnel_{side}"], tunnel_children[side],
            doorway_width=TUNNEL_DOOR[0], doorway_height=TUNNEL_DOOR[1],
        )
    for kind, room, door in (("lower", lower, LOWER_DOOR), ("upper", upper, UPPER_DOOR)):
        room_t = templates[room]
        child_pos = next(
            tuple(b["pos"]) for b in room_t["blocks"]
            if b.get("nbt", {}).get("id") == "minecraft:jigsaw"
        )
        for key, parent_pos in positions[kind].items():
            side = key.split("_")[0]
            results[f"{kind}_{key}"] = connect_templates(
                chamber, parent_pos, room_t, child_pos, rotation=rotation_for(side),
                doorway_width=door[0], doorway_height=door[1],
            )
    return results


def write_pack(
    output: Path | str,
    templates: dict[str, dict[str, Any]],
    lower: list[str],
    upper: list[str],
    description: str = "MoreMinecrafts Forgotten Underground Kingdom — SG-02 cavern expansion",
    protection_manifest: bool = False,
    structure_step: str = STRUCTURE_STEP,
) -> Path:
    pack = DatapackBuilder(output, namespace=NAMESPACE, pack_format=PACK_FORMAT, description=description)
    for identifier, template in templates.items():
        pack.add_structure(identifier, template)
    start_pool = f"{BASE}/start"
    pack.add_template_pool(start_pool, [MAIN])
    for direction in SIDES:
        pack.add_template_pool(f"{BASE}/tunnels/{direction}", [f"{BASE}/tunnel_{direction}"])
    pack.add_template_pool(LOWER_POOL, lower)
    pack.add_template_pool(UPPER_POOL, upper)
    structure_id = f"{NAMESPACE}:forgotten_kingdom/central_cavern"
    pack.add_jigsaw_structure(
        structure_id,
        start_pool=start_pool,
        size=1,
        step=structure_step,
        terrain_adaptation="encapsulate",
        max_distance_from_center=112,
        start_height={
            "type": "minecraft:uniform",
            "min_inclusive": {"absolute": -40},
            "max_inclusive": {"absolute": -20},
        },
        biome_tag="#minecraft:is_overworld",
        dimension_padding=10,
    )
    pack.add_random_spread_set(
        structure_id,
        structure=structure_id,
        spacing=34,
        separation=12,
        salt=20261017,
        biome_tag="#minecraft:is_overworld",
        exclusion_structure="minecraft:trial_chambers",
        exclusion_chunk_radius=12,
    )
    if protection_manifest:
        pack.add_protection_manifest([structure_id])
    return pack.write().parent


def build_pack(output: Path | str) -> Path:
    templates = build_templates()
    validate_connections(templates, LOWER_STUB_ID, UPPER_STUB_ID)
    return write_pack(output, templates, lower_pool_members(), upper_pool_members(), structure_step=SG02_STEP)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    print(build_pack(args.output))


if __name__ == "__main__":
    main()
