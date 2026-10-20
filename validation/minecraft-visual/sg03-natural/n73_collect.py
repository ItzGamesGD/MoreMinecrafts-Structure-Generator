#!/usr/bin/env python3
"""N7-A3: collect every stage result from one results directory into docs/sg-03/evidence/n7a3-summary.json.
usage: n73_collect.py RESULTS_DIR --out FILE   (RESULTS_DIR = the n73 directory written by n73_run.sh and the Phase scripts)
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics as st
from pathlib import Path


def lab(f: str) -> dict:
    n = json.loads(Path(f).read_text())
    a = n.get("before_ticks") or {}
    sr = n.get("spike_report") or {}
    m, g, p = sr.get("monster_room", {}), sr.get("geode", {}), sr.get("probe", {})
    return {
        "run": os.path.basename(os.path.dirname(f)), "generated": n.get("generated"),
        "mismatch": (a.get("expected", 0) - a.get("matched", 0)) if a else None,
        "foreign_in_template_air": sum((a.get("interior_intrusions") or {}).values()) if a else None,
        "pieces": a.get("pieces"), "trial_spawners": a.get("trial_spawners"),
        "monster_cancelled": m.get("cancelled"), "geode_cancelled": g.get("cancelled"),
        "unavailable": (m.get("unavailable") or 0) + (g.get("unavailable") or 0),
        "scheduling": sum(p.get(k, 0) for k in ("chunkmap_schedule", "holder_schedule", "server_get_blocking", "server_get_future")),
        "region_reads": p.get("region_get_calls"), "hybrid_skip": m.get("hybrid_skip"),
        "shadow_checks": m.get("shadow_checks"), "shadow_violations": m.get("shadow_violations"),
    }


def group(root: Path, pattern: str) -> list[dict]:
    return [lab(f) for f in sorted(glob.glob(str(root / pattern / "lab.json")))]


def tally(rows: list[dict]) -> dict:
    return {
        "runs": len(rows), "corrupted": sum(1 for r in rows if r["mismatch"]),
        "foreign_runs": sum(1 for r in rows if r["foreign_in_template_air"]),
        "pieces_not_21": sum(1 for r in rows if r["pieces"] not in (None, 21)),
        "unavailable": sum(r["unavailable"] or 0 for r in rows), "scheduling_requests": sum(r["scheduling"] or 0 for r in rows),
        "monster_cancelled_total": sum(r["monster_cancelled"] or 0 for r in rows), "geode_cancelled_total": sum(r["geode_cancelled"] or 0 for r in rows),
        "shadow_checks": sum(r["shadow_checks"] or 0 for r in rows), "shadow_violations": sum(r["shadow_violations"] or 0 for r in rows),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    root = a.root
    out: dict = {}
    out["regression_H"] = tally(group(root, "regression/H_*"))
    out["regression_C"] = tally(group(root, "regression/C_*"))
    out["shadow_HS"] = tally(group(root, "shadow/HS_*"))
    out["concurrency"] = {"threads_1": tally(group(root, "concurrency/H_*_rc1")), "threads_4_H": tally(group(root, "concurrency/H_*_rc4")),
                          "threads_4_C": tally(group(root, "concurrency/C_*_rc4"))}
    out["single_thread"] = {c: group(root, f"single_thread/{c}_*") for c in ("V", "A", "B", "C", "H")}
    out["noise_floor_vanilla"] = tally(group(root, "noise/V_*"))
    out["other_mod_sparse"] = group(root, "other_mod/*")
    out["soak_radius9"] = group(root, "soak/*")
    perf = root / "perf_summary.json"
    if perf.exists():
        out["benchmark_summary"] = json.loads(perf.read_text())
    ew = root / "existing_world" / "existing_world.json"
    if ew.exists():
        out["existing_world"] = json.loads(ew.read_text())
    ctrl = root / "existing_world_control" / "existing_world_control.json"
    if ctrl.exists():
        out["existing_world_control"] = json.loads(ctrl.read_text())
    tv = root / "tag_variants" / "tag_variants.json"
    if tv.exists():
        out["tag_variants"] = json.loads(tv.read_text())
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print({k: (v if isinstance(v, dict) and "runs" in v else type(v).__name__) for k, v in out.items()})


if __name__ == "__main__":
    main()
