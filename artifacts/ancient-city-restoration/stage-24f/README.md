# Stage 24-F — owner-selected final residential designs

Selection (owner instruction): `large_ruin_1` → Stage 24-E option C (17×14×17, the +9 height is explicitly authorised); `medium_ruin_2` → Stage 24-E option A
(16×8×11); `medium_ruin_1`, `small_ruin_1`, `small_ruin_2`, `sauna_1`, `large_pillar_1`, `medium_pillar_1` → Stage 24-C, byte-identical. No other dimension changes.

References confirmed on the remote before starting: Stage 24-C `b92a4be1e9e1b901a08f1629c4f19b63dab43dce` (PR #16), Stage 24-D `02b0b198e3f016ee89b573c0355252046d065d0f` (PR #22),
Stage 24-E `5a3a57186762a2e0fcb1489b60531e328c2457b2` (PR #24). This branch is stacked on the Stage 24-E head; the Stage 24-C files (`stage-24b/`) and the Stage 24-E proposals are unchanged (CI checks both).

## Final candidate set (immutable)
`final-candidates/<module>/restored.nbt`, `final-candidates/SHA256SUMS`, `FINAL-CANDIDATES-MANIFEST.json`. `tools/stage24f/assemble.py` rebuilds the set from git objects at the
pinned commits, verifies both selections against the SHA-256 recorded in the reviewed Stage 24-E `PROPOSALS.md` and the reviewed static results, and stops on any difference; CI re-runs it and fails on any drift.

| Module | Source | Size | Final SHA-256 | Stage 24-C SHA-256 |
|---|---|---|---|---|
| `large_ruin_1` | Stage 24-E proposal option C | 17×14×17 | `92827808edb9f8f623515e983cddcc0f5aa59fcfc4a5cc95d9dafd1b3597b229` | `1eae09e6865481cae06f994a7938a6f460ec44586d325887b827109c7f844752` |
| `medium_ruin_1` | Stage 24-C validated baseline  | 8×5×13 | `89f58c3f982dcb992e585f2e3324fe89660e6492d25fc0a6724b0231afa968af` | `89f58c3f982dcb992e585f2e3324fe89660e6492d25fc0a6724b0231afa968af` |
| `medium_ruin_2` | Stage 24-E proposal option A | 16×8×11 | `d1e239c42bda2b7c0551f5b910fcc87ec10ef7ad640cf9a1bc7b4f78e7838404` | `f897372f2917e9f189f01f7d54365a4da0414f36e198a09231ff4518abd1ec48` |
| `small_ruin_1` | Stage 24-C validated baseline  | 7×5×8 | `647fa12a5210756f509e45a9b77f4bb2f57c732b1d1d74f3a9cb0be3dc838ec1` | `647fa12a5210756f509e45a9b77f4bb2f57c732b1d1d74f3a9cb0be3dc838ec1` |
| `small_ruin_2` | Stage 24-C validated baseline  | 8×5×4 | `0135f1df50b93d6953daa1da658fd3f137bd15468265cf484a7452a1516bad6d` | `0135f1df50b93d6953daa1da658fd3f137bd15468265cf484a7452a1516bad6d` |
| `sauna_1` | Stage 24-C validated baseline  | 29×10×37 | `879e21a0a4daf1b5d4fe547fe78aaa9fad5cf55ede913112d2e8a32f5697288f` | `879e21a0a4daf1b5d4fe547fe78aaa9fad5cf55ede913112d2e8a32f5697288f` |
| `large_pillar_1` | Stage 24-C validated baseline  | 6×15×6 | `a17b693c10337724e3c01402cd19a497926c1fa2afe0c81e839e2c9d61bfb9b1` | `a17b693c10337724e3c01402cd19a497926c1fa2afe0c81e839e2c9d61bfb9b1` |
| `medium_pillar_1` | Stage 24-C validated baseline  | 7×11×8 | `8705305a7bec348c40b5e7434c651526e0145aac90a9352e315150faf6a7a09d` | `8705305a7bec348c40b5e7434c651526e0145aac90a9352e315150faf6a7a09d` |

## Validation (details: `VALIDATION-MATRIX.md`)
* Tests: `tests/test_stage24f_final.py` (32: exact sources, roof geometry reproduced block-for-block from the reviewed design code, jigsaws + block entities identical to Stage 24-C,
  every block state legal in the 26.1.2 registry from the server's `--reports`, house functional checks) + all Stage 24-B/24-C/24-E tests (105 total) + the Stage 24-C regression suite run on the final set (26).
* Real Minecraft 26.1.2 server: all 8 modules × 4 rotations placed with **0 block mismatches** (lanterns, chains, stair shapes survive); sauna 43/43 water, 0 stray after 1200 ticks.
* Simulated player: **171/171** steps (doors, every bed slept in, every container opened, sauna chests roll loot, both basins, ladders to both decks, deck-edge probes, `medium_ruin_2` stairs up/down).
* Real generation (final set injected as overrides of the vanilla `ancient_city/structures` NBTs, seeds 24001–24024): placements and rotations identical to vanilla in **24/24** cities,
  **0** bounding-box overlaps; every jigsaw of the eight modules connects to a generated piece, except 12 sauna sculk-pool jigsaws that resolve to nothing exactly as in the same-method Stage 24-C re-analysis.

## Every detected generation issue (seed + world coordinates)
Terrain left inside a building's bounding box (identical placement does not prove zero terrain contact):

| Seed | Module | Type | Cells | Examples |
|---|---|---|---|---|
| 24004 | `large_ruin_1` | terrain inside bounding box | 1 | smooth_basalt (-249,-40,-1035) |
| 24004 | `large_ruin_1` | terrain inside added height | 1 | smooth_basalt (-249,-40,-1035) |
| 24005 | `medium_ruin_1` | terrain inside bounding box | 189 | dripstone_block (-1347,-50,1024), dripstone_block (-1347,-50,1025), dripstone_block (-1347,-50,1026), dripstone_block (-1347,-50,1027) … |
| 24008 | `small_ruin_1` | terrain inside bounding box | 5 | lava (596,-50,1280), lava (597,-50,1280), lava (597,-50,1281), lava (597,-49,1280) … |
| 24009 | `large_ruin_1` | terrain inside bounding box | 13 | dripstone_block (595,-50,557), dripstone_block (595,-50,558), dripstone_block (595,-49,558), dripstone_block (596,-50,557) … |
| 24012 | `sauna_1` | terrain inside bounding box | 1 | deepslate (-1245,-42,112) |
| 24014 | `medium_pillar_1` | terrain inside bounding box | 3 | deepslate (1276,-41,-932), deepslate (1279,-43,-932), deepslate (1279,-42,-932) |
| 24014 | `sauna_1` | terrain inside bounding box | 5 | lava (1293,-46,-1017), lava (1293,-45,-1017), lava (1293,-44,-1017), lava (1293,-43,-1017) … |

Protected functional blocks lost after vanilla processors/features (lanterns: vanilla 5 % rule; the door: block_rot of its support):

| Seed | Module | Block | World position | Now |
|---|---|---|---|---|
| 24001 | `medium_ruin_1` | soul_lantern | (-356,-48,138) | air |
| 24003 | `medium_pillar_1` | soul_lantern | (534,-44,-20) | air |
| 24003 | `medium_pillar_1` | soul_lantern | (592,-44,50) | air |
| 24003 | `small_ruin_2` | soul_lantern | (594,-48,67) | air |
| 24005 | `medium_ruin_1` | soul_lantern | (-1374,-48,997) | air |
| 24007 | `medium_ruin_1` | spruce_door | (-264,-50,928) | air |
| 24007 | `large_pillar_1` | soul_lantern | (-287,-39,947) | air |
| 24007 | `large_pillar_1` | soul_lantern | (-255,-39,819) | air |
| 24008 | `medium_ruin_2` | soul_lantern | (445,-48,1325) | air |
| 24009 | `small_ruin_2` | soul_lantern | (560,-48,596) | air |
| 24009 | `large_pillar_1` | soul_lantern | (421,-39,597) | air |
| 24010 | `large_pillar_1` | soul_lantern | (-3011,-39,2324) | air |
| 24010 | `small_ruin_2` | soul_lantern | (-3077,-48,2222) | air |
| 24011 | `large_ruin_1` | soul_lantern | (-85,-48,-579) | air |
| 24011 | `large_pillar_1` | soul_lantern | (-261,-39,-517) | air |
| 24012 | `small_ruin_1` | soul_lantern | (-1329,-48,-39) | air |
| 24013 | `small_ruin_2` | soul_lantern | (1123,-48,1183) | air |
| 24014 | `small_ruin_2` | soul_lantern | (1294,-48,-965) | air |
| 24018 | `large_pillar_1` | soul_lantern | (1265,-39,45) | air |
| 24022 | `medium_pillar_1` | soul_lantern | (-989,-44,-189) | air |
| 24022 | `medium_ruin_2` | soul_lantern | (-943,-48,-300) | air |
| 24022 | `small_ruin_1` | soul_lantern | (-980,-48,-387) | air |
| 24023 | `medium_ruin_1` | soul_lantern | (-554,-48,1683) | air |

Sauna: 12 of its 45 generated "up" jigsaws (pool `ancient_city/sculk`) resolve to nothing — identical (12/45) in the Stage 24-C sweep re-analysed with the same method; vanilla behaviour, not a regression.

## Outstanding defects / limits
* `large_ruin_1` (seed 24004, (-249,-40,-1035)): one smooth-basalt cell of natural terrain inside the new roof height — the only terrain contact in the added +9 volume across 20 pieces.
* `large_ruin_1` (seed 24009): a dripstone cluster (13 cells) inside the courtyard/rooms; the Stage 24-C sweep had a 7-cell cluster in the same piece at another spot — pre-existing class.
* `medium_ruin_1` (seed 24005): piece buried in a dripstone cave (189 cells), unchanged from Stage 24-C (vanilla terrain adaptation).
* Vanilla decay: 22 lanterns and 1 door lost across 192 generated pieces; not removed (owner decision from Stage 24-D V5).
* Minecraft-client visual verification: **PENDING** — the gallery (`gallery/index.html`, `stage-24f-final-gallery.zip`) contains model renders (26.1.2 block models/textures, studio light), not client screenshots.
* The simulated player is a re-implementation of client physics, not the vanilla client.
