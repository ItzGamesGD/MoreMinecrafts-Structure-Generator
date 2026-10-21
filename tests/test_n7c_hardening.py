"""N7-C code- and data-level guards: drift guard (monster room and geode), extension policy, production packaging. Runtime evidence comes from the
lab, see docs in the N7-C pull request."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/sg-worldgen-protection"
JAVA = MOD / "src/main/java/dev/itzgamesgd/sgprotection"
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
        self.assertIn('"FINGERPRINT_MISMATCH: " + failure', self.src)
        self.assertIn('s.demote(Level.ZONE, failure.startsWith("FOREIGN")', self.src)
        self.assertIn("cannot read vanilla class", self.src)
        self.assertNotIn("Level.OFF", self.src)
        self.assertIn("if (to.ordinal() <= level.ordinal()) return;", self.src)  # levels only ever become more conservative

    def test_zone_is_the_whole_write_zone_and_holds_without_assumptions(self) -> None:
        self.assertIn("(c.x() - 1) * 16, -4096, (c.z() - 1) * 16, (c.x() + 1) * 16 + 15, 4096, (c.z() + 1) * 16 + 15", self.src)
        self.assertRegex(self.mr, r"case ZONE -> \{\s*BoundingBox zone = DriftGuard\.zone\(level\);")

    def test_monster_room_decision_by_level_never_trusts_an_unverified_bound(self) -> None:
        body = self.src[self.src.index("public static Guard.Refine monsterRoomRefine"):self.src.index("/** The 3x3-chunk write zone")]
        self.assertIn("case ZONE, PROVISIONAL -> Guard.Refine.ZONE;", body)  # N7-E: unverified footprint bound -> zone, not the box
        self.assertIn("case VERIFIED -> configured;", body)
        self.assertIn("case BOX_ONLY -> configured == Guard.Refine.ZONE ? configured : Guard.Refine.OFF;", body)

    def test_production_monster_room_decision_is_the_box_not_the_replica(self) -> None:
        hooks = (JAVA / "LabHooks.java").read_text()
        self.assertIn("Guard.Refine.OFF", hooks[hooks.index("Config DEFAULT"):hooks.index("LabHooks NONE")])
        self.assertRegex(self.mr, r"default -> cancel = Guard\.shouldCancel\(Guard\.MONSTER_ROOM, level, origin, List\.of\(broad\)\)")
        # the replicated precheck is evaluated only for lab configurations that use it
        self.assertIn("boolean replica = cfg.refine() == Guard.Refine.HYBRID || cfg.refine() == Guard.Refine.PRECHECK;", self.mr)

    def test_geode_bound_is_the_configured_box_grown_by_one_cell(self) -> None:
        # GeodeFeature places crystals on pos.relative(direction) of positions inside betweenClosed(origin+min, origin+max)
        self.assertIn("self.minGenOffset() - 1", self.geode)
        self.assertIn("self.maxGenOffset() + 1", self.geode)
        self.assertRegex(self.geode, r"if \(levelBefore == DriftGuard\.Level\.VERIFIED\) \{\s*cancel = Guard\.shouldCancel\(Guard\.GEODE, level, origin, reach\);")
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

    def test_lab_faults_and_fingerprint_break_come_only_from_the_lab_hooks(self) -> None:
        self.assertIn("LabHooks.get().fingerprintBreak()", self.src)
        self.assertNotIn("getenv", self.src)
        guard = (JAVA / "Guard.java").read_text()
        for fault in ("GEODE_SHRUNK", "PRECHECK_BLIND", "ZONE_PROBE"):
            self.assertIn(fault, guard)

    def test_restored_n7b_guarantees(self) -> None:
        # N7-B asserted these on MonsterRoomSelfCheck; they now apply to DriftGuard
        self.assertIn('MessageDigest.getInstance("SHA-256")', self.src)  # fingerprints are SHA-256 of the class file
        self.assertIn("cannot read vanilla class", self.src)  # unreadable class fails closed (was FINGERPRINT_UNAVAILABLE)
        self.assertIn("RUNTIME_DEVIATION", self.src)  # was RUNTIME_VIOLATION
        mod = (JAVA / "SgProtectionMod.java").read_text()
        self.assertLess(mod.index("DriftGuard.verifyAtStartup()"), mod.index("ProtectionConfig.resolve(server)"))
        guard = (JAVA / "Guard.java").read_text()
        self.assertIn("DriftGuard.arm(DriftGuard.MONSTER_ROOM, region, inflate(broad, 2), predicted, broad)", guard)
        self.assertRegex(self.mr, r"default -> cancel = Guard\.shouldCancel\(Guard\.MONSTER_ROOM, level, origin, List\.of\(broad\)\)")  # box guard
        self.assertIn("DriftGuard.discard()", self.mr)

    def test_foreign_transformer_detection_is_present_and_fails_to_zone(self) -> None:
        self.assertIn("FOREIGN_TRANSFORM", self.src)
        self.assertIn("foreignMembers(cls, bytes)", self.src)
        self.assertIn("!ownOrPlatform(m.getName())", self.src)
        self.assertIn('name.contains("$sgprotection$")', self.src)  # the module's own (possibly wrapped) handlers are not foreign
        self.assertIn("fabric_api$", self.src)  # Fabric API's own additions are the platform, not foreign
        self.assertIn("adds no member", self.src)


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
        self.assertIn("SG_PROTECTION protection extension REJECTED", cfg)
        self.assertIn("LOGGER.error", cfg[cfg.index("rejectedExtensions"):])

    def test_a_required_extension_entry_is_never_dropped_silently(self) -> None:
        self.assertRegex(self.src, r'throw new ContractViolation\("EXTENSION_UNRESOLVED"')
        self.assertNotIn("effective.remove", self.src)
        self.assertNotIn("EXTENSION_REPLACE_FORBIDDEN", self.src)
        self.assertIn("EXTENSION_REPLACE_IGNORED", self.src)


class PackagingTests(unittest.TestCase):
    def test_module_has_a_production_identity_and_location(self) -> None:
        mod = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(mod["id"], "sg_worldgen_protection")  # N7-E: the public mod id is unchanged, only the package and logger prefix were renamed
        self.assertNotIn("spike", mod["version"].lower())
        self.assertNotIn("spike", mod["name"].lower())
        self.assertFalse((ROOT / "validation/fabric-protection-spike/build.gradle").exists())
        build = (MOD / "build.gradle").read_text()
        self.assertIn("archivesName = 'sg-worldgen-protection'", build)
        self.assertNotIn("spike", build)

    def test_lab_harness_points_at_the_new_location(self) -> None:
        lab = ROOT / "validation/minecraft-visual/sg03-natural"
        for name in ("contract_variants.py", "existing_world.py", "soak.py"):
            self.assertIn('"mod" / "sg-worldgen-protection"', (lab / name).read_text(), name)
        self.assertIn("mod/sg-worldgen-protection", (lab / "n73_run.sh").read_text())


if __name__ == "__main__":
    unittest.main()
