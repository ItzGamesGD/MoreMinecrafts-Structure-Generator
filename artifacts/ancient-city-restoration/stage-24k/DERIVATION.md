# Stage 24-K — derived data rebuilt for the two new towers

The unchanged Stage 24-G, 24-H and 24-I builders ran on `final-candidates/` (`tools/stage24k/build.py`; the path
constants of those tools are rebound by `tools/stage24k/rebase.py`, the tools are not edited). Result against the
Stage 24-I derived data:

| module | protected cells (24-I → 24-K) | clearance-mask cells | roof cells | derived data |
|---|---|---|---|---|
| large_ruin_1 | 3 → 3 | 1113 → 1113 | 0 → 0 | **identical** |
| medium_ruin_1 | 3 → 3 | 190 → 190 | 64 → 64 | **identical** |
| medium_ruin_2 | 96 → 96 | 565 → 565 | 78 → 78 | **identical** |
| small_ruin_1 | 3 → 3 | 81 → 81 | 29 → 29 | **identical** |
| small_ruin_2 | 3 → 3 | 32 → 32 | 11 → 11 | **identical** |
| sauna_1 | 32 → 32 | 1768 → 1768 | 0 → 0 | **identical** |
| large_pillar_1 | 39 → 53 | 40 → 40 | 0 → 0 | rebuilt (changes below) |
| medium_pillar_1 | 38 → 48 | 10 → 10 | 0 → 0 | rebuilt (changes below) |

Production pack files that differ from the Stage 24-I pack (everything else is byte-identical, incl. the pool file):

* `data/minecraft/structure/ancient_city/structures/large_pillar_1.nbt`
* `data/minecraft/structure/ancient_city/structures/medium_pillar_1.nbt`
* `data/moreminecrafts/structure/ancient_city/protection/large_pillar_1.nbt`
* `data/moreminecrafts/structure/ancient_city/protection/medium_pillar_1.nbt`
* 26 files identical

## large_pillar_1

* Stage 24-G protected cells: 39 → 53 — removed 6 {'railing': 6}, added 20 {'railing': 16, 'walk_floor': 4}; role changes of surviving cells: 0.
* Stage 24-H clearance mask: 0 cells added, 0 removed (cell set identical; only the stored/exterior class counts move because the new corbel cells are now stored).
* Stage 24-I roof cells: 0 → 0.

Removed protected cells:

* `[1, 14, 3] railing minecraft:deepslate`
* `[2, 14, 4] railing minecraft:deepslate`
* `[3, 14, 1] railing minecraft:deepslate`
* `[3, 14, 4] railing minecraft:deepslate`
* `[4, 14, 2] railing minecraft:deepslate`
* `[4, 14, 3] railing minecraft:deepslate`

Added protected cells:

* `[0, 14, 1] railing minecraft:polished_deepslate_wall`
* `[0, 14, 2] railing minecraft:polished_deepslate_wall`
* `[0, 14, 3] railing minecraft:polished_deepslate_wall`
* `[0, 14, 4] railing minecraft:polished_deepslate_wall`
* `[1, 13, 1] walk_floor minecraft:polished_deepslate`
* `[1, 13, 4] walk_floor minecraft:polished_deepslate`
* `[1, 14, 0] railing minecraft:polished_deepslate_wall`
* `[1, 14, 5] railing minecraft:polished_deepslate_wall`
* `[2, 14, 0] railing minecraft:polished_deepslate_wall`
* `[2, 14, 5] railing minecraft:polished_deepslate_wall`
* `[3, 14, 0] railing minecraft:polished_deepslate_wall`
* `[3, 14, 5] railing minecraft:polished_deepslate_wall`
* `[4, 13, 1] walk_floor minecraft:polished_deepslate`
* `[4, 13, 4] walk_floor minecraft:polished_deepslate`
* `[4, 14, 0] railing minecraft:polished_deepslate_wall`
* `[4, 14, 5] railing minecraft:polished_deepslate_wall`
* `[5, 14, 1] railing minecraft:polished_deepslate_wall`
* `[5, 14, 2] railing minecraft:polished_deepslate_wall`
* `[5, 14, 3] railing minecraft:polished_deepslate_wall`
* `[5, 14, 4] railing minecraft:polished_deepslate_wall`

## medium_pillar_1

* Stage 24-G protected cells: 38 → 48 — removed 13 {'railing': 13}, added 23 {'railing': 22, 'walk_floor': 1}; role changes of surviving cells: 0.
* Stage 24-H clearance mask: 0 cells added, 0 removed (cell set identical; only the stored/exterior class counts move because the new corbel cells are now stored).
* Stage 24-I roof cells: 0 → 0.

Removed protected cells:

* `[1, 9, 2] railing minecraft:polished_deepslate_wall`
* `[1, 9, 3] railing minecraft:polished_deepslate_wall`
* `[1, 9, 4] railing minecraft:polished_deepslate_wall`
* `[1, 9, 5] railing minecraft:polished_deepslate_wall`
* `[2, 9, 1] railing minecraft:polished_deepslate_wall`
* `[2, 9, 6] railing minecraft:polished_deepslate_wall`
* `[3, 9, 1] railing minecraft:polished_deepslate_wall`
* `[3, 9, 6] railing minecraft:polished_deepslate_wall`
* `[4, 9, 1] railing minecraft:polished_deepslate_wall`
* `[4, 9, 6] railing minecraft:polished_deepslate_wall`
* `[5, 9, 2] railing minecraft:polished_deepslate_wall`
* `[5, 9, 4] railing minecraft:polished_deepslate_wall`
* `[5, 9, 5] railing minecraft:polished_deepslate_wall`

Added protected cells:

* `[0, 9, 1] railing minecraft:polished_deepslate_wall`
* `[0, 9, 2] railing minecraft:polished_deepslate_wall`
* `[0, 9, 3] railing minecraft:polished_deepslate_wall`
* `[0, 9, 4] railing minecraft:polished_deepslate_wall`
* `[0, 9, 5] railing minecraft:polished_deepslate_wall`
* `[0, 9, 6] railing minecraft:polished_deepslate_wall`
* `[1, 9, 0] railing minecraft:polished_deepslate_wall`
* `[1, 9, 7] railing minecraft:polished_deepslate_wall`
* `[2, 9, 0] railing minecraft:polished_deepslate_wall`
* `[2, 9, 7] railing minecraft:polished_deepslate_wall`
* `[3, 8, 1] walk_floor minecraft:deepslate_tiles`
* `[3, 9, 0] railing minecraft:polished_deepslate_wall`
* `[3, 9, 7] railing minecraft:polished_deepslate_wall`
* `[4, 9, 0] railing minecraft:polished_deepslate_wall`
* `[4, 9, 7] railing minecraft:polished_deepslate_wall`
* `[5, 9, 0] railing minecraft:polished_deepslate_wall`
* `[5, 9, 7] railing minecraft:polished_deepslate_wall`
* `[6, 9, 1] railing minecraft:polished_deepslate_wall`
* `[6, 9, 2] railing minecraft:polished_deepslate_wall`
* `[6, 9, 3] railing minecraft:polished_deepslate_wall`
* `[6, 9, 4] railing minecraft:polished_deepslate_wall`
* `[6, 9, 5] railing minecraft:polished_deepslate_wall`
* `[6, 9, 6] railing minecraft:polished_deepslate_wall`

The ladder and ladder-attach cells of both towers keep their Stage 24-G protection (test `test_ladder_protection_is_preserved`).
Railing and deck-floor cells of the new decks are protected by role (`railing`, `walk_floor`); the wall and corbel-stair
blocks of the new decks are not in `#minecraft:ancient_city_replaceable`, so `block_rot` cannot drop them regardless — the
overlay only restores the rottable protected cells.
