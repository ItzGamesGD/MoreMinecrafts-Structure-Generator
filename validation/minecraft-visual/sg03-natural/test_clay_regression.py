"""count_clay_outside must count natural clay near a structure and never count clay inside its template cells."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_natural import count_clay_outside


class FakeChunk:
    def __init__(self, clay_cells):
        idx = np.zeros(4096, dtype=np.int32)
        for x, y, z in clay_cells:
            idx[(y << 8) | (z << 4) | x] = 1
        self.sections = {-2: ([{"id": "minecraft:air"}, {"id": "minecraft:clay"}], idx)}


class FakeWorld:
    def __init__(self, chunks):
        self.chunks = chunks

    def chunk(self, cx, cz):
        return self.chunks.get((cx, cz))

    def biome(self, x, y, z):
        return "minecraft:lush_caves"


class CountClayOutside(unittest.TestCase):
    def test_outside_clay_counts_and_inside_clay_does_not(self):
        # section y=-2 covers world y -32..-17; local (1,3,2) in chunk (0,0) is world (1,-29,2)
        world = FakeWorld({(0, 0): FakeChunk([(1, 3, 2), (5, 3, 5)]), (3, 0): FakeChunk([(0, 0, 0)])})
        inside = {(5, -29, 5)}
        report = count_clay_outside(world, [((0, -30, 0), (10, -20, 10))], inside, margin=64)
        self.assertEqual(report["count"], 2)  # (1,-29,2) and (48,-32,0); the inside cell is excluded
        self.assertEqual(report["biomes"], {"minecraft:lush_caves": 2})

    def test_no_clay_reports_zero_so_a_suppressed_feature_would_be_visible(self):
        world = FakeWorld({(0, 0): FakeChunk([])})
        self.assertEqual(count_clay_outside(world, [((0, -30, 0), (10, -20, 10))], set())["count"], 0)


if __name__ == "__main__":
    unittest.main()
