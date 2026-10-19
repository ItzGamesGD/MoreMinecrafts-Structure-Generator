# Defect register (PR #10 baseline → Stage 24-C)

| id | sev | module | symptom (how reproduced) | root cause | status |
|---|---|---|---|---|---|
| D1 | P2 | 7 modules (not large_pillar_1) | after `place template`, 15 soul lanterns are `air` (placement report `placement-report-pr10-baseline.json`) | `hanging=false` with nothing below | FIXED, test `test_lanterns_have_a_floor_or_ceiling` |
| D2a | P1 | large_pillar_1 | ladder cells y=1,2 are air after placement; bot cannot climb (`max_y` −58.75) | `facing=east` needs a block at x=1 = entrance tunnel | FIXED, `test_ladders_are_mounted_on_a_full_block` |
| D2b | P1 | large_pillar_1 | after D2a the bot stalls 1 block under the deck (feet 13.15) | ladder ended at y=12, deck surface y=14 | FIXED, `test_large_pillar_1_ladder_reaches_deck_surface` |
| D3 | P1 | small_ruin_2 | `bed0_sleep` → server message "This bed is obstructed" | beds embedded in wall row z=3 beneath solid wall | FIXED, `test_beds_are_not_obstructed` |
| D4 | P1 | medium_ruin_2 | upper floor unreachable: bot stops at x=4.7 on step 1; pathing to upper bed/barrel fails | 2nd/4th steps lacked 1.8-block headroom (roof tile (5,4,5), wall (7,6,5)), plus step-over clearance at (4,4,5) | FIXED, `test_medium_ruin_2_stair_run_has_two_cells_of_headroom` |
| D5a | P1 | medium_pillar_1 | 12/22 deck-edge probes fall 8 blocks | no parapet at y=9 | FIXED, `test_medium_pillar_1_deck_has_a_complete_parapet` |
| D5b | P2 | medium_pillar_1 | with tile walls 27/630 parapet segments rotted away in real cities | walls in `#ancient_city_replaceable` | FIXED (polished_deepslate_wall), `…survives_vanilla_degradation` |
| O1 | P3 | all | vanilla `block_rot` 5 %/lantern rule 5 % remove blocks | vanilla processor | OPEN (by design of vanilla); measured in `EVIDENCE-TABLES.md` |
| O2 | P3 | medium_ruin_1 | seed 24005 piece filled with dripstone | terrain adaptation | OPEN, vanilla behaviour |
| O3 | P3 | houses | flat-roof read, low differentiation | design | OWNER decision (not touched) |

Non-defects investigated: `medium_pillar_1` east ladder works (3.6 s ground→deck) — **not relocated**. Sauna opening at (11,2,33) works functionally
(reception → 3 chests and both basins reached on foot) — visual approval still the owner's. Pathfinder failures through open doors / down stairs were
bot-controller limits (manual walking succeeds) and are reported as such, not as building defects.
