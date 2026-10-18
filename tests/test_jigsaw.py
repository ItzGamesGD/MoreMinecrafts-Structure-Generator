from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid
from structure_export.jigsaw import connect_templates, find_jigsaw, rotate_position
from structure_export.structure import grid_to_structure


def template_with_jigsaw(pos, orientation: str, *, name: str, target: str, width: int = 5, depth: int = 15):
    grid = VoxelGrid()
    for x in range(width):
        for y in range(5):
            for z in range(depth):
                grid.set(x, y, z, get_block("air").index)
    grid.set(*pos, get_block(f"jigsaw[orientation={orientation}]").index)
    return grid_to_structure(
        grid,
        data_version=5023,
        block_entities={
            pos: {
                "id": "minecraft:jigsaw",
                "name": name,
                "target": target,
                "pool": "moreminecrafts:forgotten_kingdom/tunnels/test",
                "final_state": "minecraft:air",
            }
        },
    )


class JigsawTests(unittest.TestCase):
    def test_connector_contract_aligns_opposing_faces_and_rotated_positions(self) -> None:
        parent = template_with_jigsaw(
            (2, 1, 0),
            "north_up",
            name="moreminecrafts:forgotten_kingdom/cavern_exit",
            target="moreminecrafts:forgotten_kingdom/tunnel_in",
        )
        child = template_with_jigsaw(
            (2, 1, 14),
            "south_up",
            name="moreminecrafts:forgotten_kingdom/tunnel_in",
            target="moreminecrafts:forgotten_kingdom/district_entrance",
        )
        connection = connect_templates(parent, (2, 1, 0), child, (2, 1, 14), rotation="none")
        self.assertEqual(connection["rotation"], "none")
        self.assertEqual(connection["origin"], (0, 0, -15))
        # The child connector is the cell in front of the parent connector, not the same cell.
        self.assertEqual(connection["child_connector_world_pos"], (2, 1, -1))
        self.assertEqual(connection["world_child_facing"], "south")

    def test_rotation_transforms_horizontal_position_and_facing(self) -> None:
        self.assertEqual(rotate_position((2, 1, 14), (5, 5, 15), "clockwise_90"), ((0, 1, 2), (15, 5, 5)))
        parent = template_with_jigsaw(
            (4, 1, 2),
            "east_up",
            name="moreminecrafts:forgotten_kingdom/cavern_exit",
            target="moreminecrafts:forgotten_kingdom/tunnel_in",
        )
        child = template_with_jigsaw(
            (2, 1, 14),
            "south_up",
            name="moreminecrafts:forgotten_kingdom/tunnel_in",
            target="minecraft:empty",
        )
        connection = connect_templates(parent, (4, 1, 2), child, (2, 1, 14), rotation="clockwise_90")
        self.assertEqual(connection["world_child_facing"], "west")

    def test_wrong_target_or_non_opposing_orientation_is_rejected(self) -> None:
        parent = template_with_jigsaw(
            (2, 1, 0),
            "north_up",
            name="moreminecrafts:forgotten_kingdom/cavern_exit",
            target="moreminecrafts:forgotten_kingdom/missing",
        )
        child = template_with_jigsaw(
            (2, 1, 14),
            "south_up",
            name="moreminecrafts:forgotten_kingdom/tunnel_in",
            target="minecraft:empty",
        )
        with self.assertRaisesRegex(ValueError, "target"):
            connect_templates(parent, (2, 1, 0), child, (2, 1, 14))

    def test_find_jigsaw_requires_well_formed_jigsaw_block_entity(self) -> None:
        parent = template_with_jigsaw(
            (2, 1, 0),
            "north_up",
            name="moreminecrafts:forgotten_kingdom/cavern_exit",
            target="moreminecrafts:forgotten_kingdom/tunnel_in",
        )
        self.assertEqual(find_jigsaw(parent, (2, 1, 0))["target"], "moreminecrafts:forgotten_kingdom/tunnel_in")
        with self.assertRaisesRegex(ValueError, "(?i)no jigsaw"):
            find_jigsaw(parent, (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
