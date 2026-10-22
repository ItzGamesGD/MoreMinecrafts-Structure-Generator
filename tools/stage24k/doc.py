"""Write stage-24k/DERIVATION.md from DERIVATION-DIFF.json: what the two new towers changed in the derived data."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / "artifacts/ancient-city-restoration/stage-24k"


def by_role(lines):
    return dict(Counter(l.split("] ")[1].split(" ")[0] for l in lines))


def main():
    d = json.loads((K / "DERIVATION-DIFF.json").read_text())
    towers = ("large_pillar_1", "medium_pillar_1")
    o = ["# Stage 24-K — derived data rebuilt for the two new towers", "",
         "The unchanged Stage 24-G, 24-H and 24-I builders ran on `final-candidates/` (`tools/stage24k/build.py`; the path",
         "constants of those tools are rebound by `tools/stage24k/rebase.py`, the tools are not edited). Result against the",
         "Stage 24-I derived data:", "",
         "| module | protected cells (24-I → 24-K) | clearance-mask cells | roof cells | derived data |", "|---|---|---|---|---|"]
    for m in MODULES:
        r = d[m]
        o.append(f"| {m} | {r['protected_cells']['old']} → {r['protected_cells']['new']} | {r['mask']['old']} → {r['mask']['new']}"
                 f" | {r['roof']['old']} → {r['roof']['new']} | {'**identical**' if r['protected_cells']['identical'] and r['mask']['identical'] and r['roof']['identical'] else 'rebuilt (changes below)'} |")
    o += ["", "Production pack files that differ from the Stage 24-I pack (everything else is byte-identical, incl. the pool file):", ""]
    o += [f"* `{f}`" for f in d["_pack_files_vs_stage24i"]] + [f"* {d['_pack_files_identical']} files identical", ""]
    for m in towers:
        p = d[m]["protected_cells"]
        o += [f"## {m}", "",
              f"* Stage 24-G protected cells: {p['old']} → {p['new']} — removed {len(p['removed'])} {by_role(p['removed'])}, added {len(p['added'])} {by_role(p['added'])}; "
              f"role changes of surviving cells: {len(p['role_changed'])}.",
              f"* Stage 24-H clearance mask: {len(d[m]['mask']['added'])} cells added, {len(d[m]['mask']['removed'])} removed "
              f"({'cell set identical' if not d[m]['mask']['added'] and not d[m]['mask']['removed'] else 'CHANGED'}; only the stored/exterior class counts move because the new corbel cells are now stored).",
              f"* Stage 24-I roof cells: {d[m]['roof']['old']} → {d[m]['roof']['new']}.", "",
              "Removed protected cells:", ""] + [f"* `{x}`" for x in p["removed"]] + ["", "Added protected cells:", ""] + [f"* `{x}`" for x in p["added"]] + [""]
    o += ["The ladder and ladder-attach cells of both towers keep their Stage 24-G protection (test `test_ladder_protection_is_preserved`).",
          "Railing and deck-floor cells of the new decks are protected by role (`railing`, `walk_floor`); the wall and corbel-stair",
          "blocks of the new decks are not in `#minecraft:ancient_city_replaceable`, so `block_rot` cannot drop them regardless — the",
          "overlay only restores the rottable protected cells."]
    (K / "DERIVATION.md").write_text("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
