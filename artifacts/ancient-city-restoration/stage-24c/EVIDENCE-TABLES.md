# Machine-generated evidence tables

## Simulated-player gameplay: PR #10 baseline vs Stage 24-C final

| module | PR #10 baseline | failed steps (baseline) | 24-C final | failed steps (final) |
|---|---|---|---|---|
| `large_ruin_1` | 20/20 | - | 20/20 | - |
| `medium_ruin_1` | 17/17 | - | 17/17 | - |
| `medium_ruin_2` | 20/24 | stairs_walk_up_east, bed1_[11, 5, 3]_reach, bed1_sleep, barrel_[13, 5, 8]_reach | 28/28 | - |
| `small_ruin_1` | 17/17 | - | 17/17 | - |
| `small_ruin_2` | 16/17 | bed0_sleep | 17/17 | - |
| `sauna_1` | 11/12 | bath1_3cells_rim_reach | 12/12 | - |
| `large_pillar_1` | 13/17 | climb_ground_to_deck, step_onto_deck, deck_edge_north_line2, deck_edge_west_line2 | 13/13 | - |
| `medium_pillar_1` | 34/47 | deck_edge_north_line1, deck_edge_north_line2, deck_edge_north_line4, deck_edge_north_line5, deck_edge_south_line3, deck_edge_south_line4, deck_edge_south_line5, deck_edge_east_line1, deck_edge_east_line2, deck_edge_east_line5, deck_edge_east_line6, deck_edge_west_line1, deck_edge_west_line2 | 47/47 | - |

## Isolated placement (8 modules x 4 rotations, 1200 ticks)

| module | rotations | PR #10 mismatching blocks | final mismatching blocks | block entities missing | water kept / expected | stray water |
|---|---|---|---|---|---|---|
| `large_ruin_1` | 4 | 16 | 0 | 0 | 0/0 | 0 |
| `medium_ruin_1` | 4 | 8 | 0 | 0 | 0/0 | 0 |
| `medium_ruin_2` | 4 | 4 | 0 | 0 | 0/0 | 0 |
| `small_ruin_1` | 4 | 4 | 0 | 0 | 0/0 | 0 |
| `small_ruin_2` | 4 | 4 | 0 | 0 | 0/0 | 0 |
| `sauna_1` | 4 | 12 | 0 | 0 | 43/43 | 0 |
| `large_pillar_1` | 4 | 8 | 0 | 0 | 0/0 | 0 |
| `medium_pillar_1` | 4 | 4 | 0 | 0 | 0/0 | 0 |

## Real Ancient City generation: 24 seeds (24001-24024), vanilla vs candidate

- placements (template/position/rotation) identical to vanilla in **24/24** cities
- only bounding-box difference: `medium_ruin_2` (20 pieces, y-extent 5 -> 8)

| module | generated pieces | rotations seen | BB overlaps with other pieces | blocks identical | cracked (vanilla processor) | removed to air (block_rot / lantern rule) | sculk overlay (vanilla feature) | other replacement |
|---|---|---|---|---|---|---|---|---|
| `large_ruin_1` | 20 | CLOCKWISE_180:7, CLOCKWISE_90:5, COUNTERCLOCKWISE_90:5, NONE:3 | 0 | 55.3% | 22.3% | 3.5% | 18.9% | 0.01% |
| `medium_ruin_1` | 26 | CLOCKWISE_180:4, CLOCKWISE_90:4, COUNTERCLOCKWISE_90:12, NONE:6 | 0 | 57.4% | 19.9% | 2.7% | 19.8% | 0.15% |
| `medium_ruin_2` | 20 | CLOCKWISE_180:2, CLOCKWISE_90:4, COUNTERCLOCKWISE_90:6, NONE:8 | 0 | 50.1% | 20.5% | 3.5% | 26.0% | 0.00% |
| `small_ruin_1` | 22 | CLOCKWISE_180:7, CLOCKWISE_90:5, COUNTERCLOCKWISE_90:4, NONE:6 | 0 | 62.3% | 20.3% | 3.1% | 14.3% | 0.02% |
| `small_ruin_2` | 28 | CLOCKWISE_180:8, CLOCKWISE_90:6, COUNTERCLOCKWISE_90:7, NONE:7 | 0 | 54.8% | 18.3% | 3.2% | 23.7% | 0.00% |
| `sauna_1` | 9 | CLOCKWISE_180:3, CLOCKWISE_90:4, COUNTERCLOCKWISE_90:1, NONE:1 | 0 | 61.7% | 17.7% | 3.5% | 16.9% | 0.21% |
| `large_pillar_1` | 32 | CLOCKWISE_180:9, CLOCKWISE_90:5, COUNTERCLOCKWISE_90:11, NONE:7 | 0 | 82.9% | 2.0% | 2.1% | 11.7% | 1.36% |
| `medium_pillar_1` | 35 | CLOCKWISE_180:12, CLOCKWISE_90:10, COUNTERCLOCKWISE_90:8, NONE:5 | 0 | 68.5% | 14.5% | 2.7% | 14.0% | 0.35% |

### Critical blocks lost after vanilla processors (lost / total, all generated pieces)

| module | ladder | stairs | bed | door | container | parapet_wall | lantern |
|---|---|---|---|---|---|---|---|
| `large_ruin_1` | - | - | 0/80 | 0/40 | 0/20 | - | 1/80 |
| `medium_ruin_1` | - | 0/312 | 0/52 | 1/52 | 0/26 | - | 2/52 |
| `medium_ruin_2` | - | 0/80 | 0/80 | 0/40 | 0/40 | - | 2/40 |
| `small_ruin_1` | - | 0/220 | 0/44 | 0/44 | 0/22 | - | 2/22 |
| `small_ruin_2` | - | - | 0/56 | 0/56 | 0/28 | - | 4/28 |
| `sauna_1` | - | 0/774 | - | - | 0/27 | - | 0/27 |
| `large_pillar_1` | 0/416 | 0/2016 | - | - | - | - | 6/128 |
| `medium_pillar_1` | 0/280 | 0/105 | - | - | 0/35 | 0/630 | 3/35 |

### medium_ruin_2 world-space placements (height 8)

| seed | rotation | world BB (x0,y0,z0,x1,y1,z1) | adjacent pieces | overlapping pieces |
|---|---|---|---|---|
| 24002 | COUNTERCLOCKWISE_90 | (874, -51, -793, 884, -44, -778) | intact_horizontal_wall_passage_1 | 0 |
| 24005 | COUNTERCLOCKWISE_90 | (-1466, -51, 913, -1456, -44, 928) | intact_horizontal_wall_bridge | 0 |
| 24005 | NONE | (-1430, -51, 972, -1415, -44, 982) | intact_horizontal_wall_stairs_2 | 0 |
| 24008 | CLOCKWISE_90 | (519, -51, 1306, 529, -44, 1321) | ruined_horizontal_wall_stairs_3 | 0 |
| 24008 | CLOCKWISE_180 | (432, -51, 1319, 447, -44, 1329) | ruined_horizontal_wall_stairs_1 | 0 |
| 24009 | NONE | (508, -51, 584, 523, -44, 594) | intact_horizontal_wall_passage_1 | 0 |
| 24011 | COUNTERCLOCKWISE_90 | (-142, -51, -633, -132, -44, -618) | ruined_horizontal_wall_stairs_1 | 0 |
| 24012 | COUNTERCLOCKWISE_90 | (-1399, -51, 42, -1389, -44, 57) | intact_horizontal_wall_1 | 0 |
| 24014 | NONE | (1388, -51, -904, 1403, -44, -894) | intact_horizontal_wall_passage_1 | 0 |
| 24014 | CLOCKWISE_90 | (1432, -51, -937, 1442, -44, -922) | ruined_horizontal_wall_stairs_1 | 0 |
| 24015 | COUNTERCLOCKWISE_90 | (-263, -51, -215, -253, -44, -200) | ruined_horizontal_wall_stairs_2 | 0 |
| 24017 | NONE | (81, -51, 152, 96, -44, 162) | intact_horizontal_wall_stairs_4 | 0 |
| 24017 | NONE | (47, -51, 202, 62, -44, 212) | ruined_horizontal_wall_stairs_3 | 0 |
| 24017 | COUNTERCLOCKWISE_90 | (125, -51, 150, 135, -44, 165) | intact_horizontal_wall_stairs_4 | 0 |
| 24019 | CLOCKWISE_90 | (-757, -51, -1514, -747, -44, -1499) | ruined_horizontal_wall_stairs_3 | 0 |
| 24021 | NONE | (-326, -51, 118, -311, -44, 128) | ruined_horizontal_wall_stairs_2 | 0 |
| 24022 | CLOCKWISE_180 | (-956, -51, -306, -941, -44, -296) | ruined_horizontal_wall_stairs_2 | 0 |
| 24022 | CLOCKWISE_90 | (-1067, -51, -198, -1057, -44, -183) | ruined_horizontal_wall_stairs_3 | 0 |
| 24023 | NONE | (-595, -51, 1767, -580, -44, 1777) | ruined_horizontal_wall_stairs_1 | 0 |
| 24023 | NONE | (-595, -51, 1786, -580, -44, 1796) | ruined_horizontal_wall_stairs_4 | 0 |
