"""Write stage-24g/PROTECTION-POLICY.md from the role inventory, so the document always matches the implementation."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.build import D24G, D24F  # noqa: E402

HEAD = """# Stage 24-G — Functional protection policy (exact)

Owner-approved rule: protect what a block **does**, never its block type. A block is protected only for one of the roles
below, derived geometrically from the Stage 24-F template by `tools/stage24g/roles.py`; everything else keeps vanilla
decay (`block_rot` 5 %, cracking 30 %, soul lanterns 5 %).

| role | protected cell | why it matters (26.1.2 code) |
|---|---|---|
| `door` | both halves of every door | the entrance itself |
| `door_support` | the block under each lower door half | `DoorBlock.canSurvive`: lower half needs a face-sturdy block below |
| `ladder` | every ladder | access to decks and upper levels |
| `ladder_attach` | the block a ladder hangs on (`pos - facing`) | `LadderBlock.canSurvive` |
| `walk_floor` | the floor under every walkable cell that is reachable from the ground floor and where a hole would fall **2 or more** blocks (decks, upper storeys, landings) | a hole there is a fall, not decay |
| `railing` | the foot-level edge block next to a reachable walkable cell when walking out through that edge would fall **2 or more** blocks | keeping the innermost foot-level barrier closes the walk-out whatever happens behind it; a wall with masonry above it is protected only at foot level, the masonry above keeps decaying |

Not protected (vanilla decay kept): soul lanterns, ground-floor floors (a hole drops one block onto the ground), wall
masonry above foot level, pillars, roofs, trim, decorative walls/stairs that are not an edge barrier, furniture tops.
Reachability is a breadth-first walk from every ground-floor standing cell (step up/down 1, drop up to 3, ladders),
unspecified template cells counted as open air (worst case).

Only protected cells that the main pass **can** lose are written by the overlay: tagged
(`#ancient_city_replaceable`) blocks, and the jigsaw cells under doors that resolve to `structure_void` (supplied with
the most common neighbouring floor block). Untagged protected blocks (doors, ladders, polished/chiseled deepslate,
deepslate tile stairs, polished basalt, polished deepslate walls) are never dropped by any processor and need nothing.

## Per module
"""


def main():
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    man = json.loads((D24G / "protection/BUILD-MANIFEST.json").read_text())
    out = [HEAD]
    out.append("| module | protected cells (by role) | of which tagged (overlay) | supplied door support | rottable cells left to vanilla decay | pool entry |")
    out.append("|---|---|---|---|---|---|")
    for m in MODULES:
        b = blocks_of(load_nbt(D24F / m / "restored.nbt"))
        v = inv[m]
        roles = Counter(r for e in v["protected"] for r in e["roles"])
        fills = [e for e in v["overlay"] if "note" in e]
        rottable = sum(1 for s, _ in b.values() if P.name(s) in P.ANCIENT_CITY_REPLACEABLE)
        prot_rot = sum(1 for e in v["protected"] if e["rottable"])
        out.append(f"| {m} | {len(v['protected'])} ({', '.join(f'{k} {n}' for k, n in sorted(roles.items()))}) | {len(v['overlay']) - len(fills)} | "
                   f"{', '.join(str(e['pos']) + ' ' + e['state'].replace('minecraft:', '') for e in fills) or '—'} | "
                   f"{rottable - prot_rot} of {rottable} ({100 * (rottable - prot_rot) / rottable:.1f} %) | "
                   f"{'list [template, overlay]' if m in man['wrapped_modules'] else 'unchanged single element'} |")
    out.append("")
    out.append("Full cell list with the reason for every protected cell: `protection/protected-cells.json`.")
    out.append("")
    out.append("## Mechanism")
    out.append("""
Each wrapped entry of `minecraft:ancient_city/structures` becomes a `minecraft:list_pool_element`:

```
[ <the unchanged Stage 24-F single_pool_element, minecraft:ancient_city_generic_degradation>,
  { "location": "moreminecrafts:ancient_city/protection/<module>",
    "processors": "moreminecrafts:ancient_city_functional_protection" } ]
```

* `ListPoolElement` (26.1.2): jigsaws come from the first element only, the bounding box is the union of the elements'
  boxes (identical sizes -> identical box), elements are placed in order at the same position and rotation. Jigsaw
  assembly, piece placement and rotation are therefore unchanged (verified: 24/24 cities identical to vanilla).
  Vanilla already uses list elements in this very pool (`camp_1..3`).
* `moreminecrafts:ancient_city_functional_protection` = `ancient_city_generic_degradation` without the `block_rot`
  entry (same rule list, same `protected_blocks`). Because `RuleProcessor` seeds its random from the world position, the
  overlay cracks exactly the bricks the main pass cracked; it only puts back what `block_rot` dropped.
* The overlay template has the module's size and DataVersion and contains only the protected cells listed above: no
  jigsaws, no block entities, no entities. The eight approved structure NBTs are byte-identical to Stage 24-F.
* Every other pool entry, every vanilla processor list and tag, and every other Ancient City structure are untouched.
  `large_ruin_1` and `small_ruin_2` keep their plain pool entry: none of their protected cells can be dropped
  (`StructureTemplate.placeInWorld` also refuses an empty template, so an empty overlay would fail placement).
""")
    (D24G / "PROTECTION-POLICY.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
