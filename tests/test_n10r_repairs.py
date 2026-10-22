"""N10-R: unit tests of the pure repair classes (compiled with javac, no Minecraft on the classpath) and static guards on the packaged-jar rules."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mod/sg-worldgen-protection/src/main/java/dev/itzgamesgd/sgprotection"

JAVA_TEST = r'''
import dev.itzgamesgd.sgprotection.ExemptionScope;
import dev.itzgamesgd.sgprotection.UncertainFootprint;
import java.util.Random;

public class Check {
    static int failures = 0;
    static void check(boolean ok, String what) { if (!ok) { failures++; System.out.println("FAIL " + what); } }

    public static void main(String[] a) throws Exception {
        // nested scopes
        boolean t1 = ExemptionScope.enter(true);
        boolean t2 = ExemptionScope.enter(true);
        check(ExemptionScope.depth() == 2 && ExemptionScope.active(), "nested depth 2");
        ExemptionScope.exit(t2);
        check(ExemptionScope.depth() == 1 && ExemptionScope.active(), "inner exit leaves the outer scope open");
        ExemptionScope.exit(t1);
        check(ExemptionScope.depth() == 0 && !ExemptionScope.active(), "outer exit closes");
        // a non-exempt scope never changes the depth, even inside an exempt one
        boolean own = ExemptionScope.enter(true);
        boolean other = ExemptionScope.enter(false);
        check(ExemptionScope.depth() == 1, "non-exempt enter does not increment");
        ExemptionScope.exit(other);
        check(ExemptionScope.depth() == 1, "non-exempt exit does not decrement");
        ExemptionScope.exit(own);
        check(ExemptionScope.depth() == 0, "balanced");
        // exception safety: the finally pattern used by the mixin restores the depth
        try {
            boolean tok = ExemptionScope.enter(true);
            try { throw new IllegalStateException("placement failed"); } finally { ExemptionScope.exit(tok); }
        } catch (IllegalStateException expected) { }
        check(ExemptionScope.depth() == 0, "depth restored after an exception");
        try {
            boolean tok = ExemptionScope.enter(true);
            try { throw new StackOverflowError(); } finally { ExemptionScope.exit(tok); }
        } catch (StackOverflowError expected) { }
        check(ExemptionScope.depth() == 0, "depth restored after an Error");
        // reload lifecycle: the decision is taken once; the exit uses the entry token even if the protected set changed in between
        boolean protectedAtEntry = true, protectedAtExit = false;   // the set was swapped while the scope was open
        boolean tok = ExemptionScope.enter(protectedAtEntry);
        ExemptionScope.exit(tok);                                    // old design re-evaluated protectedAtExit (false) here and leaked
        check(ExemptionScope.depth() == 0 && !protectedAtExit, "no leak when the protected set changes between enter and exit");
        // exit never goes below zero, and a stray exit does not create credit
        ExemptionScope.exit(true);
        check(ExemptionScope.depth() == 0, "stray exit stays at zero");
        // thread isolation: an open scope on one thread is invisible to another
        boolean mine = ExemptionScope.enter(true);
        final boolean[] seen = {true};
        Thread th = new Thread(() -> seen[0] = ExemptionScope.active());
        th.start(); th.join();
        check(!seen[0], "another thread is not exempt");
        ExemptionScope.exit(mine);

        // footprints: bounded by the 3x3 zone
        int[] zone = UncertainFootprint.zone(10, -4);
        check(zone[0] == 9 && zone[1] == -5 && zone[2] == 11 && zone[3] == -3, "zone is centre +-1");
        int[] c = UncertainFootprint.ofChunk(10, -4, zone);
        check(c != null && UncertainFootprint.columns(c) == 1, "missing chunk = its own column");
        check(UncertainFootprint.ofChunk(30, 30, zone) == null, "a chunk outside the zone has no footprint");
        int[] near = UncertainFootprint.ofStart(10 + 9, -4, zone);   // start 9 chunks east of the centre: reaches only the nearest zone column
        check(near != null && UncertainFootprint.columns(near) == 3 && near[0] == 11, "far start reaches one zone column");
        check(UncertainFootprint.ofStart(10 + 10, -4, zone) == null, "a start 10 chunks away cannot reach the zone");
        int[] full = UncertainFootprint.ofStart(10, -4, zone);
        check(full != null && UncertainFootprint.columns(full) == 9, "a start at the centre can cover the whole zone and no more");
        check(UncertainFootprint.contains(c, 10 * 16 + 5, -4 * 16 + 15) && !UncertainFootprint.contains(c, 10 * 16 + 16, -4 * 16), "contains uses chunk coordinates");
        check(UncertainFootprint.contains(UncertainFootprint.ofChunk(-1, -1, UncertainFootprint.zone(-1, -1)), -1, -1), "negative block coordinates map to chunk -1");
        Random r = new Random(7);
        for (int i = 0; i < 20000; i++) {
            int[] z = UncertainFootprint.zone(r.nextInt(2000) - 1000, r.nextInt(2000) - 1000);
            int[] f = UncertainFootprint.ofStart(z[0] + r.nextInt(30) - 15, z[1] + r.nextInt(30) - 15, z);
            if (f != null) check(UncertainFootprint.columns(f) >= 1 && UncertainFootprint.columns(f) <= 9 && f[0] >= z[0] && f[2] <= z[2] && f[1] >= z[1] && f[3] <= z[3], "bounded by the zone");
        }
        System.out.println(failures == 0 ? "ALL OK" : failures + " FAILURES");
        System.exit(failures == 0 ? 0 : 1);
    }
}
'''


class PureRepairClassesTest(unittest.TestCase):
    def test_pure_classes_behave(self) -> None:
        javac = shutil.which("javac") or (Path(os.environ.get("JAVA_HOME", "")) / "bin/javac")
        if not javac or not Path(javac).exists():
            self.skipTest("no javac available")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "Check.java").write_text(JAVA_TEST)
            subprocess.run([str(javac), "-d", d, str(SRC / "ExemptionScope.java"), str(SRC / "UncertainFootprint.java"), str(out / "Check.java")], check=True, capture_output=True)
            java = Path(javac).parent / "java"
            run = subprocess.run([str(java), "-cp", d, "Check"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("ALL OK", run.stdout)


class SourceRuleTest(unittest.TestCase):
    def test_write_guard_keeps_partial_hits_and_never_returns_unprotected_on_unavailable(self) -> None:
        wg = (SRC / "WriteGuard.java").read_text()
        self.assertNotIn("return List.of();\n        }\n        if (!hits.isEmpty()) REGIONS_WITH_PIECES", wg)
        self.assertIn("Guard.scanZone(region, zoneBox, u)", wg)
        self.assertIn("UNCERTAIN_REFUSED", wg)
        self.assertIn("LOG_FIRST", wg)  # incident logging is bounded

    def test_exemption_uses_an_entry_token(self) -> None:
        mixin = (SRC / "mixin/StructureStartWriteGuardMixin.java").read_text()
        self.assertIn("boolean own = WriteGuard.enterPlacement", mixin)
        self.assertIn("WriteGuard.exitPlacement(own)", mixin)
        self.assertIn("finally", mixin)

    def test_lab_entrypoint_needs_opt_in_and_the_lab_mod_id(self) -> None:
        mod = (SRC / "SgProtectionMod.java").read_text()
        self.assertIn('Boolean.getBoolean(LAB_OPT_IN_PROPERTY)', mod)
        self.assertIn("LAB_MOD_ID.equals(id)", mod)
        gradle = (ROOT / "mod/sg-worldgen-protection/build.gradle").read_text()
        self.assertEqual(gradle.count("-Dsg_worldgen_protection.lab=true"), 1)  # only the lab run configuration opts in

    def test_mod_loads_on_integrated_and_dedicated_servers(self) -> None:
        meta = (ROOT / "mod/sg-worldgen-protection/src/main/resources/fabric.mod.json").read_text()
        self.assertIn('"environment": "*"', meta)
        self.assertNotIn('"environment": "server"', meta)
        self.assertNotIn("net.minecraft.client", "".join(p.read_text() for p in SRC.rglob("*.java")))


if __name__ == "__main__":
    unittest.main()
