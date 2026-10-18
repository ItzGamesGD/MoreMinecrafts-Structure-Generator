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

    def test_ring_is_reachable_but_only_with_a_jump(self) -> None:
        """Characterisation of the current geometry: the top stair's back is 8.0 and the ring floor surface is 9.0.

        If the stair runs are later extended by one step, this test should flip to walk-only reachability.
        """
        for name, modes in self.report["mouths"].items():
            self.assertFalse(any(modes["walk_only"]["reaches_ring"].values()), name)
            self.assertTrue(all(modes["walk_and_jump"]["reaches_ring"].values()), name)
            self.assertGreater(modes["walk_and_jump"]["jump_edges_used"], 0, name)

    def test_stair_top_riser_is_one_block(self) -> None:
        asm = static_probe.Assembly(TEMPLATES)
        # North run, middle column x=20, last stair at z=7 (level 7): standing on its back half is 8.0, the ring floor is 9.0.
        sx, sz = 40, 14  # (x=20, z=7) sub-column, back half is the north half (facing=north)
        self.assertIn(8.0, asm.levels(sx, sz))
        ring = asm.levels(40, 12)  # (x=20, z=6)
        self.assertIn(9.0, ring)

    def test_negative_control_enclosed_node_is_not_reachable(self) -> None:
        asm = static_probe.Assembly(TEMPLATES)
        start = static_probe.mouth_nodes(asm)["north"]
        reached, _ = asm.search([start], allow_jump=True)
        outside = (asm.lo[0] * 2 - 4, asm.lo[2] * 2 - 4)
        self.assertEqual(asm.levels(*outside), [])
        self.assertFalse(any(node[0] == outside[0] and node[1] == outside[1] for node in reached))


if __name__ == "__main__":
    unittest.main()
