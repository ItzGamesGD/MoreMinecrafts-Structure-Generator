# ST-03 barracks batch: F02 / F03 / F04 (candidate, awaiting owner approval)

Free-design brief ST03-IMPLEMENT-05, built on `feat/st03-military-f05-f06-20261105` @ `36d036d`.

The fixed contract is unchanged; `tools/seam01/data/st03_placements.json` is not modified:

| placement | module | size (x×y×z) | rect | street face |
|---|---|---|---|---|
| F02 | `M-barracks_a` | 13×12×11 | x 24..36, z 24..34 | +x (east) |
| F03 | `M-barracks_b` | 13×12×11 | x 75..87, z 24..34 | -x (west) |
| F04 | `M-barracks_c` | 13×12×11 | x 75..87, z 39..49 | -x (west) |

All three modules use `air = include`, floor y=0 and `local_turns` 0. No approved facility or NBT was changed. The only edit to shared tooling is `experiments/st03-placement-check/place_check.py`, which now also loads batch 4.

## Concepts

The three buildings share one vocabulary: stone-brick family, dark oak, spruce. Each has its own massing, roof and material lead, so none of them is a recolour of another.

**F02 "standard hall": symmetrical, gable-front to the street.**
- **Exterior:**
  - Stone ground storey: cobble/stone footing, stone-brick walls, andesite quoins.
  - A jettied dark-oak timber gable on corbel brackets, with calcite plaster panels and a 3×2 hall window over the door.
  - A steep dark-oak roof with spruce barge boards and eave brackets at the post rhythm.
  - A jettied, plastered cross gable centred on each long side, repeating the street-gable motif.
  - Small windows with dark-oak shutters.
  - A stone rear gable with two buttresses.
- **Entrance:** a 3-wide doorway with dark-oak leaves folded back, a lantern under the jetty, and two illager banners.
- **Interior:**
  - Four bunk frames (8 berths) either side of a stone runner.
  - Footlocker chest and barrel between the bunks, under banners.
  - Weapon racks by the door.
  - A ladder in the axis up to a railed rear loft (sergeant's bed, stores), with a mess table and stools under the loft.

**F03 "stone keep": fortified.**
- **Exterior:**
  - All-stone hall on a deepslate plinth.
  - Crow-stepped gables front and rear, with slab-capped steps and a chiseled crowning stone.
  - A deepslate-tile roof with a polished-deepslate ridge.
- **Entrance:** a round-arched gate with a raised portcullis grille and open dark-oak leaves, under an oak bretèche (machicolation box) on stone corbels with a deepslate pent roof.
- **Flanks:** buttresses with barred slits between them; a chimney stack rising through the north slope.
- **Interior:**
  - Black bunk frames, weapon racks, and an arms table with benches.
  - A hearth (furnace) under the chimney.
  - An armoury under a rear loft (grindstone, smithing and fletching tables, spear barrels, chest), reached by a ladder.
  - Loft stores: target, barrels, hay, stacked hafts.

**F04 "timber lodge": residential / logistics.**
- **Roof and gables:**
  - A spruce gambrel roof (steep lower pitch, shallow upper pitch) with dark-oak barge boards.
  - The street verge forms a hoist hood: a beam, a chain and a hoisted hay bale over a loft hay door between open shutters.
  - Louvres in the gable and a ridge vent.
  - A dark-oak frame with mud-brick nogging.
- **Entrance:** a pent canopy on posts shelters the door, with barrels and hay under it.
- **Walls and rear:** broad windows with shutters and flower ledges; a stone chimney on the rear gable.
- **Interior:**
  - Four single beds under a large loft, reached by a timber stair.
  - A stove in the chimney breast, a dining table with chairs, and stores.
  - Two more beds and hay on the loft.
- **Outside:** a firewood stack along the south eave.

## Contracts kept

- **Size:** 13×12×11 for all three, checked against the placement table.
- **Placement:** no move and no rotation change.
- **Containers:** all empty, using the block-entity allow-list (`chest[type=single]`, `barrel[open=false]`, `furnace[lit=false]`, and the illager-pattern `white_wall_banner`). Ordinary loot is a runtime decision; no loot, item or probability is authored here.
- **Out of scope:** no mobs, spawners, AI, loot tables or HQ-wide integration.
- **Supplies:** exterior supplies stay inside each footprint, and the doorway lanes are kept clear.

## Files

| file | what |
|---|---|
| `build.py` | `f02()`, `f03()`, `f04()` designs, `BUILDINGS` (street entrance, wall box); a height-map roof helper with explicit inner/outer stair shapes; writes `out/` |
| `out/st03_barracks_{a,b,c}.*` | NBT, source .schem, export report |
| `checks.py` → `check-result.json` | NBT/state validity, 3-D walk access (ladder-aware) from the street entrance alone, strict 26.3 placement |
| `capture.py` → `screenshots/` | real 26.3 client F2 screenshots: isolated copies plus the real q=0 layout with every built neighbour |
| `sheet.py` → `approval/*.png` | labelled contact sheets; `comparison_approval_contact_sheet.png` is the side-by-side approval image |
| `../st03-placement-check/place-check-result-f02-f04.json` | placement-table checks (`--only M-barracks_a,M-barracks_b,M-barracks_c`) |

NBT sha256 (identical in check-result, place-check and both capture-info files):
- a: `3702b103ff9a19fb...`
- b: `0faa0ea8be5dd19b...`
- c: `536352915e6581b9...`

## Verification (run in this task on the pinned 26.3 server, sha1 33680f5f...)

**`checks.py`: PASS.**
- **verify.py:** 0 mismatches. Each NBT is 13×12×11, with 1716 cells compared. Palettes: 79 / 72 / 81 states. Every authored state is present unchanged.
- **Strict `place template`** (rotation none), every cell compared: 0 failures for all three.
- **Access**, from the single street entrance with no outside ground allowed. Reached in all three:
  - every container and workstation;
  - every floor or loft bed (upper bunks are decorative berths);
  - the loft;
  - every named key point (aisle, under-loft area, gate/stair top).

  | | F02 | F03 | F04 |
  |---|---|---|---|
  | interior feet cells | 68 | 74 | 81 |
  | loft feet cells | 15 | 12 | 18 |

  Apron supplies outside the walls are reachable from the open ground around the footprint.
- **Counts:**

  | | beds | chests | barrels | loft access |
  |---|---|---|---|---|
  | F02 | 9 (4 of them upper bunks) | 1 | 7 | ladder |
  | F03 | 8 (4 of them upper bunks) | 2 | 8 | ladder |
  | F04 | 6 | 1 | 11 | stair |

**`place_check.py --only M-barracks_a,M-barracks_b,M-barracks_c`: PASS.**
- **Footprint overlaps:** 0 for q=0..3.
- **Whole-structure turns q=1..3:** 0 failed cells (F02 742, F03 713, F04 728 non-air cells).
- **All 15 built placements placed together at q=0:** 0 failures, so the barracks do not overwrite F05/F06, houses or support buildings, and are not overwritten by them.
- **Test terrain falling 0..2 blocks:** 104 footing columns filled per barracks, 0 hollow, 0 template failures.
- **Street entrances:**

  | entrance | outside cell | free run | direction |
  |---|---|---|---|
  | F02 east door | (37, 29) | 38 blocks | east |
  | F03 west gate | (74, 29) | 38 blocks | west |
  | F04 west door | (74, 44) | 46 blocks | west |

- **Nearest neighbour gaps:**
  - F02 – F13: 3 blocks
  - F03 – F04: 4 blocks
  - F04 – F08: 3 blocks (F08 is not built yet; its footprint is reserved)

**Screenshots:** unmodified 26.3 client, Xvfb / lavapipe, noon, HUD hidden.
- **Isolated copies:** front, front-left and front-right diagonals, rear, rear diagonal and side for each barracks, plus interiors (night vision).
- **Street context in the real q=0 layout:** seven views.
- **Loft retakes:** the two loft interiors were retaken with corrected cameras; the first camera positions stood inside a fence and a hay bale. See `capture-info-loft-retake.json`, which carries the same NBT hashes.

## Design iterations (reviewed in real client screenshots)

1. **F03 v1** (side-gabled with a stepped porch) read as a flat stone box from the street, and its gable piers made a ziggurat. It was rebuilt as v2: front-gabled, refined crow steps, bretèche, buttresses, chimney.
2. **F02 front gable** with spruce infill was too dark to read the framing. Changed to calcite plaster with dark-oak shutters.
3. **F02 small dormers** read as lumps. Replaced by one jettied cross gable per long side.
4. **F04 spruce/stripped-spruce infill** merged with the spruce roof. Changed to mud-brick nogging, and a ridge vent was added.
5. **Offline access check** found footlocker chests boxed in by bunk posts (F02/F03) and a tie beam blocking headroom on the F04 loft stair. All fixed before the checks above.

## Not covered / notes

- **Road connection: UNTESTED.** The road masterplan and MQ ground modules are not in this repository. All three entrances face the free central area.
- **`BUILDINGS[...]["door"]`** is the entrance column on the street face (±x), not the +z face. `place_check.py`'s legacy `front_free_blocks` field assumes +z for every module; use its `entrances` block for the barracks.
- **Q23** suggested a 2-wide central entrance. Both 13 and 11 are odd, so a symmetric centre needs an odd width. F02 and F03 use a 3-wide opening with folded leaves; F04 uses a single door under a canopy.
- **Q21 ordinary loot** (F02 balanced, F03 military, F04 household) is not authored. The containers are slots only.
