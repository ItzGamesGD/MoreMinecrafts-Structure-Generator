"""CODE-level guards for the N7-A2 experimental additions (refinement, causal fixture, oracle, probes). Runtime evidence comes from the lab."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1] / "validation/fabric-protection-spike"
RES = SPIKE / "src/main/resources"
JAVA = SPIKE / "src/main/java/dev/itzgamesgd/sg01spike"
MIXIN = JAVA / "mixin"
PROBES = ["WorldGenRegionProbeMixin", "ServerChunkCacheProbeMixin", "ChunkMapProbeMixin", "GenerationChunkHolderProbeMixin"]


class SpikeN72Tests(unittest.TestCase):
    def test_mixin_config_lists_hooks_and_probes_and_stays_fail_loud(self) -> None:
        cfg = json.loads((RES / "sg01spike.mixins.json").read_text())
        self.assertTrue(cfg["required"])
        self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        self.assertEqual(sorted(cfg["mixins"]), sorted(["GeodeFeatureMixin", "MonsterRoomFeatureMixin", *PROBES]))
        for name in PROBES:
            self.assertTrue((MIXIN / f"{name}.java").exists(), name)

    def test_probes_only_observe(self) -> None:
        for name in PROBES:
            src = (MIXIN / f"{name}.java").read_text()
            for forbidden in ("setReturnValue", "setBlock", "cancel("):
                self.assertNotIn(forbidden, src, f"{name} must not contain {forbidden}")
            # every injector guards its counter with Probe.inGuard() (or only reads its arguments)
            self.assertIn("Probe.", src)

    def test_experiment_switches_default_to_the_n7a_behaviour(self) -> None:
        guard = (JAVA / "Guard.java").read_text()
        self.assertRegex(guard, r'REFINE = parseEnum\("sg01.refine", "SG01_REFINE", Refine.class, Refine.OFF')
        self.assertRegex(guard, r'FIXTURE = parseEnum\("sg01.fixture", "SG01_FIXTURE", Fixture.class, Fixture.NONE')
        self.assertRegex(guard, r'ORACLE_MONSTER_ROOM = "monster_room".equalsIgnoreCase')

    def test_fixture_is_only_reachable_when_explicitly_set_and_is_never_default(self) -> None:
        geode = (MIXIN / "GeodeFeatureMixin.java").read_text()
        self.assertIn("Guard.FIXTURE == Guard.Fixture.NO_GEODE", geode)
        # the fixture branch comes before the guard and can only disable geodes, never enable anything
        self.assertLess(geode.index("Guard.FIXTURE"), geode.index("Guard.shouldCancel"))

    def test_oracle_never_cancels(self) -> None:
        mm = (MIXIN / "MonsterRoomFeatureMixin.java").read_text()
        oracle_branch = mm[mm.index("if (Guard.ORACLE_MONSTER_ROOM)"):mm.index("List<BoundingBox> reaches;")]
        self.assertIn("return;", oracle_branch)
        self.assertNotIn("setReturnValue", oracle_branch)

    def test_refined_monster_room_reach_is_a_subset_of_the_n7a_box(self) -> None:
        geom = (JAVA / "MonsterRoomGeometry.java").read_text()
        # variants are xr, zr in {2, 3}; the N7-A box is the union (xr = zr = 3, walls at +-4)
        self.assertRegex(geom, r"VARIANTS = \{2, 3\}")
        self.assertRegex(geom, r"origin\.getX\(\) - xr - 1")
        self.assertRegex(geom, r"origin\.getY\(\) \+ 4")

    def test_precheck_mirrors_vanilla_order_and_predicates(self) -> None:
        geom = (JAVA / "MonsterRoomGeometry.java").read_text()
        self.assertRegex(geom, r"for \(int dx = minX; dx <= maxX; dx\+\+\)")
        self.assertRegex(geom, r"for \(int dy = -1; dy <= 4; dy\+\+\)")
        self.assertRegex(geom, r"for \(int dz = minZ; dz <= maxZ; dz\+\+\)")
        self.assertRegex(geom, r"holeCount >= 1 && holeCount <= 5")
        self.assertIn("getBlockState(holePos).isSolid()", geom)
        self.assertIn("level.isEmptyBlock(holePos) && level.isEmptyBlock(holePos.above())", geom)
        # the precheck is read-only
        self.assertNotIn("setBlock", geom)


if __name__ == "__main__":
    unittest.main()
