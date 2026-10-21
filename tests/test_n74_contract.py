"""CODE-level guards for the N7-A4 protection contract (runtime evidence comes from contract_variants.py against the real module)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "mod/sg-worldgen-protection/src/main/java/dev/itzgamesgd/sg01spike"
LAB = ROOT / "validation/minecraft-visual/sg03-natural"
CODES = ["MANIFEST_MISSING", "MANIFEST_CONFLICT", "MANIFEST_INVALID", "FORMAT_UNSUPPORTED", "MANIFEST_STALE", "MANIFEST_EMPTY", "REQUIRED_UNRESOLVED",
         "OWNER_PACK_INCOMPATIBLE", "GAME_VERSION_MISMATCH", "OWNERSHIP_MISMATCH", "EXTENSION_MALFORMED", "EXTENSION_UNRESOLVED"]


class ProtectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = (SPIKE / "ProtectionContract.java").read_text()

    def test_every_failure_has_a_stable_code_and_throws(self) -> None:
        for code in CODES:
            self.assertRegex(self.src, rf'new ContractViolation\("{code}"', code)
        self.assertIn("extends IllegalStateException", self.src)

    def test_manifest_is_single_provider_and_authoritative_for_required_structures(self) -> None:
        self.assertIn("getResourceStack(MANIFEST)", self.src)
        self.assertRegex(self.src, r"providers\.size\(\) > 1")
        self.assertIn("SUPPORTED_FORMATS", self.src)
        self.assertIn("MIN_REVISION", self.src)

    def test_pack_format_is_checked_for_the_owner_only(self) -> None:
        # getPack is called exactly once, with the owner pack's id; no other pack's declared format is ever inspected
        self.assertEqual(len(re.findall(r"getPack\(", self.src)), 1)
        self.assertIn("getPack(owner)", self.src)
        self.assertNotIn("getAvailablePacks", self.src)
        self.assertNotIn("getSelectedPacks", self.src)

    def test_extensions_are_additive_only(self) -> None:
        self.assertIn("EXTENSION_REPLACE_IGNORED", self.src)  # N7-C: replace is ignored with a warning and the entries are still added
        self.assertIn("effective.add(", self.src)
        self.assertNotIn("effective.remove", self.src)
        self.assertNotIn("effective.retainAll", self.src)

    def test_reload_rejection_keeps_the_last_validated_set(self) -> None:
        cfg = (SPIKE / "ProtectionConfig.java").read_text()
        body = cfg[cfg.index("public static void reload"):cfg.index("public static int protectedCountOrZero")]
        self.assertIn("catch (RuntimeException e)", body)
        self.assertIn("keeping the last validated protection set", body)
        self.assertNotIn("protectedStructures = null", body)

    def test_manifest_is_the_only_mode(self) -> None:
        cfg = (SPIKE / "ProtectionConfig.java").read_text()
        self.assertNotIn("SG01_PROTECTION", cfg)
        self.assertNotIn("MANIFEST_MODE", cfg)

    def test_every_error_carries_a_remedy(self) -> None:
        self.assertIn('" Remedy: "', self.src)
        # every ContractViolation construction passes message and remedy
        for m in re.finditer(r'new ContractViolation\("([A-Z_]+)"', self.src):
            self.assertIn(m.group(1), CODES)

    def test_contract_experiment_covers_every_code_and_the_unrelated_pack_case(self) -> None:
        exp = (LAB / "contract_variants.py").read_text()
        for code in CODES:
            self.assertIn(f'"{code}"', exp, code)
        for case in ("conflicting_provider", "unrelated_pack_format_999", "reload_conflict", "reload_stale"):
            self.assertIn(f'"{case}"', exp, case)


if __name__ == "__main__":
    unittest.main()
