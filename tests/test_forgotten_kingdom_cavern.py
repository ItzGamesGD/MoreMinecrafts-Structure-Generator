from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))

from build_cavern import build_pack, build_templates, validate_connections
from structure_export.nbt import read_nbt
from structure_export.jigsaw import connect_templates


class ForgottenKingdomCavernTests(unittest.TestCase):
    def test_main_cavern_stays_within_target_and_has_constructed_shell(self) -> None:
        templates, _ = build_templates()
        root = templates["moreminecrafts:forgotten_kingdom/central_cavern/main_chamber"]
        self.assertEqual(root["size"], [41, 17, 41])
        palette = root["palette"]
        states = {tuple(block["pos"]): palette[block["state"]]["id"] for block in root["blocks"]}
        self.assertTrue(all(states[(x, 0, z)] != "minecraft:air" for x in range(41) for z in range(41)))
        self.assertTrue(all(states[(x, 16, z)] != "minecraft:air" for x in range(41) for z in range(41)))
        for y in range(1, 16):
            for lateral in range(41):
                in_door = 19 <= lateral <= 21 and 1 <= y <= 4
                for x, z in ((0, lateral), (40, lateral), (lateral, 0), (lateral, 40)):
                    if not in_door:
                        self.assertNotEqual(states[(x, y, z)], "minecraft:air")
        self.assertEqual(states[(20, 1, 0)], "minecraft:jigsaw")
        self.assertEqual(states[(40, 1, 20)], "minecraft:jigsaw")
        self.assertEqual(states[(20, 1, 40)], "minecraft:jigsaw")
        self.assertEqual(states[(0, 1, 20)], "minecraft:jigsaw")

    def test_four_tunnel_connections_have_resolved_targets_and_aligned_seams(self) -> None:
        templates, _ = build_templates()
        joins = validate_connections(templates)
        self.assertEqual(set(joins), {"north", "east", "south", "west"})
        for connection in joins.values():
            front = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}[
                connection["parent_facing"]
            ]
            self.assertEqual(
                connection["child_connector_world_pos"],
                tuple(connection["parent_pos"][i] + front[i] for i in range(3)),
            )
            self.assertEqual(connection["world_child_facing"], {
                "north": "south", "east": "west", "south": "north", "west": "east"
            }[connection["parent_facing"]])

    def test_pack_includes_independent_jigsaw_structure_and_trial_chamber_exclusion(self) -> None:
        with __import__("tempfile").TemporaryDirectory() as tmp:
            pack_root = build_pack(Path(tmp) / "datapack")
            manifest = json.loads((pack_root / "manifest.json").read_text())
            paths = {resource["path"] for resource in manifest["resources"]}
            self.assertIn(
                "data/moreminecrafts/worldgen/structure_set/forgotten_kingdom/central_cavern.json", paths
            )
            self.assertIn("data/moreminecrafts/structure/forgotten_kingdom/central_cavern/main_chamber.nbt", paths)
            structure_set = json.loads(
                (pack_root / "data/moreminecrafts/worldgen/structure_set/forgotten_kingdom/central_cavern.json").read_text()
            )
            self.assertEqual(structure_set["placement"]["exclusion_zone"]["other_set"], "minecraft:trial_chambers")
            nbt = read_nbt((pack_root / "data/moreminecrafts/structure/forgotten_kingdom/central_cavern/main_chamber.nbt").read_bytes())
            self.assertEqual(nbt["value"]["DataVersion"], 5023)
            self.assertEqual(len(paths), 14)
            for resource in manifest["resources"]:
                resource_path = pack_root / resource["path"]
                self.assertTrue(resource_path.is_file())
                if "sha256" in resource:
                    self.assertEqual(hashlib.sha256(resource_path.read_bytes()).hexdigest(), resource["sha256"])

    def test_connection_validation_detects_orientation_or_target_regressions(self) -> None:
        templates, _ = build_templates()
        chamber = templates["moreminecrafts:forgotten_kingdom/central_cavern/main_chamber"]
        north = templates["moreminecrafts:forgotten_kingdom/central_cavern/tunnel_north"]
        connection = connect_templates(chamber, (20, 1, 0), north, (2, 1, 14))
        self.assertEqual(connection["origin"], (18, 0, -15))

    def test_full_export_is_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_root = build_pack(Path(first_dir) / "datapack")
            second_root = build_pack(Path(second_dir) / "datapack")
            first = {
                path.relative_to(first_root).as_posix(): path.read_bytes()
                for path in first_root.rglob("*")
                if path.is_file()
            }
            second = {
                path.relative_to(second_root).as_posix(): path.read_bytes()
                for path in second_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
