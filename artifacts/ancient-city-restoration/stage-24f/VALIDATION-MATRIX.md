# Stage 24-F per-module validation matrix

Final set: `final-candidates/` (SHA256SUMS). Stage 24-C head `b92a4be1e9e1b901a08f1629c4f19b63dab43dce`, Stage 24-E head `5a3a57186762a2e0fcb1489b60531e328c2457b2`.
Real-generation sweep: 24 cities (seeds 24001–24024), placements identical to vanilla in **24/24**.

| Module | Source | Size | SHA-256 | Static / regression tests | Block states valid (26.1.2 registry) | Live placement mismatches | Simulated player | Generation | Terrain inside the piece box | Protected blocks lost after processors | Client visual | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `large_ruin_1` | 24-E option C | 17×14×17 | `92827808edb9` | PASS | PASS | 0 / 4 rot | 20/20 | 20 pcs, 0 overlaps, 0 unconnected jigsaws | 2 pcs (14 cells; 24-C sweep 7) | container 0/20, bed 0/80, door 0/40, lantern 1/80, stairs 0/5160 | PENDING | PENDING |
| `medium_ruin_1` | 24-C (byte-identical) | 8×5×13 | `89f58c3f982d` | PASS | PASS | 0 / 4 rot | 17/17 | 26 pcs, 0 overlaps, 0 unconnected jigsaws | 1 pcs (189 cells; 24-C sweep 189) | container 0/26, door 1/52, bed 0/52, lantern 3/52, stairs 0/312 | PENDING | PENDING |
| `medium_ruin_2` | 24-E option A | 16×8×11 | `d1e239c42bda` | PASS | PASS | 0 / 4 rot | 28/28 | 20 pcs, 0 overlaps, 0 unconnected jigsaws | 0 pcs (0 cells; 24-C sweep 0) | door 0/40, stairs 0/1740, bed 0/80, container 0/40, lantern 2/40 | PENDING | PENDING |
| `small_ruin_1` | 24-C (byte-identical) | 7×5×8 | `647fa12a5210` | PASS | PASS | 0 / 4 rot | 17/17 | 22 pcs, 0 overlaps, 0 unconnected jigsaws | 1 pcs (5 cells; 24-C sweep 6) | bed 0/44, door 0/44, container 0/22, lantern 2/22, stairs 0/220 | PENDING | PENDING |
| `small_ruin_2` | 24-C (byte-identical) | 8×5×4 | `0135f1df50b9` | PASS | PASS | 0 / 4 rot | 17/17 | 28 pcs, 0 overlaps, 0 unconnected jigsaws | 0 pcs (0 cells; 24-C sweep 0) | bed 0/56, door 0/56, container 0/28, lantern 5/28 | PENDING | PENDING |
| `sauna_1` | 24-C (byte-identical) | 29×10×37 | `879e21a0a4da` | PASS | PASS | 0 / 4 rot | 12/12 | 9 pcs, 0 overlaps, 12 unconnected jigsaws | 2 pcs (6 cells; 24-C sweep 7) | stairs 0/774, container 0/27, lantern 0/27 | PENDING | PENDING |
| `large_pillar_1` | 24-C (byte-identical) | 6×15×6 | `a17b693c1033` | PASS | PASS | 0 / 4 rot | 13/13 | 32 pcs, 0 overlaps, 0 unconnected jigsaws | 0 pcs (0 cells; 24-C sweep 0) | stairs 0/2016, ladder 0/416, lantern 6/128 | PENDING | PENDING |
| `medium_pillar_1` | 24-C (byte-identical) | 7×11×8 | `8705305a7bec` | PASS | PASS | 0 / 4 rot | 47/47 | 35 pcs, 0 overlaps, 0 unconnected jigsaws | 1 pcs (3 cells; 24-C sweep 3) | stairs 0/105, ladder 0/280, container 0/35, lantern 3/35, parapet_wall 0/630 | PENDING | PENDING |

* "Terrain inside the piece box" counts natural blocks (rock, ores, dripstone) the template leaves in place inside its bounding box — places where the
  building touches cave walls or ceilings. It is reported separately from bounding-box overlaps with other pieces and from identical placement, which do not prove it is zero.
  The comparable Stage 24-C sweep number is given for the same seeds; every cell is listed with seed and coordinates in `worldgen/f24-issues.json`.
* "Protected blocks lost" = doors, beds, ladders, stairs, parapet walls, containers, lanterns removed by the vanilla processors (block_rot 5 % on
  `#ancient_city_replaceable`, soul lantern 5 %) or by later features; each loss is listed with seed and coordinates in `worldgen/f24-issues.json`.
* Client visual verification remains **PENDING**: all images are model renders (26.1.2 block models + textures), not client screenshots.
