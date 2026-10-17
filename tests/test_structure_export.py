from __future__ import annotations

import gzip
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid
from structure_export.nbt import read_nbt, write_nbt
from structure_export.structure import grid_to_structure, structure_bytes


class StructureExportTests(unittest.TestCase):
    def test_small_template_round_trip_preserves_state_air_and_block_entity(self) -> None:
        grid = VoxelGrid()
        grid.set(-1, 4, 2, get_block("polished_deepslate").index)
        grid.set(0, 4, 2, get_block("oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]").index)
        grid.set(0, 4, 3, get_block("chest").index)
        grid.set(0, 5, 2, get_block("air").index)

        template = grid_to_structure(
            grid,
            data_version=5023,
            block_entities={(0, 4, 3): {"id": "minecraft:chest", "LootTable": "minecraft:chests/simple_dungeon"}},
        )
        decoded = read_nbt(write_nbt(template))["value"]

        self.assertEqual(decoded["DataVersion"], 5023)
        self.assertEqual(decoded["size"], [2, 2, 2])
        palette = decoded["palette"]
        self.assertEqual(
            {entry["Name"] for entry in palette},
            {"minecraft:polished_deepslate", "minecraft:oak_stairs", "minecraft:chest", "minecraft:air"},
        )
        stairs = next(entry for entry in palette if entry["Name"] == "minecraft:oak_stairs")
        self.assertEqual(
            stairs["Properties"],
            {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"},
        )
        block = next(
            block for block in decoded["blocks"] if block.get("nbt", {}).get("id") == "minecraft:chest"
        )
        self.assertEqual(block["pos"], [1, 0, 1])
        self.assertEqual(block["nbt"]["LootTable"], "minecraft:chests/simple_dungeon")
        self.assertTrue(any(palette[block["state"]]["Name"] == "minecraft:air" for block in decoded["blocks"]))
        self.assertEqual(decoded["entities"], [])

    def test_template_output_is_byte_reproducible(self) -> None:
        grid = VoxelGrid()
        grid.set(0, 0, 0, get_block("stone").index)
        first = structure_bytes(grid_to_structure(grid, data_version=5023))
        second = structure_bytes(grid_to_structure(grid, data_version=5023))
        self.assertEqual(first, second)
        self.assertTrue(gzip.decompress(first).startswith(b"\x0a\x00\x00"))

    def test_empty_grid_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            grid_to_structure(VoxelGrid(), data_version=5023)

    def test_block_entity_outside_grid_is_rejected(self) -> None:
        grid = VoxelGrid()
        grid.set(0, 0, 0, get_block("stone").index)
        with self.assertRaisesRegex(ValueError, "block_entities.*not a placed block"):
            grid_to_structure(grid, data_version=5023, block_entities={(4, 0, 0): {"id": "minecraft:chest"}})

    def test_block_entity_type_must_match_its_block(self) -> None:
        grid = VoxelGrid()
        grid.set(0, 0, 0, get_block("chest").index)
        with self.assertRaisesRegex(ValueError, "requires 'minecraft:chest'"):
            grid_to_structure(
                grid,
                data_version=5023,
                block_entities={(0, 0, 0): {"id": "minecraft:barrel"}},
            )


if __name__ == "__main__":
    unittest.main()
