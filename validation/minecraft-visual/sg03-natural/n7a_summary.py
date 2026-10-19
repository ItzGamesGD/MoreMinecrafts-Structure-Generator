#!/usr/bin/env python3
"""Condense N7-A spike runs (collision_lab.py --fabric-project) into one comparable table + JSON."""
import argparse
import json
from pathlib import Path


def row(path: Path) -> dict:
    n = json.loads((path / "lab.json").read_text())
    a = n.get("after_ticks") or {}
    sr = n.get("spike_report") or {}
    g, m = sr.get("geode", {}), sr.get("monster_room", {})
    au = n.get("audit", {})
    log = " ".join(n.get("mixin_log", []))
    return {
        "run": path.name, "seed": n["seed"], "chunk": n["chunk"], "order": n["order"], "mode": n.get("guard_mode"),
        "fault": n.get("fault"),
        "hooks_applied": "GeodeFeature.place applied=true MonsterRoomFeature.place applied=true" in log,
        "tag_resolved": "protected structures resolved" in log,
        "pieces": a.get("pieces"), "mismatched_blocks": (a.get("expected", 0) - a.get("matched", 0)) if a else None,
        "by_feature": a.get("by_feature"), "foreign_blocks_in_template_air": sum((a.get("interior_intrusions") or {}).values()) if a else None,
        "trial_spawner_block_entity": a.get("trial_spawners"),
        "geode": {k: g.get(k) for k in ("attempts", "fast_path", "collisions", "unavailable", "cancelled", "would_cancel")},
        "monster_room": {k: m.get(k) for k in ("attempts", "fast_path", "collisions", "unavailable", "cancelled", "would_cancel")},
        "be_in_piece_boxes": au.get("block_entities_inside_piece_boxes"),
        "be_in_bbox_gaps": au.get("block_entities_in_bbox_but_outside_all_pieces"),
        "mob_spawners_outside_bbox": (au.get("block_entities_outside_bbox") or {}).get("minecraft:mob_spawner", 0),
        "amethyst": au.get("amethyst_blocks"),
        "elapsed_s": n.get("elapsed_s"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("dirs", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rows = [row(d) for d in a.dirs if (d / "lab.json").exists()]
    a.out.write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(f"{r['run']:4} s{r['seed']} {tuple(r['chunk'])} {r['order']:12} {str(r['mode']):8} hooks={r['hooks_applied']} mismatch={r['mismatched_blocks']} "
              f"foreign={r['foreign_blocks_in_template_air']} geode(c/w/x)={r['geode']['collisions']}/{r['geode']['would_cancel']}/{r['geode']['cancelled']} "
              f"room={r['monster_room']['collisions']}/{r['monster_room']['would_cancel']}/{r['monster_room']['cancelled']} unavail={r['geode']['unavailable']}+{r['monster_room']['unavailable']} "
              f"piece_spawners={ (r['be_in_piece_boxes'] or {}).get('minecraft:mob_spawner',0)} gap_spawners={(r['be_in_bbox_gaps'] or {}).get('minecraft:mob_spawner',0)}")


if __name__ == "__main__":
    main()
