"""CODE-level guards for the N7-A2 experimental additions (refinement, causal fixture, oracle, probes). Runtime evidence comes from the lab."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1] / "mod/sg-worldgen-protection"
RES = SPIKE / "src/main/resources"
JAVA = SPIKE / "src/main/java/dev/itzgamesgd/sg01spike"
MIXIN = JAVA / "mixin"
LABMIXIN = SPIKE / "src/lab/java/dev/itzgamesgd/sg01spike/lab/mixin"
LABRES = SPIKE / "src/lab/resources"
PROBES = ["WorldGenRegionProbeMixin", "ServerChunkCacheProbeMixin", "ChunkMapProbeMixin", "GenerationChunkHolderProbeMixin", "DecorationOrderProbeMixin"]


class SpikeN72Tests(unittest.TestCase):
    def test_mixin_configs_list_hooks_and_probes_and_stay_fail_loud(self) -> None:
        # N7-D: production applies exactly the two protection hooks; the lab mod applies the probes (and the foreign-transformer stand-ins)
        prod = json.loads((RES / "sg01spike.mixins.json").read_text())
        lab = json.loads((LABRES / "sg-lab.mixins.json").read_text())
        for cfg in (prod, lab):
            self.assertTrue(cfg["required"])
            self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        self.assertEqual(sorted(prod["mixins"]), ["GeodeFeatureMixin", "MonsterRoomFeatureMixin"])
        self.assertEqual(sorted(lab["mixins"]), sorted([*PROBES, "ForeignMonsterRoomMixin", "ForeignGeodeMixin"]))
        for name in PROBES:
            self.assertTrue((LABMIXIN / f"{name}.java").exists(), name)
            self.assertFalse((MIXIN / f"{name}.java").exists(), f"{name} must not be in the production source set")

    def test_probes_only_observe(self) -> None:
        for name in PROBES:
            src = (LABMIXIN / f"{name}.java").read_text()
            for forbidden in ("setReturnValue", "setBlock", "cancel("):
                self.assertNotIn(forbidden, src, f"{name} must not contain {forbidden}")
            # every injector guards its counter with Probe.inGuard() (or only reads its arguments)
            self.assertIn("Probe.", src)

    def test_production_defaults_come_from_the_hooks_and_the_guard_reads_no_environment(self) -> None:
        guard = (JAVA / "Guard.java").read_text()
        hooks = (JAVA / "LabHooks.java").read_text()
        # N7-B/N7-C asserted the defaults on Guard; since N7-D they are LabHooks.DEFAULT and the guard has no environment access at all
        self.assertIn("new Config(Guard.Mode.ENFORCE, Guard.Refine.HYBRID, \"both\", Guard.Fixture.NONE, Guard.Fault.NONE, false, false)", hooks)
        self.assertIn("return LabHooks.get().config();", guard)
        self.assertNotIn("getenv", guard)
        self.assertNotIn("getProperty", guard)
        for removed in ("labEnv", "parseEnum", "SG01_"):
            self.assertNotIn(removed, guard)

    def test_fixture_is_only_reachable_when_explicitly_set_and_is_never_default(self) -> None:
        geode = (MIXIN / "GeodeFeatureMixin.java").read_text()
        self.assertIn("cfg.fixture() == Guard.Fixture.NO_GEODE", geode)
        # the fixture branch comes before the guard and can only disable geodes, never enable anything
        self.assertLess(geode.index("cfg.fixture()"), geode.index("Guard.shouldCancel"))
        self.assertIn("Guard.Fixture.NONE", (JAVA / "LabHooks.java").read_text())

    def test_oracle_never_cancels(self) -> None:
        mm = (MIXIN / "MonsterRoomFeatureMixin.java").read_text()
        # the oracle branch ends where the drift guard / timing mark begins
        oracle_branch = mm[mm.index("if (cfg.oracle())"):mm.index("DriftGuard.discard();\n        lab.mark();")]
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
