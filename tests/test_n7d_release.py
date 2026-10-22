"""N7-D guards: production/lab source separation, release hygiene and the lab hooks seam. The built-jar checks are in
validation/minecraft-visual/sg03-natural/verify_artifacts.py (they need Gradle)."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/sg-worldgen-protection"
MAIN = MOD / "src/main"
LAB = MOD / "src/lab"
LABJAVA = "dev.itzgamesgd.sgprotection.lab"
LAB_SYMBOLS = ("Probe", "Perf", "Sampler", "MonsterRoomOracle", "LabMod", "LabMixinPlugin", "ForeignMonsterRoom", "ForeignGeode")


class SourceSeparationTests(unittest.TestCase):
    def production_sources(self):
        return {p: p.read_text() for p in (MAIN / "java").rglob("*.java")}

    def test_production_sources_contain_no_lab_code_or_lab_references(self) -> None:
        for path, text in self.production_sources().items():
            for symbol in LAB_SYMBOLS:
                self.assertIsNone(re.search(rf"\b{symbol}\w*\b", text), f"{path.name} mentions {symbol}")
            self.assertNotIn(LABJAVA, text, path.name)
            # N10-R: the lab entrypoint is honoured only for the lab mod's own id; that id appears once, in the production entrypoint class, as the allow-list.
            self.assertEqual(text.count("sg_worldgen_protection_lab"), 1 if path.name == "SgProtectionMod.java" else 0, path.name)

    def test_production_reads_one_environment_variable_only_and_no_lab_setting(self) -> None:
        names = set()
        for path, text in self.production_sources().items():
            names |= set(re.findall(r'getenv\("([A-Za-z0-9_]+)"', text))
            self.assertNotIn("SG01_", text, path.name)
            self.assertNotIn("System.getProperty", text, path.name)
        self.assertEqual(names, {"SG_PROTECTION_REPORT"})

    def test_lab_hooks_are_the_only_seam_and_default_to_the_production_configuration(self) -> None:
        hooks = (MAIN / "java/dev/itzgamesgd/sgprotection/LabHooks.java").read_text()
        self.assertIn("new Config(Guard.Mode.ENFORCE, Guard.Refine.OFF, \"none\", Guard.Fixture.NONE, Guard.Fault.NONE, false, false, true)", hooks)
        holder = (MAIN / "java/dev/itzgamesgd/sgprotection/LabHolder.java").read_text()  # N10-R: the holder is package-private
        self.assertIn("static volatile LabHooks current = LabHooks.NONE;", holder)
        mod = (MAIN / "java/dev/itzgamesgd/sgprotection/SgProtectionMod.java").read_text()
        self.assertIn('LAB_ENTRYPOINT = "sg_worldgen_protection:lab"', mod)
        self.assertIn("more than one validation lab mod is installed", mod)

    def test_production_mod_and_mixin_metadata(self) -> None:
        mod = json.loads((MAIN / "resources/fabric.mod.json").read_text())
        self.assertEqual(mod["id"], "sg_worldgen_protection")
        self.assertEqual(set(mod["entrypoints"]), {"main"})
        self.assertIn("fabric-api", mod["depends"])  # the module uses Fabric API lifecycle events, so the dependency must be declared
        self.assertEqual(mod["entrypoints"]["main"], ["dev.itzgamesgd.sgprotection.SgProtectionMod"])
        self.assertNotIn("lab", json.dumps(mod).lower())
        cfg = json.loads((MAIN / "resources/sgprotection.mixins.json").read_text())
        self.assertEqual(sorted(cfg["mixins"]), ["GeodeFeatureMixin", "MonsterRoomFeatureMixin", "StructureStartWriteGuardMixin", "WorldGenRegionWriteGuardMixin"])
        self.assertNotIn("plugin", cfg)
        self.assertTrue(cfg["required"])
        self.assertEqual(cfg["injectors"]["defaultRequire"], 1)
        self.assertFalse((MAIN / "resources/data").exists(), "the module ships no datapack data")

    def test_lab_is_a_separate_mod_that_depends_on_production_only(self) -> None:
        mod = json.loads((LAB / "resources/fabric.mod.json").read_text())
        self.assertEqual(mod["id"], "sg_worldgen_protection_lab")
        self.assertIn("sg_worldgen_protection", mod["depends"])
        self.assertEqual(list(mod["entrypoints"]), ["sg_worldgen_protection:lab"])
        cfg = json.loads((LAB / "resources/sg-lab.mixins.json").read_text())
        probes = {p.stem for p in (LAB / "java").rglob("*ProbeMixin.java")}
        self.assertEqual(probes, {m for m in cfg["mixins"] if m.endswith("ProbeMixin")})
        self.assertTrue({"ForeignMonsterRoomMixin", "ForeignGeodeMixin"} <= set(cfg["mixins"]))
        for p in (LAB / "java").rglob("*.java"):
            self.assertIn(f"package {LABJAVA}", p.read_text(), p.name)

    def test_gradle_builds_two_artifacts_and_two_runs(self) -> None:
        build = (MOD / "build.gradle").read_text()
        for token in ("sourceSets {", "lab {", "tasks.register('labJar', Jar)", "labServer {", 'sg_worldgen_protection_lab" { sourceSet sourceSets.lab }'):
            self.assertIn(token, build)
        self.assertNotIn("sourceSets.lab", build[build.index("dependencies {"):build.index("sourceSets {")])  # main never depends on lab

    def test_lab_harness_uses_the_lab_run_and_production_uses_the_plain_run(self) -> None:
        lab = ROOT / "validation/minecraft-visual/sg03-natural"
        cl = (lab / "collision_lab.py").read_text()
        self.assertIn('"runServer" if a.production else "runLabServer"', cl)
        self.assertIn("runServer", (lab / "contract_variants.py").read_text())
        self.assertNotIn("runLabServer", (lab / "contract_variants.py").read_text())
        for name in ("soak.py", "existing_world.py"):
            self.assertIn("runLabServer", (lab / name).read_text(), name)


class NamingTests(unittest.TestCase):
    def test_production_naming_has_no_spike_leftovers_but_the_mod_id_is_unchanged(self) -> None:
        # N7-E: package dev.itzgamesgd.sgprotection, logger prefix SG_PROTECTION; the public mod id stays sg_worldgen_protection (no migration needed)
        files = [p for p in list(MAIN.rglob("*")) + list(LAB.rglob("*")) if p.is_file()]
        for p in files:
            text = p.read_text()
            for old in ("sg01spike", "SG_SPIKE", "sg01-spike", "SpikeMod"):
                self.assertNotIn(old, text, f"{p.name} still mentions {old}")
        self.assertTrue((MAIN / "java/dev/itzgamesgd/sgprotection/SgProtectionMod.java").is_file())
        self.assertFalse((MAIN / "java/dev/itzgamesgd/sg01spike").exists())
        self.assertTrue((MAIN / "resources/sgprotection.mixins.json").is_file())
        mod = json.loads((MAIN / "resources/fabric.mod.json").read_text())
        self.assertEqual(mod["id"], "sg_worldgen_protection")
        self.assertIn("SG_PROTECTION", (MAIN / "java/dev/itzgamesgd/sgprotection/SgProtectionMod.java").read_text())


class HygieneTests(unittest.TestCase):
    def test_no_bytecode_or_class_files_are_tracked(self) -> None:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        bad = [t for t in tracked if "__pycache__" in t or t.endswith((".pyc", ".pyo", ".class"))]
        self.assertEqual(bad, [])

    def test_gitignore_excludes_generated_caches_and_build_output(self) -> None:
        ignore = (ROOT / ".gitignore").read_text()
        for token in ("__pycache__/", "*.py[cod]", "*.class", "mod/sg-worldgen-protection/build/", "mod/sg-worldgen-protection/run/", "mod/sg-worldgen-protection/.gradle/"):
            self.assertIn(token, ignore)


if __name__ == "__main__":
    unittest.main()
