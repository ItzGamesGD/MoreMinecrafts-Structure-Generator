"""SG-03-N4: the lush-cave clay overwrite is resolved by structure ordering, not by suppressing vanilla features."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))
from worldgen_steps import SG01_STEP, SG02_STEP, STRUCTURE_STEP  # noqa: E402

STEPS = ["raw_generation", "lakes", "local_modifications", "underground_structures", "surface_structures", "strongholds",
         "underground_ores", "underground_decoration", "fluid_springs", "vegetal_decoration", "top_layer_modification"]
# Vanilla 26.3 lush_caves / deep_dark / default-overworld feature steps, read from the server jar's biome data.
OVERLAY_FEATURE_STEP = {"amethyst_geode": 2, "monster_room": 3, "sculk_patch_deep_dark": 7, "sculk_vein": 7, "lush_caves_clay": 9}
PACKS = {n: ROOT / f"exports/sg-0{n}/forgotten-underground-kingdom/datapack" for n in (1, 2, 3)}
STRUCTURE = "data/moreminecrafts/worldgen/structure/forgotten_kingdom/central_cavern.json"


class ClayResolutionTests(unittest.TestCase):
    def test_sg03_generates_after_all_known_overlay_features(self) -> None:
        step = json.loads((PACKS[3] / STRUCTURE).read_text())["step"]
        self.assertEqual(step, STRUCTURE_STEP, "SG-03")
        for feature, index in OVERLAY_FEATURE_STEP.items():
            self.assertGreater(STEPS.index(step), index, f"SG-03 must follow {feature} (step {index})")

    def test_sg01_and_sg02_keep_the_steps_they_had_before_pr19(self) -> None:
        """N10-R: PR #19 moved all three packs, but the clay overwrite was demonstrated for SG-03 only; SG-01 and SG-02 are restored to their original steps."""
        self.assertEqual(SG01_STEP, "vegetal_decoration")
        self.assertEqual(SG02_STEP, "strongholds")
        self.assertEqual(json.loads((PACKS[1] / STRUCTURE).read_text())["step"], SG01_STEP)
        self.assertEqual(json.loads((PACKS[2] / STRUCTURE).read_text())["step"], SG02_STEP)

    def test_sg03_step_does_not_depend_on_the_other_packs(self) -> None:
        # SG-03 is written through SG-02's write_pack; its step is the function default, so changing SG-02's step cannot move SG-03.
        self.assertNotEqual(SG02_STEP, STRUCTURE_STEP)
        self.assertEqual(json.loads((PACKS[3] / STRUCTURE).read_text())["step"], STRUCTURE_STEP)

    def test_no_pack_overrides_or_disables_any_vanilla_feature(self) -> None:
        """Clay stays enabled: production packs must not ship any minecraft-namespace worldgen, tag or feature file."""
        for n, pack in PACKS.items():
            self.assertFalse((pack / "data/minecraft").exists(), f"SG-0{n} ships data/minecraft overrides")
            self.assertEqual(sorted(p.name for p in (pack / "data").iterdir()), ["moreminecrafts"], f"SG-0{n}")
            for f in pack.rglob("*.json"):
                self.assertNotIn("lush_caves_clay", f.read_text(), f"{f.relative_to(pack)} mentions the clay feature")

    def test_only_the_generation_step_changed_in_the_structure_definition(self) -> None:
        for n, pack in PACKS.items():
            d = json.loads((pack / STRUCTURE).read_text())
            self.assertEqual(d["biomes"], "#minecraft:is_overworld")
            self.assertEqual(d["start_height"]["min_inclusive"], {"absolute": -40})
            self.assertEqual(d["start_height"]["max_inclusive"], {"absolute": -20})
            self.assertEqual(d["terrain_adaptation"], "encapsulate")
            self.assertEqual(d["type"], "minecraft:jigsaw")
            sets = json.loads((pack / "data/moreminecrafts/worldgen/structure_set/forgotten_kingdom/central_cavern.json").read_text())
            self.assertEqual(sets["placement"]["spacing"], 34)
            self.assertEqual(sets["placement"]["separation"], 12)
            self.assertEqual(sets["placement"]["exclusion_zone"], {"chunk_count": 12, "other_set": "minecraft:trial_chambers"})

    def test_the_ab_treatment_file_is_not_in_production(self) -> None:
        treatment = ROOT / "validation/minecraft-visual/sg03-natural/ab/disable-lush-caves-clay.json"
        self.assertTrue(treatment.exists())  # kept only as an experiment fixture
        for pack in PACKS.values():
            self.assertFalse((pack / "data/minecraft/worldgen/placed_feature/lush_caves_clay.json").exists())


if __name__ == "__main__":
    unittest.main()
