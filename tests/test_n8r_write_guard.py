"""N8-R code-level guards for the write-level protection (runtime evidence: the N8-R lab runs)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/sg-worldgen-protection"
JAVA = MOD / "src/main/java/dev/itzgamesgd/sgprotection"
LAB = MOD / "src/lab/java/dev/itzgamesgd/sgprotection/lab"


class WriteGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = (JAVA / "WriteGuard.java").read_text()
        self.region = (JAVA / "mixin/WorldGenRegionWriteGuardMixin.java").read_text()
        self.start = (JAVA / "mixin/StructureStartWriteGuardMixin.java").read_text()
        self.hooks = (JAVA / "LabHooks.java").read_text()

    def test_hook_is_the_single_world_generation_write_path_and_is_fail_loud(self) -> None:
        self.assertIn('@Mixin(WorldGenRegion.class)', self.region)
        self.assertIn('@Inject(method = "setBlock", at = @At("HEAD"), cancellable = true, require = 1)', self.region)
        cfg = json.loads((JAVA.parents[3] / "resources/sgprotection.mixins.json").read_text())
        self.assertTrue({"WorldGenRegionWriteGuardMixin", "StructureStartWriteGuardMixin"} <= set(cfg["mixins"]))
        self.assertTrue(cfg["required"])

    def test_only_refuses_writes_into_protected_boxes_and_never_writes(self) -> None:
        self.assertNotRegex(self.guard + self.region + self.start, r"\bsetBlock\s*\(")
        self.assertNotIn("getChunk(", self.guard)  # never requests a chunk
        self.assertIn("box.isInside(pos)", self.guard)
        self.assertIn("cir.setReturnValue(false)", self.region)

    def test_boxes_are_computed_once_per_region_and_unavailable_data_is_loud(self) -> None:
        self.assertIn("@Unique", self.region)
        self.assertIn("if (boxes == null)", self.region)
        self.assertIn("UNAVAILABLE.incrementAndGet()", self.guard)
        self.assertIn("SgProtectionMod.LOGGER.error", self.guard)
        self.assertIn("Guard.pieceBoxes(region, zone)", self.guard)

    def test_only_the_protected_structure_itself_is_exempt_and_exception_safe(self) -> None:
        self.assertIn("ProtectionConfig.protectedStructures().contains(structure)", self.guard)
        self.assertIn("@WrapMethod", self.start)
        self.assertRegex(self.start, r"try \{\s*original\.call\(.*\);\s*\} finally \{\s*WriteGuard\.exitPlacement")

    def test_production_default_is_write_guard_on_and_feature_hooks_off(self) -> None:
        default = self.hooks[self.hooks.index("Config DEFAULT"):self.hooks.index("LabHooks NONE")]
        self.assertIn('"none"', default)
        self.assertTrue(default.strip().rstrip(";").endswith("true)"))
        guard = (JAVA / "Guard.java").read_text()
        self.assertIn("return state.level() == DriftGuard.Level.ZONE;", guard)  # unverifiable vanilla switches the second layer on
        for mixin in ("GeodeFeatureMixin", "MonsterRoomFeatureMixin"):
            self.assertIn('Guard.hookActive("', (JAVA / "mixin" / f"{mixin}.java").read_text())

    def test_write_guard_dependencies_are_fingerprinted_and_lab_can_disable_it(self) -> None:
        drift = (JAVA / "DriftGuard.java").read_text()
        self.assertIn('START = P + "levelgen.structure.StructureStart"', drift)
        self.assertIn("REGION, \"f33962d43745ecd21ca163ab713c2af2f8fbcc84b490c285e4b5d8ea0f3b744e\"", drift)
        self.assertIn('!"0".equals(env("SG01_WRITE_GUARD"))', (LAB / "LabMod.java").read_text())
        self.assertIn('"write_guard"', (JAVA / "SgProtectionMod.java").read_text().replace('\\"', '"'))


if __name__ == "__main__":
    unittest.main()
