"""Guard against misreporting unverified world state as SG-03 success."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_natural import inspect, overlay_kind
from spread import SG01, candidate_chunk


class FakeWorld:
    def state(self, *pos):
        return {"id": "minecraft:air"}

    def block_id(self, *pos):
        return "minecraft:air"


class NaturalValidationContracts(unittest.TestCase):
    def test_empty_start_never_passes(self):
        report = inspect(FakeWorld(), {"Children": []}, {})
        self.assertFalse(report["pass"])
        self.assertEqual(report["piece_count"], 0)

    def test_unrecognized_piece_does_not_pass(self):
        child = {"pool_element": {"location": "made-up:room"}, "rotation": "NONE", "BB": [0, 0, 0, 1, 1, 1]}
        report = inspect(FakeWorld(), {"Children": [child]}, {})
        self.assertFalse(report["pass"])
        self.assertTrue(report["errors"])

    def test_worldgen_overlay_not_disguised_as_clean_match(self):
        self.assertEqual(overlay_kind("minecraft:sculk_sensor"), "sculk")
        self.assertEqual(overlay_kind("minecraft:budding_amethyst"), "geode")
        self.assertEqual(overlay_kind("minecraft:lava"), "unexplained")
        self.assertEqual(overlay_kind("minecraft:air"), "unexplained")

    def test_pinned_vanilla_candidate_seed_173(self):
        self.assertEqual(candidate_chunk(173, 9, 9, **SG01), (324, 309))


if __name__ == "__main__":
    unittest.main()
