#!/usr/bin/env python3
"""Pure synthetic comparison tests: no Minecraft server needed."""
import unittest
from compare_ab import compare


def report(clay, *, start="same"):
    def check():
        return {"clay_replacement_diagnostics": {"positions": clay, "biomes": {"minecraft:lush_caves": len(clay)}},
                "pass": not clay, "missing_or_other": len(clay),
                "expected": 100, "piece_count": 21}
    site = {"candidate_chunk": [4, 13], "generated": True,
            "start_signature": [{"location": start, "rotation": "NONE", "bb": [0, 0, 0, 1, 1, 1]}],
            "bbox": [0, 0, 0, 1, 1, 1],
            "before_ticks": check(), "after_ticks": check()}
    other = {"candidate_chunk": [6, -19], "generated": True,
             "start_signature": [{"location": "other", "rotation": "NONE", "bb": [0, 0, 0, 1, 1, 1]}],
             "bbox": [0, 0, 0, 1, 1, 1], "before_ticks": check(), "after_ticks": check()}
    return {"seed": 42, "generated_sites": 2,
            "candidates": [[4, 13], [6, -19]], "sites": [site, other]}


class CompareTests(unittest.TestCase):
    def test_removed_without_hardcoding_count(self):
        for n in (46, 47):
            with self.subTest(n=n):
                control = report([[i, -26, 190] for i in range(n)])
                treatment = report([])
                result = compare(control, treatment)
                self.assertTrue(result["experiment_valid"])
                self.assertTrue(result["hypothesis_supported"])
                self.assertEqual(result["phases"]["before_ticks"]["control_clay_count"], n)

    def test_remaining_clay_does_not_support_hypothesis(self):
        result = compare(report([[1, 2, 3]]), report([[1, 2, 3]]))
        self.assertTrue(result["experiment_valid"])
        self.assertFalse(result["hypothesis_supported"])

    def test_changed_start_invalidates_comparison(self):
        result = compare(report([[1, 2, 3]]), report([], start="different"))
        self.assertFalse(result["experiment_valid"])
        self.assertFalse(result["structure_starts_match"])


if __name__ == "__main__":
    unittest.main()
