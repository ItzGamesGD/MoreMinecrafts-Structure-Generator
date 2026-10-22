# Stage 24-H — validation matrix

Statuses: **VERIFIED**, **PARTIAL**, **BLOCKED**, **OWNER DECISION REQUIRED**, **VISUAL PENDING**.
"Simulated player" = mineflayer bot on a real 26.1.2 server; it is not client gameplay.

| # | check | evidence | result | status |
|---|---|---|---|---|
| 1 | Approved NBTs byte-identical to Stage 24-F | `mask/BUILD-MANIFEST.json`, tests, CI `cmp` | 8/8 identical | VERIFIED |
| 2 | Stage 24-G files unchanged | test `test_approved_nbts_and_stage24g_files_unchanged`, CI diff of `stage-24g/` | all 24-G overlays and processor list byte-identical; pool only gains one appended element per entry | VERIFIED |
| 3 | Mask explicit, reproducible, restricted | `MASK.md`, `mask/interior-masks.json`, `tools/stage24h/mask.py`, tests | 9 classes, exact local coordinates; never a stored cell, never exterior or decorative void, never outside the box; rebuild is byte-identical | VERIFIED |
| 4 | Air placement semantics | `INVESTIGATION` in `README.md` (code), live test | air written only at mask cells, after the main template, `protected_blocks` keeps chests/spawners/vaults; cannot reach outside the piece box | VERIFIED |
| 5 | Live placement, buried in deepslate, 8 modules × 4 rotations | `live/live-clearance-report.json` (+ `-small_ruin_2-extra`) | 84 + 9 placements: every mask cell air, stored architecture as the processor model predicts, every other cell untouched; Stage 24-G controls keep the fill in the mask | VERIFIED |
| 6 | Live placement, buried in lava | `live/live-clearance-report-lava-frozen.json` | 8/8 placements: mask cleared at placement; lava returns through decay holes and open shafts after ticks (the main report's unfrozen sauna lava snapshot is superseded by this rerun) | VERIFIED (late fluids: see 15) |
| 7 | Simulated player in buried placements, 8 modules × 4 rotations | `live/gameplay-buried/` | 32/32 module-rotations, all steps (doors, beds incl. sleeping, containers, stairs, ladders, decks, bath) | VERIFIED |
| 8 | 24-seed sweep: layout, rotation, overlaps | `worldgen/h24-summary.json` | 24/24 cities identical to Stage 24-G and 24-F (2,160 pieces), identical to vanilla except the approved heights, 0 overlaps | VERIFIED |
| 9 | Stage 24-G protection still effective | `worldgen/h24-functional-survival.json` | 0 of 5,006 protected cell instances missing (5 replaced by later ore features, as in 24-G) | VERIFIED |
| 10 | Decorative decay unchanged | `worldgen/h24-processor-replay.json` vs 24-G | the same 3,271 block-rot cells at identical positions; no stored-architecture difference 24-G vs 24-H | VERIFIED |
| 11 | Sauna water | `worldgen/fgh-comparison.json` | 387/387 pool cells hold water (waterlogged sculk veins count) | VERIFIED |
| 12 | Seed 24005 medium_ruin_1 buried | `worldgen/h24-summary.json` cases, gallery `buried-medium_ruin_1-*`, `live/city-gameplay` | 189 dripstone blocks in the mask (24-F, 24-G) -> 0, 190/190 mask cells air; in the generated city the bot walks the room, reaches the bed, sleeps, opens the barrel (24-G: all fail) | VERIFIED |
| 13 | Seed 24009 large_ruin_1 dripstone | same | 13 dripstone blocks in the courtyard -> 0 (1,113/1,113 mask cells air) | VERIFIED |
| 14 | Entrance approach outside the box (24005, 24009) | `live/city-gameplay` | the doors open onto solid dripstone **outside** the piece box (city path space) in 24-G and 24-H alike | OWNER DECISION REQUIRED |
| 15 | Seed 24008 small_ruin_1 lava | `FLUIDS.md` | lava spring placed after the city enters through a rotted roof tile: 5 lava cells remain; the bot cannot reach bed/barrel (same as 24-G) | OWNER DECISION REQUIRED (roof role) |
| 16 | Seed 24014 sauna_1 lava | `FLUIDS.md`, `worldgen/h24-terrain-classification.json` | lava column behind the masonry, not in a mask, touches no walkable cell (5 cells in 24-G, 6 in 24-H) | VERIFIED (environmental) |
| 17 | Terrain obstruction across the sweep | terrain classification 24-G vs 24-H | functional obstruction 136 -> 0 cells; remaining 11 fluid-hazard, 4 environmental, 1 cosmetic | VERIFIED |
| 18 | Changes outside the mask | `worldgen/fgh-comparison.json`, `worldgen/reproducibility.json` | 0 architecture differences; 87 natural-terrain + 2 ore cells differ in the piece box ring; repeat runs show cross-chunk generation noise, and at seed 24005 the dripstone features around the cleared room grow differently (1,532 natural blocks within 12 blocks, reproducible) | VERIFIED — reported as a side effect |
| 19 | Vanilla sculk in cleared rooms | `worldgen/h24-issues.json` | 6,350 sculk veins, 204 sensors, 42 shriekers, 38 catalysts grow into cleared cells (vanilla deep-dark decoration after the city) | VERIFIED (vanilla behaviour) |
| 20 | Tower deck headroom above the piece box | buried-gameplay investigation | the space above the large watchtower deck is outside the box; air in 192/192 cells across the sweep, cannot be cleared without a taller box | VERIFIED limitation |
| 21 | Visual evidence | `gallery/` | 4 cases × before/after × full + cutaway, 16 mask visualisations; headless renders | VERIFIED as simulated evidence |
| 22 | Minecraft-client verification | — | no rendering client in this environment | VISUAL PENDING |
