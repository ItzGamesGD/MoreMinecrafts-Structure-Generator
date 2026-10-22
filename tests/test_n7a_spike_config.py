"""CODE-level guards for the N7-A Fabric spike module (the runtime evidence comes from the collision lab, not from these tests)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1] / "mod/sg-worldgen-protection"
RES = SPIKE / "src/main/resources"
MOD = SPIKE
JAVA = SPIKE / "src/main/java/dev/itzgamesgd/sgprotection"


class SpikeConfigTests(unittest.TestCase):
    def test_mixin_config_is_fail_loud_and_targets_only_the_two_features(self) -> None:
        cfg = json.loads((RES / "sgprotection.mixins.json").read_text())
        self.assertTrue(cfg["required"])
        self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        # N7-A2 added observe-only probe mixins (tests/test_n72_spike_guard.py); the two protection hooks are unchanged.
        self.assertTrue({"GeodeFeatureMixin", "MonsterRoomFeatureMixin"} <= set(cfg["mixins"]))
        for name, target in (("GeodeFeatureMixin", "GeodeFeature"), ("MonsterRoomFeatureMixin", "MonsterRoomFeature")):
            src = (JAVA / "mixin" / f"{name}.java").read_text()
            self.assertIn(f"@Mixin({target}.class)", src)
            self.assertRegex(src, r'@Inject\(method = "place", at = @At\("HEAD"\), cancellable = true, require = 1\)')

    def test_no_global_block_write_interception_or_feature_override(self) -> None:
        production = "\n".join(p.read_text() for p in JAVA.rglob("*.java"))
        lab_java = MOD / "src/lab/java"
        lab = "\n".join(p.read_text() for p in lab_java.rglob("*.java"))
        # Region mixins: the lab's observe-only read probe, and (N8-R) the production write guard, which may only REFUSE a write into a protected piece box.
        region_mixins = sorted(p.name for p in list(JAVA.rglob("*.java")) + list(lab_java.rglob("*.java")) if "WorldGenRegion.class" in p.read_text())
        self.assertEqual(region_mixins, ["WorldGenRegionProbeMixin.java", "WorldGenRegionWriteGuardMixin.java"])
        wg = (JAVA / "mixin/WorldGenRegionWriteGuardMixin.java").read_text()
        self.assertIn('@Inject(method = "setBlock", at = @At("HEAD"), cancellable = true, require = 1)', wg)
        self.assertEqual(wg.count("setReturnValue"), 1)
        self.assertIn("setReturnValue(false)", wg)  # a refused write only; the mixin never returns true and never writes a block
        self.assertIn("WriteGuard.blocked(zone, pos)", wg)
        for sources in (production, lab):
            self.assertNotIn("@Redirect", sources)
            self.assertNotIn("@Overwrite", sources)
        self.assertFalse(re.search(r"\bsetBlock\s*\(", production))  # the production module never writes a block
        self.assertEqual(len(re.findall(r"\bsetBlock\s*\(", lab)), 2)  # only the lab's write-zone probe (place marker, restore), nowhere else
        self.assertFalse((RES / "data/minecraft").exists())  # no vanilla datapack override shipped

    def test_version_pin_and_loads_on_dedicated_and_integrated_servers(self) -> None:
        mod = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(mod["depends"]["minecraft"], "26.3")
        # N10-R: "*" so that the module also loads on the integrated server (single-player and LAN); it still touches no client class (test_n10r_repairs)
        self.assertEqual(mod["environment"], "*")
        self.assertEqual(mod["mixins"][0]["environment"], "*")

    def test_legacy_tag_mode_is_gone(self) -> None:
        # N7-B: the manifest contract is the only protection source; the N7-A merged-tag mode and its bundled tag no longer exist
        self.assertFalse((RES / "data/moreminecrafts/tags/worldgen/structure/protected_from_overlays.json").exists())
        self.assertFalse((RES / "data").exists() and any((RES / "data").rglob("*.json")), "the module ships no datapack data")
        for p in JAVA.rglob("*.java"):
            text = p.read_text()
            self.assertNotIn("protected_from_overlays", text, p.name)
            self.assertNotIn("SG01_PROTECTION", text, p.name)
            self.assertNotIn("MANIFEST_MODE", text, p.name)

    def test_missing_manifest_is_a_hard_failure(self) -> None:
        src = (JAVA / "ProtectionConfig.java").read_text()
        self.assertIn("never resolved", src)
        contract = (JAVA / "ProtectionContract.java").read_text()
        self.assertRegex(contract, r'new ContractViolation\("MANIFEST_MISSING"')

    def test_guard_never_requests_generation(self) -> None:
        src = (JAVA / "Guard.java").read_text()
        for forbidden in ("getChunkSource", "getLevel()", "loadOrGenerate", "scheduleGeneration", "ChunkStatus.FULL"):
            self.assertNotIn(forbidden, src)
        self.assertIn("MAX_STRUCTURE_DISTANCE", src)
        self.assertIn("hasChunk", src)


if __name__ == "__main__":
    unittest.main()
