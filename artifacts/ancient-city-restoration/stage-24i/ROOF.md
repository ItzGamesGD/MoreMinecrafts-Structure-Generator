# Stage 24-I — Functional roof protection (Part A)

## Rule (`tools/stage24i/roof.py`)

A stored template cell is a protected roof cell when **all** hold:

1. its block is in `#minecraft:ancient_city_replaceable` (so `block_rot` can drop it) and the Stage 24-G roles do not already protect it;
2. the cell directly below is a Stage 24-H `room_interior` cell (an enclosed, roofed, usable room);
3. the cell directly above is open: outside the template, or a Stage 24-H `exterior` / `decorative_void` cell.

Walls, floors, thick-roof lower layers, courtyards and every other rottable cell are left to vanilla decay. Nothing is
added to the envelope by default.

## Inventory (verified, not the estimate taken as a quota)

| module | Stage 24-H estimate | verified roof cells | decay-eligible cells before → after | share still decaying |
|---|---|---|---|---|
| medium_ruin_1 | 64 | **64** | 285 → 221 | 77.5 % |
| medium_ruin_2 | 78 | **78** | 509 → 431 | 72.0 % |
| small_ruin_1 | 29 | **29** | 165 → 136 | 82.4 % |
| small_ruin_2 | 11 | **11** | 108 → 97 | 89.8 % |
| large_ruin_1 | – | 0 (tile-stair roof, not rottable) | unchanged | |
| sauna_1, large_pillar_1, medium_pillar_1 | – | 0 (no enclosed roofed room under a single rottable layer) | unchanged | |

Every cell with its state: `roof/roof-cells.json`. The seed-24008 entry cell `small_ruin_1 (4,4,4)` is in the set.
Visualisation: `gallery/roof-<module>.jpg` (orange glass = protected roof cell; headless render of the template).

## Generation integration (`tools/stage24i/build.py`)

Same mechanism as Stage 24-G: one more element in the restored `list_pool_element`, inserted **before** the Stage 24-H
clearance element:

```json
{ "element_type": "minecraft:single_pool_element", "location": "moreminecrafts:ancient_city/roof/<module>",
  "processors": "moreminecrafts:ancient_city_functional_protection", "projection": "rigid" }
```

The roof template has the module's size and DataVersion and stores only the roof cells with their Stage 24-F states;
the processor list is the Stage 24-G one (vanilla degradation without `block_rot`), so a roof cell keeps its vanilla
cracking but is never dropped. Box, jigsaws and pool weights are unchanged (`tests/test_stage24i_roof.py`).

## Results

| check | result |
|---|---|
| live `/place jigsaw`, buried, 8 modules × 4 rotations (86 placements) | 0 violations; **every roof cell present in every Stage 24-I placement** (would-rot cells 94 across the placements, all restored) |
| live Stage 24-H control placements (same procedure, no roof element) | medium_ruin_1 3, medium_ruin_2 2, small_ruin_2 1, small_ruin_1 2 roof cells MISSING — the unprotected baseline |
| 24-seed sweep, roof continuity | **4,170 / 4,170** roof cells present (cracked/sculk-covered counted as present), 0 missing |
| 24-seed sweep, `block_rot` losses | **3,271 → 3,067 (−204, −6.2 %)**: medium_ruin_1 −78, medium_ruin_2 −77, small_ruin_1 −29, small_ruin_2 −20 |
| decay outside the roof cells, block-for-block vs Stage 24-H | identical: 0 architecture differences outside the roof cells in 2,160 pieces (`worldgen/hi-comparison.json`); the only differences are sculk spread, fluid flow timing and 3 natural-terrain cells (generation run-to-run noise documented in Stage 24-H) |
| replay of the processors against the sweep | 3,067 `block_rot` losses, every one predicted by the position-seeded processor model; the 5 REPLACED protected cells are the same 5 as in Stage 24-H (pre-existing) |

## Seed 24008 (lava)

| | Stage 24-H | Stage 24-I |
|---|---|---|
| lava cells in the small_ruin_1 room (after the normal generation sequence and the sweep's fluid ticks) | 5 | **0** |
| lava cells outside the template next to the house | 13 | 9 |

The spring at (596,-39,1278) still flows down the outside of the house and rests on the roof surface and in the column
beside the wall (template cells (7,0..4,3), (5..6,5,3), (5,6,3) — all outside the template). Roof protection closes the
entry point; it does not remove the lava. Images: `gallery/roof-lava-small_ruin_1-*.jpg`.

**No universal lava immunity is claimed.** Fluids can still enter through doorways, wall decay holes and open
courtyards, and springs are decorated after the city. Remaining decay openings next to interiors are listed in
`roof/remaining-decay-openings.json` (walls beside an interior, floors below one, thick-roof layers).

## Aesthetic

The protected cells are a single roof layer of four houses; walls, floors and every other surface keep vanilla decay
(72–90 % of each module's decay-eligible cells still decay). Cracking still applies to roof cells. No shape or material
changed.
