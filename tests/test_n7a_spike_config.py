"""CODE-level guards for the N7-A Fabric spike module (the runtime evidence comes from the collision lab, not from these tests)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1] / "mod/sg-worldgen-protection"
RES = SPIKE / "src/main/resources"
JAVA = SPIKE / "src/main/java/dev/itzgamesgd/sg01spike"


class SpikeConfigTests(unittest.TestCase):
    def test_mixin_config_is_fail_loud_and_targets_only_the_two_features(self) -> None:
        cfg = json.loads((RES / "sg01spike.mixins.json").read_text())
        self.assertTrue(cfg["required"])
        self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        # N7-A2 added observe-only probe mixins (tests/test_n72_spike_guard.py); the two protection hooks are unchanged.
        self.assertTrue({"GeodeFeatureMixin", "MonsterRoomFeatureMixin"} <= set(cfg["mixins"]))
        for name, target in (("GeodeFeatureMixin", "GeodeFeature"), ("MonsterRoomFeatureMixin", "MonsterRoomFeature")):
            src = (JAVA / "mixin" / f"{name}.java").read_text()
            self.assertIn(f"@Mixin({target}.class)", src)
            self.assertRegex(src, r'@Inject\(method = "place", at = @At\("HEAD"\), cancellable = true, require = 1\)')

    def test_no_global_block_write_interception_or_feature_override(self) -> None:
        sources = "\n".join(p.read_text() for p in JAVA.rglob("*.java"))
        # N7-A2: the only WorldGenRegion mixin is the observe-only read probe, which targets hasChunk/getChunk, never setBlock
        region_mixins = [p for p in JAVA.rglob("*.java") if "WorldGenRegion.class" in p.read_text()]
        self.assertEqual([p.name for p in region_mixins], ["WorldGenRegionProbeMixin.java"])
        self.assertNotIn("@Redirect", sources)
        self.assertNotIn("@Overwrite", sources)
        self.assertFalse(re.search(r"\bsetBlock\s*\(", sources))
        self.assertFalse((RES / "data/minecraft").exists())  # no vanilla datapack override shipped by the spike

    def test_version_pin_and_server_only(self) -> None:
        mod = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(mod["depends"]["minecraft"], "26.3")
        self.assertEqual(mod["environment"], "server")
        self.assertEqual(mod["mixins"][0]["environment"], "server")

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
