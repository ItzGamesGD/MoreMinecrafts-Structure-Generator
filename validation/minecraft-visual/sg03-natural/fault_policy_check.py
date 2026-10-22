#!/usr/bin/env python3
"""N10-R: the bounded fail-closed policy for unavailable structure data, exercised with the lab's injected faults (lab run configuration, write guard on).
usage: fault_policy_check.py --out DIR   (env: SERVER_JAR, SG_PACK, JAVA_HOME)
For each fault (a referenced start is missing / lies beyond the chunk cache / its read fails) at seed 173 chunk (-19,15) the check requires:
  - the structure is fully intact (every template cell, 21 pieces)          - the incident is counted by its cause and is NOT silent (unavailable > 0)
  - writes in the unreadable footprint were refused (uncertain_refused > 0) - the effect is bounded: only regions that reference the structure are affected"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = (("WM", "start_missing_or_invalid"), ("WO", "start_out_of_range"), ("WS", "start_failed"))


def problems(lab: dict, cause: str) -> list[str]:
    out: list[str] = []
    b = lab.get("before_ticks", {})
    if not lab.get("generated"):
        return ["the structure did not generate"]
    if b.get("matched") != b.get("expected") or b.get("pieces") != 21 or b.get("errors"):
        out.append(f"structure not intact: {b.get('matched')}/{b.get('expected')} cells, {b.get('pieces')} pieces")
    wg = lab.get("spike_report", {}).get("write_guard", {})
    if not wg.get("enabled"):
        out.append("write guard not enabled")
    if not wg.get("unavailable"):
        out.append("the unavailable-data incident was not counted (silent)")
    if cause not in (wg.get("unavailable_causes") or {}):
        out.append(f"cause {cause} not reported: {wg.get('unavailable_causes')}")
    if not wg.get("uncertain_refused_writes"):
        out.append("no write was refused in the unreadable footprint (fail-open)")
    if wg.get("unavailable", 0) >= wg.get("regions", 1):
        out.append("every region was affected: the effect is not bounded to regions that reference the structure")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    failed = 0
    for cfg, cause in CASES:
        subprocess.run(["bash", str(HERE / "n73_run.sh"), str(a.out), cfg, "173", "-19", "15", "rowmajor_rev", "1", "0"], check=False, env=os.environ)
        path = a.out / f"{cfg}_173_-19_15_rowmajor_rev_r1" / "lab.json"
        why = problems(json.loads(path.read_text()), cause) if path.exists() else ["no lab.json"]
        print(f"FAULT_POLICY {cfg} {cause} {'PASS' if not why else 'FAIL'} {why}", flush=True)
        failed += bool(why)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
