"""Assemble machine-generated tables for the Stage 24-C report from the JSON evidence."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa


def gameplay(variant):
    out = {}
    for m in MODULES:
        p = OUT / f"gameplay/result-{variant}-{m}.json"
        if p.exists():
            steps = json.loads(p.read_text())["steps"]
            out[m] = (sum(1 for s in steps if s.get("ok")), len(steps), [s["name"] for s in steps if not s.get("ok")])
    return out


def main():
    base, fixed = gameplay("pr10-baseline"), gameplay("fixed")
    lines = ["# Machine-generated evidence tables", "", "## Simulated-player gameplay: PR #10 baseline vs Stage 24-C final", "",
             "| module | PR #10 baseline | failed steps (baseline) | 24-C final | failed steps (final) |", "|---|---|---|---|---|"]
    for m in MODULES:
        b, f = base.get(m), fixed.get(m)
        lines.append(f"| `{m}` | {b[0]}/{b[1]} | {', '.join(b[2]) or '-'} | {f[0]}/{f[1]} | {', '.join(f[2]) or '-'} |")
    pl = {}
    for v in ("pr10-baseline", "fixed"):
        d = json.loads((OUT / f"placement/placement-report-{v}.json").read_text())["results"]
        pl[v] = d
    lines += ["", "## Isolated placement (8 modules x 4 rotations, 1200 ticks)", "",
              "| module | rotations | PR #10 mismatching blocks | final mismatching blocks | block entities missing | water kept / expected | stray water |", "|---|---|---|---|---|---|---|"]
    for m in MODULES:
        ks = [k for k in pl["fixed"] if k.startswith(m + "@")]
        bm = sum(pl["pr10-baseline"][k]["mismatches"] for k in ks)
        fm = sum(pl["fixed"][k]["mismatches"] for k in ks)
        be = sum(len(pl["fixed"][k]["block_entities_missing"]) for k in ks)
        w = pl["fixed"][ks[0]]
        lines.append(f"| `{m}` | {len(ks)} | {bm} | {fm} | {be} | {w['water_present_after_1200_ticks']}/{w['expected_water']} | {sum(pl['fixed'][k]['stray_water_blocks'] for k in ks)} |")
    wa = json.loads((OUT / "worldgen/worldgen-analysis.json").read_text())
    agg, n, ovl, rots, crit = defaultdict(Counter), Counter(), Counter(), defaultdict(Counter), defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for s in wa:
        for m in s["modules"]:
            k = m["module"]
            n[k] += 1
            ovl[k] += len(m["overlapping_pieces"])
            rots[k][m["rotation"]] += 1
            for c, v in m["block_replacement"].items():
                agg[k][c] += v
            for c, (t, l) in m["critical_blocks_total_lost"].items():
                crit[k][c][0] += t
                crit[k][c][1] += l
    lines += ["", f"## Real Ancient City generation: {len(wa)} seeds (24001-24024), vanilla vs candidate", "",
              f"- placements (template/position/rotation) identical to vanilla in **{sum(1 for s in wa if s['placements_identical_to_vanilla'])}/{len(wa)}** cities",
              f"- only bounding-box difference: `medium_ruin_2` ({sum(len(s['bounding_box_differences']) for s in wa)} pieces, y-extent 5 -> 8)", "",
              "| module | generated pieces | rotations seen | BB overlaps with other pieces | blocks identical | cracked (vanilla processor) | removed to air (block_rot / lantern rule) | sculk overlay (vanilla feature) | other replacement |", "|---|---|---|---|---|---|---|---|---|"]
    for m in MODULES:
        t = sum(agg[m].values()) or 1
        lines.append(f"| `{m}` | {n[m]} | {', '.join(f'{r}:{c}' for r, c in sorted(rots[m].items()))} | {ovl[m]} | {agg[m]['identical']/t:.1%} | {agg[m]['cracked_by_processor']/t:.1%} | {agg[m]['removed_to_air']/t:.1%} | {agg[m]['sculk_feature_overlay']/t:.1%} | {(agg[m]['replaced_by_other']+agg[m]['same_block_other_state'])/t:.2%} |")
    lines += ["", "### Critical blocks lost after vanilla processors (lost / total, all generated pieces)", "", "| module | " + " | ".join(["ladder", "stairs", "bed", "door", "container", "parapet_wall", "lantern"]) + " |", "|---|---|---|---|---|---|---|---|"]
    for m in MODULES:
        lines.append(f"| `{m}` | " + " | ".join(f"{crit[m][c][1]}/{crit[m][c][0]}" if c in crit[m] else "-" for c in ["ladder", "stairs", "bed", "door", "container", "parapet_wall", "lantern"]) + " |")
    mr2 = [m for s in wa for m in s["modules"] if m["module"] == "medium_ruin_2"]
    lines += ["", "### medium_ruin_2 world-space placements (height 8)", "", "| seed | rotation | world BB (x0,y0,z0,x1,y1,z1) | adjacent pieces | overlapping pieces |", "|---|---|---|---|---|"]
    for s in wa:
        for m in s["modules"]:
            if m["module"] == "medium_ruin_2":
                lines.append(f"| {s['seed']} | {m['rotation']} | {tuple(m['bb'])} | {', '.join(m['adjacent_templates']) or '-'} | {len(m['overlapping_pieces'])} |")
    (OUT / "EVIDENCE-TABLES.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    main()
