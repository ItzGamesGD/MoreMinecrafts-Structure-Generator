"""CODE-level guards for the N7-A Fabric spike module (the runtime evidence comes from the collision lab, not from these tests)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1] / "validation/fabric-protection-spike"
RES = SPIKE / "src/main/resources"
JAVA = SPIKE / "src/main/java/dev/itzgamesgd/sg01spike"


class SpikeConfigTests(unittest.TestCase):
    def test_mixin_config_is_fail_loud_and_targets_only_the_two_features(self) -> None:
        cfg = json.loads((RES / "sg01spike.mixins.json").read_text())
        self.assertTrue(cfg["required"])
        self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        self.assertEqual(sorted(cfg["mixins"]), ["GeodeFeatureMixin", "MonsterRoomFeatureMixin"])
        for name, target in (("GeodeFeatureMixin", "GeodeFeature"), ("MonsterRoomFeatureMixin", "MonsterRoomFeature")):
            src = (JAVA / "mixin" / f"{name}.java").read_text()
            self.assertIn(f"@Mixin({target}.class)", src)
            self.assertRegex(src, r'@Inject\(method = "place", at = @At\("HEAD"\), cancellable = true, require = 1\)')

    def test_no_global_block_write_interception_or_feature_override(self) -> None:
        sources = "\n".join(p.read_text() for p in JAVA.rglob("*.java"))
        self.assertNotIn("WorldGenRegion.class", sources)  # no mixin on setBlock
        self.assertNotIn("@Redirect", sources)
        self.assertNotIn("@Overwrite", sources)
        self.assertFalse(re.search(r"\bsetBlock\s*\(", sources))
        self.assertFalse((RES / "data/minecraft").exists())  # no vanilla datapack override shipped by the spike

    def test_version_pin_and_server_only(self) -> None:
        mod = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(mod["depends"]["minecraft"], "26.3")
        self.assertEqual(mod["environment"], "server")
        self.assertEqual(mod["mixins"][0]["environment"], "server")

    def test_protection_tag_lists_only_the_sg_structure_and_is_optional_per_entry(self) -> None:
        tag = json.loads((RES / "data/moreminecrafts/tags/worldgen/structure/protected_from_overlays.json").read_text())
        self.assertEqual(tag["values"], [{"id": "moreminecrafts:forgotten_kingdom/central_cavern", "required": False}])

    def test_missing_or_empty_tag_is_a_hard_failure(self) -> None:
        src = (JAVA / "ProtectionConfig.java").read_text()
        self.assertEqual(src.count("throw new IllegalStateException"), 2)  # never resolved; tag resolves to nothing
        self.assertRegex(src, r"orElseThrow\(\s*\(\) -> new IllegalStateException\(\"SG protection spike: required structure tag")  # tag missing

    def test_guard_never_requests_generation(self) -> None:
        src = (JAVA / "Guard.java").read_text()
        for forbidden in ("getChunkSource", "getLevel()", "loadOrGenerate", "scheduleGeneration", "ChunkStatus.FULL"):
            self.assertNotIn(forbidden, src)
        self.assertIn("MAX_STRUCTURE_DISTANCE", src)
        self.assertIn("hasChunk", src)


if __name__ == "__main__":
    unittest.main()
