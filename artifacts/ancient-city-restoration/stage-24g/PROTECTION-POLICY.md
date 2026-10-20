# Stage 24-G — Functional protection policy (exact)

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

| module | protected cells (by role) | of which tagged (overlay) | supplied door support | rottable cells left to vanilla decay | pool entry |
|---|---|---|---|---|---|
| large_ruin_1 | 3 (door 2, door_support 1) | 0 | — | 762 of 762 (100.0 %) | unchanged single element |
| medium_ruin_1 | 3 (door 2, door_support 1) | 0 | [0, 0, 6] deepslate_bricks | 285 of 285 (100.0 %) | list [template, overlay] |
| medium_ruin_2 | 96 (door 2, door_support 1, railing 33, walk_floor 60) | 90 | — | 509 of 599 (85.0 %) | list [template, overlay] |
| small_ruin_1 | 3 (door 2, door_support 1) | 0 | [0, 0, 3] deepslate_bricks | 165 of 165 (100.0 %) | list [template, overlay] |
| small_ruin_2 | 3 (door 2, door_support 1) | 0 | — | 108 of 108 (100.0 %) | unchanged single element |
| sauna_1 | 32 (railing 20, walk_floor 13) | 25 | — | 1649 of 1674 (98.5 %) | list [template, overlay] |
| large_pillar_1 | 39 (ladder 13, ladder_attach 13, railing 11, walk_floor 3) | 9 | — | 133 of 142 (93.7 %) | list [template, overlay] |
| medium_pillar_1 | 38 (ladder 8, ladder_attach 8, railing 15, walk_floor 7) | 17 | — | 179 of 196 (91.3 %) | list [template, overlay] |

Full cell list with the reason for every protected cell: `protection/protected-cells.json`.

## Mechanism

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
