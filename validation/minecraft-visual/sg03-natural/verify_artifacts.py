#!/usr/bin/env python3
"""N7-D: verify the BUILT jars, not the source layout. usage: verify_artifacts.py OUT.json [--build]
Production jar (sg-worldgen-protection-<v>.jar) must contain only the required runtime classes and its two metadata files, read no SG01_* lab
variable, reference no lab class, apply exactly the four protection mixins and register no lab entrypoint. The lab jar (…-lab.jar) must contain
only lab classes, depend on the production mod and must not contain a production class."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

MOD = Path(__file__).resolve().parents[3] / "mod" / "sg-worldgen-protection"
PKG = "dev/itzgamesgd/sgprotection/"
PRODUCTION_CLASSES = {
    "DriftGuard", "DriftGuard$Armed", "DriftGuard$Level", "DriftGuard$State", "Guard", "Guard$Fault", "Guard$Finding", "Guard$Fixture", "Guard$Mode",
    "Guard$Refine", "GuardMarker", "GuardStats", "LabHooks", "LabHooks$1", "LabHooks$Config", "LabHooks$Holder", "MonsterRoomGeometry", "ProtectionConfig",
    "ProtectionContract", "ProtectionContract$ContractViolation", "ProtectionContract$Result", "SgProtectionMod", "mixin/GeodeFeatureMixin", "mixin/MonsterRoomFeatureMixin",
    "mixin/MonsterRoomFeatureMixin$1", "WriteGuard", "mixin/StructureStartWriteGuardMixin", "mixin/WorldGenRegionWriteGuardMixin",
    "ExemptionScope", "UncertainFootprint", "WriteGuard$Zone", "Guard$Uncertainty",
}
LAB_NAMES = re.compile(rb"(?<![A-Za-z])Probe(?![a-z])|ProbeMixin|(?<![A-Za-z])Perf(?![a-z])|Sampler|MonsterRoomOracle|LabMod|LabMixinPlugin|ForeignMonsterRoom|ForeignGeode|dev/itzgamesgd/sgprotection/lab")


def main() -> None:
    out = Path(sys.argv[1])
    if "--build" in sys.argv:
        subprocess.run(["./gradlew", "--no-daemon", "-q", "jar", "labJar"], cwd=MOD, check=True)
    # select by the project version, never by sort order (a stale jar of an older version must not be verified)
    version = re.search(r"^version\s*=\s*'([^']+)'", (MOD / "build.gradle").read_text(), re.M).group(1)
    libs = MOD / "build" / "libs"
    prod = libs / f"sg-worldgen-protection-{version}.jar"
    lab = libs / f"sg-worldgen-protection-{version}-lab.jar"
    stale = sorted(j.name for j in libs.glob("sg-worldgen-protection-*.jar") if j not in (prod, lab))
    if stale:
        print(f"note: ignoring jars of other versions: {stale}", file=sys.stderr)
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    with zipfile.ZipFile(prod) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        classes = {n[len(PKG):-6] for n in names if n.startswith(PKG) and n.endswith(".class")}
        others = sorted(n for n in names if not (n.startswith(PKG) and n.endswith(".class")))
        check("production jar: exactly the required classes", classes == PRODUCTION_CLASSES, f"extra={sorted(classes - PRODUCTION_CLASSES)} missing={sorted(PRODUCTION_CLASSES - classes)}")
        check("production jar: only metadata besides classes", set(others) <= {"META-INF/MANIFEST.MF", "fabric.mod.json", "sgprotection.mixins.json"}, str(others))
        blob = b"".join(z.read(n) for n in names if n.endswith(".class"))
        check("production jar: no SG01_ lab variable is read", b"SG01_" not in blob)
        check("production jar: no reference to a lab class or lab mod", LAB_NAMES.search(blob) is None, str(LAB_NAMES.findall(blob)[:5]))
        # N10-R: the lab entrypoint is honoured only for the lab mod's own id and only with the operator opt-in property; the id is the only lab reference allowed
        sm = z.read(PKG + "SgProtectionMod.class")
        check("production jar: lab entrypoint needs the opt-in property and the lab mod id (once, in the entrypoint class)",
              blob.count(b"sg_worldgen_protection_lab") == 1 and sm.count(b"sg_worldgen_protection_lab") == 1 and b"sg_worldgen_protection.lab" in sm)
        check("production jar: references no client class (loads on dedicated and integrated servers)", b"net/minecraft/client" not in blob and b"net.minecraft.client" not in blob)
        check("production jar: reads only SG_PROTECTION_REPORT from the environment", set(re.findall(rb"SG_[A-Z_0-9]+", blob)) <= {b"SG_PROTECTION_REPORT", b"SG_PROTECTION", b"SG_PROTECTION_REPORT"})
        mod = json.loads(z.read("fabric.mod.json"))
        check("production jar: mod id and entrypoints", mod["id"] == "sg_worldgen_protection" and list(mod["entrypoints"]) == ["main"], f"{mod['id']} {list(mod['entrypoints'])}")
        cfg = json.loads(z.read("sgprotection.mixins.json"))
        check("production jar: exactly the four protection mixins, no plugin", sorted(cfg["mixins"]) == ["GeodeFeatureMixin", "MonsterRoomFeatureMixin", "StructureStartWriteGuardMixin", "WorldGenRegionWriteGuardMixin"] and "plugin" not in cfg, str(cfg["mixins"]))
        check("production jar: mixins required and fail-loud", cfg["required"] is True and cfg["injectors"]["defaultRequire"] == 1)
        check("production jar: ships no datapack data", not any(n.startswith("data/") for n in names))
    with zipfile.ZipFile(lab) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        check("lab jar: only lab classes", all(n.startswith(PKG + "lab/") for n in names if n.endswith(".class")), str([n for n in names if n.endswith(".class") and not n.startswith(PKG + "lab/")]))
        check("lab jar: contains no production class", not any(n.startswith(PKG) and not n.startswith(PKG + "lab/") and n.endswith(".class") for n in names))
        mod = json.loads(z.read("fabric.mod.json"))
        check("lab jar: separate mod id that depends on production", mod["id"] == "sg_worldgen_protection_lab" and "sg_worldgen_protection" in mod["depends"])
    report = {"production_jar": prod.name, "production_bytes": prod.stat().st_size, "lab_jar": lab.name, "lab_bytes": lab.stat().st_size, "checks": checks,
              "all_pass": all(c["pass"] for c in checks)}
    out.write_text(json.dumps(report, indent=1) + "\n")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"] + ("" if c["pass"] else f"  [{c['detail']}]"))
    print(f"{sum(c['pass'] for c in checks)}/{len(checks)} checks pass")
    sys.exit(0 if report["all_pass"] else 1)


if __name__ == "__main__":
    main()
