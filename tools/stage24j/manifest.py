"""Dimensional manifest of the Stage 24-J watchtower candidates (and the approved towers)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import blocks_of, load_nbt  # noqa: E402
from tools.stage24j.designs import DESIGNS, D24F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24J = ROOT / "artifacts/ancient-city-restoration/stage-24j"


def main():
    checks = json.loads((D24J / "static-checks.json").read_text())
    out = {}
    for m, fs in DESIGNS.items():
        out[m] = {}
        for f in fs:
            v = f()
            path = D24F / m / "restored.nbt" if v.variant == "current" else D24J / "proposals" / m / v.variant / "candidate.nbt"
            r = load_nbt(path)
            b = {p: s for p, (s, _) in blocks_of(r).items() if not s.startswith(("minecraft:air", "minecraft:jigsaw"))}
            size = [int(s) for s in r["size"]]
            c = checks[m][v.variant]
            dy = v.meta["deck_y"]
            xs = [x for x, z in v.meta["deck"]]
            zs = [z for x, z in v.meta["deck"]]
            out[m][v.variant] = {
                "title": v.title, "file": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "template_size_xyz": size, "size_change": [a - b for a, b in zip(size, checks[m]["current"]["dimensions"])],
                "highest_block_y": max(p[1] for p in b), "footprint_cells_at_top": len({(p[0], p[2]) for p in b if p[1] >= dy - 1}),
                "deck_feet_y": dy, "deck_standable_cells": c["deck"]["reachable_from_ladder"],
                "deck_extent_xz": [min(xs), min(zs), max(xs), max(zs)],
                "eye_height_above_template_base": round(dy + 1.62, 2),
                "headroom_cells_above_template": c["deck"]["headroom_cells_above_template"],
                "ladder": c["ladder"], "fall_protection": c["fall_protection"]["sides"],
                "blocks_stored": len(b), "changed_cells_vs_approved": c["changed_cells"],
                "decay_eligible_blocks": c["decay_eligible_blocks"], "bounding_box_and_jigsaws": "unchanged" if c["size_unchanged"] and c["jigsaws_and_block_entities_identical"] else "CHANGED",
                "notes": v.notes,
            }
    (D24J / "DIMENSIONS-MANIFEST.json").write_text(json.dumps(out, indent=1) + "\n")
    for m in out:
        for k, r in out[m].items():
            print(m, k, r["template_size_xyz"], "top y", r["highest_block_y"], "deck y", r["deck_feet_y"], "cells", r["deck_standable_cells"], "changed", r["changed_cells_vs_approved"])


if __name__ == "__main__":
    main()
