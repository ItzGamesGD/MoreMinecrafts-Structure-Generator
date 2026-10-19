#!/usr/bin/env python3
"""Condense N7-A2 spike runs (collision_lab.py --fabric-project with --refine/--fixture/--oracle) into one comparable JSON + Markdown table.

Run directories are named ARM_SITE_ORDER (e.g. C_s173a_rowmajor_rev). The reference start signature of a site is taken from arm A
(observe, both hooks cancel nothing); every run is compared with it.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

SITES = {"s173a": (173, [-19, 15]), "s173b": (173, [-18, 36]), "s42a": (42, [4, 13]), "s42b": (42, [6, -19])}


def row(path: Path) -> dict:
    n = json.loads((path / "lab.json").read_text())
    a = n.get("after_ticks") or {}
    sr = n.get("spike_report") or {}
    g, m = sr.get("geode", {}), sr.get("monster_room", {})
    au = n.get("audit", {})
    arm, site, _order = path.name.split("_", 2)
    mismatched = (a.get("expected", 0) - a.get("matched", 0)) if a else None
    intrusions = sum((a.get("interior_intrusions") or {}).values()) if a else None
    return {
        "run": path.name, "arm": arm, "site": site, "seed": n["seed"], "chunk": n["chunk"], "order": n["order"],
        "guard_mode": n.get("guard_mode"), "features": n.get("features"), "fixture": n.get("fixture", "none"),
        "refine": n.get("refine", "off"), "oracle": n.get("oracle", "off"),
        "generated": n.get("generated"), "pieces": a.get("pieces"), "mismatched_blocks": mismatched,
        "by_feature": a.get("by_feature") or {}, "foreign_blocks_in_template_air": intrusions,
        "trial_spawners": a.get("trial_spawners"), "start_signature": n.get("start_signature"),
        "geode": {k: g.get(k) for k in ("attempts", "fast_path", "clear", "collisions", "unavailable", "cancelled", "would_cancel", "no_write")},
        "monster_room": {k: m.get(k) for k in ("attempts", "fast_path", "clear", "collisions", "unavailable", "cancelled", "would_cancel", "no_write",
                                               "oracle_non_air_write", "oracle_no_write", "oracle_unknown")},
        "confusion": m.get("confusion"),
        "probe": sr.get("probe"),
        "be_in_piece_boxes": au.get("block_entities_inside_piece_boxes"),
        "gap_spawners": (au.get("natural_spawners_in_bbox_gaps") or []),
        "elapsed_s": n.get("elapsed_s"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path, help="directory holding one subdirectory per run")
    p.add_argument("--out-json", type=Path, required=True)
    p.add_argument("--out-md", type=Path)
    a = p.parse_args()
    rows = [row(d) for d in sorted(a.root.iterdir()) if (d / "lab.json").exists() and d.name.count("_") >= 2]
    # Per-site references come from arm A (observe, nothing cancelled), rowmajor. Trial-spawner counts differ by site (3 at seed 173,
    # 12 at seed 42 (6,-19)), so the expected count is taken from the reference run, never hard-coded.
    ref_run = {r["site"]: r for r in rows if r["arm"] == "A" and r["order"] == "rowmajor"}
    for r in rows:
        ref = ref_run.get(r["site"])
        r["starts_match_reference"] = ref is not None and r["start_signature"] == ref["start_signature"]
        r["pieces_expected"] = ref is not None and r["pieces"] == ref["pieces"]
        r["spawners_expected"] = ref is not None and r["trial_spawners"] == ref["trial_spawners"] and r["trial_spawners"][0] == r["trial_spawners"][1]
        r["corrupted"] = bool(r["mismatched_blocks"])
    a.out_json.write_text(json.dumps(rows, indent=1) + "\n")
    if a.out_md:
        lines = ["| arm | site | order | mismatch | foreign in air | geode c/w/x | monster c/w/x | no-write | clear | oracle nonair/noW/unk | starts ok | pieces 21 | spawners 3/3 |",
                 "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            g, m = r["geode"], r["monster_room"]
            lines.append(f"| {r['arm']} | {r['site']} ({r['chunk'][0]},{r['chunk'][1]}) | {r['order']} | {r['mismatched_blocks']} | {r['foreign_blocks_in_template_air']} | "
                         f"{g['collisions']}/{g['would_cancel']}/{g['cancelled']} | {m['collisions']}/{m['would_cancel']}/{m['cancelled']} | {m['no_write']} | {m['clear']} | "
                         f"{m['oracle_non_air_write']}/{m['oracle_no_write']}/{m['oracle_unknown']} | {r['starts_match_reference']} | {r['pieces_expected']} | {r['spawners_expected']} |")
        a.out_md.write_text("\n".join(lines) + "\n")
    agg = defaultdict(lambda: {"runs": 0, "corrupted": 0, "cancelled_geode": 0, "cancelled_monster": 0})
    for r in rows:
        k = (r["arm"], r["site"])
        agg[k]["runs"] += 1
        agg[k]["corrupted"] += int(r["corrupted"])
        agg[k]["cancelled_geode"] += r["geode"]["cancelled"] or 0
        agg[k]["cancelled_monster"] += r["monster_room"]["cancelled"] or 0
    for (arm, site), v in sorted(agg.items()):
        print(f"{arm} {site:6} corrupted {v['corrupted']}/{v['runs']}  cancelled geode={v['cancelled_geode']} monster={v['cancelled_monster']}")


if __name__ == "__main__":
    main()
