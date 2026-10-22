"""N9: static guards on the live-acceptance driver (no live run here; the run itself needs a graphical client)."""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAT = ROOT / "validation" / "minecraft-visual" / "sg03-natural"
DRIVER = (NAT / "live_acceptance.py").read_text()
CRITERIA = (ROOT / "docs" / "sg-03" / "n9-live-acceptance-criteria.md").read_text()


class LiveAcceptanceDriverTest(unittest.TestCase):
    def test_driver_and_control_parse(self) -> None:
        for name in ("live_acceptance.py", "n9_stall_control.py"):
            ast.parse((NAT / name).read_text())

    def test_no_synthetic_placement(self) -> None:
        # criteria: "No synthetic placement (/place) is used anywhere in N9"
        self.assertIn("No synthetic placement", CRITERIA)
        for src in (DRIVER, (NAT / "n9_stall_control.py").read_text()):
            self.assertIsNone(re.search(r"cmd\(\s*f?[\"']\s*place\b", src))
            self.assertNotIn("/place ", src.replace("no /place", "").replace("No /place", ""))

    def test_runs_the_production_jar_not_the_lab_mod(self) -> None:
        self.assertIn("runJarServer", DRIVER)
        self.assertNotIn("runLabServer", DRIVER)
        self.assertNotIn("SG01_FEATURES", DRIVER)  # no lab environment is set

    def test_every_criterion_has_a_driver_step(self) -> None:
        for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            self.assertIn(f"L{i}_", DRIVER, f"L{i} has no step in the driver")
            self.assertRegex(CRITERIA, rf"\| L{i} \|")

    def test_input_that_counts_as_live_comes_from_xdotool(self) -> None:
        for needle in ('"keydown"', '"mousedown"', '"mousemove_relative"', "screenshot("):
            self.assertIn(needle, DRIVER)
        # the cursor warp that rotated the camera in run 4 must not come back
        self.assertNotIn('xdo("mousemove", "640", "360")', DRIVER)

    def test_server_only_evidence_is_labelled(self) -> None:
        for label in ("SERVER-ONLY", "SAVED-DATA"):
            self.assertIn(label, DRIVER)


if __name__ == "__main__":
    unittest.main()
