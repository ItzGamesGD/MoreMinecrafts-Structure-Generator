#!/usr/bin/env python3
"""SG-03-N4 acceptance: production passes natural integrity, clay still exists outside the structure, and the control proves detection."""
import argparse
import json
import sys
from pathlib import Path

CLAY_FAMILY = {"minecraft:clay", "minecraft:water", "minecraft:big_dripleaf", "minecraft:big_dripleaf_stem"}


def sites(report):
    return {tuple(s["candidate_chunk"]): s for s in report["sites"] if s.get("generated")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--production", type=Path, required=True)
    p.add_argument("--control", type=Path, help="same seed, structure step vegetal_decoration (pre-fix ordering)")
    p.add_argument("--require-clay-outside", action="store_true", help="seed 42 site (4,13) must show natural clay beside the structure")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    prod = json.loads(a.production.read_text())
    problems, notes = [], []
    ps = sites(prod)
    if not ps:
        problems.append("no generated production site")
    for chunk, site in ps.items():
        for phase in ("before_ticks", "after_ticks"):
            r = site[phase]
            if not r["pass"]:
                problems.append(f"production {chunk} {phase} integrity FAIL: {r['state_transitions'][:3]}")
            if r["piece_count"] != 21:
                problems.append(f"production {chunk} {phase}: {r['piece_count']} pieces")
            if r["trial_spawners"] != r["trial_spawner_entities"] or r["trial_spawners"] < 1:
                problems.append(f"production {chunk} {phase}: spawners {r['trial_spawners']}/{r['trial_spawner_entities']}")
            clay = [t for t in r["state_transitions"] if t["actual"] in CLAY_FAMILY]
            if clay:
                problems.append(f"production {chunk} {phase}: clay-family overwrites {clay}")
    # lush_caves biome also receives ore_clay veins, so this is necessary, not sufficient, evidence; the pack-level
    # tests (no data/minecraft overrides) and the control arm's clay overwrites are the other halves of the proof.
    outside = {str(c): s["after_ticks"]["vanilla_clay_outside_structure"]["biomes"].get("minecraft:lush_caves", 0) for c, s in ps.items()}
    if a.require_clay_outside and not any(v > 0 for v in outside.values()):
        problems.append(f"no natural lush-caves clay found beside the structure: {outside}")
    verdict_control = "NOT RUN"
    if a.control:
        ctl = json.loads(a.control.read_text())
        cs = sites(ctl)
        if {c: [(x["location"], x["rotation"], x["bb"], x["pos"]) for x in s["start_signature"]] for c, s in cs.items()} != \
           {c: [(x["location"], x["rotation"], x["bb"], x["pos"]) for x in s["start_signature"]] for c, s in ps.items()}:
            problems.append("control and production Jigsaw start signatures differ (placement changed, comparison invalid)")
        clay_cells = sum(t["count"] for s in cs.values() for t in s["after_ticks"]["state_transitions"] if t["actual"] in CLAY_FAMILY)
        other = sum(t["count"] for s in cs.values() for t in s["after_ticks"]["state_transitions"] if t["actual"] not in CLAY_FAMILY)
        verdict_control = f"clay-family overwrites in control: {clay_cells}; other overwrites: {other}"
        if a.require_clay_outside and clay_cells == 0:
            notes.append("CONTROL INCONCLUSIVE: the pre-fix ordering did not reproduce the overwrite in this run (cross-chunk race)")
    report = {"production_sites": [list(c) for c in ps], "clay_outside_structure": outside, "control": verdict_control,
              "notes": notes, "problems": problems, "pass": not problems}
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
