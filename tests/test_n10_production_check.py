"""N10: the production-module check must pass a real production result and fail every way protection can be missing."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pmc", ROOT / "validation/minecraft-visual/sg03-natural/production_module_check.py")
pmc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pmc)
GOOD = json.loads((ROOT / "tests/fixtures/pj_lab_trimmed.json").read_text())


class ProductionModuleCheckTest(unittest.TestCase):
    def mutated(self, fn) -> list[str]:
        lab = copy.deepcopy(GOOD)
        fn(lab)
        return pmc.problems(lab)

    def test_real_production_result_passes(self) -> None:
        self.assertEqual(pmc.problems(GOOD), [])

    def test_overwritten_structure_cells_fail(self) -> None:
        self.assertTrue(self.mutated(lambda d: d["before_ticks"].update(matched=d["before_ticks"]["expected"] - 1)))

    def test_missing_or_unexercised_write_guard_fails(self) -> None:
        self.assertTrue(self.mutated(lambda d: d["spike_report"]["write_guard"].update(enabled=False)))
        self.assertTrue(self.mutated(lambda d: d["spike_report"]["write_guard"].update(blocked_writes=0)))
        self.assertTrue(self.mutated(lambda d: d["spike_report"]["write_guard"].update(regions_with_pieces=0)))
        self.assertTrue(self.mutated(lambda d: d["spike_report"]["write_guard"].update(unavailable=2)))

    def test_lab_or_observe_configuration_fails(self) -> None:
        self.assertTrue(self.mutated(lambda d: d["spike_report"].update(lab=True)))
        self.assertTrue(self.mutated(lambda d: d["spike_report"].update(mode="OBSERVE")))

    def test_unreported_hooks_or_contract_fail(self) -> None:
        self.assertTrue(self.mutated(lambda d: d.update(mixin_log=[])))
        self.assertTrue(self.mutated(lambda d: d.update(generated=False)))


if __name__ == "__main__":
    unittest.main()
