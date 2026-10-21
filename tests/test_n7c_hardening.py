"""N7-C code- and data-level guards: drift guard (monster room and geode), extension policy, production packaging. Runtime evidence comes from the
lab, see docs in the N7-C pull request."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/sg-worldgen-protection"
JAVA = MOD / "src/main/java/dev/itzgamesgd/sg01spike"
RES = MOD / "src/main/resources"


class DriftGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = (JAVA / "DriftGuard.java").read_text()
        self.mr = (JAVA / "mixin/MonsterRoomFeatureMixin.java").read_text()
        self.geode = (JAVA / "mixin/GeodeFeatureMixin.java").read_text()

    def test_every_dependency_class_has_a_validated_sha256(self) -> None:
        known = self.src[self.src.index("KNOWN = Map.of("):self.src.index("public static final class State")]
        hashes = re.findall(r'"([0-9a-f]{64})"', known)
        self.assertEqual(len(hashes), 6)
        self.assertEqual(len(set(hashes)), 6)
        for cls in ("MonsterRoomFeature", "GeodeFeature", "levelgen.feature.Feature", "BlockBehaviour$BlockStateBase", "BuddingAmethystBlock", "WorldGenRegion"):
            self.assertIn(cls, self.src)
        # each feature depends on its own class plus the shared helpers
        self.assertRegex(self.src, r'MONSTER_ROOM = new State\("monster_room",\s*List\.of\(P \+ "levelgen\.feature\.MonsterRoomFeature", FEATURE, STATE_BASE, REGION\)')
        self.assertRegex(self.src, r'GEODE = new State\("geode",\s*List\.of\(P \+ "levelgen\.feature\.GeodeFeature", FEATURE, P \+ "block\.BuddingAmethystBlock", REGION\)')

    def test_unknown_or_unreadable_vanilla_goes_to_zone_never_off(self) -> None:
        self.assertIn('s.demote(Level.ZONE, "FINGERPRINT_MISMATCH', self.src)
        self.assertIn("cannot read vanilla class", self.src)
        self.assertNotIn("Level.OFF", self.src)
        self.assertIn("if (to.ordinal() <= level.ordinal()) return;", self.src)  # levels only ever become more conservative

    def test_zone_is_the_whole_write_zone_and_holds_without_assumptions(self) -> None:
        self.assertIn("(c.x() - 1) * 16, -4096, (c.z() - 1) * 16, (c.x() + 1) * 16 + 15, 4096, (c.z() + 1) * 16 + 15", self.src)
        self.assertRegex(self.mr, r"case ZONE -> \{\s*BoundingBox zone = DriftGuard\.zone\(level\);")

    def test_provisional_monster_room_does_not_use_the_replicated_precheck_for_its_decision(self) -> None:
        body = self.src[self.src.index("public static Guard.Refine monsterRoomRefine"):self.src.index("/** The 3x3-chunk write zone")]
        self.assertIn("case VERIFIED -> configured;", body)
        self.assertIn("default -> configured == Guard.Refine.ZONE ? configured : Guard.Refine.OFF;", body)  # provisional / box-only -> N7-A box
        self.assertIn("case ZONE -> Guard.Refine.ZONE;", body)

    def test_geode_bound_is_the_configured_box_grown_by_one_cell(self) -> None:
        # GeodeFeature places crystals on pos.relative(direction) of positions inside betweenClosed(origin+min, origin+max)
        self.assertIn("self.minGenOffset() - 1", self.geode)
        self.assertIn("self.maxGenOffset() + 1", self.geode)
        self.assertRegex(self.geode, r"if \(DriftGuard\.GEODE\.level\(\) == DriftGuard\.Level\.VERIFIED\) \{\s*cancel = Guard\.shouldCancel\(Guard\.GEODE, level, origin, reach\);")
        self.assertIn("PROVISIONAL / ZONE", self.geode)

    def test_verification_is_differential_and_demotes_on_any_deviation(self) -> None:
        self.assertIn("outsideHard > 0", self.src)
        self.assertIn("s.demote(Level.ZONE", self.src)
        self.assertIn("s.demote(Level.BOX_ONLY", self.src)
        self.assertIn("s.promote()", self.src)
        self.assertRegex(self.mr, r"DriftGuard\.end\(level, origin\);")
        self.assertRegex(self.geode, r"DriftGuard\.end\(level, origin\);")

    def test_runtime_watch_is_documented_as_detective_not_preventive(self) -> None:
        self.assertIn("can be detected after the fact", self.src)
        self.assertIn("not claimed as prevented", self.src)

    def test_lab_faults_and_fingerprint_break_are_lab_only(self) -> None:
        self.assertIn('Guard.LAB ? System.getenv("SG01_LAB_FINGERPRINT_BREAK") : null', self.src)
        guard = (JAVA / "Guard.java").read_text()
        self.assertIn("GEODE_SHRUNK", guard)
        self.assertIn("PRECHECK_BLIND", guard)
        self.assertRegex(guard, r'FAULT = parseEnum\("sg01.fault", "SG01_FAULT", Fault.class, Fault.NONE, false\)')  # parseEnum -> labEnv


class ExtensionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = (JAVA / "ProtectionContract.java").read_text()

    def test_owner_manifest_violations_stay_fatal(self) -> None:
        for code in ("MANIFEST_MISSING", "MANIFEST_CONFLICT", "MANIFEST_INVALID", "REQUIRED_UNRESOLVED", "OWNERSHIP_MISMATCH", "MANIFEST_EMPTY"):
            self.assertRegex(self.src, rf'throw new ContractViolation\("{code}"')

    def test_malformed_extension_is_isolated_not_fatal_and_not_silent(self) -> None:
        self.assertRegex(self.src, r"catch \(ContractViolation e\) \{\s*rejected\.add\(")
        self.assertIn("List<String> rejected", self.src)
        self.assertIn("the file was dropped, its structures are NOT protected", self.src)
        cfg = (JAVA / "ProtectionConfig.java").read_text()
        self.assertIn("SG_SPIKE protection extension REJECTED", cfg)
        self.assertIn("LOGGER.error", cfg[cfg.index("rejectedExtensions"):])

    def test_a_required_extension_entry_is_never_dropped_silently(self) -> None:
        self.assertRegex(self.src, r'throw new ContractViolation\("EXTENSION_UNRESOLVED"')
        self.assertNotIn("effective.remove", self.src)
        self.assertNotIn("EXTENSION_REPLACE_FORBIDDEN", self.src)
        self.assertIn("EXTENSION_REPLACE_IGNORED", self.src)


class PackagingTests(unittest.TestCase):
    def test_module_has_a_production_identity_and_location(self) -> None:
        mod = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(mod["id"], "sg_worldgen_protection")
        self.assertNotIn("spike", mod["version"].lower())
        self.assertNotIn("spike", mod["name"].lower())
        self.assertFalse((ROOT / "validation/fabric-protection-spike/build.gradle").exists())
        build = (MOD / "build.gradle").read_text()
        self.assertIn("archivesName = 'sg-worldgen-protection'", build)
        self.assertNotIn("spike", build)

    def test_probe_mixins_are_inert_in_production(self) -> None:
        cfg = json.loads((RES / "sg01spike.mixins.json").read_text())
        self.assertEqual(cfg["plugin"], "dev.itzgamesgd.sg01spike.mixin.SgMixinPlugin")
        plugin = (JAVA / "mixin/SgMixinPlugin.java").read_text()
        self.assertIn('return LAB || !mixinClassName.endsWith("ProbeMixin");', plugin)
        probes = [p.stem for p in (JAVA / "mixin").glob("*ProbeMixin.java")]
        self.assertTrue(probes)
        self.assertTrue({"GeodeFeatureMixin", "MonsterRoomFeatureMixin"} <= set(cfg["mixins"]))  # protection hooks are never gated

    def test_lab_harness_points_at_the_new_location(self) -> None:
        lab = ROOT / "validation/minecraft-visual/sg03-natural"
        for name in ("contract_variants.py", "existing_world.py", "soak.py"):
            self.assertIn('"mod" / "sg-worldgen-protection"', (lab / name).read_text(), name)
        self.assertIn("mod/sg-worldgen-protection", (lab / "n73_run.sh").read_text())


if __name__ == "__main__":
    unittest.main()
