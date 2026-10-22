# Stage 24-G — validation matrix

Statuses: **VERIFIED** (measured on the real 26.1.2 server / in real generated worlds), **PARTIAL**, **BLOCKED**,
**OWNER DECISION REQUIRED**, **VISUAL PENDING**.

| # | check | evidence | result | status |
|---|---|---|---|---|
| 1 | Removal mechanism documented from the 26.1.2 code | `INVESTIGATION.md`, decompiled `BlockRotProcessor`, `RuleProcessor`, `JigsawReplacementProcessor`, `ProtectedBlockProcessor`, `SinglePoolElement`, `ListPoolElement`, `StructureTemplate`, `DoorBlock`, `LadderBlock` | block_rot (position-seeded, 5 % of `#ancient_city_replaceable`), jigsaw `structure_void` cells left unwritten, no shape updates at placement | VERIFIED |
| 2 | Processor model = engine | `investigation/jvm-rng-crosscheck.txt` (real JVM classes), `investigation/f24-processor-replay.json` | RNG bit-identical; 91,118 cells of the 24-F sweep predicted, 211 later-feature exceptions explained | VERIFIED |
| 3 | Door lower-half loss root cause | seed 24007 medium_ruin_1 (-264,-50,928) in 24-C and 24-F worlds; 48/48 door-support cells unwritten in 24-F | support cell unwritten (`structure_void` jigsaw); the exact update that removed the lower half not isolated | VERIFIED / last step HYPOTHESIS |
| 4 | Structural NBT hashes unchanged | `protection/BUILD-MANIFEST.json`, test `test_structure_nbts_unchanged_from_stage24f`, CI `cmp` | all 8 byte-identical to Stage 24-F (large_ruin_1 Option C 17×14×17, medium_ruin_2 Option A 16×8×11, six 24-C modules) | VERIFIED |
| 5 | Jigsaw metadata, loot tables, block entities preserved | NBTs unchanged; overlays carry no jigsaws / block entities / entities (unit tests); containers opened and beds slept in on decayed placements | preserved | VERIFIED |
| 6 | Only the eight restored entries change; no global behaviour change | `test_pool_override_changes_only_wrapped_restored_entries`; vanilla processor lists and tags not overridden | 6 entries wrapped, every other entry byte-equal to vanilla; large_ruin_1 / small_ruin_2 unchanged | VERIFIED |
| 7 | Protected cells survive — real server, 8 modules × 4 rotations | `live/live-processing-report.json` (`/place jigsaw`, real pool processors, layer under the piece cleared to air) | Stage 24-G: 59 placements, **0** protected cells lost, 0 unexplained blocks; same test with the 24-F entry: 58 lost in 29 of 63 placements | VERIFIED |
| 8 | Protected cells survive — real world generation, 24 seeds | `worldgen/g24-functional-survival.json` vs `investigation/f24-functional-survival.json` | 5,006 protected cell instances: Stage 24-F 186 missing + 8 replaced; Stage 24-G **0 missing**, 5 replaced by later ore features (tuff/gravel, still solid) | VERIFIED |
| 9 | Decorative decay preserved | `worldgen/g24-summary.json` `decorative_decay`; live counts | 3,271 / 64,846 decorative cells rotted (5.04 %) in **both** sweeps; 25 lanterns to air and 17,458 cracked bricks/tiles in both; live: 5.03 % (G) vs 4.93 % (F) | VERIFIED |
| 10 | Doors usable, ladders climbable, beds/containers reachable, stair headroom, deck edges safe — decayed placements, 4 rotations | `live/gameplay/summary-decayed.json` (mineflayer, Stage 24-C/24-F scenarios rotated into each placement) | **684 / 684** steps pass (171 × 4) | VERIFIED |
| 11 | Piece placement and rotation vs vanilla and 24-F | `worldgen/g24-summary.json` `placements` | 24/24 cities, 2,160 pieces identical to Stage 24-F (position, rotation, box, ground delta, junctions); identical to vanilla except the owner-approved taller boxes of large_ruin_1 / medium_ruin_2 | VERIFIED |
| 12 | Bounding-box overlaps | `worldgen/g24-analysis.json` | 0 | VERIFIED |
| 13 | Unexpected block changes | `worldgen/g24-processor-replay.json`, `worldgen/g24-issues.json` | 180, all explained: 175 plain deepslate -> tuff/gravel/ore by later ore features, 5 candle states; no unexplained change | VERIFIED |
| 14 | Terrain contact classified | `TERRAIN-CLASSIFICATION.md`, `worldgen/g24-terrain-classification.json` | 136 functional obstruction (24005 medium_ruin_1, 24009 large_ruin_1), 11 lava (24008 small_ruin_1 room, 24014 sauna_1), 70 vanilla/environmental, 1 cosmetic (24004) | VERIFIED |
| 15 | large_ruin_1 seed 24004 (-249,-40,-1035) | `TERRAIN-CLASSIFICATION.md`, gallery `terrain-large_ruin_1-24004-*` | one amethyst-geode smooth-basalt block in the corner of the added height, touches no roof/room/path: cosmetic | VERIFIED |
| 16 | Terrain/fluids inside rooms (navigation failures) | `OWNER-DECISION-interior-terrain.md` | not fixed: needs clearing terrain in room interiors | OWNER DECISION REQUIRED |
| 17 | Unconnected sauna sculk jigsaws | `worldgen/g24-issues.json` | 12, vanilla `ancient_city/sculk` pool resolving to nothing (same as 24-C/24-F) | VERIFIED (vanilla behaviour) |
| 18 | Visual evidence | `gallery/` (70 images, 10 cases) | model renders of real generated world blocks, same seed in 24-F vs 24-G | VERIFIED as simulated evidence |
| 19 | Minecraft-client verification | — | no rendering client in this environment | VISUAL PENDING |
