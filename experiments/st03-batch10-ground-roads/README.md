# ST-03 batch 10: ground / road modules MQ-NW, MQ-NE, MQ-SW, MQ-SE (new design, owner screenshot approval pending)

**This is a new design.** The road masterplan of the external design package (`ST03_PHASE_B2_V2_AUDIT_20261029.zip`,
SHA-256 prefix `0b025a52`) has not been obtained. Nothing here restores, reconstructs or claims to match it.
- The road plan is designed from scratch, following the owner-approved direction Q1-Q4 (2026-11-14).
- It is built around the structures and entrances that exist in this repository.

Base: batch 9 `aa3ac8b` (towers and gatehouse) on the batch-8 tip `831e125`.

## Contract (confirmed facts, unchanged)

| module | file | size | air | order | placement (st03_placements.json) |
|---|---|---|---|---|---|
| MQ-NW | `out/st03_ground_nw.nbt` | 51×8×51 | include | 1 | GROUND-NW x5-55 z5-55, turns 0 |
| MQ-NE | `out/st03_ground_ne.nbt` | 51×8×51 | include | 1 | GROUND-NE x56-106 z5-55, turns 0 |
| MQ-SW | `out/st03_ground_sw.nbt` | 51×8×51 | include | 1 | GROUND-SW x5-55 z56-106, turns 0 |
| MQ-SE | `out/st03_ground_se.nbt` | 51×8×51 | include | 1 | GROUND-SE x56-106 z56-106, turns 0 |

- **Tiling and order:** the four modules tile the inside of the walls (x/z 5-106) exactly. They are placed first, and
  towers, walls, the gate and F01-F20 are placed over them. Inside those footprints MQ holds only coarse dirt, which
  the later placement overwrites.
- **Grade:** y0 is grade, the same plane as every facility floor, the wall footing and the tower and gate ground
  course. The assembly places every module at one y, so roads and floors meet flush.
- **Effect of `air = include` (8 high):** placing MQ clears terrain up to 7 blocks above grade inside its box. This
  follows from the module table; this batch did not choose it. Ground below grade needs the same placement-time
  footing fill as the walls (Q89), and natural worldgen is not hooked up (see UNTESTED).
- Not changed: no module, placement, building, wall or tower was moved or edited. The wall F adoption (D-1) and the
  F06 grass fix (D-9) are owner decisions; this batch does not swap or edit those assets.

## Design (owner Q1-Q4, 2026-11-14; ledger Q76-Q79 and Q93 read as context)

**Road network** (q=0 frame, inclusive rectangles; `ROADS` in `build.py`):

| road | level | rect x0,z0-x1,z1 | width | joins |
|---|---|---|---|---|
| avenue: gate → plaza | main | 53,38-58,99 | 6 | gate passage x53-58 at z99; plaza |
| plaza before the manor | main (square) | 44,26-67,37 | 24×12 | avenue, barracks street, manor lanes; F01 porch |
| barracks street | main | 37,27-74,31 | 5 | F02 front, F03 gate, yard lane, depot lane |
| middle road | main | 37,73-91,77 | 5 | avenue, yard lane, depot lane, east service lane, F09 front |
| south road (gate side) | main | 7,93-99,97 | 5 | avenue; F07, F19, F20 and F10 fronts; T-SW and T-SE |
| west / east manor lanes | secondary | 45,7-47,25 / 65,18-67,25 | 3 | plaza ↔ north lanes |
| north wall lane | secondary | 13,7-47,9 | 3 | T-NW door |
| north-west houses lane | secondary | 13,18-47,20 | 3 | F11, F12; F13 lane |
| north-east houses lane | secondary | 68,18-104,20 | 3 | F15, F14; T-NE lane |
| yard lane | secondary | 37,32-39,72 | 3 | F05 portal and service door (two 3-wide spurs), F06 road gate |
| depot lane | secondary | 72,32-74,72 | 3 | F04 front, F08 unloading bay, F08 loft-stair apron |
| east service lane | secondary | 89,21-91,72 | 3 | F16, F17 and F18 fronts (3-wide spurs) |
| spurs / aprons | secondary | see `ROADS` | 1-3 | F13, F09, F19, F20, T-NE, T-SE, F07, F10, T-SW |

- **Main roads:** 5-6 wide (Q2); the plaza is the square.
- **Secondary lanes:** 3 wide.
- **Aprons:** 1-3 blocks long. Each joins a door to the road beside it.
- **Spine:** gate → avenue → plaza → manor.
- **Other routes:** loops connect every quarter, and there is no dead-end maze.

**Surface palette** (y0; shares measured on the final design):

| level | mix |
|---|---|
| main roads | dirt path 31 %, gravel 26 %, cobblestone 16 %, andesite 9 %, then stone, coarse dirt, mossy cobble and some stone bricks |
| plaza, junctions of main roads and the last avenue stretch before the manor (Q78: neat stone, stone at intersections) | stone bricks 51 %, polished andesite 20 %, then cracked stone bricks, andesite, gravel and mossy stone bricks |
| lanes | dirt path 35 %, coarse dirt 31 %, gravel 26 %, cobblestone 7 %, packed mud 1 % |
| edges | one ragged cell beside roads in about 40 % of places (coarse dirt, dirt path, gravel, rooted dirt), level and walkable |
| open ground | grass with coarse / rooted dirt patches and a little moss |

Materials come in patches (value noise), not per-block speckle.

**Ground (Q3, partial levelling):**
- Roads, junctions and door aprons are level at grade.
- Away from them (at least 3 blocks from a road, a building or the wall), low mounds keep a natural micro-relief:
  213 cells, 10 of them 2 high and only inside a mound, so every step is one block.
- No exposed plain dirt and no grass or dirt path under a block (random ticks would change either; see the F06
  finding).

**Decoration (Q4, medium density):**
- 25 roadside clusters: 5 barrel groups (empty barrels), 5 hay groups, 3 log piles, 3 barrel + chopping-block groups,
  4 fence rails with a torch, 5 torch posts (including the plaza corners and junctions), plus weeds (short grass,
  fern).
- Clearance: clusters are anchored 2 blocks off a road edge and never stand on a road or its ragged fringe. They also
  keep at least 2 blocks from every entrance and every building footprint.
- Nothing stands on a road; there are no chests, loot, spawners or mobs.

## Verification (all newly run 2026-11-14, pinned 26.3 server sha1 33680f5f…)

| # | item | result | evidence |
|---|---|---|---|
| A1 | NBT validity, size, block states | PASS | `check-result.json` `modules`: verify.py, 0 mismatches. Each module: 20808 cells, 51×8×51; palette 23-30. Every authored state present unchanged, with no extra non-air cell. |
| A2 | ground / support | PASS | 0 holes at y0, 0 grass / dirt path under a block, 0 exposed plain dirt; every torch and weed supported |
| A3 | boundary / interface | PASS | MQ tile x/z 5-106 exactly; 0 road cells inside any other placement's footprint |
| B1 | gate ↔ main road, road connectivity | PASS | 2455 road cells, all one network from the gate passage (56,99) |
| B2 | every entrance on the network | PASS | 27 entrances: F01-F20 (all doors and portals), 4 tower doors, gate passage — every entrance cell is a road cell |
| B3 | walk test, assembled q=0 (all 34 placements) | PASS | Walking search from outside the gate through the passage: every entrance reached, and one step inside each building |
| B4 | road widths free of obstruction | PASS | Every road rectangle is paved over its full nominal width; nothing at y1-y2 on any road cell in the assembled structure. Main 5-6, lanes 3. |
| B5 | decoration placement | PASS | 0 clusters on a road, within 2 of an entrance or within 2 of a building |
| B6 | steps / holes | PASS | Neighbouring walkable surfaces differ by at most 1 block everywhere in the MQ ground |
| B7 | walls / towers / gate | PASS | MQ never reaches the walls (x/z 0-4, 107-111). Towers and gate overwrite MQ inside their boxes by order. Live B: towers, gate and walls 0 failures. |
| C1 | server load, strict placement | PASS | `place template` of each module, rotation none: every cell compared including air, 0 failures |
| C2 | rotations q=1-3 | PASS | `../st03-placement-check/place-check-result-ground.json` live A: all 32 placements (incl. the 4 MQ) per turn, every cell, 0 failures |
| C3 | whole ST-03, q=0 | PASS for MQ and all new modules | Same file, live B: all 34 placements together. Each cell is compared with its final owner in manifest order: MQ 1942-2106 cells compared each, 695-905 overwritten by later placements by design. **2 failures in F06** (known grass defect, see below). |
| C4 | drop test terrain (0-2) | PASS | Same file, live C: all 34 placements, 0 hollow, 0 template failures |
| C5 | slope site | PASS (test terrain) | MQ-SE on ground −4..+3: 1236 columns filled (max 4), 0 template failures, 0 hollow, 0 outside cells changed. 1679 terrain cells above grade cleared by `air = include`. |
| C6 | real client | done | 33 F2 screenshots in `screenshots/`: whole compound q=0 and q=1-3, 12 road views, 9 entrance views (3 retaken), decoration, mounds, slope site. Contact sheets in `approval/`; schematic plan `approval/plan_q0.png` |
| – | natural worldgen on real seeds and biomes, generator hook for the below-grade fill | UNTESTED | no ST-03 worldgen exists |

## Findings

- **F06 grass, known and out of scope:**
  - F06 authors 33 `grass_block` cells under its own blocks. A random tick turns them to dirt, so live B fails 1-2
    of them per run, at varying cells.
  - The owner approved a minimal fix (D-9). This batch does not touch F06.
  - Random ticks were switched off during the screenshot session only.
- **Grass spreading onto exposed dirt:** found and fixed in this batch. The first build left plain dirt next to
  grass; one strict-placement check failed when grass spread onto it. Exposed dirt is now coarse or rooted dirt,
  and the check guards it.
- **place_check live B:**
  - It compared every placement's whole template, which assumes no overlap.
  - MQ is overwritten by design, so live B now compares each cell with its final owner in manifest order. For every
    earlier module nothing overlaps, so their results are unchanged.

## Remaining weaknesses (seen in the client)

- Large lawns stay between the avenue and the lanes. Q4 asked for medium density, so they are not filled.
- `dc_03` shows some mounds as small square blocks. Mounds are at most 2 high and follow value noise, so some read
  blocky up close.

## Reproduce

```
PYTHONPATH=. python experiments/st03-batch10-ground-roads/build.py
PYTHONPATH=. python experiments/st03-batch10-ground-roads/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py --server-jar server.jar --java java25 --work <dir> \
    --out experiments/st03-placement-check/place-check-result-ground.json
PYTHONPATH=. python experiments/st03-batch10-ground-roads/capture.py --server-jar server.jar --java java25 \
    --client-dir client --work <dir> --out experiments/st03-batch10-ground-roads/screenshots
python experiments/st03-batch10-ground-roads/sheet.py experiments/st03-batch10-ground-roads/screenshots \
    experiments/st03-batch10-ground-roads/approval
PYTHONPATH=. python experiments/st03-batch10-ground-roads/plan_render.py experiments/st03-batch10-ground-roads/approval/plan_q0.png
```
