#!/usr/bin/env python3
"""N10 production-module integration check: launch the BUILT production jar (gradle jar + runJarServer, no lab mod) on a fresh world, generate natural SG-03
sites, and assert that the approved write guard is loaded and the structure is intact. The integrity criteria are strict: every template cell must match.
usage: production_module_check.py --out DIR    (env: SERVER_JAR, SG_PACK, JAVA_HOME)
Sites: seed 173 chunk (-19,15) and seed 42 chunk (4,13), the sites used in N7 to N9."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES = ((173, -19, 15), (42, 4, 13))


def problems(lab: dict) -> list[str]:
    """Reasons this run does NOT show an intact structure protected by the loaded production write guard (empty list = pass)."""
    out: list[str] = []
    if not lab.get("generated"):
        return ["the structure did not generate"]
    b = lab.get("before_ticks", {})
    if b.get("matched") != b.get("expected") or not b.get("expected"):
        out.append(f"structure cells overwritten: {b.get('expected', 0) - b.get('matched', 0)} of {b.get('expected')}")
    if not b.get("pass"):
        out.append("template integrity check failed")
    if b.get("pieces") != 21:
        out.append(f"{b.get('pieces')} pieces, expected 21")
    if b.get("errors"):
        out.append(f"inspection errors: {b['errors'][:3]}")
    rep = lab.get("spike_report", {})
    if rep.get("lab"):
        out.append("a lab mod was loaded: this is not the production configuration")
    if rep.get("mode") != "ENFORCE":
        out.append(f"mode {rep.get('mode')}, expected ENFORCE")
    wg = rep.get("write_guard", {})
    if not wg.get("enabled"):
        out.append("the write guard is not enabled")
    if wg.get("unavailable", 1) != 0:
        out.append(f"write guard reported {wg.get('unavailable')} unavailable regions")
    if not wg.get("regions_with_pieces"):
        out.append("the write guard never saw a region with protected pieces")
    if not wg.get("blocked_writes"):
        out.append("the write guard blocked no write (it was not exercised)")
    log = "\n".join(lab.get("mixin_log", []))
    if "applied=true" not in log:
        out.append("the mixin hooks were not reported as applied")
    if "fingerprints validated" not in log:
        out.append("vanilla dependency fingerprints were not reported as validated")
    if "protection contract OK" not in log:
        out.append("the protection contract was not reported OK")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for seed, cx, cz in SITES:
        tag = f"PJ_{seed}_{cx}_{cz}_rowmajor_rev_r1"
        with (a.out / f"PJ_{seed}_{cx}_{cz}.run.log").open("w") as log:
            subprocess.run(["bash", str(HERE / "n73_run.sh"), str(a.out), "PJ", str(seed), str(cx), str(cz), "rowmajor_rev", "1", "0"], check=False, env=os.environ, stdout=log, stderr=subprocess.STDOUT)
        path = a.out / tag / "lab.json"
        lab = json.loads(path.read_text()) if path.exists() else {}
        why = problems(lab) if lab else ["no lab.json: the run did not complete"]
        print(f"PRODUCTION_MODULE_CHECK seed={seed} chunk=({cx},{cz}) {'PASS' if not why else 'FAIL'} {why}", flush=True)
        failed += bool(why)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
