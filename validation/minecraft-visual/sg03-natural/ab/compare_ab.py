#!/usr/bin/env python3
"""Independent, coordinate-level SG-03 natural-world A/B comparison.

Exit 0 means the *experiment* was valid, not that the clay hypothesis was proven.
Exit 2 means the arms were not comparable or runtime reports were invalid.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGET = (4, 13)
PHASES = ("before_ticks", "after_ticks")


def positions(check: dict) -> set[tuple[int, int, int]]:
    return {tuple(p) for p in check["clay_replacement_diagnostics"]["positions"]}


def index_sites(report: dict) -> dict[tuple[int, int], dict]:
    return {tuple(s["candidate_chunk"]): s for s in report["sites"]}


def compare(control: dict, treatment: dict) -> dict:
    errors = []
    for name, report in (("control", control), ("treatment", treatment)):
        if report.get("error"):
            errors.append(f"{name} runtime error: {report['error']}")
        if report.get("seed") != 42:
            errors.append(f"{name} must use seed 42")
        if report.get("generated_sites") != 2:
            errors.append(f"{name} expected two naturally generated sites")
    if errors:
        return {"experiment_valid": False, "errors": errors}
    if control.get("candidates") != treatment.get("candidates"):
        errors.append("candidate selection/order differs")
    a, b = index_sites(control), index_sites(treatment)
    if a.keys() != b.keys() or TARGET not in a:
        errors.append("candidate site keys differ or target site absent")
    for key in a.keys() & b.keys():
        if not a[key].get("generated") or not b[key].get("generated"):
            errors.append(f"missing natural structure start at {key}")
        if not a[key].get("start_signature") or a[key]["start_signature"] != b[key].get("start_signature"):
            errors.append(f"Jigsaw start/rooms/rotations/bounding boxes differ at {key}")
        if a[key].get("bbox") != b[key].get("bbox"):
            errors.append(f"structure bounds differ at {key}")
    if errors:
        return {"experiment_valid": False, "errors": errors,
                "structure_starts_match": False}
    rows = {}
    for phase in PHASES:
        ac, bc = a[TARGET][phase], b[TARGET][phase]
        p, q = positions(ac), positions(bc)
        rows[phase] = {
            "control_clay_count": len(p),
            "treatment_clay_count": len(q),
            "removed_positions": [list(x) for x in sorted(p - q)],
            "remaining_positions": [list(x) for x in sorted(p & q)],
            "introduced_positions": [list(x) for x in sorted(q - p)],
            "control_biomes": ac["clay_replacement_diagnostics"]["biomes"],
            "treatment_biomes": bc["clay_replacement_diagnostics"]["biomes"],
            "control_integrity_pass": ac["pass"],
            "treatment_integrity_pass": bc["pass"],
            "treatment_other_unexplained": bc["missing_or_other"] - len(q),
            "same_expected_solid_count": ac["expected"] == bc["expected"],
            "same_piece_count": ac["piece_count"] == bc["piece_count"] == 21,
        }
    stable = all(
        positions(a[TARGET][phase]) == positions(a[TARGET]["before_ticks"])
        and positions(b[TARGET][phase]) == positions(b[TARGET]["before_ticks"])
        for phase in PHASES
    )
    baseline_positive = all(rows[x]["control_clay_count"] > 0 for x in PHASES)
    no_clay_treatment = all(rows[x]["treatment_clay_count"] == 0 for x in PHASES)
    expected_equal = all(rows[x]["same_expected_solid_count"] and rows[x]["same_piece_count"] for x in PHASES)
    valid = stable and expected_equal and baseline_positive
    if not stable:
        errors.append("coordinates changed between before/after 200 ticks")
    if not expected_equal:
        errors.append("expected solid counts or piece counts differ")
    if not baseline_positive:
        errors.append("control did not reproduce any moss-to-clay replacements")
    supported = valid and no_clay_treatment and all(
        rows[x]["treatment_other_unexplained"] == 0 for x in PHASES
    )
    return {
        "experiment_valid": valid, "errors": errors,
        "structure_starts_match": True,
        "chunk_load_order_same": control["candidates"] == treatment["candidates"],
        "control_tick_stable": stable, "hypothesis_supported": supported,
        "hypothesis": "minecraft:lush_caves_clay placed feature causes moss-to-clay replacements",
        "conclusion": ("SUPPORTED_BY_SELECTIVE_SUPPRESSION" if supported
                       else "NOT_SUPPORTED_OR_INCONCLUSIVE"),
        "site": list(TARGET), "phases": rows,
        "other_site_integrity": {
            str(k): {
                "control": {phase: a[k][phase]["pass"] for phase in PHASES},
                "treatment": {phase: b[k][phase]["pass"] for phase in PHASES}
            } for k in sorted(a) if k != TARGET
        }
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--treatment", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        result = compare(json.loads(args.control.read_text()), json.loads(args.treatment.read_text()))
    except (KeyError, ValueError, TypeError) as e:
        result = {"experiment_valid": False, "errors": [f"invalid report: {type(e).__name__}: {e}"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "experiment_valid": result["experiment_valid"],
        "conclusion": result.get("conclusion"),
        "errors": result.get("errors"),
        "phase_counts": {k: (v["control_clay_count"], v["treatment_clay_count"])
                         for k, v in result.get("phases", {}).items()},
        "report": str(args.out),
    }, sort_keys=True))
    return 0 if result["experiment_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
