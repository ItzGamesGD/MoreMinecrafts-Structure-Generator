"""N7-B code- and data-level guards: the production manifest in the real SG-03 content pack, the manifest builder, and the monster-room
self-check. Runtime evidence (real server, reloads, regressions) comes from the lab, see docs/sg-03/n7b-production-guard.md."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))

import build_sg02  # noqa: E402
import build_sg03  # noqa: E402
from structure_export.datapack import MINECRAFT_VERSION, DatapackBuilder  # noqa: E402

PACK = ROOT / "exports/sg-03/forgotten-underground-kingdom/datapack"
MANIFEST = PACK / "data/moreminecrafts/sg_protection/manifest.json"
JAVA = ROOT / "validation/fabric-protection-spike/src/main/java/dev/itzgamesgd/sg01spike"


class ProductionManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text())

    def test_committed_sg03_pack_carries_the_manifest(self) -> None:
        self.assertEqual(set(self.manifest), {"format", "minecraft", "revision", "structures"})
        self.assertEqual(self.manifest["minecraft"], MINECRAFT_VERSION)
        self.assertEqual(self.manifest["structures"], ["moreminecrafts:forgotten_kingdom/central_cavern"])

    def test_every_listed_structure_is_defined_by_the_same_pack(self) -> None:
        for identifier in self.manifest["structures"]:
            namespace, path = identifier.split(":")
            self.assertTrue((PACK / "data" / namespace / "worldgen/structure" / f"{path}.json").is_file(), identifier)

    def test_manifest_matches_what_the_module_accepts(self) -> None:
        contract = (JAVA / "ProtectionContract.java").read_text()
        formats = {int(v) for v in re.search(r"SUPPORTED_FORMATS = Set\.of\(([\d, ]+)\)", contract).group(1).split(",")}
        min_revision = int(re.search(r"MIN_REVISION = (\d+)", contract).group(1))
        self.assertIn(self.manifest["format"], formats)
        self.assertGreaterEqual(self.manifest["revision"], min_revision)
        self.assertIn('Identifier.parse("moreminecrafts:sg_protection/manifest.json")', contract)

    def test_resource_manifest_lists_it_with_the_right_checksum(self) -> None:
        resources = json.loads((PACK / "manifest.json").read_text())["resources"]
        entry = next(r for r in resources if r["path"] == "data/moreminecrafts/sg_protection/manifest.json")
        self.assertEqual(entry["role"], "protection_manifest")
        self.assertEqual(entry["sha256"], hashlib.sha256(MANIFEST.read_bytes()).hexdigest())
        self.assertEqual(entry["references"], self.manifest["structures"])

    def test_committed_pack_is_reproducible_from_the_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_sg03.build_pack(tmp)
            for rel in ("data/moreminecrafts/sg_protection/manifest.json", "manifest.json", "pack.mcmeta"):
                self.assertEqual((Path(tmp) / rel).read_bytes(), (PACK / rel).read_bytes(), rel)

    def test_sg02_pack_is_not_touched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_sg02.build_pack(tmp)
            self.assertFalse((Path(tmp) / "data/moreminecrafts/sg_protection").exists())
        self.assertFalse(list((ROOT / "exports/sg-02").rglob("sg_protection")))


class ManifestBuilderTests(unittest.TestCase):
    def builder(self) -> DatapackBuilder:
        b = DatapackBuilder(tempfile.mkdtemp(), namespace="moreminecrafts")
        b.worldgen_structures.add("moreminecrafts:a/b")
        return b

    def test_rejects_unknown_empty_duplicate_and_bad_revision(self) -> None:
        for structures, revision in ((["moreminecrafts:missing"], 1), ([], 1), (["moreminecrafts:a/b", "moreminecrafts:a/b"], 1),
                                     (["moreminecrafts:a/b"], 0), (["moreminecrafts:a/b"], True)):
            with self.assertRaises(ValueError, msg=str((structures, revision))):
                self.builder().add_protection_manifest(structures, revision=revision)

    def test_rejects_a_second_manifest(self) -> None:
        b = self.builder()
        b.add_protection_manifest(["moreminecrafts:a/b"])
        with self.assertRaises(ValueError):
            b.add_protection_manifest(["moreminecrafts:a/b"])


class SelfCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = (JAVA / "MonsterRoomSelfCheck.java").read_text()
        self.mixin = (JAVA / "mixin/MonsterRoomFeatureMixin.java").read_text()

    def test_fingerprint_set_is_non_empty_sha256(self) -> None:
        values = re.search(r"KNOWN_FINGERPRINTS = Set\.of\(([^)]*)\)", self.src).group(1)
        hashes = re.findall(r'"([0-9a-f]{64})"', values)
        self.assertTrue(hashes, "an unfilled placeholder would make every start fall back")
        self.assertNotIn("__FINGERPRINT", self.src)

    def test_fallback_is_the_conservative_box_never_off(self) -> None:
        body = self.src[self.src.index("public static Guard.Refine effective"):self.src.index("public static boolean inFallback")]
        self.assertIn("Guard.Refine.OFF", body)  # OFF is the N7-A box reach, i.e. the conservative guard, not a disabled one
        guard = (JAVA / "Guard.java").read_text()
        self.assertIn("Refine { OFF, PRECHECK, HYBRID }", guard)
        self.assertRegex(self.mixin, r"switch \(MonsterRoomSelfCheck\.effective\(Guard\.REFINE\)\)")
        self.assertRegex(self.mixin, r"default -> cancel = Guard\.shouldCancel\(Guard\.MONSTER_ROOM, level, origin, List\.of\(MonsterRoomGeometry\.maxBox\(origin\)\)\)")

    def test_both_checks_exist_and_fail_closed(self) -> None:
        for token in ("FINGERPRINT_UNAVAILABLE", "FINGERPRINT_MISMATCH", "RUNTIME_VIOLATION", "MessageDigest.getInstance(\"SHA-256\")"):
            self.assertIn(token, self.src)
        self.assertIn("MonsterRoomSelfCheck.end(level, origin)", self.mixin)
        self.assertIn("MonsterRoomSelfCheck.discard()", self.mixin)
        mod = (JAVA / "SpikeMod.java").read_text()
        self.assertLess(mod.index("MonsterRoomSelfCheck.verifyAtStartup()"), mod.index("ProtectionConfig.resolve(server)"))
        guard = (JAVA / "Guard.java").read_text()
        self.assertIn("MonsterRoomSelfCheck.begin(region, broad, pieces)", guard)

    def test_fingerprint_override_and_fault_injection_are_lab_only(self) -> None:
        self.assertIn("Guard.LAB ? System.getenv(\"SG01_LAB_MR_FINGERPRINT\") : null", self.src)
        geometry = (JAVA / "MonsterRoomGeometry.java").read_text()
        self.assertIn("Guard.FAULT == Guard.Fault.PRECHECK_BLIND", geometry)  # FAULT itself is parsed through labEnv (see test_n72)

    def test_production_has_no_timing_instrumentation(self) -> None:
        perf = (JAVA / "Perf.java").read_text()
        self.assertRegex(perf, r"public static void mark\(\) \{\s*if \(!Guard\.LAB\) return;")


if __name__ == "__main__":
    unittest.main()
