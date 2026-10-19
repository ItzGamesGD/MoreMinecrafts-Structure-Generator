"""STATIC geometric reachability checks for SG-01 (collision model only; not a live player traversal)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "validation/minecraft-visual/stress"))

import static_probe  # noqa: E402

TEMPLATES = ROOT / "exports/sg-01/forgotten-underground-kingdom/datapack/data/moreminecrafts/structure/forgotten_kingdom/central_cavern"


class StaticAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = static_probe.report(TEMPLATES)

    def test_every_tunnel_mouth_walks_to_plaza_and_the_other_mouths(self) -> None:
        for name, modes in self.report["mouths"].items():
            walk = modes["walk_only"]
            self.assertTrue(walk["reaches_plaza_centre"], name)
            self.assertEqual(sorted(walk["reaches_other_mouths"]), sorted({"north", "east", "south", "west"} - {name}), name)

    def test_ring_is_walk_only_reachable_in_all_four_rotations(self) -> None:
        """F-4 repair: eight steps per run, so the ring landing is reachable without any jump edge."""
        for turns in range(4):
            report = static_probe.report(TEMPLATES, turns)
            for name, modes in report["mouths"].items():
                walk = modes["walk_only"]
                self.assertTrue(all(walk["reaches_ring"].values()), (turns, name))
                self.assertEqual(walk["jump_edges_used"], 0, (turns, name))
                self.assertTrue(walk["reaches_plaza_centre"], (turns, name))

    def test_every_stair_run_rises_at_most_half_a_block_per_step_and_lands_flush(self) -> None:
        """Walk along each run from the foot to the landing; every consecutive standing height differs by <= 0.5."""
        asm = static_probe.Assembly(TEMPLATES)
        runs = {  # (axis, fixed lateral cell, cells from foot to landing in chamber-local coordinates)
            "north": [(20, z) for z in range(14, 4, -1)], "south": [(20, z) for z in range(26, 36)],
            "west": [(x, 20) for x in range(14, 4, -1)], "east": [(x, 20) for x in range(26, 36)],
        }
        for name, cells in runs.items():
            heights = []
            for x, z in cells:
                levels = sorted(set(asm.levels(2 * x, 2 * z)) | set(asm.levels(2 * x + 1, 2 * z + 1)))
                heights.append(levels)
            self.assertIn(1.0, heights[0], name)
            self.assertIn(9.0, heights[-1], name)
            top = [h for lv in heights for h in lv if 1.0 <= h <= 9.0]
            ladder = sorted(set(top))
            steps = [round(b - a, 3) for a, b in zip(ladder, ladder[1:])]
            self.assertLessEqual(max(steps), 0.5, (name, ladder))
            self.assertEqual(ladder[0], 1.0)
            self.assertEqual(ladder[-1], 9.0)

    def test_stair_top_meets_ring_surface(self) -> None:
        asm = static_probe.Assembly(TEMPLATES)
        # North run, middle column x=20: last stair at z=6 (level 8) has its back (north half) flush with the 9.0 ring surface.
        self.assertIn(9.0, asm.levels(40, 12))
        self.assertIn(8.5, asm.levels(40, 13))  # its low front half
        self.assertIn(9.0, asm.levels(40, 10))  # ring floor beyond (z=5)

    def test_established_architecture_is_unchanged(self) -> None:
        asm = static_probe.Assembly(TEMPLATES)
        self.assertEqual(len(asm.model), 8575)
        ids = [s["id"] for s in asm.model.values()]
        self.assertEqual(ids.count("minecraft:sea_lantern"), 9)
        self.assertEqual(ids.count("minecraft:deepslate_brick_wall"), 100)
        self.assertEqual(sum(i.endswith("_stairs") for i in ids), 96)
        self.assertEqual(asm.chamber_size, [41, 17, 41])
        # 4 pillars: 5x5 footing at the base and capital, 3x3 shaft between
        for cx in (10, 30):
            for cz in (10, 30):
                self.assertIn((cx, 2, cz), asm.model)
                self.assertIn((cx + 2, 2, cz + 2), asm.model)
                self.assertIn((cx, 8, cz), asm.model)
                self.assertNotIn((cx + 2, 8, cz + 2), asm.model)

    def test_negative_control_enclosed_node_is_not_reachable(self) -> None:
        asm = static_probe.Assembly(TEMPLATES)
        start = static_probe.mouth_nodes(asm)["north"]
        reached, _ = asm.search([start], allow_jump=True)
        outside = (asm.lo[0] * 2 - 4, asm.lo[2] * 2 - 4)
        self.assertEqual(asm.levels(*outside), [])
        self.assertFalse(any(node[0] == outside[0] and node[1] == outside[1] for node in reached))


if __name__ == "__main__":
    unittest.main()
