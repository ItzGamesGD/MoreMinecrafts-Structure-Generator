from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid
from structure_export.datapack import DatapackBuilder
from structure_export.structure import grid_to_structure


class DatapackBuilderTests(unittest.TestCase):
    def test_builder_writes_referenced_template_pool_and_placement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            grid = VoxelGrid()
            grid.set(0, 0, 0, get_block("stone").index)
            template = grid_to_structure(grid, data_version=5023)
            pack = DatapackBuilder(root / "pack", namespace="moreminecrafts", pack_format=121)
            pack.add_structure("moreminecrafts:forgotten_kingdom/test/start", template)
            pack.add_template_pool(
                "moreminecrafts:forgotten_kingdom/test/start",
                ["moreminecrafts:forgotten_kingdom/test/start"],
                fallback="minecraft:empty",
            )
            pack.add_jigsaw_structure(
                "moreminecrafts:forgotten_kingdom/test",
                start_pool="moreminecrafts:forgotten_kingdom/test/start",
                size=1,
                step="strongholds",
                terrain_adaptation="encapsulate",
                max_distance_from_center=64,
            )
            pack.add_random_spread_set(
                "moreminecrafts:forgotten_kingdom/test",
                structure="moreminecrafts:forgotten_kingdom/test",
                spacing=32,
                separation=8,
                salt=27493117,
                biome_tag="#minecraft:is_overworld",
                exclusion_structure="minecraft:trial_chambers",
                exclusion_chunk_radius=12,
            )
            manifest = json.loads(pack.write().read_text())

            self.assertEqual(manifest["minecraft_version"], "26.3")
            self.assertEqual(
                {entry["path"] for entry in manifest["resources"]},
                {
                    "pack.mcmeta",
                    "manifest.json",
                    "data/moreminecrafts/structure/forgotten_kingdom/test/start.nbt",
                    "data/moreminecrafts/worldgen/template_pool/forgotten_kingdom/test/start.json",
                    "data/moreminecrafts/worldgen/structure/forgotten_kingdom/test.json",
                    "data/moreminecrafts/worldgen/structure_set/forgotten_kingdom/test.json",
                },
            )
            pool = json.loads(
                (root / "pack/data/moreminecrafts/worldgen/template_pool/forgotten_kingdom/test/start.json").read_text()
            )
            self.assertEqual(pool["fallback"], "minecraft:empty")
            structure_set = json.loads(
                (root / "pack/data/moreminecrafts/worldgen/structure_set/forgotten_kingdom/test.json").read_text()
            )
            self.assertEqual(structure_set["placement"]["exclusion_zone"]["other_set"], "minecraft:trial_chambers")

    def test_builder_rejects_unsafe_resource_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = DatapackBuilder(Path(tmp) / "pack", namespace="moreminecrafts", pack_format=121)
            with self.assertRaisesRegex(ValueError, "(?i)resource"):
                pack.add_structure("moreminecrafts:../escape", {})

    def test_structure_set_cannot_reference_missing_internal_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = DatapackBuilder(Path(tmp) / "pack", namespace="moreminecrafts", pack_format=121)
            pack.add_random_spread_set(
                "moreminecrafts:forgotten_kingdom/missing",
                structure="moreminecrafts:forgotten_kingdom/missing",
                spacing=34,
                separation=12,
                salt=123,
                biome_tag="#minecraft:is_overworld",
                exclusion_structure="minecraft:trial_chambers",
                exclusion_chunk_radius=12,
            )
            with self.assertRaisesRegex(ValueError, "missing worldgen structure"):
                pack.write()


if __name__ == "__main__":
    unittest.main()
