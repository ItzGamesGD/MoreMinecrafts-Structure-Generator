# Stage 24-K — validation matrix

Statuses: **VERIFIED**, **OPEN ITEM** (reported, not altered), **VISUAL PENDING**. "Bot" = mineflayer simulated player on a real
26.1.2 server — scripted checks, **not Minecraft-client gameplay**.

| # | requested check | evidence | result | status |
|---|---|---|---|---|
| 1 | Exact NBT comparison against the approved Option A candidates | tests, CI `cmp`, `SOURCES.json` | both towers byte-identical to `stage-24j/proposals/*/A/candidate.nbt`; six others byte-identical to Stage 24-F; production pack templates equal the final candidates | VERIFIED |
| 2 | Four-rotation placement on 26.1.2 | `live/towers/live-report.json`, `live/live-pool-report.json` | exact `/place template`: 8/8, 0 mismatching cells; real-processor `/place jigsaw`, buried: 71 placements, all 8 modules × 4 rotations, 0 violations, every roof cell present | VERIFIED |
| 3 | Ladder, deck and railing safety | `static-checks.json`, `worldgen/ik-comparison.json` | ladder continuous and backed, all deck cells reachable, 0 open drops, valid states; in 67 generated towers 0 ladder cells and 0 of 1,282 railing cells missing | VERIFIED |
| 4 | Scripted traversal to all observation positions | `live/towers/bot-*.json`, `live/gameplay-buried/` | outside → ladder → climb → every deck cell (15 / 29) → every deck edge: large 52/52, medium 78/78 steps in 4 rotations; buried placements with real processors 32/32 | VERIFIED (bot) |
| 5 | 24-seed world-generation regression | `worldgen/` | 24 seeds, 2,160 pieces | VERIFIED |
| 6 | Layout, bounding box, jigsaw comparison | `worldgen/ik-comparison.json`, `k24-analysis.json` | positions/rotations/boxes of every piece identical to Stage 24-I, 0 overlaps, boxes = model = vanilla except the approved heights (40, as before), 263 jigsaw records identical (251 connected) | VERIFIED |
| 7 | Functional protection and interior clearance | `worldgen/k24-functional-survival.json`, `live/live-pool-report.json`, `DERIVATION.md` | 9,974 protected instances present, 0 replaced (Stage 24-I: 5 replaced old slab-edge cells); clearance masks cell-identical; masks air in all live placements | VERIFIED |
| 8 | Decorative decay outside the new architecture | `worldgen/decay-regression.json` | `block_rot` 3,067 → 2,972; six unchanged modules identical; tower loss cells differ only at designed or newly protected cells; 0 architecture differences unexplained | VERIFIED |
| 9 | Sauna water and the six-module regression | `worldgen/ik-comparison.json`, `worldgen/reproducibility.json`, `worldgen/sauna-bisect.json` | six modules: identical derived data, decay and layout; sauna water 385/387 (2 floor cells replaced by sculk catalysts at seeds 24006/24007) | **OPEN ITEM** (cause unresolved, reproducible, pool functional) |
| 10 | Vanilla sculk on decks | `worldgen/ik-comparison.json` | 12 of 2,990 deck-cell checks in 6 of 67 towers; all clear deck cells reachable, no ladder exit blocked | OPEN ITEM (vanilla behaviour) |
| 11 | Deferred entrances unchanged | `worldgen/k24-entrance-survey.json` | identical to Stage 24-I: 113/116 open; 24005 (14 cells), 24009 (6 cells), 24015 (drop) deferred | VERIFIED |
| 12 | Updated comparison renders | `gallery/` | before/after templates (front/rear, side silhouettes, elevated, platform close-up, cutaway, changed cells) and the same towers in the Stage 24-I and 24-K sweep worlds; headless renders | VERIFIED as simulated evidence |
| 13 | Minecraft-client verification | — | not performed | VISUAL PENDING |
