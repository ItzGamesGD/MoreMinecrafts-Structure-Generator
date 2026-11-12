"""Block-entity handler for the exporter (the `block_entity` feature in convert.py).

A block entity is written into the template as `nbt` on its block. Its contents are never copied from the
source: the source carries no block-entity data (schem.py rejects `BlockEntities`), so the NBT is what the
allow-list in reference/block_entities-26.3.json says, and nothing else. That keeps containers empty in the
template; loot is assigned at generation time by the mod, not by the template.

Responsibilities are split like this:
- block states (facing, waterlogged, ...) are block-state data: the converter writes them as-is and the game
  rotates them with the template; a rotated template therefore needs no change to these states here.
- the block-entity NBT has no orientation and no position (no x/y/z), so a template rotation never changes it.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from nbtlib.tag import Compound, Int, List, String

from .errors import UnsupportedFeature

REFERENCE = Path(__file__).resolve().parent / "reference" / "block_entities-26.3.json"


@cache
def load(target: str = "26.3") -> dict:
    if target != "26.3":
        raise UnsupportedFeature("block_entity", f"no block-entity reference for Minecraft {target}")
    return json.loads(REFERENCE.read_text())


def expected_nbt(block_id: str, loot_table: str | None = None, target: str = "26.3") -> dict | None:
    """The block-entity NBT (plain dict) the policy allows for `block_id`, or None when it has none. `loot_table` is
    written only on blocks whose allow-list entry says `loot_table` (chests and barrels): one `LootTable` string per
    container, never `Items`, `LootTableSeed` or a position. Furnaces, banners etc. ignore it."""
    spec = load(target)["allow"].get(block_id)
    if spec is None:
        return None
    nbt = dict(spec["nbt"])
    if loot_table is not None and spec.get("loot_table"):
        nbt["LootTable"] = loot_table
    return nbt


def handler(block_id: str, state: dict[str, str], target: str, loot_table: str | None = None) -> Compound:
    """The template `nbt` for a block entity, or UnsupportedFeature naming why it is refused."""
    allow = load(target)["allow"]
    if block_id not in allow:
        raise UnsupportedFeature("block_entity", f"{block_id} is not on the block-entity allow-list")
    spec = allow[block_id]
    for key, values in spec["states"].items():
        if state.get(key) not in values:
            raise UnsupportedFeature(
                "block_entity",
                f"{block_id}[{key}={state.get(key)}] is not allowed (the block entity needs {key} in {values})",
            )
    return to_nbt(expected_nbt(block_id, loot_table, target))


def to_nbt(value):
    if isinstance(value, dict):
        return Compound({k: to_nbt(v) for k, v in value.items()})
    if isinstance(value, list):
        return (
            List[Compound]([to_nbt(v) for v in value])
            if all(isinstance(v, dict) for v in value)
            else List[String]([String(v) for v in value])
        )
    if isinstance(value, bool):
        raise TypeError("booleans are not used in block-entity NBT")
    if isinstance(value, int):
        return Int(value)
    return String(value)
