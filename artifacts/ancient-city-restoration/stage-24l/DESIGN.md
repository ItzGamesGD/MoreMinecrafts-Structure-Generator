# Stage 24-L - Ancient City connectivity: design report (DESIGN ONLY)

Baseline: main `ab5959227ab7ad529533c62a1c7818e23a606911`. Stage 24-K: CODE VERIFIED / conditional PASS, **VISUAL PENDING**.
Accepted and not reopened: sauna water 385/387, limited sculk on watchtower decks, deferred entrance seeds 24005 / 24009 / 24015,
seed 24012 water flow, seed 24014 lava column. Nothing here is implemented; the measurement is read-only
(`phase0/PHASE0-RESULTS.md`, `tools/stage24l/phase0.py`). Everything below is a static model of saved worlds, **not client gameplay**.

## 1. Phase 0 findings (24 seeds, 116 house doors)

1. **Reproduction.** All 116 entrance observations of the Stage 24-I survey are reproduced row for row (door, status, cells, path);
   the regenerated city layouts equal the committed Stage 24-K manifests in 24/24 seeds.
2. **Street connectivity is not a problem for houses.** In the walkable-area graph (two-way steps of +-1 block) **113 of 116 doors open into
   one single main component per city**, not just into "a 200-cell area". The five largest other components of each seed (120) contain **no**
   house door: 69% of their sampled cells are natural cave floor, the rest wall-top walkways; 29 of them can be left by a safe drop onto
   the main component. Routes between buildings (311 routes to the 3 nearest neighbours, median 94 blocks, p90 184) and from every one of the 113
   buildings to the city entrance path (median 76) exist everywhere; 36% of the steps lie in vanilla `wall_stairs` piece boxes, 22% on natural
   terrain. Existing streets and stairs therefore already provide usable routes; no road, bridge or walkway is missing for the houses.
3. **No door apron is needed in general.** The step from the door to the street is -1 block at 96 doors, 0 at 17, and only one door
   (seed 24015) differs (-4). Aprons or stair landings would fix nothing for 113 doors.
4. **A house box cannot be grown.** The cell directly outside **every one of the 116 doors lies inside the box of another piece**
   (vanilla wall pieces: `wall_stairs` 83, `wall_passage` 16, `wall` 12, `wall_bridge` 5). Enlarging a house template by one block on its door side
   would overlap that piece in 116/116 cases and change jigsaw collision, i.e. the city layout, by construction.
5. **The three deferred entrances are three different things:**

| seed | piece | class | exact obstruction | owner of the blocked cells | minimum change (computed, nothing applied) |
|---|---|---|---|---|---|
| 24005 | medium_ruin_1 #71, door (-1348,-50,1029) | **natural terrain interference** | 14 `dripstone_block`, x=-1349, y=-50..-49, z=1029..1035 (2 x 7 strip along the wall); no walkable cell outside the door | all 14 inside the box of vanilla `intact_horizontal_wall_1`, none inside the house box; 0 architecture | clear 14 natural cells; placing blocks alone cannot help |
| 24009 | large_ruin_1 #59, door (597,-50,551) | **natural terrain interference** | 6 `dripstone_block`, x=595..597, y=-50..-49, z=550 | all 6 inside the box of vanilla `ruined_horizontal_wall_stairs_4`; 0 architecture | clear 6 natural cells; placing alone cannot help |
| 24015 | large_ruin_1 #55, door (-272,-50,-154) | **terrain gap, not an obstruction** | the cell outside the door is a 4-deep pit (floor y=-55, front cell y=-54 is in a 27-cell pocket); the ledge of the neighbouring `intact_horizontal_wall_passage_1` is 1 cell further, at feet y=-51. The building interior is not in the main component (no other opening). Main can drop into the pocket, the pocket cannot climb out | the pit cells belong to **no** piece box | **one** floor block at (-272,-52,-153) joins the door (step down 1) to the main component; no natural block removed |

   No door in the other 21 seeds has a missing floor in front of it, so the 24015 pattern occurs once in 116 doors (0.9%); the dripstone pattern twice (1.7%).
6. **Out-of-box writes are mostly possible but not always.** For 5 of 116 doors the outside cell lies in a chunk that the house box does not touch,
   so a write there would be clipped (consistent with the Stage 24-I experiment). The 24015 gap cell is in a chunk the box touches.
7. **Rotations / modules.** Open doors occur in every module and rotation (table 7 of the results); the three failures are `medium_ruin_1` NONE,
   `large_ruin_1` CLOCKWISE_90 and `large_ruin_1` COUNTERCLOCKWISE_90, i.e. no systematic module or rotation defect.

## 2. Problem classes

* **Building access** (door -> street): 113/116 fine; 24005 and 24009 blocked by natural dripstone inside neighbouring vanilla wall boxes.
* **Terrain obstruction**: 24015 is a one-cell floor gap, not a clearing problem.
* **Street connectivity** (building <-> building / city entrance): no deficit found for houses in 24 seeds.

## 3. Alternatives (revised by Phase 0)

| # | approach | 24005 | 24009 | 24015 | terrain destroyed | generation safety | verdict |
|---|---|---|---|---|---|---|---|
| 0 | accept as natural variation (97.4% of doors open) | no | no | no | none | unchanged | **recommended for 24005 / 24009** |
| 1 | out-of-box air clearing in a list-element overlay | partly (regrowth) | yes | no | natural blocks beside every placement | unreliable (5/116 clipped, dripstone regrows) | rejected (24-I) |
| 2 | grow the house box by one block at the door | - | - | - | none | **collides with another piece at 116/116 doors** | rejected by Phase 0 |
| 3 | fill-only floor patch: a derived element writes one floor block at the cell outside the door **only where it is air/water** | no | no | yes (1 block) | none (only fills air) | writes outside the box (clip risk 5/116, 24015 not clipped); fires nowhere else in 24 seeds; layout unchanged because the box is not changed | **candidate for 24015, needs Phase 1 proof** |
| 4 | stair / landing / bridge modules | no | no | not needed (1 block) | none | new pieces change layout | not needed |
| 5 | road / walkway street links | no | no | no | none | new pieces change layout | not needed (no isolated house) |
| 6 | clear the dripstone through the vanilla wall pieces | yes | yes | no | natural blocks, in every city | global change to vanilla pieces | only with an explicit owner decision |
| 7 | post-generation excavator / carve | yes | yes | no | yes | structure-unaware | excluded by the owner |

## 4. Recommended minimum-change interventions

* **24005, 24009: keep accepted (Alt 0).** The obstruction is natural dripstone inside neighbouring vanilla wall boxes; every mechanism that
  removes it is either unreliable, global on vanilla pieces, or excluded. Both buildings' interiors remain usable once reached.
* **24015: optional Alt 3**, one air-only floor block outside the door. It places a block and removes none, leaves the box and the layout unchanged,
  and is inert wherever a floor already exists. It needs a Phase 1 proof on the pinned server (below) before any approval to implement.
* **Street links, aprons and stair landings: not warranted** by the measurements.

## 5. Owner decisions needed before any implementation

1. Keep 24005 and 24009 accepted (recommended), or authorise a global vanilla-wall-piece change / another new mechanism?
2. Fix 24015 with the one-block fill-only patch (Alt 3), or keep it accepted too?
3. If Alt 3: may a derived Stage 24-L datapack layer (new pool-element overlay, same templates) be created, with a new identity baseline for the
   derived data while the 24-F residential NBTs and 24-K towers stay byte-identical?
4. Phase 1 (proof, no production change) approval: on the pinned 26.1.2 server, test that (a) the overlay writes the cell, (b) the 24-seed layout
   is unchanged, (c) a bot walks door -> street at 24015 in 4 rotations, (d) the patch is inert at every other door, (e) the 32 production identities hold.

## 6. Uncertainties

* Static geometry only; the main component includes natural cave floor (22% of route steps). A stricter "city streets only" graph is possible but
  every house door being in one component still holds with the model used by Stage 24-I.
* Ladders / upper floors are not modelled; wall-top walkways are separate components and are not building access.
* No bot navigation was run in Phase 0; the only scripted navigation evidence remains Stage 24-I. Nothing was verified in the Minecraft client.
* 24 seeds are a small sample: the 0.9% / 1.7% rates are indicative.
* Visuals remain VISUAL PENDING.
